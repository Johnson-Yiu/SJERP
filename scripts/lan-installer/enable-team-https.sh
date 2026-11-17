#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ] || exit 1
base=/var/lib/sjerp-team-tls
root="$base/sjerp-alex-ca.pem"
leaf="$base/sjerp-alex-server.pem"
config=/etc/nginx/conf.d/sjerp-a.conf
key=/etc/sjerp/a/lan-https.key
new=/etc/sjerp/a/team-https.crt
status=/etc/issue.d/96-sjerp-team-tls.issue
report() { printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"; }
rollback=$(mktemp)
changed=false
cleanup() {
    rc=$?
    if [ "$rc" -ne 0 ]; then
        if [ "$changed" = true ]; then
            install -m 0644 "$rollback" "$config"
            nginx -t && systemctl reload nginx || :
        fi
        if [ "$rc" -ne 60 ]; then report "SJERP TEAM TLS FAILED (exit $rc)"; fi
    fi
    rm -f "$rollback"
}
trap cleanup EXIT
openssl verify -CAfile "$root" -purpose sslserver -verify_ip 192.168.1.36 "$leaf"
test "$(openssl x509 -pubkey -noout -in "$leaf")" = "$(openssl pkey -pubout -in "$key")"
grep -Fq 'ssl_certificate /etc/sjerp/a/lan-https.crt;' "$config"
grep -Fq 'ssl_certificate_key /etc/sjerp/a/lan-https.key;' "$config"
cp "$config" "$rollback"
install -m 0644 "$leaf" "$new"
changed=true
sed -i 's|ssl_certificate /etc/sjerp/a/lan-https.crt;|ssl_certificate /etc/sjerp/a/team-https.crt;|' "$config"
nginx -t
systemctl reload nginx
# A successful reload request can return before replacement workers start.
# Recheck the full certificate chain on each attempt, including TLS failures.
ready=false
for attempt in $(seq 1 20); do
    if diagnostic=$(curl --noproxy '*' -fsS --connect-timeout 2 --max-time 4 --cacert "$root" \
        --connect-to 192.168.1.36:443:127.0.0.1:18443 \
        https://192.168.1.36/api/session/csrf/ 2>&1); then
        ready=true
        break
    fi
    sleep 1
done
if [ "$ready" != true ]; then
    printf 'Team TLS probe failed: %s\n' "$diagnostic" >&2
    report "SJERP TEAM TLS FAILED: $diagnostic"
    exit 60
fi
install -m 0644 "$root" /etc/sjerp-a-test-ca.crt
report 'SJERP TEAM TLS READY'
