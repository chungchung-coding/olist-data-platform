<#
.SYNOPSIS
    Runs the whole Olist pipeline on DuckDB. The Windows equivalent of `make all`.

.DESCRIPTION
    Ingest raw CSVs -> dbt run -> dbt test -> Great Expectations -> analysis charts.
    Every path is resolved to an absolute path from this script's location, so it
    does not matter which directory you launch it from.

.PARAMETER Clean
    Delete the existing DuckDB file, dbt target folder and GE report before running.

.PARAMETER SkipAnalysis
    Stop after the quality gate (useful when you only want to rebuild the warehouse).

.EXAMPLE
    .\run_all.ps1
.EXAMPLE
    .\run_all.ps1 -Clean
#>
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipAnalysis
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

# Absolute paths so dbt, Great Expectations and the notebooks all agree on one warehouse file.
$env:DUCKDB_PATH      = Join-Path $root 'data\warehouse\olist.duckdb'
$env:DBT_PROFILES_DIR = Join-Path $root 'dbt\olist_dbt'

# Prefer the virtual environment's executables if one exists next to this script.
$python = if (Test-Path (Join-Path $root '.venv\Scripts\python.exe')) { Join-Path $root '.venv\Scripts\python.exe' } else { 'python' }
$dbt    = if (Test-Path (Join-Path $root '.venv\Scripts\dbt.exe'))    { Join-Path $root '.venv\Scripts\dbt.exe' }    else { 'dbt' }

function Invoke-Step {
    param([string]$Name, [scriptblock]$Body)
    Write-Host ''
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $Name  (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# --- preflight -------------------------------------------------------------
$csvCount = @(Get-ChildItem (Join-Path $root 'data\raw') -Filter *.csv -ErrorAction SilentlyContinue).Count
if ($csvCount -lt 9) {
    Write-Host "Found $csvCount CSV files in data\raw - expected 9." -ForegroundColor Red
    Write-Host 'Copy the Olist CSVs into data\raw before running. See docs\RUNBOOK_WINDOWS.md step 1.2.'
    exit 1
}
Write-Host "Python:    $python"
Write-Host "dbt:       $dbt"
Write-Host "Warehouse: $env:DUCKDB_PATH"

if ($Clean) {
    Write-Host ''
    Write-Host '=== Clean ===' -ForegroundColor Cyan
    Remove-Item $env:DUCKDB_PATH -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $root 'dbt\olist_dbt\target') -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $root 'quality\gx_results.json') -ErrorAction SilentlyContinue
    Write-Host 'Removed warehouse file, dbt target and previous GE report.'
}

# --- pipeline --------------------------------------------------------------
Invoke-Step 'Ingest raw CSVs into DuckDB' {
    & $python (Join-Path $root 'ingestion\load_raw_duckdb.py') --db $env:DUCKDB_PATH --raw (Join-Path $root 'data\raw')
}

Invoke-Step 'dbt run (8 staging views + 12 analytics tables)' {
    & $dbt run --project-dir (Join-Path $root 'dbt\olist_dbt') --profiles-dir $env:DBT_PROFILES_DIR --target duckdb
}

Invoke-Step 'dbt test (96 tests; 2 warnings are expected)' {
    & $dbt test --project-dir (Join-Path $root 'dbt\olist_dbt') --profiles-dir $env:DBT_PROFILES_DIR --target duckdb
}

Invoke-Step 'Great Expectations quality gate' {
    & $python (Join-Path $root 'quality\run_great_expectations.py')
}

if (-not $SkipAnalysis) {
    Invoke-Step 'Analysis: charts and KPIs' {
        Push-Location (Join-Path $root 'analysis')
        try { & $python 'run_analysis.py' } finally { Pop-Location }
    }
}

Write-Host ''
Write-Host 'Pipeline complete.' -ForegroundColor Green
Write-Host "Charts and KPIs: $(Join-Path $root 'analysis\outputs')"
Write-Host "Quality report:  $(Join-Path $root 'quality\gx_results.json')"
