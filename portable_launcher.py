import os
import ipaddress
import secrets
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SENTINEL = ROOT / 'backups' / '.restart_pending'
DEFAULT_PORT = 5012


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


def _dotenv_value(key):
    target = ROOT / '.env'
    if not target.is_file():
        return ''
    try:
        for raw_line in target.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, value = line.split('=', 1)
            if name.strip() == key:
                return value.strip().strip('"\'')
    except OSError:
        return ''
    return ''


def configured_port():
    raw_value = os.environ.get('PORT') or _dotenv_value('PORT') or str(DEFAULT_PORT)
    try:
        port = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return port if 1 <= port <= 65535 else DEFAULT_PORT


def _usable_ipv4(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.version == 4
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_unspecified
        and not address.is_multicast
    )


def detect_lan_ipv4():
    candidates = []
    for target in (('8.8.8.8', 80), ('1.1.1.1', 80)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(target)
                candidates.append(probe.getsockname()[0])
        except OSError:
            continue
    try:
        candidates.extend(
            item[4][0]
            for item in socket.getaddrinfo(
                socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM,
            )
        )
    except OSError:
        pass
    return next((value for value in dict.fromkeys(candidates) if _usable_ipv4(value)), '127.0.0.1')


def wait_for_server(process, port, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def open_browser(url):
    try:
        if sys.platform == 'win32':
            os.startfile(url)
        else:
            webbrowser.open(url)
        return True
    except OSError:
        return False


def main():
    ensure_environment()
    env = os.environ.copy()
    env['CE_MANAGED_LAUNCHER'] = '1'
    env['HOST'] = '0.0.0.0'
    port = configured_port()
    env['PORT'] = str(port)
    lan_ip = detect_lan_ipv4()
    access_url = f'http://{lan_ip}:{port}'
    print(f'CampusMetric LAN address: {access_url}', flush=True)
    print('Keep this window open. Allow Python to use the local network if the system asks.', flush=True)
    bootstrap = (
        'import runpy, sys; '
        'sys.path.insert(0, sys.argv[1]); '
        "runpy.run_path(sys.argv[2], run_name='__main__')"
    )
    browser_opened = False
    while True:
        process = subprocess.Popen(
            [sys.executable, '-c', bootstrap, str(ROOT), str(ROOT / 'app.py')],
            cwd=ROOT,
            env=env,
        )
        if not browser_opened:
            if wait_for_server(process, port):
                browser_opened = open_browser(access_url)
                if not browser_opened:
                    print(f'Open this address manually: {access_url}', flush=True)
            else:
                print(f'Server did not become ready. Try this address later: {access_url}', flush=True)
        code = process.wait()
        if SENTINEL.exists():
            SENTINEL.unlink(missing_ok=True)
            continue
        raise SystemExit(code)


if __name__ == '__main__':
    main()
