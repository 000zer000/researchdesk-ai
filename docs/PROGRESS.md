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

Before writing any new cases, a final period-boundary review found that compact `FY2024` notation was not recognized consistently by the old bare-year regex. Added one shared year parser across scope, retrieval and finance, plus five regressions including unavailable FY2025. This supersedes the first correction commit before any new batch execution; no consumed batch is being called fresh. The final native suite passes 94 tests without skips.

The last pre-batch definition check made unsupported net/adjusted definitions unconditional: an unrelated occurrence of “gross” cannot authorize them. Three additional regression variants pass. The definitive correction suite is 97 tests, zero skipped. New evaluation cases are written only after the following code commit.

## Consumed first v1.1 evaluation and period correction

The first new 31-question batch completed on frozen commit `f009015`. It is retained, including ten pending review responses, complete outputs and checksums. It exposed a false calendar comparison: Dell FY2023 and FY2024 were said to have equal week counts despite source evidence of 53 and 52. Financial reference-answer coverage was only 5/15; strict validation rejected many model proposals. Qualitative responses often remained generic. No success target or inferred semantic-support score is claimed.

Corrected the calendar route generally using verified inclusive fiscal dates and deterministic whole-week/change contracts. Added comparison wording variants, wrong-direction refusal and non-week-calendar tests. The consumed Q18 is a labeled regression replay. The first batch's simple answered-status behavior metric did not detect its false substance; that limitation is published explicitly. The next batch must be distinct and frozen after this correction, rather than rerunning old questions and calling them new.

The consumed batch also exposed a wording refusal on plural “capital expenditures.” Before writing the second batch, generalized financial label morphology (margins, profits, cash flows and expenditures) and added plural regressions. This changes rules across metrics, not individual question IDs. The final native suite passes 106 tests without skips.

The second distinct 25-question batch completed on frozen correction commit `90e484e`. It produced 12 answered, six financial conclusions withheld, five abstentions and two source-conflict refusals. Seven of thirteen financial/calendar reference targets were answered correctly; the others remain unanswered. Both new two-period week comparisons were correct. Currency and segment fixtures resolved the ledger but their model proposals were still rejected. Generic prose remains a published limitation, not an invented support score. Prepared ten prespecified actual responses with all human-review fields pending. Runtime/result/source hashes and both historical archives validate. No runtime changes follow this batch.

Final frozen-runtime Chromium verification passed all three journeys, including two actual-model calls and the separately labeled simulated conflict display. Full source/answer fingerprints and ten pending review responses validate. Publishing these measured limitations with the release; deterministic CI is not presented as AI-quality validation.


## v1.2 — diagnosis and result-path separation

The six archived v1.1 blocked cases have resolved ledger data and no plan issues. Original raw proposals were not retained. An explicitly labeled instrumented replay on immutable v1.1 source reproduces malformed/truncated JSON (N04/N08/N11/N23) and nested mappings instead of assertion objects (N09/N24). This diagnoses the model-copy gate, not missing data or retrieval; replay outputs are retained without claiming they are the original raw responses. Qualitative diagnosis separates wrong-topic retrieval, three-passage context loss, incomplete 220-character slices, generic generation and citation identity from semantic support. See V12_DIAGNOSIS.md.

Implemented a typed financial request with bounded operations and server-authored execution through the existing finance engine. Valid calculations no longer require model authorization. Ambiguities, unsupported definitions/units/scopes and unresolved conflicts remain explicit. Output includes formulas, input records, units, dates and sources. Optional AI explanations have separate status and failure handling. The model and free local inference target are unchanged; this is an architecture correction, not improved numerical reasoning by the LLM.

Context development compares legacy fragments, complete sentences, and deduplicated neighboring context under a 2,400-token input limit (including reserved chat overhead), 650 output tokens, and the existing 90-second total inference bound. Actual selected sentences, omissions, context hashes and raw generated outputs are retained. Human semantic review remains pending. Historical v1.1 source hashes are checked against the immutable tag rather than incorrectly comparing them to v1.2 source.

Development retained three failed/limited explanation protocols before the final context comparison: long sentence IDs were copied as text; a short-ID JSON-only prompt caused false abstentions; a simple labeled-bullet protocol produced real claims but still exposed fragment/citation failures. These executions are all retained and are development replays, not independent final tests. No model upgrade was used.

Direct source inspection found that the key HP digitization disclosure starts at the end of one passage and continues in the next. Dropping incomplete sentences separately therefore removed the relevant evidence. Context windows now join only adjacent same-document offsets separated by exactly one normalized whitespace, and bind each sentence to every exact source fragment/offset. Rarer query-term anchors recover continuations lacking the earlier topic noun. This is a retrieval/context correction, not a generation-quality claim by itself.

## 2026-11-01 — measured local model trial and pre-final checks

