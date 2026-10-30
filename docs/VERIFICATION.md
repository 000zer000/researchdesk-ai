# Verification ledger

Status is updated from actual execution. Configuration alone is never evidence of a passing check.

| Check | Status / evidence |
|---|---|
| Official source access | Six original SEC 10-Ks cached successfully; source/manifest JSON records provenance |
| Real local model | Qwen/MLX executed on Apple M1; first failed-quality smoke and subsequent run documented |
| PostgreSQL integration | Native PostgreSQL 17, dedicated test database; initial corrected run 29 passed / 0 skipped |
| Financial facts | Independent original inline-XBRL cross-check command; result ledger published after completion |
| DCF and ratios | Independent annuity identity, discount-period, NWC, tax, sensitivity, invalid input and missing data tests |
| PDF visual review | Three rendered pages inspected at desktop-readable resolution; no clipping/overlap observed |
| TypeScript / production build | Executed successfully locally |
| Chromium simulated journey | Pending execution; proves UI/API integration, not inference |
| Chromium real-model journey | Pending execution; required separately |
| Desktop/mobile visual review | Pending actual screenshots |
| Clean Docker Compose | Local Docker unavailable; Linux GitHub Actions execution required |
| Public repository / CI / release | Pending publication and confirmed run results |

There is no hosted interactive AI service. A recording and local reproducibility are the delivery path. Independent human review of narrative support is outstanding; do not describe coding-agent assessment as human verification.
