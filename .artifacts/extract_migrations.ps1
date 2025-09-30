# Extract migration step output from full run log
$log = Join-Path (Get-Location) ".\.artifacts\run-18114183610.log"
if (-not (Test-Path $log)) {
    Write-Output "Log not found: $log"
    exit 0
}

# Find start/end markers (the step names)
$startMatch = Select-String -Path $log -Pattern 'Run DB migrations' -SimpleMatch | Select-Object -First 1
$endMatch = Select-String -Path $log -Pattern 'Run Enterprise Application Tests' -SimpleMatch | Select-Object -First 1

if (-not $startMatch) {
    Write-Output 'Start marker not found (Run DB migrations)'
    exit 0
}
if (-not $endMatch) {
    Write-Output 'End marker not found (Run Enterprise Application Tests)'
    exit 0
}

$start = $startMatch.LineNumber
$end = $endMatch.LineNumber
Write-Output "start=$start end=$end"

$lines = Get-Content $log -Encoding UTF8 -ErrorAction Stop
if ($end -le $start) {
    Write-Output 'Unexpected marker positions; aborting'
    exit 0
}

$segment = $lines[$start..($end - 2)]
$outPath = Join-Path (Get-Location) ".\.artifacts\run-18114183610-migrations-segment.log"
$segment | Set-Content -Path $outPath -Encoding UTF8
Write-Output "WROTE $outPath (lines: $($segment.Length))"

Write-Output '--- BEGIN SEGMENT (first 400 lines) ---'
$limit = [Math]::Min(399, [Math]::Max(0, $segment.Length - 1))
for ($i = 0; $i -le $limit; $i++) { Write-Output $segment[$i] }
Write-Output '--- END SEGMENT ---'
