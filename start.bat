@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist .venv (
  python -m venv .venv
  if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
python -c "import flask, sqlalchemy" >nul 2>&1
if errorlevel 1 (
  echo 正在安装依赖...
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 pip install -r requirements.txt
  if errorlevel 1 goto :error
)

if not exist .env (
  python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48)); print('HOST=0.0.0.0'); print('PORT=5012'); print('APP_DEBUG=0')" > .env
)

echo CampusMetric 已监听局域网，请使用 http://本机局域网IP:5012 访问
python app.py
pause
exit /b 0

:error
echo 启动失败，请确认已经安装 Python 3.11 或以上版本。
pause
exit /b 1
