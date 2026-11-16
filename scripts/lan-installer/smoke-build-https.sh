#!/bin/sh
set -eu
umask 077
base="$HOME/sjerp-build"
release="$base/alex-stage-96276dff"
pg=/usr/lib/postgresql/17/bin
work=$(mktemp -d "$base/https-smoke.XXXXXX")
gunicorn_pid=
nginx_pid=
cleanup() {
    [ -z "$nginx_pid" ] || kill "$nginx_pid" 2>/dev/null || :
    [ -z "$gunicorn_pid" ] || kill "$gunicorn_pid" 2>/dev/null || :
    [ ! -s "$work/db/postmaster.pid" ] || "$pg/pg_ctl" -D "$work/db" -m fast -w stop >/dev/null
}
trap cleanup EXIT
"$pg/initdb" --no-locale --encoding=UTF8 --auth=trust -D "$work/db" >"$work/init.log"
"$pg/pg_ctl" -D "$work/db" -l "$work/pg.log" -o "-c listen_addresses= -k $work" -w start
export PGHOST="$work"
"$pg/createdb" sjerp_https_smoke
export DATABASE_URL=postgresql:///sjerp_https_smoke
export APP_STAGE=staging DJANGO_ALLOWED_HOSTS=localhost MEDIA_ROOT="$work/media"
export DJANGO_SECRET_KEY="$(openssl rand -hex 48)"
mkdir "$MEDIA_ROOT"
cd "$release/backend"
"$base/offline-check/bin/python" manage.py migrate --noinput >"$work/migrate.log" 2>&1 || { tail -35 "$work/migrate.log"; exit 1; }
"$base/offline-check/bin/gunicorn" --bind 127.0.0.1:18182 --workers 1 config.wsgi >"$work/gunicorn.log" 2>&1 &
gunicorn_pid=$!
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=localhost -addext subjectAltName=DNS:localhost -keyout "$work/key.pem" -out "$work/cert.pem" 2>"$work/tls.log"
mkdir "$work/client" "$work/proxy"
cat >"$work/nginx.conf" <<EOF
worker_processes 1;
pid $work/nginx.pid;
error_log $work/nginx.log;
events {}
http {
    include /etc/nginx/mime.types;
    access_log $work/access.log;
    client_body_temp_path $work/client;
    proxy_temp_path $work/proxy;
    server {
        listen 127.0.0.1:18443 ssl;
        server_name localhost;
        ssl_certificate $work/cert.pem;
        ssl_certificate_key $work/key.pem;
        root $release/frontend/dist;
        location ^~ /media/ { return 404; }
        location /api/ {
            proxy_pass http://127.0.0.1:18182;
            proxy_set_header Host localhost;
            proxy_set_header X-Forwarded-Proto https;
        }
        location / { try_files \$uri \$uri/ /index.html; }
    }
}
EOF
for dir in fastcgi uwsgi scgi; do
    mkdir "$work/$dir"
    sed -i "/access_log/a\    ${dir}_temp_path $work/$dir;" "$work/nginx.conf"
done
/usr/sbin/nginx -t -p "$work" -c "$work/nginx.conf"
/usr/sbin/nginx -p "$work" -c "$work/nginx.conf" -g 'daemon off;' &
nginx_pid=$!
request() {
    curl -fsS --retry 6 --retry-delay 1 --retry-connrefused --max-time 5 --cacert "$work/cert.pem" "https://localhost:18443$1"
}
request / >"$work/index.html"
asset=$(sed -n 's/.*src="\([^"]*\.js\)".*/\1/p' "$work/index.html" | head -1)
test -n "$asset"
request "$asset" >"$work/main.js"
test -s "$work/main.js"
request /api/session/csrf/ >"$work/csrf.json"
test -s "$work/csrf.json"
code=$(curl -sS --cacert "$work/cert.pem" -o /dev/null -w '%{http_code}' https://localhost:18443/media/private.txt)
test "$code" = 404
printf 'HTTPS 首页、JS、CSRF 接口及私有媒体拒绝通过。日志：%s\n' "$work"
