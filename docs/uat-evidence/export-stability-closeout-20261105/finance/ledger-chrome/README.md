# 账户资金 CSV：真实 Django / 隔离 SQLite / Chrome

- Django `127.0.0.1:11893`、Vite `127.0.0.1:11895`；`DATABASE_URL` 指向本目录全新 `isolated.sqlite3`，`MEDIA_ROOT` 指向本目录 `media`，`APP_STAGE=development`、`DJANGO_DEBUG=true`、`DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`。造数脚本在调用前核对实际 DB 与 media 路径；未连接真实数据库。Vite 使用现有隔离配置，缓存位于本目录。源码 HEAD 与账户资金页面 Git blob 见 setup.json。
- `seed.py` 使用真实 Django API 及状态机创建一个合成账户、上传合成凭证、创建并记账 8 条资金事实。来源编号在 9 月、10 月分别覆盖 `= + - @`。首次 seed.log 因 DEBUG=false 不满足开发身份而返回 403，未写入账户；设置项目约定的开发身份后 `seed-retry.log` 成功，退出码 0。
- 每个视口仅首次 CSV 请求通过 Playwright 拦截并模拟 HTTP 400，验证显示失败且按钮重新可用；后续正常请求全部转发到真实 Django。1440 和 390 均在 9 月、10 月分别连续成功下载两次，共 8 份；9 月下载后切到财务概览再返回账户资金，重选 10 月后继续下载。该页面切换发生在下载完成后，不覆盖下载请求进行中的离页场景。
- 实际下载保存为 `ledger-*.csv`，逐项状态、期间、字节数、SHA-256 和断言见 results.json / chrome-retry.log；chrome-retry-exit-code.txt 为 0。每份检查 BOM `EF BB BF`、字段、指定金额（9 月 120.01，10 月 450.01）、四种来源编号前缀的单引号转义，以及排除另一个期间的数据。并向相同 URL 再发一笔独立 HTTP 请求，原始字节与下载完全一致；这并非浏览器导出请求的同一 HTTP 响应。Playwright `response.body()` 少 BOM 三字节，故浏览器响应体本身与下载字节并非直接相等。
- 1440/390 页面及模拟失败截图已保存并人工检查，页面无横向溢出；控制台记录的 pageerror 为空。首轮 chrome.log 及初始失败截图保留：诊断脚本的标题定位匹配到两个相同标题，未进入导出；仅调整新诊断脚本的定位范围后重试，未改产品或原测试。
- 页面退出重入、失败重试、两个期间和连续下载均已验证；未测试请求进行中离页或所有字段与所有可能公式前缀。Django 和 Vite 隔离服务已停止；未改工作树源码、原测试或全量运行器。

版本核对：该真实服务由同一会话中的 `python manage.py runserver` 启动，命令解析对应 `C:\Python314\python.exe`、Django 6.0.6；项目锁定 Django 6.0.9，因此此结果不是锁定依赖验证。服务进程未单独记录 sys.executable 和版本，路径为同会话命令解析证据。详见上一级 finance/README.md。
