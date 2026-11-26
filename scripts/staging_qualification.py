#!/usr/bin/env python3
"""RegimeX — Controlled Staging Qualification CLI.

scripts/staging_qualification.py
================================
Executes the Volume V27 controlled staging qualification orchestrator against
validated Volume V26 preflight, infrastructure evidence, and readiness gates.

Usage:
    python scripts/staging_qualification.py [options]

Options:
    --environment NAME          Target environment (must be 'staging')
    --commit-sha SHA            40-character hexadecimal git commit SHA
    --preflight-report PATH     Path to V26 StagingPreflightReport JSON
    --evidence-report PATH      Path to V26 InfrastructureEvidenceReport JSON
    --staging-api-url URL       Explicit staging backend base URL
    --staging-web-url URL       Explicit staging frontend base URL
    --max-age-seconds SEC       Maximum allowable V26 evidence age (default: 3600)
    --output PATH               Optional file path to write qualification report
    --format {json,text}        Output format (default: text)
    --dry-run                   Validate prerequisites without network requests
    --strict                    Escalate advisory warnings to qualification failures
    --repo-root PATH            Explicit path to repository root

Exit Codes:
    0: Qualification PASS (or valid dry-run / non-strict WARNING)
    1: Qualification FAIL (or WARNING in strict mode)
    2: Prerequisites BLOCKED (e.g. V26 gates blocked or missing report artifact)
    3: Missing Configuration (NOT_CONFIGURED staging target or V26 config)
    4: Invalid Arguments (e.g. non-staging/production environment or malformed SHA)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

# Ensure apps/api is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.staging_qualification import StagingQualificationOrchestrator  # noqa: E402
from app.schemas.staging_readiness import (  # noqa: E402
    QualificationStatus,
    StagingQualificationReport,
)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BLOCKED = 2
EXIT_NOT_CONFIGURED = 3
EXIT_INVALID_ARGS = 4


class QualificationArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that exits with EXIT_INVALID_ARGS (4) on parse errors."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(EXIT_INVALID_ARGS, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = QualificationArgumentParser(
        description="RegimeX Controlled Staging Qualification Orchestrator (V27).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--environment",
        default="staging",
        help="Target qualification environment (only 'staging' is allowed)",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="40-character commit SHA to qualify (defaults to env/git HEAD when omitted)",
    )
    parser.add_argument(
        "--preflight-report",
        default="",
        help="Path to V26 staging preflight JSON report",
    )
    parser.add_argument(
        "--evidence-report",
        default="",
        help="Path to V26 infrastructure evidence JSON report",
    )
    parser.add_argument(
        "--staging-api-url",
        default="",
        help="Explicit staging backend URL (overrides STAGING_API_URL)",
    )
    parser.add_argument(
        "--staging-web-url",
        default="",
        help="Explicit staging frontend URL (overrides STAGING_WEB_URL)",
    )
    parser.add_argument(
        "--max-age-seconds",
        type=int,
        default=3600,
        help="Maximum allowable V26 evidence age in seconds",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional file path to write generated qualification report",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output presentation format",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and gates without making network requests",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat advisory warnings as qualification failures",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Explicit path to repository root",
    )
    return parser


def format_text_qualification_report(report: StagingQualificationReport) -> str:
    """Render human-readable text summary of a staging qualification report."""
    lines: list[str] = [
        "=" * 78,
        "  REGIMEX — CONTROLLED STAGING QUALIFICATION REPORT (V27)",
        "=" * 78,
        f"  Run ID:              {report.run_id}",
        f"  Environment:         {report.environment.name}",
        f"  Repository:          {report.repository}",
        f"  Commit SHA:          {report.commit_sha or 'UNRESOLVED'}",
        f"  Release Tag:         {report.release_tag}",
        f"  Dry-Run Mode:        {'ENABLED' if report.run_metadata.dry_run else 'DISABLED'}",
        f"  Strict Mode:         {'ENABLED' if report.run_metadata.strict_mode else 'DISABLED'}",
        f"  Overall Status:      {report.overall_status.value}",
        f"  Lifecycle:           requested={report.qualification_requested} | "
        f"started={report.qualification_started} | completed={report.qualification_completed}",
        f"  Outcome Flags:       passed={report.qualification_passed} | "
        f"blocked={report.qualification_blocked} | failed={report.qualification_failed}",
        f"  V26 Gates:           preflight={report.v26_preflight_status.value} | "
        f"evidence={report.v26_evidence_status.value} | "
        f"gate={report.v26_gate_status.value} (ready={report.v26_gate_passed})",
        f"  Governance:          live_qual_auth={report.live_qualification_authorized} | "
        f"prod_deploy_auth={report.production_deployment_authorized} | "
        f"images_published={report.container_images_published}",
        "-" * 78,
    ]

    if report.stages:
        lines.append("  QUALIFICATION STAGES")
        lines.append("-" * 78)
        for st in report.stages:
            lines.append(
                f"  [{st.status.value:<14}] {st.stage_id:<24} {st.name} "
                f"({st.duration_seconds:.3f}s)"
            )
            lines.append(f"    Message: {st.message}")
            if st.error:
                lines.append(f"    Error:   {st.error}")
        lines.append("-" * 78)

    if report.error_message:
        lines.append(f"  ERROR: {report.error_message}")

    if report.failed_checks:
        lines.append("  FAILED CHECKS:")
        for item in report.failed_checks:
            lines.append(f"    - {item}")

    if report.blocked_checks:
        lines.append("  BLOCKED CHECKS:")
        for item in report.blocked_checks:
            lines.append(f"    - {item}")

    if report.warnings:
        lines.append("  WARNINGS:")
        for item in report.warnings:
            lines.append(f"    - {item}")

    if report.remediations:
        lines.append("  REMEDIATIONS:")
        for rem in report.remediations:
            lines.append(f"    -> {rem}")

    lines.append("=" * 78)
    return "\n".join(lines)


def resolve_exit_code(report: StagingQualificationReport, *, strict: bool = False) -> int:
    """Map StagingQualificationReport outcome to a deterministic CLI exit code."""
    if not report.qualification_started and report.overall_status == QualificationStatus.FAIL:
        return EXIT_INVALID_ARGS

    if report.overall_status == QualificationStatus.PASS:
        return EXIT_SUCCESS
    if report.overall_status == QualificationStatus.WARNING:
        return EXIT_FAILURE if strict else EXIT_SUCCESS
    if report.overall_status == QualificationStatus.NOT_RUN:
        if report.run_metadata.dry_run and not report.failed_checks and not report.blocked_checks:
            return EXIT_SUCCESS
        return EXIT_BLOCKED
    if report.overall_status == QualificationStatus.BLOCKED:
        return EXIT_BLOCKED
    if report.overall_status == QualificationStatus.NOT_CONFIGURED:
        return EXIT_NOT_CONFIGURED
    return EXIT_FAILURE


def main(argv: list[str] | None = None) -> int:
    """Execute staging qualification CLI and return deterministic exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_age_seconds <= 0:
        print("error: --max-age-seconds must be a positive integer", file=sys.stderr)
        return EXIT_INVALID_ARGS

    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    preflight_path = Path(args.preflight_report) if args.preflight_report else None
    evidence_path = Path(args.evidence_report) if args.evidence_report else None
    commit_sha: str | None = args.commit_sha if args.commit_sha else None

    orchestrator = StagingQualificationOrchestrator(
        repo_root=repo_root,
        environment=args.environment,
        commit_sha=commit_sha,
        preflight_report_path=preflight_path,
        evidence_report_path=evidence_path,
        staging_api_url=args.staging_api_url or None,
        staging_web_url=args.staging_web_url or None,
        max_age_seconds=args.max_age_seconds,
        dry_run=args.dry_run,
        strict=args.strict,
    )

    report = orchestrator.run_qualification()

    output_str = (
        report.to_json(indent=2)
        if args.format == "json"
        else format_text_qualification_report(report)
    )
    print(output_str)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            report.to_json(indent=2) if args.output.endswith(".json") else output_str,
            encoding="utf-8",
        )
        print(f"\n[Qualification Report written to {out_path}]", file=sys.stderr)

    return resolve_exit_code(report, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
