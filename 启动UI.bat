@echo off
cd /d "%~dp0"
call "%~dp0start_ui.bat"
if errorlevel 1 pause
