#!/bin/sh
set -eu
umask 077
base="$HOME/sjerp-build"
pg=/usr/lib/postgresql/17/bin
work=$(mktemp -d "$base/runtime-role.XXXXXX")
unit_name="sjerp-build-smoke-${work##*.}.service"
unit=
cleanup() {
    if [ -n "$unit" ]; then
        systemctl --user stop "$unit_name" >/dev/null 2>&1 || :
        rm -f -- "$unit" "$work/runtime.env"
        systemctl --user daemon-reload
    fi
    if [ -s "$work/db/postmaster.pid" ]; then
        "$pg/pg_ctl" -D "$work/db" -m fast -w stop >/dev/null
    fi
}
trap cleanup EXIT
port=18219
"$pg/initdb" --no-locale --encoding=UTF8 --auth-local=trust --auth-host=scram-sha-256 -D "$work/db" >"$work/init.log"
"$pg/pg_ctl" -D "$work/db" -l "$work/pg.log" -o "-h 127.0.0.1 -p $port -k $work" -w start
export PGHOST="$work" PGPORT="$port"
maintenance_password=$(openssl rand -hex 32)
runtime_password=$(openssl rand -hex 32)
"$pg/psql" -X -v ON_ERROR_STOP=1 -d postgres <<EOF
CREATE ROLE sjerp_smoke_migrate LOGIN PASSWORD '$maintenance_password';
CREATE ROLE sjerp_smoke_runtime LOGIN PASSWORD '$runtime_password';
CREATE DATABASE sjerp_role_smoke OWNER sjerp_smoke_migrate;
REVOKE ALL ON DATABASE sjerp_role_smoke FROM PUBLIC;
GRANT CONNECT ON DATABASE sjerp_role_smoke TO sjerp_smoke_runtime;
EOF
export APP_STAGE=staging DJANGO_ALLOWED_HOSTS=localhost MEDIA_ROOT="$work/media"
export SJERP_EXPECTED_MEDIA_ROOT="$MEDIA_ROOT"
export DJANGO_SECRET_KEY="$(openssl rand -hex 48)"
mkdir "$MEDIA_ROOT"
backend="$base/alex-stage-96276dff/backend"
python="$base/offline-check/bin/python"
cd "$backend"
export DATABASE_URL="postgresql://sjerp_smoke_migrate:$maintenance_password@127.0.0.1:$port/sjerp_role_smoke"
"$python" manage.py migrate --noinput >"$work/migrate.log" 2>&1 || { tail -25 "$work/migrate.log"; exit 1; }
"$pg/psql" -X -v ON_ERROR_STOP=1 -d sjerp_role_smoke <<'EOF'
GRANT USAGE ON SCHEMA public TO sjerp_smoke_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sjerp_smoke_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sjerp_smoke_runtime;
REVOKE INSERT, UPDATE, DELETE ON django_migrations FROM sjerp_smoke_runtime;
REVOKE UPDATE, DELETE, TRUNCATE ON crm_operationlog FROM sjerp_smoke_runtime, PUBLIC;
EOF
export DATABASE_URL="postgresql://sjerp_smoke_runtime:$runtime_password@127.0.0.1:$port/sjerp_role_smoke"
export SJERP_EXPECTED_DB_HOST=127.0.0.1 SJERP_EXPECTED_DB_PORT="$port" SJERP_EXPECTED_DB_NAME=sjerp_role_smoke SJERP_EXPECTED_DB_USER=sjerp_smoke_runtime
"$python" manage.py check_local_runtime
if SJERP_EXPECTED_DB_NAME=sjerp_wrong "$python" manage.py check_local_runtime >"$work/reject.log" 2>&1; then
    echo '库名错误却未被拒绝'
    exit 1
fi
grep -F 'Configured database NAME differs' "$work/reject.log"
printf '运行角色与目标库校验通过。日志：%s\n' "$work"
unit="$HOME/.config/systemd/user/$unit_name"
mkdir -p "$(dirname "$unit")"
for name in APP_STAGE DJANGO_ALLOWED_HOSTS DJANGO_SECRET_KEY DATABASE_URL MEDIA_ROOT SJERP_EXPECTED_MEDIA_ROOT SJERP_EXPECTED_DB_HOST SJERP_EXPECTED_DB_PORT SJERP_EXPECTED_DB_NAME SJERP_EXPECTED_DB_USER; do
    printenv "$name" | sed "s/^/$name=/" >> "$work/runtime.env"
done
printf '%s\n' 'SJERP_HTTP_HOST=localhost' 'SJERP_HTTP_PORT=18182' >> "$work/runtime.env"
template="$backend/../docs/deployment/sjerp-local@.service.example"
sed -e '/^User=/d' -e '/^Group=/d' \
    -e "s|/srv/sjerp/%i/release/backend|$backend|g" \
    -e "s|/srv/sjerp/%i/venv|$base/offline-check|g" \
    -e "s|/etc/sjerp/%i/runtime.env|$work/runtime.env|g" \
    -e "s|/etc/sjerp/%i/gunicorn.conf.py|$backend/../docs/deployment/sjerp-local-gunicorn.conf.py.example|g" \
    -e '/^\[Service\]/a Restart=on-failure\nRestartSec=1' "$template" > "$unit"
systemctl --user daemon-reload
systemctl --user start "$unit_name"
first=$(systemctl --user show --property=MainPID --value "$unit_name")
test "$first" != 0
systemctl --user start "$unit_name"
test "$(systemctl --user show --property=MainPID --value "$unit_name")" = "$first"
systemctl --user kill --kill-whom=main --signal=KILL "$unit_name"
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    second=$(systemctl --user show --property=MainPID --value "$unit_name")
    if [ "$second" != 0 ] && [ "$second" != "$first" ] && systemctl --user is-active --quiet "$unit_name"; then
        break
    fi
    sleep 1
done
test "$second" != 0 && test "$second" != "$first" && systemctl --user is-active --quiet "$unit_name"
systemctl --user stop "$unit_name"
test "$(systemctl --user show --property=ActiveState --value "$unit_name")" = inactive
printf '%s\n' 'systemd 生命周期通过：启动、重复启动、崩溃重启、主动停止。'
