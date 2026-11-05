# 财务 CSV 专项验证（2026-11-05）

- Chrome 稳定版，独立 Vite 127.0.0.1:5298；API 使用合成响应拦截，不连接业务数据库。1440 与 390 财务概览截图已人工检查。
- `chrome-test.log`：3/3 通过。概览桌面与 390 覆盖 400 失败重试、导出请求期间修改并查询日期、旧请求的文件名和下载内容保持原期间、连续导出、切换页面后返回；校验模拟 CSV 的 UTF-8 BOM。实际资金覆盖失败重试和请求中禁用重复导出（桌面）。
- `django-test.log`：Django 自动创建并销毁独立测试数据库，33/33 通过；包含实际资金真实 CSV 中公式式银行参考号转义、财务概览真实 CSV 表头及金额、账户资金既有测试。
- 范围限制：浏览器下载内容为模拟 CSV，非端到端后端内容；实际资金公式注入由 Django API 测试验证；未逐一验证所有财务 CSV 字段和所有公式前缀，未进行账户资金页面的 Chrome 导出交互，也未验证实际资金导出期间切换或页面切换。
- 首轮模拟 500 触发现有 GET 自动重试，测试期望立即失败不成立；最终测试改用 400 明确模拟不可自动重试的失败，不改原测试断言。

后续独立补充：`baseline-control/`保留基线相同测试3项失败，`period-race-control/`分别实测旧版账面/实际资金文件名错标和修复版匹配；`ledger-chrome/`另以真实Django、Chrome及合成账户资金事实完成桌面/390、两期间、连续下载与模拟400后重试。它们不改变上方3/3和33/33的独立计数。

## 原专项命令、环境与退出码

以下为本次会话中实际运行并写入现有日志的命令；工作目录均相对于本工作树根目录。Chrome 3/3 运行时的测试文件是当时版本，后来该文件增加了证据目录的环境变量适配，不能把当前文件字节视为当次运行快照。

在 `frontend` 目录先启动独立前端服务（单独进程）：

```powershell
npm run dev -- --host 127.0.0.1 --port 5298 --strictPort
```

随后在 `frontend` 目录执行 Chrome 专项，API 由测试拦截：

```powershell
$env:PLAYWRIGHT_WEB_SERVER_PORT='5298'
$env:PLAYWRIGHT_CHANNEL='chrome'
npx playwright test finance-csv-stability.spec.js --config playwright.config.js --workers=1 --reporter=list 2>&1 | Tee-Object -FilePath ../docs/uat-evidence/export-stability-closeout-20261105/finance/chrome-test.log
exit $LASTEXITCODE
```

实际进程退出码 **0**，3/3 通过；Vite 随后停止。运行环境为本机 Windows PowerShell、已安装 Google Chrome 和工作树现有 frontend/node_modules。除上面列出的两个变量外，未在该命令中显式覆盖其他环境变量；不能据此确认其继承值。

在 `backend` 目录执行 Django 专项：

```powershell
python manage.py test crm.tests.test_actual_cash_reporting crm.tests.test_finance_reference_basis crm.tests.test_finance_closeout --noinput --verbosity 1 2>&1 | Tee-Object -FilePath ../docs/uat-evidence/export-stability-closeout-20261105/finance/django-test.log
exit $LASTEXITCODE
```

实际进程退出码 **0**，33/33 通过。使用本机 Python（Django 6.0.6）及项目默认测试配置；Django 日志记录创建并销毁默认别名的测试数据库。本次命令没有显式设置 `DATABASE_URL`、`APP_STAGE`、`MEDIA_ROOT` 或其他环境变量，继承环境的具体值未单独记录，故不能仅凭命令声称其显式指定了 SQLite 文件路径。

后续独立期间竞争对照及真实 Django/SQLite/Chrome 补充证据分别见 `period-race-control/README.md` 和 `real-django-chrome/README.md`；两者不改变上述原运行结果或日志。

## Python / Django 版本核对

33/33 使用 `python manage.py test`，同一会话当时 `Get-Command python` 返回 `C:\Python314\python.exe`，且 `python -c "import django; print(django.get_version())"` 返回 **6.0.6**。2026-11-05 再次核对该路径为 Python 3.14.5 / Django 6.0.6；`backend/requirements.txt` 和 `backend/requirements.lock` 均锁定 Django **6.0.9**。因此 33/33 是非锁定 Django 的结果，不能作为 6.0.9 通过证据。每次进程未单独写出 sys.executable；路径依据同一会话的命令解析记录，非逐进程版本遥测。

需在锁定依赖环境重跑的模块：`crm.tests.test_actual_cash_reporting`、`crm.tests.test_finance_reference_basis`、`crm.tests.test_finance_closeout`。先在该环境记录 `python -c "import sys,django; print(sys.executable, django.get_version())"`，再运行上文完整命令；本记录未执行该重跑。

`real-django-chrome` 与 `ledger-chrome` 真实服务同样用未显式指定绝对路径的 `python` 启动，基于同一会话的命令解析，使用系统 Python/Django 6.0.6；两个服务本身未单独记录 `sys.executable` 与 Django 版本，逐进程版本为未直接采集。两组真实 Chrome 结果因此也不是锁定 Django 6.0.9 的验证。
