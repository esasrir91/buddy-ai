# install-shortcut.ps1
# Creates Desktop + project Aura.lnk that launch the app FAST with the branded icon.
# Target: pythonw.exe Aura.py  (no VBS middleman)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $ScriptDir "Aura.py"
$IconPath = Join-Path $ScriptDir "Aura.ico"
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")

# Resolve pythonw (absolute) — required so Desktop shortcut works without PATH tricks
$PythonW = $null
foreach ($c in @(
    (Get-Command pythonw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    "C:\Python313\pythonw.exe",
    "C:\Python312\pythonw.exe",
    "C:\Python311\pythonw.exe",
    "$env:LocalAppData\Programs\Python\Python313\pythonw.exe",
    "$env:LocalAppData\Programs\Python\Python312\pythonw.exe"
)) {
    if ($c -and (Test-Path $c)) { $PythonW = $c; break }
}

if (-not $PythonW) {
    Write-Host "ERROR: pythonw.exe not found. Install Python and re-run." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $Launcher)) {
    Write-Host "ERROR: Aura.py missing at $Launcher" -ForegroundColor Red
    exit 1
}

function New-AuraShortcut([string]$ShortcutPath) {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $PythonW
    $Shortcut.Arguments = "`"$Launcher`""
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = "Aura AI Coding IDE"
    $Shortcut.WindowStyle = 1
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = "$IconPath,0"
    }
    $Shortcut.Save()
    Write-Host "  Created: $ShortcutPath" -ForegroundColor Green
}

Write-Host "  pythonw: $PythonW"
New-AuraShortcut (Join-Path $DesktopPath "Aura.lnk")
New-AuraShortcut (Join-Path $ScriptDir "Aura.lnk")

# Save path for the VBS/bat fallbacks
Set-Content -Path (Join-Path $ScriptDir "aura-pythonw.txt") -Value $PythonW -Encoding ASCII

Write-Host ""
Write-Host "  Double-click Desktop 'Aura' to open the app." -ForegroundColor Cyan
Write-Host ""
