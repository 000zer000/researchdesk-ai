# ResearchDesk contributor instructions

- Work only inside this repository. Never edit neighboring projects or databases.
- Product, documentation, reports and commits use English.
- Never substitute a mock or authored answer for real inference. Label all test doubles.
- No hosted model calls, paid services, secrets in source, arbitrary model-written tools, or public document ingestion.
- Use original annual accession + annual/instant context + USD + consolidated scope. Never silently take the newest Company Facts record.
- Keep finance in `src/researchdesk/finance.py`. The frontend only presents API results.
- Run Ruff, TypeScript, Pytest with native PostgreSQL, and Playwright for changed user journeys.
- Integration tests require a database ending `_test`. Missing PostgreSQL must fail, not skip. Never reset the demo database from tests.
- Keep raw SEC files, full report text, model weights, personal `.env` and runtime paths ignored.
- Freeze evaluation cases before final inference. Report citation existence separately from source support; never call coding-agent review independent human validation.
- Record substantive changes and measured failures in `docs/PROGRESS.md`. Do not force-push.
