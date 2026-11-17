#!/bin/sh
set -eu
umask 077
status=/etc/issue.d/90-sjerp-offline.issue
install -d -m 0755 /etc/issue.d
printf '%s\n' 'SJERP offline provisioning in progress' > "$status"
work=$(mktemp -d /var/tmp/sjerp-firstboot.XXXXXX)
mkdir "$work/seed"
cleanup() {
    rc=$?
    if [ "$rc" -ne 0 ]; then
        printf '%s\n' "SJERP OFFLINE FAILED (exit $rc; see cloud-init-output.log)" > "$status"
        cat "$status" > /dev/console 2>/dev/null || :
    fi
    cd /
    if mountpoint -q "$work/seed"; then umount "$work/seed"; fi
}
trap cleanup EXIT
mount -o ro,nosuid,nodev,noexec /dev/disk/by-label/CIDATA "$work/seed"
cd "$work/seed"
printf '%s  %s\n' "$1" system.tar "$2" erp.zip "$3" install.sh "$4" stage.py | sha256sum --strict -c -
tar -xf system.tar -C "$work"
# APT's _apt account needs read/traverse access to the verified package repository.
chmod 0755 "$work"
if [ -n "$(dpkg --audit)" ]; then
    DEBIAN_FRONTEND=noninteractive dpkg --configure -a
fi
sh install.sh --install "$work/offline-system-96276dff" "$5"
install -d -m 0700 /srv/sjerp/versions
version=/srv/sjerp/versions/96276dffa07c11fb60720a439269df8c36031f7a
if [ ! -f "$version/READY" ]; then
    if [ -e "$version" ]; then
        [ ! -L "$version" ] || exit 1
        mv -T -- "$version" "$version.interrupted.$(date +%s)"
    fi
    python3 stage.py erp.zip "$2" /srv/sjerp/versions
fi
test "$(cat "$version/READY")" = "$2"
printf '%s\n' 'SJERP OFFLINE READY: OS packages and ERP version staged' > "$status"
cat "$status" > /dev/console 2>/dev/null || :
