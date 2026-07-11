@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === ROUND1 商品一覧を LINE で見られるように公開します ===
echo.
echo ・PCの電源が入っている間だけ有効な一時URLです
echo ・表示された https://....trycloudflare.com を LINE に貼ってください
echo ・終了するときはこの窓を閉じてください
echo.

netstat -ano | findstr ":8791" | findstr "LISTENING" >nul
if errorlevel 1 (
  start "r1b-goods-server" /min cmd /c "python -m http.server 8791"
  timeout /t 2 >nul
)

cloudflared tunnel --url http://127.0.0.1:8791
