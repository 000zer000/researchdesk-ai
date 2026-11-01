"""Versioned append-only evaluation; references are never generation inputs."""

import hashlib
import json
import resource
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .config import ROOT
from .evaluation import case_session
from .research import AskInput, research

EVAL = ROOT / "evaluation/v1.2"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    files = [
        p
        for pattern in (
            "src/researchdesk/*.py",
            "tests/*.py",
            "frontend/src/*",
            "frontend/e2e/*.ts",
            "scripts/*.py",
            "scripts/*.mjs",
        )
        for p in ROOT.glob(pattern)
        if p.is_file()
    ]
    files += [
        ROOT / p
        for p in [
            "pyproject.toml",
            "uv.lock",
            "frontend/package-lock.json",
            "frontend/package.json",
            "frontend/playwright.config.ts",
            ".env.example",
            ".github/workflows/ci.yml",
        ]
    ]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}


def validate_final_freeze(historical_ref=None):
    freeze = json.loads((EVAL / "final-freeze.json").read_text())
    assert sha(EVAL / "final-cases.json") == freeze["cases_sha256"]
    if historical_ref:
        for name, expected in freeze["source_sha256"].items():
            original = subprocess.check_output(
                ["git", "show", historical_ref + ":" + name], cwd=ROOT
            )
            assert hashlib.sha256(original).hexdigest() == expected, name
    else:
        assert source_hashes() == freeze["source_sha256"], "Runtime changed after final freeze"
    cases = json.loads((EVAL / "final-cases.json").read_text())
    old = []
    for p in [
        ROOT / "evaluation/v1.0/cases.json",
        ROOT / "evaluation/v1.1/cases.json",
        ROOT / "evaluation/v1.1/attempt-01/cases.json",
        EVAL / "dev-cases.json",
    ]:
        old += json.loads(p.read_text())
    for p in EVAL.glob("attempt-*/final-cases.json"):
        old += json.loads(p.read_text())

    def normalize(text):
        return " ".join(text.casefold().split())

    assert not ({normalize(c["question"]) for c in cases} & {normalize(c["question"]) for c in old})
    assert len({c["id"] for c in cases}) == len(cases)
    return cases, freeze


