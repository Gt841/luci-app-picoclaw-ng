#!/usr/bin/env python3
"""
Build IPK + source tarball for luci-app-picoclaw-ng v3.0.2

沿用 v1.1.6 的 tar.gz 三层嵌套做法（不用 AR），本版差异：
  - OpenClash 风格生命周期页面：启停/重启/自启/面板/导出/日志
  - 双运行模式（Gateway / Launcher），Gateway 默认；面板临时开启、备用端口
  - 按 CPU 架构自动选择上游资产（可手动覆盖），固定 0.3.1 + SHA256 校验
  - 同时产出源码包 luci-app-picoclaw-ng-<ver>-source.tar.gz

用法（在仓库根目录执行）：
  python3 scripts/build-ipk.py
  PC_PRIVACY_EXTRA="secret1,secret2" python3 scripts/build-ipk.py   # 追加要拦截的字符串

产物写到仓库的 dist/ 目录。
"""

import io
import os
import re
import tarfile
import time
import hashlib

PKG_NAME = "luci-app-picoclaw-ng"
PKG_VERSION = "3.0.2"
PKG_RELEASE = "1"
PKG_ARCH = "all"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # <repo>/scripts
REPO_DIR = os.path.dirname(BASE_DIR)                          # <repo>
OUTPUT_DIR = os.path.join(REPO_DIR, "dist")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"{PKG_NAME}_{PKG_VERSION}-{PKG_RELEASE}_{PKG_ARCH}.ipk")
SOURCE_FILE = os.path.join(OUTPUT_DIR, f"{PKG_NAME}-{PKG_VERSION}-source.tar.gz")

# 包源码按 OpenWrt / iStoreOS 约定存放：apps/<id>/<package>/
#   luasrc/  -> /usr/lib/lua/luci
#   root/    -> /
PKG_DIR = os.path.join(REPO_DIR, "apps", "picoclaw", "luci-app-picoclaw-ng")
TREE_MAPS = [("luasrc", "usr/lib/lua/luci"), ("root", "")]
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".gz", ".xz",
              ".woff", ".woff2", ".ttf", ".so"}


def collect_files():
    """展开包目录，返回 [(相对路径, 绝对路径, 包内路径, 权限)]"""
    out = []
    for sub, dest in TREE_MAPS:
        base = os.path.join(PKG_DIR, sub)
        if not os.path.isdir(base):
            raise FileNotFoundError(base)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for fn in sorted(filenames):
                if fn in ('.DS_Store', 'Thumbs.db') or fn.endswith('.pyc'):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, base).replace(os.sep, '/')
                arc = './' + '/'.join(p for p in (dest, rel) if p)
                mode = 0o644
                if fn.endswith('.sh') or arc.startswith('./etc/init.d/'):
                    mode = 0o755
                out.append((rel, full, arc, mode))
    return out


def collect_dirs(entries):
    dirs = {'.'}
    for _, _, arc, _ in entries:
        parts = arc.split('/')[1:-1]
        for i in range(1, len(parts) + 1):
            dirs.add('./' + '/'.join(parts[:i]))
    return sorted(dirs, key=lambda d: (d.count('/'), d))

POSTINST = ('#!/bin/sh\n[ "${IPKG_NO_SCRIPT}" = "1" ] && exit 0\n'
            '[ -s ${IPKG_INSTROOT}/lib/functions.sh ] || exit 0\n'
            '. ${IPKG_INSTROOT}/lib/functions.sh\ndefault_postinst $0 $@\n')
PRERM = ('#!/bin/sh\n[ -s ${IPKG_INSTROOT}/lib/functions.sh ] || exit 0\n'
         '. ${IPKG_INSTROOT}/lib/functions.sh\ndefault_prerm $0 $@\n')

TEXT_EXT = {'.lua', '.htm', '.sh', '.md', '.po', '.svg', '.init', '.txt', '.json'}
SECRET_PATTERNS = [
    (r'sk-[A-Za-z0-9_\-]{20,}', 'api key (sk-...)'),
    (r'sk-or-v1-[A-Za-z0-9]{20,}', 'openrouter key'),
    (r'(?i)(api[_-]?key|app[_-]?secret|password|passwd)\s*[:=]\s*["\'][^"\'\s]{8,}["\']', 'hardcoded credential'),
    (r'[A-Za-z]:\\\\Users\\\\', 'local windows path'),
    (r'/home/[a-z]{3,}/', 'local unix path'),
]
EXTRA = [p for p in os.environ.get('PC_PRIVACY_EXTRA', '').split(',') if p.strip()]


def md5(data):
    return hashlib.md5(data).hexdigest()


def ensure_lf(data):
    return data.replace(b'\r\n', b'\n')


