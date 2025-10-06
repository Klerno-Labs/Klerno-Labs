param(
    [Parameter(Mandatory = $false)]
    [string]$Key,
    [switch]$Persist,
    [switch]$SessionOnly
)

# Prompt securely if no key provided as argument
if (-not $Key) {
    Write-Host "Enter Neon API key (input hidden):"
    $secure = Read-Host -AsSecureString
    $Key = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

if (-not $Key) {
    Write-Error "NEON_API_KEY is empty. Aborting."
    exit 1
}

# Always set for current session
$env:NEON_API_KEY = $Key

if ($Persist -and -not $SessionOnly) {
    [System.Environment]::SetEnvironmentVariable('NEON_API_KEY', $Key, 'User')
    Write-Host "NEON_API_KEY persisted to User environment."
    Write-Host "You may need to restart VS Code or terminals for the change to be picked up."
}
elseif ($SessionOnly) {
    Write-Host "NEON_API_KEY set for current session only (not persisted)."
}
else {
    # Default behavior: set for current session and persist
    [System.Environment]::SetEnvironmentVariable('NEON_API_KEY', $Key, 'User')
    Write-Host "NEON_API_KEY set for current session and persisted to User environment."
    Write-Host "You may need to restart VS Code or terminals for the change to be picked up."
}
