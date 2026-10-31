# Verification v1.1

The release records actual checks, separate from model-quality claims. Historical v1.0 evidence is retained in `evaluation/v1.0/` and [the v1.0 verification note](v1.0-VERIFICATION.md).

Before code freeze: native PostgreSQL tests pass **106/106, zero skipped**; Ruff and the TypeScript/production build pass. All **48** financial facts were rechecked against original inline-XBRL contexts, dates, scale, sign and USD units (`evaluation/v1.1/financial-source-checks.json`). The dedicated browser double tests verify the ordinary journey and the display of both contradictory source proofs. Real MLX inference and the financial evidence UI are checked separately.

The final 25-question batch executed on the frozen runtime: 7/13 reference financial/calendar targets answered correctly, six withheld; two ambiguous synthetic conflicts refused. Full records and the consumed earlier batch are preserved separately. CI receipts are added only after execution. The ten-response human-review packet is prepared from actual outputs; no human review is claimed. Hosted interactive AI, paid models, new subscriptions and changes to other projects are outside this delivery. No raw full reports, model weights, private `.env` or machine-specific runtime paths are published.


Final local checks: **106 native PostgreSQL tests, zero failures/skips; two deterministic Chromium journeys; three final local Chromium journeys (two actual-model journeys and one explicitly simulated conflict-display case)**. TypeScript/build, Ruff and immutable-archive/frozen-result validators passed. The actual financial screenshot visibly shows a rejected proposal with preserved data, not a fabricated successful answer. See `evaluation/v1.1/final-local-verification.json`.

The ten-response packet deliberately includes two withheld financial proposals among its preselected cases. Its source records and verified data remain reviewable. Human review is **0/10**, not completed by the coding agent. No new hosted AI service or paid resource is claimed.
