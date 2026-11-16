#!/bin/sh
set -eu

[ "$(id -u)" = 0 ] || { echo '请在构建机控制台通过 sudo 执行。'; exit 1; }
[ "$(hostname -s)" = sunjackerp ] || { echo '目标主机名与临时构建机不符。'; exit 1; }
. /etc/os-release
[ "${VERSION_CODENAME:-}" = noble ] && [ "$(dpkg --print-architecture)" = amd64 ] || {
    echo '需要 Ubuntu 24.04 amd64 构建机。'
    exit 1
}

key_dir=/usr/share/postgresql-common/pgdg
key="$key_dir/apt.postgresql.org.asc"
source=/etc/apt/sources.list.d/sjerp-build-pgdg.sources
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o "$tmp"
fingerprint=$(gpg --batch --show-keys --with-colons "$tmp" | awk -F: '$1 == "fpr" && !seen++ {print $10}')
[ "$fingerprint" = B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 ] || {
    echo 'PostgreSQL 软件源签名密钥指纹不符。'
    exit 1
}
if [ -e "$key" ]; then
    cmp -s "$tmp" "$key" || { echo '已有 PostgreSQL 软件源密钥不同。'; exit 1; }
else
    install -d -m 0755 "$key_dir"
    install -m 0644 "$tmp" "$key"
fi
cat > "$tmp" <<EOF
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: noble-pgdg
Architectures: amd64
Components: main
Signed-By: $key
EOF
if [ -e "$source" ]; then
    cmp -s "$tmp" "$source" || { echo '已有构建软件源配置不同。'; exit 1; }
else
    install -m 0644 "$tmp" "$source"
fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql-17 nginx
/usr/lib/postgresql/17/bin/postgres --version
nginx -v
