@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
set "EXIT_CODE=0"

if not exist "%PYEXE%" goto NO_VENV

echo.
echo Starting one scan...
"%PYEXE%" scanner.py --once
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" echo Scan did not complete. Review the messages above and logs\runtime.log.
goto END

:NO_VENV
echo .venv was not found. Run setup_windows.bat first.
set "EXIT_CODE=1"

:END
echo.
pause
exit /b %EXIT_CODE%
