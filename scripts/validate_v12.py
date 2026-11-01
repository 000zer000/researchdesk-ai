"""Verify final execution provenance; never invent a human or semantic judgment."""

import hashlib
import json

from researchdesk.config import ROOT
from researchdesk.evaluation_v12 import EVAL, summarize, validate_final_freeze

cases, freeze = validate_final_freeze(historical_ref="v1.2.0")
latest = json.loads((EVAL / "latest-final.json").read_text())
run = ROOT / latest["run"]
assert run.is_relative_to(EVAL / "runs")
data = json.loads((run / "results.json").read_text())
assert hashlib.sha256((run / "results.json").read_bytes()).hexdigest() == latest["results_sha256"]
assert data["source_sha256"] == freeze["source_sha256"]
assert data["case_sha256"] == freeze["cases_sha256"]
assert data.get("completed_at") and data["started_at"] >= freeze["created_at"]
assert [r["id"] for r in data["records"]] == [c["id"] for c in cases]
assert summarize(data) == json.loads((run / "summary.json").read_text())
assert summarize(data) == json.loads((EVAL / "summary.json").read_text())
for record in data["records"]:
    results = [record["result"], record["result"].get("explanation", {})]
    for result in results:
        for call in result.get("model_calls", []):
            meta = call["metadata"]
            assert meta["generation_tokens"] <= 650
            assert meta["prompt_tokens"] <= 2400
            assert (
                meta["model"] == freeze["model"]["model"]
                and meta["revision"] == freeze["model"]["revision"]
            )
packet = json.loads((EVAL / "human-review.json").read_text())
selected = [c["id"] for c in cases if c.get("human_review")]
assert packet["status"] == "pending" and packet["completed"] == 0
assert [r["id"] for r in packet["responses"]] == selected
by_id = {r["id"]: r for r in data["records"]}
for row in packet["responses"]:
    assert (
        row["answer_sha256"]
        == hashlib.sha256(
            json.dumps(by_id[row["id"]]["result"].get("answer"), sort_keys=True).encode()
        ).hexdigest()
    )
    assert row["human_status"] == "pending" and all(v is None for v in row["judgment"].values())
review_path = EVAL / "coding-agent-review.json"
if review_path.exists():
    review = json.loads(review_path.read_text())
    assert review["reviewer"] == "coding agent; not independent human"
    for row in review["responses"]:
        assert (
            row["answer_sha256"]
            == hashlib.sha256(
                json.dumps(by_id[row["id"]]["result"].get("answer"), sort_keys=True).encode()
            ).hexdigest()
        )
        assert len(row["claims"]) == len(
            (by_id[row["id"]]["result"].get("answer") or {}).get("claims", [])
        )
        assert row["reason"]
print(
    f"Validated {len(cases)} final results, model/input/output budgets, archive provenance and {len(selected)} pending human reviews"
)
