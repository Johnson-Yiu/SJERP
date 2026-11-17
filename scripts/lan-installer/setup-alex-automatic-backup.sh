#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ]
state=/var/lib/sjerp-automatic-backup
source=/usr/local/share/sjerp-backup-seed
version=/srv/sjerp/current
pg=/etc/postgresql/17/main
unit=/etc/systemd/system
app_dropin="$unit/sjerp-local@a.service.d/20-sjerp-backup-recovery.conf"
worker=/usr/local/sbin/sjerp-automatic-backup
transport=/usr/local/sbin/sjerp-backup-transport
status=/etc/issue.d/98-sjerp-automatic-backup.issue
report() { printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"; }
report 'SJERP AUTOMATIC BACKUP SETUP IN PROGRESS'
systemctl is-active --quiet sjerp-local@a.service
[ "$(readlink -f "$version")" = "/srv/sjerp/versions/$(cat "$source/release-sha")" ]
ip -4 -o addr show dev eth1 | grep -Fq '10.253.247.2/30'
[ ! -e "$state" ] && [ ! -e "$app_dropin" ] && [ ! -e "$worker" ]
! getent passwd sjerpbackup >/dev/null
grep -Eq '^ssh-ed25519 [A-Za-z0-9+/]{68} sjerp-backup$' "$source/collector.pub"
git --version >/dev/null
openssl pkey -pubin -in "$source/recovery-public.pem" -pubcheck -noout
runuser -u postgres -- psql -Xd postgres -v ON_ERROR_STOP=1 -Atc 'SELECT system_identifier FROM pg_control_system()' > "$source/cluster"
grep -Eq '^[0-9]{10,32}$' "$source/cluster"

install -d -m 0700 "$state" "$state/checkout"
install -m 0600 "$source/cluster" "$state/source-cluster"
install -m 0600 "$source/recovery-public.pem" "$state/recovery-public.pem"
git -C "$state/checkout" init -q
git -C "$state/checkout" index-pack --stdin < "$source/maintenance.pack"
cat "$source/release-sha" > "$state/checkout/.git/shallow"
git -C "$state/checkout" sparse-checkout set --no-cone /backend/ /templates/ /.gitignore
git -C "$state/checkout" update-ref HEAD "$(cat "$source/release-sha")"
git -C "$state/checkout" read-tree -mu HEAD
test -z "$(git -C "$state/checkout" status --porcelain --untracked-files=all -- backend templates)"
install -m 0700 "$source/worker.py" "$worker"

# Extend peer access to root for this local database only. Keep postgres as
# the unfenced login so normal, interrupted and boot recovery use peer auth.
cp -p "$pg/pg_hba.conf" "$state/original-pg_hba.conf"
cp -p "$pg/pg_ident.conf" "$state/original-pg_ident.conf"
pg_changed=false
cleanup() {
    rc=$?
    if [ "$rc" -ne 0 ]; then
        if [ "$pg_changed" = true ]; then
            cp -p "$state/original-pg_hba.conf" "$pg/pg_hba.conf"
            cp -p "$state/original-pg_ident.conf" "$pg/pg_ident.conf"
            systemctl reload postgresql@17-main.service
        fi
        report "SJERP AUTOMATIC BACKUP SETUP FAILED (exit $rc)"
    fi
}
trap cleanup EXIT
pg_changed=true
{ printf 'local sjerp_a postgres peer map=sjerp_backup\n'; cat "$state/original-pg_hba.conf"; } > "$pg/pg_hba.conf"
printf '\nsjerp_backup root postgres\nsjerp_backup postgres postgres\n' >> "$pg/pg_ident.conf"
systemctl reload postgresql@17-main.service
for attempt in $(seq 1 10); do
    if psql -h /var/run/postgresql -U postgres -Xd sjerp_a -w -Atc 'SELECT system_identifier FROM pg_control_system()'         | cmp -s - "$state/source-cluster"; then break; fi
    sleep 1
done
psql -h /var/run/postgresql -U postgres -Xd sjerp_a -w -Atc 'SELECT system_identifier FROM pg_control_system()'     | cmp -s - "$state/source-cluster"

cat > "$unit/sjerp-automatic-backup.service" <<'UNIT'
[Unit]
Description=SJERP encrypted database and attachment backup
Requires=postgresql@17-main.service
After=postgresql@17-main.service
RequiresMountsFor=/var/lib/sjerp/a/private-media

[Service]
Type=oneshot
TimeoutStartSec=30min
TimeoutStopSec=180
UMask=0077
ExecStart=/usr/bin/python3 /usr/local/sbin/sjerp-automatic-backup backup
ExecStopPost=/usr/bin/python3 /usr/local/sbin/sjerp-automatic-backup recover-online
UNIT
cat > "$unit/sjerp-automatic-backup-recover.service" <<'UNIT'
[Unit]
Description=Recover SJERP backup maintenance state after boot
Requires=postgresql@17-main.service
After=postgresql@17-main.service
RequiresMountsFor=/var/lib/sjerp/a/private-media

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 /usr/local/sbin/sjerp-automatic-backup recover-boot
UNIT
install -d -m 0755 "$(dirname "$app_dropin")"
cat > "$app_dropin" <<'UNIT'
[Unit]
Requires=sjerp-automatic-backup-recover.service
After=sjerp-automatic-backup-recover.service
UNIT
systemctl daemon-reload
systemctl start sjerp-automatic-backup-recover.service

useradd --system --user-group --home-dir /var/lib/sjerp-backup-collector --shell /bin/sh sjerpbackup
install -d -m 0755 /var/lib/sjerp-backup-collector
install -d -m 0755 /var/lib/sjerp-backup-collector/.ssh
printf 'from="10.253.247.1",restrict,command="/usr/bin/sudo -n /usr/local/sbin/sjerp-backup-transport" %s\n'     "$(cat "$source/collector.pub")" > /var/lib/sjerp-backup-collector/.ssh/authorized_keys
chmod 0644 /var/lib/sjerp-backup-collector/.ssh/authorized_keys
sudofile="$state/sudoers"
printf '%s\n' 'sjerpbackup ALL=(root) NOPASSWD: /usr/local/sbin/sjerp-backup-transport ""' > "$sudofile"
visudo -cf "$sudofile"
cat > "$transport" <<'SH'
#!/bin/sh
set -eu
state=/var/lib/sjerp-automatic-backup
exec 9>"$state/collect.lock"
flock -n 9
systemctl start sjerp-automatic-backup.service >&2
exec cat "$state/latest.zip"
SH
chmod 0700 "$transport"
install -m 0440 "$sudofile" /etc/sudoers.d/sjerp-backup-collector
report 'SJERP AUTOMATIC BACKUP SETUP READY'
