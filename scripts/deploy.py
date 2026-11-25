#!/usr/bin/env python3
"""RegimeX — Automated Production Deployment CLI.

scripts/deploy.py
=================
CLI entrypoint delegating to app.core.deployment orchestrator.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure apps/api is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.deployment import main

if __name__ == "__main__":
    sys.exit(main())
