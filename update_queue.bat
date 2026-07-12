@echo off
cd /d "%~dp0"
python fetch_queue.py
if errorlevel 1 (
  echo Failed to fetch queue status.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8791/queue.html
python -m http.server 8791
