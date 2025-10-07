Param(
    [switch]$DryRun,
    [switch]$Hydrate,
    [string[]]$Extensions = @('.py', '.md', '.txt', '.ini', '.cfg', '.toml', '.json', '.yml', '.yaml', '.ps1', '.psm1', '.sh', '.html', '.css', '.js'),
    [string[]]$ExcludeDirs = @('tests', 'test', 'static', 'templates', 'app', 'vendor', '.artifacts', '.github', '.vscode')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ==="
}

function Get-GitRoot {
    $root = & git rev-parse --show-toplevel 2>$null
    if (-not $root) {
        throw "Not a git repository or git is not available."
    }
    return $root
}

function Get-GitTrackedFiles {
    $raw = & git ls-files -z
    if ($LASTEXITCODE -ne 0) { throw "git ls-files failed" }
    $files = @()
    if ($raw) {
        $files = $raw -split "`0" | Where-Object { $_ -and $_.Trim().Length -gt 0 }
    }
    return $files
}

function Test-WhitespaceOnly {
    param([string]$Path)
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        if ($bytes.Length -eq 0) { return $true }
        # Strip UTF-8 BOM if present
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $bytes = $bytes[3..($bytes.Length - 1)]
        }
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
        return ($text -match '^\s*$')
    }
    catch {
        return $false
    }
}

function Test-IsPlaceholder {
    param([System.IO.FileInfo]$File)
    # Detect OneDrive/Cloud placeholders (Offline/ReparsePoint). Avoid removing these by default.
    $attrs = $File.Attributes
    if ($attrs.HasFlag([System.IO.FileAttributes]::Offline)) { return $true }
    if ($attrs.HasFlag([System.IO.FileAttributes]::ReparsePoint)) { return $true }
    return $false
}

$root = Get-GitRoot
Set-Location -LiteralPath $root

$tracked = Get-GitTrackedFiles
$exceptions = @('__init__.py', '.gitkeep', '.keep')

$empty = New-Object System.Collections.Generic.List[string]
$whitespace = New-Object System.Collections.Generic.List[string]
$toRemove = New-Object System.Collections.Generic.List[string]

foreach ($f in $tracked) {
    if (-not (Test-Path -LiteralPath $f)) { continue }
    $leaf = Split-Path -Leaf $f
    if ($exceptions -contains $leaf) { continue }

    # Skip excluded directories
    $parts = $f -split "[\\/]"
    if ($parts.Length -gt 1) {
        $top = $parts[0]
        if ($ExcludeDirs -contains $top) { continue }
    }

    # Filter by extension
    $ext = [System.IO.Path]::GetExtension($f)
    if ($Extensions -and (-not ($Extensions -contains $ext))) { continue }

    $fi = Get-Item -LiteralPath $f
    $isPlaceholder = Test-IsPlaceholder -File $fi
    if ($isPlaceholder -and -not $Hydrate) {
        # Skip cloud placeholders unless hydration is explicitly requested
        continue
    }
    if ($fi.Length -eq 0) {
        $empty.Add($f) | Out-Null
        $toRemove.Add($f) | Out-Null
        continue
    }

    if (Test-WhitespaceOnly -Path $f) {
        $whitespace.Add($f) | Out-Null
        $toRemove.Add($f) | Out-Null
    }
}

Write-Section "Empty files"
if ($empty.Count -eq 0) { Write-Host "(none)" } else { $empty | ForEach-Object { Write-Host $_ } }

Write-Section "Whitespace-only files"
if ($whitespace.Count -eq 0) { Write-Host "(none)" } else { $whitespace | ForEach-Object { Write-Host $_ } }

Write-Section "To remove"
if ($toRemove.Count -eq 0) { Write-Host "(none)" } else { $toRemove | Sort-Object -Unique | ForEach-Object { Write-Host $_ } }

if ($DryRun) {
    Write-Host "DryRun specified; not removing files."
    exit 0
}

if ($toRemove.Count -gt 0) {
    foreach ($f in ($toRemove | Sort-Object -Unique)) {
        & git rm -- "$f" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "git rm failed for $f" }
    }
    & git commit -m "chore: remove empty and whitespace-only files" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
    Write-Host "Removed $($toRemove.Count) files and committed."
}
else {
    Write-Host "No files to remove."
}
