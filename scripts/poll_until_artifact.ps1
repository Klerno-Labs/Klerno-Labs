param(
    [int]$Minutes = 20,
    [int]$SleepSeconds = 20
)
$iterations = [math]::Ceiling(($Minutes * 60) / $SleepSeconds)
Write-Output "Polling up to $Minutes minute(s) ($iterations iterations), sleeping $SleepSeconds s between checks"
Remove-Item -ErrorAction SilentlyContinue .\.artifacts\fetch_result.txt
for ($i = 0; $i -lt $iterations; $i++) {
    Write-Output "Iteration $($i+1)/$iterations - calling fetcher"
    try {
        .\scripts\list_and_fetch.ps1 -Limit 30
    }
    catch {
        Write-Output "fetcher failed: $($_)"
    }
    Start-Sleep -Seconds 1
    if (Test-Path .\.artifacts\fetch_result.txt) {
        $body = Get-Content .\.artifacts\fetch_result.txt -Raw
        Write-Output "fetch_result: $body"
        if ($body -match 'SUCCESS_ARTIFACT') {
            Write-Output "Success artifact detected, exiting"
            exit 0
        }
    }
    Write-Output "Sleeping $SleepSeconds seconds..."
    Start-Sleep -Seconds $SleepSeconds
}
Write-Output "Polling completed: no success artifact detected"
exit 0
