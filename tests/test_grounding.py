"""Adversarial contracts use test doubles, never count as model-quality evaluation."""

import copy
import json
from datetime import date

import pytest

from researchdesk.db import Document, Fact, Passage
from researchdesk.finance import financial_plan, historical
from researchdesk.grounding import validate_prose_provenance
from researchdesk.legacy_contracts import validate_financial
from researchdesk.research import AskInput, research
from researchdesk.search import specificity


class ContractCopyTestDouble:
    def __init__(self, mutate=None):
        self.mutate = mutate

    def generate(self, messages, **kwargs):
        context = json.loads(messages[-1]["content"].split("\n", 1)[1])
        assertions = copy.deepcopy(context["verified_measures"])
        if self.mutate:
            self.mutate(assertions)
        return json.dumps({"abstain": False, "assertions": assertions}), {
            "provider": "explicit-contract-test-double"
        }


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "Compare operating margin in 2023 versus 2024.",
        "Did operating margin decrease between 2023 and 2024?",
        "Show the operating margin change from 2023 to 2024 in percentage points.",
        "What is the 2024 operating profit margin versus 2023?",
    ],
)
def test_margin_variants_correct_direction_and_all_four_inputs(populated, question):
    r = research(populated, AskInput(question=question, method="lexical"), ContractCopyTestDouble())
    assert r["status"] == "answered"
    delta = r["verified_financials"]["measures"][-1]
    assert delta["direction"] == "increased" and delta["value"] == pytest.approx(2)
    assert delta["unit"] == "percentage points" and len(delta["citations"]) == 4
    assert "decreased" not in json.dumps(r["answer"])


@pytest.mark.integration
@pytest.mark.parametrize(
    "key,bad",
    [
        ("value", 999999),
        ("unit", "USD billion"),
        ("direction", "decreased"),
        ("company", "DELL"),
        ("scope", "printing segment"),
        ("periods", ["2024-01-01/2024-12-31"]),
        ("definition", "net-capex FCF"),
        ("citations", ["AAPL-2024-cfo"]),
    ],
)
def test_model_copy_has_no_authority_over_financial_result(populated, key, bad):
    def corrupt(assertions):
        assertions[0][key] = bad

    r = research(
        populated,
        AskInput(question="2024 CFO minus capex", method="lexical"),
        ContractCopyTestDouble(corrupt),
    )
    assert r["status"] == "answered"
    assert r["answer"]["claims"] and not r["answer"]["abstain"]
    assert r["verified_financials"]["measures"][0]["value"] == 25
    assert len(r["verified_financials"]["measures"][0]["citations"]) == 2


def test_value_tolerance_is_rounding_not_relative_error():
    m = {
        "id": "x",
        "company": "AAPL",
        "periods": ["a/b"],
        "scope": "consolidated",
        "unit": "percent",
        "definition": "x/y",
        "direction": "increased",
        "citations": ["x", "y"],
        "value": 2.021994,
        "label": "growth",
    }
    proposal = {k: v for k, v in m.items() if k != "label"}
    proposal["value"] = 2.02
    validate_financial(json.dumps({"abstain": False, "assertions": [proposal]}), [m])
    for value in [-2.02, 0.0202, 2.04, "NaN", "Infinity"]:
        proposal["value"] = value
        with pytest.raises(ValueError):
            validate_financial(json.dumps({"abstain": False, "assertions": [proposal]}), [m])
    proposal["value"] = 2.02
    with pytest.raises(ValueError):
        validate_financial(json.dumps({"abstain": False, "assertions": [proposal, proposal]}), [m])


def add_observation(s, *, value=111e6, metric="revenue", year=2024, company="AAPL", **overrides):
    doc_id = f"synthetic-{company}-{year}"
    s.add(
        Document(
            id=doc_id,
            company=company,
            cik="synthetic",
            fiscal_year=year,
            filed=date(2024, 12, 15),
            accession="synthetic-later-accession",
            url="https://example.org/synthetic",
            sha256="a" * 64,
            retrieved="test",
            parser_version="synthetic",
        )
    )
    s.flush()
    pid = doc_id + "-proof"
    s.add(
        Passage(
            id=pid,
            document_id=doc_id,
            section="Explicit synthetic conflict",
            anchor="",
            start=-1,
            end=-1,
            text="Synthetic provenance regression fixture.",
            embedding=None,
        )
    )
    s.flush()
    values = dict(
        company=company,
        fiscal_year=year,
        metric=metric,
        concept="us-gaap:OriginalTestFact",
        value=value,
        unit="USD",
        currency="USD",
        start=date(year - 1, 10, 1),
        end=date(year, 9, 30),
        scope="consolidated",
        reporting_basis="as_reported",
        restates_accession=None,
    )
    values.update(overrides)
    s.add(Fact(id=pid, document_id=doc_id, evidence_id=pid, **values))
    s.commit()
    return pid


