@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed, or "Add python.exe to PATH" was not ticked.
  echo Please read START_HERE.txt, Step 1.
  pause
  exit /b
)
echo Installing what Wapas needs. This is slow only the first time...
python -m pip install -r requirements.txt
echo.
echo Starting Wapas. Your browser will open in a moment.
echo If it asks for your email, just press Enter.
echo Keep this window open while you use the app. Closing it stops the app.
python -m streamlit run app.py
pause
