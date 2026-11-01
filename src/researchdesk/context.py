"""Inspectable, budgeted context assembly. Sentence presence is not entailment."""

import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from tokenizers import Tokenizer

from .config import settings
from .db import Document, Passage
from .grounding import source_spans
from .search import SearchInput, search_documents, serialize

PROMPT_TOKEN_LIMIT = 2400
OUTPUT_TOKEN_LIMIT = 650
CONTEXT_MODES = ("legacy_fragments", "sentences", "neighbors_dedup", "coverage_budgeted")


@lru_cache(maxsize=1)
def counter():
    metadata = json.loads((settings.data_dir / "runtime/llm.json").read_text())
    tokenizer = Tokenizer.from_file(str(Path(metadata["path"]) / "tokenizer.json"))
    return lambda text: len(tokenizer.encode(text).ids)


def complete_sentences(text: str) -> list[str]:
    """Keep whole source sentences. Incomplete chunk tails are deliberately omitted."""
    text = text.strip()
    result = []
    start = 0
    for match in re.finditer(r"[.!?](?:[”\"']?)(?=\s|$)", text):
        part = text[start : match.end()].strip()
        if re.search(r"(?:U\.S\.|Inc\.|e\.g\.|i\.e\.)$", part):
            continue
        start = match.end()
        if part and (part[0].isupper() or part[0] in '“"(•') and 20 <= len(part) <= 1500:
            result.append(part)

    return result


STOP = set(
    "a an the how why what which does did could can would should for of to with in on at and or from by as its their company apple dell hp hpq aapl fiscal annual report filing using according explain describe summarize risk risks 2023 2024".split()
)


def words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def relevance(text, question):
    wanted = words(question)
    overlap = words(text) & wanted
    score = len(overlap)
    # Multi-part questions need each concrete topic, not generic "supplier" text.
    for term in (
        "digitization",
        "digital",
        "third-party",
        "covenant",
        "pricing",
        "personal",
        "confidential",
        "ransomware",
        "shortage",
        "printing",
    ):
        if term in question.lower() and term in text.lower():
            score += 3
    if re.search(
        r"\b(cause|limit|restrict|reduce|disrupt|result|harm|expos|affect|lead|penalt|demand)",
        text,
        re.I,
    ):
        score += 1
    return score


def coverage_terms(text):
    """Lightweight lexical normalization, not a semantic entailment model."""
    result = set()
    for term in words(text):
        if term.endswith("ies"):
            term = term[:-3] + "y"
        elif len(term) > 4 and term.endswith("s") and not term.endswith(("ss", "is")):
            term = term[:-1]
        if len(term) > 6 and term.endswith("ing"):
            term = term[:-3]
        elif len(term) > 7 and term.endswith("ion"):
            term = term[:-3]
        elif len(term) > 5 and term.endswith("e"):
            term = term[:-1]
        result.add(term)
    return result


