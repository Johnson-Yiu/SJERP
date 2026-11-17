#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ] || exit 1
status=/etc/issue.d/93-sjerp-lan.issue
report() {
    printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"
}
trap 'rc=$?; if [ "$rc" -ne 0 ]; then report "SJERP LAN FAILED (exit $rc)"; fi' EXIT
report 'SJERP LAN configuration in progress'
systemctl is-active --quiet sjerp-local@a.service
test "$(readlink /srv/sjerp/current)" = /srv/sjerp/versions/96276dffa07c11fb60720a439269df8c36031f7a
host=192.168.1.36
port=18443
config=/etc/sjerp/a
nginx=/etc/nginx/conf.d/sjerp-a.conf
grep -q '^DJANGO_ALLOWED_HOSTS=localhost$' "$config/runtime.env"
grep -q 'listen 127.0.0.1:18443 ssl;' "$nginx"
address=$(ip -4 -o addr show scope global dev eth0 | awk 'NR == 1 {split($4, a, "/"); print a[1]}')
test -n "$address"
openssl req -x509 -newkey rsa:2048 -nodes -days 14 -subj "/CN=$host" \
    -addext "subjectAltName=IP:$host,DNS:localhost" \
    -keyout "$config/lan-https.key" -out "$config/lan-https.crt"
install -m 0644 "$config/lan-https.crt" /etc/sjerp-a-test-ca.crt
sed -i "s/^DJANGO_ALLOWED_HOSTS=localhost$/DJANGO_ALLOWED_HOSTS=localhost,$host/" "$config/runtime.env"
sed -i -e "s/listen 127.0.0.1:18443 ssl;/listen 127.0.0.1:$port ssl;\n    listen $address:$port ssl;/" \
    -e "s/server_name localhost;/server_name localhost $host;/" \
    -e 's/proxy_set_header Host \$host;/proxy_set_header Host $http_host;/' \
    -e 's|/https.crt;|/lan-https.crt;|' -e 's|/https.key;|/lan-https.key;|' "$nginx"
nginx -t
systemctl restart sjerp-local@a.service
systemctl reload nginx
curl -fsS --cacert /etc/sjerp-a-test-ca.crt --connect-to "$host:$port:$address:$port" "https://$host:$port/api/session/csrf/" >/dev/null
report "SJERP LAN GUEST READY: IPv4=$address HTTPS=$port"
