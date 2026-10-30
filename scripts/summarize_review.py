"""Validate source-review annotations before summarizing; never invent review labels."""

import argparse
import hashlib
import json

from researchdesk.config import ROOT
from researchdesk.evaluation import summarize

parser = argparse.ArgumentParser()
parser.add_argument("--validate-only", action="store_true")
args = parser.parse_args()
data = json.loads((ROOT / "evaluation/results.json").read_text())
records = data["records"]
assert len(records) == 80, "The final comparison must have 40 cases per method"
assert len({(r["method"], r["id"]) for r in records}) == 80
assert all(len([r for r in records if r["method"] == m]) == 40 for m in ["lexical", "hybrid"])
review = json.loads((ROOT / "evaluation/support-review.json").read_text())
by_key = {(r["method"], r["id"]): r for r in records}
assert len({(r["method"], r["id"]) for r in review}) == len(review)
for label in review:
    record = by_key[(label["method"], label["id"])]
    digest = hashlib.sha256(json.dumps(record["answer"], sort_keys=True).encode()).hexdigest()
    assert digest == label["answer_sha256"], f"Stale review: {label['method']} {label['id']}"
    assert len(label["claims"]) == len(record["answer"]["claims"])
    for claim, annotation in zip(record["answer"]["claims"], label["claims"], strict=True):
        assert set(claim["citations"]) == {c["id"] for c in annotation["citations"]}
        assert isinstance(annotation["supported"], bool) and annotation["reason"]
assert {(label["method"], label["id"]) for label in review} == {
    (r["method"], r["id"]) for r in records if (r.get("answer") or {}).get("claims")
}, "Every displayed claim requires a source review annotation"
fingerprints = json.loads((ROOT / "evaluation/runtime-source-hashes.json").read_text())
for name, expected in fingerprints["sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, (
        f"Runtime differs from evaluated code: {name}"
    )
assert fingerprints["evaluated_commit"] == data["commit"]
if args.validate_only:
    print(
        f"Validated 80 result records, {len(review)} source-reviewed answers and evaluated runtime fingerprints"
    )
else:
    summarize()
    path = ROOT / "evaluation/summary.json"
    summary = json.loads(path.read_text())
    summary["holdout_status"] = (
        "Final replay after development and runtime corrections; not a pristine holdout. Earlier attempts are retained."
    )
    summary["citation_review_definition"] = (
        "Claim support requires every material assertion to be grounded in the union of its cited passages. A citation is relevant when it contributes evidence to a material component; relevance alone is weaker than whole-claim support. Coding-agent assessment, not independent human review."
    )
    for run in summary["runs"]:
        labels = [
            label
            for label in review
            if label["method"] == run["method"]
            and by_key[(label["method"], label["id"])]["split"] == run["split"]
        ]
        pairs = [
            citation
            for label in labels
            for claim in label["claims"]
            for citation in claim["citations"]
        ]
        run["source_reviewed_citation_relevance"] = {
            "relevant": sum(p["relevant"] for p in pairs),
            "reviewed": len(pairs),
            "value": sum(p["relevant"] for p in pairs) / len(pairs) if pairs else None,
        }
        run["source_reviewed_answer_completeness"] = {
            "complete": sum(label["answers_question"] for label in labels),
            "reviewed": len(labels),
            "value": sum(label["answers_question"] for label in labels) / len(labels)
            if labels
            else None,
        }
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print("Added separately source-reviewed relevance and completeness metrics")
