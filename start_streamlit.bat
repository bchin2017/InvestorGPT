@echo off
setlocal
cd /d "%~dp0"

REM ── One-click startup for InvestorGPT (port 8502) ───────────
set "PY_CMD=python"
if exist ".venv\Scripts\python.exe" (
    call :resolve_venv_python
)

if exist "scripts\refresh_data.py" (
    start "" /min cmd /c "\"%PY_CMD%\" \"scripts\refresh_data.py\" >> \"%~dp0refresh_startup.log\" 2>&1"
)

REM ── Stop any existing instance on port 8502 ──────────────────
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8502 " ^| findstr "LISTENING" 2^>nul') do taskkill /f /pid %%a >nul 2>&1
taskkill /fi "windowtitle eq InvestorGPT Dashboard" /f >nul 2>&1
timeout /t 2 /nobreak >nul

REM ── Start keeper window (auto-restarts if Streamlit crashes) ─
start "" /min "%~dp0_keeper.bat"

REM ── Wait until port 8502 is listening (max 40s) ──────────────
echo Waiting for server...
set /a _t=0
:wait
timeout /t 1 /nobreak >nul
netstat -aon 2>nul | findstr ":8502 " | findstr "LISTENING" >nul
if %errorlevel%==0 goto open
set /a _t+=1
if %_t% lss 40 goto wait

netstat -aon 2>nul | findstr ":8502 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
    goto open
) else (
    echo Server did not start within 40 seconds. Check _keeper.bat logs.
    pause
    goto :eof
)

:open
start http://localhost:8502
goto :eof

:resolve_venv_python
".venv\Scripts\python.exe" -c "import sys; print(sys.executable)" > "%temp%\investor_py_check.txt" 2>&1
if errorlevel 1 goto :eof
findstr /I /C:"No Python at" "%temp%\investor_py_check.txt" >nul
if not errorlevel 1 goto :eof
set "PY_CMD=.venv\Scripts\python.exe"
goto :eof
