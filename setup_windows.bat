@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

echo ================================================
echo CS2 Steam x BUFF Radar V1 - Setup
echo ================================================
echo.

py -3 --version
if errorlevel 1 goto PYTHON_NOT_FOUND

if exist ".venv\Scripts\python.exe" goto VENV_READY

echo Creating virtual environment...
py -3 -m venv .venv
if errorlevel 1 goto VENV_FAILED

:VENV_READY
set "PYEXE=%~dp0.venv\Scripts\python.exe"

echo.
echo Installing dependencies...
"%PYEXE%" -m pip install --upgrade pip
if errorlevel 1 goto PIP_FAILED

"%PYEXE%" -m pip install -r requirements.txt
if errorlevel 1 goto REQUIREMENTS_FAILED

if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"

"%PYEXE%" -c "import sqlite3; print('SQLite available:', sqlite3.sqlite_version)"
if errorlevel 1 goto SQLITE_FAILED

echo.
echo Setup completed.
echo Next steps:
echo 1. Open .env and fill in CSQAQ_API_TOKEN.
echo 2. Bind your current public IP on the CSQAQ website.
echo 3. Run init_catalog.bat.
goto END

:PYTHON_NOT_FOUND
echo Python launcher "py" was not found.
echo Install Python 3 and select Add Python to PATH.
goto END

:VENV_FAILED
echo Failed to create .venv.
goto END

:PIP_FAILED
echo Failed while upgrading pip. Check the network connection.
goto END

:REQUIREMENTS_FAILED
echo Failed to install required packages. Check the network connection.
goto END

:SQLITE_FAILED
echo Python SQLite check failed.
goto END

:END
echo.
pause
exit /b
