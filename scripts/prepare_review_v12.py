"""Prepare a simple review packet from preselected actual final responses."""

import hashlib
import json

from researchdesk.config import ROOT
from researchdesk.evaluation_v12 import EVAL, validate_final_freeze

cases, _ = validate_final_freeze()
latest = json.loads((EVAL / "latest-final.json").read_text())
data = json.loads((ROOT / latest["run"] / "results.json").read_text())
rows = {r["id"]: r for r in data["records"]}
packet = {"status": "pending", "completed": 0, "run": latest["run"], "responses": []}
lines = [
    "# ResearchDesk v1.2 — human review packet",
    "",
    "**Pending: no human review has been performed.**",
    "",
    "Each response below is an actual preselected pipeline output. Deterministic results and AI claims have separate origins. Sentence identity is not semantic support. Judge complete assertions, relevance, missing aspects and the fact/interpretation labels.",
    "",
    "Judgment scale: correct / partial / incorrect / not applicable. Leave reviewer and date blank until an actual person has reviewed the evidence.",
    "",
]
for c in cases:
    if not c.get("human_review"):
        continue
    r = rows[c["id"]]["result"]
    answer = r.get("answer")
    item = {
        "id": c["id"],
        "question": c["question"],
        "status": r["status"],
        "origin": r.get("origin"),
        "answer": answer,
        "answer_sha256": hashlib.sha256(json.dumps(answer, sort_keys=True).encode()).hexdigest(),
        "evidence": r.get("evidence", []),
        "context_audit": r.get("context_audit"),
        "verified_financials": r.get("verified_financials"),
        "human_status": "pending",
        "judgment": {
            "reviewer": None,
            "date": None,
            "factual_correctness": None,
            "citation_support": None,
            "relevance": None,
            "completeness": None,
            "fact_vs_interpretation": None,
            "notes": None,
        },
    }
    packet["responses"].append(item)
    lines += [
        f"## {c['id']} — {c['question']}",
        "",
        f"Status: {r['status']} · Origin: {r.get('origin')}",
        "",
    ]
    for claim in (answer or {}).get("claims", []):
        lines += [
            f"**{claim.get('origin', 'generated_text')} · {claim.get('kind', 'verified calculation')}**",
            "",
            claim["text"],
            "",
            "Citations: " + ", ".join(claim["citations"]),
            "",
        ]
    if not (answer or {}).get("claims"):
        lines += ["No conclusion displayed. The actual refusal/rejection is retained.", ""]
    for limitation in (answer or {}).get("limitations", []):
        lines += ["Limitation: " + limitation, ""]
    for p in r.get("evidence", []):
        lines += [
            f"**[{p['id']}]({p['url']})** · {p['company']} FY{p['fiscal_year']} · filed {p['filed']} · accession {p['accession']}",
            "",
            "> " + p["text"].replace("\n", "\n> "),
            "",
        ]
    if r.get("context_audit"):
        lines += ["Complete sentences actually supplied to the model:", ""]
        for s in r["context_audit"]["sentences"]:
            lines += [f"[{s['id']}] " + s["text"], ""]
    lines += [
        "Reviewer / date: ______",
        "",
        "Correctness: ______ · Citation support: ______ · Relevance: ______",
        "",
        "Completeness: ______ · Disclosure vs interpretation: ______",
        "",
        "Missing context / notes: ______",
        "",
    ]
with (EVAL / "human-review.json").open("x") as f:
    f.write(json.dumps(packet, indent=2) + "\n")
with (EVAL / "human-review.md").open("x") as f:
    f.write("\n".join(lines) + "\n")
print("Prepared", len(packet["responses"]), "actual responses; all human fields remain pending")
