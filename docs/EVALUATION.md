# Evaluation v1.2

The released runtime is frozen at correction commit `99edbef`; the distinct final question seal is committed at `5c47ef6`, before any final inference. [Cases](../evaluation/v1.2/final-cases.json), [seal](../evaluation/v1.2/final-freeze.json), [actual first execution](../evaluation/v1.2/runs/20261101T003024066201Z/results.json) and [mechanical summary](../evaluation/v1.2/summary.json) are public. No quality tuning follows this run.

This is a coding-agent-authored batch on a familiar six-report corpus, not independent or blind. Exact questions differ from v1.0, both v1.1 attempts, development, and the consumed first v1.2 batch. Financial concepts and disclosure topics overlap prior work. Expected values/aspects are evaluator-only data and never enter prompts. Ten review IDs were selected before inference. Additional executions are labeled replays, not independent tests.

## Historical and consumed results

[v1.0](v1.0-EVALUATION.md) and [v1.1](v1.1-EVALUATION.md) remain separately documented and byte-preserved. The [six-blocker diagnosis](V12_DIAGNOSIS.md) distinguishes valid financial data from failed model-copy formatting; original raw v1.1 proposals were unavailable, so instrumented replay causes are not asserted as original raw causes.

[Development experiments](V12_DEVELOPMENT.md) retain unsuccessful JSON protocols, source truncation, all context/model trials, the first 4B hallucinations, and immutable v1.1 versus v1.2 on the same 12 questions. Baseline financial mode requires an actual model proposal; v1.2 directly executes a validated request. Prose changes model, prompt and context, so no single-component causal claim is made.

The consumed [first v1.2 batch](../evaluation/v1.2/attempt-01/) remains unchanged with its first-run outputs. It answered 13/16 answerable questions, falsely refused three documentary questions, and matched 7/10 financial references. One real intent defect selected amount change for percentage growth. Two evaluator references incorrectly assumed HP FY2023 capex of 593 rather than the source-verified 609; the displayed proxy change and capex-growth computations were consistent with 609. These reference errors are disclosed, not silently rescored into the raw summary. A source-comparison question also stopped at temporal clarification instead of displaying both conflict proofs.

General wording, documentary gating and source-versus-time comparison rules were corrected and regression-tested. The old questions were replayed explicitly as diagnostics; they are not the new final batch. A pre-inference reference-index correction is also retained under `preflight-01/`, with no inference performed on that seal.

## Final distinct batch: actual measurements

| Measurement | Observed result | Meaning |
| --- | --- | --- |
| Answerable coverage | **15/16** | 10 financial/context questions and five of six document explanations accepted |
| Accepted financial reference accuracy | **10/10** | Value, unit and direction match predeclared requested targets; not LLM arithmetic |
| False refusals | **1/16 answerable** | R10 acquisition integration failed context/generation/validation |
| False acceptances | **0/9 unanswerable** | Under this batch's definitions only |
| Ambiguities / absent data | 4 clarification requests / 3 abstentions | No invented years, FX conversion, definitions or missing facts |
| Incompatible structured contexts | **2/2** source conflicts with both proofs | Synthetic value/period variants, not alleged contradictions in official reports |
| Distinct currency / segment contexts | **2/2** accepted correct consolidated USD targets | Different observations do not replace the selected scope |
| Generated claim support, coding-agent assessment | **6 supported, 2 partial, 2 unsupported**, out of 10 accepted claims | Not independent human review; partial is not full support |
| Reference-aspect completeness, coding-agent assessment | **4 covered, 2 partial, 10 missing**, out of 16 aspects | Includes the refused explanation; compound aspects use strict full coverage |
| Human review | **0/10 completed** | [Actual preselected responses, excerpts and blank judgment grid](../evaluation/v1.2/human-review.md) |

These are separate measurements, not an overall score. Financial accuracy is conditional on a bounded request being correctly understood. Schema validation does not guarantee a free-text parser always recognizes the user's intended operation. The consumed percentage error demonstrates this limit.

[Claim-by-claim assessment](../evaluation/v1.2/coding-agent-review.json) binds judgments to actual answer hashes. R09 conflates post-launch inventory filling with pre-launch decline of older inventory. R11 omits distributor overordering/canceling/delaying. R12 omits compliance costs and penalties. R13 adds an unsupported quality/timing interpretation. R14 adds unsupported trade-secret implications and misses key licensing-term risks. These remain published defects, not passed checks.

R10 retrieved the right acquisition paragraph, but selected only its partner sentence alongside unrelated cybersecurity context. The model incorrectly said the sources could not answer; its literal evidence marker in the refusal then triggered numeric-prose validation. This is a combined context/generation/validation failure, not missing disclosure. R03's optional AI explanation was rejected while the valid operating-margin result remained available.

## Actual context and performance on the target Mac

[Mac measurements](../evaluation/v1.2/mac-performance.json) record Apple M1, 8 GiB RAM, macOS 26.0.1, Python 3.12.14, pinned local Qwen3 4B / MLX. The hard budgets are 2,400 input tokens including reserved template overhead, 650 output tokens, 90 seconds per generation workflow, and a 5 GiB operational process-RSS ceiling. Final maximum actual call input/output was 2,067 / 82 tokens. Twelve calls include format repair; no undisclosed best answer is selected.

Nine financial requests without optional AI: median **0.0032 s**, p95 **0.0608 s**, measured inside the server workflow, excluding HTTP/browser overhead. Six qualitative requests including failure/repair: median **11.75 s**, p95 **13.43 s**. The optional R03 request took **32.13 s** including cold setup and rejected prose; its correct financial result was retained. Browser optional prose is requested after showing the calculation. Process peak RSS was **863.7 MiB**; MLX allocator peak **2,991.8 MiB**. They overlap and must not be added; this is not total system memory-pressure measurement.

Curated reference-passage recall averaged 0.917 both in search and actual generation on six explanations, but this is passage identity only. R10/R12/R13 show why it does not prove the essential sentences survived four-sentence packing. Actual transmitted sentences, omitted candidates, provenance fragments and hashes are retained per response. Context assembly is improved over short three-passage fragments, but the four-sentence selection still loses important aspects. No automatic semantic-entailment metric is inferred from citation matches.

Synthetic conflicts use disposable schemas on the dedicated `_test` PostgreSQL database; the demo corpus is untouched. Independent inline-XBRL parsing rechecks all **48/48** original financial observations. CI uses clearly labeled provider doubles and original synthetic data; it proves neither model quality nor independent review.

The later scripted browser recording is a consumed-development demonstration, not an additional final test. Its declared rehearsal took 29.76 seconds for the Dell explanation; final-take timing and response are in `docs/demo/v1.2/recording.json`. Model weights may be warm, but answers are generated on each request. Recording failures and the visual-QA replacement are retained separately. No replayed demonstration response is selected as a new evaluation result.
