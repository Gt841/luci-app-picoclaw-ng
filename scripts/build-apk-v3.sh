#!/bin/sh
# ============================================
#  luci-app-picoclaw-ng — APK (v3/ADB) Builder
#  适用于 OpenWrt 25.x（apk-tools 3.x 系统）
# ============================================
#
#  用法（把本脚本和仓库放到路由器上，在仓库根目录执行）：
#      sh scripts/build-apk-v3.sh
#
#  可选环境变量：
#      PC_VERSION=3.0.2-r1     包版本
#      PC_SIGN_KEY=/path/key.rsa
#                              用该私钥签名；同目录需有 key.rsa.pub
#      PC_ALLOW_UNTRUSTED=1    额外输出未签名安装提示
#
#  产物：
#      luci-app-picoclaw-ng-<version>.apk
#
#  说明：
#    * OpenWrt 25.x 用 apk-tools 3.x，包格式是 v3(ADB)，本脚本走官方 `apk mkpkg`
#    * 25.x 之前的系统（opkg）请用 ipk，格式不同不能用这个脚本
#    * 包体未签名，安装时需要 --allow-untrusted

set -e

# 自检：脚本自身必须是 LF。Windows 上 core.autocrlf=true 会把换行转成 CRLF，
# 那样 sh 会把 `\r` 当命令的一部分，直接失败。这里提前拦下并给出修法。
if ! tr -d '\r' < "$0" | cmp -s - "$0"; then
    echo "错误：$0 含 CRLF 换行，BusyBox ash 无法执行。" >&2
    echo "      请先转换：dos2unix $0   （或在 git 里设置 core.autocrlf=false）" >&2
    exit 1
fi

PKG_NAME="luci-app-picoclaw-ng"
PC_VERSION="${PC_VERSION:-3.0.2-r1}"
SIGN_KEY="${PC_SIGN_KEY:-}"
PKG_MAINTAINER="Gt841 <Gt841@users.noreply.github.com>"
PKG_URL="https://github.com/Gt841/luci-app-picoclaw-ng"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="/tmp/${PKG_NAME}-apk-build"
OUT_DIR="$REPO_DIR/dist"

echo "=== luci-app-picoclaw APK (v3) 构建 ==="
echo "仓库:   $REPO_DIR"
echo "版本:   $PC_VERSION"
echo ""

# ---------- 0. 环境检查 ----------
command -v apk >/dev/null 2>&1 || {
    echo "错误：找不到 apk 命令。本脚本只适用于 OpenWrt 25.x（apk-tools 3.x）系统。" >&2
    echo "      25.x 以前的系统用 opkg，请改用 ipk 包。" >&2
    exit 1
}
[ "$(id -u)" = "0" ] || {
    echo "错误：必须用 root 运行（否则包内文件 owner 会写错）。" >&2
    exit 1
}

# 签名是可选步骤：私钥和公钥由用户自行保管，不放进仓库。
# apk 只认 <keyname>.rsa.pub，签名块里记录的 keyname 取自私钥文件名去掉 .rsa。
if [ -n "$SIGN_KEY" ]; then
    [ -f "$SIGN_KEY" ] || {
        echo "错误：找不到签名私钥：$SIGN_KEY" >&2
        exit 1
    }
    SIGN_PUB="${SIGN_KEY}.pub"
    [ -f "$SIGN_PUB" ] || {
        echo "错误：找不到公钥：$SIGN_PUB" >&2
        echo "      请先生成：openssl rsa -in \"$SIGN_KEY\" -pubout -out \"$SIGN_PUB\"" >&2
        exit 1
    }
    echo "签名私钥: $SIGN_KEY"
    echo "签名公钥: $SIGN_PUB"
    echo ""
fi

# ---------- 1. 准备构建根 ----------
echo "=== [1/4] 准备构建根 ==="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/root"

# 包源码按 OpenWrt / iStoreOS 约定存放：apps/<id>/<package>/
#   luasrc/ -> /usr/lib/lua/luci
#   root/   -> /
# 用 tar 管道复制，兼容 BusyBox 与 macOS，并保留目录结构。
PKG_DIR="$REPO_DIR/apps/picoclaw/luci-app-picoclaw-ng"
if [ ! -d "$PKG_DIR/luasrc" ] || [ ! -d "$PKG_DIR/root" ]; then
    echo "错误：找不到包源码目录 $PKG_DIR/{luasrc,root}" >&2
    exit 1
fi

mkdir -p "$BUILD_DIR/root/usr/lib/lua/luci"
(cd "$PKG_DIR/luasrc" && tar cf - .) | (cd "$BUILD_DIR/root/usr/lib/lua/luci" && tar xf -)
(cd "$PKG_DIR/root" && tar cf - .) | (cd "$BUILD_DIR/root" && tar xf -)

# 统一转成 LF：LuCI 的 lua/htm 解析器只吃 LF，CRLF 会报 unfinished string
find "$BUILD_DIR/root" -type f | while read -r f; do
    case "$f" in
        *.lua|*.htm|*.json|*.md|*.init|*.sh)
            tr -d '\r' < "$f" > "$f.lf" && mv "$f.lf" "$f" ;;
    esac
done

# 可执行位不依赖 git 记录，显式设置
chmod 755 "$BUILD_DIR/root/etc/init.d/picoclaw" \
          "$BUILD_DIR/root/etc/init.d/picoclaw-installer" \
          "$BUILD_DIR/root/usr/lib/picoclaw-install.sh"

find "$BUILD_DIR/root" -type f | sed "s|$BUILD_DIR/root|  |" | sort

# ---------- 2. 隐私与换行扫描 ----------
echo ""
echo "=== [2/4] 隐私与换行扫描 ==="
PROBLEMS=""

