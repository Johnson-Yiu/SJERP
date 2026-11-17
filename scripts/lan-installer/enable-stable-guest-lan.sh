#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ] || exit 1
status=/etc/issue.d/95-sjerp-stable-lan.issue
report() { printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"; }
trap 'rc=$?; if [ "$rc" -ne 0 ]; then report "SJERP STABLE LAN FAILED (exit $rc)"; fi' EXIT
report 'SJERP stable LAN configuration in progress'
test "$(readlink /srv/sjerp/current)" = /srv/sjerp/versions/3b156502472478f47ae015ae51d3ac92c1edc42a
ip -br link | grep -qi '02:53:4a:45:52:01'
cat > /etc/netplan/91-sjerp-service.yaml <<'EOF'
network:
  version: 2
  ethernets:
    sjerp-service:
      match:
        macaddress: "02:53:4a:45:52:01"
      dhcp4: false
      dhcp6: false
      addresses: [10.253.247.2/30]
      optional: true
EOF
chmod 0600 /etc/netplan/91-sjerp-service.yaml
netplan generate
netplan apply
ip -4 -o addr show | grep -F '10.253.247.2/30'
nginx=/etc/nginx/conf.d/sjerp-a.conf
grep -Fq 'listen 0.0.0.0:18443 ssl;' "$nginx"
sed -i 's/proxy_set_header Host \$host;/proxy_set_header Host $http_host;/' "$nginx"
grep -Fq 'proxy_set_header Host $http_host;' "$nginx"
nginx -t
systemctl reload nginx
curl -fsS --max-time 10 --cacert /etc/sjerp-a-test-ca.crt \
    --connect-to 192.168.1.36:443:10.253.247.2:18443 \
    https://192.168.1.36/api/session/csrf/ >/dev/null
report 'SJERP STABLE LAN READY: 10.253.247.2/30'
