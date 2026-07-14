#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PYTHON_CMD=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "未检测到 Python 3.11 或以上版本。"
    exit 1
fi

if [ ! -d ".venv" ]; then
    "$PYTHON_CMD" -m venv .venv
fi

source .venv/bin/activate

REQ_HASH=$(shasum requirements.txt 2>/dev/null | cut -d' ' -f1 || true)
OLD_HASH=$(cat .venv/.requirements_hash 2>/dev/null || true)
if [ "$REQ_HASH" != "$OLD_HASH" ] || ! python -c "import flask, sqlalchemy" >/dev/null 2>&1; then
    echo "正在安装或更新依赖..."
    if ! pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple; then
        pip install -r requirements.txt
    fi
    echo "$REQ_HASH" > .venv/.requirements_hash
fi

if [ ! -f ".env" ]; then
    SECRET=$("$PYTHON_CMD" -c "import secrets; print(secrets.token_urlsafe(48))")
    printf 'SECRET_KEY=%s\nHOST=0.0.0.0\nPORT=5012\nAPP_DEBUG=0\n' "$SECRET" > .env
fi

LAN_IP=$(ipconfig getifaddr en1 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || echo "本机局域网IP")
echo "CampusMetric 启动中：http://${LAN_IP}:5012"
exec python app.py
