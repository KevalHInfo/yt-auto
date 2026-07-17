"""OPTIONAL: generate a YouTube video script with a Cursor agent.

This is an *alternative* to the workflow's `Generate Script (Groq)` node. Using a
coding agent as a text generator is off-label (slower and pricier than a plain
chat LLM), so Groq stays the default. This exists so you can A/B the quality.

It prints a single JSON object to stdout matching the contract the rest of the
workflow expects, so an n8n `executeCommand` node can consume it directly:
    { "title": str, "description": str,
      "sections": [ {"heading": str, "content": str}, ... ],
      "script": str }

Usage:
    python automation/generate_script.py "Why Rust is taking over systems programming"
    echo "Some topic" | python automation/generate_script.py
    python automation/generate_script.py "Topic" --out C:/path/script.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from _common import TMP_DIR, run_one_shot

REQUIRED_KEYS = ("title", "description", "sections", "script")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a YouTube script via a Cursor agent.")
    p.add_argument("topic", nargs="?", help="Video topic (or pipe it via stdin).")
    p.add_argument("--out", help="Also write the JSON to this file path.")
    return p.parse_args()


def resolve_topic(args: argparse.Namespace) -> str:
    topic = (args.topic or "").strip()
    if not topic and not sys.stdin.isatty():
        topic = sys.stdin.read().strip()
    if not topic:
        sys.stderr.write("ERROR: no topic provided (pass as an argument or via stdin).\n")
        sys.exit(1)
    return topic


def build_prompt(topic: str) -> str:
    return (
        "You are a YouTube script writer. Write a short educational YouTube video "
        f"script about: {topic}.\n\n"
        "Do NOT create or edit any files. Respond in your final message with ONLY "
        "valid JSON (no markdown fences, no commentary) with exactly these four keys:\n"
        '  "title": a catchy video title (string)\n'
        '  "description": a 1-2 sentence YouTube description (string)\n'
        '  "sections": an array of objects, each with "heading" and "content" strings\n'
        '  "script": the full spoken narration as ONE plain-text string (no quotes '
        "around sentences, no markdown headings, one continuous block).\n"
    )


def extract_json(text: str) -> dict:
    """Pull the JSON object out of the agent's final message, tolerating fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to the largest {...} span in the message.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def main() -> int:
    args = parse_args()
    topic = resolve_topic(args)

    print(f"[script] generating script for topic: {topic!r}", file=sys.stderr, flush=True)
    result = run_one_shot(build_prompt(topic), cwd=TMP_DIR)

    status = getattr(result, "status", "unknown")
    text = getattr(result, "result", "") or ""
    if status != "finished":
        sys.stderr.write(f"Agent run did not finish (status={status}). Raw:\n{text}\n")
        return 2

    try:
        parsed = extract_json(text)
    except json.JSONDecodeError:
        sys.stderr.write(f"Agent did not return valid JSON. Raw:\n{text}\n")
        return 2

    missing = [k for k in REQUIRED_KEYS if k not in parsed]
    if missing:
        sys.stderr.write(f"Parsed JSON missing keys {missing}. Got: {json.dumps(parsed)[:500]}\n")
        return 2

    out_json = json.dumps(parsed, ensure_ascii=False)
    print(out_json)  # stdout = the machine-readable result
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)
        print(f"[script] written to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
