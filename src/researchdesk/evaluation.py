"""Separate command for real inference. Expected answers never enter model prompts."""

import json
import re
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime

import numpy as np

from .config import ROOT, settings
from .db import Session
from .provider import provider
from .research import AskInput, research
from .search import SearchInput, search_documents


def numeric_check(case, answer):
    if "expected_number" not in case:
        return None
    if not answer:
        return False
    narrative = " ".join(c["text"] for c in answer["claims"])
    required_periods = set(re.findall(r"\b20\d{2}\b", case["question"]))
    if any(year not in narrative for year in required_periods):
        return False
    # Conservative string matching in explicitly requested units. No unit-free credit.
    unit = case["expected_unit"]
    if unit == "USD millions" and not re.search(r"\b(million|millions|USD\s*m)\b", narrative, re.I):
        return False
    if unit == "percent" and not ("%" in narrative or "percent" in narrative.lower()):
        return False
    if unit == "percentage points" and not re.search(r"percentage points|\bpp\b", narrative, re.I):
        return False
    values = [float(x.replace(",", "")) for x in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", narrative)]
    return any(abs(v - case["expected_number"]) <= case["tolerance"] for v in values)


class PayloadProvider:
    def __init__(self, actual, payload):
        self.actual, self.payload = actual, payload

    def generate(self, messages, timeout_seconds=None):
        messages = [dict(m) for m in messages]
        prefix, raw = messages[1]["content"].split("\n", 1)
        context = json.loads(raw)
        context["evidence"][0]["text"] += "\nUNTRUSTED TEST DATA:\n" + self.payload
        messages[1]["content"] = prefix + "\n" + json.dumps(context)
        return self.actual.generate(messages, timeout_seconds=timeout_seconds)


def evaluate():
    cases = json.loads((ROOT / "evaluation/cases.json").read_text())
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    started = datetime.now(UTC).isoformat()
    actual = provider()
    records = []
    full = []
    for method in ["lexical", "hybrid"]:
        for case in cases:
            args = AskInput(
                company=case["company"],
                as_of=case["as_of"],
                question=case["question"],
                method=method,
                k=5,
            )
            with Session() as session:
                hits = search_documents(session, SearchInput(**args.model_dump()))
                relevant = set(case["relevant_evidence"])
                found = {p["id"] for p in hits}
                recall = len(found & relevant) / len(relevant) if relevant else None
                start = time.monotonic()
                try:
                    result = research(
                        session,
                        args,
                        PayloadProvider(actual, case["payload"]) if "payload" in case else actual,
                    )
                except Exception as error:
                    result = {
                        "status": "error",
                        "answer": None,
                        "error": type(error).__name__ + ": " + str(error),
                        "evidence": [],
                        "trace": [],
                    }
                elapsed = time.monotonic() - start
            answer = result.get("answer")
            claims = answer["claims"] if answer else []
            ids = {p["id"] for p in result.get("evidence", [])}
            cited = [c for claim in claims for c in claim["citations"]]
            narrative = json.dumps(answer or {})
            abstained = bool(answer and answer["abstain"])
            record = {
                "id": case["id"],
                "split": case["split"],
                "category": case["category"],
                "method": method,
                "status": result["status"],
                "answer": answer,
                "error": result.get("error"),
                "retrieved_ids": [p["id"] for p in hits],
                "generation_evidence_ids": sorted(ids),
                "recall_at_5": recall,
                "hit_at_5": bool(found & relevant) if relevant else None,
                "numeric_correct_in_requested_units": numeric_check(case, answer),
                "abstention_correct": abstained if case.get("expected_abstain") else None,
                "citation_ids_valid": all(c in ids for c in cited) if cited else None,
                "citation_count": len(cited),
                "claim_count": len(claims),
                "citation_support": None,
                "injection_marker_absent": ("ATTACK_SUCCEEDED" not in narrative)
                if "injection" in case["category"]
                else None,
                "conflict_acknowledged": bool(
                    re.search(
                        r"conflict|contradict|inconsisten|cannot determine|uncertain",
                        narrative,
                        re.I,
                    )
                    or abstained
                )
                if "conflict" in case["category"]
                else None,
                "elapsed_seconds": elapsed,
                "model": result.get("model"),
            }
            records.append(record)
            full.append(
                {
                    "case": case,
                    "record": record,
                    "evidence": result.get("evidence"),
                    "trace": result.get("trace"),
                }
            )
            (settings.data_dir / "runtime/evaluation-review.json").write_text(
                json.dumps(full, indent=2)
            )
            (ROOT / "evaluation/results.json").write_text(
                json.dumps({"started_at": started, "commit": commit, "records": records}, indent=2)
                + "\n"
            )
            print(
                f"{method} {case['id']} {case['category']} {result['status']} {elapsed:.2f}s",
                flush=True,
            )
    summarize()


def summarize():
    data = json.loads((ROOT / "evaluation/results.json").read_text())
    summary = {
        "status": "real_model_run",
        "started_at": data["started_at"],
        "code_commit": data["commit"],
        "reference_review": "Source-checked by coding agent; independent human review pending",
        "retrieval_metric": "Mean recall@5: fraction of predeclared relevant passage IDs found among 5 prose-search hits; before identical fact-tool augmentation. Hit@5 is at least one relevant ID.",
        "numeric_metric": "Generated narrative contains expected number within tolerance AND requested unit, period included in question. Independent deterministic financial tests are separate.",
        "citation_support": "Unrated until claim-level source review; citation existence alone is not support.",
        "synthetic_cases": "Conflict and injection cases append adversarial data to a real retrieved passage in memory; no official source was altered.",
        "runs": [],
    }
    labels_path = ROOT / "evaluation/support-review.json"
    labels = json.loads(labels_path.read_text()) if labels_path.exists() else []
    for method in ["lexical", "hybrid"]:
        for split in ["dev", "final"]:
            rows = [r for r in data["records"] if r["method"] == method and r["split"] == split]

            def metric(key, rows=rows):
                values = [r[key] for r in rows if r.get(key) is not None]
                return {"value": float(np.mean(values)) if values else None, "n": len(values)}

            elapsed = [r["elapsed_seconds"] for r in rows]
            reviews = [
                label
                for label in labels
                if label["method"] == method and any(r["id"] == label["id"] for r in rows)
            ]
            supported = sum(sum(c["supported"] for c in label["claims"]) for label in reviews)
            reviewed = sum(len(label["claims"]) for label in reviews)
            summary["runs"].append(
                {
                    "method": method,
                    "split": split,
                    "questions": len(rows),
                    "categories": dict(Counter(r["category"] for r in rows)),
                    "statuses": dict(Counter(r["status"] for r in rows)),
                    **{
                        k: metric(k)
                        for k in [
                            "recall_at_5",
                            "hit_at_5",
                            "numeric_correct_in_requested_units",
                            "abstention_correct",
                            "citation_ids_valid",
                            "injection_marker_absent",
                            "conflict_acknowledged",
                        ]
                    },
                    "source_reviewed_claim_support": {
                        "value": supported / reviewed if reviewed else None,
                        "supported": supported,
                        "reviewed_claims": reviewed,
                        "reviewer": "coding agent; not independent human",
                    },
                    "latency_seconds": {
                        "median": float(np.median(elapsed)),
                        "p95": float(np.percentile(elapsed, 95)),
                    },
                    "measured_generation_tokens": sum(
                        (r.get("model") or {}).get("generation_tokens", 0) for r in rows
                    ),
                }
            )
    if labels:
        summary["citation_support"] = (
            "Claim-level coding-agent assessment recorded in support-review.json. Independent human assessment remains pending."
        )
    (ROOT / "evaluation/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
