"""USD millions throughout. No model or frontend performs these calculations."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Document, Fact


class MissingData(ValueError):
    pass


class DCFInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    base_revenue: float = Field(gt=0, le=10_000_000)
    growth: list[float] = Field(default_factory=lambda: [0.04] * 5, min_length=5, max_length=5)
    operating_margin: float = Field(default=0.30, ge=-0.5, le=0.8)
    tax_rate: float = Field(default=0.21, ge=0, le=0.6)
    da_ratio: float = Field(default=0.03, ge=0, le=0.5)
    capex_ratio: float = Field(default=0.03, ge=0, le=0.5)
    nwc_ratio: float = Field(default=0.02, ge=-0.5, le=0.5)
    discount_rate: float = Field(default=0.09, ge=0.001, le=0.5)
    terminal_growth: float = Field(default=0.02, ge=-0.05, le=0.10)

    @model_validator(mode="after")
    def coherent(self):
        if self.discount_rate <= self.terminal_growth:
            raise ValueError("Discount rate must exceed terminal growth")
        if self.discount_rate - self.terminal_growth < 0.0001:
            raise ValueError(
                "Discount rate must exceed terminal growth by at least 0.01 percentage point"
            )
        if any(not -0.5 <= g <= 0.5 for g in self.growth):
            raise ValueError("Annual growth must be between -50% and 50%")
        return self


def dcf(a: DCFInput) -> dict:
    # Decimal from decimal strings avoids hidden binary arithmetic in the financial engine.
    d = lambda v: Decimal(str(v))  # noqa: E731
    revenue = d(a.base_revenue)
    wacc, g = d(a.discount_rate), d(a.terminal_growth)
    rows = []
    pv_total = Decimal(0)
    for year, growth in enumerate(a.growth, 1):
        previous = revenue
        revenue *= 1 + d(growth)
        ebit = revenue * d(a.operating_margin)
        # No modeled tax credit for losses; no loss carryforward modeled.
        tax = max(ebit, Decimal(0)) * d(a.tax_rate)
        da, capex = revenue * d(a.da_ratio), revenue * d(a.capex_ratio)
        delta_nwc = (revenue - previous) * d(a.nwc_ratio)
        fcff = ebit - tax + da - capex - delta_nwc
        pv = fcff / (1 + wacc) ** year
        pv_total += pv
        rows.append(
            {
                k: float(v)
                for k, v in dict(
                    year=year,
                    revenue=revenue,
                    ebit=ebit,
                    operating_tax=tax,
                    da=da,
                    capex=capex,
                    delta_nwc=delta_nwc,
                    fcff=fcff,
                    present_value=pv,
                ).items()
            }
        )
    # Recompute steady-state year six so working capital follows terminal growth.
    terminal_revenue = revenue * (1 + g)
    terminal_ebit = terminal_revenue * d(a.operating_margin)
    terminal_fcff = (
        terminal_ebit
        - max(terminal_ebit, Decimal(0)) * d(a.tax_rate)
        + terminal_revenue * (d(a.da_ratio) - d(a.capex_ratio))
        - revenue * g * d(a.nwc_ratio)
    )
    terminal_value = terminal_fcff / (wacc - g)
    terminal_pv = terminal_value / (1 + wacc) ** 5
    ev = pv_total + terminal_pv
    return {
        "unit": "USD millions",
        "assumptions": a.model_dump(),
        "years": rows,
        "terminal_fcff": float(terminal_fcff),
        "terminal_value": float(terminal_value),
        "terminal_present_value": float(terminal_pv),
        "enterprise_value": float(ev),
        "terminal_share": float(terminal_pv / ev) if ev else None,
        "discount_convention": "year-end; first forecast discounted one full year",
    }


def sensitivity(a: DCFInput) -> list[dict]:
    result = []
    for dw in [-0.02, -0.01, 0, 0.01, 0.02]:
        for dg in [-0.01, 0, 0.01]:
            w, g = round(a.discount_rate + dw, 6), round(a.terminal_growth + dg, 6)
            values = {**a.model_dump(), "discount_rate": w, "terminal_growth": g}
            try:
                value = dcf(DCFInput(**values))["enterprise_value"]
            except ValueError:
                value = None
            result.append({"discount_rate": w, "terminal_growth": g, "enterprise_value": value})
    return result


def historical(session: Session, company: str, as_of: date) -> list[dict]:
    facts = session.scalars(
        select(Fact)
        .join(Document)
        .where(Fact.company == company, Document.filed <= as_of)
        .order_by(Fact.fiscal_year, Document.filed)
    ).all()
    years: dict[int, dict] = {}
    for f in facts:
        row = years.setdefault(
            f.fiscal_year,
            {"fiscal_year": f.fiscal_year, "end": str(f.end), "unit": "USD millions", "facts": {}},
        )
        # Ingested facts are only the contemporary annual period of the pinned filing.
        row["facts"][f.metric] = {
            "value": f.value / 1e6,
            "concept": f.concept,
            "unit": f.unit,
            "currency": f.currency,
            "start": str(f.start) if f.start else None,
            "end": str(f.end),
            "scope": f.scope,
            "evidence_id": f.evidence_id,
            "document_id": f.document_id,
        }
    for row in years.values():
        f = row["facts"]
        revenue = f.get("revenue", {}).get("value")
        if revenue and "operating_income" in f:
            row["operating_margin"] = f["operating_income"]["value"] / revenue
        if revenue and "cfo" in f:
            row["cfo_margin"] = f["cfo"]["value"] / revenue
        if "cfo" in f and "capex" in f:
            row["cfo_less_capex"] = f["cfo"]["value"] - f["capex"]["value"]
    result = list(years.values())
    for previous, current in zip(result, result[1:], strict=False):
        if all("revenue" in x["facts"] for x in (previous, current)):
            current["revenue_growth"] = (
                current["facts"]["revenue"]["value"] / previous["facts"]["revenue"]["value"] - 1
            )
    return result


def calculate_metrics(rows: list[dict]) -> dict:
    if len(rows) != 2:
        raise MissingData("Two published annual periods are required")
    a, b = rows
    try:
        r0, r1 = [x["facts"]["revenue"]["value"] for x in rows]
        o0, o1 = [x["facts"]["operating_income"]["value"] for x in rows]
    except KeyError as error:
        raise MissingData("Revenue and operating income are required") from error
    if r0 <= 0 or r1 <= 0:
        raise MissingData("Positive revenues required for margins")
    return {
        "from_year": a["fiscal_year"],
        "to_year": b["fiscal_year"],
        "revenue_change": r1 - r0,
        "revenue_growth": r1 / r0 - 1,
        "operating_margin_from": o0 / r0,
        "operating_margin_to": o1 / r1,
        "margin_change_pp": (o1 / r1 - o0 / r0) * 100,
        "unit": "USD millions; ratios as fractions",
    }
