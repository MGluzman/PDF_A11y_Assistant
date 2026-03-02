@echo off
REM =============================================================================
REM setup.bat — One-click environment setup for PDF Remediation Tool
REM =============================================================================
REM Purpose: Creates an isolated Python virtual environment (venv), then
REM          installs all required libraries from requirements.txt.
REM
REM A "virtual environment" is a self-contained Python installation just for
REM this project. It prevents conflicts with other Python projects on the
REM same computer.
REM
REM How to run:
REM   1. Double-click this file in Windows Explorer, OR
REM   2. Open a Command Prompt in this folder and type:  setup.bat
REM =============================================================================

echo.
echo ============================================================
echo  PDF Accessibility Remediation Tool — Environment Setup
echo ============================================================
echo.

REM --- Step 1: Verify Python is installed ----------------------------------
REM 'py' is the Windows Python Launcher that works even when 'python'
REM is not in the PATH. We redirect error output to nul to keep it clean.
py --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python is not installed or not found.
    echo.
    echo  Please install Python 3.11 or newer from:
    echo  https://www.python.org/downloads/windows/
    echo.
    echo  IMPORTANT: During installation, check the box that says
    echo  "Add Python to PATH" before clicking Install.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
py --version
echo.

REM --- Step 2: Create a virtual environment --------------------------------
REM A virtual environment ("venv") isolates this project's packages from
REM other Python projects. The folder "venv" will be created here.
IF NOT EXIST "venv\" (
    echo [INFO] Creating virtual environment in .\venv ...
    py -m venv venv
    echo [OK]  Virtual environment created.
) ELSE (
    echo [INFO] Virtual environment already exists, skipping creation.
)
echo.

REM --- Step 3: Activate the virtual environment ----------------------------
REM Activating means all pip/python commands now use the venv, not the
REM system Python.
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK]  Virtual environment activated.
echo.

REM --- Step 4: Upgrade pip -------------------------------------------------
REM pip is the Python package installer. We upgrade it first to avoid
REM warnings and ensure compatibility with the latest packages.
echo [INFO] Upgrading pip...
py -m pip install --upgrade pip
echo.

REM --- Step 5: Install all required libraries ------------------------------
echo [INFO] Installing all libraries from requirements.txt...
echo        This may take several minutes on first run (downloading ~500 MB).
echo.
pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Some packages failed to install. See messages above.
    pause
    exit /b 1
)
echo.
echo [OK]  All Python libraries installed successfully.
echo.

REM --- Step 6: Remind user about Tesseract ---------------------------------
echo ============================================================
echo  IMPORTANT: Tesseract OCR Binary Required
echo ============================================================
echo.
echo  pytesseract is a Python wrapper — it still needs the actual
echo  Tesseract program installed on Windows separately.
echo.
echo  Download the installer from:
echo  https://github.com/UB-Mannheim/tesseract/wiki
echo  (Choose the 64-bit Windows installer)
echo.
echo  After installing Tesseract, note the path (usually):
echo  C:\Program Files\Tesseract-OCR\tesseract.exe
echo.
echo  You will enter this path in the app's Settings panel.
echo ============================================================
echo.
echo Setup complete! To START the app, run:   launch.bat
echo.
pause
