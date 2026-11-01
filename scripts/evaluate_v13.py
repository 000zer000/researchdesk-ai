"""Frozen acceptance batch on a familiar corpus; no independent human judgment."""

import argparse
import hashlib
import json
import resource
import statistics
import sys
import time
from datetime import UTC, datetime

from sqlalchemy import text

from researchdesk.config import ROOT, settings
from researchdesk.db import Session
from researchdesk.evaluation_v12 import source_hashes
from researchdesk.research import AskInput, research

EVAL = ROOT / "evaluation/v1.3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_freeze():
    frozen = json.loads((EVAL / "freeze.json").read_text())
    assert frozen["cases_sha256"] == digest(EVAL / "cases.json")
    assert frozen["source_sha256"] == source_hashes(), "Runtime changed after freeze"
    assert frozen["corpus_manifest_sha256"] == digest(ROOT / "data/manifest.json")
    return frozen


def summarize(data):
    records = data["records"]
    numeric = [r for r in records if r["category"] == "financial"]
    docs = [r for r in records if r["category"] == "documentary"]
    return {
        "scope": "Coding-agent-authored acceptance cases on the familiar six-report corpus; not independent or a general accuracy estimate.",
        "financial_targets": len(numeric),
        "financial_targets_accepted_and_correct": sum(r["numeric_correct"] for r in numeric),
        "documentary_cases": len(docs),
        "generated_documentary_answers_accepted": sum(
            r["generated"]["status"] == "answered" for r in docs
        ),
        "source_excerpt_answers_available": sum(
            r["extractive"]["status"] == "answered" for r in docs
        ),
        "source_excerpt_model_calls": sum(
            len(r["extractive"].get("model_calls", [])) for r in docs
        ),
        "human_reviews_completed": 0,
        "semantic_support": "Unscored; source identity and answered status do not establish support or completeness.",
        "generated_documentary_median_seconds": statistics.median(
            r["generated"]["elapsed_seconds"] for r in docs
        ),
        "extractive_documentary_median_seconds": statistics.median(
            r["extractive"]["elapsed_seconds"] for r in docs
        ),
        "peak_process_rss_mib": data["peak_process_rss_mib"],
    }


def freeze():
    cases = json.loads((EVAL / "cases.json").read_text())
    assert len({c["id"] for c in cases}) == len(cases)
    previous = []
    for path in (ROOT / "evaluation").glob("**/*cases.json"):
        if EVAL not in path.parents:
            previous += json.loads(path.read_text())
    normalize = lambda q: " ".join(q.casefold().split())  # noqa: E731
    assert not (
        {normalize(c["question"]) for c in cases} & {normalize(c["question"]) for c in previous}
    )
    target = EVAL / "freeze.json"
    assert not target.exists(), "Never overwrite a consumed freeze"
    model = json.loads((settings.data_dir / "runtime/llm.json").read_text())
    target.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "scope": "First execution of new wording on a familiar corpus, not a blind external evaluation",
                "cases_sha256": digest(EVAL / "cases.json"),
                "source_sha256": source_hashes(),
                "corpus_manifest_sha256": digest(ROOT / "data/manifest.json"),
                "model": {k: model.get(k) for k in ("model", "revision")},
            },
            indent=2,
        )
        + "\n"
    )


def run():
    frozen = check_freeze()
    assert not (EVAL / "results.json").exists(), "First run already consumed; preserve it"
    cases = json.loads((EVAL / "cases.json").read_text())
    data = {
        "started_at": datetime.now(UTC).isoformat(),
        "freeze_sha256": digest(EVAL / "freeze.json"),
        "scope": frozen["scope"],
        "records": [],
    }
    for case in cases:
        args = AskInput(company=case["company"], question=case["question"], k=8)
        with Session() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            start = time.monotonic()
            try:
                generated = research(session, args)
            except Exception as error:
                generated = {
                    "status": "error",
                    "error": type(error).__name__ + ": " + str(error),
                    "answer": None,
                    "elapsed_seconds": time.monotonic() - start,
                }
            row = {"id": case["id"], "category": case["category"], "generated": generated}
            if case["category"] == "documentary":
                row["extractive"] = research(
                    session, args.model_copy(update={"response_mode": "extractive"})
                )
            else:
                result = generated.get("verified_financials") or {}
                selected = [
                    m for m in result.get("measures", []) if m["id"] in result.get("result_ids", [])
                ]
                row["numeric_correct"] = bool(
                    generated["status"] == "answered"
                    and len(selected) == 1
                    and selected[0]["unit"] == case["reference_unit"]
                    and abs(selected[0]["value"] - case["reference_value"])
                    <= case["absolute_tolerance"]
                )
        data["records"].append(row)
        (EVAL / "results.json").write_text(json.dumps(data, indent=2) + "\n")
        print(case["id"], generated["status"], flush=True)
    data["completed_at"] = datetime.now(UTC).isoformat()
    data["peak_process_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
        1024**2 if sys.platform == "darwin" else 1024
    )
    (EVAL / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    (EVAL / "summary.json").write_text(json.dumps(summarize(data), indent=2) + "\n")
    packet = {
        "status": "pending",
        "completed": 0,
        "reviewer": None,
        "responses": [
            {
                "id": row["id"],
                "question": next(c["question"] for c in cases if c["id"] == row["id"]),
                "generated": row["generated"],
                "extractive": row["extractive"],
                "judgment": {
                    "support": None,
                    "completeness": None,
                    "relevance": None,
                    "chronology": None,
                },
                "reviewer": None,
                "reviewed_at": None,
            }
            for row in data["records"]
            if row["category"] == "documentary"
        ],
    }
    (EVAL / "human-review-pending.json").write_text(json.dumps(packet, indent=2) + "\n")
    (EVAL / "receipts.json").write_text(
        json.dumps(
            {p.name: digest(p) for p in EVAL.glob("*.json") if p.name != "receipts.json"}, indent=2
        )
        + "\n"
    )


def validate():
    check_freeze()
    receipts = json.loads((EVAL / "receipts.json").read_text())
    for name, expected in receipts.items():
        assert digest(EVAL / name) == expected, name
    data = json.loads((EVAL / "results.json").read_text())
    assert (
        data.get("completed_at")
        and data["started_at"] >= json.loads((EVAL / "freeze.json").read_text())["created_at"]
    )
    assert data["freeze_sha256"] == digest(EVAL / "freeze.json")
    assert summarize(data) == json.loads((EVAL / "summary.json").read_text())
    packet = json.loads((EVAL / "human-review-pending.json").read_text())
    assert packet["completed"] == 0 and packet["reviewer"] is None
    for row in packet["responses"]:
        assert all(v is None for v in row["judgment"].values())
    print("v1.3 execution receipts and pending human review validated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["freeze", "run", "validate"])
    args = parser.parse_args()
    {"freeze": freeze, "run": run, "validate": validate}[args.operation]()
