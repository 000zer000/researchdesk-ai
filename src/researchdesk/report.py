"""Three-page analyst note; the API and export share the same financial engine."""

import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Document
from .finance import DCFInput, MissingData, calculate_metrics, dcf, historical, sensitivity

NAVY = colors.HexColor("#142d3d")
TEAL = colors.HexColor("#087e82")
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="DeskTitle",
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=30,
        textColor=NAVY,
        spaceAfter=15,
    )
)
styles.add(
    ParagraphStyle(
        name="DeskH",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=TEAL,
        spaceBefore=14,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(name="DeskBody", fontName="Helvetica", fontSize=9, leading=13, spaceAfter=8)
)
styles.add(
    ParagraphStyle(name="DeskSmall", fontName="Helvetica", fontSize=8, leading=11, spaceAfter=6)
)
styles.add(ParagraphStyle(name="DeskRight", parent=styles["DeskSmall"], alignment=TA_RIGHT))


def p(text, style="DeskBody"):
    return Paragraph(text, styles[style])


def table(data, widths=None):
    out = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    out.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f5f7"), colors.white]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#d6e0e5")),
            ]
        )
    )
    return out


def make_report(session: Session, as_of: date, a: DCFInput) -> bytes:
    rows = historical(session, "AAPL", as_of)
    if not rows or "revenue" not in rows[-1]["facts"]:
        raise MissingData("No published Apple revenue at this analysis date")
    base = rows[-1]["facts"]["revenue"]["value"]
    if abs(a.base_revenue - base) > 0.001:
        raise ValueError("Base revenue must match the latest published Apple annual fact")
    result = dcf(a)
    out = io.BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=(595.28, 841.89),
        rightMargin=42,
        leftMargin=42,
        topMargin=47,
        bottomMargin=44,
        title="ResearchDesk | Apple research note",
    )
    story = [
        p("RESEARCHDESK / ANALYST NOTE", "DeskSmall"),
        p("Apple, in evidence", "DeskTitle"),
        p(
            f"Analysis date: {as_of} (end of day) | Published fiscal years: {', '.join(str(r['fiscal_year']) for r in rows)} | USD millions",
            "DeskSmall",
        ),
        p(
            "An educational review of published financials and explicit valuation assumptions. No investment recommendation."
        ),
    ]
    story += [p("01 / Published financial record", "DeskH")]
    labels = {
        "revenue": "Revenue",
        "operating_income": "Operating income",
        "cfo": "Operating cash flow",
        "capex": "Capital expenditure (cash outflow)",
        "da": "Depreciation & amortization",
        "cash": "Cash & equivalents",
    }
    data = [["USD millions"] + [f"FY{r['fiscal_year']}" for r in rows]]
    for key, label in labels.items():
        data.append(
            [label]
            + [
                f"{r['facts'][key]['value']:,.0f}" if key in r["facts"] else "Not mapped"
                for r in rows
            ]
        )
    data.append(
        ["Operating margin"]
        + [
            f"{r['operating_margin']:.2%}" if "operating_margin" in r else "Unavailable"
            for r in rows
        ]
    )
    story += [table(data, [285] + [105] * len(rows)), Spacer(1, 12)]
    if len(rows) == 2:
        m = calculate_metrics(rows)
        story += [
            p(
                f"Revenue changed by {m['revenue_change']:,.0f} ({m['revenue_growth']:.2%}). "
                f"Operating margin moved from {m['operating_margin_from']:.2%} to {m['operating_margin_to']:.2%}, "
                f"a change of {m['margin_change_pp']:.2f} percentage points. These are server-calculated ratios."
            )
        ]
    story += [
        p("02 / Documented risk context", "DeskH"),
        p(
            "Apple discloses reliance on outsourcing partners and concentrated supply chains, including manufacturing in Asia. "
            "Component availability, production disruptions and geopolitical restrictions can affect its ability to supply products. "
            f"See Apple FY{rows[-1]['fiscal_year']} Form 10-K, Item 1A, operational and supply-chain risk factors. This paragraph is an editorial source summary, not a live model response."
        ),
        p(
            "Historical periods use only their original pinned annual filings. Apple FY2023 contains 53 weeks; FY2024 contains 52 weeks. "
            "Apple's services mix differs from Dell's infrastructure exposure and HP's printing business. Financial comparability is limited.",
            "DeskSmall",
        ),
        PageBreak(),
        p("Peers & source discipline", "DeskTitle"),
        p("03 / Operating comparison", "DeskH"),
    ]
    peers = []
    for company in ["AAPL", "DELL", "HPQ"]:
        history = historical(session, company, as_of)
        if history:
            latest = history[-1]
            peers.append(
                [
                    company,
                    latest["end"],
                    f"{latest['facts']['revenue']['value']:,.0f}"
                    if "revenue" in latest["facts"]
                    else "Missing",
                    f"{latest['revenue_growth']:.1%}" if "revenue_growth" in latest else "n/a",
                    f"{latest['operating_margin']:.1%}" if "operating_margin" in latest else "n/a",
                    f"{latest['cfo_margin']:.1%}" if "cfo_margin" in latest else "n/a",
                ]
            )
    story += [
        table(
            [["Company", "Year end", "Revenue", "Growth", "Op. margin", "CFO/rev."]] + peers,
            [62, 86, 94, 70, 92, 91],
        ),
        Spacer(1, 12),
        p(
            "These are operating comparisons, with different fiscal calendars and product mixes. No market prices, trading multiples or implied upside are used. "
            "Dell FY2023 includes 53 weeks and its FY2024 includes 52. CFO less capex, when shown in the application, is a cash-flow proxy and is not labeled FCFF."
        ),
        p("04 / Source register", "DeskH"),
    ]
    documents = session.scalars(
        select(Document).where(Document.filed <= as_of).order_by(Document.id)
    ).all()
    for source in documents:
        story += [
            p(
                f"<b>{escape(source.id)}</b> | filed {source.filed} | CIK {source.cik}<br/>"
                f"Accession {source.accession} | <link href='{escape(source.url)}' color='#087e82'>Open official filing</link><br/>"
                f"SHA-256 {source.sha256[:24]}... | parser {escape(source.parser_version)}",
                "DeskSmall",
            )
        ]
    story += [
        p("Evidence and interpretation", "DeskH"),
        p(
            "The application exposes passage identifiers, source context and tool traces. Citation existence is validated automatically; "
            "claim support still requires independent review. Live model outputs are excluded from this note so changes to valuation inputs cannot retain stale model commentary. "
            "The source manifest records full document hashes and retrieval dates. No full report or model weights are distributed.",
            "DeskSmall",
        ),
        PageBreak(),
        p("Valuation, by assumption", "DeskTitle"),
        p("05 / Five-year FCFF scenario", "DeskH"),
        p(
            f"Enterprise value: <b>{result['enterprise_value']:,.0f} USD million</b>. "
            f"Terminal value contributes {result['terminal_share']:.1%} of enterprise value. This is a scenario output, not a price target."
        ),
        table(
            [
                ["Input", "Scenario assumption"],
                ["Base revenue (published)", f"{a.base_revenue:,.0f}"],
                ["Revenue growth, years 1-5", ", ".join(f"{g:.1%}" for g in a.growth)],
                [
                    "Operating margin / operating tax",
                    f"{a.operating_margin:.1%} / {a.tax_rate:.1%}",
                ],
                [
                    "D&A / capex / operating NWC, % revenue",
                    f"{a.da_ratio:.1%} / {a.capex_ratio:.1%} / {a.nwc_ratio:.1%}",
                ],
                [
                    "Discount rate / terminal growth",
                    f"{a.discount_rate:.1%} / {a.terminal_growth:.1%}",
                ],
            ],
            [300, 195],
        ),
        Spacer(1, 12),
    ]
    story += [
        table(
            [["Forecast year", "Revenue", "EBIT", "FCFF", "PV of FCFF"]]
            + [
                [str(int(y["year"]))]
                + [f"{y[k]:,.0f}" for k in ["revenue", "ebit", "fcff", "present_value"]]
                for y in result["years"]
            ],
            [95, 100, 100, 100, 100],
        ),
        p("06 / Sensitivity of enterprise value (USD millions)", "DeskH"),
    ]
    cells = sensitivity(a)
    rates = sorted({c["discount_rate"] for c in cells})
    gs = sorted({c["terminal_growth"] for c in cells})
    story += [
        table(
            [["Discount / terminal g"] + [f"{g:.1%}" for g in gs]]
            + [
                [f"{w:.1%}"]
                + [
                    next(
                        (
                            f"{c['enterprise_value']:,.0f}"
                            if c["enterprise_value"] is not None
                            else "Invalid"
                        )
                        for c in cells
                        if c["discount_rate"] == w and c["terminal_growth"] == g
                    )
                    for g in gs
                ]
                for w in rates
            ],
            [180, 105, 105, 105],
        ),
        Spacer(1, 10),
        p(
            "FCFF = EBIT - cash operating tax + D&A - capex - change in operating NWC. "
            "Forecast assumptions are analyst inputs, not company guidance. Year-end discounting; no tax credit for losses; "
            "no loss carryforwards, leases, acquisitions or equity bridge. Terminal year-six cash flow is recomputed with terminal growth. "
            "Operating NWC is modeled as a revenue ratio, not inferred from total current assets less liabilities. The model is highly sensitive to terminal assumptions.",
            "DeskSmall",
        ),
    ]

    def footer(canvas, document):
        canvas.setStrokeColor(TEAL)
        canvas.line(42, 33, 553, 33)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(
            42, 20, "ResearchDesk | Educational scenario | Reproduce and inspect every assumption"
        )
        canvas.drawRightString(553, 20, str(document.page))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
