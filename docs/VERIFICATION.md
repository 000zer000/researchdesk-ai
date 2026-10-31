# Verification ledger

The application is delivered as a local research prototype with measured model limitations. Configuration files and test doubles are not counted as real inference.

| Check | Verified result / evidence |
|---|---|
| Official source access and repeat import | Six original SEC 10-Ks, 2,851 passages, 48 facts; repeat cached import retained those counts |
| Original financial values | All 48 facts matched original inline XBRL with exact context dates, consolidated scope, USD unit, scale and sign; `evaluation/financial-source-checks.json` |
| Native PostgreSQL and business/API tests | **52 passed, 0 skipped, 0 failed** on the dedicated test database; `evaluation/local-verification.json` |
| Native real-data persistence | Same six documents/48 facts and fact-value digest after restart and migration reapplication; `evaluation/native-persistence.json` |
| DCF and ratios | Independent perpetuity identity, year-one/year-five discount periods, working capital, year-six terminal cash flow, tax treatment, sensitivity, invalid inputs and missing data tested |
| Real local model | Pinned Qwen 1.5B MLX on Apple M1/8 GB; complete 80-case lexical/hybrid comparison, 64 research cases invoking the model, 16 deterministic refusals; `evaluation/results.json` |
| Repeated real HTTP requests | Three successful generations and evidence opens on the same corrected Uvicorn process, followed by an explicit no-inference scope refusal; `evaluation/service-smoke.json` |
| Chromium with simulated model | Passed; explicit test-double narrative, real API finance/PDF and a separate synthetic-fixture database |
| Chromium with real model | Passed after the three real HTTP requests: company, actual generated answer, citation, discount-rate change, PDF download, mobile company choice, publication filter and stale-data clearing on service error |
| TypeScript / production build / Python style | TypeScript, Vite build, Ruff check and format check passed |
| Desktop/mobile and PDF visual review | Actual screenshots inspected; all three latest PDF pages inspected without clipping or overlapping content; `docs/demo/` |
| Demonstration | Actual 23.68-second Chromium recording, no mocked network routes; model-call metadata in `docs/demo/recording.json`; exported scenario independently confirmed to contain 12% discount rate |
| Clean Docker Compose | Local Docker unavailable; Linux GitHub Actions built from clean source, migrated, imported an original synthetic fixture and verified persistence after restart. This does not claim containerized real-model inference. |
| Public repository / release CI | Repository is public. The release process requires the latest commit's PostgreSQL/browser and clean-Compose jobs to be green; immutable commit/run URLs are included in the release notes. |

The evaluated research/finance runtime is fingerprinted in `evaluation/runtime-source-hashes.json`. The validator checks both these source hashes and the correspondence between every displayed answer and its source-review annotations. Additional delivery evidence and documentation do not silently change the evaluated runtime.

The first API smoke passed but a later request exposed a thread-affine MLX stream error. The adapter was corrected to keep import, loading, generation and cache cleanup on one persistent owner thread. Three distinct caller threads, repeated HTTP requests, a fresh full evaluation and the final browser/recording runs verify that correction. The initial failure is retained in the progress journal.

## Remaining limitations and non-executed work

- The final set is a **replay**, not a pristine holdout. Independent human review of reference answers and citation support has not been performed.
- Generated prose remains fallible: operating-margin direction, capex definitions, citation support, generic answers and conflict handling can fail. See the complete failures in `EVALUATION.md`; deterministic financial tables/DCF are a separate layer.
- There is **no hosted interactive AI demo**. The tested local run and actual recording are the delivery path; the release does not imply a remote working model.
- Linux local-HTTP model adapters are supported by configuration but were not used for the published MLX evaluation. No hosted model calls, paid inference, uploads or public administrative ingestion were executed.

No access or payment intervention is required to use the delivered current-Mac workspace. Fresh machines must install the documented free dependencies and retrieve official sources with their own identified client. The independent human review above remains a deliberate review task, not a completed validation.
