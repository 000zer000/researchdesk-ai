"""Explicit synthetic disclosures; no test double is presented as real inference."""

from datetime import date

import pytest

from researchdesk.context import PROMPT_TOKEN_LIMIT, assemble_context
from researchdesk.db import Document, Passage
from researchdesk.explanations import extract_source_sentences
from researchdesk.research import AskInput, research


def add_disclosures(session):
    session.add(
        Document(
            id="SYNTHETIC-COVERAGE",
            company="AAPL",
            cik="test",
            fiscal_year=2024,
            filed=date(2024, 11, 1),
            accession="synthetic-original",
            url="https://example.org/test",
            sha256="0" * 64,
            retrieved="test",
            parser_version="synthetic",
        )
    )
    session.flush()
    sentences = [
        "Supplier concentration can interrupt product assembly.",
        "Component shortages may delay shipments to customers.",
        "Privacy regulations can increase compliance costs.",
        "Cybersecurity breaches can expose confidential information.",
        "Acquisition integration may divert management resources.",
        "Inventory obsolescence may require product write-downs.",
        "Trade restrictions may prevent international shipments.",
        "Licensing agreements may restrict distribution of software.",
    ]
    for i, sentence in enumerate(sentences):
        session.add(
            Passage(
                id=f"test-coverage-{i}",
                document_id="SYNTHETIC-COVERAGE",
                section="Synthetic risk",
                anchor="",
                start=i * 1000,
                end=i * 1000 + len(sentence),
                text=sentence,
            )
        )
    session.commit()
    return sentences


@pytest.mark.integration
def test_budgeted_context_covers_more_than_four_distinct_topics(pg_session):
    sentences = add_disclosures(pg_session)
    args = AskInput(
        question="Explain supplier concentration, component shortages, privacy regulations, "
        "cybersecurity breaches, acquisition integration, inventory obsolescence, "
        "trade restrictions and licensing agreements in 2024.",
        method="lexical",
        k=8,
    )
    current, _, audit = assemble_context(
        pg_session, args, "Test", count=lambda text: len(text) // 3
    )
    legacy, _, _ = assemble_context(
        pg_session, args, "Test", mode="neighbors_dedup", count=lambda text: len(text) // 3
    )
    assert len(current["sentences"]) == len(sentences) == 8
    assert len(legacy["sentences"]) == 4
    assert audit["estimated_prompt_tokens_including_reserve"] <= PROMPT_TOKEN_LIMIT
    assert all(s["text"] in sentences for s in current["sentences"])


@pytest.mark.integration
def test_extract_mode_never_calls_model_and_keeps_exact_sentences(pg_session):
    sentences = add_disclosures(pg_session)

    class ForbiddenModel:
        def generate(self, *args, **kwargs):
            pytest.fail("Extractive mode must not invoke inference")

    result = research(
        pg_session,
        AskInput(
            question="Describe supplier concentration and privacy regulations",
            method="lexical",
            response_mode="extractive",
            k=8,
        ),
        llm=ForbiddenModel(),
        token_count=lambda text: len(text) // 3,
    )
    assert result["status"] == "answered" and result["origin"] == "source_extract"
    assert result["model_calls"] == []
    assert all(c["text"] in sentences for c in result["answer"]["claims"])
    assert all(c["origin"] == "source_extract" for c in result["answer"]["claims"])
    assert "completeness" in result["citation_support"]


def test_extract_rejects_changed_quote_and_changed_sentence():
    fragment = {"citation": "p1", "quote": "Licensing may restrict software distribution."}
    context = {"sentences": [{"id": "E1", "text": fragment["quote"], "fragments": [fragment]}]}
    evidence = [{"id": "p1", "text": fragment["quote"]}]
    assert extract_source_sentences(context, evidence)["claims"][0]["text"] == fragment["quote"]
    context["sentences"][0]["text"] = "Licensing never restricts software distribution."
    with pytest.raises(ValueError, match="differs"):
        extract_source_sentences(context, evidence)
    fragment["quote"] = "Invented quote."
    with pytest.raises(ValueError, match="absent"):
        extract_source_sentences(context, evidence)


@pytest.mark.integration
def test_extract_mode_cannot_change_financial_results(populated):
    result = research(
        populated,
        AskInput(
            question="How did operating margin change between 2023 and 2024?",
            response_mode="extractive",
            method="lexical",
        ),
    )
    assert result["origin"] == "deterministic finance engine"
    assert result["status"] == "answered"
    assert all(c["origin"] == "deterministic_calculation" for c in result["answer"]["claims"])


@pytest.mark.integration
def test_budget_stays_bounded_with_more_sentence_slots(pg_session):
    add_disclosures(pg_session)
    args = AskInput(
        question="Describe privacy regulations and supplier concentration in 2024",
        method="lexical",
        k=8,
    )
    context, _, audit = assemble_context(pg_session, args, "Test", count=lambda text: len(text) * 4)
    assert audit["estimated_prompt_tokens_including_reserve"] <= PROMPT_TOKEN_LIMIT
    assert len(context["sentences"]) < 8
    assert any(x["reason"] == "token_budget" for x in audit["omitted"])
