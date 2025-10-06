param(
    [string]$Url = "https://ep-odd-wave-adbr94n5.apirest.c-2.us-east-1.aws.neon.tech/neondb/rest/v1",
    [string]$Token = $env:NEON_API_KEY
)

if ([string]::IsNullOrWhiteSpace($Token)) {
    Write-Error "NEON_API_KEY not set. Provide -Token or run the set-neon-api-key task."
    exit 1
}

Write-Host "Testing Neon REST base: $Url"

function Invoke-WebRequestSafe {
    param(
        [string]$TargetUrl
    )
    $headers = @{ Authorization = "Bearer $Token" }
    try {
        $resp = Invoke-WebRequest -Uri $TargetUrl -Headers $headers -Method GET -ErrorAction Stop
        return [pscustomobject]@{
            StatusCode = $resp.StatusCode
            Content    = $resp.Content
        }
    }
    catch {
        $e = $_.Exception
        if ($e.Response) {
            try {
                $reader = New-Object System.IO.StreamReader($e.Response.GetResponseStream())
                $body = $reader.ReadToEnd()
                $reader.Close()
            }
            catch { $body = "" }
            return [pscustomobject]@{
                StatusCode = [int]$e.Response.StatusCode
                Content    = $body
            }
        }
        else {
            return [pscustomobject]@{
                StatusCode = -1
                Content    = $e.Message
            }
        }
    }
}

# Base call (often 404/400 even when authorized, but should not be 'missing authentication credentials')
$response = Invoke-WebRequestSafe -TargetUrl $Url
Write-Host ("Status: {0}" -f $response.StatusCode)
try { $json = $response.Content | ConvertFrom-Json; Write-Host ("Body  : {0}" -f ($json | ConvertTo-Json -Depth 6)) } catch { Write-Host ("Body  : {0}" -f $response.Content) }

# Try a standard PostgREST root (usually 404/400)
$openapi = ($Url.TrimEnd('/')) + "/"
$resp2 = Invoke-WebRequestSafe -TargetUrl $openapi
Write-Host ("OpenAPI/Root Status: {0}" -f $resp2.StatusCode)
try { $json2 = $resp2.Content | ConvertFrom-Json; Write-Host ("OpenAPI Body: {0}" -f ($json2 | ConvertTo-Json -Depth 6)) } catch { }

# Probe a known table path for better diagnostics
$notesUrl = ($Url.TrimEnd('/')) + "/notes?select=*&limit=1"
Write-Host "\nTesting /notes endpoint: $notesUrl"
$resp3 = Invoke-WebRequestSafe -TargetUrl $notesUrl
Write-Host ("Notes Status: {0}" -f $resp3.StatusCode)
try { $json3 = $resp3.Content | ConvertFrom-Json; Write-Host ("Notes Body  : {0}" -f ($json3 | ConvertTo-Json -Depth 6)) } catch { Write-Host ("Notes Body  : {0}" -f $resp3.Content) }
