# Evaluation v1.1

v1.0 is preserved byte-for-byte under `evaluation/v1.0/`, including failed attempts, its final **replay** set, coding-agent source assessments and original runtime hashes. [Historical methodology and failures](v1.0-EVALUATION.md) remain available. They must not be relabeled as a new holdout or compared directly with a different batch.

The v1.1 corrections are frozen in a code commit **before** the new cases are written. `evaluation/v1.1/freeze.json` binds that commit, runtime and test source hashes, case hash and creation time. Expected values and source references are evaluator-only data; generation receives the ordinary application context. The application does expose verified measures to its model by design, so numeric results demonstrate guarded pipeline consistency, not independent model arithmetic.

The batch is coding-agent-authored on a known corpus, not an independently authored blind benchmark. Exact questions are checked against v1.0 to prevent exact replay. Topic and financial concepts necessarily overlap the supported product scope. Ten cases are selected for human review before inference. A second execution, even after an incomplete attempt, is labeled a replay and stored in a new run directory.

Metrics are separate: accepted reference financial measures, unanswered/withheld responses, expected behavior, curated reference-passage recall, and the narrow injection-marker probe. No aggregate score or target is used. Financial refusals do not count as correct numeric answers. Quote presence does not establish semantic support. Qualitative completeness and citation entailment await human review.

Synthetic conflicts copy one real observation into a disposable `_test` schema and add an explicitly synthetic source. Variants distinguish altered values, periods, concepts, reporting bases, currencies, segments and companies. These are not claims that the six official reports contain genuine financial contradictions. They never modify the demo corpus.

The actual run, failures, source excerpts and ten pending review responses will be linked here after execution; an unexecuted check is not counted as passed.

## Consumed first v1.1 batch: retained failure, not the final runtime

The first post-correction batch ran 31 questions on commit `f009015`. Its [cases and freeze](../evaluation/v1.1/attempt-01/) and [complete results](../evaluation/v1.1/runs/20261031T122309885153Z/results.json) remain unchanged. It produced 12 `answered`, 8 withheld financial conclusions, 7 abstentions and 4 source-conflict refusals. Only **5/15** reference financial measures were answered and correct; abstentions are unanswered, not numeric successes. All four synthetic ambiguous sources withheld conclusions, while two of three distinct-context cases were still rejected by the model contract despite correctly resolved ledger data.

A coding-agent diagnosis found a substantive false answer in Q18: “equal week counts” contradicted the cited Dell disclosure of 53 and 52 weeks. Several qualitative answers were generic restatements rather than complete explanations. These are not passed semantic-support checks. The old mechanical `expected_behavior_met` count of 22/31 is **not a quality score**: it counted Q18's answered status without validating its substance. F10 also has a predeclared conservative refusal expectation despite asking for an otherwise valid CFO-minus-capex operation with negated net-capex wording; its numeric outcome correctly remains unanswered. No claim of improved semantic accuracy is drawn from this metric.

The period defect was corrected generally: reporting-week comparisons now use inclusive verified fiscal dates, company/period/basis checks and the same model-proposal contract. Non-whole-week periods do not receive an assumed 52-week calendar. The Q18 replay is explicitly [a known regression](../evaluation/v1.1/calendar-replay-regression.json), not a fresh test. A distinct second batch is written only after the new correction commit and is checked for exact overlap with both earlier batches.
