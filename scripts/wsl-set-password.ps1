Param(
    [Parameter(Mandatory=$true)][string]$User,
    [Parameter(Mandatory=$true)][string]$Password
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg){ Write-Host "[WSL-PASS] $msg" -ForegroundColor Cyan }
function Write-Err($msg){ Write-Host "[WSL-PASS] $msg" -ForegroundColor Red }

try {
    Write-Info "Setting password for '$User'..."
    $escaped = $Password.Replace("'","'\''")
    wsl -u root -- bash -lc "echo '${User}:${escaped}' | chpasswd"
    Write-Info 'Verifying:'
    wsl -u root -- bash -lc "passwd -S ${User}"
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}

