Param(
    [string]$DistroName = 'Ubuntu',
    [switch]$EnableFeatures = $true,
    [switch]$SetDefaultVersion2 = $true
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        throw 'This script must be run as Administrator.'
    }
}

function Write-Info($msg){ Write-Host "[WSL-INSTALL] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WSL-INSTALL] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[WSL-INSTALL] $msg" -ForegroundColor Red }

try {
    Assert-Admin

    if ($EnableFeatures) {
        Write-Info 'Enabling required Windows features (VMP + WSL)...'
        & dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        & dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        Write-Warn 'If prompted, restart the PC before proceeding.'
    }

    try {
        Write-Info 'Installing WSL (Store-based if available)...'
        if ($DistroName) {
            & wsl --install -d $DistroName
        } else {
            & wsl --install
        }
    } catch {
        Write-Warn 'wsl --install failed or not available. Ensure Windows is up to date.'
        throw
    }

    if ($SetDefaultVersion2) {
        Write-Info 'Setting WSL2 as default version...'
        & wsl --set-default-version 2
    }

    Write-Info 'Updating WSL...'
    & wsl --update 2>$null | Out-Null

    Write-Info 'WSL status:'
    & wsl --status
    Write-Info 'Installed distros:'
    & wsl -l -v
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}

