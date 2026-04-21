"""
Aggregate results from scores.csv and print a human-readable summary table.

Run from project root:
    python scripts/summarize.py

Optionally filter to a single condition:
    python scripts/summarize.py --condition baseline
    python scripts/summarize.py --condition treatment
"""

import sys
import os
import csv
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_CSV = os.path.join(PROJECT_ROOT, "results", "scores.csv")


def pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}%" if denominator > 0 else "N/A"


def avg(values: list) -> str:
    nums = [v for v in values if v is not None and v >= 0]
    return f"{sum(nums)/len(nums):.2f}" if nums else "N/A"


def summarize_condition(label: str, data: list) -> None:
    n = len(data)
    if n == 0:
        print(f"\n{label.upper()}: no data")
        return

    def count(field, value=True):
        return sum(1 for r in data if str(r.get(field, "")).lower() == str(value).lower())

    parseable = count("parseable", "True")
    valid = count("xsd_valid", "True")
    sem_errors = [int(r["semantic_errors"]) for r in data if r.get("semantic_errors") not in (None, "", "-1")]
    hall_nodes = sum(int(r.get("hallucinated_nodes") or 0) for r in data)
    total_nodes = sum(int(r.get("total_nodes") or 0) for r in data)
    hall_fields = sum(int(r.get("hallucinated_fields") or 0) for r in data)
    total_fields = sum(int(r.get("total_fields") or 0) for r in data)

    print(f"\n{'─'*50}")
    print(f"  {label.upper()}  (n={n})")
    print(f"{'─'*50}")
    print(f"  Parseable XML        : {parseable}/{n}  ({pct(parseable, n)})")
    print(f"  XSD Valid            : {valid}/{n}  ({pct(valid, n)})")
    print(f"  Avg semantic errors  : {avg(sem_errors)} per scene  (total {sum(sem_errors)})")
    print(f"  Node hallucination   : {hall_nodes}/{total_nodes} nodes  ({pct(hall_nodes, total_nodes)})")
    print(f"  Field hallucination  : {hall_fields}/{total_fields} fields  ({pct(hall_fields, total_fields)})")

    # Per-level breakdown
    print()
    for level in ("1", "2", "3"):
        ld = [r for r in data if str(r.get("level")) == level]
        if not ld:
            continue
        lv = sum(1 for r in ld if str(r.get("xsd_valid", "")).lower() == "true")
        lse = sum(int(r.get("semantic_errors") or 0) for r in ld if str(r.get("semantic_errors", "")) not in ("", "-1"))
        ln = len(ld)
        print(f"  Level {level}: XSD valid {lv}/{ln} ({pct(lv,ln)})  |  semantic errors {lse}  ({lse/ln:.1f} avg)")


def print_delta(baseline: list, treatment: list, label: str = "") -> None:
    if not baseline or not treatment:
        return

    def rate(data, field, value="True"):
        n = len(data)
        c = sum(1 for r in data if str(r.get(field, "")).lower() == str(value).lower())
        return c / n if n else 0

    def mean_sem(data):
        vals = [int(r["semantic_errors"]) for r in data if r.get("semantic_errors") not in (None, "", "-1")]
        return sum(vals) / len(vals) if vals else 0

    def hall_rate(data, node_field, total_field):
        h = sum(int(r.get(node_field) or 0) for r in data)
        t = sum(int(r.get(total_field) or 0) for r in data)
        return h / t if t else 0

    bv = rate(baseline, "xsd_valid")
    tv = rate(treatment, "xsd_valid")
    bse = mean_sem(baseline)
    tse = mean_sem(treatment)
    bhn = hall_rate(baseline, "hallucinated_nodes", "total_nodes")
    thn = hall_rate(treatment, "hallucinated_nodes", "total_nodes")
    bhf = hall_rate(baseline, "hallucinated_fields", "total_fields")
    thf = hall_rate(treatment, "hallucinated_fields", "total_fields")

    print(f"\n{'═'*50}")
    print("  DELTA  (treatment − baseline)")
    print(f"{'═'*50}")
    print(f"  XSD validity          : {bv:.1%} → {tv:.1%}  (Δ {tv-bv:+.1%})")
    print(f"  Semantic errors (avg) : {bse:.2f} → {tse:.2f}  (Δ {tse-bse:+.2f})")
    print(f"  Node halluc rate      : {bhn:.1%} → {thn:.1%}  (Δ {thn-bhn:+.1%})")
    print(f"  Field halluc rate     : {bhf:.1%} → {thf:.1%}  (Δ {thf-bhf:+.1%})")
    print()


def summarize() -> None:
    if not os.path.exists(SCORES_CSV):
        print(f"scores.csv not found at {SCORES_CSV}")
        print("Run score_results.py first.")
        return

    with open(SCORES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    filter_condition = None
    for arg in sys.argv[1:]:
        if arg.startswith("--condition="):
            filter_condition = arg.split("=", 1)[1]
        elif arg == "--condition" and len(sys.argv) > sys.argv.index(arg) + 1:
            filter_condition = sys.argv[sys.argv.index(arg) + 1]

    by_condition = defaultdict(list)
    for row in rows:
        by_condition[row["condition"]].append(row)

    print(f"\n{'═'*50}")
    print("  X3D-MCP EVALUATION RESULTS")
    print(f"  {len(rows)} scored outputs")
    print(f"{'═'*50}")

    all_conditions = ["Claude Sonnet 4.6", "Gemini 3.1 Pro", "MCP"]
    conditions = [filter_condition] if filter_condition else all_conditions
    for cond in conditions:
        summarize_condition(cond, by_condition.get(cond, []))

    if not filter_condition:
        print(f"\n{'═'*50}")
        print("  DELTA  (MCP vs each baseline)")
        print(f"{'═'*50}")
        mcp = by_condition.get("MCP", [])
        for baseline_label in ("Claude Sonnet 4.6", "Gemini 3.1 Pro"):
            baseline = by_condition.get(baseline_label, [])
            if baseline and mcp:
                print(f"\n  vs {baseline_label}:")
                print_delta(baseline, mcp)


if __name__ == "__main__":
    summarize()
