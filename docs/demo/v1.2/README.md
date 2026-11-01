# Actual v1.2 walkthrough

[Download the 90-second WebM and English captions](https://github.com/000zer000/researchdesk-ai/releases/tag/v1.2.0). Silent recording; use the companion WebVTT captions. No hosted interactive AI service is implied.

The capture uses actual Chromium and the local Mac API, original annual-source data and pinned local Qwen3 4B inference. No routes are mocked, no answer is authored or cached, and no model timing is accelerated. Intentional reading pauses complete the 90 seconds. Only the idle tail is trimmed by stream copy. `recording.json` retains actual action times, responses, provenance and model usage; `media-verification.json` binds the delivered file hashes and duration.

| Time | Actual action |
| --- | --- |
| 0–5 s | Local workspace and published financial data |
| 5–19 s | Apple operating-margin change; deterministic request, formula and four inputs |
| 19–26 s | Original source identifier, annual dates and evidence |
| 26–40 s | Discount rate changed to 12%; actual scenario recalculation and PDF download |
| 40–76 s | Real local Dell explanation, generated/disclosed labels and source inspection |
| 76–90 s | Official source register and evaluation workspace |

The question is a consumed development walkthrough, not a final independent evaluation. The acquisition-financing connection in its second claim still merits source review; the recording is not proof that the narrative is fully supported. Weights were already loaded by a declared rehearsal; there is no answer cache. The rehearsal took 29.76 seconds; the separate final evaluation's qualitative median was 11.75 seconds. Local latency varies.

Reproduce from the repository root, with the actual app running and the workspace Chromium installed:

```bash
node docs/demo/v1.2/record.mjs
```

For a custom Playwright installation, set `PLAYWRIGHT_BROWSERS_PATH` to your own browser directory. The script saves the untrimmed video under ignored `work/`; use a locally available FFmpeg to stream-copy its first 90 seconds. Never present an incomplete or sped-up take as the complete journey.

Recording-only failures are preserved: take 1 selected a hidden mobile control; take 2 missed the research response after a rapid company switch; a real rehearsal verified the settled desktop interaction. Take 3 completed, but full-page screenshot capture temporarily resized recorded frames. The final take waits for company state and takes viewport-only screenshots. These are capture corrections, not product/model tuning or rerun final evaluation. The historical `scripts/record_v12.mjs` remains frozen with the evaluated source; this maintained recording-only helper lives here separately.

The exported three-page PDF contains the 12% discount rate and the recalculated scenario. All pages were rendered with Poppler and visually checked for clipping, overlap and legibility. Generated AI prose is excluded from scenario PDFs. PDF/source/video hashes are recorded separately from judgments of model quality.
