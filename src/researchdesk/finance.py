"""USD millions throughout. No model or frontend performs these calculations."""

import math
import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Document, Fact
from .scope import requested_years


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
    """Resolve comparable observations, never last-write-wins across filings.

    Segment/currency observations remain visible but cannot replace consolidated USD.
    Different periods, concepts or reporting bases for the same annual metric are
    unresolved until curated provenance establishes a single comparable observation.
    Even explicitly linked restatements are shown alongside originals, not selected
    merely because they were published later.
    """
    pairs = session.execute(
        select(Fact, Document)
        .join(Document)
        .where(Fact.company == company, Document.company == company, Document.filed <= as_of)
        .order_by(Fact.fiscal_year, Fact.metric, Document.filed, Fact.id)
    ).all()
    years: dict[int, dict] = {}
    groups: dict[tuple, list] = {}
    for f, d in pairs:
        row = years.setdefault(
            f.fiscal_year,
            {
                "fiscal_year": f.fiscal_year,
                "end": str(f.end),
                "unit": "USD millions",
                "facts": {},
                "observations": [],
                "conflicts": [],
            },
        )
        observation = {
            "metric": f.metric,
            "company": f.company,
            "value": f.value / 1e6,
            "raw_value": f.value,
            "concept": f.concept,
            "unit": f.unit,
            "currency": f.currency,
            "start": str(f.start) if f.start else None,
            "end": str(f.end),
            "scope": f.scope,
            "reporting_basis": f.reporting_basis,
            "restates_accession": f.restates_accession,
            "evidence_id": f.evidence_id,
            "evidence_ids": [f.evidence_id] if f.evidence_id else [],
            "document_id": d.id,
            "accession": d.accession,
            "filed": str(d.filed),
        }
        row["observations"].append(observation)
        groups.setdefault((f.fiscal_year, f.metric), []).append(observation)
    for (year, metric), observations in groups.items():
        row = years[year]
        eligible = [
            o
            for o in observations
            if math.isfinite(o["raw_value"])
            and o["unit"] == "USD"
            and o["currency"] == "USD"
            and o["scope"] == "consolidated"
            and o["evidence_id"]
            and o["reporting_basis"] in {"as_reported", "restated"}
            and (
                not o["restates_accession"]
                if o["reporting_basis"] == "as_reported"
                else bool(o["restates_accession"])
            )
            and (
                o["start"] is None
                or 350
                <= (date.fromisoformat(o["end"]) - date.fromisoformat(o["start"])).days
                <= 380
            )
        ]
        identities = {
            (
                o["company"],
                o["start"],
                o["end"],
                o["concept"],
                o["reporting_basis"],
                o["restates_accession"],
            )
            for o in eligible
        }
        values = {Decimal(str(o["raw_value"])) for o in eligible}
        if len(identities) != 1 or len(values) != 1:
            row["conflicts"].append(
                {
                    "metric": metric,
                    "fiscal_year": year,
                    "reason": "No single comparable consolidated USD observation: check value, period, definition and reporting basis. No filing was preferred by recency.",
                    "observations": observations,
                }
            )
            continue
        chosen = dict(eligible[0])
        chosen["evidence_ids"] = sorted({o["evidence_id"] for o in eligible})
        row["facts"][metric] = chosen
    for row in years.values():
        f = row["facts"]

        def same_period(*metrics, f=f):
            return (
                all(m in f for m in metrics)
                and len({(f[m]["start"], f[m]["end"]) for m in metrics}) == 1
            )

        revenue = f.get("revenue", {}).get("value")
        if revenue and same_period("revenue", "operating_income"):
            row["operating_margin"] = f["operating_income"]["value"] / revenue
        if revenue and same_period("revenue", "cfo"):
            row["cfo_margin"] = f["cfo"]["value"] / revenue
        if same_period("cfo", "capex"):
            row["cfo_less_capex"] = f["cfo"]["value"] - f["capex"]["value"]
    result = list(years.values())
    for previous, current in zip(result, result[1:], strict=False):
        if all("revenue" in x["facts"] for x in (previous, current)):
            a, b = [x["facts"]["revenue"] for x in (previous, current)]
            if a["concept"] == b["concept"] and a["value"] > 0:
                current["revenue_growth"] = b["value"] / a["value"] - 1
    return result


METRIC_PATTERNS = {
    "revenue": r"\b(revenues?|sales)\b",
    "operating_income": r"\b(operating (income|profits?|earnings))\b",
    "cfo": r"\b(cfo|operating cash(?: flows?)?|cash (?:flows?|generated|provided) (?:from|by) (?:operating activities|operations))\b",
    "capex": r"\b(capex|capital (?:expenditure|spending)s?|purchases of (?:property|ppe))\b",
    "da": r"\b(depreciation|amortization|d&a)\b",
    "cash": r"\b(cash balances?|cash (?:and cash )?equivalents)\b",
    "current_assets": r"\bcurrent assets\b",
    "current_liabilities": r"\bcurrent liabilities\b",
}


