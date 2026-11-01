# v1.2 diagnosis before architecture changes

The original v1.1 records retain verified facts and generic rejection messages, not raw proposals. An instrumented replay on the immutable v1.1 tag retains raw outputs separately. Replay causes below must not be asserted as exact original raw failures. These are old diagnostic cases, not new independent tests.

| Case | Retrieval / data | Request understanding | Replay generation / format / validation | Product diagnosis |
| --- | --- | --- | --- | --- |
| N04 | Ledger resolved, required inputs present; no ledger issues | Requested metric/year correctly represented in canonical measures | The local model did not return complete structured JSON | Unnecessary model-copy gate hides a valid result |
| N08 | Ledger resolved, required inputs present; no ledger issues | Requested metric/year correctly represented in canonical measures | The local model did not return complete structured JSON | Unnecessary model-copy gate hides a valid result |
| N09 | Ledger resolved, required inputs present; no ledger issues | Requested metric/year correctly represented in canonical measures | 10 validation errors for FinancialAnswer | Unnecessary model-copy gate hides a valid result |
| N11 | Ledger resolved, required inputs present; no ledger issues | Requested metric/year correctly represented in canonical measures | The local model did not return complete structured JSON | Unnecessary model-copy gate hides a valid result |
| N23 | Ledger resolved, required inputs present; no ledger issues | Requested metric/year correctly represented in canonical measures | The local model did not return complete structured JSON | Unnecessary model-copy gate hides a valid result |
| N24 | Ledger resolved, required inputs present; no ledger issues | Requested metric/year correctly represented in canonical measures | 10 validation errors for FinancialAnswer | Unnecessary model-copy gate hides a valid result |

In all six cases, execution had already produced the verified measure. N23 and N24 correctly excluded the foreign-currency/segment observation. No missing-data diagnosis or model upgrade is justified by these records. The v1.2 correction therefore removes generation from the result-availability path.

| Qualitative case | Observed problem | Stage classification |
| --- | --- | --- |
| N13 | Restates limited-supplier risk without the shortage/pricing mechanism; selected first 220-character span ends mid-sentence | Context segmentation and generation/completeness |
| N14 | Claim mentions covenants/flexibility, but selected first slice stops before the covenant consequence and an extra citation concerns borrowing availability | Context/citation selection and validation that checks identity, not support |
| N15 | Generic printing statement cites general component suppliers and a clipped printing bullet rather than the full digital/third-party mechanism | Ranking (printing vs incidental supplies), context and generation |
| N16 | Specific consequences exist in later source text, but prose only says the business could be harmed; evidence is spread across fragments | Generation/completeness and fragmented context |
| N25 | Generic cyber concern cites a natural-disaster sentence; exact source identity did not establish semantic relevance | Ranking, citation selection and inadequate semantic support; synthetic injection probe alone is not quality evidence |

The three-passage truncation is evaluated separately from search@5. v1.2 context audits record the actual complete sentences, selected/omitted IDs, tokenizer budget and hash. Human semantic review remains pending.
