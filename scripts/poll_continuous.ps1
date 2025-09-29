param(
    [int]$Minutes = 10,
    [int]$SleepSeconds = 15,
    [string]$Repo = 'Klerno-Labs/Klerno-Labs',
    [string]$Branch = 'ci/enterprise-run-migrations-pr25',
    [string]$ArtifactName = 'alembic-logs',
    [string]$OutDir = '.\\.artifacts'
)

if (-not (Test-Path -Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

$end = (Get-Date).AddMinutes($Minutes)
Write-Host "Starting continuous poll for up to $Minutes minute(s) (sleep $SleepSeconds s between checks)"

while ((Get-Date) -lt $end) {
    Write-Host "--- Polling at $(Get-Date -Format o) ---"

    # list workflow runs for the branch
    $idsRaw = gh api "repos/$Repo/actions/runs?branch=$Branch" --jq '.workflow_runs[].id' 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($idsRaw)) {
        Write-Host 'gh api list failed or returned no runs; sleeping' $SleepSeconds 's'
        Start-Sleep -Seconds $SleepSeconds
        continue
    }

    # idsRaw may be multiline; split into array
    $ids = $idsRaw -split "\r?\n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($id in $ids) {
        Write-Host "Trying run $id for artifact '$ArtifactName'"
        $out = gh run download $id --repo $Repo --name $ArtifactName --dir $OutDir 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Downloaded $ArtifactName from run $id to $OutDir"
            "SUCCESS: run $id" | Out-File -FilePath (Join-Path $OutDir 'poll_result.txt') -Encoding utf8
            exit 0
        }
        else {
            Write-Host "No $ArtifactName for run $id (gh exit $LASTEXITCODE)"
        }
    }

    Write-Host "Sleeping $SleepSeconds seconds before next poll"
    Start-Sleep -Seconds $SleepSeconds
}

Write-Host "Polling window ended; no artifact found"
"NO_ARTIFACT: branch=$Branch minutes=$Minutes" | Out-File -FilePath (Join-Path $OutDir 'poll_result.txt') -Encoding utf8
Write-Host "Wrote .\\.artifacts\\poll_result.txt"
exit 0