def assemble_context(session, args, system, mode="coverage_budgeted", count=None):
    if mode not in CONTEXT_MODES:
        raise ValueError("Unknown server context strategy")
    count = count or counter()
    hits = search_documents(
        session,
        SearchInput(
            **{k: v for k, v in args.model_dump().items() if k not in {"explain", "response_mode"}}
        ),
        profile="legacy" if mode == "legacy_fragments" else "focused",
    )
    sources = {p["id"]: p for p in hits}
    candidates = list(hits[:3] if mode == "legacy_fragments" else hits)
    if mode in {"neighbors_dedup", "coverage_budgeted"}:
        for p in hits[:5]:
            if p["start"] < 0:
                continue
            for before in (True, False):
                query = (
                    select(Passage, Document)
                    .join(Document)
                    .where(
                        Document.id == p["document_id"],
                        Document.company == args.company,
                        Document.filed <= args.as_of,
                        Passage.start >= 0,
                    )
                )
                query = (
                    query.where(Passage.start < p["start"]).order_by(Passage.start.desc())
                    if before
                    else query.where(Passage.start > p["start"]).order_by(Passage.start)
                )
                pair = session.execute(query.limit(1)).first()
                if pair:
                    item = serialize(*pair)
                    if item["id"] not in sources:
                        sources[item["id"]] = item
                        candidates.append(item)
    pool = []
    for p in candidates:
        group = [p]
        if mode in {"neighbors_dedup", "coverage_budgeted"} and p["start"] >= 0:
            same = sorted(
                [x for x in candidates if x["document_id"] == p["document_id"] and x["start"] >= 0],
                key=lambda x: x["start"],
            )
            idx = next(i for i, x in enumerate(same) if x["id"] == p["id"])
            group = same[max(0, idx - 1) : idx + 2]
            # Do not bridge missing words, documents, periods or arbitrary gaps.
            if any(y["start"] - x["end"] != 1 for x, y in zip(group, group[1:], strict=False)):
                group = [p]
        joined = " ".join(x["text"] for x in group)
        chunks = (
            list(source_spans(p["text"]).values())
            if mode == "legacy_fragments"
            else complete_sentences(joined)
        )
        for n, sentence in enumerate(chunks):
            offset = joined.find(sentence)
            if offset < 0:
                continue
            sentence_start = group[0]["start"] + offset
            fragments = []
            if p["start"] < 0 or mode == "legacy_fragments":
                fragments = [{"citation": p["id"], "quote": sentence}]
            else:
                for part in group:
                    left = max(sentence_start, part["start"])
                    right = min(sentence_start + len(sentence), part["end"])
                    if right > left:
                        fragments.append(
                            {
                                "citation": part["id"],
                                "quote": part["text"][left - part["start"] : right - part["start"]],
                                "start": left,
                                "end": right,
                            }
                        )
            if not fragments:
                continue
            pool.append(
                {
                    "id": f"{p['id']}:s{n}",
                    "passage_id": p["id"],
                    "passage_ids": [f["citation"] for f in fragments],
                    "fragments": fragments,
                    "text": sentence,
                    "company": p["company"],
                    "fiscal_year": p["fiscal_year"],
                    "score": relevance(sentence, args.question),
                    "neighbor": p["id"] not in {h["id"] for h in hits},
                    "document_id": p["document_id"],
                    "source_start": sentence_start,
                }
            )
    if mode != "legacy_fragments":
        pool.sort(key=lambda s: (-s["score"], s["id"]))
    selected, seen, per_source = [], [], {}
    omitted = []
    base = {
        "company": args.company,
        "analysis_date": str(args.as_of),
        "sentences": [],
        "question": args.question,
    }
    covered = set()
    wanted = coverage_terms(args.question)
    weights = {
        w: math.log(1 + len(pool) / (1 + sum(w in coverage_terms(p["text"]) for p in pool)))
        for w in wanted
    }
    remaining = list(pool)
    while remaining:
        if mode == "coverage_budgeted":
            # Rare query terms anchor the topic; nearby source sentences retain
            # conditions/consequences that need not repeat the topic noun.
            def priority(sentence):
                matches = coverage_terms(sentence["text"]) & wanted
                anchors = sum(weights[w] for w in matches)
                novelty = sum(weights[w] for w in matches - covered)
                nearby = any(
                    s.get("document_id") == sentence["document_id"]
                    and abs(s["source_start"] - sentence["source_start"]) < 1500
                    for s in selected
                )
                return (-(anchors + 0.5 * novelty + (3 if nearby else 0)), sentence["id"])

            remaining.sort(key=priority)
        item = remaining.pop(0)
        bag = words(item["text"])
        if mode in {"neighbors_dedup", "coverage_budgeted"} and any(
            len(bag & prior) / max(1, len(bag | prior)) > 0.8 for prior in seen
        ):
            omitted.append({"id": item["id"], "reason": "near_duplicate"})
            continue
        source_limit = 6 if mode == "coverage_budgeted" else 2
        if mode != "legacy_fragments" and per_source.get(item["passage_id"], 0) >= source_limit:
            omitted.append({"id": item["id"], "reason": "source_diversity_limit"})
            continue
        public = {k: v for k, v in item.items() if k not in {"score", "neighbor"}}
        public["id"] = f"E{len(selected) + 1}"
        proposed = {**base, "sentences": selected + [public]}
        tokens = (
            count(system + render_context(args, proposed["sentences"])) + 100
        )  # Reserve chat-template overhead.
        if tokens > PROMPT_TOKEN_LIMIT:
            omitted.append({"id": item["id"], "reason": "token_budget"})
            continue
        public["source_sentence_id"] = item["id"]
        public["id"] = f"E{len(selected) + 1}"
        selected.append(public)
        seen.append(bag)
        covered.update(coverage_terms(item["text"]) & wanted)
        per_source[item["passage_id"]] = per_source.get(item["passage_id"], 0) + 1
        if len(selected) >= (
            18 if mode == "legacy_fragments" else 8 if mode == "coverage_budgeted" else 4
        ):
            break
    context = {**base, "sentences": selected}
    ids = {i for s in selected for i in s.get("passage_ids", [s["passage_id"]])}
    evidence = [p for p in sources.values() if p["id"] in ids]
    audit = {
        "strategy": mode,
        "search_ids": [p["id"] for p in hits],
        "generation_passage_ids": sorted(ids),
        "sentences": selected,
        "omitted": omitted,
        "estimated_prompt_tokens_including_reserve": count(system + render_context(args, selected))
        + 100,
        "prompt_token_limit": PROMPT_TOKEN_LIMIT,
        "output_token_limit": OUTPUT_TOKEN_LIMIT,
        "query_terms_covered": sorted(covered),
        "query_terms_not_covered": sorted(wanted - covered),
        "coverage_note": "Lexical term coverage only; not semantic completeness or support.",
        "context_sha256": hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest(),
        "support_status": "Source identity and sentence presence only; semantic support requires review.",
    }
    return context, evidence, audit


def render_context(args, selected):
    sources = "\n\n".join(
        f"[{item['id']}] {item['company']} FY{item['fiscal_year']}\n{item['text']}"
        for item in selected
    )
    return f"UNTRUSTED SOURCES:\n{sources}\n\nQUESTION: {args.question}"
