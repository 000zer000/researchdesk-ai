import re
from datetime import date
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import Document, Passage
from .embeddings import embedder


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


def search_documents(session: Session, args: SearchInput) -> list[dict]:
    base = (
        select(Passage, Document)
        .join(Document)
        .where(Document.company == args.company, Document.filed <= args.as_of)
    )
    years = {int(y) for y in re.findall(r"\b20\d{2}\b", args.question)}
    if years:
        base = base.where(Document.fiscal_year.in_(years))
    stop = set(
        "a an the how did do does which what was were is are in on of for to and between these this its their show explain discuss describe summarize company apple inc dell technologies hp aapl hpq annual report reports filing filings disclose disclosed 2023 2024".split()
    )
    words = [w for w in re.findall(r"[a-zA-Z]+", args.question.lower()) if w not in stop]
    cleaned = " ".join(words) or args.question
    query = func.websearch_to_tsquery("english", " OR ".join(words) or args.question)
    vector = func.to_tsvector("english", Passage.text)
    lexical = session.execute(
        base.where(vector.op("@@")(query))
        .order_by(func.ts_rank_cd(vector, query).desc(), Passage.id)
        .limit(30)
    ).all()
    if args.method == "lexical":
        return [serialize(p, d, 1 / (i + 1)) for i, (p, d) in enumerate(lexical[: args.k])]
    # RRF is transparent and needs no learned reranker. Corpus is intentionally small.
    candidates = session.execute(base.where(Passage.embedding.is_not(None))).all()
    if not candidates:
        if session.execute(base.limit(1)).first() is None:
            return []
        raise RuntimeError("Semantic index unavailable; run ingestion with local embeddings")
    q = np.array(embedder().encode([cleaned])[0])
    vectors = np.array([p.embedding for p, _ in candidates])
    similarities = vectors @ q
    order = np.argsort(-similarities, kind="stable")[:30]
    semantic = [candidates[int(i)] for i in order]
    scores: dict[str, float] = {}
    lookup = {}
    for ranked in (lexical, semantic):
        for rank, (p, d) in enumerate(ranked, 1):
            scores[p.id] = scores.get(p.id, 0) + 1 / (60 + rank)
            lookup[p.id] = (p, d)
    ids = sorted(scores, key=lambda key: (-scores[key], key))[: args.k]
    return [serialize(*lookup[key], scores[key]) for key in ids]
