$max = 40
$pattern = 'run-181440*.log'
for ($i = 0; $i -lt $max; $i++) {
    Write-Host ('Attempt ' + ($i + 1) + '/' + $max + ': running fetcher...')
    powershell -NoProfile -ExecutionPolicy Bypass -File ..\scripts\list_and_fetch.ps1
    $files = Get-ChildItem -Path . -Filter $pattern -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 0 } | Sort-Object LastWriteTime -Descending
    if ($files.Count -gt 0) {
        Write-Host "Found non-empty run log:"
        $files | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
        break
    }
    else {
        Write-Host "No completed run logs yet. Sleeping 15s..."
        Start-Sleep -Seconds 15
    }
}
Write-Host "poll finished"
