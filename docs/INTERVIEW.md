# Interview guide

## A two-minute explanation

“ResearchDesk helps an analyst inspect annual filings rather than trust an unsupported summary. It combines a small real local language model with retrieval, exact source-linked financial facts, and deterministic scenario valuation. I deliberately limited coverage to Apple and two operating peers. The evidence panel shows what the model actually saw. A valid citation ID is not proof that the claim is supported, so those checks are measured separately.”

Use “implemented and measured” for the actual pipeline; use the verification ledger for checks that ran. Do not call the small model reliably accurate, independent human-reviewed or production-ready. Explain the recorded failures as engineering evidence, not as hidden exceptions.

## Walk through the code

1. `data/sources.json`: identify one original accession and its filing date. Explain why the fiscal year-end is not a publication date.
2. `ingestion.py`: follow `choose_fact`. Show how a quarterly record, a segment or a later filing cannot silently become the annual consolidated historical fact. Then show the separate original-inline-XBRL check.
3. `search.py`: explain PostgreSQL stemming and lexical rank; cosine on local MiniLM vectors; reciprocal-rank fusion with constant 60. Discuss the modest corpus and why pgvector/reranking were not automatically added.
4. `research.py`: show the fixed typed workflow and financial-fact augmentation. The model does not decide to execute code or call the internet. Discuss structured validation, one bounded structure-repair attempt, citation membership, and why semantic support still requires source inspection.
5. `finance.py`: derive FCFF from EBIT and operating assumptions. Explain why CFO minus capex is not automatically FCFF. Demonstrate that the first cash flow is discounted one year and that terminal year-six working capital uses terminal growth.
6. `report.py` and React: the PDF uses the same financial functions as the API. Change a discount rate and export; the file contains the current assumptions. No stale AI paragraphs are carried into the note.
7. `evaluation.py`, `cases.json`, result/review files: distinguish retrieval, numeric correctness, citation existence, source support and abstention. State the small sample and the replay/holdout limitation. CI uses a labeled fake model, while real inference is a separate recorded run.

## Questions to expect

**Why Apple, Dell and HP?** Official sources were accessible; Apple provides clear annual cash-flow and income facts suitable for an educational DCF. The peers add hardware operating comparisons but differ in services, infrastructure, financing and printing. Their fiscal calendars are not aligned, so this is not a controlled relative-valuation study.

**What stops hallucinations?** Evidence restriction, deterministic financial tools, bounded context, explicit abstention and structural checks reduce risk. They do not guarantee entailment. The evaluation and UI expose this limitation; the first smoke run and unsupported tax claim were retained as failures.

**What did the model actually run on?** Pinned Qwen2.5 1.5B 4-bit MLX, on an M1 with 8 GB RAM. Embeddings use pinned MiniLM ONNX locally. Quote measured timings from the result files rather than remembered estimates. No fine-tuning, paid inference or hosted-model transfer occurred.

**How would you improve it next?** Review the measured failure categories first. Better relevance labels and independent claim-support review may be more valuable than a bigger architecture. A larger model, constrained JSON decoder, better chunk boundaries or an evidence reranker would need an explicit resource/license check and a fresh held-out evaluation.

**What is the most important financial simplification?** Constant operating ratios after revenue growth, an assumed operating NWC ratio, no tax-loss carryforwards, no leases/acquisitions and no enterprise-to-equity bridge. Terminal value is often dominant. It is a transparent scenario, not a price target.

## Guided change to implement yourself

Add an optional **mid-year discount convention** while preserving the current year-end default. Budget: about 60–90 minutes.

1. Add a typed `discount_convention` enum to `DCFInput` (`year_end` / `mid_year`). Reject unknown values.
2. For forecast cash flows only, use exponent `t - 0.5` in mid-year mode. Define the terminal value as end-of-year five and continue discounting it five years. Explain this convention explicitly; do not blindly shift every exponent.
3. Independently compute the one-year check: a USD15 forecast FCFF at 10% has PV = `15 / sqrt(1.10)` in mid-year mode, versus `15 / 1.10` in year-end mode. Test that terminal PV is unchanged for otherwise identical assumptions.
4. Add an accessible UI selector that sends the enum to the API. Do not calculate finance in TypeScript.
5. Include the convention in the PDF assumption table. Extend the API/PDF test so the two exports identify the different conventions and forecast PVs.
6. Run Ruff, Pytest on the dedicated PostgreSQL test database, TypeScript and the browser journey. Add a short explanation of why enterprise value changes.

This exercise is deliberately left for the repository owner. Being able to explain and verify the change is more valuable than memorizing the existing implementation.
