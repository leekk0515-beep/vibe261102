@echo off
REM ============================================================
REM  Birth Statistics Analyzer - build a Windows exe with PyInstaller
REM
REM  Builds inside a clean virtual environment (.venv-build-birth)
REM  with only the packages this app needs (pandas, openpyxl,
REM  matplotlib, PyQt6), so the exe stays small and unrelated
REM  global packages do not clash with PyQt6.
REM
REM  The birth statistics xlsx next to this file is bundled into
REM  the exe, so it opens with data even when run from another
REM  folder. An xlsx placed next to the exe takes priority over
REM  the bundled one.
REM
REM  Output: dist\BirthAnalyzer.exe
REM  (cmd.exe cannot parse UTF-8 Korean in .bat files reliably,
REM   so this file is kept ASCII only; the Korean xlsx name is
REM   matched with a wildcard instead.)
REM ============================================================
cd /d "%~dp0"

set "XLSX_FILE="
for %%f in ("%~dp0*__*__*.xlsx") do set "XLSX_FILE=%%~ff"
if not defined XLSX_FILE (
    echo Birth statistics xlsx file not found next to this script.
    goto :error
)

if not exist .venv-build-birth (
    echo [1/3] Creating build virtualenv...
    python -m venv .venv-build-birth || goto :error
)

echo [2/3] Installing packages...
.venv-build-birth\Scripts\python -m pip install --quiet --upgrade pip
.venv-build-birth\Scripts\python -m pip install --quiet pandas openpyxl matplotlib PyQt6 pyinstaller || goto :error

echo [3/3] Building exe...
.venv-build-birth\Scripts\pyinstaller ^
    --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --name BirthAnalyzer ^
    --icon "%~dp0assets\app.ico" ^
    --add-data "%XLSX_FILE%;data" ^
    --exclude-module tkinter ^
    --specpath build ^
    birth_gui.py || goto :error

echo.
echo Done: %~dp0dist\BirthAnalyzer.exe
exit /b 0

:error
echo.
echo Build failed.
exit /b 1
