#!/usr/bin/env python3
"""Start a server, wait until its port answers, run a command, then stop the server.

    python scripts/with_server.py --server "flask run --port 5055" --port 5055 -- pytest tests/e2e
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time


def wait_for_port(port: int, timeout: float) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        with socket.socket() as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True, help="shell command that starts the server")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        ap.error("no command given after --")

    server = subprocess.Popen(args.server, shell=True)
    try:
        if not wait_for_port(args.port, args.timeout):
            print(f"server didn't open port {args.port} in {args.timeout:.0f}s", file=sys.stderr)
            return 1
        return subprocess.run(cmd).returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
