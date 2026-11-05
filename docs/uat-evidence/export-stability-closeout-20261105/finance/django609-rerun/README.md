# Django 6.0.9 财务重跑（2026-11-05）

使用 `D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/.tmp/closeout-python312/Scripts/python.exe`（Python 3.12.16、Django 6.0.9），`versions-utf8.log` 为实际解释器记录；`lock-check.log` 核对 requirements.lock 16 项全部一致，退出码 0。保留既有 Django 6.0.6 证据与首次失败日志，本目录为单独重跑。

## Django 自动测试

在工作树根目录运行：

```powershell
& $python backend/manage.py test crm.tests.test_actual_cash_reporting crm.tests.test_finance_reference_basis crm.tests.test_finance_closeout --noinput --verbosity 1
```

其中 `$python` 是上面的绝对路径；`APP_STAGE=development`、`DJANGO_DEBUG=true`、`DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`，DATABASE_URL 和 MEDIA_ROOT 指向本目录 unit 下的独立路径。`unit/django-tests.log` 记录 33/33 通过，`unit/exit-code.txt` 为 0；Django 创建和销毁测试数据库。

## 真实服务与 Chrome

两套独立全新 SQLite 和媒体目录分别为 `dashboard/isolated.sqlite3`、`dashboard/media` 和 `ledger/isolated.sqlite3`、`ledger/media`；开发环境权限遵循现有服务端入口。`ports.json` 记录各自 Django/Vite 专用端口，Vite 使用 `frontend/vite.isolated.config.js`，未使用全量运行器。每套先执行同一 Python 的 `manage.py migrate --noinput`，再执行该目录中的原样合法 API 种子脚本；迁移及种子日志和种子退出码保留。服务均以指定 Python 的 `manage.py runserver 127.0.0.1:<专用端口> --noreload` 启动，随后运行：

```powershell
node <本目录>/dashboard/real-check.cjs
node <本目录>/ledger/ledger-check.cjs
```

概览脚本原样副本为 `dashboard/real-check.original.cjs`，实际执行版本仅将写死的 5299 替换为新端口，替换逆向核对无其他变化；账户资金 Chrome 脚本及两份种子脚本按原样复制，SHA-256 见 `script-hashes.txt`。

- `dashboard/chrome.log`：16 次下载通过，退出码 0；桌面/390、9 月/10 月、账面/实际资金、连续两次，CSV、BOM、指定金额及 `= + - @` 转义通过。
- `ledger/chrome.log`：8 次下载通过，退出码 0；桌面/390、9 月/10 月及连续导出，按原脚本每个视口模拟首次 400，其余下载走真实 Django，检查重试和下载完成后切页重入。CSV、BOM、指定金额及四种公式转义通过。
- 两组正常下载均与另一笔相同 URL 的独立 HTTP 请求逐字节一致；Playwright 对浏览器响应体的读取少 BOM 三字节，不能称为同一响应体与下载直接逐字节一致。详见各自 `results.json`。
- 原账户资金脚本在页面查询完成前可能截到上一次期间数据，原截图保留；额外 `ledger/settled-screens.cjs` 等待查询完成并确认只有目标期间记录后补拍四张 `*-settled.png`，日志及退出码 0 单独保留。该补充没有更改原测试或断言。

首次 Django 6.0.6 运行与其失败记录不属于本次重跑，保留在上一级既有证据中。服务均已停止，未修改产品源码、原测试或全量运行器。
