#!/usr/bin/env python3
"""Run the Playwright smoke tests against a throwaway local server.

Creates a fresh SQLite DB, applies migrations, starts Flask through the
webapp-testing skill's with_server.py, then runs pytest on tests/e2e.

    python scripts/run_e2e.py [extra pytest args]
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WITH_SERVER = ROOT / ".claude" / "skills" / "webapp-testing" / "scripts" / "with_server.py"
PORT = int(os.environ.get("E2E_PORT", "5055"))


def main() -> int:
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "e2e.db"
        env = {
            **os.environ,
            "AGRISENSE_ENV": "development",
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
            "E2E_BASE_URL": f"http://127.0.0.1:{PORT}",
        }
        subprocess.run([py, "-m", "flask", "--app", "wsgi", "db", "upgrade"], cwd=ROOT, env=env, check=True)
        server = f'"{py}" -m flask --app wsgi run --host 127.0.0.1 --port {PORT}'
        cmd = [py, str(WITH_SERVER), "--server", server, "--port", str(PORT),
               "--", py, "-m", "pytest", "tests/e2e", "-q", *sys.argv[1:]]
        try:
            return subprocess.run(cmd, cwd=ROOT, env=env).returncode
        finally:
            stop_orphaned_server()


def stop_orphaned_server() -> None:
    """with_server.py starts the server with shell=True. On Windows, stopping
    the shell leaves the Flask process running, so stop whatever still
    listens on our test port. Linux/CI doesn't need this."""
    if os.name != "nt":
        return
    script = (
        f"Get-NetTCPConnection -LocalPort {PORT} -State Listen -ErrorAction SilentlyContinue"
        " | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)


if __name__ == "__main__":
    sys.exit(main())