After the architecture and context fixes, compared the old 1.5B model with a reviewed Apache-2.0 pinned Qwen3 4B quantization on consumed development questions. The first 4B setup omitted its external chat template and failed without inference; the first actual trial formatted all answers but invented covenant conditions. Both are preserved. A global source-only prompt revision reduced those details on the same declared development replay; residual inference/labeling concerns remain. Selected 4B for formatting reliability under the measured local budget, not as a cure for all defects. See V12_DEVELOPMENT.md and raw runs. Earlier journal statements that the model was unchanged describe the preceding architecture-only phase.

The same 12-case development batch produced eight answers with v1.2, versus six with immutable v1.1; two formerly withheld calculations now bypass inference. This is not a numerical-reasoning gain. Native PostgreSQL suite: 135 passed without skips before the final cache-model guard test; that guard's three provider tests also pass. Chromium mock mode: three journeys pass, including optional AI transport failure after editing the question. The independent inline-XBRL parser verifies 48/48 original facts. Final cases have not yet been executed.

## v1.2 consumed first final batch — preserved defects

The first frozen 25-case batch is preserved unchanged in `attempt-01/` and its timestamped run. It answered 13/16 answerable questions, with three false documentary refusals and no false acceptance. Raw numeric matching was 7/10. Investigation distinguishes a real request error from evaluator mistakes: “grow in percentage terms” selected monetary change; two HP references incorrectly assumed 2023 capex of 593 million, while the source-verified observation is 609 million. The displayed proxy change of 195 and capex growth of approximately −2.79% were consistent with that original observation. No reference is silently edited in the consumed batch.

Generalized percentage-growth grammar; separated one-period source comparison from temporal comparison; expanded documentary capability terms for trade restrictions, inventory/customization and third-party software. Added eight wording/decision regressions, not question-ID rules. Corrected the old live browser assertion's v1.1 origin label. All 144 native PostgreSQL tests pass, zero skipped; three mock Chromium journeys pass. Known failing questions are explicitly replayed as diagnostics only. A distinct final batch is authored after the following correction commit. No favorable prior attempt is substituted for its first execution.

## 2026-11-01 — final measured quality and actual delivery journey

The distinct post-correction final batch ran once on frozen source: 15/16 answerable questions accepted, 10/10 accepted financial reference targets correct, one false explanation refusal, no false acceptances, two unresolved structured conflicts withheld with both proofs. This is not an aggregate success score. Coding-agent source review found six fully supported, two partial and two unsupported generated claims; only four of sixteen predeclared explanation aspects were fully covered, two partial and ten missing. The ten human forms remain entirely pending. Narrative completeness/entailment are still insufficient; no further tuning follows the final batch.

All four real-mode Chromium journeys pass, including actual generation, evidence, changed WACC/PDF and real deterministic financial display. Fault-injection/conflict display tests remain explicitly simulated. Three PDF pages render cleanly and contain the changed 12% scenario. The initial bundled renderer had invalid Fontconfig paths; a workspace-local cache/config fixed rendering without changing the app. The recording's first hidden-mobile selector and second rapid-switch/wait failure were capture defects; a real settled-state rehearsal answered in 29.76 seconds. The third completed take had a full-page-screenshot video-resize artifact, found by frame inspection; a viewport-only capture replaces it. All recording attempts and actual calls are declared separately from final evaluation.

Final take 4 passed visual QA at sampled frames, with viewport-only capture. Actual recorded Dell generation took 26.56 seconds. Delivered WebM is 90.00 seconds, 1440×1000, VP9/25 fps, stream-copied without acceleration. Latest three-page PDF was re-rendered and inspected after this take; the 12% scenario is present. Media hashes and the recording-only helper hash are published. Frozen product/evaluation source hashes remain unchanged.


## 1 November 2026 — documentary source excerpts and bounded coverage

Added a clearly distinct verbatim source mode with zero model calls and fragment
identity validation, plus budgeted topic/context selection and visible response-mode
labels. Preserved deterministic financial execution and all v1.2 outputs. The first
development replay and subsequent context-only inspection are retained. The frozen
v1.3 eight-case acceptance run produced two correct accepted financial targets,
one out-of-scope working-capital refusal, five excerpt responses and three accepted
generated documentary responses. Excess/repeated model citations caused two format
rejections; accepted prose still contains unsupported elaboration/irrelevance.
Human review is zero of five new packets, with prior reviews also pending.

149 native tests and four mock Chromium journeys pass, plus build/lint/format.
The generated/extractive modes and numerical results have distinct origins. Source
excerpts are an inspectable browsing mode, not a claim of improved AI synthesis.
Detailed measurements, scope/reference mistakes and limitations are published in
V13_VERIFICATION.md. No historical source/results were overwritten.


The frozen source is now anchored at 21a22f9. After consuming the batch, corrected
duplicate citation-label counting and the visible version badge. The final native
suite passes 152 tests. Deterministic replay accepts the prior V308 formatting but
still rejects V305 for too many distinct sources. No new model-quality score is
inferred; original outputs and first-run metrics remain untouched.
