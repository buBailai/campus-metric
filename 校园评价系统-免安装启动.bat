@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist env\python.exe (
  echo CampusMetric 免安装 Python 运行环境不存在，请使用正式发布包。
  pause
  exit /b 1
)
env\python.exe portable_launcher.py
pause
