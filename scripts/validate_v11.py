"""Verify frozen provenance and human-review receipts without rerunning inference."""

import hashlib
import json

from researchdesk.config import ROOT
from researchdesk.evaluation import EVAL, summarize, validate_freeze

for manifest in (ROOT / "evaluation/v1.1").glob("attempt-*/archive-sha256.json"):
    for name, expected in json.loads(manifest.read_text()).items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
cases, freeze = validate_freeze()
latest = json.loads((EVAL / "latest.json").read_text())
run = ROOT / latest["run"]
assert run.is_relative_to(EVAL / "runs")
assert hashlib.sha256((run / "results.json").read_bytes()).hexdigest() == latest["results_sha256"]
data = json.loads((run / "results.json").read_text())
assert data["code_commit"] == freeze["code_commit"]
assert data["freeze_sha256"] == hashlib.sha256((EVAL / "freeze.json").read_bytes()).hexdigest()
assert [r["id"] for r in data["records"]] == [c["id"] for c in cases]
assert data.get("completed_at"), "Incomplete evaluation cannot be a release result"
assert data["started_at"] >= freeze["created_at"]
assert summarize(data) == json.loads((run / "summary.json").read_text())
assert summarize(data) == json.loads((ROOT / "evaluation/summary.json").read_text())
packet = json.loads((EVAL / "human-review.json").read_text())
assert packet["status"] == "pending" and packet["human_reviews_completed"] == 0
selected = [c["id"] for c in cases if c.get("human_review")]
assert len(selected) == 10 and [r["id"] for r in packet["responses"]] == selected
by_id = {r["id"]: r for r in data["records"]}
for r in packet["responses"]:
    assert r["review_status"] == "pending"
    result = by_id[r["id"]]["result"]
    assert (
        r["answer_sha256"]
        == hashlib.sha256(json.dumps(result.get("answer"), sort_keys=True).encode()).hexdigest()
    )
    assert r["answer"] == result.get("answer") and r["evidence"] == result["evidence"]
print(
    f"Validated {len(cases)} frozen v1.1 results and ten pending human-review responses; no inferred human labels"
)
