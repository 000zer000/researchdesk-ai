"""Conservative capability gate, independent of model-generated language.

The frozen corpus supports annual financial facts, risk disclosures and calendars.
It has no verified market-price feed, monthly units, private information or forecasts.
Entity checks cover explicit question subjects; this is not a general NER system.
"""

import re

ALIASES = {
    "AAPL": {"apple", "apple inc", "aapl"},
    "DELL": {"dell", "dell technologies", "dell technologies inc"},
    "HPQ": {"hp", "hp inc", "hpq", "hewlett packard"},
}
FINANCIAL = r"\b(revenue|revenues|sales|operating income|operating profit|operating earnings|ebitda|net income|margin|growth|cash flow|free cash flow|fcf|cfo|capex|capital expenditure|depreciation|amortization|cash balance|cash equivalents|current assets|current liabilities)\b"
DOCUMENTARY = r"\b(risks?|supply.chain|suppliers?|outsourc\w*|manufactur\w*|component\w*|indebtedness|debt|acquisition|financing|privacy|personal information|cyber\w*|digitization|printing|calendar|weeks?|fiscal period|seasonality)\b"


def capability_gap(question: str, company: str) -> str | None:
    lower = question.lower()
    for other, aliases in ALIASES.items():
        if other != company and any(
            re.search(r"\b" + re.escape(alias) + r"\b", lower) for alias in aliases
        ):
            return "Research answers cover one selected company. A different covered company is named; select it or ask separately."

    # Detect explicit subject names, including unknown companies; do not whitelist
    # individual benchmark names. Generic "the company" means the selected company.
    subject = re.search(
        r"\b(?:(?:what|how)\s+)?(?:was|were|is|are|did|does|do)\s+((?-i:[A-Z][A-Za-z0-9.&-]*(?:\s+[A-Z][A-Za-z0-9.&-]*){0,3})|[a-z][a-z0-9.&-]*)['’]s\b",
        question,
        re.I,
    )
    if not subject:
        subject = re.search(
            r"\b(?:was|were|is|are|did|does|do)\s+((?-i:[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}))\s+(?:annual|consolidated|revenue|operating|cash|sales|disclose|describe|face|report|identify)\b",
            question,
            re.I,
        )
    if subject:
        entity = subject.group(1).strip().rstrip(".").lower()
        if entity not in ALIASES[company] and entity not in {
            "the company",
            "company",
            "its",
            "our company",
        }:
            return "The question names a different or unsupported company. Select a covered company and ask about its filings."
    explicit_risk = bool(re.search(r"\b(risks?|volatility)\b", lower))
    if (
        re.search(
            r"\b(prices?|closing|market cap|market capitalization|price target|upside|buy|sell)\b",
            lower,
        )
        and not explicit_risk
    ):
        return "No verified market-price, supplier-price or trading-recommendation data is available in this workspace."
    if re.search(r"\b(guaranteed|guarantee)\b", lower) or (
        re.search(r"\b(next year|forecast|predicted|future annual)\b", lower)
        and re.search(FINANCIAL, lower)
        and not explicit_risk
    ):
        return "Future financial figures are not published facts in the frozen annual corpus. Use the valuation workspace for explicit assumptions."
    if re.search(r"\b(monthly|month|quarterly|quarter|q[1-4])\b", lower) and not explicit_risk:
        return "Only annual consolidated financial periods are supported; monthly and quarterly figures are outside coverage."
    if re.search(r"\b(dcf|discount rate|enterprise value)\b", lower):
        return "Use Financials & Valuation to supply validated DCF assumptions; free-text questions do not define a complete scenario."
    if not re.search(FINANCIAL, lower) and not re.search(DOCUMENTARY, lower):
        return "Supported questions concern annual financial metrics, disclosed business risks and reporting calendars. The requested information is outside those capabilities."
    return None


def requested_years(question: str) -> set[int]:
    """Recognize both FY2024 and bare year notation at every workflow boundary."""
    return {int(y) for y in re.findall(r"\b(?:FY\s*)?(20\d{2})(?!\d)", question, re.I)}
