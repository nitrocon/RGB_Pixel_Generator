@echo off
REM Batch Script for Running Python Script in Virtual Environment
REM =====================================================

REM Set colors for different statuses
set COLOR_RESET=^[[0m
set COLOR_GREEN=^[[32m
set COLOR_RED=^[[31m
set COLOR_YELLOW=^[[33m
set COLOR_CYAN=^[[36m
set COLOR_BLUE=^[[34m

echo !COLOR_CYAN!=====================================================
echo Welcome to the Project Runner!
echo =====================================================

REM Verify if Python 3.10 or higher is installed
echo !COLOR_BLUE!Checking if Python 3.10 or higher is installed...
for /f "tokens=2 delims= " %%i in ('python --version') do set PYTHON_VERSION=%%i
echo %PYTHON_VERSION% | findstr /r /c:"3\.[1-9][0-9]*\." >nul
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Python 3.10 or higher is not installed or not in the system PATH.
    echo Please install Python 3.10 or higher and ensure it is added to your PATH.
    pause
    exit /b 1
)
echo !COLOR_GREEN!Python 3.10 or higher found successfully.

REM Create a virtual environment with the found Python version
echo !COLOR_YELLOW!====================================================
echo Step 1: Creating virtual environment...
echo ====================================================
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo !COLOR_GREEN!Virtual environment created successfully.

REM Activate the virtual environment
echo !COLOR_YELLOW!====================================================
echo Step 2: Activating virtual environment...
echo ====================================================
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo !COLOR_GREEN!Virtual environment activated.

REM Display the Python version in the activated environment
echo !COLOR_BLUE!Python version in the virtual environment:
python --version

REM Check if pip is installed in the virtual environment
echo !COLOR_BLUE!Checking if pip is installed in the virtual environment...
pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_BLUE!pip not found. Installing pip...
    python -m ensurepip
    if %ERRORLEVEL% NEQ 0 (
        echo !COLOR_RED!ERROR: Failed to install pip.
        pause
        exit /b 1
    )
    echo !COLOR_GREEN!pip installed successfully in the virtual environment.
) else (
    echo !COLOR_GREEN!pip is already installed in the virtual environment.
)

REM Install dependencies (check if requirements.txt exists)
echo !COLOR_YELLOW!====================================================
echo Step 3: Installing dependencies...
echo ====================================================
if exist "requirements.txt" (
    echo !COLOR_BLUE!Found requirements.txt. Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo !COLOR_RED!ERROR: Failed to install dependencies from requirements.txt.
        pause
        exit /b 1
    )
    echo !COLOR_GREEN!Dependencies installed successfully.
) else (
    echo !COLOR_RED!ERROR: requirements.txt not found. Cannot proceed with dependency installation.
    pause
    exit /b 1
)

REM Run the generator.py script
echo !COLOR_YELLOW!====================================================
echo Step 4: Running generator.py script...
echo ====================================================
python generator.py
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Failed to run generator.py script.
    pause
    exit /b 1
)
echo !COLOR_GREEN!generator.py script ran successfully.

REM Final message
echo !COLOR_YELLOW!====================================================
echo All tasks completed! The batch script will now close.
echo =====================================================
pause
exit