import math
import re
from datetime import date
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import Document, Passage
from .embeddings import embedder
from .scope import requested_years


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: Literal["AAPL", "DELL", "HPQ"] = "AAPL"
    as_of: date = date(2024, 12, 31)
    question: str = Field(min_length=3, max_length=1200)
    method: Literal["lexical", "hybrid"] = "hybrid"
    k: int = Field(default=5, ge=1, le=8)


def serialize(p: Passage, d: Document, score: float = 0) -> dict:
    return {
        "id": p.id,
        "document_id": d.id,
        "company": d.company,
        "fiscal_year": d.fiscal_year,
        "filed": str(d.filed),
        "section": p.section,
        "anchor": p.anchor,
        "start": p.start,
        "end": p.end,
        "offset_basis": "normalized text; " + d.parser_version
        if p.start >= 0
        else "structured XBRL evidence; no HTML offsets",
        "text": p.text,
        "url": d.url + ("#" + p.anchor if p.anchor else ""),
        "accession": d.accession,
        "sha256": d.sha256,
        "score": score,
    }


def search_documents(session: Session, args: SearchInput, profile: str = "focused") -> list[dict]:
    base = (
        select(Passage, Document)
        .join(Document)
        .where(Document.company == args.company, Document.filed <= args.as_of)
    )
    years = requested_years(args.question)
    if years:
        base = base.where(Document.fiscal_year.in_(years))
    stop = set(
        "a an the how did do does which what was were is are in on of for to and between these this its their show explain discuss describe summarize company apple inc dell technologies hp aapl hpq annual report reports filing filings disclose disclosed 2023 2024".split()
    )
    words = [w for w in re.findall(r"[a-zA-Z]+", args.question.lower()) if w not in stop]
    cleaned = " ".join(words) or args.question
    focus = retrieval_focus(args.question, profile)
    expanded = words + [w for group in focus for w in group]
    query = func.websearch_to_tsquery("english", " OR ".join(expanded) or args.question)
    vector = func.to_tsvector("english", Passage.text)
    lexical = session.execute(
        base.where(vector.op("@@")(query))
        .order_by(func.ts_rank_cd(vector, query).desc(), Passage.id)
        .limit(30)
    ).all()
    corpus = session.execute(base).all() if profile == "focused" else []
    idf_scores = {}
    anchors = []
    if corpus:
        # Rarer query terms recover split paragraphs that lack their topic noun
        # (for example a continuation containing digitization but not printing).
        terms = sorted(set(w for w in words if len(w) >= 4))
        frequencies = {
            w: sum(bool(re.search(r"\b" + re.escape(w), p.text, re.I)) for p, _ in corpus)
            for w in terms
        }
        weights = {w: math.log(1 + len(corpus) / (1 + df)) for w, df in frequencies.items() if df}
        idf_scores = {
            p.id: sum(
                weight
                for word, weight in weights.items()
                if re.search(r"\b" + re.escape(word), p.text, re.I)
            )
            for p, _ in corpus
        }
        anchors = sorted(corpus, key=lambda pair: (-idf_scores[pair[0].id], pair[0].id))[:20]
    if args.method == "lexical":
        lookup = {p.id: (p, d) for p, d in lexical + anchors}
        ranked = [(p, d, 1 / (60 + i + 1)) for i, (p, d) in enumerate(lookup.values())]
        return rerank(ranked, focus, args.k, idf_scores)
    candidates = (
        [(p, d) for p, d in corpus if p.embedding is not None]
        if corpus
        else session.execute(base.where(Passage.embedding.is_not(None))).all()
    )
    if not candidates:
        if session.execute(base.limit(1)).first() is None:
            return []
        raise RuntimeError("Semantic index unavailable; run ingestion with local embeddings")
    q = np.array(
        embedder().encode([cleaned + " " + " ".join(w for group in focus for w in group)])[0]
    )
    vectors = np.array([p.embedding for p, _ in candidates])
    similarities = vectors @ q
    order = np.argsort(-similarities, kind="stable")[:30]
    semantic = [candidates[int(i)] for i in order]
    scores: dict[str, float] = {}
    lookup = {}
    for ranked in (lexical, semantic, anchors):
        for rank, (p, d) in enumerate(ranked, 1):
            scores[p.id] = scores.get(p.id, 0) + 1 / (60 + rank)
            lookup[p.id] = (p, d)
    return rerank(
        [(p, d, scores[key]) for key, (p, d) in lookup.items()], focus, args.k, idf_scores
    )


# Query expansion and specificity are topic rules, never question IDs or company-
# specific answers. They target observed boilerplate and wrong-section retrieval.
FOCUSES = [
    (
        r"supply.chain|suppli|outsourc|component|manufactur",
        [
            ("supplier", "suppliers", "manufacturing", "component", "components", "outsourcing"),
            ("shortage", "disruption", "limited", "single", "accident", "concentration"),
        ],
    ),
    (
        r"debt|indebted|covenant|borrow",
        [
            ("debt", "indebtedness", "borrowing", "covenants"),
            ("restrict", "repay", "service", "interest", "financing", "adverse"),
        ],
    ),
    (
        r"privacy|cyber|personal information|ransomware",
        [
            ("privacy", "cybersecurity", "personal", "confidential", "ransomware", "unauthorized"),
            ("breach", "attack", "damage", "harm", "access", "sensitive"),
        ],
    ),
    (
        r"printing|digitization|print demand",
        [
            ("printing", "print", "printer", "printers"),
            ("demand", "digitization", "hybrid", "decline", "alternatives", "softness"),
        ],
    ),
    (r"calendar|weeks?|fiscal period", [("week", "weeks"), ("52", "53", "calendar", "fiscal")]),
]


def retrieval_focus(question: str, profile: str = "focused") -> list[tuple[str, ...]]:
    matching = [
        (pattern, groups) for pattern, groups in FOCUSES if re.search(pattern, question, re.I)
    ]
    if profile == "focused":
        # Explicit subject outranks incidental supplier vocabulary. Otherwise a
        # printing/privacy question is misrouted to general procurement risks.
        for index in (2, 3, 1):
            pattern, groups = FOCUSES[index]
            if re.search(pattern, question, re.I):
                matching = [(pattern, groups)]
                break
    return [tuple(group) for _, groups in matching for group in groups]


def specificity(text: str, groups: list[tuple[str, ...]]) -> float:
    if not groups:
        return 0
    lower = text.lower()
    hits = [sum(bool(re.search(r"\b" + re.escape(w), lower)) for w in group) for group in groups]
    # Requiring different topic components prevents generic "risk factors" text
    # and unrelated cash/portfolio concentration from outranking direct evidence.
    score = sum(min(n, 3) for n in hits) + (4 if all(hits) else 0)
    if len(text.split()) < 28:
        score -= 5
    if re.search(r"refer to.*risk factors|risks and uncertainties.*could", lower) and sum(hits) < 2:
        score -= 3
    return score


def rerank(candidates: list, focus: list, k: int, idf_scores=None) -> list[dict]:
    idf_scores = idf_scores or {}
    weight = 0.002 if idf_scores else 0.012

    def score(item):
        return (
            item[2]
            + weight * specificity(item[0].text, focus)
            + 0.006 * idf_scores.get(item[0].id, 0)
        )

    ordered = sorted(
        candidates,
        key=lambda item: (-score(item), item[0].id),
    )
    return [serialize(p, d, score((p, d, base_score))) for p, d, base_score in ordered[:k]]
