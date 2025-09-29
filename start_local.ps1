# start_local.ps1
# Helper to create venv, install deps, and start the app (foreground logs)
# Run from project root (where this file is located)

param(
    [int]$Port = 8002
)

Set-StrictMode -Version Latest

Write-Host "== KLERNO LABS - Local Start Helper =="
Write-Host "Project dir: $(Get-Location)"

# Locate a Python executable
function Find-PythonExecutable {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "python"
    )
    foreach ($p in $candidates) {
        try {
            $which = & $p --version 2>$null
            if ($LASTEXITCODE -eq 0 -or $which) {
                return $p
            }
        }
        catch {
            continue
        }
    }
    return $null
}

$pythonExe = Find-PythonExecutable
if (-not $pythonExe) {
    Write-Host "No Python executable found on PATH or standard locations. Install Python 3.11 and re-run." -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $pythonExe"

$venvPath = ".\.venv-py311"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment at $venvPath..."
    & $pythonExe -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment." -ForegroundColor Red
        exit 2
    }
}

Write-Host "Upgrading pip in venv..."
& $venvPython -m pip install --upgrade pip setuptools wheel

Write-Host "Installing project requirements... (this may take a few minutes)"
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ pip install failed. Check the output above for errors." -ForegroundColor Red
    exit 3
}

Write-Host "Starting uvicorn (foreground). Ctrl+C to stop. Logs will be printed below."
Write-Host "Starting uvicorn (foreground). Ctrl+C to stop. Logs will be printed below and written to start_local.log"
# Run uvicorn and tee output to a log file so we can inspect failures after the run.
$logFile = Join-Path (Get-Location) 'start_local.log'
Write-Host "Logging to: $logFile"

# Ensure Python and the child process use UTF-8 for IO to avoid Windows console encoding issues
# This sets the Python UTF-8 mode and the IO encoding so emoji and other unicode can be written
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# Ensure the PowerShell console output encoding is UTF-8 for the lifetime of this process
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
}
catch {
    # Best-effort: some hosts may not allow changing encoding
}
$OutputEncoding = New-Object System.Text.UTF8Encoding $false

# Launch uvicorn under the venv Python (stdout/stderr piped to Tee-Object)
& $venvPython -m uvicorn enterprise_main_v2:app --host 127.0.0.1 --port $Port --log-level debug 2>&1 | Tee-Object -FilePath $logFile

Write-Host "uvicorn exited. Check start_local.log for full logs."
