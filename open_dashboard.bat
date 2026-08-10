@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LAUNCH_MODE=full"
if /I "%~1"=="--fast" set "LAUNCH_MODE=fast"

set "PY_CMD=python"
if exist ".venv\Scripts\python.exe" (
	set "PY_CMD=.venv\Scripts\python.exe"
)

if /I "%LAUNCH_MODE%"=="fast" (
	if not exist "webpage\index.html" (
		echo Fast mode requested, but no existing dashboard snapshot was found.
		echo Falling back to full mode...
		set "LAUNCH_MODE=full"
	)
)

set "STEP_SERVER=[1/4]"
set "STEP_REFRESH=[2/4]"
set "STEP_GENERATE=[3/4]"
set "STEP_OPEN=[4/4]"
if /I "%LAUNCH_MODE%"=="fast" (
	set "STEP_SERVER=[1/2]"
	set "STEP_OPEN=[2/2]"
)

echo ============================================
echo  InvestorGPT - Static Dashboard Launcher
echo ============================================
echo Mode: %LAUNCH_MODE%
echo.

call :write_status "Starting launcher" "Preparing startup checks..." "0"
start "" "webpage\loading.html"

echo %STEP_SERVER% Checking RAG server on port 8503...
call :write_status "Starting AI server" "Checking backend on port 8503..." "0"
call :is_port_listening 8503
if errorlevel 1 (
	powershell -ExecutionPolicy Bypass -File "scripts\start_server_bg.ps1"
	call :wait_for_port 8503 45
	if errorlevel 1 (
		call :write_status "AI server warning" "Backend startup is slow. Dashboard will still open." "0"
	)
)

if /I "%LAUNCH_MODE%"=="full" (
	echo %STEP_REFRESH% Refreshing market data...
	call :write_status "Refreshing market data" "Downloading latest stock history..." "0"
	"%PY_CMD%" scripts\refresh_data.py
	if errorlevel 1 (
		call :write_status "Refresh warning" "Market refresh failed, continuing with existing data..." "0"
	)

	echo %STEP_GENERATE% Generating dashboard data...
	call :write_status "Generating dashboard" "Building latest metrics and charts..." "0"
	"%PY_CMD%" scripts\generate_dashboard.py
	if errorlevel 1 (
		call :write_status "Generation warning" "Generation failed, opening dashboard with previous snapshot..." "0"
	)
) else (
	call :write_status "Fast mode" "Skipping refresh and generation. Using existing dashboard snapshot..." "0"
)

echo %STEP_OPEN% Opening dashboard...
call :write_status "Ready" "Dashboard is ready. Redirecting now..." "1"
echo Done!
exit /b 0

:is_port_listening
netstat -aon 2>nul | findstr ":%~1 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
	exit /b 0
)
exit /b 1

:wait_for_port
set "_port=%~1"
set /a _max=%~2
set /a _count=0
:wait_loop
call :is_port_listening %_port%
if %errorlevel%==0 exit /b 0
set /a _count+=1
if %_count% GEQ %_max% exit /b 1
timeout /t 1 /nobreak >nul
goto wait_loop

:write_status
set "_step=%~1"
set "_message=%~2"
set "_ready=%~3"
(
echo window.STARTUP_STATUS = {
echo   ready: %_ready%,
echo   step: "%_step%",
echo   message: "%_message%",
echo   updatedAt: "%date% %time%"
echo };
) > "webpage\startup_status.js"
exit /b 0
