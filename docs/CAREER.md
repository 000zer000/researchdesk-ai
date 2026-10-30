# Career materials — draft only

These materials describe executed implementation and explicitly measured scope. They do not claim unmeasured model accuracy, investment returns or public cloud inference.

## CV bullets (English)

- Built ResearchDesk, a local AI financial-research application using FastAPI, PostgreSQL and React, combining source-linked retrieval over six official SEC filings with 48 financial facts cross-checked against original inline XBRL.
- Implemented a deterministic five-year FCFF/DCF engine, scenario sensitivities and PDF notes; verified 52 tests on PostgreSQL and real-model Chromium journeys, and evaluated 40 cases with lexical/hybrid retrieval while separating numeric accuracy, citation validity, source support and deterministic abstention.

Use the second bullet's validation claims only together with the final verification ledger and linked CI results. No accuracy percentage is stated because retrieval success and generated-claim support are different measurements.

## LinkedIn draft (not sent)

I built ResearchDesk to explore a practical question: how can a small local language model help with financial research while keeping the numbers and sources inspectable?

The application combines official SEC filings, lexical and semantic retrieval, a real local Qwen model, and a deterministic valuation engine. Every displayed financial fact links back to its original filing context. Forecast assumptions stay separate from published history, and the same calculation code feeds both the interface and an exportable note.

The most useful lesson was that a valid citation is not necessarily a supporting citation. I retained failed model responses and measured retrieval, numerical answers, source support and abstention separately. The evaluation also documents its small sample, synthetic adversarial cases and lack of independent human review.

The code, verification results and local demonstration are available in the public repository. I would be interested in feedback on the retrieval evaluation and financial modeling choices.

Repository: https://github.com/000zer000/researchdesk-ai

This is a project update draft only. It has not been posted or sent.
