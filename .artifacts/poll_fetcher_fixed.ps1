# Robust poller for GitHub Actions run logs
# Calls the repo fetcher script directly (no nested powershell) and checks
# for a completed CI run log (contains pytest short test summary or failures).

param(
    [int]$MaxIterations = 40,
    [int]$SleepSeconds = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

Write-Output "[poll_fetcher_fixed] starting: MaxIterations=$MaxIterations, SleepSeconds=$SleepSeconds"

for ($i = 1; $i -le $MaxIterations; $i++) {
    Write-Output "[poll] iter $i/$MaxIterations at $(Get-Date -Format o)"
    try {
        # Call the fetcher script directly (avoid starting new powershell instances)
        $fetcher = Join-Path -Path $PSScriptRoot -ChildPath "..\scripts\list_and_fetch.ps1"
        if (Test-Path $fetcher) {
            Write-Output "[poll] running fetcher: $fetcher"
            & $fetcher
            Write-Output "[poll] fetcher returned exit code: $LASTEXITCODE"
        }
        else {
            Write-Warning "fetcher not found at $fetcher"
        }
    }
    catch {
        Write-Warning "fetcher call failed: $_"
    }

    # Look for the newest non-empty run-*.log under this .artifacts folder
    try {
        $latest = Get-ChildItem -Path (Join-Path $PSScriptRoot 'run-*.log') -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt 0 } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    }
    catch {
        $latest = $null
    }

    if ($null -ne $latest) {
        Write-Output "[poll] newest non-empty: $($latest.Name) ($($latest.Length) bytes)"
        $text = ''
        try { $text = Get-Content $latest.FullName -Raw -ErrorAction Stop } catch { $text = '' }
        # Match common completion markers: pytest short summary, failures, GH Actions error, or a numeric "N passed" summary
        if ($text -match 'short test summary|=== FAILURES ===|##\[error\]Process completed|Process completed with exit code|\b\d+\s+passed\b|Smoke tests passed') {
            Write-Output "[poll] completed run detected: $($latest.FullName)"
            Set-Content -Path (Join-Path $PSScriptRoot 'latest_completed_run.txt') -Value $latest.FullName -Force
            exit 0
        }
        else {
            Write-Output "[poll] newest non-empty doesn't look complete yet"
        }
    }
    else {
        Write-Output "[poll] no non-empty run logs found yet"
    }

    Start-Sleep -Seconds $SleepSeconds
}

Write-Output "[poll] timeout after $MaxIterations iterations"
exit 2
