<#
start_local.ps1 (wrapper)
Canonical local start script that delegates to scripts/start_local.ps1 to avoid duplication.
Run from project root: .\start_local.ps1
#>

param(
    [int]$Port = 0
)

Set-StrictMode -Version Latest

$delegate = Join-Path $PSScriptRoot 'scripts\start_local.ps1'
if (Test-Path $delegate) {
    Write-Host "Delegating to scripts/start_local.ps1 ..."
    if ($Port -gt 0) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $delegate -Port $Port
    }
    else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $delegate
    }
    exit $LASTEXITCODE
}

# Fallback: run the canonical Python launcher
Write-Host "scripts/start_local.ps1 not found, falling back to python scripts/run_local.py"

$candidates = @(
    ".\\.venv-1\\Scripts\\python.exe",
    ".\\.venv-py311\\Scripts\\python.exe",
    ".\\.venv-3.11\\Scripts\\python.exe",
    ".\\.venv\\Scripts\\python.exe",
    "python"
)
$py = $null
foreach ($p in $candidates) { if (Get-Command $p -ErrorAction SilentlyContinue) { $py = $p; break } }
if (-not $py) { $py = "python" }

if ($Port -gt 0) { $env:LOCAL_PORT = "$Port" }
& $py "scripts/run_local.py"
exit $LASTEXITCODE
