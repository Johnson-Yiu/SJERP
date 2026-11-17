#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ] || exit 1

base=/var/lib/sjerp-team-tls
root="$base/sjerp-alex-ca.pem"
leaf="$base/sjerp-alex-server.pem"
config=/etc/nginx/conf.d/sjerp-a.conf
key=/etc/sjerp/a/lan-https.key
current=/etc/sjerp/a/team-https.crt
health_ca=/etc/sjerp-a-test-ca.crt
status=/etc/issue.d/96-sjerp-team-tls.issue
ip=192.168.1.36
endpoint=127.0.0.1:18443
report() { printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"; }

work=$(mktemp -d /etc/sjerp/a/.team-tls.XXXXXX)
updated=false
ca_updated=false
cleanup() {
    rc=$?
    if [ "$rc" -ne 0 ]; then
        rollback_ok=true
        if [ "$ca_updated" = true ]; then
            install -m 0644 "$work/previous-ca" "$health_ca" || rollback_ok=false
        fi
        if [ "$updated" = true ]; then
            mv -f "$work/previous-leaf" "$current" || rollback_ok=false
            if ! nginx -t || ! systemctl reload nginx; then rollback_ok=false; fi
        fi
        if [ "$rollback_ok" = true ]; then
            report "SJERP TEAM TLS AKI FAILED (exit $rc)"
        else
            report "SJERP TEAM TLS AKI FAILED (exit $rc; rollback needs attention)"
            printf 'Previous certificate files retained in %s\n' "$work" >&2
            return
        fi
    fi
    rm -f "$work/candidate" "$work/previous-leaf" "$work/previous-ca" "$work/peer"
    rmdir "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
report 'SJERP TEAM TLS AKI IN PROGRESS'

grep -Fq "ssl_certificate $current;" "$config"
grep -Fq "ssl_certificate_key $key;" "$config"
openssl verify -x509_strict -CAfile "$root" -purpose sslserver -verify_ip "$ip" "$leaf"
test "$(openssl x509 -pubkey -noout -in "$leaf")" = "$(openssl pkey -pubout -in "$key")"
expected=$(openssl x509 -fingerprint -sha256 -noout -in "$leaf")
cp -p "$current" "$work/previous-leaf"
cp -p "$health_ca" "$work/previous-ca"
install -m 0644 "$leaf" "$work/candidate"
mv -f "$work/candidate" "$current"
updated=true
nginx -t
systemctl reload nginx

ready=false
for attempt in $(seq 1 20); do
    if timeout 5 openssl s_client -connect "$endpoint" -CAfile "$root" -verify_ip "$ip" \
        -verify_return_error -x509_strict </dev/null >"$work/peer" 2>&1 &&
        actual=$(openssl x509 -fingerprint -sha256 -noout -in "$work/peer") &&
        [ "$actual" = "$expected" ] &&
        curl --noproxy '*' -fsS --connect-timeout 2 --max-time 4 --cacert "$root" \
            --connect-to "$ip:443:$endpoint" "https://$ip/api/session/csrf/" -o /dev/null; then
        ready=true
        break
    fi
    sleep 1
done
[ "$ready" = true ]
ca_updated=true
install -m 0644 "$root" "$health_ca"
report 'SJERP TEAM TLS AKI READY'
