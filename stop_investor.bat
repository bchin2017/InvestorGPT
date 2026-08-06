@echo off
echo Stopping InvestorGPT dashboard server...
taskkill /fi "windowtitle eq InvestorGPT Dashboard" /f >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8502 " ^| findstr "LISTENING" 2^>nul') do taskkill /f /pid %%a >nul 2>&1
echo Dashboard stopped.
timeout /t 2 /nobreak >nul
