Param(
    [Parameter(Mandatory=$false)]
    [string[]]$RunIds = @(
        '18084494090','18084306090','18084253043','18084214995','18084173760','18084144557','18083937513','18083727726','18083727627'
    ),
    [string]$Repo = 'Klerno-Labs/Klerno-Labs',
    [string]$ArtifactName = 'alembic-logs',
    [string]$OutDir = '.\\.artifacts'
)

# Ensure output directory exists
if (-not (Test-Path -Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

foreach ($id in $RunIds) {
    Write-Host "Checking run $id for artifact '$ArtifactName'..."

    # Query run artifacts and look for the artifact by name
    # Build a jq expression safely. Use single quotes for the outer PowerShell string
    # and inject the artifact name using a subexpression to avoid quoting issues.
    $jq = '.artifacts[] | select(.name=="' + $ArtifactName + '") | .id'
    $artifactId = gh run view $id --repo $Repo --json artifacts --jq $jq 2>$null

    if ($LASTEXITCODE -ne 0) {
        Write-Host "gh run view failed for $id (exit $LASTEXITCODE); skipping"
        continue
    }

    if ([string]::IsNullOrWhiteSpace($artifactId)) {
        Write-Host "No artifact '$ArtifactName' found for run $id"
        continue
    }

    Write-Host "Artifact present for run $id (artifact id: $artifactId). Attempting download..."

    # Use call operator to invoke gh as an executable and capture exit code
    & gh run download $id --repo $Repo --name $ArtifactName --dir $OutDir
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host "Downloaded artifact '$ArtifactName' from run $id to $OutDir"
        exit 0
    } else {
        Write-Host "Download attempt failed for run $id with exit code $code; continuing"
        continue
    }
}

Write-Host "No artifact downloaded from provided run IDs"
exit 1