def evaluate(split="final", mode="neighbors_dedup"):
    if split == "final":
        cases, _ = validate_final_freeze()
    else:
        cases = json.loads((EVAL / "dev-cases.json").read_text())
    prior = [
        p
        for p in (EVAL / "runs").glob("*/results.json")
        if json.loads(p.read_text()).get("case_sha256") == sha(EVAL / f"{split}-cases.json")
    ]
    run = EVAL / "runs" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True, exist_ok=False)
    data = {
        "split": split,
        "context_mode": mode,
        "started_at": datetime.now(UTC).isoformat(),
        "case_sha256": sha(EVAL / f"{split}-cases.json"),
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": source_hashes(),
        "execution_kind": "replay of same question batch; previous runs retained"
        if prior
        else "first execution of this batch",
        "records": [],
    }
    for case in cases:
        with case_session(case) as session:
            started = time.monotonic()
            try:
                result = research(
                    session,
                    AskInput(
                        company=case["company"],
                        question=case["question"],
                        as_of=case["as_of"],
                        k=8,
                        explain=case.get("explain", False),
                    ),
                    context_mode=mode,
                )
            except Exception as error:
                result = {
                    "status": "error",
                    "answer": None,
                    "error": type(error).__name__ + ": " + str(error),
                    "evidence": [],
                }
            elapsed = time.monotonic() - started
        answer = result.get("answer") or {}
        accepted = (
            result["status"] == "answered"
            and not answer.get("abstain", True)
            and bool(answer.get("claims"))
        )
        measures = {
            m["id"]: m for m in (result.get("verified_financials") or {}).get("measures", [])
        }
        targets = case.get("reference_targets", [])
        numeric = (
            all(
                t["id"] in measures
                and abs(measures[t["id"]]["value"] - t["value"]) <= t["tolerance"]
                and measures[t["id"]]["unit"] == t["unit"]
                and measures[t["id"]]["direction"] == t["direction"]
                for t in targets
            )
            if accepted and targets
            else False
            if targets
            else None
        )
        # Keep source excerpts and complete transmitted context, never whole reports.
        result["evidence"] = [
            {**p, "text": p["text"][:900], "excerpt_truncated": len(p["text"]) > 900}
            for p in result.get("evidence", [])
        ]
        context = result.get("context_audit", {})
        record = {
            "id": case["id"],
            "question": case["question"],
            "company": case["company"],
            "category": case["category"],
            "answerable": case["answerable"],
            "accepted": accepted,
            "numeric_correct": numeric,
            "decision_expected": result["status"] in case["expected_statuses"],
            "false_refusal": case["answerable"] and not accepted,
            "false_acceptance": not case["answerable"] and accepted,
            "wall_seconds": elapsed,
            "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / (1024**2 if sys.platform == "darwin" else 1024),
            "search_reference_recall": len(
                set(context.get("search_ids", [])) & set(case.get("reference_passages", []))
            )
            / len(case["reference_passages"])
            if case.get("reference_passages")
            else None,
            "generation_reference_recall": len(
                set(context.get("generation_passage_ids", []))
                & set(case.get("reference_passages", []))
            )
            / len(case["reference_passages"])
            if case.get("reference_passages")
            else None,
            "result": result,
        }
        data["records"].append(record)
        (run / "results.json").write_text(json.dumps(data, indent=2) + "\n")
        print(case["id"], result["status"], round(elapsed, 3), flush=True)
    data["completed_at"] = datetime.now(UTC).isoformat()
    (run / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    summary = summarize(data)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (EVAL / f"latest-{split}.json").write_text(
        json.dumps(
            {"run": str(run.relative_to(ROOT)), "results_sha256": sha(run / "results.json")},
            indent=2,
        )
        + "\n"
    )
    if split == "final":
        (EVAL / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(run.relative_to(ROOT))


def summarize(data):
    rows = data["records"]
    answerable = [r for r in rows if r["answerable"]]
    numeric = [r for r in rows if r["numeric_correct"] is not None]
    accepted_numeric = [r for r in numeric if r["accepted"]]
    latencies = {}
    for category in sorted({r["category"] for r in rows}):
        values = [r["wall_seconds"] for r in rows if r["category"] == category]
        latencies[category] = {
            "n": len(values),
            "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)),
        }
    return {
        "version": "1.2.0",
        "split": data["split"],
        "execution_kind": data["execution_kind"],
        "context_mode": data["context_mode"],
        "questions": len(rows),
        "statuses": dict(Counter(r["result"]["status"] for r in rows)),
        "coverage_on_answerable": {
            "answered": sum(r["accepted"] for r in answerable),
            "n": len(answerable),
        },
        "accepted_numeric_accuracy": {
            "correct": sum(r["numeric_correct"] is True for r in accepted_numeric),
            "accepted": len(accepted_numeric),
            "reference_questions": len(numeric),
        },
        "false_refusals": sum(r["false_refusal"] for r in rows),
        "false_acceptances": sum(r["false_acceptance"] for r in rows),
        "latency_seconds_by_category": latencies,
        "peak_process_rss_mib": max(r["process_peak_rss_mib"] for r in rows),
        "semantic_citation_support": "Pending separately labeled coding-agent assessment and independent human review. Exact sentence presence is not entailment.",
        "completeness": "Pending reference-aspect assessment; not inferred from answered status.",
        "human_review": {"status": "pending", "completed": 0},
        "interpretation": "Financial results are deterministic execution of a validated request; availability gains are architecture changes, not improved LLM numerical reasoning. Local model/prompt and actual context are recorded. No overall quality score.",
    }
