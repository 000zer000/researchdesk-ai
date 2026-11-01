# v1.2 development experiments

These are consumed development cases, diagnostics and replays on a familiar corpus, never independent holdouts. Every execution remains in `evaluation/v1.2/`; no best-of-run selection is claimed.

## Diagnosis before model choice

The six archived financial blockers had valid ledger plans. Instrumented v1.1 replay showed truncated JSON and wrong object shapes. Separating deterministic execution from optional prose fixes this architectural dependency without asking a larger model to do arithmetic. The original raw v1.1 proposals were not retained, so replay errors are not asserted as the original individual causes.

The old prose path sent only the first three retrieved passages, sliced into short fragments. Retrieval success therefore did not guarantee generation received the relevant sentence. HP's digitization disclosure crosses a passage boundary. Sentence parsing independently inside each passage discarded it. Joining only genuinely contiguous offsets, retaining both fragments, and rare-term lexical anchors address that general class of loss.

## Context comparison

`context-comparison.json` and timestamped `development/*/results.json` retain four protocols, each comparing legacy fragments, full sentences, and neighboring deduplicated sentences on D05–D08. Ranking/topic routing, sentence completion, deduplication and neighboring windows were changed during development, so this is an incremental diagnostic comparison, not a clean single-factor causal experiment.

The first long-ID JSON protocol failed formatting in all twelve executions. Short-ID JSON caused false refusals. Labeled bullets improved formatting but exposed the incomplete-window defect and overlong outputs. Raw calls, repair attempts, actual transmitted text, offsets, source IDs, omissions and token counts are retained. An answered status never establishes semantic support. The final default packs up to four complete sentences from eight search hits plus one neighbor on either side of the first five hits, with near-duplicate filtering. Legacy mode demonstrates the old three-passage ceiling. Both modes use the declared 2,400-token input / 650-token output / 90-second bounds in the new comparison harness; immutable v1.1 used its original 1,200-output-token copy contract.

## Local model trial

Reviewed Apache-2.0 Qwen3-4B-Instruct-2507, pinned MLX 4-bit revision `50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b`, after the architectural/context diagnosis. The public weight snapshot is about 2.28 GB. The target is an 8 GiB Apple M1; the declared process-RSS ceiling is 5 GiB. RSS and MLX allocator peaks overlap and must not be added.

The initial setup failed because the restricted download omitted the model's separate chat template. That failure is retained, and the downloader now permits the pinned template without remote Python code. A development 1.5B comparison answered two of four qualitative cases and rejected two formats. The first actual 4B comparison answered four, but invented covenant thresholds and conditions not stated in the supplied sources. Those outputs remain failures of semantic grounding despite valid citations. A global source-only prompt revision, applied to every question, then yielded four formatted answers on the same consumed cases. This is a declared development replay, not a new test. The last trial took 6.19–13.30 seconds per question, process peak RSS 616 MiB, MLX peak about 2.72 GiB. It still contained an acquisition-financing connection and a simplified printing mechanism requiring critical review.

The 4B model is selected for more reliable claim formatting and inspectable short explanations within this measured local budget. This is not evidence that model substitution alone fixes retrieval, intent, arithmetic or semantic support. Final unseen wording is evaluated only after source freeze.

## Same-batch system comparison

Immutable v1.1 code on the same 12 development questions: six answered (two financial, four prose), two financial proposals withheld, four refusals. v1.2 selected mode: eight answered (four financial, four prose), two clarification requests, two refusals. Four accepted financial targets match the predeclared value/unit/direction references. No false refusal or false acceptance under these case definitions. Raw baseline and v1.2 results are separate. The financial modes differ: proposal-and-validation versus direct deterministic execution. Prose also changes context, prompt and model; this comparison cannot attribute its effects to any one component.

The baseline D06 restated the question and D07 said only that printing demand was affected; these are incomplete explanations. The new D06 names liens and sale-and-lease-back restrictions; D07 separates digitization from lower-priced non-original supplies. More concrete wording remains subject to semantic review; extra detail can introduce unsupported links. No independent human support rate is claimed.
