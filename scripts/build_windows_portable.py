import hashlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


APP_VERSION = '0.3.0'
PYTHON_VERSION = '3.13.14'
PYTHON_TAG = '313'
PYTHON_URL = f'https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip'

INCLUDE = [
    'app.py', 'evaluation_app', 'templates', 'static', 'vendor', 'deployment',
    'requirements.txt', 'portable_launcher.py', 'CampusMetric-启动.bat',
    'LICENSE', 'SECURITY.md', 'README.md',
]


def copy_entry(root, package_root, name):
    source = root / name
    target = package_root / name
    if source.is_dir():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main():
    root = Path(__file__).resolve().parent.parent
    build = root / 'build' / 'windows-portable'
    package_root = build / 'CampusMetric'
    env_dir = package_root / 'env'
    wheel_dir = build / 'wheels'
    dist = root / 'dist'
    shutil.rmtree(build, ignore_errors=True)
    env_dir.mkdir(parents=True)
    wheel_dir.mkdir(parents=True)
    dist.mkdir(exist_ok=True)

    runtime_zip = build / f'python-{PYTHON_VERSION}-embed-amd64.zip'
    print(f'Downloading official Python runtime: {PYTHON_URL}', flush=True)
    urllib.request.urlretrieve(PYTHON_URL, runtime_zip)
    with zipfile.ZipFile(runtime_zip) as archive:
        archive.extractall(env_dir)

    pth = env_dir / f'python{PYTHON_TAG}._pth'
    lines = [line for line in pth.read_text(encoding='utf-8').splitlines() if line.strip() != '#import site']
    lines.extend(['Lib/site-packages', 'import site'])
    pth.write_text('\n'.join(dict.fromkeys(lines)) + '\n', encoding='utf-8')

    command = [
        sys.executable, '-m', 'pip', 'download', '--dest', str(wheel_dir),
        '--only-binary=:all:', '--platform', 'win_amd64', '--python-version', PYTHON_TAG,
        '--implementation', 'cp', '--abi', f'cp{PYTHON_TAG}', '-r', str(root / 'requirements.txt'),
    ]
    print('Downloading Windows wheels...', flush=True)
    subprocess.run(command, check=True)
    site_packages = env_dir / 'Lib' / 'site-packages'
    site_packages.mkdir(parents=True)
    wheels = sorted(wheel_dir.glob('*.whl'))
    if not wheels:
        raise RuntimeError('No Windows wheels were downloaded')
    for wheel in wheels:
        print(f'  extracting {wheel.name}', flush=True)
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(site_packages)

    for name in INCLUDE:
        copy_entry(root, package_root, name)
    (package_root / 'README-Windows.txt').write_text(
        'CampusMetric Windows 免安装版\n'
        f'版本：{APP_VERSION}\n'
        f'内置 Python：{PYTHON_VERSION} 64-bit\n\n'
        '使用方法：\n'
        '1. 完整解压 ZIP 文件，不要直接在压缩包内运行。\n'
        '2. 双击 CampusMetric-启动.bat。\n'
        '3. 浏览器访问 http://127.0.0.1:5012。\n'
        '4. 首次打开时按页面提示创建超级管理员和学年。\n\n'
        '局域网访问：在管理端“移动访问”页面查看二维码。\n'
        '数据目录：instance（数据库）和 uploads（附件）。升级或迁移时请一并备份。\n',
        encoding='utf-8',
    )

    output = dist / f'CampusMetric-Windows-Portable-{APP_VERSION}.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package_root.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(build))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = dist / f'{output.name}.sha256'
    checksum.write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'Portable package: {output}')
    print(f'SHA256: {digest}')
    print(f'Size: {output.stat().st_size}')


if __name__ == '__main__':
    main()
