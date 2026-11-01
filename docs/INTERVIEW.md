# Interview guide v1.2

Start with the [current technical guide](TECHNICAL_GUIDE.md), [measured evaluation](EVALUATION.md), and [90-second walkthrough](demo/v1.2/README.md). [The previous interview guide](v1.1-INTERVIEW.md) remains historical.

“ResearchDesk separates two kinds of output. Server code interprets a bounded financial request and calculates from original source-linked data; a local language model explains annual disclosures. Verified arithmetic is visible even if optional generation fails. I can inspect each formula and input, and then separately judge whether a generated explanation is supported and complete.”

Show the removed copy gate: six old blockers had valid server data but malformed model proposals. Explain why displaying those figures directly is an architecture correction, not improved LLM numerical reasoning. Then show the consumed v1.2 evaluation, including a percentage-intent mistake, two incorrect evaluator references, false refusals, and their general regressions. Expected answers can also be wrong; preserved results make that visible.

For retrieval, show search candidates versus the actual transmitted context. A sentence split across adjacent passages must retain both original fragments. Four complete sentences under a tokenizer budget can be more useful than three truncated passages, but no retrieved sentence count proves semantic support.

For local inference, cite the pinned Qwen3 4B quantization and measured M1 memory/latency, plus the first 4B trial's invented covenant conditions. Model choice is a resource and output-quality tradeoff, not a substitute for request validation or evidence inspection. Independent human review remains pending.

For finance, derive FCFF and terminal working capital from `finance.py`, distinguish CFO less gross PPE capex from company-reported FCF and unlevered FCFF, and demonstrate WACC sensitivity and the exported assumptions. This is a transparent scenario, not a price target.

For testing, distinguish native PostgreSQL and Chromium checks from real-model evaluation. Discuss corpus limits, heuristic intent recognition, narrative conflicts and remaining completeness defects. Use actual result files, never a remembered aggregate score.

The previous guide's optional mid-year-discount exercise remains unimplemented for the owner to practice; it is not a delivered feature.
