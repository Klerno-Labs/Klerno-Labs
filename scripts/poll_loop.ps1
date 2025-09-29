# Wrapper to run poll_artifacts.ps1 repeatedly until artifact is found or timeout
param(
    [int]$Attempts = 12,
    [int]$SleepSeconds = 15
)

for ($i = 1; $i -le $Attempts; $i++) {
    Write-Host "Polling attempt $i of $Attempts"
    & .\scripts\poll_artifacts.ps1
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host "Artifact downloaded on attempt $i"
        if (-not (Test-Path -Path '.\.artifacts')) { New-Item -ItemType Directory -Path '.\.artifacts' -Force | Out-Null }
        "SUCCESS: attempt $i" | Out-File -FilePath '.\\.artifacts\\poll_result.txt' -Encoding utf8
        exit 0
    }
    Write-Host "No artifact yet; sleeping $SleepSeconds seconds"
    Start-Sleep -Seconds $SleepSeconds
}

Write-Host "Polling finished: no artifact found after $Attempts attempts"
if (-not (Test-Path -Path '.\.artifacts')) { New-Item -ItemType Directory -Path '.\.artifacts' -Force | Out-Null }
"NO_ARTIFACT: attempts=$Attempts" | Out-File -FilePath '.\\.artifacts\\poll_result.txt' -Encoding utf8
Write-Host 'Polling finished with no artifact; see .\.artifacts\\poll_result.txt for status.'
exit 0