class NeverCalled:
    def generate(self, *args, **kwargs):
        pytest.fail("Unresolved sources must not call the model")


@pytest.mark.integration
@pytest.mark.parametrize(
    "variant",
    [
        {},
        {"start": date(2023, 9, 24), "value": 110e6},
        {"concept": "custom:AdjustedRevenue", "value": 110e6},
        {"reporting_basis": "restated", "restates_accession": "original-2024", "value": 110e6},
    ],
)
def test_conflicts_retain_both_proofs_and_do_not_prefer_later_filing(populated, variant):
    pid = add_observation(populated, **variant)
    r = research(populated, AskInput(question="2024 revenue", method="lexical"), NeverCalled())
    assert r["status"] == "source_conflict" and not r["answer"]["claims"]
    assert {p["id"] for p in r["evidence"]} == {pid, "AAPL-2024-revenue"}
    observations = r["verified_financials"]["conflicts"][0]["observations"]
    assert len(observations) == 2 and len({o["accession"] for o in observations}) == 2
    before = historical(populated, "AAPL", date(2024, 12, 14))[-1]
    assert before["facts"]["revenue"]["value"] == 110 and not before["conflicts"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "variant",
    [
        {"company": "DELL"},
        {"scope": "segment:printing"},
        {"unit": "EUR", "currency": "EUR"},
        {"year": 2023, "value": 100e6},
        {"value": 110e6},
    ],
)
def test_different_entities_scopes_units_periods_and_equal_duplicates_are_not_false_conflicts(
    populated, variant
):
    add_observation(populated, **variant)
    r = research(
        populated, AskInput(question="2024 revenue", method="lexical"), ContractCopyTestDouble()
    )
    assert r["status"] == "answered"
    assert r["verified_financials"]["measures"][0]["value"] == 110
    assert not r["verified_financials"]["conflicts"]


@pytest.mark.integration
def test_mismatched_ratio_input_dates_and_unverified_net_definition_are_withheld(populated):
    f = populated.get(Fact, "AAPL-2024-cfo")
    f.start = date(2023, 9, 24)
    populated.commit()
    r = research(
        populated, AskInput(question="2024 CFO less capex", method="lexical"), NeverCalled()
    )
    assert r["status"] == "abstained" and "different fiscal periods" in str(
        r["verified_financials"]["issues"]
    )
    plan = financial_plan(
        "What was 2024 company-reported free cash flow using net capex?",
        historical(populated, "AAPL", date(2024, 12, 31)),
        "AAPL",
    )
    assert plan["issues"] and "not verified" in plan["issues"][0]


def test_exact_quotes_are_required_but_not_claimed_to_prove_entailment():
    p = {"id": "risk", "text": "Supply shortages could disrupt manufacturing and sales."}
    a = {
        "claims": [
            {
                "text": "Supply shortages could disrupt manufacturing.",
                "citations": ["risk"],
                "evidence_spans": [
                    {"citation": "risk", "quote": "shortages could disrupt manufacturing"}
                ],
            }
        ],
        "limitations": [],
    }
    validate_prose_provenance(a, [p])
    a["claims"][0]["evidence_spans"][0]["quote"] = "Debt could restrict borrowing."
    with pytest.raises(ValueError, match="absent"):
        validate_prose_provenance(a, [p])
    a["claims"][0]["evidence_spans"] = []
    with pytest.raises(ValueError, match="Each citation"):
        validate_prose_provenance(a, [p])


@pytest.mark.parametrize(
    "text",
    ["Revenue decreased 2% in 2024.", "Operating income increased.", "The figure is $110 million."],
)
def test_prose_cannot_bypass_financial_contract(text):
    a = {
        "claims": [
            {
                "text": text,
                "citations": ["x"],
                "evidence_spans": [{"citation": "x", "quote": "A sufficiently long source quote."}],
            }
        ],
        "limitations": [],
    }
    with pytest.raises(ValueError):
        validate_prose_provenance(a, [{"id": "x", "text": "A sufficiently long source quote."}])


