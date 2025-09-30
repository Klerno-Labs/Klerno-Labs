$log = Join-Path (Get-Location) '.\.artifacts\run-18114806621.log'
$out = Join-Path (Get-Location) '.\.artifacts\run-18114806621-errors.txt'
if (-not (Test-Path $log)) { Write-Output "Log not found: $log"; exit 0 }
$patterns = 'Traceback', 'ERROR', 'FAILED', 'FAIL', 'AssertionError', 'Exception', 'CRITICAL'
$matches = Select-String -Path $log -Pattern ($patterns -join '|') -Context 3 -AllMatches -ErrorAction SilentlyContinue
if (-not $matches) {
    "No obvious ERROR/Traceback matches found" | Out-File $out -Encoding UTF8
    Write-Output "WROTE $out"
    Get-Content $out -Raw | Write-Output
    exit 0
}
"Found $($matches.Count) matches" | Out-File $out -Encoding UTF8
foreach ($m in $matches) {
    "---- Match ----" | Out-File $out -Append -Encoding UTF8
    "Line $($m.LineNumber):" | Out-File $out -Append -Encoding UTF8
    if ($m.Context.PreContext) { ($m.Context.PreContext -join "`n") | Out-File $out -Append -Encoding UTF8 }
    ($m.Line) | Out-File $out -Append -Encoding UTF8
    if ($m.Context.PostContext) { ($m.Context.PostContext -join "`n") | Out-File $out -Append -Encoding UTF8 }
    "" | Out-File $out -Append -Encoding UTF8
}
Write-Output "WROTE $out"
Get-Content $out -Raw | Write-Output
