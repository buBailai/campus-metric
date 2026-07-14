@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CampusMetric
if not exist env\python.exe (
  echo CampusMetric 免安装 Python 运行环境不存在，请重新下载完整 Windows 免安装包。
  pause
  exit /b 1
)
echo CampusMetric 正在启动...
echo 启动后请访问 http://127.0.0.1:5012
env\python.exe portable_launcher.py
pause
