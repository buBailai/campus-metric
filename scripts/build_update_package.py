import hashlib
import json
import runpy
import sys
import zipfile
from pathlib import Path


INCLUDE = [
    'app.py', 'evaluation_app', 'templates', 'static', 'scripts', 'docs', 'examples', 'vendor', 'deployment',
    'requirements.txt', 'start.sh', 'start.bat', 'portable_launcher.py',
    'CampusMetric-启动.bat', 'README.md', 'LICENSE', 'SECURITY.md', '开发进度.md',
    '班主任考评方案指标与计分规则梳理.md',
]


def main(version):
    root = Path(__file__).resolve().parent.parent
    changelog_module = runpy.run_path(str(root / 'evaluation_app' / 'changelog.py'))
    changelog = changelog_module['CHANGELOG']
    if not changelog or changelog[0].get('version') != version:
        latest = changelog[0].get('version') if changelog else '无'
        raise SystemExit(f'请先在 evaluation_app/changelog.py 顶部补充版本 {version}（当前最新：{latest}）')
    notes = changelog_module['notes_for_version'](version)
    output_dir = root / 'dist'
    output_dir.mkdir(exist_ok=True)
    package = output_dir / f'campus-evaluation-update-{version}.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in INCLUDE:
            entry = root / name
            print(f'adding {name}', flush=True)
            paths = [entry] if entry.is_file() else entry.rglob('*') if entry.is_dir() else []
            for path in paths:
                relative = path.relative_to(root)
                if (
                    not path.is_file() or path.suffix == '.pyc' or path.name == '.DS_Store'
                    or '__pycache__' in relative.parts or relative.parts[:2] == ('docs', 'assets')
                    or relative.as_posix() == 'docs/公网测试部署.md'
                ):
                    continue
                print(f'  {relative}', flush=True)
                archive.write(path, relative)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    manifest = {
        'version': version, 'zip': package.name, 'sha256': digest,
        'size': package.stat().st_size,
        'notes': notes,
        'min_from': '0.1.0',
    }
    manifest_path = output_dir / 'version.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(package)
    print(manifest_path)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '0.3.7')
