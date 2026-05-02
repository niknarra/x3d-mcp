"""
Baseline condition: Claude with no tools generates X3D from natural language prompts.
Outputs saved to results/baseline/task_XX.x3d.

Run from project root:
    python scripts/run_baseline.py

Requires:
    pip install anthropic
    ANTHROPIC_API_KEY set in environment
"""

import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from scripts.tasks import TASKS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "baseline")
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are an expert X3D 4.0 author. Your task is to generate valid X3D 4.0 XML scenes.

When given a scene description, output ONLY the complete X3D XML document.
Requirements:
- Start with: <?xml version="1.0" encoding="UTF-8"?>
- Use X3D 4.0 with profile="Interchange" or appropriate profile
- Do NOT include markdown code fences, explanations, or comments outside the XML
- The output must be parseable XML
"""


def extract_x3d(text: str) -> str:
    """Strip markdown fences and find the XML content."""
    text = text.strip()
    match = re.search(r"```(?:xml)?\s*([\s\S]+?)```", text)
    if match:
        return match.group(1).strip()
    idx = text.find("<?xml")
    if idx >= 0:
        return text[idx:]
    idx = text.find("<X3D")
    if idx >= 0:
        return text[idx:]
    return text


def run_baseline(dry_run: bool = False) -> None:
    client = anthropic.Anthropic()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"Baseline run — model: {MODEL}, tasks: {len(TASKS)}")
    print(f"Output dir: {RESULTS_DIR}\n")

    for task in TASKS:
        output_path = os.path.join(RESULTS_DIR, f"{task['id']}.x3d")

        if os.path.exists(output_path):
            print(f"  [skip] {task['id']} — already exists")
            continue

        label = f"{task['id']} (L{task['level']}/{task['category']})"
        print(f"  [{label}] {task['prompt'][:70]}...")

        if dry_run:
            print("    [dry-run] skipping API call")
            continue

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": task["prompt"]}],
            )

            raw = response.content[0].text if response.content else ""
            x3d = extract_x3d(raw)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(x3d)

            status = "OK" if x3d.startswith("<?xml") else "WARN:no-xml-decl"
            print(f"    [{status}] saved {len(x3d)} chars")
            time.sleep(0.5)

        except Exception as e:
            print(f"    [ERROR] {e}")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"<!-- ERROR: {e} -->")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    run_baseline(dry_run=dry)
