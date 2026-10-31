# Verification v1.1

The release records actual checks, separate from model-quality claims. Historical v1.0 evidence is retained in `evaluation/v1.0/` and [the v1.0 verification note](v1.0-VERIFICATION.md).

Before code freeze: native PostgreSQL tests pass **89/89, zero skipped**; Ruff and the TypeScript/production build pass. All **48** financial facts were rechecked against original inline-XBRL contexts, dates, scale, sign and USD units (`evaluation/v1.1/financial-source-checks.json`). The dedicated browser double tests verify the ordinary journey and the display of both contradictory source proofs. Real MLX inference and the financial evidence UI are checked separately.

Final evaluation and CI receipts are added only after their execution. The ten-response human-review packet is prepared from actual outputs; no human review is claimed. Hosted interactive AI, paid models, new subscriptions and changes to other projects are outside this delivery. No raw full reports, model weights, private `.env` or machine-specific runtime paths are published.
