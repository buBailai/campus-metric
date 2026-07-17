import hashlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


APP_VERSION = '0.4.0'
PORTABLE_RELEASE = APP_VERSION
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


def windows_crlf_ascii(text):
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    return normalized.replace('\n', '\r\n').encode('ascii')


def validate_package(package_root, pth):
    required = [
        package_root / 'app.py',
        package_root / 'portable_launcher.py',
        package_root / 'evaluation_app' / '__init__.py',
        package_root / 'env' / 'python.exe',
        package_root / 'env' / 'Lib' / 'site-packages' / 'flask' / '__init__.py',
        package_root / 'env' / 'Lib' / 'site-packages' / 'sqlalchemy' / '__init__.py',
        package_root / 'env' / 'Lib' / 'site-packages' / 'waitress' / '__init__.py',
    ]
    missing = [str(path.relative_to(package_root)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f'Portable package is incomplete: {", ".join(missing)}')
    pth_lines = {line.strip() for line in pth.read_text(encoding='utf-8').splitlines()}
    if '..' not in pth_lines or 'Lib/site-packages' not in pth_lines or 'import site' not in pth_lines:
        raise RuntimeError('Embedded Python path file does not expose the app root and site-packages')
    for name in ('CampusMetric-启动.bat', 'Start-CampusMetric.bat'):
        content = (package_root / name).read_bytes()
        content.decode('ascii')
        if b'\r\n' not in content or b'\n' in content.replace(b'\r\n', b''):
            raise RuntimeError(f'{name} is not an ASCII CRLF batch file')


def main():
    root = Path(__file__).resolve().parent.parent
    build = Path(tempfile.gettempdir()) / 'campusmetric-windows-portable-build'
    cache = root / 'build' / 'windows-portable-cache'
    package_root = build / 'CampusMetric'
    env_dir = package_root / 'env'
    requirement_hash = hashlib.sha256((root / 'requirements.txt').read_bytes()).hexdigest()[:12]
    wheel_dir = cache / f'wheels-cp{PYTHON_TAG}-{requirement_hash}'
    dist = root / 'dist'
    cache.mkdir(parents=True, exist_ok=True)
    runtime_zip = cache / f'python-{PYTHON_VERSION}-embed-amd64.zip'
    legacy_runtime = build / f'python-{PYTHON_VERSION}-embed-amd64.zip'
    if not runtime_zip.is_file() and legacy_runtime.is_file():
        shutil.copy2(legacy_runtime, runtime_zip)
    legacy_wheels = build / 'wheels'
    if not any(wheel_dir.glob('*.whl')) and legacy_wheels.is_dir():
        wheel_dir.mkdir(parents=True, exist_ok=True)
        for wheel in legacy_wheels.glob('*.whl'):
            shutil.copy2(wheel, wheel_dir / wheel.name)
    if build.exists():
        shutil.rmtree(build)
    env_dir.mkdir(parents=True)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    dist.mkdir(exist_ok=True)

    if not runtime_zip.is_file():
        print(f'Downloading official Python runtime: {PYTHON_URL}', flush=True)
        urllib.request.urlretrieve(PYTHON_URL, runtime_zip)
    else:
        print(f'Using cached official Python runtime: {runtime_zip}', flush=True)
    with zipfile.ZipFile(runtime_zip) as archive:
        archive.extractall(env_dir)

    pth = env_dir / f'python{PYTHON_TAG}._pth'
    lines = [line for line in pth.read_text(encoding='utf-8').splitlines() if line.strip() != '#import site']
    lines.extend(['..', 'Lib/site-packages', 'import site'])
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
    launcher_text = (root / 'CampusMetric-启动.bat').read_text(encoding='ascii')
    launcher_bytes = windows_crlf_ascii(launcher_text)
    (package_root / 'CampusMetric-启动.bat').write_bytes(launcher_bytes)
    (package_root / 'Start-CampusMetric.bat').write_bytes(launcher_bytes)
    (package_root / 'README-Windows.txt').write_text(
        'CampusMetric Windows 免安装版\n'
        f'版本：{APP_VERSION}\n'
        f'免安装包修订：{PORTABLE_RELEASE}\n'
        f'内置 Python：{PYTHON_VERSION} 64-bit\n\n'
        '使用方法：\n'
        '1. 完整解压 ZIP 文件，不要直接在压缩包内运行。\n'
        '2. 双击 CampusMetric-启动.bat；若文件名显示异常，也可双击 Start-CampusMetric.bat。\n'
        '3. 启动器会识别本机局域网 IP，服务就绪后自动打开浏览器。\n'
        '4. 首次打开时按页面提示创建超级管理员和学年。\n\n'
        '局域网访问：启动窗口会显示实际访问地址，也可在管理端“移动访问”页面查看二维码。\n'
        '数据目录：instance（数据库）和 uploads（附件）。升级或迁移时请一并备份。\n',
        encoding='utf-8',
    )
    validate_package(package_root, pth)
    print('Portable structure check passed.', flush=True)

    output = dist / f'CampusMetric-Windows-Portable-{PORTABLE_RELEASE}.zip'
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
