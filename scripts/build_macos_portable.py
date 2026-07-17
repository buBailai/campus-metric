import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


APP_VERSION = '0.4.0'
PORTABLE_RELEASE = APP_VERSION
PYTHON_VERSION = '3.13.14'
PYTHON_TAG = '313'
PBS_RELEASE = '20260623'
PBS_BASE = f'https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}'

# arch name used by `uname -m` -> (python-build-standalone triple, pip platform tag)
ARCHES = {
    'arm64': ('aarch64-apple-darwin', 'macosx_15_0_arm64'),
    'x86_64': ('x86_64-apple-darwin', 'macosx_15_0_x86_64'),
}

INCLUDE = [
    'app.py', 'evaluation_app', 'templates', 'static', 'vendor', 'deployment',
    'requirements.txt', 'portable_launcher.py',
    'LICENSE', 'SECURITY.md', 'README.md',
]

LAUNCHER_NAMES = ('CampusMetric-启动.command', 'Start-CampusMetric.command')

LAUNCHER_SCRIPT = '''#!/bin/bash
cd "$(dirname "$0")"
# 清除下载隔离标记，保证内置 Python 可以直接运行
/usr/bin/xattr -rd com.apple.quarantine . >/dev/null 2>&1 || true
ARCH="$(/usr/bin/uname -m)"
case "$ARCH" in
    arm64) RUNTIME="runtime/arm64/python/bin/python3" ;;
    *) RUNTIME="runtime/x86_64/python/bin/python3" ;;
esac
if [ ! -x "$RUNTIME" ]; then
    echo "未找到内置 Python 运行时：$RUNTIME"
    echo "请先完整解压 ZIP，再双击启动。"
    read -r -p "按回车键退出..." _
    exit 1
fi
exec "$RUNTIME" portable_launcher.py
'''


def copy_entry(root, package_root, name):
    source = root / name
    target = package_root / name
    if source.is_dir():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def site_packages_dir(runtime_dir):
    return runtime_dir / 'python' / 'lib' / f'python{PYTHON_TAG[0]}.{PYTHON_TAG[1:]}' / 'site-packages'


