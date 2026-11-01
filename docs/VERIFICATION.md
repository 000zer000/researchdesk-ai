# Verification v1.2

Runtime correction commit: `99edbef`. Final question seal: `5c47ef6`. [Evaluation](EVALUATION.md) separates source identity, numerical targets, semantic support, completeness and refusals. [Historical v1.1 checks](v1.1-VERIFICATION.md) remain available.

Completed locally on the target 8 GiB M1 Mac:

- Ruff check and format check pass; TypeScript/Vite production build passes.
- **144 Pytest tests pass, zero skipped**, on native PostgreSQL 17 in isolated `_test` schemas. Demo data are not reset. One upstream Starlette/httpx deprecation warning remains.
- **3 Chromium mock-mode journeys pass**: full scenario/evidence/PDF journey, synthetic conflicting-proof display, and optional AI transport failure after editing the form question. Test doubles are explicit.
- **4 Chromium live-mode journeys pass** on the real-data API: actual local generated research and source inspection, scenario change and PDF, real deterministic financial display, plus the separately labeled simulated conflict/transport-failure tests. “Live mode” does not turn the latter simulated fault injections into real source conflicts.
- **48/48 original financial facts** match a separate inline-XBRL parser's exact concept, annual/instant dates, consolidated context, USD unit, scale, sign and value.
- Historical v1.0 and v1.1 archive validation passes; final v1.2 case/source/result hashes, model revision, token budgets and ten pending human-review records validate.
- The first execution of the final distinct 25-case batch is retained, including a failed explanation and rejected optional prose. Its limitations are published; this is not an aggregate quality pass.

The recorded demonstration and PDF rendering checks are documented with actual receipts under `docs/demo/v1.2/`. GitHub CI and release receipts are linked from the release notes after completion. A green deterministic build is not independent AI validation.
