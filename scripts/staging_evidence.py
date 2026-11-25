#!/usr/bin/env python3
"""RegimeX — Staging Infrastructure Evidence CLI.

scripts/staging_evidence.py
===========================
Collects reproducible, auditable evidence for Docker staging host capabilities,
GitHub/GHCR access, immutable release manifest validation, smoke test credentials,
and rollback readiness.

Usage:
    python scripts/staging_evidence.py [options]

Options:
    --format {text,json}    Report presentation format (default: json)
    --output PATH           Optional file path to write generated evidence report
    --strict                Enforce strict gate: treat any WARNING as failure
    --verbose               Print full evidence details in text output
    --commit-sha SHA        Explicit commit SHA override (defaults to HEAD)
    --manifest-path PATH    Path to release-manifest.json
    --repo-root PATH        Explicit path to repository root

Exit Codes:
    0: All checks PASS (or non-strict WARNING)
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

from app.core.staging_evidence import InfrastructureEvidenceCollector  # noqa: E402
from app.schemas.staging_readiness import CheckStatus, InfrastructureEvidenceReport  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="RegimeX Staging Infrastructure Evidence Collector.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="json",
        help="Report presentation format",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional file path to write generated evidence report",
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
        help="Print detailed evaluation per check in text output",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="Explicit commit SHA to inspect (defaults to HEAD)",
    )
    parser.add_argument(
        "--manifest-path",
        default="",
        help="Explicit path to release-manifest.json",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Explicit path to repository root",
    )
    return parser


def format_text_report(
    report: InfrastructureEvidenceReport, verbose: bool = False
) -> str:
    """Render human-readable text summary of infrastructure evidence."""
    lines: list[str] = [
        "=" * 78,
        "  REGIMEX — STAGING INFRASTRUCTURE READINESS EVIDENCE REPORT",
        "=" * 78,
        f"  Environment:         {report.environment}",
        f"  Repository:          {report.repository}",
        f"  Commit SHA:          {report.commit_sha or 'UNRESOLVED'}",
        f"  Timestamp:           {report.timestamp}",
        f"  Overall Status:      {report.overall_status.value}",
        f"  Is Ready:            {'YES' if report.is_ready else 'NO'}",
        f"  Strict Mode:         {'ENABLED' if report.strict_mode else 'DISABLED'}",
        f"  Live Qual Auth:      {report.live_qualification_authorized}",
        f"  Prod Deploy Auth:    {report.production_deployment_authorized}",
        "-" * 78,
        "  COMPONENT EVIDENCE BREAKDOWN",
        "-" * 78,
        (
            f"  [Docker]             {report.docker.status.value:<12} "
            f"Engine: {report.docker.engine_accessible} | "
            f"Compose: {report.docker.compose_available} | "
            f"Storage: {report.docker.available_storage_gb or 'N/A'} GB"
        ),
        (
            f"  [GitHub Access]      {report.github.status.value:<12} "
            f"CLI: {report.github.cli_available} | "
            f"Auth: {report.github.auth_status.value} | "
            f"Repo Access: {report.github.repository_accessible}"
        ),
        (
            f"  [GHCR Registry]      {report.ghcr.status.value:<12} "
            f"Registry: {report.ghcr.registry_url} | "
            f"Auth: {report.ghcr.auth_status.value} | "
            f"Pull Verified: {report.ghcr.pull_capability_verified}"
        ),
        (
            f"  [Release Manifest]   {report.release_manifest.status.value:<12} "
            f"Digests Verified: {report.release_manifest.immutable_digests_verified} | "
            f"Images: {len(report.release_manifest.images)}"
        ),
        (
            f"  [Smoke Credentials]  {report.smoke_credentials.status.value:<12} "
            f"Configured: {report.smoke_credentials.username_configured} | "
            f"Leak Detected: {report.smoke_credentials.production_secret_leak_detected}"
        ),
        (
            f"  [Rollback Readiness] {report.rollback.status.value:<12} "
            f"Backup Configured: {report.rollback.backup_configured} | "
            f"Runbooks: {report.rollback.recovery_runbook_verified}"
        ),
        (
            f"  [GPU Capability]     {report.gpu.status.value:<12} "
            f"Available: {report.gpu.gpu_available} | "
            f"Count: {report.gpu.device_count} (Optional)"
        ),
        "-" * 78,
    ]

    if report.failed_checks:
        lines.append("  FAILED CHECKS:")
        for item in report.failed_checks:
            lines.append(f"    - {item}")

    if report.blocked_checks:
        lines.append("  BLOCKED CHECKS:")
        for item in report.blocked_checks:
            lines.append(f"    - {item}")

    if report.warnings:
        lines.append("  ADVISORY WARNINGS:")
        for item in report.warnings:
            lines.append(f"    - {item}")

    if report.remediations:
        lines.append("  REMEDIATIONS:")
        for rem in report.remediations:
            lines.append(f"    -> {rem}")

    lines.append("=" * 78)
    return "\n".join(lines)


def main() -> int:
    """Execute evidence collection CLI and return exit code."""
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else None
    manifest_path = Path(args.manifest_path) if args.manifest_path else None
    commit_sha = args.commit_sha if args.commit_sha else None

    collector = InfrastructureEvidenceCollector(
        repo_root=repo_root,
        commit_sha=commit_sha,
        manifest_path=manifest_path,
        strict=args.strict,
    )

    report = collector.collect_full_evidence()

    if args.format == "json":
        output_str = report.to_json(indent=2)
    else:
        output_str = format_text_report(report, verbose=args.verbose)

    print(output_str)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(
                report.to_json(indent=2)
                if args.output.endswith(".json")
                else output_str
            )
        print(f"\n[Evidence Report written to {out_path}]", file=sys.stderr)

    # Determine exit code
    if report.overall_status == CheckStatus.PASS:
        return 0
    if report.overall_status == CheckStatus.WARNING:
        return 1 if args.strict else 0
    if report.overall_status == CheckStatus.BLOCKED:
        return 2
    if report.overall_status == CheckStatus.NOT_CONFIGURED:
        return 3
    return 1


if __name__ == "__main__":
    sys.exit(main())
