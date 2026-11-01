# v1.3 verification — 1 November 2026

## Product changes

The financial engine is unchanged. Optional documentary generation now shares a
coverage-budgeted context selector with an explicitly separate extractive mode.
The selector allows up to eight whole sentences under the existing 2,400-token
input budget, normalizes simple lexical variants, weights rarer query terms and
keeps nearby conditions/consequences. It records omissions and lexical coverage.
Those are retrieval diagnostics, not semantic judgments.

The extractive path verifies that every fragment occurs in its original passage
and reconstructs each complete sentence without model wording. It makes no model
call. It retains citations, source dates and clear origin labels. Source quotations
can contain numbers; these remain quoted text, not additional financial calculations.
The browser explicitly distinguishes excerpts from AI synthesis. The default AI
mode remains available and fallible. No generated prose is asserted to be verified.

## Development retained

`evaluation/v1.3/development/20261101T132205.json` replays the six consumed v1.2
explanation cases and compares four/eight-sentence context. It retains one rejected
answer and the other generated outputs, including irrelevant/unsupported additions.
The later context-only run is separately retained; it contains no new model output.
Lexical normalization, weighting and neighborhood selection were then refined before
freezing the separate acceptance batch. No company/case-specific answers were coded.

## Frozen acceptance run

Cases, source files, corpus manifest and model revision were hashed before first
execution. References never enter a generation request. Results were saved after
each case; none were replaced or selected from repeated attempts. The familiar
Apple/Dell/HP corpus and related development topics make this an engineering
acceptance batch, not independent validation or a general accuracy benchmark.

- Financial targets: two accepted and correct out of three authored targets.
  V303 wrongly assumed that a free-text working-capital operation was in scope.
  The app refused it. That target was not silently edited or counted as correct;
  this is a scope/reference gap, not wrong arithmetic in an accepted result.
- Documentary excerpts: five of five available, no model calls, median 0.277 s.
  Exact source identity is checked; relevance and completeness remain unscored.
- Generated documentary responses: three of five passed output validation;
  median 15.896 s including failures. The two refusals include repeated/excess
  citation labels. Deduplicating labels is a possible future formatting improvement,
  not evidence that their prose is semantically correct.
- Manual inspection by the coding agent still finds unsupported elaboration and
  irrelevant material, including competitive-product language mapped to component
  competition, inferred pricing responses, and portfolio boilerplate. No aggregate
  semantic score is claimed. This inspection is not independent human review.
- Five actual response pairs with sources and blank judgments are prepared in
  `evaluation/v1.3/human-review-pending.json`; all remain pending. The ten v1.2
  human-review forms also remain pending and unchanged.
- Peak process RSS was 484.48 MiB. This excludes separate Metal/GPU allocations;
  it is not the full model or system memory footprint.

## Executed checks

149 native PostgreSQL tests passed, zero skipped. Ruff, formatting, TypeScript and
frontend production build passed. Four Chromium tests passed including desktop
and mobile source-mode labeling; synthetic browser responses remain explicitly
marked test doubles. The earlier failed launch used the wrong browser-cache path;
rerunning with the repository's cached Chromium passed. Real-source excerpt mode
was also checked separately, with no generation call. Existing historical v1.1/v1.2
receipts validate against their original source references, not the changed runtime.

No new Docker or hosted deployment was performed locally for this iteration.
The required GitHub workflow retains its clean Compose check. The historical
v1.2 release, video, evaluation results and hashes are unchanged. Run
`python scripts/evaluate_v13.py validate` to verify this new batch's receipts.
