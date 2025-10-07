# Diagnose artifact visibility across recent runs
param(
    [int]$Limit = 20
)
$repo = 'Klerno-Labs/Klerno-Labs'
$branch = 'ci/enterprise-run-migrations-pr25'
Write-Output "Listing $Limit runs for branch $branch"
$runs = gh run list --branch $branch --limit $Limit
if (-not $runs) { Write-Output 'no runs'; exit 0 }

# Extract run ids from text
$ids = @()
foreach ($line in $runs) {
    if ($line -match '\b(\d{6,})\b') { $ids += $matches[1] }
}
$ids = $ids | Select-Object -Unique
Write-Output "Found runs: $($ids -join ', ')"

# Repo-level artifacts
Write-Output "\nRepository-level artifacts:"
try { gh api repos/$repo/actions/artifacts --jq '.artifacts | map({id:.id,name:.name,size:.size,expired:.expired})' | ConvertFrom-Json | Format-Table -AutoSize } catch { Write-Output "Failed to list repo artifacts: $($_)" }

foreach ($id in $ids) {
    Write-Output "\n--- Run $id ---"
    # list jobs for the run
    try {
        $jobsRaw = gh api repos/$repo/actions/runs/$id/jobs --jq '.jobs | map({id:.id,name:.name,conclusion:.conclusion,status:.status})'
        Write-Output "Jobs (json): $jobsRaw"
    }
    catch {
        Write-Output "Failed to fetch jobs for run $($id): $($_)"
    }

    # list artifacts for the run
    try {
        $artJson = gh api repos/$repo/actions/runs/$id/artifacts
        Write-Output "Artifacts JSON length: $($artJson.Length)"
        $artObj = $null
        try { $artObj = $artJson | ConvertFrom-Json } catch { Write-Output "Parse error for artifacts JSON: $($_)" }
        if ($artObj -and $artObj.artifacts) {
            foreach ($a in $artObj.artifacts) {
                Write-Output "Artifact: id=$($a.id) name=$($a.name) size=$($a.size) expires_at=$($a.expire_at)"
                # try to download by artifact id
                try {
                    gh api repos/$repo/actions/artifacts/$($a.id)/zip --output .\.artifacts\artifact-$($a.id).zip
                    Write-Output "Downloaded artifact-$($a.id).zip"
                }
                catch {
                    Write-Output "Failed to download artifact id $($a.id): $($_)"
                }
            }
        }
        else {
            Write-Output "No artifacts found in API response for run $id"
        }
    }
    catch {
        Write-Output "Failed to call artifacts API for run $($id): $($_)"
    }
}

Write-Output "Diagnostic complete."
