@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\tv-blocker.exe" run --config "config.json" >> "tv-blocker.log" 2>&1
