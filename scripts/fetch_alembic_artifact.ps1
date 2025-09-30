<#
Query recent GitHub Actions runs for branch ci/enterprise-run-migrations-pr25,
try to download artifact named `alembic-logs`. If not present, fallback to
saving the run logs. Writes machine-readable results to .\.artifacts\fetch_result.txt
#>
param(
    [int]$Limit = 30
)

$ErrorActionPreference = 'Stop'
$repo = "Klerno-Labs/Klerno-Labs"
$branch = "ci/enterprise-run-migrations-pr25"
$artifactsDir = Join-Path -Path (Get-Location) -ChildPath '.artifacts'
if (-not (Test-Path $artifactsDir)) { New-Item -Path $artifactsDir -ItemType Directory | Out-Null }

function Write-Result($msg) {
    $outFile = Join-Path $artifactsDir 'fetch_result.txt'
    $msg | Out-File -FilePath $outFile -Encoding UTF8 -Append
}

Write-Output "Listing up to $Limit runs for branch $branch..."
$runListJson = gh api repos/$repo/actions/runs --field branch=$branch --field per_page=$Limit | ConvertFrom-Json
if (-not $runListJson.workflow_runs -or $runListJson.workflow_runs.Count -eq 0) {
    Write-Output "No runs found for branch $branch"
    Write-Result "NO_RUNS: branch=$branch"
    exit 0
}

foreach ($run in $runListJson.workflow_runs) {
    $runId = $run.id
    Write-Output "Checking run $runId (event=$($run.event))"

    # Check artifacts for the run via API
    $artApi = gh api repos/$repo/actions/runs/$runId/artifacts
    $art = $null
    try {
        $art = ($artApi | ConvertFrom-Json).artifacts
    }
    catch {
        Write-Output "Failed to parse artifacts JSON for run $($runId): $($_)"
        $art = @()
    }

    if ($art -and $art.Count -gt 0) {
        foreach ($a in $art) {
            if ($a.name -eq 'alembic-logs') {
                Write-Output "Found alembic-logs artifact for run $runId, attempting download..."
                try {
                    gh run download $runId --name alembic-logs --dir $artifactsDir
                    Write-Output ("Downloaded alembic-logs for run $runId to $artifactsDir")
                    Write-Result "SUCCESS_ARTIFACT: run=$runId file=alembic-logs"
                    exit 0
                }
                catch {
                    Write-Output "gh run download failed for run $($runId): $($_)"
                    Write-Result ("DOWNLOAD_FAIL: run=$runId error=" + $($_.Exception.Message))
                }
            }
        }
    }
    else {
        Write-Output "No artifacts listed for run $runId"
    }

    # Fallback: try to download run logs
    Write-Output "Attempting to download run logs for run $runId"
    try {
        $logPath = Join-Path $artifactsDir ("run-$runId.log")
        gh run view $runId --log > $logPath
        Write-Output "Saved run logs to $logPath"
        Write-Result "SAVED_RUN_LOG: run=$runId path=$logPath"

        # Try to extract alembic-related lines as a snippet
        $snippet = Join-Path $artifactsDir ("run-$runId-alembic-snippet.log")
        Select-String -Path $logPath -Pattern 'alembic|Alembic|alembic.ini|alembic upgrade' -SimpleMatch -CaseSensitive:$false | ForEach-Object { $_.Line } | Out-File -FilePath $snippet -Encoding UTF8
        Write-Output "Saved alembic snippet to $snippet"
        Write-Result "SAVED_SNIPPET: run=$runId snippet=$snippet"
        exit 0
    }
    catch {
        Write-Output "Failed to fetch run logs for run $($runId): $($_)"
        Write-Result ("LOG_FAIL: run=$runId error=" + $($_.Exception.Message))
    }
}

Write-Output "No alembic-logs artifact or downloadable run logs found for last $Limit runs"
Write-Result "NO_ARTIFACTS_OR_LOGS: branch=$branch checked=$Limit"
exit 0
