import hashlib
import json
import sys
import zipfile
from pathlib import Path


INCLUDE = [
    'app.py', 'evaluation_app', 'templates', 'static', 'scripts', 'docs', 'examples', 'vendor', 'deployment',
    'requirements.txt', 'start.sh', 'start.bat', 'portable_launcher.py',
    'CampusMetric-启动.bat', '校园评价系统-免安装启动.bat', 'README.md', 'LICENSE', 'SECURITY.md', '开发进度.md',
    '通用型评价系统产品功能大纲.md', '班主任考评方案指标与计分规则梳理.md',
]


def main(version):
    root = Path(__file__).resolve().parent.parent
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
                if not path.is_file() or path.suffix == '.pyc' or path.name == '.DS_Store' or '__pycache__' in relative.parts:
                    continue
                print(f'  {relative}', flush=True)
                archive.write(path, relative)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    manifest = {
        'version': version, 'zip': package.name, 'sha256': digest,
        'size': package.stat().st_size,
        'notes': '项目正式命名为 CampusMetric，统一网页标题、登录页、侧栏和启动器品牌；补充 GitHub 与 Windows 免安装版发布入口；免安装启动时自动生成随机会话密钥。',
        'min_from': '0.1.0',
    }
    manifest_path = output_dir / 'version.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(package)
    print(manifest_path)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '0.3.0')
