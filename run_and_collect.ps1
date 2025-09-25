# run_and_collect.ps1
# Starts the local helper, waits briefly to capture startup logs, then stops the process
# and prints the generated logs. Run from project root.
param(
    [int]$WaitSeconds = 8
)

Write-Host "Running start_local.ps1, waiting $WaitSeconds seconds to capture startup logs..."

$startScript = Join-Path (Get-Location) 'start_local.ps1'
if (-not (Test-Path $startScript)) {
    Write-Host "start_local.ps1 not found in current directory" -ForegroundColor Red
    exit 2
}

# Start start_local.ps1 in a separate PowerShell process
$proc = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',"& '$startScript'" -PassThru

Start-Sleep -Seconds $WaitSeconds

# If still running, attempt to stop (Ctrl+C equivalent)
if (-not $proc.HasExited) {
    try {
        Write-Host "Stopping process (after $WaitSeconds s)..."
        $proc.Kill()
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "Failed to stop process: $_"
    }
}

Write-Host "\n=== start_local.log (tail) ==="
if (Test-Path 'start_local.log') { Get-Content start_local.log -Tail 400 } else { Write-Host 'start_local.log not found' }

Write-Host "\n=== logs\enterprise.log (tail) ==="
if (Test-Path 'logs\enterprise.log') { Get-Content 'logs\enterprise.log' -Tail 400 } else { Write-Host 'logs\enterprise.log not found' }

Write-Host "\n=== End of logs ==="
