@echo off
REM ============================================================
REM  S&P 500 Analyzer - build a Windows exe with PyInstaller
REM
REM  Builds inside a clean virtual environment (.venv-build-sp500)
REM  with only the packages this app needs (pandas, numpy,
REM  matplotlib, PyQt6), so the exe stays small and unrelated
REM  global packages do not clash with PyQt6.
REM
REM  The S&P 500 CSV next to this file is bundled into the exe,
REM  so it opens with data even when run from another folder.
REM  A CSV placed next to the exe takes priority over the bundled one.
REM
REM  Output: dist\SP500Analyzer.exe
REM  (cmd.exe cannot parse UTF-8 Korean in .bat files reliably,
REM   so this file is kept ASCII only; the Korean CSV name is
REM   matched with a wildcard instead.)
REM ============================================================
cd /d "%~dp0"

set "CSV_FILE="
for %%f in ("%~dp0S?P 500 *.csv") do set "CSV_FILE=%%~ff"
if not defined CSV_FILE (
    echo S^&P 500 CSV file not found next to this script.
    goto :error
)

if not exist .venv-build-sp500 (
    echo [1/3] Creating build virtualenv...
    python -m venv .venv-build-sp500 || goto :error
)

echo [2/3] Installing packages...
.venv-build-sp500\Scripts\python -m pip install --quiet --upgrade pip
.venv-build-sp500\Scripts\python -m pip install --quiet pandas numpy matplotlib PyQt6 pyinstaller || goto :error

echo [3/3] Building exe...
.venv-build-sp500\Scripts\pyinstaller ^
    --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --name SP500Analyzer ^
    --icon "%~dp0assets\app.ico" ^
    --add-data "%CSV_FILE%;data" ^
    --exclude-module tkinter ^
    --specpath build ^
    sp500_gui.py || goto :error

echo.
echo Done: %~dp0dist\SP500Analyzer.exe
exit /b 0

:error
echo.
echo Build failed.
exit /b 1
