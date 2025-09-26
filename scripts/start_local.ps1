# Start the local app using the project's .venv-py311 Python.
# It will try ports 8000..8100 and pick the first free one.
# Run from the repository root.

Param()

$venvPython = Join-Path -Path $PSScriptRoot -ChildPath "..\.venv-py311\Scripts\python.exe"
$venvPython = (Resolve-Path $venvPython -ErrorAction SilentlyContinue).ProviderPath
if (-not $venvPython) {
    Write-Host "Warning: .venv-py311 Python not found. Falling back to system python."
    $venvPython = "python"
}

$bindHost = "127.0.0.1"

function Test-Port($h, $port) {
    $sock = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $sock.BeginConnect($h, $port, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne(200)
        if ($ok) { $sock.EndConnect($async); $sock.Close(); return $true }
        $sock.Close(); return $false
    }
    catch {
        try { $sock.Close() } catch {}
        return $false
    }
}

$chosen = $null
for ($p = 8000; $p -le 8100; $p++) {
    if (-not (Test-Port $bindHost $p)) { $chosen = $p; break }
}

if (-not $chosen) {
    Write-Host "No free port found in 8000..8100. Stop the process using the port or set LOCAL_PORT manually." -ForegroundColor Red
    exit 1
}

Write-Host "Starting local server on port $chosen using $venvPython"
$env:LOCAL_PORT = "$chosen"
& $venvPython "scripts/run_local.py"
