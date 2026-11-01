import logging
import re
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Document, Passage
from .finance import historical
from .grounding import (
    json_object,
    render_financial,
)
from .scope import capability_gap, requested_years
from .search import SearchInput, serialize


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citation: str
    quote: str = Field(default="", max_length=240)
    span_id: str | None = None


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1600)
    citations: list[str] = Field(default_factory=list, max_length=8)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list, max_length=8)


class SourceConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=600)
    evidence: list[EvidenceSpan] = Field(min_length=2, max_length=4)


class ModelAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    abstain: bool
    claims: list[Claim] = Field(max_length=6)
    limitations: list[str] = Field(default_factory=list, max_length=8)
    conflicts: list[SourceConflict] = Field(default_factory=list, max_length=3)


class AskInput(SearchInput):
    method: Literal["lexical", "hybrid"] = "hybrid"
    explain: bool = False


def validate_answer(raw: str, ids: set[str], spans: dict | None = None) -> ModelAnswer:
    # Legacy JSON-answer regression helper; the v1.2 route uses explanations.py.
    answer = ModelAnswer.model_validate_json(json_object(raw))
    all_spans = [s for c in answer.claims for s in c.evidence_spans] + [
        s for c in answer.conflicts for s in c.evidence
    ]
    for span in all_spans:
        if span.span_id is not None:
            quote = (spans or {}).get(span.citation, {}).get(span.span_id)
            if not quote or (span.quote and span.quote != quote):
                raise ValueError("The model selected an unknown or inconsistent source span")
            span.quote = quote
    for claim in answer.claims:
        if not claim.citations and claim.evidence_spans:
            claim.citations = sorted({s.citation for s in claim.evidence_spans})
        if any(c not in ids for c in claim.citations):
            raise ValueError("The local model cited evidence outside the retrieved set")
        if not answer.abstain and not claim.citations:
            raise ValueError("The local model returned an uncited claim")
    if not answer.abstain and not answer.claims:
        raise ValueError("An answer requires at least one cited claim")
    return answer


def research(
    session: Session, args: AskInput, llm=None, *, context_mode="neighbors_dedup", token_count=None
) -> dict:
    """Financial execution never depends on successful local text generation."""
    from .explanations import generate_explanation
    from .finance import execute_financial_request, interpret_financial_request

    started = time.monotonic()
    rows = historical(session, args.company, args.as_of)
    request, ambiguity = interpret_financial_request(args.question, args.company, rows)
    gap = capability_gap(args.question, args.company)
    if gap and not (ambiguity and gap.startswith("Supported questions concern")):
        return refusal("abstained", gap, started)
    if ambiguity:
        return refusal("clarification_required", ambiguity, started)
    years = requested_years(args.question)
    if years - {r["fiscal_year"] for r in rows}:
        return refusal(
            "abstained",
            "Requested fiscal year is unavailable at the selected publication date.",
            started,
        )
    if request is None:
        result = generate_explanation(session, args, llm, context_mode, token_count)
        return {
            **result,
            "trace": [
                {"tool": "search_documents", "status": "ok", "context_strategy": context_mode},
                {"tool": "generate_explanation", "status": result["status"]},
            ],
            "calculations": None,
        }
    plan = execute_financial_request(request, rows)
    ids = {o["evidence_id"] for o in plan["observations"] if o["evidence_id"]}
    pairs = session.execute(
        select(Passage, Document)
        .join(Document)
        .where(Passage.id.in_(ids), Document.company == args.company, Document.filed <= args.as_of)
        .order_by(Passage.id)
    ).all()
    evidence = [serialize(p, d) for p, d in pairs]
    available = {p["id"] for p in evidence}
    if not {c for m in plan["measures"] for c in m["citations"]}.issubset(available):
        plan["issues"].append("A verified input source is unavailable; conclusion withheld.")
    answer = (
        render_financial(plan["measures"])
        if not plan["issues"]
        else {"abstain": True, "claims": [], "limitations": plan["issues"]}
    )
    for claim in answer["claims"]:
        claim["origin"] = "deterministic_calculation"
    answer["limitations"] = plan["issues"] or [
        "Calculated by server code from the validated request and original consolidated sources. Fiscal calendars and metric definitions can limit comparability."
    ]
    result = {
        "status": "source_conflict"
        if plan["conflicts"]
        else "abstained"
        if plan["issues"]
        else "answered",
        "origin": "deterministic finance engine",
        "answer": answer,
        "financial_request": request.model_dump(),
        "verified_financials": plan,
        "evidence": evidence,
        "calculations": None,
        "trace": [
            {"tool": "validate_financial_request", "status": "ok", "request": request.model_dump()},
            {
                "tool": "calculate_metrics",
                "status": "withheld" if plan["issues"] else "ok",
                "measure_ids": [m["id"] for m in plan["measures"]],
            },
        ],
        "explanation": {"status": "not_requested", "origin": "generated_text"},
        "citation_support": "Structured input provenance checked; generated text requires separate semantic review.",
    }
    if args.explain and not plan["issues"]:
        try:
            note = generate_explanation(
                session, args, llm, context_mode, token_count, calculation=plan
            )
            if any(
                re.search(
                    r"\b(increas\w*|decreas\w*|higher|lower|rose|fell|grew|declin\w*|up|down)\b",
                    c["text"],
                    re.I,
                )
                for c in (note.get("answer") or {}).get("claims", [])
            ):
                note = {
                    **note,
                    "status": "invalid_model_answer",
                    "answer": None,
                    "limitations": [
                        "The optional explanation made a financial-direction assertion outside its permitted scope. Use the verified result and formula above."
                    ],
                }
            result["explanation"] = note
        except Exception as error:
            logging.getLogger("researchdesk").warning(
                "Optional explanation failed (%s)", type(error).__name__, exc_info=True
            )
            result["explanation"] = {
                "status": "unavailable",
                "origin": "generated_text",
                "reason": type(error).__name__,
                "limitations": [
                    "The optional AI explanation is unavailable. The verified calculation remains valid and visible."
                ],
            }
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def refusal(status, reason, started):
    return {
        "status": status,
        "origin": "deterministic request validation; no inference",
        "answer": {"abstain": True, "claims": [], "limitations": [reason]},
        "clarification": reason if status == "clarification_required" else None,
        "evidence": [],
        "trace": [{"tool": "validate_request", "status": status}],
        "calculations": None,
        "elapsed_seconds": time.monotonic() - started,
    }
