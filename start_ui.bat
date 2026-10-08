@echo off
setlocal
title Math Worksheet Generator - UI
cd /d "%~dp0"

rem --- make LOCALAPPDATA available (avoids noisy site-packages warning) ---
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"

set "LOG=%~dp0ui_launch.log"
echo [%date% %time%] launcher started >> "%LOG%"

rem --- locate a python interpreter that really has reportlab ---
set "PY="
call :try_python "python"
if not defined PY call :try_python "C:\Users\Administrator\AppData\Local\Programs\OfficeAce\tools\python\python.exe"
if not defined PY call :try_python "%LOCALAPPDATA%\Programs\OfficeAce\tools\python\python.exe"
if not defined PY call :try_python "C:\Python313\python.exe"
if not defined PY call :try_python "C:\Python312\python.exe"
if not defined PY call :try_python "C:\Python311\python.exe"

if not defined PY (
    echo.
    echo   [ERROR] No usable Python found ^(python + reportlab required^).
    echo   Please install Python 3, then run:
    echo       pip install reportlab
    echo   [ERROR] python not found >> "%LOG%"
    echo.
    pause
    exit /b 1
)
echo [%date% %time%] python=%PY% >> "%LOG%"

echo.
echo   Starting local UI ...
echo   If the browser does not open automatically, visit:
echo       http://127.0.0.1:8765/
echo   Close this window to stop the server.
echo.

%PY% app_web.py
set "RC=%ERRORLEVEL%"
echo [%date% %time%] app_web exited with %RC% >> "%LOG%"

if not "%RC%"=="0" (
    echo.
    echo   [ERROR] Failed to start, exit code = %RC%
    echo   See ui_launch.log in this folder for details.
    echo.
    pause
)
endlocal
exit /b 0

:try_python
rem %~1 = candidate path/command
if defined PY goto :eof
"%~1" -c "import reportlab" >nul 2>nul
if not errorlevel 1 (
    set "PY=%~1"
    rem strip quotes is not needed; %~1 already unquoted
)
goto :eof
