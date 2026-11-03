@echo off
REM ============================================================
REM  KOSPI200 Crawler - build a Windows exe with PyInstaller
REM
REM  Builds inside a clean virtual environment (.venv-build) that
REM  has only the packages this app needs, so unrelated packages
REM  from the global Python (PySide6, pandas, ...) do not end up
REM  in the exe or clash with PyQt6.
REM
REM  Output: dist\Kospi200Crawler.exe
REM  (cmd.exe cannot parse UTF-8 Korean in .bat files reliably,
REM   so this file is kept ASCII only.)
REM ============================================================
cd /d "%~dp0"

if not exist .venv-build (
    echo [1/3] Creating build virtualenv...
    python -m venv .venv-build || goto :error
)

echo [2/3] Installing packages...
.venv-build\Scripts\python -m pip install --quiet --upgrade pip
.venv-build\Scripts\python -m pip install --quiet requests PyQt6 pyinstaller || goto :error

echo [3/3] Building exe...
.venv-build\Scripts\pyinstaller ^
    --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --name Kospi200Crawler ^
    --icon "%~dp0assets\app.ico" ^
    --add-data "%~dp0assets\app.ico;assets" ^
    --specpath build ^
    naver_kospi200_gui.py || goto :error

echo.
echo Done: %~dp0dist\Kospi200Crawler.exe
exit /b 0

:error
echo.
echo Build failed.
exit /b 1
