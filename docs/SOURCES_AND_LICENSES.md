# Sources, rights and local models

Official SEC references: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [developer resources and fair access](https://www.sec.gov/about/developer-resources), and [privacy/security policy](https://www.sec.gov/about/privacy-information). APIs require no key. The downloader requires a real name/contact User-Agent, caches each response and retrieval time, spaces requests at least 0.6 seconds, backs off on transient failures and stops on access denial. It never bypasses authentication, paywalls or a provider block.

`data/sources.json` identifies the original filings. `data/manifest.json` records original URL, company/CIK, year end, publication date, accession, retrieval timestamps, source and normalized-text SHA-256 hashes, parser version and Company Facts cache hash. Stable prose passage IDs and normalized offsets refer to this parser/corpus version; HTML anchors are retained where available. Structured XBRL evidence is labeled as such, with no fabricated HTML offset or PDF page.

Issuer-created filings may contain copyright or third-party rights despite public EDGAR access. The repository redistributes **no full reports, extracted corpus, issuer logos, raw Company Facts dumps or model weights**. It includes source manifests, code, original synthetic test fixtures, a small fact-verification ledger and generated research/evaluation results. Local users retrieve the originals from the official source. This conservative publication choice is not a blanket statement that all issuer content is public domain. Screenshots show only short retrieved passages needed to demonstrate evidence inspection; generated notes paraphrase risk disclosures.

| Component | Pinned revision | License / role |
|---|---|---|
| [Qwen MLX 1.5B 4-bit](https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit) | `8b403126fc14f14cfc99bb4cfa72ecbc129ea677` | Apache-2.0, local generation; quantized derivative of Qwen2.5-1.5B-Instruct |
| [Qwen upstream](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | See derivative model card | Apache-2.0 |
| [MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Apache-2.0, 384-dimensional local sentence embeddings |
| [MLX-LM](https://github.com/ml-explore/mlx-lm) | Python lockfile | MIT, Apple Silicon inference runtime |

Embeddings use the official ONNX `model_qint8_arm64.onnx`, attention-mask mean pooling, L2 normalization and a 256-token limit. Long passages can lose tail context at embedding time; complete retrieved text is retained for inspection. No model is fine-tuned. Real runs record package versions via `uv.lock`, model revision, temperature, token cap and accessible token usage. Host tested: Apple M1 (8 cores), 8 GB RAM. Inference quality is limited; the first smoke test incorrectly summarized page footers, recorded as a failure in the journal. No energy or GPU-memory measurement is claimed.

Source code in this repository is MIT-licensed. Third-party libraries retain their licenses, specified by their package metadata. The repository license does not relicense issuer documents or model weights. No cost, subscription, hosted-model data transfer or public inference service was used.

Runtime compatibility note: the pinned MLX/MLX-LM combination has thread-affine generation streams. ResearchDesk keeps model import/loading and generation on one owner thread. The observed failure and fix are consistent with the [upstream stream-thread issue](https://github.com/ml-explore/mlx-lm/issues/1181) and the [upstream server's dedicated generation thread](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/server.py). No third-party runtime source was modified.
