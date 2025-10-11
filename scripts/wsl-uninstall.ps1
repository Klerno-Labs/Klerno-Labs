Param(
    [switch]$BackupDistros = $false,
    [switch]$UnregisterAll = $true,
    [switch]$AutoRestart = $false
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        throw 'This script must be run as Administrator.'
    }
}

function Write-Info($msg){ Write-Host "[WSL-UNINSTALL] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WSL-UNINSTALL] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[WSL-UNINSTALL] $msg" -ForegroundColor Red }

try {
    Assert-Admin

    Write-Info 'Checking installed WSL distros...'
    $distros = & wsl -l -q 2>$null | Where-Object { $_ -and $_.Trim() -ne '' }

    if ($BackupDistros -and $distros -and $distros.Count -gt 0) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $downloads = Join-Path $env:USERPROFILE 'Downloads'
        foreach ($d in $distros) {
            $out = Join-Path $downloads ("$($d)-backup-$stamp.tar")
            Write-Info "Exporting '$d' to '$out'..."
            & wsl --export $d $out
        }
    }

    Write-Info 'Shutting down WSL...'
    & wsl --shutdown 2>$null | Out-Null

    if ($UnregisterAll -and $distros -and $distros.Count -gt 0) {
        foreach ($d in $distros) {
            Write-Warn "Unregistering distro '$d' (this deletes its data)..."
            & wsl --unregister $d
        }
    } else {
        Write-Warn 'Skipping distro unregister. Use -UnregisterAll to remove installed distros.'
    }

    $uninstallSupported = $false
    try {
        Write-Info 'Attempting `wsl --uninstall` (Windows 11 Store-based WSL)...'
        & wsl --uninstall
        if ($LASTEXITCODE -eq 0) { $uninstallSupported = $true }
    } catch {
        $uninstallSupported = $false
    }

    if (-not $uninstallSupported) {
        Write-Info 'Falling back to disabling Windows features via DISM...'
        & dism /online /disable-feature /featurename:VirtualMachinePlatform /norestart
        & dism /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart
        Write-Warn 'A restart is typically required to complete feature removal.'
    }

    if ($AutoRestart) {
        Write-Info 'Restarting computer now...'
        Restart-Computer -Force
    } else {
        Write-Info 'Uninstall stage complete. Please restart your PC before reinstalling.'
    }
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}

