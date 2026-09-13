@echo off
cd /d "%~dp0"
echo Pornire GlobePulse AI in modul DEMO (fara internet)...
python server.py --demo
if errorlevel 1 pause
