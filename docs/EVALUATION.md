# Evaluation v1.1

v1.0 is preserved byte-for-byte under `evaluation/v1.0/`, including failed attempts, its final **replay** set, coding-agent source assessments and original runtime hashes. [Historical methodology and failures](v1.0-EVALUATION.md) remain available. They must not be relabeled as a new holdout or compared directly with a different batch.

The v1.1 corrections are frozen in a code commit **before** the new cases are written. `evaluation/v1.1/freeze.json` binds that commit, runtime and test source hashes, case hash and creation time. Expected values and source references are evaluator-only data; generation receives the ordinary application context. The application does expose verified measures to its model by design, so numeric results demonstrate guarded pipeline consistency, not independent model arithmetic.

The batch is coding-agent-authored on a known corpus, not an independently authored blind benchmark. Exact questions are checked against v1.0 to prevent exact replay. Topic and financial concepts necessarily overlap the supported product scope. Ten cases are selected for human review before inference. A second execution, even after an incomplete attempt, is labeled a replay and stored in a new run directory.

Metrics are separate: accepted reference financial measures, unanswered/withheld responses, expected behavior, curated reference-passage recall, and the narrow injection-marker probe. No aggregate score or target is used. Financial refusals do not count as correct numeric answers. Quote presence does not establish semantic support. Qualitative completeness and citation entailment await human review.

Synthetic conflicts copy one real observation into a disposable `_test` schema and add an explicitly synthetic source. Variants distinguish altered values, periods, concepts, reporting bases, currencies, segments and companies. These are not claims that the six official reports contain genuine financial contradictions. They never modify the demo corpus.

The actual run, failures, source excerpts and ten pending review responses will be linked here after execution; an unexecuted check is not counted as passed.
