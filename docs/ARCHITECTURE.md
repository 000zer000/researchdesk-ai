# Architecture v1.2

The current request/execution/context boundaries are documented in the [technical guide](TECHNICAL_GUIDE.md), including a flow diagram and source-level interview walkthrough. [v1.1 architecture](v1.1-ARCHITECTURE.md) is historical.

`finance.py` owns bounded financial request interpretation, validated schema, source compatibility, Decimal arithmetic, formula construction and DCF. The frontend presents these results. Numerical display does not depend on model inference. `research.py` dispatches validated calculations or source explanations, and keeps optional AI failure separate.

`search.py` combines company/publication-filtered PostgreSQL English lexical ranking, MiniLM cosine similarity and reciprocal rank fusion. Focused ranking prioritizes topic and rare lexical anchors. `context.py` constructs complete adjacent sentences with original fragment offsets, deduplicates and packs actual model input. It audits search IDs separately from transmitted IDs. No general vector database is needed for this six-report corpus.

`explanations.py` gives the local model no executable tools. It binds labeled claims only to supplied sentence references, checks original fragment identity, scope and numeric-prose restrictions. Exact presence is not semantic entailment. Disclosed/interpretation labels are generated and can be wrong. Prose contradictions not identified by the model remain a known limitation; structured financial conflicts are handled deterministically.

The MLX adapter uses a persistent owner thread for loading/generation/cleanup; only inference acquires its gate. A valid financial request can execute while the model is occupied. Local HTTP is an alternative local-only adapter and is not covered by the Mac MLX quality results.

`report.py` reuses the same finance functions and validated scenario assumptions. The PDF excludes generated AI paragraphs, so changing an assumption cannot retain stale model narrative. Publication dates filter all facts, retrieval and evidence requests. Model weights, runtime paths and full reports remain ignored.

Evaluation imports references only after normal research execution. Frozen hashes, raw attempts, transmitted context, repaired formats, failures and pending review packets are separate from deterministic CI. Neither source identity nor green CI proves AI claim quality.
