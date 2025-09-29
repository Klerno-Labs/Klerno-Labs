Param(
    [Parameter(Mandatory = $false)]
    [string[]]$RunIds = @(
        '18084494090', '18084306090', '18084253043', '18084214995', '18084173760', '18084144557', '18083937513', '18083727726', '18083727627'
    ),
    [string]$Repo = 'Klerno-Labs/Klerno-Labs',
    [string]$ArtifactName = 'alembic-logs',
    [string]$OutDir = '.\\.artifacts'
)

# Ensure output directory exists
if (-not (Test-Path -Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

foreach ($id in $RunIds) {
    Write-Host "Checking run $id for artifact '$ArtifactName'..."

    # Query run artifacts via the REST API (gh run view doesn't expose artifacts on this gh version)
    $apiPath = "repos/$Repo/actions/runs/$id/artifacts"

    $raw = $null
    $artifactId = $null
    # Small retry loop to handle transient API issues
    for ($try = 1; $try -le 2; $try++) {
        Write-Host "Fetching artifacts (attempt $try) for run $id"
        $raw = gh api $apiPath 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Write-Host "gh api call failed with exit code $code; output: $raw"
            Start-Sleep -Seconds 2
            continue
        }

        try {
            $json = $raw | ConvertFrom-Json
        }
        catch {
            Write-Host "Failed to parse JSON response for run $id; raw output: $raw"
            Start-Sleep -Seconds 2
            continue
        }

        if ($null -eq $json.artifacts -or $json.artifacts.Count -eq 0) {
            Write-Host "No artifacts array or empty artifacts for run $id"
            break
        }

        $match = $json.artifacts | Where-Object { $_.name -eq $ArtifactName }
        if ($null -ne $match) {
            $artifactId = $match.id
        }
        break
    }

    if ($null -eq $artifactId) {
        Write-Host "No artifact '$ArtifactName' found for run $id"

        # As a fallback, download the run logs so we can inspect migration output.
        try {
            Write-Host "Downloading run logs for run $id to help triage..."
            $logOut = Join-Path -Path $OutDir -ChildPath "run-$id.log"
            $logOutA = Join-Path -Path $OutDir -ChildPath "run-$id-alembic-snippet.log"
            $logOutput = gh run view $id --repo $Repo --log 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Failed to fetch run logs for $id (exit $LASTEXITCODE); output: $logOutput"
            }
            else {
                # Save full logs
                $logOutput | Out-File -FilePath $logOut -Encoding utf8
                Write-Host "Saved run logs to $logOut"
                # Extract alembic-related lines for quick review
                $alembicLines = $logOutput | Select-String -Pattern "alembic|Alembic|upgrade|ERROR|Traceback" -SimpleMatch
                if ($alembicLines) {
                    $alembicLines.Line | Out-File -FilePath $logOutA -Encoding utf8
                    Write-Host "Saved alembic-related snippet to $logOutA"
                }
                else {
                    Write-Host "No alembic-related lines found in run logs"
                }
            }
        }
        catch {
            Write-Host "Exception while fetching run logs: $_"
        }

        continue
    }

    Write-Host "Artifact present for run $id (artifact id: $artifactId). Attempting download..."

    # Use call operator to invoke gh as an executable and capture exit code
    & gh run download $id --repo $Repo --name $ArtifactName --dir $OutDir
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host "Downloaded artifact '$ArtifactName' from run $id to $OutDir"
        exit 0
    }
    else {
        Write-Host "Download attempt failed for run $id with exit code $code; continuing"
        continue
    }
}

Write-Host "No artifact downloaded from provided run IDs"
exit 1
