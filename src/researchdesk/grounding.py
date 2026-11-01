"""Mechanical source identity/scope checks; never semantic entailment."""

import json
import re
import unicodedata


def json_object(raw: str) -> str:
    """Extract JSON; permit one missing final root brace, never invent values.

    A small model sometimes emits a complete assertions array and EOS before the
    outer brace. This narrowly bounded syntax normalization must parse in full;
    truncated strings, missing array brackets or additional tokens still fail.
    """
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate).removesuffix("```").strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        if not candidate.startswith("{") or not candidate.endswith("]"):
            raise ValueError("The local model did not return complete structured JSON") from None
        try:
            value = json.loads(candidate + "}")
        except json.JSONDecodeError:
            raise ValueError("The local model did not return complete structured JSON") from None
    if not isinstance(value, dict):
        raise ValueError("The local model must return a JSON object")
    return json.dumps(value)


def render_financial(measures: list[dict]) -> dict:
    """Render only approved canonical values, never the model's numerical text."""
    return {
        "abstain": False,
        "claims": [
            {
                "text": f"{m['company']} · {', '.join(m['periods'])} · {m['scope']}: {m['label']}: {m['value']:,.2f} {m['unit']} ({m['direction']}). Definition: {m['definition']}.",
                "citations": m["citations"],
            }
            for m in measures
        ],
        "limitations": [
            "Server-calculated values, periods, units, definitions and complete input citations. No model authorization is required. Actual fiscal dates can have different week counts."
        ],
    }


def normalize_span(text: str) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", text).casefold().replace("’", "'").replace("‘", "'").split()
    )


def validate_prose_provenance(
    answer: dict, passages: list[dict], company: str | None = None, minimum_quote_length: int = 12
) -> None:
    texts = {p["id"]: normalize_span(p["text"]) for p in passages}
    from .scope import ALIASES

    for conflict in answer.get("conflicts", []):
        proofs = conflict["evidence"]
        if len({s["citation"] for s in proofs}) < 2:
            raise ValueError("A conflict requires two distinct source proofs")
        for span in proofs:
            if normalize_span(span["quote"]) not in texts.get(span["citation"], ""):
                raise ValueError("Conflict evidence quote is absent from source")
        if not answer["abstain"] or answer["claims"]:
            raise ValueError("Unresolved conflict requires abstention without conclusions")
    for claim in answer["claims"]:
        if company:
            for other, aliases in ALIASES.items():
                if other != company and any(
                    re.search(r"\b" + re.escape(alias) + r"\b", claim["text"], re.I)
                    for alias in aliases
                ):
                    raise ValueError("Claim names a different covered company")
            fiscal_mentions = set(
                re.findall(r"(?:FY\s*|fiscal(?: year)?\s*)(20\d{2})", claim["text"], re.I)
            )
            cited_years = {str(p["fiscal_year"]) for p in passages if p["id"] in claim["citations"]}
            if fiscal_mentions - cited_years:
                raise ValueError("Claim fiscal period is not covered by its citations")
        spans = claim.get("evidence_spans", [])
        if {s["citation"] for s in spans} != set(claim["citations"]):
            raise ValueError("Each citation requires an exact supporting evidence span")
        for span in spans:
            quote = normalize_span(span["quote"])
            if len(quote) < minimum_quote_length or quote not in texts.get(span["citation"], ""):
                raise ValueError("A supporting quote is absent from its cited source")
    # Prose is not an alternate route around the numerical contract. Calendar
    # week counts and fiscal-year labels are the only numeric prose exceptions.
    for text in [c["text"] for c in answer["claims"]] + answer["limitations"]:
        scrubbed = re.sub(r"\b(?:FY\s*)?20\d{2}\b|\b(?:52|53)[ -]weeks?\b", "", text, flags=re.I)
        if re.search(
            r"\d|[$€£%]|\b(millions?|billions?|trillions?|percent|percentage|usd|dollars?)\b",
            scrubbed,
            re.I,
        ):
            raise ValueError(
                "Numerical prose requires a verified financial contract or calendar week evidence"
            )
        if re.search(
            r"\b(revenue|sales|margin|cash flow|operating income)\b", text, re.I
        ) and re.search(
            r"\b(increased|decreased|rose|fell|grew|declined|higher|lower)\b", text, re.I
        ):
            raise ValueError("Financial direction in prose requires a verified measure contract")
        for weeks in re.findall(r"\b(52|53)[ -]weeks?\b", text, re.I):
            cited = " ".join(texts[c] for claim in answer["claims"] for c in claim["citations"])
            if not re.search(rf"\b{weeks}[ -]weeks?\b", cited):
                raise ValueError("Calendar week claim is not present in the cited evidence")


def source_spans(text: str) -> dict[str, str]:
    """Short, lossless word-boundary slices identified before generation.

    The model selects IDs; the server retrieves quotes from these exact slices.
    Selecting a real slice still does not establish that it entails the prose.
    """
    result = {}
    start = 0
    while start < len(text):
        end = min(start + 220, len(text))
        if end < len(text):
            split = text.rfind(" ", start + 12, end)
            if split > start:
                end = split
        quote = text[start:end].strip()
        if len(quote) >= 12:
            result[f"s{len(result)}"] = quote
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    return result
