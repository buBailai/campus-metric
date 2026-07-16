@echo off
setlocal
cd /d "%~dp0"
title CampusMetric

if not exist "env\python.exe" goto missing_runtime
if not exist "evaluation_app\__init__.py" goto missing_app
if not exist "portable_launcher.py" goto missing_app

echo CampusMetric is starting...
echo The browser will open the detected LAN address after the server is ready.
"env\python.exe" "portable_launcher.py"
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" exit /b 0

echo.
echo CampusMetric stopped with error code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%

:missing_runtime
echo ERROR: env\python.exe is missing.
echo Please extract the complete Windows portable ZIP before starting.
pause
exit /b 1

:missing_app
echo ERROR: CampusMetric application files are incomplete.
echo Please download and extract the complete Windows portable ZIP again.
pause
exit /b 1
