@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHON=C:\Users\okaju\AppData\Local\Python\bin\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

if not exist "logs" mkdir logs

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "LOG=logs\update_%STAMP%.txt"

echo [%date% %time%] ROUND1 goods update start> "%LOG%"
echo Working dir: %CD%>> "%LOG%"
echo Python: %PYTHON%>> "%LOG%"

"%PYTHON%" fetch_goods.py >> "%LOG%" 2>&1
set "ERR=%ERRORLEVEL%"

echo.>> "%LOG%"
echo [%date% %time%] exit_code=%ERR%>> "%LOG%"

REM 古いログを30日分だけ残す
powershell -NoProfile -Command "Get-ChildItem -Path 'logs\update_*.txt' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force" >> "%LOG%" 2>&1

exit /b %ERR%