COMPARISON_PATTERN = r"\b(change|growth|compare|comparison|increase|decrease|rose|fell|grew|declined|versus|vs|trend|equal|same|different|longer|shorter|higher|lower|greater|smaller)\b"


def financial_plan(question: str, rows: list[dict], company: str) -> dict | None:
    """Bounded question interpretation; all arithmetic and measure contracts live here.

    Unsupported financial definitions do not fall through into unchecked prose.
    Dates are actual fiscal dates, not inferred calendar-year periods.
    """
    q = question.lower()
    calendar = bool(re.search(r"\b(weeks?|calendar|fiscal period)\b", q))
    metrics = [m for m, pattern in METRIC_PATTERNS.items() if re.search(pattern, q)]
    margin = bool(re.search(r"\boperating(?: profit| income)? margins?\b", q))
    proxy = bool(
        re.search(
            r"\b(free cash flow|fcf|cash.flow proxy|cfo\s*(?:minus|less|-)\s*(?:gross\s+)?capex)\b",
            q,
        )
    )
    proxy = proxy or (
        "cfo" in metrics
        and "capex" in metrics
        and bool(re.search(r"\b(minus|less|subtract|net of|after)\b", q))
    )
    financial = bool(
        calendar
        or metrics
        or margin
        or proxy
        or re.search(r"\b(margins?|growth|cash flows?|net income|ebitda)\b", q)
    )
    # Qualitative risk disclosures retain the prose route, with a numeric-claim gate.
    if not financial or (
        not calendar and re.search(r"\b(risks?|could|drivers?|factors?|reasons?)\b", q)
    ):
        return None
    issues = []
    unsupported_definition = bool(
        re.search(
            r"\b(net capex|net capital|adjusted|non.gaap|gross margins?|ebitda|net income|net margins?)\b",
            q,
        )
    )
    ambiguous_fcf = bool(re.search(r"\b(free cash flow|fcf)\b", q)) and not bool(
        re.search(r"\bcfo\s*(?:minus|less|-)\s*(?:gross\s+)?capex\b", q)
    )
    if unsupported_definition or ambiguous_fcf:
        issues.append(
            "The requested definition is not verified in the structured ledger. Company-reported net-capex free cash flow must not be substituted for CFO less gross PPE capex."
        )
    reverse = re.search(r"\bfrom\s+(?:fy\s*)?(20\d{2})\s+(?:back\s+)?to\s+(?:fy\s*)?(20\d{2})", q)
    if reverse and reverse.group(1) > reverse.group(2):
        issues.append(
            "Reverse chronological change is outside the supported comparison convention; no reversal was assumed."
        )
    explicit = sorted(requested_years(q))
    selected = [r for r in rows if not explicit or r["fiscal_year"] in explicit]
    if not explicit and selected:
        if re.search(
            COMPARISON_PATTERN,
            q,
        ):
            selected = selected[-2:]
        else:
            selected = selected[-1:]
    if calendar:
        metrics = ["revenue"]
    if margin:
        metrics = list(dict.fromkeys(metrics + ["revenue", "operating_income"]))
    if proxy:
        metrics = list(dict.fromkeys(metrics + ["cfo", "capex"]))
    if re.search(r"\bgrowth\b", q) and not metrics:
        issues.append("Specify the metric whose growth is requested.")
    if not metrics:
        issues.append("The requested financial measure has no verified definition in this ledger.")
    measures = []
    observations = [
        dict(o, fiscal_year=r["fiscal_year"])
        for r in selected
        for o in r["observations"]
        if o["metric"] in metrics
    ]
    conflicts = [c for r in selected for c in r["conflicts"] if c["metric"] in metrics]
    if conflicts:
        issues.append(
            "Conflicting or incomparable source observations remain unresolved; both proofs are retained below."
        )

    def add(name, rs, inputs, value, unit, definition, label, change=False):
        periods = [
            f"{r['facts'][inputs[0]]['start'] or 'instant'}/{r['facts'][inputs[0]]['end']}"
            for r in rs
        ]
        facts = [r["facts"][m] for r in rs for m in inputs]
        if len({f["reporting_basis"] for f in facts}) != 1:
            issues.append("Inputs have different reporting bases; derived measure withheld.")
            return
        if any(
            (f["start"], f["end"]) != (r["facts"][inputs[0]]["start"], r["facts"][inputs[0]]["end"])
            for r in rs
            for f in [r["facts"][m] for m in inputs]
        ):
            issues.append("Inputs cover different fiscal periods; derived measure withheld.")
            return
        if len(rs) > 1 and any(len({r["facts"][m]["concept"] for r in rs}) != 1 for m in inputs):
            issues.append("Input definitions changed across periods; comparison withheld.")
            return
        measures.append(
            {
                "id": name + ":" + ":".join(str(r["fiscal_year"]) for r in rs),
                "company": company,
                "periods": periods,
                "scope": "consolidated",
                "unit": unit,
                "definition": definition,
                "value": float(value),
                "direction": (
                    "increased" if value > 0 else "decreased" if value < 0 else "unchanged"
                )
                if change
                else "level",
                "citations": sorted({e for f in facts for e in f["evidence_ids"]}),
                "label": label,
            }
        )

    complete = [r for r in selected if all(m in r["facts"] for m in metrics)]
    if len(complete) != len(selected) or not complete:
        issues.append("One or more required annual facts are missing or unresolved.")
        return {
            "measures": measures,
            "issues": issues,
            "observations": observations,
            "conflicts": conflicts,
        }

    def D(r, m):
        return Decimal(str(r["facts"][m]["raw_value"])) / Decimal(1000000)

    def period_weeks(row):
        fact = row["facts"]["revenue"]
        if not fact["start"]:
            return None
        days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days + 1
        return Decimal(days) / 7 if days % 7 == 0 else None

    for r in complete:
        if calendar:
            weeks = period_weeks(r)
            if weeks is None:
                issues.append(
                    "A whole-week fiscal calendar is not established by this annual period. Actual source dates remain visible; no week count is assumed."
                )
            else:
                add(
                    "period_weeks",
                    [r],
                    ["revenue"],
                    weeks,
                    "weeks",
                    "inclusive_fiscal_days/7",
                    "Fiscal period length",
                )
        elif margin:
            if D(r, "revenue") <= 0:
                issues.append("Positive revenue is required for operating margin.")
                continue
            add(
                "operating_margin",
                [r],
                ["revenue", "operating_income"],
                D(r, "operating_income") / D(r, "revenue") * 100,
                "percent",
                "operating_income/revenue",
                "Operating margin",
            )
        elif proxy:
            add(
                "cfo_less_capex",
                [r],
                ["cfo", "capex"],
                D(r, "cfo") - D(r, "capex"),
                "USD million",
                "cfo-gross_PPE_capex",
                "CFO less gross PPE capex (not company-reported net-capex FCF)",
            )
        else:
            for m in metrics:
                add(
                    m,
                    [r],
                    [m],
                    D(r, m),
                    "USD million",
                    r["facts"][m]["concept"],
                    m.replace("_", " ").capitalize(),
                )
    change = bool(
        re.search(
            COMPARISON_PATTERN,
            q,
        )
    )
    if change:
        if len(complete) != 2:
            issues.append("A change requires two explicitly available comparable annual periods.")
        else:
            a, b = complete
            if calendar:
                wa, wb = period_weeks(a), period_weeks(b)
                if wa is not None and wb is not None:
                    add(
                        "period_weeks_change",
                        complete,
                        ["revenue"],
                        wb - wa,
                        "weeks",
                        "delta(inclusive_fiscal_days/7)",
                        "Fiscal period length change",
                        True,
                    )
            elif margin and D(a, "revenue") > 0 and D(b, "revenue") > 0:
                value = (
                    D(b, "operating_income") / D(b, "revenue")
                    - D(a, "operating_income") / D(a, "revenue")
                ) * 100
                add(
                    "operating_margin_change",
                    complete,
                    ["revenue", "operating_income"],
                    value,
                    "percentage points",
                    "delta(operating_income/revenue)*100",
                    "Operating margin change",
                    True,
                )
            elif not proxy:
                for m in metrics:
                    add(
                        m + "_change",
                        complete,
                        [m],
                        D(b, m) - D(a, m),
                        "USD million",
                        "delta:" + a["facts"][m]["concept"],
                        m.replace("_", " ").capitalize() + " change",
                        True,
                    )
                    if re.search(r"\b(growth|percent|percentage|rate)\b|%", q):
                        if D(a, m) <= 0:
                            issues.append("Positive starting value required for a growth rate.")
                        else:
                            add(
                                m + "_growth",
                                complete,
                                [m],
                                (D(b, m) / D(a, m) - 1) * 100,
                                "percent",
                                "growth:" + a["facts"][m]["concept"],
                                m.replace("_", " ").capitalize() + " growth",
                                True,
                            )
    return {
        "measures": measures,
        "issues": issues,
        "observations": observations,
        "conflicts": conflicts,
    }


def calculate_metrics(rows: list[dict]) -> dict:
    if len(rows) != 2:
        raise MissingData("Two published annual periods are required")
    a, b = rows
    try:
        r0, r1 = [x["facts"]["revenue"]["value"] for x in rows]
        o0, o1 = [x["facts"]["operating_income"]["value"] for x in rows]
    except KeyError as error:
        raise MissingData("Revenue and operating income are required") from error
    for row in rows:
        facts = row["facts"]
        if any(
            not facts[m].get(k)
            for m in ("revenue", "operating_income")
            for k in ("start", "end", "concept")
        ):
            raise MissingData("Annual period and definition metadata required for comparison")
        if (
            len({(facts[m]["start"], facts[m]["end"]) for m in ("revenue", "operating_income")})
            != 1
        ):
            raise MissingData("Ratio inputs cover different fiscal periods")
    for metric in ("revenue", "operating_income"):
        if len({row["facts"][metric]["concept"] for row in rows}) != 1:
            raise MissingData("Input definitions changed across periods")
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
