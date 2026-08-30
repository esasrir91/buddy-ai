@echo off
title Aura
cd /d "%~dp0"

REM Fast path: run Aura.py with pythonw (or python)
set "PYW="
if exist "%~dp0aura-pythonw.txt" (
  set /p PYW=<"%~dp0aura-pythonw.txt"
)
if not defined PYW (
  where pythonw >nul 2>&1 && for /f "delims=" %%i in ('where pythonw') do (set "PYW=%%i" & goto :run)
)
if not defined PYW (
  where python >nul 2>&1 && for /f "delims=" %%i in ('where python') do (set "PYW=%%i" & goto :run)
)
if not defined PYW if exist "C:\Python313\pythonw.exe" set "PYW=C:\Python313\pythonw.exe"
if not defined PYW (
  echo Python not found. Install Python 3.10+ first.
  pause
  exit /b 1
)

:run
echo Starting Aura...
start "" "%PYW%" "%~dp0Aura.py"
exit /b 0
