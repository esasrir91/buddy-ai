# Aura — AI Coding IDE launcher (PowerShell)
# Right-click and "Run with PowerShell" or add to Start Menu.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host "   A U R A  —  AI Coding IDE" -ForegroundColor Cyan
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "  Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found in PATH." -ForegroundColor Red
    Write-Host "  Install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Optional: workspace via param  e.g.  .\Aura.ps1 -Workspace C:\myproject
param([string]$Workspace = "")

$args = @("--desktop")
if ($Workspace) { $args += @("--workspace", $Workspace) }

Write-Host "  Launching Aura…" -ForegroundColor Cyan
python -m buddy.code @args
