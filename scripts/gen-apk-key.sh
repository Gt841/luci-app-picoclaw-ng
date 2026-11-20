#!/bin/sh
# ============================================
#  luci-app-picoclaw-ng — APK signing key helper
#  生成 RSA 私钥 + 公钥，私钥默认放在仓库外
# ============================================
#
#  用法：
#      sh scripts/gen-apk-key.sh
#      KEY_DIR=/path/to/keys KEY_NAME=my-key sh scripts/gen-apk-key.sh
#
#  产物：
#      <KEY_DIR>/<KEY_NAME>.rsa      私钥，权限 0600，不要提交/泄露
#      <KEY_DIR>/<KEY_NAME>.rsa.pub  公钥，安装到路由器 /etc/apk/keys/
#
#  生成后签名构建：
#      PC_SIGN_KEY=<KEY_DIR>/<KEY_NAME>.rsa sh scripts/build-apk-v3.sh

set -e

KEY_NAME="${KEY_NAME:-luci-app-picoclaw-ng}"
KEY_DIR="${KEY_DIR:-$HOME/.config/luci-app-picoclaw-ng/apk-keys}"
PRIV="$KEY_DIR/${KEY_NAME}.rsa"
PUB="${PRIV}.pub"

command -v openssl >/dev/null 2>&1 || {
    echo "错误：找不到 openssl，请先安装 OpenSSL。" >&2
    exit 1
}

if [ -e "$PRIV" ]; then
    echo "错误：私钥已存在：$PRIV" >&2
    echo "      为避免覆盖正在使用的签名密钥，本脚本不会自动重建。" >&2
    echo "      确实要重建请先手动备份并删除它。" >&2
    exit 1
fi

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

echo "生成 RSA 4096 私钥: $PRIV"
(umask 077; openssl genrsa -out "$PRIV" 4096 2>/dev/null)

echo "导出公钥: $PUB"
openssl rsa -in "$PRIV" -pubout -out "$PUB" 2>/dev/null

chmod 600 "$PRIV"
chmod 644 "$PUB"

echo ""
echo "完成。"
echo "  私钥（务必离线备份，不要提交）：$PRIV"
echo "  公钥（发到路由器信任目录）：     $PUB"
echo ""
echo "签名构建："
echo "  PC_SIGN_KEY=\"$PRIV\" sh scripts/build-apk-v3.sh"
echo ""
echo "路由器信任公钥（只需一次）："
echo "  scp \"$PUB\" root@<路由器IP>:/etc/apk/keys/"
