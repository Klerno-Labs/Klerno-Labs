Param(
    [string]$NewUserName = 'somli',
    [string]$TemporaryPassword = 'ChangeMe!12345',
    [switch]$RemoveOldUser = $true
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg){ Write-Host "[WSL-SWITCH] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WSL-SWITCH] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[WSL-SWITCH] $msg" -ForegroundColor Red }

try {
    # Capture current default user in the default distro
    $OldUser = (wsl -e bash -lc 'whoami').Trim()
    if (-not $OldUser) { throw 'Unable to detect current WSL user via whoami.' }
    Write-Info "Current WSL user: $OldUser"

    if ($OldUser -eq $NewUserName) {
        Write-Warn "Old and new user are the same ('$NewUserName'). Skipping creation and removal."
        exit 0
    }

    # Create new user with no password prompt, then add to sudo
    Write-Info "Creating user '$NewUserName' (if missing) and adding to sudo..."
    wsl -u root -- bash -lc "id -u $NewUserName >/dev/null 2>&1 || adduser --disabled-password --gecos '' $NewUserName"
    wsl -u root -- bash -lc "usermod -aG sudo $NewUserName"

    # Set temporary password
    if ($TemporaryPassword -and $TemporaryPassword.Length -gt 0) {
        Write-Info "Setting temporary password for '$NewUserName'..."
        $escaped = $TemporaryPassword.Replace("'","'\''")
        wsl -u root -- bash -lc "echo '${NewUserName}:${escaped}' | chpasswd"
    } else {
        Write-Warn 'No temporary password set. Use passwd inside WSL to set one.'
    }

    # Try to set default user using the app-specific launcher
    $setDefaultSucceeded = $false
    $candidates = @('ubuntu','ubuntu2204','ubuntu2004','ubuntu1804')
    foreach ($exe in $candidates) {
        try {
            Write-Info "Trying '$exe config --default-user $NewUserName'..."
            & $exe config --default-user $NewUserName 2>$null
            if ($LASTEXITCODE -eq 0) { $setDefaultSucceeded = $true; break }
        } catch { }
    }

    if (-not $setDefaultSucceeded) {
        Write-Warn 'Could not use ubuntu launcher to set default user. Falling back to /etc/wsl.conf.'
        wsl -u root -- bash -lc "printf '[user]\ndefault=$NewUserName\n' > /etc/wsl.conf"
    }

    # Restart WSL to pick up default user change
    Write-Info 'Restarting WSL...'
    wsl --shutdown

    # Verify new default user
    $NowUser = (wsl -e bash -lc 'whoami').Trim()
    Write-Info "Default user after restart: $NowUser"

    if ($RemoveOldUser -and $OldUser -ne 'root' -and $OldUser -ne $NewUserName) {
        Write-Info "Removing old user '$OldUser' and its home..."
        try {
            wsl -u root -- bash -lc "deluser --remove-home '$OldUser'"
        } catch {
            Write-Warn "Failed to remove user '$OldUser': $($_.Exception.Message)"
        }
    } else {
        Write-Warn 'Skipping old user removal due to safety check or configuration.'
    }

    Write-Info 'Done. Use `wsl -e bash -lc "whoami"` to verify.'
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}
