"""
Treatment condition: Claude with x3d-mcp tools generates X3D from the same prompts.
Uses the MCP Python SDK to connect to server.py over stdio, then runs an agentic
tool-use loop via the Anthropic API.

Outputs saved to results/treatment/task_XX.x3d.

Run from project root:
    python scripts/run_treatment.py

Requires:
    pip install anthropic
    ANTHROPIC_API_KEY set in environment
    mcp[cli] already installed via pyproject.toml
"""

import sys
import os
import re
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from scripts.tasks import TASKS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "treatment")
MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 30  # max agentic loop turns per task

SYSTEM_PROMPT = """\
You are an expert X3D 4.0 author. You have access to x3d-mcp tools that let you look up \
the official X3D specification, generate valid nodes, build and validate scenes.

Workflow for each task:
1. Use x3d_scene_template to create the base scene document.
2. Use x3d_node_info to look up any node you are unsure about before generating it.
3. Use x3d_generate_node + x3d_add_node to build up the scene incrementally.
4. Use validate_x3d and x3d_semantic_check to verify correctness before finishing.
5. When the scene is complete and valid, output the final X3D XML document.

Output requirements:
- Return ONLY the complete X3D XML — no markdown fences, no explanation.
- The output must start with: <?xml version="1.0" encoding="UTF-8"?>
"""


def mcp_tool_to_anthropic(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


def extract_x3d(text: str) -> str:
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
    return ""


def extract_x3d_from_tool_results(messages: list) -> str:
    """Scan tool result messages in reverse for the most recent complete X3D."""
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in reversed(content):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                text = block.get("content", "")
                if isinstance(text, str) and ("<?xml" in text or "<X3D" in text):
                    x3d = extract_x3d(text)
                    if x3d:
                        return x3d
    return ""


async def run_task(
    task: dict,
    session: ClientSession,
    client: anthropic.Anthropic,
    tools: list,
) -> str:
    messages = [{"role": "user", "content": task["prompt"]}]

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Try to find X3D in the final assistant text
            for block in response.content:
                if hasattr(block, "text"):
                    x3d = extract_x3d(block.text)
                    if x3d:
                        return x3d

            # Not in assistant text — check tool results accumulated so far
            x3d = extract_x3d_from_tool_results(messages)
            if x3d:
                return x3d

            # Last resort: ask Claude to emit the final XML explicitly
            messages.append({
                "role": "user",
                "content": "Output the final complete X3D XML document now. Start with <?xml",
            })
            followup = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            for block in followup.content:
                if hasattr(block, "text"):
                    x3d = extract_x3d(block.text)
                    if x3d:
                        return x3d

            return ""

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    result = await session.call_tool(block.name, block.input)
                    content = (
                        result.content[0].text
                        if result.content
                        else "(empty result)"
                    )
                except Exception as e:
                    content = f"Tool call failed: {e}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })

            messages.append({"role": "user", "content": tool_results})

    # Max iterations hit — try to salvage from tool results
    return extract_x3d_from_tool_results(messages)


async def run_treatment(dry_run: bool = False) -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        cwd=PROJECT_ROOT,
    )

    client = anthropic.Anthropic()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"Treatment run — model: {MODEL}, tasks: {len(TASKS)}")
    print(f"Output dir: {RESULTS_DIR}\n")

    if dry_run:
        print("[dry-run] skipping MCP server startup and API calls")
        return

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = [mcp_tool_to_anthropic(t) for t in tools_result.tools]
            print(f"MCP server ready — {len(tools)} tools available\n")

            for task in TASKS:
                output_path = os.path.join(RESULTS_DIR, f"{task['id']}.x3d")

                if os.path.exists(output_path):
                    print(f"  [skip] {task['id']} — already exists")
                    continue

                label = f"{task['id']} (L{task['level']}/{task['category']})"
                print(f"  [{label}] {task['prompt'][:70]}...")

                try:
                    x3d = await run_task(task, session, client, tools)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(x3d if x3d else "<!-- No output produced -->")

                    status = "OK" if x3d.startswith("<?xml") else "WARN:no-xml-decl"
                    print(f"    [{status}] saved {len(x3d)} chars")
                    time.sleep(1.0)

                except Exception as e:
                    print(f"    [ERROR] {e}")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(f"<!-- ERROR: {e} -->")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(run_treatment(dry_run=dry))
