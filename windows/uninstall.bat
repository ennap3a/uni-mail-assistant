@echo off
REM Removes Uni Mail Assistant from this PC: background tasks, saved logins (optional), local data (optional).
REM Your emails and calendars are NOT touched.
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0service.ps1" off
del "%USERPROFILE%\Desktop\Uni Mail Assistant.lnk" 2>nul
set /p PY=<.python-path
if "%PY%"=="" set PY=python
"%PY%" uninstall.py
pause
