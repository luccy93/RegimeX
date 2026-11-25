#!/usr/bin/env python3
"""RegimeX — Staging Readiness Preflight CLI.

scripts/staging_preflight.py
============================
Evaluates staging host, runtime, security, and release prerequisites before
collecting qualification evidence.

Usage:
    python scripts/staging_preflight.py [options]

Options:
    --format {text,json}    Output format (default: text)
    --output PATH           Write report to specified file path
    --strict                Enforce strict gate: treat any WARNING as failure
    --verbose               Print full check details in text output
    --commit-sha SHA        Explicit target commit SHA override
    --branch REF            Explicit target branch or ref override
    --manifest-path PATH    Path to release-manifest.json
    --repo-root PATH        Explicit path to repository root

Exit Codes:
    0: All mandatory and optional checks PASS (Staging is Ready)
    1: One or more checks FAIL (or WARNING in strict mode)
    2: One or more required checks are BLOCKED
    3: One or more mandatory checks are NOT_CONFIGURED
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure apps/api is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.staging_readiness import StagingPreflightInspector  # noqa: E402
from app.schemas.staging_readiness import CheckStatus  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="RegimeX Staging Readiness Preflight Inspector.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Report presentation format",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional file path to write generated preflight report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce strict gate: treat warnings as failures",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed evaluation per check",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="Explicit commit SHA to inspect (defaults to HEAD)",
    )
    parser.add_argument(
        "--branch",
        default="",
        help="Explicit branch name to inspect (defaults to current branch)",
    )
    parser.add_argument(
        "--manifest-path",
        default="",
        help="Path to release-manifest.json",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Path to repository root",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    manifest_path = Path(args.manifest_path).resolve() if args.manifest_path else None

    inspector = StagingPreflightInspector(
        repo_root=repo_root,
        commit_sha=args.commit_sha or None,
        branch=args.branch or None,
        manifest_path=manifest_path,
        strict=args.strict,
    )

    report = inspector.run_preflight()

    # Render presentation
    if args.format == "json":
        output_str = report.to_json(indent=2)
    else:
        output_str = inspector.to_text_report(report, verbose=args.verbose)

    print(output_str)

    # Optionally write to file
    if args.output:
        out_file = Path(args.output).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        # If outputting to json file or format is json, write json
        if out_file.suffix == ".json" and args.format != "json":
            out_file.write_text(report.to_json(indent=2), encoding="utf-8")
        else:
            out_file.write_text(output_str, encoding="utf-8")
        print(f"[INFO] Report written to: {out_file}", file=sys.stderr)

    # Determine exit code
    if report.overall_status == CheckStatus.PASS:
        return 0
    if report.overall_status == CheckStatus.BLOCKED:
        return 2
    if report.overall_status == CheckStatus.NOT_CONFIGURED:
        return 3
    # FAIL or strict WARNING
    return 1


if __name__ == "__main__":
    sys.exit(main())
