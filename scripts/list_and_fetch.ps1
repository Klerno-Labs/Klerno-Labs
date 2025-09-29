# Lists recent runs for branch and tries to fetch `alembic-logs` artifact or run logs.
param(
    [int]$Limit = 30
)

$ErrorActionPreference = 'Stop'
$repo = 'Klerno-Labs/Klerno-Labs'
$branch = 'ci/enterprise-run-migrations-pr25'
$artifactsDir = Join-Path -Path (Get-Location) -ChildPath '.artifacts'
if (-not (Test-Path $artifactsDir)) { New-Item -Path $artifactsDir -ItemType Directory | Out-Null }
$outFile = Join-Path $artifactsDir 'fetch_result.txt'
if (Test-Path $outFile) { Remove-Item $outFile -Force }

function Write-Result([string]$s) {
    $s | Out-File -FilePath $outFile -Encoding UTF8 -Append
}

Write-Output "Listing runs for branch $branch (limit $Limit)..."
$txt = gh run list --branch $branch --limit $Limit
if (-not $txt) {
    Write-Output "gh run list returned nothing"
    Write-Result "NO_RUNS"
    exit 0
}

$ids = @()
foreach ($line in $txt) {
    if ($line -match '\b(\d{6,})\b') {
        $ids += $matches[1]
    }
}
$ids = $ids | Select-Object -Unique
if (-not $ids -or $ids.Count -eq 0) {
    Write-Output "No run ids parsed from gh run list"
    Write-Result "NO_RUN_IDS"
    exit 0
}

foreach ($id in $ids) {
    Write-Output "\n==== Checking run $id ===="
    # Query artifacts via API
    try {
        $json = gh api repos/$repo/actions/runs/$id/artifacts
    }
    catch {
        Write-Output "gh api call failed for run $($id): $($_)"
        Write-Result ("API_FAIL: run=$id error=" + $($_))
        $json = $null
    }

    $found = $false
    if ($json) {
        try {
            $obj = $json | ConvertFrom-Json
            if ($obj.artifacts -and $obj.artifacts.Count -gt 0) {
                foreach ($a in $obj.artifacts) {
                    if ($a.name -eq 'alembic-logs' -or $a.name -eq 'run-marker') {
                        Write-Output "Found artifact $($a.name) for run $id"
                        try {
                            gh run download $id --name $($a.name) --dir $artifactsDir
                            Write-Output "Downloaded $($a.name) for run $id"
                            Write-Result ("SUCCESS_ARTIFACT: run=$id name=" + $($a.name))
                            $found = $true
                            break
                        }
                        catch {
                            Write-Output "gh run download failed for run $($id): $($_)"
                            Write-Result ("DOWNLOAD_FAIL: run=$id error=" + $($_.Exception.Message))
                        }
                    }
                }
            }
            else {
                Write-Output "No artifacts in API response for run $id"
            }
        }
        catch {
            Write-Output "Failed to parse artifacts JSON for run $($id): $($_)"
            Write-Result ("PARSE_FAIL: run=$id error=" + $($_))
        }
    }

    if ($found) { exit 0 }

    # Fallback to downloading run logs
    try {
        $logPath = Join-Path $artifactsDir ("run-$id.log")
        Write-Output "Downloading run logs for run $id to $logPath"
        gh run view $id --log > $logPath
        if (Test-Path $logPath) {
            Write-Output "Saved run log: $logPath"
            Write-Result "SAVED_RUN_LOG: run=$id path=$logPath"
            # extract alembic lines
            $snippet = Join-Path $artifactsDir ("run-$id-alembic-snippet.log")
            Select-String -Path $logPath -Pattern 'alembic|Alembic|alembic.ini|alembic upgrade' -SimpleMatch -CaseSensitive:$false | ForEach-Object { $_.Line } | Out-File -FilePath $snippet -Encoding UTF8
            Write-Output "Saved alembic snippet: $snippet"
            Write-Result "SAVED_SNIPPET: run=$id snippet=$snippet"
            exit 0
        }
    }
    catch {
        Write-Output "Failed to download run logs for run $($id): $($_)"
        Write-Result ("LOG_FAIL: run=$id error=" + $($_))
    }
}

Write-Output "Checked all runs; no artifact or logs saved"
Write-Result "NO_ARTIFACTS_OR_LOGS: checked=$($ids.Count)"
exit 0
