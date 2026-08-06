@echo off
cd /d "%~dp0"
echo ============================================
echo  InvestorGPT - Static Dashboard Launcher
echo ============================================
echo.
echo [1/2] Refreshing market data...
python scripts\refresh_data.py
echo.
echo [2/2] Generating dashboard...
python scripts\generate_dashboard.py
echo.
echo Opening dashboard in browser...
start "" "webpage\index.html"
echo Done!