def test_specificity_prefers_direct_debt_and_supply_evidence_to_boilerplate():
    from researchdesk.search import retrieval_focus

    for question, direct, generic in [
        (
            "How can debt restrict financing?",
            "Outstanding debt requires interest service and could restrict our borrowing and financing options. "
            * 3,
            "Refer to risk factors for risks and uncertainties which could affect our business.",
        ),
        (
            "What supply-chain disruption risks exist?",
            "Single suppliers and limited components could cause manufacturing disruption and shortages. "
            * 3,
            "Portfolio liquidity concentration presents investment risk. " * 4,
        ),
    ]:
        focus = retrieval_focus(question)
        assert specificity(direct, focus) > specificity(generic, focus)


def test_json_normalization_never_fills_financial_fields_or_truncated_arrays():
    from researchdesk.grounding import json_object

    assert json.loads(json_object('{"abstain": false, "assertions": []')) == {
        "abstain": False,
        "assertions": [],
    }
    assert json.loads(json_object('```json\n{"abstain": true,"assertions":[]}\n```'))["abstain"]
    for broken in [
        '{"abstain":false,"assertions":[{"value":',
        '{"assertions":[{"value":2}',
        '{"assertions":[]} ATTACK',
    ]:
        with pytest.raises(ValueError):
            json_object(broken)


def test_prose_conflict_requires_two_real_quotes_and_no_conclusion():
    passages = [
        {"id": "a", "text": "Original scope disclosure differs."},
        {"id": "b", "text": "Another scope disclosure differs."},
    ]
    answer = {
        "abstain": True,
        "claims": [],
        "limitations": [],
        "conflicts": [
            {
                "reason": "ambiguous",
                "evidence": [
                    {"citation": "a", "quote": "Original scope disclosure"},
                    {"citation": "b", "quote": "Another scope disclosure"},
                ],
            }
        ],
    }
    validate_prose_provenance(answer, passages)
    answer["conflicts"][0]["evidence"][1]["citation"] = "a"
    with pytest.raises(ValueError, match="distinct"):
        validate_prose_provenance(answer, passages)


@pytest.mark.integration
def test_descending_period_request_is_not_silently_reversed(populated):
    plan = financial_plan(
        "Revenue change from 2024 to 2023",
        historical(populated, "AAPL", date(2024, 12, 31)),
        "AAPL",
    )
    assert plan["issues"] and "reverse" in str(plan["issues"]).lower()


def test_selected_source_spans_are_bound_to_their_passage():
    from researchdesk.grounding import source_spans
    from researchdesk.research import validate_answer

    text = "A supplier shortage can interrupt production. " * 10
    spans = source_spans(text)
    assert spans and all(q in text for q in spans.values())
    raw = {
        "abstain": False,
        "claims": [
            {
                "text": "Supplier shortages can disrupt production.",
                "evidence_spans": [{"citation": "risk", "span_id": "s0"}],
            }
        ],
    }
    answer = validate_answer(json.dumps(raw), {"risk"}, {"risk": spans})
    assert answer.claims[0].citations == ["risk"]
    assert answer.claims[0].evidence_spans[0].quote == spans["s0"]
    raw["claims"][0]["evidence_spans"][0]["span_id"] = "s999"
    with pytest.raises(ValueError, match="unknown"):
        validate_answer(json.dumps(raw), {"risk"}, {"risk": spans})


@pytest.mark.integration
def test_financial_model_is_not_called_to_authorize_results(populated):
    class WrongProposal(ContractCopyTestDouble):
        calls = 0

        def generate(self, messages, **kwargs):
            self.calls += 1
            return super().generate(messages, **kwargs)

    simulated = WrongProposal(lambda a: a[0].update(value=999))
    r = research(populated, AskInput(question="2024 revenue"), simulated)
    assert r["status"] == "answered" and simulated.calls == 0


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "Subtract capex from CFO for 2024.",
        "2024 operating cash flow less capital spending",
        "CFO after gross capex in 2024",
    ],
)
def test_cash_proxy_operation_variants_require_both_inputs(populated, question):
    r = research(populated, AskInput(question=question), ContractCopyTestDouble())
    assert r["status"] == "answered"
    assert r["verified_financials"]["measures"][0]["definition"] == "cfo-gross_PPE_capex"
    assert r["verified_financials"]["measures"][0]["value"] == 25


