# Progress journal

## 2026-10-30 — inspection and source selection

Read the full delivery brief. Created an isolated `researchdesk-ai` checkout, without modifying neighboring projects. Verified the authenticated personal GitHub account as `000zer000`; the target repository did not exist. Host: Apple M1, 8 GB RAM. Docker is unavailable locally; PostgreSQL binaries bundled in DBngin were copied into task-local work storage, with an isolated port and separate demo/test databases. No existing DBngin data was used.

Checked SEC API/fair-access documentation. All six official reports and three Company Facts responses downloaded successfully with an identified, throttled client. Selected Apple, Dell and HP after source inspection. Downloaded reviewed Apache-2.0 model snapshots locally, with no paid inference or hosted-provider calls.

## Vertical slice and measured failure

Implemented parsing, provenance, PostgreSQL lexical search, ONNX MiniLM embeddings, reciprocal-rank fusion and Qwen/MLX generation. The first actual response was structurally valid but unhelpful: it repeated report footers. This was not counted as success. Removed repeated footer blocks, normalized search terms and filtered explicit fiscal years. The second live response addressed supply-chain risks, but included a tax claim not supported by its cited supply-chain passage. This motivates distinct citation-support evaluation; ID validation alone is insufficient.

## Finance, interface and export

Implemented original-accession financial facts, deterministic ratios, Decimal five-year FCFF/terminal valuation, sensitivity, typed API endpoints, React research/evidence/valuation/source spaces and a three-page ReportLab export. Source checks confirmed HP's different capex concept; added an explicit company-specific mapping. Inspected all three rendered PDF pages. First PostgreSQL test run: 28 pass / 1 fail from whitespace in a PDF-text assertion. Corrected the assertion's whitespace normalization; 29 pass / 0 skipped on the next native PostgreSQL run.

## Evaluation and delivery

Frozen 40 cases with 20 development / 20 final questions before the full real-model run. Conflict and injection cases are explicitly synthetic perturbations of real retrieved context. Final results, independent inline-XBRL checks, browser evidence, CI runs and release are recorded in the evaluation and verification documents after execution. No model-quality threshold is assumed in advance.

The first comparison revealed repeated structured-output failures (objects in the `limitations` string array). Stopped the partial attempt and retained its results. Added one bounded model-generated structure repair, with both attempts' tokens recorded and a shared remaining time budget. This affects the interpretation of the final split: it is now a replay set, not an untouched holdout. Added a dedicated simulated test of repair bounds and token aggregation. A browser assertion also needed to account for the unit being rendered inside the same metric element as the number.

Development checks also exposed a factor-of-ten raw-USD copying error. Normalized structured-fact presentation in the model context to USD millions using code; original source evidence remains unchanged. A concise single-claim response on the development risk question avoided the earlier tax extrapolation. The first full GitHub Actions run passed PostgreSQL/Chromium and clean Compose persistence checks. Desktop/mobile screenshots were visually inspected; the mobile company picker was added after inspection revealed that the desktop-only sidebar hid company selection.

The next comparison completed all lexical cases and 32 hybrid cases before the evaluator exposed an empty-publication-window bug. Preserved that incomplete run. Its failures included a fabricated USD150 closing price, a historical revenue presented as guaranteed future revenue, and Apple's revenue attributed to another company. Added a conservative deterministic capability gate for unsupported prices/forecasts/monthly data/private topics and explicit mismatched question subjects. Refusals are labeled as policy decisions, not credited to LLM reasoning. Empty hybrid retrieval now returns no evidence when no document is available, while still raising a setup error if documents lack embeddings. These corrections further weaken any held-out interpretation; the final set is a replay.

The first complete 80-record comparison exposed a false-positive in the new subject heuristic: a phrase such as 'What does the evidence say about Apple's revenue?' was misread as an unrelated company name. Preserved the complete attempt and its summary, fixed the subject boundary, and added three regression cases. Re-running the complete comparison after this correction avoids reporting accidental policy refusals as successful conflict handling. No further model-quality tuning is planned for V1; remaining narrative failures will be published.

## 2026-10-31 — repeated-request verification and delivery

The first real-model Chromium journey passed, but the next recording request returned 503. A controlled two-caller reproduction showed `RuntimeError: There is no Stream(gpu, 0) in current thread`: the pinned MLX-LM runtime creates a stream on its importing thread, while FastAPI can dispatch later requests to another worker. Moved MLX imports, model loading and all generation onto one persistent owner thread, retaining the concurrency gate and time/token bounds. Added owner-thread/busy regressions and API error logging without exposing internal details to the browser. Re-running real inference and the full comparison after this execution fix; prompts, financial formulas and reference answers are unchanged.

The corrected adapter passed three real generations from distinct caller threads and all 52 deterministic/native-PostgreSQL tests without skips. A fresh complete 80-record comparison produced identical answer bodies to the preceding run; annotations are answer-hash-bound and runtime fingerprints now identify the corrected evaluated commit. Three actual HTTP research requests on one Uvicorn process then succeeded, followed by a successful real-model Chromium journey and a 23.68-second actual recording. The PDF exported in the recording contains the changed 12% discount rate. Latest mobile/desktop screens and all three PDF pages were visually inspected. The delivered local launcher was startup-tested on port 8008 without downloading dependencies or changing another project.


## 2026-10-31 — v1.1 correction phase (before new batch)

Archived all v1.0 evaluation JSON byte-for-byte with checksums. Added provenance-aware resolution instead of last-write-wins, explicit reporting-basis fields/migration, deterministic financial measure contracts and complete-input citation validation. Regressions vary values, units, directions, companies, scopes, periods, definitions, duplicates, revision bases and wording. Ambiguous eligible observations retain both proofs and refuse conclusions. Other-company, segment and currency observations are distinguished instead of falsely compared.

Development inference initially failed JSON shape and exact-quote copying. Those failures were not credited as answers. A narrowly bounded missing-root-brace normalization preserves all generated values; other malformed proposals get one structure repair. Prose now selects preidentified source slices; the server binds exact quotes. General topic expansion/specificity reranking targets observed wrong-section retrieval. Small-model generic prose and weak semantic support remain known limitations; exact span existence is not reported as entailment.

New period-provenance checks exposed an old numeric unit fixture missing dates and concepts; updated that explicit test fixture and fail closed on absent metadata. Native tests then passed 89/89 without skips. Chromium exposed the old CI fixture's `synthetic` scope, correctly excluded by the new consolidated filter; the synthetic fixture now explicitly simulates consolidated scope while remaining labeled synthetic in all provenance. Browser assertion text and package version editing were corrected before freezing. The independent inline-XBRL parser reverified all 48 real financial facts. No new final batch has run at this point.

Final pre-freeze review added single-company output scoping, subtraction wording variants and reporting-basis compatibility across derived inputs. No further quality tuning is permitted after the fresh batch begins; any later runtime correction requires preserving the consumed attempt and explicitly labeling replays.
