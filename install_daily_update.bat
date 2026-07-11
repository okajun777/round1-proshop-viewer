@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "TASK_NAME=Round1GoodsUpdate"
set "BAT=%~dp0update_goods.bat"

echo タスク「%TASK_NAME%」を毎朝 6:00 に登録します...
echo 対象: %BAT%
echo.

schtasks /Create /F /TN "%TASK_NAME%" /TR "\"%BAT%\"" /SC DAILY /ST 06:00 /RL LIMITED
if errorlevel 1 (
  echo 登録に失敗しました。管理者権限が必要な場合があります。
  exit /b 1
)

echo.
echo 登録完了。確認:
schtasks /Query /TN "%TASK_NAME%" /V /FO LIST | findstr /I "TaskName Status Next Run Time Task To Run Schedule"
echo.
echo 手動実行: schtasks /Run /TN "%TASK_NAME%"
echo 削除:     schtasks /Delete /TN "%TASK_NAME%" /F
