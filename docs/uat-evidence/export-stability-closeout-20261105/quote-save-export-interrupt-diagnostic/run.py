import json, os, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[4]
here = Path(__file__).resolve().parent
backend, frontend = root / 'backend', root / 'frontend'
python = Path(r'D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/.tmp/closeout-python312/Scripts/python.exe')
source_db = root / 'docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/synthetic.sqlite3'
node = shutil.which('node')
flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
assert python.is_file() and source_db.is_file() and node

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def ready(url, process):
    for _ in range(100):
        if process.poll() is not None: raise RuntimeError(f'server exited {process.returncode}')
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200: return
        except Exception: time.sleep(.2)
    raise RuntimeError(f'server not ready: {url}')

def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=10)

summary = []
for index in range(1, 4):
    run = here / f'run-{index}'
    run.mkdir(exist_ok=False)
    shutil.copyfile(source_db, run / 'synthetic.sqlite3')
    api, web = port(), port()
    while web == api: web = port()
    env = os.environ.copy()
    env.update(DATABASE_URL='sqlite:///' + (run/'synthetic.sqlite3').as_posix(), MEDIA_ROOT=str(run/'media'), APP_STAGE='development', DEVELOPMENT_SUPERADMIN='true', RBAC_ENFORCEMENT='false', PYTHONUNBUFFERED='1', DIAG_RUN_DIR=str(run), R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR=str(run), ISOLATED_TEST_ROOT=str(run), DIAG_BASE_URL=f'http://127.0.0.1:{web}', VITE_API_PROXY_PORT=str(api), EXPORT_STABILITY_CHROME='1')
    seed_cmd = [str(python), 'manage.py', 'shell', '-c', f'import runpy; runpy.run_path({str(here / "seed.py")!r})']
    servers = []
    result = {'run': index, 'api_port': api, 'vite_port': web, 'database': str(run/'synthetic.sqlite3'), 'seed_command': seed_cmd, 'status': 'UNKNOWN'}
    try:
        with (run/'seed.raw.log').open('wb') as out:
            seed = subprocess.run(seed_cmd, cwd=backend, env=env, stdout=out, stderr=subprocess.STDOUT, timeout=90, creationflags=flags)
        result['seed_exit'] = seed.returncode
        if seed.returncode: raise RuntimeError('seed failed')
        api_out = (run/'django.raw.log').open('wb')
        web_out = (run/'vite.raw.log').open('wb')
        servers.append((subprocess.Popen([str(python), 'manage.py', 'runserver', f'127.0.0.1:{api}', '--noreload'], cwd=backend, env=env, stdout=api_out, stderr=subprocess.STDOUT, creationflags=flags), api_out))
        servers.append((subprocess.Popen([node, str(frontend/'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(web), '--strictPort'], cwd=frontend, env=env, stdout=web_out, stderr=subprocess.STDOUT, creationflags=flags), web_out))
        ready(f'http://127.0.0.1:{api}/api/session/current-operator/', servers[0][0])
        ready(f'http://127.0.0.1:{web}/', servers[1][0])
        cmd = [node, str(frontend/'node_modules/@playwright/test/cli.js'), 'test', '--config', str(here/'playwright.config.cjs'), '--output', str(run/'artifacts')]
        result['test_command'] = cmd
        with (run/'playwright.raw.log').open('wb') as out:
            test = subprocess.run(cmd, cwd=frontend, env=env, stdout=out, stderr=subprocess.STDOUT, timeout=120, creationflags=flags)
        result['test_exit'] = test.returncode
        result['status'] = 'PASS' if test.returncode == 0 else 'FAIL'
    except Exception as exc:
        result['status'] = 'FAIL'
        result['error'] = repr(exc)
    finally:
        for proc, out in reversed(servers): stop(proc); out.close()
        (run/'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
        summary.append(result)
        (here/'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=True), flush=True)
    if result['status'] != 'PASS': break
sys.exit(0 if len(summary) == 3 and all(x['status']=='PASS' for x in summary) else 1)
