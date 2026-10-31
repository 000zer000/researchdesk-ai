"""Prepare ten preselected real outputs. Never assign human review labels."""

import hashlib
import json

from researchdesk.config import ROOT
from researchdesk.evaluation import EVAL, validate_freeze

cases, _ = validate_freeze()
latest = json.loads((EVAL / "latest.json").read_text())
data = json.loads((ROOT / latest["run"] / "results.json").read_text())
by_id = {r["id"]: r for r in data["records"]}
selected = [c for c in cases if c.get("human_review")]
assert len(selected) == 10
packet = {
    "status": "pending",
    "human_reviews_completed": 0,
    "run": latest["run"],
    "instructions": "These are actual pipeline responses, including refusals and rejected outputs. Check the answer against the linked official source and exact fiscal period. Quote presence and deterministic consistency do not establish full semantic support. Financial prose is rendered by code after validation of an actual model proposal. Mark each criterion yourself; none has been pre-approved.",
    "responses": [],
}
lines = [
    "# ResearchDesk v1.1 — ten responses for human review",
    "",
    "**Human review pending. 0/10 completed.**",
    "",
    packet["instructions"],
    "",
    f"Recorded run: `{latest['run']}`. Selection was declared in the frozen cases before inference.",
    "",
]
for case in selected:
    record = by_id[case["id"]]
    r = record["result"]
    response = {
        "id": case["id"],
        "question": case["question"],
        "company": case["company"],
        "as_of": case["as_of"],
        "status": r["status"],
        "origin": r.get("origin"),
        "answer": r.get("answer"),
        "answer_sha256": hashlib.sha256(
            json.dumps(r.get("answer"), sort_keys=True).encode()
        ).hexdigest(),
        "verified_financials": r.get("verified_financials"),
        "evidence": r["evidence"],
        "review_status": "pending",
        "human_review": {
            "reviewer": None,
            "date": None,
            "financial_correctness": None,
            "units_period_definition": None,
            "citation_support": None,
            "answer_completeness": None,
            "conflict_handling": None,
            "notes": None,
        },
    }
    packet["responses"].append(response)
    lines += [
        f"## {case['id']} — {case['question']}",
        "",
        f"Company: {case['company']} · Analysis date: {case['as_of']} · Status: `{r['status']}` · Origin: {r.get('origin')}",
        "",
    ]
    answer = r.get("answer") or {}
    for claim in answer.get("claims", []):
        lines += [
            claim["text"],
            "",
            "Citations: " + ", ".join(f"`{c}`" for c in claim["citations"]),
            "",
        ]
    if not answer.get("claims"):
        lines += ["No model conclusion displayed. The refusal/rejection is preserved.", ""]
    for limitation in answer.get("limitations", []):
        lines += ["Limitation: " + limitation, ""]
    for m in (r.get("verified_financials") or {}).get("measures", []):
        lines += [
            f"Verified data (code): {m['label']} = {m['value']:.6f} {m['unit']} · {m['direction']} · {', '.join(m['periods'])} · {m['definition']}",
            "",
        ]
    for evidence in r["evidence"]:
        lines += [
            f"**[{evidence['id']}]({evidence['url']})** · {evidence['company']} FY{evidence['fiscal_year']} · filed {evidence['filed']} · accession {evidence['accession']}",
            "",
            "Source excerpt (may be truncated; open filing for context):",
            "",
            "> " + evidence["source_excerpt"].replace("\n", "\n> "),
            "",
        ]
        for span in evidence["cited_spans"]:
            lines += ["Exact selected span:", "", "> " + span.replace("\n", "\n> "), ""]
    lines += [
        "Reviewer: ______  Date: ______",
        "",
        "Correctness / units / periods / definitions: ______",
        "",
        "Does each citation support the complete claim? ______",
        "",
        "Does the response fully answer the question? ______",
        "",
        "Contradictions / missing context / notes: ______",
        "",
    ]
for name, content in [
    ("human-review.json", json.dumps(packet, indent=2) + "\n"),
    ("human-review.md", "\n".join(lines)),
]:
    with (EVAL / name).open("x") as out:
        out.write(content)
print("Prepared ten actual responses; every human-review field is pending")
