"""Real local TLS proxy and application checks against isolated synthetic SQLite."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def reserve_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_process(arguments, *, env, log):
    stream = log.open("ab")
    process = subprocess.Popen(arguments, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    stream.close()
    return process


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def main():
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Only a task-owned ephemeral GitHub runner is supported")
    root = Path(tempfile.mkdtemp(prefix="sunjack-nginx-acceptance-", dir=runner_temp))
    if root.resolve().parent != runner_temp:
        raise RuntimeError("Temporary root identity mismatch")
    app = nginx = None
    start = time.monotonic()
    try:
        media, static, dist, certs = [root / name for name in ("media", "static", "dist", "certs")]
        for directory in (media, static, dist, certs):
            directory.mkdir(mode=0o700)
        runtime_temp = root / "runtime-temp"
        runtime_temp.mkdir(mode=0o700)
        (dist / "index.html").write_text("SYNTHETIC ERP", encoding="utf-8")
        relative = "sku-images/synthetic.bin"
        (media / "sku-images").mkdir()
        content = b"SYNTHETIC PRIVATE IMAGE CONTENT"
        (media / relative).write_bytes(content)
        voucher_relative = "finance-vouchers/synthetic.bin"
        (media / "finance-vouchers").mkdir()
        voucher_content = b"SYNTHETIC PRIVATE FINANCE VOUCHER"
        (media / voucher_relative).write_bytes(voucher_content)
        (static / "synthetic.css").write_text("/* synthetic */", encoding="utf-8")
        api_port, proxy_port, http_port = reserve_port(), reserve_port(), reserve_port()
        if len({api_port, proxy_port, http_port}) != 3:
            raise RuntimeError("Independent ports could not be allocated")
        backend = Path(__file__).resolve().parents[2]
        environment = os.environ.copy()
        environment.update(APP_STAGE="development", DEVELOPMENT_SUPERADMIN="false", RBAC_ENFORCEMENT="true",
            DATABASE_URL="sqlite:///" + (root / "synthetic.sqlite3").as_posix(), MEDIA_ROOT=str(media),
            DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1", DJANGO_SECRET_KEY=secrets.token_urlsafe(48),
            DJANGO_DEBUG="false", SESSION_COOKIE_SECURE="true", CSRF_COOKIE_SECURE="true", TMPDIR=str(runtime_temp))
        subprocess.run([sys.executable, str(backend / "manage.py"), "migrate", "--noinput", "--verbosity", "0"],
                       env=environment, check=True, timeout=180, capture_output=True)
        fixture = root / "fixture.py"
        fixture.write_text('''from pathlib import Path
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from crm.models import FinanceVoucher, Product, SKU
import hashlib
import os
root=Path(os.environ["SUNJACK_FIXTURE_ROOT"])
product=Product.objects.create(code="SYN-NGINX-P", name="Synthetic product")
SKU.objects.create(product=product, sku="SYN-NGINX-SKU", unit="pcs", image="sku-images/synthetic.bin")
voucher_data=b"SYNTHETIC PRIVATE FINANCE VOUCHER"
FinanceVoucher.objects.create(file="finance-vouchers/synthetic.bin", original_name="synthetic.bin", sha256=hashlib.sha256(voucher_data).hexdigest(), size=len(voucher_data), actor={"kind":"synthetic"}, scope="account")
users=get_user_model()
for name, privileged in (("synthetic_admin", True), ("synthetic_denied", False)):
 user=users.objects.create_user(username=name, is_staff=privileged, is_superuser=privileged)
 session=SessionStore()
 session["_auth_user_id"]=str(user.pk)
 session["_auth_user_backend"]="django.contrib.auth.backends.ModelBackend"
 session["_auth_user_hash"]=user.get_session_auth_hash()
 session.save()
 path=root / (name + ".session")
 path.write_text(session.session_key, encoding="ascii")
 path.chmod(0o600)
''', encoding="utf-8")
        environment["SUNJACK_FIXTURE_ROOT"] = str(root)
        subprocess.run([sys.executable, str(backend / "manage.py"), "shell", "--no-imports", "-c", "exec(open(" + repr(str(fixture)) + ",encoding='utf-8').read())"],
                       env=environment, check=True, timeout=60, capture_output=True)
        openssl, nginx_bin = shutil.which("openssl"), shutil.which("nginx")
        if not openssl or not nginx_bin:
            raise RuntimeError("OpenSSL and Nginx are required")
        key, cert = certs / "local.key", certs / "local.crt"
        subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key),
                        "-out", str(cert), "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
                       check=True, timeout=60, capture_output=True)
        repo = backend.parent
        template = (repo / "docs/deployment/operations-nginx.conf.example").read_text(encoding="utf-8")
        for old, new in (("listen 80;", f"listen 127.0.0.1:{http_port};"), ("listen 443 ssl;", f"listen 127.0.0.1:{proxy_port} ssl;"),
                         ("erp.example.invalid", "localhost"), ("/etc/sunjack/tls/fullchain.pem", str(cert)),
                         ("/etc/sunjack/tls/privkey.pem", str(key)), ("/srv/sunjack/frontend/dist", str(dist)),
                         ("/srv/sunjack/static/", str(static) + "/"), ("http://127.0.0.1:8000", f"http://127.0.0.1:{api_port}")):
            if old not in template:
                raise RuntimeError("Nginx template no longer matches acceptance substitution")
            template = template.replace(old, new)
        config = root / "nginx.conf"
        nginx_temp = root / "nginx-temp"
        nginx_temp.mkdir()
        temp_directives = "\n".join(f"{kind}_temp_path {nginx_temp / kind};" for kind in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"))
        config.write_text(f"worker_processes 1;\npid {root / 'nginx.pid'};\nerror_log {root / 'nginx-error.log'};\nevents {{ worker_connections 128; }}\nhttp {{\naccess_log {root / 'nginx-access.log'};\n{temp_directives}\n{template}\n}}\n", encoding="utf-8")
        subprocess.run([nginx_bin, "-t", "-p", str(root), "-c", str(config)], check=True, capture_output=True, timeout=30)
        context = ssl.create_default_context(cafile=str(cert))
        def request(path, session=None):
            headers = {"Cookie": "sessionid=" + session} if session else {}
            try:
                with urllib.request.urlopen(urllib.request.Request(f"https://localhost:{proxy_port}{path}", headers=headers), context=context, timeout=4) as response:
                    return response.status, response.headers, response.read()
            except urllib.error.HTTPError as error:
                return error.code, error.headers, error.read()
        def launch_app():
            return start_process([sys.executable, str(backend / "manage.py"), "runserver", f"127.0.0.1:{api_port}", "--noreload"], env=environment, log=root / "django.log")
        app = launch_app()
        nginx = start_process([nginx_bin, "-p", str(root), "-c", str(config), "-g", "daemon off;"], env=environment, log=root / "nginx-process.log")
        admin = (root / "synthetic_admin.session").read_text(encoding="ascii")
        denied = (root / "synthetic_denied.session").read_text(encoding="ascii")
        for _ in range(60):
            try:
                status, headers, body = request("/api/media/" + relative, admin)
                if status == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            if app.poll() is not None or nginx.poll() is not None:
                raise RuntimeError("Owned application or proxy exited before readiness")
            time.sleep(0.5)
        else:
            raise RuntimeError("Authorized proxy request never became ready")
        assert status == 200 and body == content and "no-store" in headers.get("Cache-Control", "")
        anonymous = request("/api/media/" + relative)
        restricted = request("/api/media/" + relative, denied)
        direct = request("/media/" + relative)
        assert anonymous[0] in (401, 403) and restricted[0] in (403, 404) and direct[0] == 404
        assert "no-store" in anonymous[1].get("Cache-Control", "") and "no-store" in restricted[1].get("Cache-Control", "")
        voucher_authorized = request("/api/finance-ledger/voucher-download/?id=1", admin)
        voucher_anonymous = request("/api/finance-ledger/voucher-download/?id=1")
        voucher_restricted = request("/api/finance-ledger/voucher-download/?id=1", denied)
        voucher_direct = request("/media/" + voucher_relative)
        assert voucher_authorized[0] == 200 and voucher_authorized[2] == voucher_content
        assert voucher_anonymous[0] in (401, 403) and voucher_restricted[0] in (403, 404) and voucher_direct[0] == 404
        assert all("no-store" in item[1].get("Cache-Control", "") for item in (voucher_authorized, voucher_anonymous, voucher_restricted))
        assert request("/static/synthetic.css")[0] == 200
        stop_process(app); app = launch_app()
        stop_process(nginx); nginx = start_process([nginx_bin, "-p", str(root), "-c", str(config), "-g", "daemon off;"], env=environment, log=root / "nginx-process.log")
        for _ in range(60):
            try:
                after = request("/api/media/" + relative, admin)
                if after[0] == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Authorized file unavailable after owned process restart")
        assert after[2] == content and hashlib.sha256(after[2]).digest() == hashlib.sha256(content).digest()
        assert request("/api/finance-ledger/voucher-download/?id=1", admin)[2] == voucher_content
        result = {"status": "PASS", "source_sha": os.environ["GITHUB_SHA"], "nginx_config_test": True,
                  "tls": "local synthetic certificate trusted explicitly", "authorized": status,
                  "anonymous": anonymous[0], "authenticated_without_permission": restricted[0],
                  "public_media": direct[0], "private_no_store": True, "static_separate": True,
                  "voucher_authorized": voucher_authorized[0], "voucher_anonymous": voucher_anonymous[0],
                  "voucher_authenticated_without_permission": voucher_restricted[0], "voucher_public_media": voucher_direct[0],
                  "application_and_nginx_restart_persisted": True, "seconds": round(time.monotonic()-start, 3)}
    except Exception:
        for filename in ("django.log", "nginx-process.log", "nginx-error.log"):
            path = root / filename
            if path.exists():
                print(filename + ": " + path.read_text(encoding="utf-8", errors="replace")[-3000:], file=sys.stderr)
        raise
    finally:
        stop_process(nginx)
        stop_process(app)
        if root.is_symlink() or root.resolve().parent != runner_temp or not root.name.startswith("sunjack-nginx-acceptance-"):
            raise RuntimeError("Owned temporary root identity mismatch")
        shutil.rmtree(root)
    result["cleanup"] = "complete"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
