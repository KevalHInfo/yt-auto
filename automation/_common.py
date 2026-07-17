"""Shared helpers for the Cursor-agent automation scripts.

Both ``self_heal.py`` and ``generate_script.py`` run a Cursor coding agent via
the ``cursor-sdk`` package. This module centralises credential loading, model
selection and the two distinct failure modes the SDK exposes so the entry-point
scripts stay small.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Project root = parent of the automation/ directory this file lives in.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where the n8n workflow reads/writes its working files on this machine.
# Portable across machines/users: honor the same YT_TMP_DIR the workflow uses,
# otherwise default under the current user's home profile.
TMP_DIR = Path(os.environ.get("YT_TMP_DIR") or (Path.home() / ".n8n-files" / "tmp"))


def get_api_key() -> str:
    """Return the Cursor API key from the environment, or exit with guidance.

    The key is intentionally *never* read from a file in the repo so it cannot be
    committed by accident. Set it once with:  setx CURSOR_API_KEY "cursor_..."
    """
    key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not key:
        sys.stderr.write(
            "ERROR: CURSOR_API_KEY is not set.\n"
            'Set it once (PowerShell):  setx CURSOR_API_KEY "cursor_...yourkey..."\n'
            "then open a new terminal so the variable is available.\n"
        )
        sys.exit(1)
    return key


def get_model() -> str:
    """Model id for the agent. Override with the CURSOR_MODEL env var.

    Defaults to "auto" so the server picks a model the account has access to,
    avoiding hard-coded ids that may not be enabled for this key.
    """
    return os.environ.get("CURSOR_MODEL", "auto").strip() or "auto"


def run_one_shot(prompt: str, cwd: Path):
    """Run a single-shot Cursor agent and return its RunResult.

    Distinguishes the two SDK failure modes:
      * ``CursorAgentError`` -> the run never started (auth/config/network).
      * ``result.status == "error"`` -> the run started but failed mid-flight.
    Startup failures exit 1; run failures are handled by the caller via status.
    """
    # Imported lazily so `--help` and arg parsing work even if the SDK is missing.
    from cursor_sdk import Agent, AgentOptions, LocalAgentOptions, CursorAgentError

    cwd.mkdir(parents=True, exist_ok=True)

    try:
        return Agent.prompt(
            prompt,
            AgentOptions(
                api_key=get_api_key(),
                model=get_model(),
                local=LocalAgentOptions(cwd=str(cwd)),
            ),
        )
    except CursorAgentError as err:
        retryable = getattr(err, "is_retryable", None)
        sys.stderr.write(
            f"Cursor agent failed to start: {err}\n"
            f"retryable={retryable}\n"
        )
        sys.exit(1)
