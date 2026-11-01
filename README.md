# ResearchDesk

**Evidence before opinion.** A local research workspace for original Apple, Dell and HP FY2023–FY2024 annual filings, verified financial calculations and a transparent five-year DCF.

ResearchDesk combines FastAPI, PostgreSQL, React/TypeScript, local MiniLM retrieval and actual Qwen/MLX generation. Publication-date filtering, original accessions and exact annual/instant contexts keep financial provenance inspectable. No paid model endpoint, public ingestion or trading feed is used.

**v1.2 separates verified calculations from optional AI text.** A bounded typed request specifies company, metric, period, unit, scope, definition and allowed operation. The existing server finance engine returns the result, formula, complete inputs and sources. A language model no longer has to copy verified results before they can be displayed. Optional generation can fail without hiding valid arithmetic. This is an architecture improvement, **not improved LLM numerical reasoning**.

[Watch the actual 90-second walkthrough](https://github.com/000zer000/researchdesk-ai/releases/tag/v1.2.0) · [Technical interview guide](docs/TECHNICAL_GUIDE.md) · [Evaluation and retained failures](docs/EVALUATION.md) · [Ten pending human-review responses](evaluation/v1.2/human-review.md)

![Actual v1.2 verified calculation and original evidence](docs/demo/v1.2/financial-evidence.png)

**Final distinct batch:** 15/16 answerable questions accepted; 10/10 accepted financial targets matched; one explanation falsely refused. Both ambiguous structured-source fixtures withheld conclusions with both proofs. These are narrow pipeline measurements, not an overall quality score.

**Narrative quality remains insufficient for unattended use.** Coding-agent source inspection of ten accepted generated claims found six fully supported, two partial and two unsupported. Only four of sixteen predeclared explanation aspects were fully covered. That assessment is not independent human review; all ten human-review forms remain pending. The first consumed v1.2 batch, reference mistakes, malformed outputs and initial model hallucinations are preserved. See [measured limitations](docs/EVALUATION.md).

## Run locally

Verified real-inference target: Apple M1, 8 GiB RAM, macOS, Python 3.12. Default: pinned Apache-2.0 Qwen3 4B MLX 4-bit, approximately 2.28 GB public snapshot. No card/API key is required. Internet is needed for first source/model downloads; subsequent research uses local cached data and inference.

```bash
git clone https://github.com/000zer000/researchdesk-ai.git
cd researchdesk-ai
cp .env.example .env
# Edit SEC_USER_AGENT with your real name/contact. Keep .env private.
uv sync --frozen --all-extras
docker compose up -d db
uv run alembic upgrade head
HF_HUB_DISABLE_XET=1 uv run researchdesk models
uv run researchdesk ingest
cd frontend && npm ci && npm run build && cd ..
uv run uvicorn researchdesk.api:app --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000
```

Native PostgreSQL 17 is also verified. Use an isolated `researchdesk` database and set `DATABASE_URL`, never another project's database. Ingestion is idempotent, identified, cached and rate limited; changed pinned documents or access denials stop acquisition. Full reports, weights and machine-specific runtime paths are ignored. Standard HTTP model download was used on this target after a stalled Xet transfer; the pinned model-provided chat template is included without remote Python execution.

Linux/Windows require a separately installed **local** OpenAI-compatible server: set `LLM_BACKEND=local-http`, `LOCAL_LLM_URL` and matching `LLM_MODEL`. Nonlocal HTTP hosts are rejected. This alternative is not covered by the published Mac MLX quality results. No interactive public AI service is hosted.

## Demonstrate

1. In **Research**, ask “Compare Apple operating margin in 2023 and 2024. Show percentage point change.” Inspect the deterministic origin, formula, inputs and original evidence. Optional AI text has its own status.
2. Ask a documentary question such as “How can acquisition debt covenants constrain Dell capital raising and operating flexibility in 2023?” Inspect each actual generated claim against its sources. A valid source ID alone does not establish support.
3. In **Financials & Valuation**, change the discount rate to 12%, inspect enterprise value/sensitivity and export the current three-page PDF. All finance executes server-side; forecasts are explicit assumptions.
4. In **Sources & Evaluation**, inspect dates/accessions, historical results and pending human review. [Recording details and captions](docs/demo/v1.2/README.md) distinguish this scripted development walkthrough from final evaluation.

Local financial workflow median was 0.0032 seconds without optional AI; qualitative median was 11.75 seconds on the final Mac batch. One optional explanation took 32.13 seconds and was rejected while the result survived. [Timing and memory receipts](evaluation/v1.2/mac-performance.json) include failure/repair and distinguish process RSS from overlapping MLX allocation.

## Verify

```bash
# Create a separate test database in your isolated cluster:
docker compose exec db createdb -U researchdesk researchdesk_test
export TEST_DATABASE_URL=postgresql+psycopg://researchdesk:researchdesk@127.0.0.1:55432/researchdesk_test
uv run ruff check .
uv run ruff format --check .
uv run pytest --junitxml=work/pytest.xml
uv run python scripts/ci_checks.py work/pytest.xml
cd frontend
npm run build
npm exec playwright install chromium
E2E_MODE=mock npm run e2e # explicit doubles; real API finance/PDF
E2E_MODE=live npm run e2e # actual running source/model app; includes labeled fault injections
cd ..
uv run python scripts/verify_inline_facts.py
uv run python scripts/summarize_review.py --validate-only
uv run python scripts/validate_v11.py
uv run python scripts/validate_v12.py
# Optional real inference on already consumed questions, stored as a REPLAY:
uv run researchdesk evaluate --split final
```

Local checks: **144 native PostgreSQL tests, zero skipped; three mock Chromium journeys; four live-mode journeys; 48 original inline-XBRL fact checks**. CI separately checks PostgreSQL/Chromium and a clean Compose migration/import/restart-persistence flow with original synthetic fixtures. CI test doubles do not prove model quality. [Verification ledger](docs/VERIFICATION.md).

Evaluation is append-only. Final cases were committed after corrections and before inference; code/source/result hashes and model revision are validated. Exact questions are distinct from prior batches, but the corpus and financial concepts are familiar. No blind independent benchmark is claimed. Reference values never enter prompts. Synthetic conflict variants use disposable `_test` schemas, not demo-data writes.

## Containers and limits

`docker compose up --build` serves UI/API on loopback and persists PostgreSQL. The container includes no model or full corpus. Download embeddings/ingest inside it and use a host-local model server on port 8081; model runtime paths are machine-specific. MLX remains on macOS. Do not use `docker compose down -v` on data you want to preserve.

One local generation is admitted at a time; verified calculations do not acquire the inference gate. Input/output caps are 2,400/650 tokens; generation is time-bounded. Browser cancellation stops waiting, while active local generation may finish within its budget. There are no accounts, uploads or administrative HTTP endpoints.

Coverage is annual consolidated USD only. Monetary results default to USD millions, with explicit million/billion/raw-USD conversions; no FX. Ambiguous definitions/periods require clarification. Different currencies, entities and scopes are separated; unresolved eligible value/period/basis conflicts retain both proofs. Narrative contradiction detection and free-text intent recognition remain limited. The DCF has no equity bridge or price target and is an educational scenario, not investment advice.

[Architecture](docs/ARCHITECTURE.md) · [Financial definitions](docs/FINANCIAL_METHOD.md) · [Source/model licenses](docs/SOURCES_AND_LICENSES.md) · [Interview guide](docs/INTERVIEW.md) · [Progress journal](docs/PROGRESS.md)
