import pytest
from pydantic import ValidationError

from researchdesk.finance import FinancialRequest
from researchdesk.research import AskInput, research


class NeverModel:
    def generate(self, *args, **kwargs):
        pytest.fail("A verified financial calculation must not call the model")


@pytest.mark.integration
@pytest.mark.parametrize(
    "question,operation,metric,unit,expected",
    [
        ("2024 revenue", "level", "revenue", "USD million", 110),
        ("2024 revenue in USD billion", "level", "revenue", "USD billion", 0.110),
        ("Raw USD revenue for 2024", "level", "revenue", "USD", 110000000),
        ("Percentage revenue growth from 2023 to 2024", "growth", "revenue", "percent", 10),
        (
            "Compare operating margins in 2023 and 2024",
            "compare",
            "operating_margin",
            "percentage points",
            2,
        ),
        (
            "Subtract capex from CFO in 2024 without switching to net capex",
            "level",
            "cfo_less_capex",
            "USD million",
            25,
        ),
    ],
)
def test_structured_request_and_authorized_execution(
    populated, question, operation, metric, unit, expected
):
    r = research(populated, AskInput(question=question), NeverModel())
    assert r["status"] == "answered", r
    request = r["financial_request"]
    assert (
        request["operation"] == operation
        and request["metrics"] == [metric]
        and request["unit"] == unit
    )
    measure = r["verified_financials"]["measures"][-1]
    assert measure["value"] == pytest.approx(expected)
    assert (
        measure["inputs"]
        and measure["formula"]
        and measure["origin"] == "deterministic_calculation"
    )
    assert r["explanation"]["status"] == "not_requested"


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "What was free cash flow in 2024?",
        "Give 2024 margin",
        "What was cash in 2024?",
        "Show revenue",
        "Compare 2024 revenue",
        "2024 revenue in EUR",
        "2024 cash for the Europe segment",
        "Divide 2024 capex by CFO",
    ],
)
def test_real_ambiguity_does_not_silently_become_a_calculation(populated, question):
    r = research(populated, AskInput(question=question), NeverModel())
    assert r["status"] == "clarification_required", r
    assert not r["answer"]["claims"] and r["clarification"]


@pytest.mark.integration
def test_optional_ai_failure_never_masks_result(populated, monkeypatch):
    import researchdesk.explanations as explanation

    def fail(*a, **k):
        raise TimeoutError("Explicit test backend timeout")

    monkeypatch.setattr(explanation, "generate_explanation", fail)
    r = research(populated, AskInput(question="2024 revenue", explain=True))
    assert r["status"] == "answered" and r["explanation"]["status"] == "unavailable"
    assert r["verified_financials"]["measures"][0]["value"] == 110
    assert r["answer"]["claims"][0]["origin"] == "deterministic_calculation"


def test_schema_forbids_arbitrary_sql_code_operations_and_incompatible_units():
    base = dict(
        company="AAPL",
        metrics=["revenue"],
        years=[2024],
        operation="level",
        unit="USD million",
        definition="as_reported",
    )
    for change in [
        dict(sql="DROP TABLE facts"),
        dict(operation="execute"),
        dict(scope="Europe"),
        dict(unit="EUR"),
        dict(definition="net-income"),
        dict(years=[2024, 2023]),
    ]:
        with pytest.raises(ValidationError):
            FinancialRequest(**{**base, **change})


@pytest.mark.integration
def test_financial_api_not_blocked_by_inference_gate(populated):
    from fastapi.testclient import TestClient

    from researchdesk.api import app
    from researchdesk.db import session_dependency
    from researchdesk.explanations import GATE

    app.dependency_overrides[session_dependency] = lambda: populated
    try:
        with GATE, TestClient(app) as client:
            r = client.post("/api/research", json={"question": "2024 revenue"})
        assert r.status_code == 200 and r.json()["status"] == "answered"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_proxy_change_uses_all_four_verified_inputs(populated):
    r = research(
        populated, AskInput(question="Change in CFO less capex from 2023 to 2024"), NeverModel()
    )
    assert r["status"] == "answered"
    last = r["verified_financials"]["measures"][-1]
    assert last["value"] == 0 and last["direction"] == "unchanged" and len(last["citations"]) == 4
    assert r["verified_financials"]["result_ids"] == [last["id"]]


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "Sum revenue and CFO for 2024",
        "Revenue as a percentage of CFO in 2024",
        "Subtract an unknown outflow from CFO in 2024",
    ],
)
def test_unrecognized_arithmetic_is_not_silently_replaced_by_levels(populated, question):
    result = research(populated, AskInput(question=question), NeverModel())
    assert result["status"] == "clarification_required"


@pytest.mark.integration
@pytest.mark.parametrize(
    "question", ["Convert USD revenue for 2024 into EUR", "Revenue for 2024 in USD and EUR"]
)
def test_currency_conversion_or_mixed_targets_are_not_assumed(populated, question):
    assert (
        research(populated, AskInput(question=question), NeverModel())["status"]
        == "clarification_required"
    )


@pytest.mark.integration
def test_unknown_possessive_company_does_not_receive_selected_company_figures(populated):
    result = research(
        populated, AskInput(question="Tell me Contoso's revenue in 2024"), NeverModel()
    )
    assert result["status"] == "abstained" and not result["answer"]["claims"]


@pytest.mark.integration
def test_optional_direction_statement_cannot_override_verified_result(populated, monkeypatch):
    import researchdesk.explanations as explanation

    monkeypatch.setattr(
        explanation,
        "generate_explanation",
        lambda *a, **k: {
            "status": "answered",
            "origin": "generated_text",
            "answer": {
                "claims": [{"text": "Cash balances are higher.", "citations": []}],
                "limitations": [],
            },
        },
    )
    r = research(populated, AskInput(question="2024 revenue", explain=True))
    assert r["status"] == "answered" and r["explanation"]["status"] == "invalid_model_answer"
    assert r["verified_financials"]["measures"][0]["value"] == 110


@pytest.mark.integration
@pytest.mark.parametrize(
    "question",
    [
        "How much did revenue grow in percentage terms from 2023 to 2024?",
        "What was the percentage increase in revenue between FY2023 and FY2024?",
        "Give revenue growth from 2023 to 2024 as a percentage rate",
    ],
)
def test_percentage_wording_selects_growth_not_absolute_change(populated, question):
    r = research(populated, AskInput(question=question), NeverModel())
    assert r["status"] == "answered"
    assert r["financial_request"]["operation"] == "growth"
    assert r["verified_financials"]["measures"][-1]["value"] == pytest.approx(10)
    assert r["verified_financials"]["measures"][-1]["unit"] == "percent"


@pytest.mark.integration
def test_one_period_source_comparison_does_not_require_two_fiscal_years(populated):
    r = research(
        populated,
        AskInput(question="Revenue in 2024 with different source observations"),
        NeverModel(),
    )
    assert r["status"] == "answered"
    assert r["financial_request"]["operation"] == "level"
