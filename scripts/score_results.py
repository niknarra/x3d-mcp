"""
Score all outputs in results/baseline/ and results/treatment/.

For each .x3d file, measures:
  - parseable       : is it valid XML at all?
  - xsd_valid       : does it pass X3D 4.0 schema validation?
  - xsd_errors      : number of XSD validation errors
  - semantic_errors : authoring-level errors (DEF/USE, ROUTEs, Shape completeness, etc.)
  - semantic_warnings
  - semantic_info
  - total_nodes     : X3D scene nodes found (excludes structural tags)
  - hallucinated_nodes : nodes not in X3DUOM concrete or abstract node list
  - total_fields    : attribute assignments across all nodes
  - hallucinated_fields : attributes not recognized for that node type

Writes results/scores.csv.

Run from project root:
    python scripts/score_results.py
"""

import sys
import os
import csv
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxml import etree
from src.validation import validate_x3d_string
from src.semantic_check import semantic_check
from src.x3duom_loader import get_x3duom
from scripts.tasks import TASKS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
OUTPUT_CSV = os.path.join(RESULTS_DIR, "scores.csv")

# Tags that are X3D document structure, not scene nodes tracked by X3DUOM
STRUCTURAL_TAGS = {
    "X3D", "Scene", "head", "meta", "component", "unit",
    "connect", "IS", "ProtoInterface", "ProtoBody",
    "ProtoDeclare", "ExternProtoDeclare", "ProtoInstance",
    "IMPORT", "EXPORT", "ROUTE", "field", "fieldValue",
}

# Attributes valid on any X3D node (not node-specific)
UNIVERSAL_ATTRS = {"DEF", "USE", "class", "id", "style", "containerField"}

FIELDNAMES = [
    "condition", "task_id", "level", "category",
    "parseable", "xsd_valid", "xsd_errors",
    "semantic_errors", "semantic_warnings", "semantic_info",
    "total_nodes", "hallucinated_nodes",
    "total_fields", "hallucinated_fields",
]


def parse_semantic_counts(report: str) -> tuple:
    """Extract (errors, warnings, info) integers from semantic_check output string."""
    def find(pattern):
        m = re.search(pattern, report, re.IGNORECASE)
        return int(m.group(1)) if m else 0

    return find(r"(\d+)\s+error"), find(r"(\d+)\s+warning"), find(r"(\d+)\s+info")


def check_hallucinations(x3d_xml: str, uom) -> tuple:
    """
    Returns (total_nodes, hallucinated_nodes, total_fields, hallucinated_fields).
    Hallucinated = not present in X3DUOM concrete or abstract node lists.
    """
    try:
        root = etree.fromstring(x3d_xml.encode())
    except Exception:
        return 0, 0, 0, 0

    total_nodes = hallucinated_nodes = 0
    total_fields = hallucinated_fields = 0

    for el in root.iter():
        tag = el.tag
        if not isinstance(tag, str):  # skip comments, PIs
            continue
        if "{" in tag:
            tag = tag.split("}", 1)[1]

        if tag in STRUCTURAL_TAGS:
            continue

        total_nodes += 1
        node_info = uom.get_node(tag)
        is_known = node_info is not None or tag in uom.abstract_node_types

        if not is_known:
            hallucinated_nodes += 1
            continue  # No point checking fields of an unknown node

        valid_fields = {f["name"] for f in uom.get_all_fields(tag)} | UNIVERSAL_ATTRS

        for attr in el.attrib:
            if "{" in attr:
                continue  # skip namespace-qualified attrs
            total_fields += 1
            if attr not in valid_fields:
                hallucinated_fields += 1

    return total_nodes, hallucinated_nodes, total_fields, hallucinated_fields


def score_file(filepath: str, uom) -> dict:
    result = {k: None for k in FIELDNAMES}

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()

    # Sentinel outputs written by run scripts on error
    if content.startswith("<!-- ERROR") or content.startswith("<!-- No output"):
        result.update({
            "parseable": False, "xsd_valid": False, "xsd_errors": 0,
            "semantic_errors": 0, "semantic_warnings": 0, "semantic_info": 0,
            "total_nodes": 0, "hallucinated_nodes": 0,
            "total_fields": 0, "hallucinated_fields": 0,
        })
        return result

    # Parse check
    try:
        etree.fromstring(content.encode())
        result["parseable"] = True
    except Exception:
        result["parseable"] = False
        result.update({
            "xsd_valid": False, "xsd_errors": 0,
            "semantic_errors": 0, "semantic_warnings": 0, "semantic_info": 0,
            "total_nodes": 0, "hallucinated_nodes": 0,
            "total_fields": 0, "hallucinated_fields": 0,
        })
        return result

    # XSD validation
    val = validate_x3d_string(content)
    result["xsd_valid"] = val.get("valid", False)
    result["xsd_errors"] = len(val.get("errors", []))

    # Semantic check
    try:
        report = semantic_check(content)
        e, w, i = parse_semantic_counts(report)
        result["semantic_errors"] = e
        result["semantic_warnings"] = w
        result["semantic_info"] = i
    except Exception as exc:
        result["semantic_errors"] = -1  # -1 = check failed
        result["semantic_warnings"] = 0
        result["semantic_info"] = 0
        print(f"      semantic_check failed: {exc}")

    # Hallucination check
    tn, hn, tf, hf = check_hallucinations(content, uom)
    result["total_nodes"] = tn
    result["hallucinated_nodes"] = hn
    result["total_fields"] = tf
    result["hallucinated_fields"] = hf

    return result


def run_scoring() -> None:
    print("Loading X3DUOM spec...")
    uom = get_x3duom()
    print("Spec loaded.\n")

    task_map = {t["id"]: t for t in TASKS}
    rows = []

    conditions = [
        ("Claude Sonnet 4.6", os.path.join(RESULTS_DIR, "baseline", "Claude Sonnet 4.6")),
        ("Gemini 3.1 Pro",    os.path.join(RESULTS_DIR, "baseline", "Gemini 3.1 Pro")),
        ("MCP",               os.path.join(RESULTS_DIR, "baseline", "mcp")),
    ]

    for condition, cond_dir in conditions:
        if not os.path.isdir(cond_dir):
            print(f"  [skip] {cond_dir} not found")
            continue

        files = sorted(f for f in os.listdir(cond_dir) if f.endswith(".x3d"))
        print(f"Scoring {len(files)} files in {condition}/")

        for fname in files:
            task_id = fname.replace(".x3d", "")
            task = task_map.get(task_id, {})

            scored = score_file(os.path.join(cond_dir, fname), uom)
            row = {
                "condition": condition,
                "task_id": task_id,
                "level": task.get("level", ""),
                "category": task.get("category", ""),
                **{k: scored.get(k) for k in FIELDNAMES if k not in ("condition", "task_id", "level", "category")},
            }
            rows.append(row)

            print(
                f"  {condition}/{task_id}: "
                f"parse={scored['parseable']} "
                f"xsd={scored['xsd_valid']} "
                f"sem_err={scored['semantic_errors']} "
                f"hall_nodes={scored['hallucinated_nodes']}/{scored['total_nodes']}"
            )

        print()

    if not rows:
        print("No results found. Run run_baseline.py and run_treatment.py first.")
        return

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Scores written to {OUTPUT_CSV}")


if __name__ == "__main__":
    run_scoring()
