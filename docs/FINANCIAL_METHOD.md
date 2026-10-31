# Financial methodology

## Source discipline

Coverage: Apple (CIK 0000320193), Dell (0001571996), HP (0000047217), original FY2023 and FY2024 10-Ks. Each fact is pinned to the exact accession, consolidated context, USD unit and exact annual start/end or balance-sheet instant. Annual duration must be 350–380 days to admit 52/53-week calendars while excluding quarters and year-to-date periods. Duplicate equal records are accepted; conflicting values within the same selection raise an error. No latest-record selection or later restatement substitution occurs.

Publication filtering is inclusive at **end of the chosen calendar day**, not an intraday backtest. The original SEC filing date is used, not the report period end. No sources published later are retrieved or exposed by the evidence API. This is a small frozen corpus, not a current financial-data feed.

`evaluation/v1.1/financial-source-checks.json` records a second parser's check of the original inline XBRL context, scale, sign, unit and value. That is independent of Company Facts selection, but it is not independent human validation.

## Definitions and signs

Revenue and operating income use consolidated US GAAP tags. Operating margin = operating income / revenue. Revenue growth = current annual revenue / previous annual revenue - 1. Margin changes are percentage points, not percent growth of the margin.

CFO is net cash provided by operating activities. Capex is a **positive cash outflow**, deducted in cash-flow calculations. Apple and Dell use `PaymentsToAcquirePropertyPlantAndEquipment`. HP uses `PaymentsToAcquireProductiveAssets`; the original cash-flow statements label the selected 2023/2024 values as investment in property, plant and equipment. The mapping is explicit for HP, not a global concept equivalence. Depreciation/amortization uses the consolidated reported cash-flow reconciliation concept; company definitions and composition can differ.

Cash is cash and equivalents only, not all liquid securities. Current assets/current liabilities are descriptive balance-sheet facts. They are not used as operating working capital because they include financing and cash-related components. CFO less capex is a **cash-flow proxy**, not unlevered FCFF: CFO can include interest, cash taxes and working-capital effects not isolated by the proxy.

Apple FY2023: 53 weeks, ended 2023-09-30; FY2024: 52 weeks, ended 2024-09-28. Dell FY2023: 53 weeks, ended 2023-02-03; FY2024: 52 weeks, ended 2024-02-02. HP years end October 31. Apple services, Dell infrastructure/financing and HP printing differ materially. Peer tables compare growth, operating margins and cash generation, without calendar alignment or segment adjustment. They are not trading-multiple comparisons.

## Five-year DCF

All monetary values are USD millions. The base is the latest Apple annual revenue actually published by the analysis date. Every forecast input is an analyst assumption, not a model prediction or company guidance.

For year t = 1…5:

```text
Revenue[t] = Revenue[t-1] × (1 + growth[t])
EBIT[t] = Revenue[t] × operating margin
Operating tax[t] = max(EBIT[t], 0) × operating tax rate
D&A[t] = Revenue[t] × D&A ratio
Capex[t] = Revenue[t] × capex ratio
ΔNWC[t] = (Revenue[t] - Revenue[t-1]) × operating NWC ratio
FCFF[t] = EBIT[t] - operating tax[t] + D&A[t] - Capex[t] - ΔNWC[t]
PV[t] = FCFF[t] / (1 + discount rate)^t
```

Year six is recomputed using terminal growth and the same operating ratios, including ΔNWC = revenue[5] × terminal growth × NWC ratio. Terminal value at year five = FCFF[6] / (discount rate - terminal growth). Enterprise value = five forecast present values + terminal value discounted five periods. This avoids incorrectly growing a high-growth year-five working-capital cash outflow into perpetuity.

Decimal arithmetic is used in the DCF. First forecast cash flow is discounted one full year (year-end convention). A positive minimum discount rate and at least a 0.01-percentage-point spread over terminal growth prevent numerically unstable denominators. Invalid sensitivity cells are absent values, not fabricated zeros. Taxes receive no loss credit; loss carryforwards are not modeled. No leases, acquisitions, cash/debt bridge, share counts, dilution, market price or upside is inferred.

The annuity/perpetuity test independently checks a flat USD100 revenue business with USD15 annual FCFF and 10% discount rate: EV = 15 / 0.10 = USD150. Separate tests check year-one/year-five discount periods, working capital, terminal year-six cash flow, sensitivities, invalid inputs, and missing facts.


## v1.1 answer consistency and conflicting evidence

Every supported research financial measure carries actual start/end dates, consolidated scope, USD display unit, concept/definition, value, direction and the complete source-input citation set. Margin change uses percentage points, not percentage growth. CFO less gross PPE capex requires both CFO and gross-capex evidence; it must not be replaced by Dell's company-reported net-capex FCF. A requested definition absent from the ledger is refused, with the available verified data shown separately.

Multiple same-metric observations are compared before selection. Different companies never enter the same selected-company ledger. Currency and segment records cannot replace consolidated USD records. Period, concept, value or reporting-basis disagreements within the eligible annual metric remain unresolved: both sources are exposed and derived conclusions withheld. `reporting_basis` and `restates_accession` preserve explicitly curated revision metadata; the LLM never assigns it. The present official corpus contains original filings, not a claimed exhaustive restatement history.

The model proposes structured measures; code validates every field and renders the accepted financial wording. Financial assertions cannot bypass the contract through qualitative prose or limitations. Source excerpts may contain other reported figures: these remain labeled source evidence, not approved calculations. Unsupported paraphrases of intent can lead to abstention or incomplete interpretation; the small dataset does not establish universal natural-language understanding.

Reporting-week comparisons are also typed measures. For a verified annual start/end pair, inclusive days are `(end - start).days + 1`; only a duration exactly divisible by seven supports a whole-week count. Both periods and complete period-source IDs are required for the change. This corrects a measured prose equality error. HP's date-based annual periods must not be silently labeled 52-week calendars.
