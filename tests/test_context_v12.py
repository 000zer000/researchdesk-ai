import json
from datetime import date

import pytest

from researchdesk.context import PROMPT_TOKEN_LIMIT, assemble_context, complete_sentences
from researchdesk.explanations import validate_generated
from researchdesk.research import AskInput


def test_sentence_slices_preserve_complete_text_and_drop_incomplete_tail():
    text = "Supplier shortages can interrupt production. Price increases can raise costs. incomplete tail"
    sentences = complete_sentences(text)
    assert sentences == [
        "Supplier shortages can interrupt production.",
        "Price increases can raise costs.",
    ]
    assert all(s in text for s in sentences)


@pytest.mark.integration
def test_context_budget_dedup_and_publication_boundary(populated):
    args = AskInput(
        question="Supply chain manufacturing risks in 2023",
        method="lexical",
        as_of=date(2024, 10, 31),
        k=8,
    )
    context, evidence, audit = assemble_context(
        populated, args, "Explicit test system", count=lambda text: len(text) // 3
    )
    assert audit["estimated_prompt_tokens_including_reserve"] <= PROMPT_TOKEN_LIMIT
    assert context["sentences"] and all(p["fiscal_year"] == 2023 for p in evidence)
    assert len({s["text"] for s in context["sentences"]}) == len(context["sentences"])
    assert [s["id"] for s in context["sentences"]] == [
        f"E{i + 1}" for i in range(len(context["sentences"]))
    ]
    assert audit["generation_passage_ids"] == sorted(
        {s["passage_id"] for s in context["sentences"]}
    )


def test_source_identity_and_classification_are_checked_separately_from_support():
    context = {
        "sentences": [
            {"id": "E1", "passage_id": "p1", "text": "Supplier shortages can interrupt production."}
        ]
    }
    sources = [
        {
            "id": "p1",
            "text": "Supplier shortages can interrupt production.",
            "company": "AAPL",
            "fiscal_year": 2024,
        }
    ]
    raw = {
        "abstain": False,
        "claims": [
            {
                "kind": "disclosed_fact",
                "text": "Supplier shortages can interrupt production.",
                "evidence_ids": ["E1"],
            }
        ],
        "limitations": [],
    }
    answer = validate_generated(json.dumps(raw), context, sources, "AAPL")
    assert answer["claims"][0]["origin"] == "generated_text"
    assert answer["claims"][0]["evidence_spans"][0]["quote"] == sources[0]["text"]
    raw["claims"][0]["evidence_ids"] = ["E9"]
    with pytest.raises(ValueError, match="Unknown"):
        validate_generated(json.dumps(raw), context, sources, "AAPL")
    raw["claims"][0]["evidence_ids"] = ["E1"]
    raw["claims"][0]["kind"] = "verified_truth"
    with pytest.raises(ValueError):
        validate_generated(json.dumps(raw), context, sources, "AAPL")


@pytest.mark.integration
def test_neighbor_sentence_keeps_both_exact_source_fragments(pg_session):
    from researchdesk.db import Document, Passage

    first = "Demand for printing products and solutions has declined"
    second = " as a result of digitization and hybrid work."
    # The normalized corpus separates chunks by one whitespace character.
    left = first
    right = second.lstrip()
    pg_session.add(
        Document(
            id="SYNTHETIC-JOIN",
            company="HPQ",
            cik="test",
            fiscal_year=2024,
            filed=date(2024, 12, 13),
            accession="test-original",
            url="https://example.org/synthetic",
            sha256="0" * 64,
            retrieved="test",
            parser_version="test",
        )
    )
    pg_session.flush()
    for pid, start, text in [("left", 0, left), ("right", len(left) + 1, right)]:
        pg_session.add(
            Passage(
                id=pid,
                document_id="SYNTHETIC-JOIN",
                section="Synthetic context",
                anchor="",
                start=start,
                end=start + len(text),
                text=text,
            )
        )
    pg_session.commit()
    args = AskInput(
        company="HPQ",
        question="Explain printing digitization demand in 2024",
        method="lexical",
        k=8,
    )
    context, evidence, _ = assemble_context(
        pg_session, args, "Test system", count=lambda text: len(text) // 3
    )
    sentence = next(s for s in context["sentences"] if "digitization" in s["text"])
    assert sentence["text"] == left + " " + right
    assert {f["citation"] for f in sentence["fragments"]} == {"left", "right"}
    raw = {
        "abstain": False,
        "claims": [
            {
                "kind": "disclosed_fact",
                "text": "Digitization and hybrid work reduce demand for printing products.",
                "evidence_ids": [sentence["id"]],
            }
        ],
    }
    answer = validate_generated(json.dumps(raw), context, evidence, "HPQ")
    assert answer["claims"][0]["citations"] == ["left", "right"]
