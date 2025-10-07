# Downloads Chart.js UMD build to our static vendor folder
param(
    [string]$Version = "4.4.1"
)

$ErrorActionPreference = "Stop"
$destDir = Join-Path $PSScriptRoot "..\static\vendor\chartjs"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$url = "https://cdn.jsdelivr.net/npm/chart.js@${Version}/dist/chart.umd.min.js"
$out = Join-Path $destDir "chart.umd.min.js"

Write-Host "Downloading Chart.js $Version ..."
Invoke-WebRequest -Uri $url -OutFile $out

Write-Host "Saved to $out"
