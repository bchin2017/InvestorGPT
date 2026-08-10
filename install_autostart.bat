@echo off
:: Install a Windows Scheduled Task to start rag_server.py at login.
:: Run this ONCE (elevated). The server will auto-start on every login thereafter.
cd /d "%~dp0"

set "TASK_NAME=InvestorGPT_RAG_Server"
set "SCRIPT_PATH=%~dp0scripts\start_server_bg.ps1"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %errorlevel%==0 (
    echo Task "%TASK_NAME%" already exists. Deleting and re-creating...
    schtasks /Delete /TN "%TASK_NAME%" /F
)

schtasks /Create /TN "%TASK_NAME%" ^
    /TR "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT_PATH%\"" ^
    /SC ONLOGON ^
    /RL HIGHEST ^
    /F

if %errorlevel%==0 (
    echo.
    echo SUCCESS: Task "%TASK_NAME%" created.
    echo The RAG server will auto-start at every login.
    echo To remove: schtasks /Delete /TN "%TASK_NAME%" /F
) else (
    echo.
    echo FAILED: Run this script as Administrator.
)
pause