def scan(name, data):
    """隐私/换行检查；返回问题列表"""
    problems = []
    text = data.decode('utf-8', errors='replace')
    for pat, label in SECRET_PATTERNS:
        for m in re.finditer(pat, text):
            frag = m.group(0)
            # 允许 i18n 里形如 api_key:"API Key" 的标签
            if re.match(r'(?i)^(api[_-]?key|app[_-]?secret|password)\s*[:=]\s*"[^"]*"$', frag) and \
               not re.search(r'[A-Za-z0-9]{8,}', frag.split('"')[1] if '"' in frag else ''):
                continue
            problems.append('%s: %s -> %s' % (name, label, frag[:60]))
    for extra in EXTRA:
        if extra in text:
            problems.append('%s: 命中自定义拦截串 %s' % (name, extra[:6] + '...'))
    return problems


def tar_add_bytes(tf, name, data, mode, mtime):
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mtime = mtime
    info.mode = mode
    info.uid = info.gid = 0
    info.uname = info.gname = 'root'
    tf.addfile(info, io.BytesIO(data))


def build_data_tar_gz(problems):
    now = int(time.time())
    hashes = {}
    total = 0
    entries = collect_files()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        root = tarfile.TarInfo(name='.')
        root.type = tarfile.DIRTYPE
        root.size = 0
        root.mtime = now
        root.mode = 0o755
        root.uid = root.gid = 0
        root.uname = root.gname = 'root'
        tf.addfile(root)

        for d in collect_dirs(entries):
            if d == '.':
                continue
            di = tarfile.TarInfo(name=d)
            di.type = tarfile.DIRTYPE
            di.size = 0
            di.mtime = now
            di.mode = 0o755
            di.uid = di.gid = 0
            di.uname = di.gname = 'root'
            tf.addfile(di)

        for _, path, arc, mode in entries:
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            with open(path, 'rb') as f:
                data = f.read()
            if os.path.splitext(path)[1].lower() not in BINARY_EXT:
                data = ensure_lf(data)
                problems.extend(scan(arc, data))
            hashes[arc] = md5(data)
            total += len(data)
            tar_add_bytes(tf, arc, data, mode, now)
            print('  file %-58s %8d bytes  md5=%s  CRLF=%d'
                  % (arc, len(data), hashes[arc], data.count(b'\r\n')))
    out = buf.getvalue()
    print('  data.tar.gz: %d bytes' % len(out))
    return out, hashes, total, len(entries)


def build_control_tar_gz(installed_size):
    epoch = int(time.time())
    control = (
        'Package: %s\n'
        'Version: %s-%s\n'
        'Depends: libc, luci\n'
        'Source: feeds/packages/luci/applications/%s\n'
        'SourceName: %s\n'
        'Section: luci\n'
        'SourceDateEpoch: %d\n'
        'Maintainer: Gt841 <Gt841@users.noreply.github.com>\n'
        'Architecture: %s\n'
        'Installed-Size: %d\n'
        'Description:  LuCI app for PicoClaw 0.3.1 (Gateway/Launcher, arch-aware auto-install)\n'
    ) % (PKG_NAME, PKG_VERSION, PKG_RELEASE, PKG_NAME, PKG_NAME, epoch, PKG_ARCH, installed_size)

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        root = tarfile.TarInfo(name='.')
        root.type = tarfile.DIRTYPE
        root.size = 0
        root.mtime = epoch
        root.mode = 0o755
        root.uid = root.gid = 0
        root.uname = root.gname = 'root'
        tf.addfile(root)
        tar_add_bytes(tf, './control', control.encode(), 0o644, epoch)
        tar_add_bytes(tf, './conffiles', b'/etc/config/picoclaw\n', 0o644, epoch)
        tar_add_bytes(tf, './postinst', POSTINST.encode(), 0o755, epoch)
        tar_add_bytes(tf, './prerm', PRERM.encode(), 0o755, epoch)
    out = buf.getvalue()
    print('  control.tar.gz: %d bytes' % len(out))
    print(control)
    return out, epoch


