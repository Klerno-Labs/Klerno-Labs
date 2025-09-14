# Environment checker for Klerno Labs
# This script validates the environment and settings before starting the application

param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$success = $true
$warnings = 0
$errors = 0

function Write-Status {
    param (
        [string]$Message,
        [string]$Status,
        [string]$Details = ""
    )
    
    if ($Quiet) { return }
    
    $statusColor = switch ($Status) {
        "OK" { "Green" }
        "WARNING" { "Yellow"; $script:warnings++ }
        "ERROR" { "Red"; $script:errors++; $script:success = $false }
        default { "White" }
    }
    
    Write-Host "  [" -NoNewline
    Write-Host $Status -ForegroundColor $statusColor -NoNewline
    Write-Host "] " -NoNewline
    Write-Host $Message
    
    if ($Details) {
        Write-Host "       $Details" -ForegroundColor DarkGray
    }
}

function Test-PythonPackage {
    param (
        [string]$PackageName,
        [string]$MinVersion = ""
    )
    
    try {
        $result = python -c "import $PackageName; print(getattr($PackageName, '__version__', 'unknown'))" 2>$null
        $version = $result.Trim()
        
        if ($MinVersion -and ($version -ne "unknown")) {
            # Simple version comparison - in production you might want a more robust version check
            if ($version -lt $MinVersion) {
                Write-Status "$PackageName" "WARNING" "Found v$version, but v$MinVersion or higher recommended"
                return $false
            }
        }
        
        Write-Status "$PackageName" "OK" "v$version"
        return $true
    } catch {
        Write-Status "$PackageName" "ERROR" "Not installed or import error"
        return $false
    }
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Write-Status ".env file" "ERROR" "Not found"
        return $false
    }
    
    $envContent = Get-Content ".env" -Raw
    $requiredVars = @(
        "APP_ENV", 
        "SECRET_KEY",
        "XRPL_NET",
        "DESTINATION_WALLET"
    )
    
    $missingVars = @()
    foreach ($var in $requiredVars) {
        if ($envContent -notmatch "$var\s*=") {
            $missingVars += $var
        }
    }
    
    if ($missingVars.Count -gt 0) {
        Write-Status ".env file" "WARNING" "Missing required variables: $($missingVars -join ', ')"
        return $false
    }
    
    Write-Status ".env file" "OK" "All required variables present"
    return $true
}

function Test-Database {
    # Simplified database check - just verifies the database file exists for SQLite
    # For PostgreSQL, would need to check connection
    
    try {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "DATABASE_URL\s*=\s*sqlite:///(.+)") {
            $dbPath = $matches[1].Trim()
            $dbPath = $dbPath -replace "^\./", ""  # Remove leading ./ if present
            
            if (-not (Test-Path $dbPath)) {
                Write-Status "Database" "WARNING" "SQLite file not found: $dbPath"
                return $false
            }
            
            Write-Status "Database" "OK" "SQLite: $dbPath"
            return $true
        } elseif ($envContent -match "DATABASE_URL\s*=\s*postgresql://") {
            # Would need a proper PostgreSQL connection test here
            Write-Status "Database" "OK" "PostgreSQL configured (connection not verified)"
            return $true
        } else {
            Write-Status "Database" "WARNING" "DATABASE_URL not found or unrecognized format"
            return $false
        }
    } catch {
        Write-Status "Database" "ERROR" $_.Exception.Message
        return $false
    }
}

# Main checking routine
if (-not $Quiet) {
    Write-Host "===== Klerno Labs Environment Check =====" -ForegroundColor Cyan
    Write-Host "Checking environment..."
}

# Check Python version
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python (\d+\.\d+\.\d+)") {
        $version = $matches[1]
        if ($version -like "3.11.*") {
            Write-Status "Python version" "OK" "v$version"
        } else {
            Write-Status "Python version" "WARNING" "v$version (recommended: 3.11.x)"
        }
    } else {
        Write-Status "Python version" "ERROR" "Could not determine version"
    }
} catch {
    Write-Status "Python version" "ERROR" "Python not found"
}

# Check virtual environment
if (Test-Path ".venv311/Scripts/python.exe") {
    Write-Status "Virtual environment" "OK" ".venv311"
} else {
    Write-Status "Virtual environment" "WARNING" ".venv311 not found"
}

# Check critical packages
Test-PythonPackage "fastapi" "0.110.0"
Test-PythonPackage "xrpl" "2.6.0"
Test-PythonPackage "uvicorn"
Test-PythonPackage "pydantic" "2.0.0"

# Check environment file
Test-EnvFile

# Check database
Test-Database

# Output summary
if (-not $Quiet) {
    Write-Host "`n----- Environment Check Summary -----" -ForegroundColor Cyan
    if ($success) {
        Write-Host "✓ Environment check passed!" -ForegroundColor Green
        if ($warnings -gt 0) {
            Write-Host "  $warnings warning(s) found but not critical" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Environment check failed: $errors error(s), $warnings warning(s)" -ForegroundColor Red
        Write-Host "  Please fix the issues above before running the application" -ForegroundColor Red
    }
    Write-Host "------------------------------------`n" -ForegroundColor Cyan
}

# Return success status for use in calling scripts
return $success