def validate_package(package_root):
    required = [
        package_root / 'app.py',
        package_root / 'portable_launcher.py',
        package_root / 'evaluation_app' / '__init__.py',
    ]
    for arch in ARCHES:
        runtime = package_root / 'runtime' / arch
        required.extend([
            runtime / 'python' / 'bin' / 'python3',
            site_packages_dir(runtime) / 'flask' / '__init__.py',
            site_packages_dir(runtime) / 'sqlalchemy' / '__init__.py',
            site_packages_dir(runtime) / 'waitress' / '__init__.py',
            site_packages_dir(runtime) / 'PIL' / '__init__.py',
        ])
    missing = [str(path.relative_to(package_root)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f'Portable package is incomplete: {", ".join(missing)}')
    forbidden = ['.env', 'instance', 'uploads', 'backups', '开发进度.md', '项目记忆.md', '测试账号说明.md']
    present = [name for name in forbidden if (package_root / name).exists()]
    if present:
        raise RuntimeError(f'Portable package contains files that must stay private: {", ".join(present)}')
    for name in LAUNCHER_NAMES:
        launcher = package_root / name
        if not launcher.is_file() or not (launcher.stat().st_mode & 0o111):
            raise RuntimeError(f'{name} is missing or not executable')


def download(url, target):
    if target.is_file():
        print(f'Using cached: {target.name}', flush=True)
        return
    print(f'Downloading: {url}', flush=True)
    urllib.request.urlretrieve(url, target)


def main():
    root = Path(__file__).resolve().parent.parent
    build = Path(tempfile.gettempdir()) / 'campusmetric-macos-portable-build'
    cache = root / 'build' / 'macos-portable-cache'
    package_root = build / 'CampusMetric'
    requirement_hash = hashlib.sha256((root / 'requirements.txt').read_bytes()).hexdigest()[:12]
    dist = root / 'dist'
    cache.mkdir(parents=True, exist_ok=True)
    dist.mkdir(exist_ok=True)
    if build.exists():
        shutil.rmtree(build)
    package_root.mkdir(parents=True)

    for arch, (triple, pip_platform) in ARCHES.items():
        runtime_tar = cache / f'cpython-{PYTHON_VERSION}+{PBS_RELEASE}-{triple}-install_only_stripped.tar.gz'
        download(f'{PBS_BASE}/{runtime_tar.name}', runtime_tar)
        runtime_dir = package_root / 'runtime' / arch
        runtime_dir.mkdir(parents=True)
        print(f'Extracting runtime for {arch}...', flush=True)
        with tarfile.open(runtime_tar) as archive:
            archive.extractall(runtime_dir, filter='fully_trusted')

        wheel_dir = cache / f'wheels-{arch}-cp{PYTHON_TAG}-{requirement_hash}'
        wheel_dir.mkdir(parents=True, exist_ok=True)
        if not any(wheel_dir.glob('*.whl')):
            command = [
                sys.executable, '-m', 'pip', 'download', '--dest', str(wheel_dir),
                '--only-binary=:all:', '--platform', pip_platform, '--python-version', PYTHON_TAG,
                '--implementation', 'cp', '--abi', f'cp{PYTHON_TAG}', '-r', str(root / 'requirements.txt'),
            ]
            print(f'Downloading {arch} wheels...', flush=True)
            subprocess.run(command, check=True)
        wheels = sorted(wheel_dir.glob('*.whl'))
        if not wheels:
            raise RuntimeError(f'No {arch} wheels were downloaded')
        site_packages = site_packages_dir(runtime_dir)
        site_packages.mkdir(parents=True, exist_ok=True)
        for wheel in wheels:
            print(f'  extracting {wheel.name} ({arch})', flush=True)
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(site_packages)

    for name in INCLUDE:
        copy_entry(root, package_root, name)
    for name in LAUNCHER_NAMES:
        launcher = package_root / name
        launcher.write_text(LAUNCHER_SCRIPT, encoding='utf-8')
        launcher.chmod(0o755)
    (package_root / 'README-macOS.txt').write_text(
        'CampusMetric（校园全域智评系统）macOS 免安装版\n'
        f'版本：{APP_VERSION}\n'
        f'免安装包修订：{PORTABLE_RELEASE}\n'
        f'内置 Python：{PYTHON_VERSION}（Apple Silicon 与 Intel 双架构通用）\n\n'
        '使用方法：\n'
        '1. 完整解压 ZIP 文件，不要直接在压缩包内运行。\n'
        '2. 双击 CampusMetric-启动.command；若文件名显示异常，也可双击 Start-CampusMetric.command。\n'
        '3. 首次打开若提示“无法打开，因为它来自身份不明的开发者”：\n'
        '   按住 Control 点击该文件 → 选择“打开” → 再点“打开”确认；\n'
        '   若仍被拦截，请到 系统设置 → 隐私与安全性 → 点“仍要打开”。\n'
        '   （只需处理一次，之后可直接双击。）\n'
        '4. 启动器会识别本机局域网 IP，服务就绪后自动打开浏览器。\n'
        '   若系统询问“是否允许 Python 访问本地网络 / 接受传入网络连接”，请选择允许，\n'
        '   否则同事的手机和电脑将无法通过局域网访问本系统。\n'
        '5. 首次打开时按页面提示创建超级管理员和学年。\n\n'
        '局域网访问：启动窗口会显示实际访问地址，也可在管理端“移动访问”页面查看二维码。\n'
        '数据目录：instance（数据库）和 uploads（附件）。升级或迁移时请一并备份。\n'
        '退出：关闭启动的终端窗口，或在终端里按 Ctrl+C。\n',
        encoding='utf-8',
    )
    validate_package(package_root)
    print('Portable structure check passed.', flush=True)

    output = dist / f'CampusMetric-macOS-Portable-{PORTABLE_RELEASE}.zip'
    output.unlink(missing_ok=True)
    subprocess.run(
        ['ditto', '-c', '-k', '--keepParent', str(package_root), str(output)],
        check=True,
    )
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = dist / f'{output.name}.sha256'
    checksum.write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'Portable package: {output}')
    print(f'SHA256: {digest}')
    print(f'Size: {output.stat().st_size}')


if __name__ == '__main__':
    main()
