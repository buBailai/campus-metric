import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import requests

from .version import APP_VERSION


OFFICIAL_UPDATE_BASE_URL = 'http://bubailai.top/campus-evaluation/updates'


def effective_update_base_url(custom_url=''):
    return str(custom_url or '').strip().rstrip('/') or OFFICIAL_UPDATE_BASE_URL


DATA_EXCLUDE = (
    'instance/', 'uploads/', 'backups/', '.env', '.venv/', 'env/', '.git/',
    '__pycache__/', 'release/',
)


def version_tuple(value):
    try:
        return tuple(int(part) for part in str(value).split('.'))
    except ValueError:
        return (0,)


def fetch_manifest(base_url):
    url = base_url.rstrip('/') + '/version.json'
    response = requests.get(url, headers={'User-Agent': 'campus-evaluation-updater'}, timeout=15)
    response.raise_for_status()
    data = response.json()
    for key in ('version', 'zip', 'sha256'):
        if not data.get(key):
            raise ValueError(f'更新清单缺少 {key}')
    return data


def staging_root(app_root):
    return Path(app_root) / 'backups' / 'update_staging'


def download_and_stage(app_root, base_url, manifest):
    root = staging_root(app_root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    package = root / 'pending.zip'
    url = manifest['zip'] if str(manifest['zip']).startswith('http') else base_url.rstrip('/') + '/' + manifest['zip']
    digest = hashlib.sha256()
    with requests.get(url, headers={'User-Agent': 'campus-evaluation-updater'}, timeout=60, stream=True) as response:
        response.raise_for_status()
        with package.open('wb') as output:
            for chunk in response.iter_content(65536):
                if chunk:
                    output.write(chunk)
                    digest.update(chunk)
    if digest.hexdigest().lower() != str(manifest['sha256']).lower():
        package.unlink(missing_ok=True)
        raise ValueError('sha256 校验失败，更新包已丢弃')
    target = root / 'app_new'
    target.mkdir()
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            parts = Path(name).parts
            if Path(name).is_absolute() or '..' in parts:
                raise ValueError('更新包包含非法路径')
        archive.extractall(target)
    package.unlink(missing_ok=True)
    if not (target / 'app.py').exists() or not (target / 'evaluation_app').is_dir():
        raise ValueError('更新包结构不正确')
    (root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return target


def is_excluded(relative):
    value = str(relative).replace('\\', '/').lstrip('/')
    if value.endswith('.pyc') or value.endswith('/.DS_Store') or value == '.DS_Store' or '/__pycache__/' in '/' + value:
        return True
    return any(value == item.rstrip('/') or value.startswith(item) for item in DATA_EXCLUDE)


def apply_staged_update(app_root):
    root = Path(app_root)
    staging = staging_root(root) / 'app_new'
    if not (staging / 'app.py').exists():
        raise ValueError('没有已下载的更新')
    rollback = root / 'backups' / f'update_rollback_{datetime.now():%Y%m%d_%H%M%S}'
    database = root / 'instance' / 'evaluation.sqlite'
    if database.exists():
        database_snapshot = rollback / 'instance' / 'evaluation.sqlite'
        database_snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(database, database_snapshot)
    replaced = 0
    for source in staging.rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(staging)
        if is_excluded(relative):
            continue
        destination = root / relative
        if destination.exists():
            snapshot = rollback / relative
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, snapshot)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        replaced += 1
    return replaced, rollback


def status(app_root):
    pending = (staging_root(app_root) / 'app_new' / 'app.py').exists()
    return {'version': APP_VERSION, 'managed': os.getenv('CE_MANAGED_LAUNCHER') == '1', 'pending': pending}
