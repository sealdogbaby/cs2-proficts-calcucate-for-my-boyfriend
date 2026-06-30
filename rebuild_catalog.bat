@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
set "EXIT_CODE=0"

echo WARNING: this clears the current test catalog and scan results.
choice /C YN /M "Continue"
if errorlevel 2 goto END
if not exist "%PYEXE%" goto NO_VENV

echo.
echo Rebuilding catalog...
"%PYEXE%" init_catalog.py --reset
set "EXIT_CODE=%ERRORLEVEL%"
goto END

:NO_VENV
echo .venv was not found. Run setup_windows.bat first.
set "EXIT_CODE=1"

:END
echo.
pause
exit /b %EXIT_CODE%
