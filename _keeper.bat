@echo off
setlocal
title InvestorGPT Dashboard
cd /d "%~dp0"

set "PY_CMD=python"
if exist ".venv\Scripts\python.exe" (
    call :resolve_venv_python
)

:loop
echo [%date% %time%] Starting InvestorGPT Streamlit server...
if /i "%PY_CMD%"==".venv\Scripts\python.exe" (
    echo Using virtualenv Python at .venv\Scripts\python.exe
) else (
    echo Using system Python: python
)
"%PY_CMD%" -m streamlit run "%~dp0dashboard.py" --server.port 8502 --server.headless true
echo [%date% %time%] Server stopped. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto loop

:resolve_venv_python
".venv\Scripts\python.exe" -c "import sys; print(sys.executable)" > "%temp%\investor_py_check.txt" 2>&1
if errorlevel 1 goto :eof
findstr /I /C:"No Python at" "%temp%\investor_py_check.txt" >nul
if not errorlevel 1 goto :eof
set "PY_CMD=.venv\Scripts\python.exe"
goto :eof
