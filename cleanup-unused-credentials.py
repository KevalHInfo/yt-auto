"""
Remove unused n8n credentials from the local SQLite DB.

n8n's `import:credentials` only upserts — it never deletes leftovers.
This script keeps only the credentials referenced by YouTube-Daily-Automation.json
and removes everything else (including decrypt-failing orphans).

Stop n8n before running. Restart after.
"""
from __future__ import annotations

import os
import sqlite3
import sys

# IDs that the current workflow still references
KEEP_IDS = {
    "TTc4vODzbyjX0MU1",  # YouTube account
    "N8L0EcpwiiFZIpBU",  # Google Sheets account
    "ZSExo67ptAa9VKFK",  # Google Drive account
    "ofUgu2LzCWB5Mflr",  # Gmail account
    "p1ZJOiKGhwVnGGQq",  # Header Auth account (Pexels)
    "1xzDiuRIOcvhKnqY",  # Bearer Auth account 2 (Groq)
    "nxMongoDbVideos01",  # MongoDB account
}

DB_PATH = os.path.join(os.path.expanduser("~"), ".n8n", "database.sqlite")


def main() -> int:
    if not os.path.isfile(DB_PATH):
        print(f"No n8n DB found at {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = list(conn.execute("SELECT id, name, type FROM credentials_entity ORDER BY name"))
        remove = [r for r in rows if r["id"] not in KEEP_IDS]
        keep = [r for r in rows if r["id"] in KEEP_IDS]

        print("Keeping:")
        for r in keep:
            print(f"  {r['name']} ({r['type']})")
        print("\nRemoving:")
        for r in remove:
            print(f"  {r['name']} ({r['type']})")

        if not remove:
            print("\nNothing to remove.")
            return 0

        ids = [r["id"] for r in remove]
        placeholders = ",".join("?" * len(ids))

        conn.execute(
            f"DELETE FROM shared_credentials WHERE credentialsId IN ({placeholders})",
            ids,
        )
        # credential_dependency may not exist on older n8n versions
        try:
            conn.execute(
                f"DELETE FROM credential_dependency WHERE credentialId IN ({placeholders})",
                ids,
            )
        except sqlite3.OperationalError:
            pass

        conn.execute(
            f"DELETE FROM credentials_entity WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()

        remaining = conn.execute("SELECT COUNT(*) AS n FROM credentials_entity").fetchone()["n"]
        print(f"\nDone. Removed {len(ids)} credential(s). Remaining: {remaining}")
        print("Restart n8n, then refresh Credentials in the UI.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
