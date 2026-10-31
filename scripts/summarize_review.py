"""Validate source-review annotations before summarizing; never invent review labels."""

import argparse
import hashlib
import json

from researchdesk.config import ROOT

parser = argparse.ArgumentParser()
parser.add_argument("--validate-only", action="store_true")
args = parser.parse_args()
data = json.loads((ROOT / "evaluation/v1.0/results.json").read_text())
records = data["records"]
assert len(records) == 80, "The final comparison must have 40 cases per method"
assert len({(r["method"], r["id"]) for r in records}) == 80
assert all(len([r for r in records if r["method"] == m]) == 40 for m in ["lexical", "hybrid"])
review = json.loads((ROOT / "evaluation/v1.0/support-review.json").read_text())
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
archive = ROOT / "evaluation/v1.0"
manifest = json.loads((archive / "archive-sha256.json").read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((archive / name).read_bytes()).hexdigest() == digest, name
if not args.validate_only:
    raise SystemExit(
        "v1.0 is an immutable archive. Do not regenerate its results with a newer runtime."
    )
print(
    f"Validated immutable v1.0 archive: 80 records and {len(review)} coding-agent annotations; no human review claimed"
)