def build_ipk():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    problems = []

    print('Building %s v%s-%s -> %s' % (PKG_NAME, PKG_VERSION, PKG_RELEASE, OUTPUT_FILE))
    print('\n[1/4] data.tar.gz')
    data_tgz, hashes, installed_size, expected_files = build_data_tar_gz(problems)
    if problems:
        print('\n[ABORT] 命中隐私/换行问题，未生成任何安装包：')
        for p in problems:
            print('  -', p)
        return False
    print('\n[2/4] control.tar.gz')
    control_tgz, epoch = build_control_tar_gz(max(1, round(installed_size / 1024)))

    print('[3/4] 组装 IPK（tar.gz 三层嵌套，非 AR）')
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        tar_add_bytes(tf, './debian-binary', b'2.0\n', 0o644, epoch)
        tar_add_bytes(tf, './control.tar.gz', control_tgz, 0o644, epoch)
        tar_add_bytes(tf, './data.tar.gz', data_tgz, 0o644, epoch)
    ipk = buf.getvalue()
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(ipk)

    magic = ipk[:2].hex()
    print('  size=%d bytes (%.1f KB)  md5=%s  magic=%s %s'
          % (len(ipk), len(ipk) / 1024, md5(ipk), magic, 'OK(gzip)' if magic == '1f8b' else 'ERROR'))

    print('\n[4/4] 回读校验')
    ok = True
    with tarfile.open(OUTPUT_FILE, 'r:gz') as tf:
        names = tf.getnames()
        print('  顶层成员:', names)
        if sorted(names) != sorted(['./debian-binary', './control.tar.gz', './data.tar.gz']):
            ok = False
            print('  [FAIL] 顶层成员不对')
        for n in names:
            content = tf.extractfile(n).read() if tf.getmember(n).isfile() else b''
            if tf.getmember(n).isfile() and len(content) != tf.getmember(n).size:
                ok = False
                print('  [FAIL] %s 长度不符' % n)
            if n == './debian-binary' and content != b'2.0\n':
                ok = False
                print('  [FAIL] debian-binary 内容不对')
            if n == './data.tar.gz':
                with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as dtf:
                    files = [m for m in dtf.getmembers() if m.isfile()]
                    print('  data 内文件 %d 个:' % len(files))
                    for m in files:
                        d = dtf.extractfile(m).read()
                        want = hashes.get(m.name)
                        status = 'OK' if want == md5(d) else 'MISMATCH'
                        if status != 'OK':
                            ok = False
                        print('    [%s] %-58s %8d bytes  mode=%o' % (status, m.name, m.size, m.mode))
                        if d.count(b'\r\n'):
                            ok = False
                            print('    [FAIL] 含 CRLF')
                    if len(files) != expected_files:
                        ok = False
                        print('  [FAIL] 文件数不符，期望 %d' % expected_files)
            if n == './control.tar.gz':
                with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as ctf:
                    print('  control 内:', [m.name for m in ctf.getmembers()])

    print('\n[隐私/换行扫描]')
    if problems:
        for p in problems:
            print('  [FAIL]', p)
        ok = False
    else:
        print('  未命中任何密钥/路径模式')

    print('\n%s  %s' % ('BUILD OK' if ok else 'BUILD FAILED', OUTPUT_FILE))
    return ok


def build_source():
    """源码包：luci / skills / scripts / istore + 顶层文档，排除 .git、构建产物"""
    prefix = '%s-%s' % (PKG_NAME, PKG_VERSION)
    include_top = ['CHANGELOG.md', 'LICENSE', 'README.md', 'README.zh.md', '.gitignore']
    include_dirs = ['apps', 'scripts', '.github', 'keys']
    skip_ext = {'.ipk', '.bak', '.log', '.pyc'}
    skip_dirs = {'__pycache__', '.git'}

    problems = []
    count = 0
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        for name in include_top:
            path = os.path.join(REPO_DIR, name)
            if not os.path.exists(path):
                continue
            with open(path, 'rb') as f:
                data = ensure_lf(f.read())
            problems.extend(scan(name, data))
            tar_add_bytes(tf, '%s/%s' % (prefix, name), data, 0o644, int(time.time()))
            count += 1
        for d in include_dirs:
            base = os.path.join(REPO_DIR, d)
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [x for x in dirnames if x not in skip_dirs]
                for fn in filenames:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in skip_ext:
                        continue
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, REPO_DIR).replace('\\', '/')
                    with open(full, 'rb') as f:
                        data = f.read()
                    if ext in TEXT_EXT or fn == 'Makefile':
                        data = ensure_lf(data)
                        problems.extend(scan(rel, data))
                    mode = 0o755 if os.stat(full).st_mode & 0o111 else 0o644
                    tar_add_bytes(tf, '%s/%s' % (prefix, rel), data, mode, int(time.time()))
                    count += 1
    if problems:
        print('\n[ABORT] 源码包命中隐私问题，未写盘：')
        for p in problems:
            print('  -', p)
        return False
    out = buf.getvalue()
    with open(SOURCE_FILE, 'wb') as f:
        f.write(out)
    print('\n源码包: %s  %d 个文件  %.1f KB  md5=%s'
          % (SOURCE_FILE, count, len(out) / 1024, md5(out)))
    if problems:
        for p in problems:
            print('  [FAIL]', p)
    else:
        print('  隐私扫描通过')
    return not problems


if __name__ == '__main__':
    ok = build_ipk()
    ok = build_source() and ok
    raise SystemExit(0 if ok else 1)
