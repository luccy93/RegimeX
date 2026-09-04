# =============================================================================
# RegimeX — Repository Quality Gate Script (PowerShell)
# scripts/quality-check.ps1
# =============================================================================
#
# Runs the full quality gate in order:
#   1. Backend: Ruff format check
#   2. Backend: Ruff lint
#   3. Backend: mypy type check
#   4. Backend: pytest
#   5. Frontend: ESLint
#   6. Frontend: TypeScript check
#
# Usage:
#   powershell scripts/quality-check.ps1
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
# =============================================================================

$ErrorActionPreference = "Continue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ApiDir = Join-Path $RepoRoot "apps\api"
$WebDir = Join-Path $RepoRoot "apps\web"

$FailedChecks = @()

function Run-Check {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host ""
    Write-Host "▶  $Name" -ForegroundColor Cyan
    try {
        & $Command
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅  $Name passed" -ForegroundColor Green
        } else {
            Write-Host "   ❌  $Name FAILED (exit code $LASTEXITCODE)" -ForegroundColor Red
            $script:FailedChecks += $Name
        }
    } catch {
        Write-Host "   ❌  $Name FAILED with error: $_" -ForegroundColor Red
        $script:FailedChecks += $Name
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  RegimeX Quality Gate (Windows / PowerShell)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

# 1. Backend: Ruff format check
Run-Check "Backend: Ruff format check" {
    Push-Location $ApiDir
    try { ruff format --check app/ tests/ } finally { Pop-Location }
}

# 2. Backend: Ruff lint
Run-Check "Backend: Ruff lint" {
    Push-Location $ApiDir
    try { ruff check app/ tests/ } finally { Pop-Location }
}

# 3. Backend: mypy type check
Run-Check "Backend: mypy type check" {
    Push-Location $ApiDir
    try { mypy app tests } finally { Pop-Location }
}

# 4. Backend: pytest
Run-Check "Backend: pytest" {
    Push-Location $ApiDir
    try { python -m pytest tests/ -v --tb=short } finally { Pop-Location }
}

# 5. Frontend: ESLint
Run-Check "Frontend: ESLint" {
    Push-Location $WebDir
    try { npm run lint } finally { Pop-Location }
}

# 6. Frontend: TypeScript check
Run-Check "Frontend: TypeScript check" {
    Push-Location $WebDir
    try { npm run type-check } finally { Pop-Location }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
if ($FailedChecks.Count -eq 0) {
    Write-Host "  ✅  All quality gates passed." -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    exit 0
} else {
    Write-Host "  ❌  $($FailedChecks.Count) check(s) failed:" -ForegroundColor Red
    foreach ($Check in $FailedChecks) {
        Write-Host "     • $Check" -ForegroundColor Red
    }
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
