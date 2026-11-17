#!/bin/sh
set -eu

mode=${1:-}
[ "$#" -eq 3 ] && { [ "$mode" = --plan ] || [ "$mode" = --install ]; } || {
    echo '用法：sh install-offline-system.sh --plan|--install 软件包目录 SHA256SUMS摘要'
    exit 2
}
repo=$(realpath -e -- "$2")
digest=$3
case "$repo" in *[!a-zA-Z0-9_./-]*) echo '请使用不含空格或特殊字符的本地软件包路径。'; exit 2 ;; esac
. /etc/os-release
[ "${VERSION_CODENAME:-}" = noble ] && [ "$(dpkg --print-architecture)" = amd64 ] || {
    echo '需要 Ubuntu 24.04 amd64。'
    exit 1
}
if [ "$mode" = --install ] && [ "$(id -u)" != 0 ]; then
    echo '安装模式需要管理员权限。'
    exit 1
fi
cd "$repo"
[ "$(sha256sum SHA256SUMS | cut -d ' ' -f1)" = "$digest" ] || {
    echo '软件包清单摘要不匹配。'
    exit 1
}
sha256sum --strict --quiet -c SHA256SUMS
work=$(mktemp -d /var/tmp/sjerp-offline-apt.XXXXXX)
trap 'rm -f "$work/apt.list"; if [ -d "$work/lists" ]; then find "$work/lists" -depth -delete; fi; rmdir "$work"' EXIT
chmod 0755 "$work"
mkdir "$work/lists"
printf 'deb [trusted=yes arch=amd64] file:%s ./\n' "$repo" > "$work/apt.list"
run_apt() {
    apt-get -o Dir::Etc::sourcelist="$work/apt.list" -o Dir::Etc::sourceparts=- \
        -o Dir::State::lists="$work/lists" -o APT::Get::List-Cleanup=0 \
        -o Acquire::Languages=none -o Acquire::Retries=0 "$@"
}
run_apt update
if [ "$mode" = --plan ]; then
    run_apt -s --no-install-recommends --no-remove install postgresql-17 nginx python3-venv
else
    DEBIAN_FRONTEND=noninteractive run_apt -y --no-install-recommends --no-remove install postgresql-17 nginx python3-venv
fi
