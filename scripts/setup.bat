@echo off
setlocal enabledelayedexpansion

:: Colors for Windows console
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "NC=[0m"

:: Print banner
echo %GREEN%
echo ======================================================================
echo                 Daily Positivity SMS Service Setup
echo ======================================================================
echo %NC%

:: Check if running from project root
if not exist "pyproject.toml" (
    echo %RED%Error: This script must be run from the project root directory%NC%
    echo Please run: scripts\setup.bat
    exit /b 1
)

:: Check Python installation
echo %YELLOW%Checking Python installation...%NC%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%Python is not installed. Please install Python 3.9 or higher%NC%
    exit /b 1
)

:: Make setup_dev.py executable (not really needed on Windows but for consistency)
icacls scripts\setup_dev.py /grant:r Everyone:RX >nul 2>&1

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo %YELLOW%Creating virtual environment...%NC%
    python -m venv .venv
)

:: Activate virtual environment
echo %YELLOW%Activating virtual environment...%NC%
call .venv\Scripts\activate.bat

:: Install Poetry using pip
echo %YELLOW%Installing Poetry...%NC%
pip install poetry

:: Install required packages for setup
echo %YELLOW%Installing setup requirements...%NC%
pip install requests psycopg2-binary twilio openai

:: Run the Python setup script
echo %YELLOW%Running setup script...%NC%
python scripts\setup_dev.py

:: Deactivate virtual environment
deactivate

echo %GREEN%
echo ======================================================================
echo                         Setup Complete!
echo ======================================================================
echo %NC%
echo To start development:
echo 1. Activate the virtual environment: .venv\Scripts\activate
echo 2. Start the development server: poetry run flask run
echo 3. Start the scheduler: poetry run python -m src.cli schedule_messages
echo 4. Start the processor: poetry run python -m src.cli process_messages
echo.
echo For more information, see docs/PROJECT_GUIDE.md

:: Pause to keep the window open if double-clicked
pause
