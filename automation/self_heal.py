"""Self-healing agent for the YouTube Daily Automation.

When the n8n workflow fails, this launches a Cursor coding agent pointed at the
project so it can read the helper scripts + workflow JSON, diagnose the failure,
and (optionally) fix it. By default it is *diagnose-only*: it writes a Markdown
report with root cause + a proposed patch and does NOT edit any files. Pass
``--apply`` to let the agent actually change files (recommended only once the repo
is under git so you can review the diff).

Usage (from the project root):
    python automation/self_heal.py --node "Render Video (Local FFmpeg)" \
        --message "ffmpeg: command not found"

    # or feed the whole error object as JSON (e.g. from n8n):
    echo '{"node":"...","message":"..."}' | python automation/self_heal.py --stdin

    # let the agent apply fixes directly:
    python automation/self_heal.py --node "..." --message "..." --apply
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from _common import PROJECT_ROOT, run_one_shot

REPORT_DIR = PROJECT_ROOT / "automation" / "heal_reports"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cursor self-healing agent for the YT automation.")
    p.add_argument("--node", default="unknown", help="Name of the n8n node that failed.")
    p.add_argument("--message", default="", help="Error message from the failed run.")
    p.add_argument("--stdin", action="store_true", help="Read a JSON error object from stdin (keys: node, message).")
    p.add_argument("--context-file", help="Path to a JSON file holding the error object (keys: node, message). Best for n8n wiring.")
    p.add_argument("--apply", action="store_true", help="Allow the agent to edit files (default: diagnose only).")
    return p.parse_args()


def _from_json_blob(raw: str, node: str, message: str) -> tuple[str, str]:
    raw = raw.strip()
    if not raw:
        return node, message
    try:
        data = json.loads(raw)
        node = data.get("node") or data.get("lastNodeExecuted") or node
        message = data.get("message") or data.get("error") or message
    except json.JSONDecodeError:
        message = message or raw
    return node, message


def load_context(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve (node, message) from CLI flags, a context file, or stdin."""
    node, message = args.node, args.message
    if args.context_file:
        node, message = _from_json_blob(Path(args.context_file).read_text(encoding="utf-8"), node, message)
    if args.stdin:
        node, message = _from_json_blob(sys.stdin.read(), node, message)
    return node, message


def build_prompt(node: str, message: str, apply: bool) -> str:
    edit_clause = (
        "You ARE allowed to edit files in this project to fix the problem. Make the "
        "smallest change that addresses the root cause."
        if apply
        else "Do NOT edit any files. Only investigate and report; include a proposed "
        "patch as a diff or code block in your answer."
    )
    return f"""You are the maintenance engineer for a YouTube automation project.

The project is an n8n workflow (`YouTube-Daily-Automation.json`) plus local Python
helper scripts in `scripts/` (tts_edge.py, render_video.py, generate_thumbnail.py).
It failed during its latest daily run.

Failed node: {node}
Error message: {message or "(none provided)"}

Investigate the likely root cause by reading the relevant helper script(s) and the
matching node parameters in the workflow JSON. Consider common causes: missing
executables on PATH (ffmpeg), missing Python packages (edge_tts), wrong file paths,
API/credential errors, or malformed model output.

{edit_clause}

End your response with a concise section titled "SUMMARY" containing:
1. Root cause (one or two sentences).
2. The fix (what to change, exactly).
3. Whether it is safe to auto-apply.
"""


def main() -> int:
    args = parse_args()
    node, message = load_context(args)

    print(f"[self-heal] investigating failure in node: {node!r}", flush=True)
    result = run_one_shot(build_prompt(node, message, args.apply), cwd=PROJECT_ROOT)

    report_text = getattr(result, "result", "") or ""
    status = getattr(result, "status", "unknown")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = REPORT_DIR / f"heal-{stamp}.md"
    report_path.write_text(
        f"# Self-heal report ({stamp})\n\n"
        f"- Failed node: `{node}`\n"
        f"- Error: {message or '(none)'}\n"
        f"- Agent status: `{status}`\n"
        f"- Apply mode: {args.apply}\n\n"
        f"---\n\n{report_text}\n",
        encoding="utf-8",
    )

    print(f"[self-heal] status={status}")
    print(f"[self-heal] report written to: {report_path}")

    # Run started but failed mid-flight -> distinct exit code for observability.
    return 0 if status == "finished" else 2


if __name__ == "__main__":
    raise SystemExit(main())
