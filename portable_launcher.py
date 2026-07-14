import os
import secrets
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SENTINEL = ROOT / 'backups' / '.restart_pending'


def ensure_environment():
    target = ROOT / '.env'
    if target.exists():
        return
    target.write_text(
        '\n'.join([
            f'SECRET_KEY={secrets.token_urlsafe(48)}',
            'HOST=0.0.0.0',
            'PORT=5012',
            'APP_DEBUG=0',
            '',
        ]),
        encoding='utf-8',
    )


def main():
    ensure_environment()
    env = os.environ.copy()
    env['CE_MANAGED_LAUNCHER'] = '1'
    while True:
        process = subprocess.Popen([sys.executable, str(ROOT / 'app.py')], cwd=ROOT, env=env)
        code = process.wait()
        if SENTINEL.exists():
            SENTINEL.unlink(missing_ok=True)
            continue
        raise SystemExit(code)


if __name__ == '__main__':
    main()
