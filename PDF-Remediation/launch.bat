@echo off
REM =============================================================================
REM launch.bat — Start the PDF Remediation Streamlit app
REM =============================================================================
REM Purpose: Activates the virtual environment and launches the Streamlit
REM          web server. Your browser will open automatically.
REM
REM How to run:
REM   Double-click this file, OR type  launch.bat  in Command Prompt.
REM =============================================================================

echo.
echo ============================================================
echo  Launching PDF Accessibility Remediation Tool...
echo ============================================================
echo.

REM Activate the virtual environment (must have run setup.bat first)
call venv\Scripts\activate.bat

REM Start Streamlit — it will open http://localhost:8501 in your browser
streamlit run app.py

pause
