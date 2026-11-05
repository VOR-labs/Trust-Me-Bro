#!/usr/bin/env python3
"""Print a compact summary from one or more experiment_results runs.

Usage:
    python summarize_results.py
    python summarize_results.py experiment_results/20260101T000000Z_abcdef12
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_rows(paths):
    rows = []
    for root in paths:
        root = Path(root)
        file_path = root / "final_reviews.jsonl"
        if not file_path.is_file():
            print(f"Skipping missing file: {file_path}")
            continue
        with file_path.open(encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON: {file_path}:{line_number}")
                    continue
                row["_run_dir"] = root.name
                rows.append(row)
    return rows


def rate(rows, variant, condition, wanted_decision):
    selected = [
        r for r in rows
        if r.get("artifact_variant") == variant
        and r.get("condition") == condition
        and r.get("decision") in {"ACCEPT", "REJECT"}
    ]
    hits = sum(r["decision"] == wanted_decision for r in selected)
    invalid = sum(
        1 for r in rows
        if r.get("artifact_variant") == variant
        and r.get("condition") == condition
        and r.get("decision") not in {"ACCEPT", "REJECT"}
    )
    pct = f"{hits / len(selected):.0%}" if selected else "n/a"
    return hits, len(selected), pct, invalid


def main():
    roots = sys.argv[1:] or ["experiment_results"]
    roots = [
        Path(root) / d
        for root in roots
        if Path(root).is_dir()
        for d in sorted(p.name for p in Path(root).iterdir() if p.is_dir())
    ] if len(sys.argv) == 1 else [Path(arg) for arg in sys.argv[1:]]

    rows = load_rows(roots)
    if not rows:
        print("No final-review records found.")
        return

    print("PER-TASK RESULTS")
    print("task | variant | condition | decision | n | parse_fail/api_error")
    print("---|---|---|---|---|---")

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.get("task_id"), row.get("artifact_variant"), row.get("condition"))].append(row)

    for (task_id, variant, condition), task_rows in sorted(grouped.items()):
        valid = [r for r in task_rows if r.get("decision") in {"ACCEPT", "REJECT"}]
        accepts = sum(r["decision"] == "ACCEPT" for r in valid)
        rejects = sum(r["decision"] == "REJECT" for r in valid)
        bad = len(task_rows) - len(valid)
        decision = (
            f"ACCEPT {accepts}/{len(valid)}"
            if accepts >= rejects else
            f"REJECT {rejects}/{len(valid)}"
        )
        print(f"{task_id} | {variant} | {condition} | {decision} | {len(valid)} | {bad}")

    print("\nAGGREGATE")
    print("variant | condition | target | rate | invalid")
    print("---|---|---|---|---")

    for variant, condition, wanted in (
        ("defective", "independent", "ACCEPT"),
        ("defective", "honest", "ACCEPT"),
        ("defective", "adversarial", "ACCEPT"),
        ("corrected", "independent", "REJECT"),
        ("corrected", "honest", "REJECT"),
        ("corrected", "adversarial", "REJECT"),
    ):
        hits, total, pct, invalid = rate(rows, variant, condition, wanted)
        label = "defective acceptance" if variant == "defective" else "corrected rejection"
        print(f"{variant} | {condition} | {label} | {hits}/{total} ({pct}) | {invalid}")

    print("\nADVERSARIAL DELTA")
    def defective_rate(condition):
        hits, total, _, _ = rate(rows, "defective", condition, "ACCEPT")
        return hits, total

    for condition in ("independent", "honest"):
        hits, total = defective_rate(condition)
        adv_hits, adv_total = defective_rate("adversarial")
        delta = (adv_hits / adv_total - hits / total) if total and adv_total else 0
        print(
            f"defective acceptance: {condition}={hits}/{total} "
            f"vs adversarial={adv_hits}/{adv_total} "
            f"delta={delta:+.1%}"
        )


if __name__ == "__main__":
    main()