scan_file() {
    f="$1"
    # CRLF
    if tr -d '\r' < "$f" | cmp -s - "$f"; then
        :
    else
        PROBLEMS="$PROBLEMS\n  $f: 含 CRLF 换行"
    fi
    # 常见密钥形态
    if grep -qE 'sk-[A-Za-z0-9_-]{20,}' "$f" 2>/dev/null; then
        PROBLEMS="$PROBLEMS\n  $f: 疑似 api key (sk-...)"
    fi
    if grep -qE 'sk-or-v1-[A-Za-z0-9]{20,}' "$f" 2>/dev/null; then
        PROBLEMS="$PROBLEMS\n  $f: 疑似 openrouter key"
    fi
    # 硬编码凭据：api_key = "至少8位"
    if grep -qiE '(api[_-]?key|app[_-]?secret|password|passwd)[[:space:]]*[:=][[:space:]]*"[A-Za-z0-9]{8,}"' "$f" 2>/dev/null; then
        PROBLEMS="$PROBLEMS\n  $f: 疑似硬编码凭据"
    fi
    # 本机路径
    if grep -qE '[A-Za-z]:\\Users\\|/home/[a-z]{3,}/' "$f" 2>/dev/null; then
        PROBLEMS="$PROBLEMS\n  $f: 含本机路径"
    fi
}

for f in $(find "$BUILD_DIR/root" -type f); do
    scan_file "$f"
done

# 自定义拦截串（逗号分隔），用于排除掉你自己知道不该进包的东西
if [ -n "$PC_PRIVACY_EXTRA" ]; then
    OLDIFS="$IFS"
    IFS=','
    for pat in $PC_PRIVACY_EXTRA; do
        [ -z "$pat" ] && continue
        if grep -rqF "$pat" "$BUILD_DIR/root" 2>/dev/null; then
            PROBLEMS="$PROBLEMS\n  命中自定义拦截串: ${pat}"
        fi
    done
    IFS="$OLDIFS"
fi

if [ -n "$PROBLEMS" ]; then
    echo "扫描发现问题，未生成任何包："
    echo -e "$PROBLEMS"
    exit 1
fi
echo "  扫描通过：无密钥、无 CRLF、无本机路径"

# ---------- 3. 生成 post-install ----------
cat > "$BUILD_DIR/post-install" <<'EOF'
#!/bin/sh
# 清理 LuCI 编译缓存，让新页面立即生效
rm -f /tmp/luci-indexcache* 2>/dev/null
rm -rf /tmp/luci-modulecache/* 2>/dev/null
exit 0
EOF
chmod 755 "$BUILD_DIR/post-install"

# ---------- 4. 打包 ----------
echo ""
echo "=== [3/4] apk mkpkg ==="
mkdir -p "$OUT_DIR"
OUT_APK="$OUT_DIR/${PKG_NAME}-${PC_VERSION}.apk"
rm -f "$OUT_APK"

# 注意：
#   * depends 用空格分隔一次给全（多次 -I depends: 是覆盖不是追加）
#   * 必须在 root 下跑，owner 才会是 root
#   * 签名必须在 mkpkg 阶段完成：apk-tools 3.0.x 的 adbsign 会把 v3 包截断，
#     不要用它给已经构建好的包补签名
set -- apk mkpkg -F "$BUILD_DIR/root" \
    -I "name:${PKG_NAME}" \
    -I "version:${PC_VERSION}" \
    -I "description:LuCI app for PicoClaw 0.3.1 (Gateway/Launcher, arch-aware auto-install)" \
    -I "arch:noarch" \
    -I "license:MIT" \
    -I "origin:${PKG_NAME}" \
    -I "maintainer:${PKG_MAINTAINER}" \
    -I "url:${PKG_URL}" \
    -I "depends:luci" \
    -s "post-install:$BUILD_DIR/post-install"
if [ -n "$SIGN_KEY" ]; then
    set -- "$@" --sign-key "$SIGN_KEY"
fi
set -- "$@" -o "$OUT_APK"
"$@"

echo ""
echo "=== [4/4] 校验 ==="
[ -f "$OUT_APK" ] || { echo "错误：没有生成包" >&2; exit 1; }
ls -la "$OUT_APK"
md5sum "$OUT_APK"

echo ""
echo "包信息："
apk adbdump "$OUT_APK" 2>/dev/null | sed -n '1,14p'

if [ -n "$SIGN_KEY" ]; then
    echo ""
    echo "签名校验："
    apk verify --keys-dir "$(dirname "$SIGN_PUB")" "$OUT_APK"
fi

echo ""
echo "=== 完成 ==="
echo "产物: $OUT_APK"
echo ""
if [ -n "$SIGN_KEY" ]; then
    echo "安装（OpenWrt 25.x，apk 系统）："
    echo "  1. 把公钥放进路由器信任目录（只需一次）："
    echo "     scp $(basename "$SIGN_PUB") root@<路由器IP>:/etc/apk/keys/"
    echo "  2. 安装："
    echo "     scp $OUT_APK root@<路由器IP>:/tmp/"
    echo "     ssh root@<路由器IP> 'apk add /tmp/${PKG_NAME}-${PC_VERSION}.apk'"
    echo ""
    echo "私钥不要提交到仓库，也不要泄露；更换密钥后路由器需要重新导入新公钥。"
else
    echo "安装（OpenWrt 25.x，apk 系统）："
    echo "  scp $OUT_APK root@<路由器IP>:/tmp/"
    echo "  ssh root@<路由器IP> 'apk add --allow-untrusted /tmp/${PKG_NAME}-${PC_VERSION}.apk'"
    echo ""
    echo "本包未签名（没有发布密钥），所以必须带 --allow-untrusted。"
fi
