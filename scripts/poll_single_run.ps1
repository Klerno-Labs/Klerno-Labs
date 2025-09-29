param(
    [string]$RunId = '18084608074',
    [int]$Attempts = 20,
    [int]$SleepSeconds = 15
)

for ($i = 1; $i -le $Attempts; $i++) {
    Write-Host "Polling run $RunId attempt $i of $Attempts"
    & .\scripts\poll_artifacts.ps1 -RunIds @($RunId)
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Artifact downloaded on attempt $i"
        # Write success marker
        if (-not (Test-Path -Path '.\.artifacts')) { New-Item -ItemType Directory -Path '.\.artifacts' -Force | Out-Null }
        "SUCCESS: run $RunId" | Out-File -FilePath '.\\.artifacts\\poll_result.txt' -Encoding utf8
        exit 0
    }
    Start-Sleep -Seconds $SleepSeconds
}

Write-Host "Finished polling; no artifact found"
if (-not (Test-Path -Path '.\.artifacts')) { New-Item -ItemType Directory -Path '.\.artifacts' -Force | Out-Null }
"NO_ARTIFACT: run $RunId" | Out-File -FilePath '.\\.artifacts\\poll_result.txt' -Encoding utf8
# Do not exit with non-zero code to avoid terminating the VS Code integrated terminal with an error popup.
Write-Host 'Polling finished with no artifact; see .\.artifacts\\poll_result.txt for status.'
exit 0
