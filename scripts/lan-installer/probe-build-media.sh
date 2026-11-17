#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo '请从临时构建机控制台使用 sudo 运行。'; exit 1; }
[ "$(hostname -s)" = sunjackerp ] || { echo '仅允许在临时构建机运行。'; exit 1; }

work=$(mktemp -d /var/tmp/sjerp-media-probe.XXXXXX)
cleanup() {
    if mountpoint -q "$work/media"; then
        umount "$work/media" || return
    fi
    rm -f "$work/media.ext4"
    rmdir "$work/media" "$work"
}
trap cleanup EXIT
mkdir "$work/media"
truncate -s 64M "$work/media.ext4"
mkfs.ext4 -q -F "$work/media.ext4"
mount -o loop,nodev,nosuid,noexec "$work/media.ext4" "$work/media"
printf '%s\n' 'synthetic media probe' > "$work/media/probe.txt"
mount -o remount,ro "$work/media"
findmnt --mountpoint "$work/media" --noheadings --output FSTYPE,OPTIONS
test "$(cat "$work/media/probe.txt")" = 'synthetic media probe'
if touch "$work/media/must-not-write" 2>/dev/null; then
    echo '只读媒体写入检查失败。'
    exit 1
fi
echo '独立 ext4 媒体卷可读，且只读期间拒绝写入。'
