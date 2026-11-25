#!/usr/bin/env python3
"""RegimeX — Staging Readiness Gate Evaluator CLI.

scripts/evaluate_staging_readiness.py
=====================================
Hardened gate evaluator that unifies preflight readiness and concrete infrastructure
evidence to ensure all 6 core readiness policies are satisfied before live qualification.

Usage:
    python scripts/evaluate_staging_readiness.py [options]

Options:
    --preflight-report PATH Path to preflight report JSON (generated on-the-fly if omitted)
    --evidence-report PATH  Path to evidence report JSON (generated on-the-fly if omitted)
    --max-age-seconds SEC   Maximum allowable evidence age in seconds (default: 3600)
    --format {text,json}    Output presentation format (default: text)
    --output PATH           Optional file path to write generated gate report
    --strict                Enforce strict gate: treat any WARNING as failure
    --commit-sha SHA        Explicit commit SHA override (defaults to HEAD)
    --repo-root PATH        Explicit path to repository root

Exit Codes:
    0: Gate PASS (Staging is Ready for Live Qualification)
    1: Gate FAIL (Policy failures detected, or WARNING in strict mode)
    2: Gate BLOCKED (Required dependencies or infrastructure unavailable)
    3: Gate NOT_CONFIGURED (Mandatory configuration or secrets missing)
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
from app.core.staging_gates import StagingReadinessGateEvaluator  # noqa: E402
from app.core.staging_readiness import StagingPreflightInspector  # noqa: E402
from app.schemas.staging_readiness import (  # noqa: E402
    CheckStatus,
    InfrastructureEvidenceReport,
    StagingGateEvaluationReport,
    StagingPreflightReport,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="RegimeX Staging Readiness Hardened Gate Evaluator.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--preflight-report",
        default="",
        help="Path to staging preflight JSON report (generated on-the-fly if omitted)",
    )
    parser.add_argument(
        "--evidence-report",
        default="",
        help="Path to infrastructure evidence JSON report (generated on-the-fly if omitted)",
    )
    parser.add_argument(
        "--max-age-seconds",
        type=int,
        default=3600,
        help="Maximum allowable evidence report age in seconds",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output presentation format",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional file path to write generated gate report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce strict gate: treat warnings as failures",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="Explicit commit SHA override (defaults to HEAD)",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Explicit path to repository root",
    )
    return parser


def format_text_gate_report(report: StagingGateEvaluationReport) -> str:
    """Render human-readable text breakdown of staging gate policies."""
    lines: list[str] = [
        "=" * 78,
        "  REGIMEX — STAGING READINESS HARDENED GATE EVALUATION",
        "=" * 78,
        f"  Environment:         {report.environment}",
        f"  Repository:          {report.repository}",
        f"  Commit SHA:          {report.commit_sha or 'UNRESOLVED'}",
        f"  Evaluated At:        {report.evaluated_at}",
        f"  Overall Gate Status: {report.overall_status.value}",
        f"  Staging Ready:       {'YES (GATE OPEN)' if report.is_ready else 'NO (GATE CLOSED)'}",
        f"  Strict Mode:         {'ENABLED' if report.strict_mode else 'DISABLED'}",
        f"  Evidence Fresh:      {'YES' if report.evidence_is_fresh else 'NO'} "
        f"({report.evidence_freshness_seconds}s age)",
        f"  Live Qual Auth:      {report.live_qualification_authorized} (strictly enforced)",
        f"  Prod Deploy Auth:    {report.production_deployment_authorized} (strictly enforced)",
        "-" * 78,
        "  READINESS GATE POLICIES",
        "-" * 78,
    ]

    for p in report.gate_policies:
        lines.append(f"  [{p.status.value:<14}] {p.policy_id:<24} {p.policy_name}")
        lines.append(f"    Message: {p.message}")
        if p.remediation:
            lines.append(f"    Remediation: -> {p.remediation}")

    lines.append("-" * 78)

    if report.failed_policies:
        lines.append("  FAILED GATE POLICIES:")
        for item in report.failed_policies:
            lines.append(f"    - {item}")

    if report.blocked_policies:
        lines.append("  BLOCKED GATE POLICIES:")
        for item in report.blocked_policies:
            lines.append(f"    - {item}")

    if report.warnings:
        lines.append("  ADVISORY WARNINGS:")
        for item in report.warnings:
            lines.append(f"    - {item}")

    if report.remediations:
        lines.append("  ACTIONABLE REMEDIATIONS:")
        for rem in report.remediations:
            lines.append(f"    -> {rem}")

    lines.append("=" * 78)
    return "\n".join(lines)


def main() -> int:
    """Execute gate evaluator CLI and return standard exit code."""
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    commit_sha = args.commit_sha or None

    # Load or generate Preflight Report
    if args.preflight_report and Path(args.preflight_report).is_file():
        with open(args.preflight_report, encoding="utf-8") as f:
            preflight = StagingPreflightReport.model_validate_json(f.read())
    else:
        inspector = StagingPreflightInspector(
            repo_root=repo_root, commit_sha=commit_sha, strict=args.strict
        )
        preflight = inspector.run_preflight()

    # Load or generate Evidence Report
    if args.evidence_report and Path(args.evidence_report).is_file():
        with open(args.evidence_report, encoding="utf-8") as f:
            evidence = InfrastructureEvidenceReport.model_validate_json(f.read())
    else:
        collector = InfrastructureEvidenceCollector(
            repo_root=repo_root, commit_sha=commit_sha, strict=args.strict
        )
        evidence = collector.collect_full_evidence()

    # Evaluate Gates
    evaluator = StagingReadinessGateEvaluator(
        repo_root=repo_root,
        max_age_seconds=args.max_age_seconds,
        strict=args.strict,
    )
    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    if args.format == "json":
        output_str = report.to_json(indent=2)
    else:
        output_str = format_text_gate_report(report)

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
        print(f"\n[Gate Report written to {out_path}]", file=sys.stderr)

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
