@echo off
setlocal

cd /d "%~dp0"
set "APP_DIR=%~dp0"

rem Optional Google AdSense configuration. Remove "rem" and replace the values after approval.
rem set "GOOGLE_ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX"
rem set "GOOGLE_ADSENSE_SLOT=1234567890"

echo ==============================================
echo        Word Search Studio
 echo ==============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found on this computer.
    echo Install Python 3.10 or newer, then run this file again.
    pause
    exit /b 1
)

python -c "import streamlit, pydantic, PIL, xlsxwriter" >nul 2>&1
if errorlevel 1 (
    echo Installing or updating Word Search Studio dependencies...
    python -m pip install -r "%APP_DIR%requirements.txt"
    if errorlevel 1 (
        echo.
        echo Dependency installation failed. Check your internet connection or Python installation.
        pause
        exit /b 1
    )
)

echo Starting the local Word Search Studio interface...
echo Close this window to stop the tool.
echo.
python -m streamlit run "%APP_DIR%app.py"

if errorlevel 1 (
    echo.
    echo The application stopped with an error.
    pause
)
