#!/bin/sh
set -eu
umask 077
base="$HOME/sjerp-build"
pg=/usr/lib/postgresql/17/bin
work=$(mktemp -d "$base/runtime-role.XXXXXX")
trap 'if [ -s "$work/db/postmaster.pid" ]; then "$pg/pg_ctl" -D "$work/db" -m fast -w stop >/dev/null; fi' EXIT
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
