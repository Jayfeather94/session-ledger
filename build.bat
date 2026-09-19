@echo off
chcp 65001 >nul
rem ---------------------------------------------------------------------------
rem  SessionLedger - one-click build.  Double-click it, or run it from a prompt.
rem
rem  NOTE: this file is deliberately ASCII-only.  cmd.exe parses a .bat with the
rem  console codepage that is active *when it starts reading the file*, so
rem  non-ASCII characters in here can eat the end of a line and corrupt the
rem  next one.  Keep it English.
rem
rem  Prerequisite: a venv built from an OFFICIAL python.org Python with the
rem  packages below.  The Microsoft Store build does NOT work - its python.exe
rem  is a zero-byte shim and the real interpreter lives in a protected folder
rem  that PyInstaller cannot read.
rem ---------------------------------------------------------------------------

setlocal

rem ============ EDIT THIS: point at your own venv ============
set VENV=D:\build\venv
set PY=%VENV%\Scripts\python.exe
rem ===========================================================

cd /d "%~dp0"

if not exist "%PY%" (
    echo.
    echo [x] Not found: %PY%
    echo.
    echo     Build the packaging environment first:
    echo.
    echo       winget install Python.Python.3.13
    echo       "%%LOCALAPPDATA%%\Programs\Python\Python313\python.exe" -m venv %VENV%
    echo       %VENV%\Scripts\activate
    echo       pip install PySide6==6.11.2 Pillow==12.3.0 pyinstaller
    echo.
    echo     When installing the official Python, do NOT tick "Add to PATH".
    echo     The python on PATH is the Store build and the app normally runs on
    echo     it.  If the official build gets in front, the launcher will use it
    echo     instead - and it has no PySide6, so the app will not start.
    echo.
    pause
    exit /b 1
)

echo.
echo === 1/5  Checking UI strings for missing translations ===
"%PY%" check_i18n.py
if errorlevel 1 (
    echo.
    echo [x] Some strings are not translated.  Add them to i18n.py first.
    echo     A miss does not crash anything, but an English user sees Chinese -
    echo     so it has to be caught here.
    pause
    exit /b 1
)

echo.
echo === 2/5  Cleaning previous output ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo === 3/5  Building ===
"%PY%" -m PyInstaller --clean --noconfirm build.spec
if errorlevel 1 (
    echo.
    echo [x] Build failed.  Read the errors above.
    pause
    exit /b 1
)

echo.
echo === 4/5  Copying the user guide and the license texts ===
rem These go NEXT TO the exe, not into PyInstaller's datas - a data file lands
rem under _internal\ where nobody looks.
rem Do NOT let the destination path end with a backslash: inside quotes, the
rem trailing \" is parsed as an escaped quote and the command fails silently.
copy /y "README.txt" "dist\SessionLedger"
if errorlevel 1 goto :copyfailed
xcopy /y /i /e "THIRD-PARTY-LICENSES" "dist\SessionLedger\THIRD-PARTY-LICENSES"
if errorlevel 1 goto :copyfailed
echo README.txt and THIRD-PARTY-LICENSES\ copied next to the EXE.
goto :selfcheck

:copyfailed
echo.
echo [x] Failed to copy README.txt / THIRD-PARTY-LICENSES into the output folder.
pause
exit /b 1

:selfcheck

echo.
echo === 5/5  Self-check ===
if not exist "dist\SessionLedger\SessionLedger.exe" (
    echo [x] dist\SessionLedger\SessionLedger.exe was not produced.
    pause
    exit /b 1
)
for /f "usebackq" %%A in (`powershell -NoProfile -Command "(Get-ChildItem -Recurse 'dist\SessionLedger' | Measure-Object -Property Length -Sum).Sum/1MB"`) do set SIZE=%%A
echo Output: dist\SessionLedger\SessionLedger.exe
echo Size:   %SIZE% MB  (typically 120-180 MB before trimming)
echo.
echo Next step (optional, roughly halves the size):
echo     powershell -ExecutionPolicy Bypass -File slim.ps1
echo Trimming fails SILENTLY when it goes wrong, so back up dist\SessionLedger\
echo first, and run the app after deleting each category.
echo.
pause
