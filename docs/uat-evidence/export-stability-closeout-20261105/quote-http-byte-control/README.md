# 报价导出 HTTP 字节对照诊断

基线 HEAD `56ce3588f544fcfeb98d431fb71d7e2d937f67db`。本目录是新增独立证据，不修改原测试、运行器或产品源码；没有覆盖既有证据。

## 隔离和范围

从空白 `synthetic.sqlite3` 执行迁移，`seed.py` 在启动服务之前直接使用 Django ORM 写入测试合成 fixture：客户、产品、SKU 和报价。它不是业务写入操作、真实身份认证或正式数据；并断言实际数据库路径恰为本目录的 SQLite。`DATABASE_URL` 和 `MEDIA_ROOT` 均指向本目录，`APP_STAGE=development`、`DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`；没有连接业务数据库。专用 Django `127.0.0.1:18352`、Vite `127.0.0.1:18353`。真实 HTTP 验证的是开发身份下的报价导出读取路径，不证明业务创建流程、真实登录、正式权限或审计。

## 结果

- Chrome headless `156.0.8078.80`；页面 `/quotes?detail=1`，通过报价详情的“导出 Excel”触发真实 HTTP GET `/api/quotes/1/export/`，状态 200、正确 XLSX MIME。建议文件名和 Content-Disposition 均为 `QHTTP-20261105-001.xlsx`；浏览器下载无错误。
- 同一次 HTTP 响应 `http-response.xlsx` 和 Chrome `browser-download.xlsx` 均为 10,117 字节，SHA-256 均为 `cfcafad31c61b812ff6b06532b64ae277d677ec6836806dd541e9b986902a0a6`，原始字节相等。两份分别通过 ZIP CRC 和 openpyxl：`PI` 表 L9 报价号、C11 `QHTTP-MODEL`、J11 数量 2、L11 单价 12.5、M11 行金额 25、M14 小计 25。
- Playwright `download.path()` 内部临时路径长度 **100**，`saveAs` 目标绝对路径长度 **164**（JavaScript 字符串 UTF-16 代码单元）；完整路径、建议文件名及毫秒时间线记录在 `browser-result.json` 和 `chrome.raw.log`。这次路径长度仅作观察，不足以推断取消的原因。
- 时间均相对脚本开始：点击开始 6125.00 ms、完成 6205.75 ms；响应头 6614.68 ms、download 事件 6621.33 ms、`download.path()` 完成 7015.79 ms、`saveAs()` 完成 7020.56 ms、读取响应 body 完成 7026.41 ms。包含脚本调度时间，不是独立网络性能测量。

## 命令与原始日志

全部命令在本工作树中执行；日志为原始命令输出，退出码保存在对应 `*.exit.txt`：

| 目录 | 命令 | 退出码 | 原始日志 |
|---|---|---:|---|
| backend | `python manage.py migrate --noinput` | 0 | `migrate.raw.log` |
| backend | `python manage.py shell -c "import runpy; runpy.run_path('../docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/seed.py')"` | 0 | `seed.raw.log` |
| frontend | `node ../docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/chrome-control.cjs` | 0 | `chrome.raw.log` |
| 工作树根 | `python docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/verify.py` | 0 | `verify.raw.log` |

服务命令分别为 `python manage.py runserver 127.0.0.1:18352 --noreload` 和 `npm run dev -- --host 127.0.0.1 --port 18353 --strictPort`，原始输出在 `django.raw.log`、`vite.raw.log`。完成后人工中断服务，工具会话因中断返回 1；不将它作为服务异常或成功的正常退出码，未生成服务退出码文件。

`response.body()` 是专门的诊断钩子，且 `download.path()`、捕获和日志也可能影响时序；本次 body 在 `saveAs` 之后读取。此单次诊断不能替代原始无钩子场景或完整套件，也不能否定既有取消记录。未运行 CI、PostgreSQL 或 Linux。XLSX 使用现有应用模板，可能包含模板中预配置的卖方资料，分享前应按实际内容处理。
