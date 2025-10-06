param(
    [string]$BaseUrl = "http://127.0.0.1:8010",
    [int]$Retries = 3,
    [int]$DelayMs = 500
)

$paths = @("/", "/health", "/docs", "/api/neon/notes")

function Test-Path {
    param(
        [string]$Url
    )
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 10 -ErrorAction Stop
        return $resp.StatusCode
    }
    catch {
        if ($_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode
        }
        else {
            return "unreachable: $($_.Exception.GetType().Name)"
        }
    }
}

$ok = $true
for ($i = 1; $i -le $Retries; $i++) {
    Write-Host "Attempt $i of $Retries"
    foreach ($p in $paths) {
        $full = "$BaseUrl$p"
        $code = Test-Path -Url $full
        Write-Host "  $p -> $code"
        if ($code -eq 404 -or ($code -is [string] -and $code.StartsWith("unreachable"))) {
            $ok = $false
        }
    }
    if ($ok) { break }
    Start-Sleep -Milliseconds $DelayMs
}

if (-not $ok) {
    Write-Error "Smoke test failed due to 404 or unreachable endpoints."
    exit 1
}
Write-Host "Smoke test passed: no 404/unreachable."
