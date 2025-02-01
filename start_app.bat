@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Set project root directory (modify this path as needed)
SET PROJECT_ROOT=%CD%

REM Set paths to the frontend and backend directories
SET FRONTEND_DIR=%PROJECT_ROOT%\frontend
SET BACKEND_DIR=%PROJECT_ROOT%\backend

REM Set the virtual environment directory
SET VENV_DIR=%PROJECT_ROOT%\.venv

REM Check if virtual environment exists, create if missing
IF NOT EXIST "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
) ELSE (
    echo Virtual environment already exists.
)

REM Activate the virtual environment
CALL "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
echo Installing backend dependencies...
python -m pip install -r "%BACKEND_DIR%\requirements.txt"

echo Installing frontend dependencies...
python -m pip install -r "%FRONTEND_DIR%\requirements.txt"

REM Start backend
echo Starting backend...
START "Backend" /MIN CMD /C "cd /D %BACKEND_DIR% && python app.py"

REM Start frontend
echo Starting frontend...
START "Frontend" CMD /C "cd /D %FRONTEND_DIR% && streamlit run frontend.py"

echo Applications started. Press any key to exit...
pause