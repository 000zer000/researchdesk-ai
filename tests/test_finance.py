import math

import pytest
from pydantic import ValidationError

from researchdesk.finance import DCFInput, MissingData, calculate_metrics, dcf, sensitivity


def test_constant_perpetuity_independent_identity():
    args = DCFInput(
        base_revenue=100,
        growth=[0] * 5,
        operating_margin=0.2,
        tax_rate=0.25,
        da_ratio=0,
        capex_ratio=0,
        nwc_ratio=0,
        discount_rate=0.1,
        terminal_growth=0,
    )
    result = dcf(args)
    assert result["enterprise_value"] == pytest.approx(15 / 0.1)
    assert result["years"][0]["present_value"] == pytest.approx(15 / 1.1)
    assert result["years"][4]["present_value"] == pytest.approx(15 / (1.1**5))


def test_nwc_and_terminal_cash_flow_independently():
    args = DCFInput(
        base_revenue=100,
        growth=[0.1] * 5,
        operating_margin=0.2,
        tax_rate=0.25,
        da_ratio=0.03,
        capex_ratio=0.04,
        nwc_ratio=0.15,
        discount_rate=0.1,
        terminal_growth=0.02,
    )
    result = dcf(args)
    y = result["years"][0]
    assert y["revenue"] == 110
    assert y["delta_nwc"] == 1.5
    assert y["fcff"] == pytest.approx(22 * 0.75 + 3.3 - 4.4 - 1.5)
    r5 = 100 * 1.1**5
    expected = r5 * 1.02 * (0.2 * 0.75 + 0.03 - 0.04) - r5 * 0.02 * 0.15
    assert result["terminal_fcff"] == pytest.approx(expected)


@pytest.mark.parametrize(
    "change",
    [
        {"discount_rate": 0.02, "terminal_growth": 0.02},
        {"discount_rate": 0.01, "terminal_growth": 0.03},
        {"growth": [0.1] * 4},
        {"growth": [float("nan")] * 5},
        {"base_revenue": 0},
        {"tax_rate": 1.5},
        {"execute": "rm"},
        {"operating_margin": float("inf")},
    ],
)
def test_invalid_assumptions_are_rejected(change):
    with pytest.raises(ValidationError):
        DCFInput(**{**{"base_revenue": 100}, **change})


def test_loss_has_no_assumed_tax_credit():
    result = dcf(DCFInput(base_revenue=100, operating_margin=-0.1))
    assert result["years"][0]["operating_tax"] == 0


def test_sensitivity_discounting_and_invalid_cells():
    args = DCFInput(base_revenue=100, discount_rate=0.04, terminal_growth=0.02)
    cells = sensitivity(args)
    assert len(cells) == 15
    assert any(c["enterprise_value"] is None for c in cells)
    same_g = [
        c
        for c in cells
        if math.isclose(c["terminal_growth"], 0.02) and c["enterprise_value"] is not None
    ]
    assert same_g[0]["enterprise_value"] > same_g[-1]["enterprise_value"]


def test_ratios_have_numeric_reference_and_missing_data_error():
    rows = [
        {
            "fiscal_year": 2023,
            "facts": {"revenue": {"value": 100}, "operating_income": {"value": 20}},
        },
        {
            "fiscal_year": 2024,
            "facts": {"revenue": {"value": 110}, "operating_income": {"value": 24.2}},
        },
    ]
    actual = calculate_metrics(rows)
    assert actual["revenue_growth"] == pytest.approx(0.1)
    assert actual["margin_change_pp"] == pytest.approx(2)
    with pytest.raises(MissingData):
        calculate_metrics(rows[:1])
