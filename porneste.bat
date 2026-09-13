@echo off
cd /d "%~dp0"
echo Pornire GlobePulse AI...
python server.py %*
if errorlevel 1 pause
