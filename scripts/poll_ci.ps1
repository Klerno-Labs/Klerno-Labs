$run = 18435915094
while ($true) {
    $r = gh run view $run --json jobs
    $obj = ConvertFrom-Json $r
    $job = $obj.jobs | Where-Object { $_.name -eq 'Unit Tests and Coverage (3.11)' }
    Write-Host (Get-Date -Format o) "status=$($job.status) conclusion=$($job.conclusion)"
    if ($job.status -eq 'completed') { break }
    Start-Sleep -Seconds 10
}
Write-Host 'done'