def test_selected_company_is_not_silently_used_for_cross_entity_comparison():
    from researchdesk.scope import capability_gap

    for q in ["Compare Apple and Dell operating income in 2024.", "HP versus Apple revenue."]:
        assert capability_gap(q, "AAPL")


@pytest.mark.parametrize(
    "question,years",
    [
        ("FY2024 revenue", {2024}),
        ("fy 2023 versus FY2024", {2023, 2024}),
        ("2023 to 2024", {2023, 2024}),
    ],
)
def test_fiscal_notation_is_consistent_at_all_boundaries(question, years):
    from researchdesk.scope import requested_years

    assert requested_years(question) == years


@pytest.mark.integration
def test_unavailable_fy_notation_cannot_silently_select_latest_period(populated):
    r = research(populated, AskInput(question="FY2025 revenue"), NeverCalled())
    assert r["status"] == "abstained"


@pytest.mark.integration
def test_compact_fy_notation_selects_only_requested_period(populated):
    r = research(populated, AskInput(question="FY2023 revenue"), ContractCopyTestDouble())
    assert r["status"] == "answered"
    assert [m["id"] for m in r["verified_financials"]["measures"]] == ["revenue:2023"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "2024 free cash flow using net capex rather than gross capex",
        "2024 adjusted CFO less gross capex",
        "2024 free cash flow and gross margin",
    ],
)
def test_gross_word_does_not_override_an_unsupported_adjusted_definition(populated, question):
    r = research(populated, AskInput(question=question), NeverCalled())
    assert r["status"] in {"abstained", "clarification_required"} and not r["answer"]["claims"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "Did fiscal 2023 and fiscal 2024 have equal week counts?",
        "Compare FY2023 and FY2024 fiscal calendar lengths in weeks.",
        "Was FY2024 shorter than FY2023 in weeks?",
    ],
)
def test_calendar_comparisons_cannot_bypass_financial_contract(populated, question):
    # Clearly synthetic annual dates: 53 weeks, then 52 weeks.
    for year, start, end in [
        (2023, date(2022, 9, 25), date(2023, 9, 30)),
        (2024, date(2023, 10, 1), date(2024, 9, 28)),
    ]:
        f = populated.get(Fact, f"AAPL-{year}-revenue")
        f.start, f.end = start, end
    populated.commit()
    r = research(populated, AskInput(question=question), ContractCopyTestDouble())
    assert r["status"] == "answered"
    measures = r["verified_financials"]["measures"]
    assert [m["value"] for m in measures] == [53, 52, -1]
    assert measures[-1]["direction"] == "decreased" and measures[-1]["unit"] == "weeks"
    assert len(measures[-1]["citations"]) == 2


@pytest.mark.integration
def test_calendar_ignores_model_proposal_and_retains_verified_direction(populated):
    for year, start, end in [
        (2023, date(2022, 9, 25), date(2023, 9, 30)),
        (2024, date(2023, 10, 1), date(2024, 9, 28)),
    ]:
        f = populated.get(Fact, f"AAPL-{year}-revenue")
        f.start, f.end = start, end
    populated.commit()
    r = research(
        populated,
        AskInput(question="Compare fiscal 2023 and fiscal 2024 week counts"),
        ContractCopyTestDouble(lambda a: a[-1].update(direction="unchanged")),
    )
    assert (
        r["status"] == "answered"
        and r["verified_financials"]["measures"][-1]["direction"] == "decreased"
    )


@pytest.mark.integration
def test_non_week_calendar_does_not_assume_fifty_two_weeks(populated):
    r = research(populated, AskInput(question="How many weeks in fiscal 2024?"), NeverCalled())
    assert r["status"] == "abstained" and "whole-week" in str(r["verified_financials"]["issues"])


@pytest.mark.integration
@pytest.mark.parametrize(
    "question,measure",
    [
        ("Compare operating margins in 2023 and 2024", "operating_margin_change:2023:2024"),
        ("What were capital expenditures in FY2024?", "capex:2024"),
        ("Show operating profits in FY2024", "operating_income:2024"),
        ("Give cash flows from operations for FY2024", "cfo:2024"),
    ],
)
def test_plural_financial_labels_reach_the_same_verified_contract(populated, question, measure):
    r = research(populated, AskInput(question=question), ContractCopyTestDouble())
    assert r["status"] == "answered"
    assert measure in {m["id"] for m in r["verified_financials"]["measures"]}
