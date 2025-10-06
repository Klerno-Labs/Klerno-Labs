<#
Lints templates for unversioned /static references.
Flags occurrences of href/src to /static without a ?v= query parameter,
except CSS source maps and manifest files which are allowed.
#>
param(
    [string]$TemplatesDir = "templates"
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspace = Resolve-Path (Join-Path $root "..")
$dir = Join-Path $workspace $TemplatesDir
if (!(Test-Path $dir)) { Write-Host "No templates directory: $dir"; exit 0 }

$files = Get-ChildItem -Path $dir -Recurse -Include *.html -File
$violations = @()

foreach ($f in $files) {
    $text = Get-Content -Raw $f.FullName
    # Find src/href to /static without ?v=
    $pattern = '(href|src)\s*=\s*\"(/static/[^\"]*?)\"'
    $rxMatches = [regex]::Matches($text, $pattern)
    foreach ($m in $rxMatches) {
        $url = $m.Groups[2].Value
        if ($url -match '\\.(map|webmanifest)$') { continue }
        if ($url -notmatch '\\?v=') {
            $violations += [pscustomobject]@{ File = $f.FullName; URL = $url }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Host "Found unversioned /static references:" -ForegroundColor Yellow
    $violations | ForEach-Object { Write-Host ("- {0}: {1}" -f $_.File, $_.URL) }
    exit 2
}
else {
    Write-Host "No unversioned /static references found."
}
