# 锁定 Django 6.0.9 的报价与 Packing 真实服务复核

HEAD `56ce3588f544fcfeb98d431fb71d7e2d937f67db`。此前报价与 Packing 真实服务均以未指定路径的 `python manage.py runserver` 启动；当时的 Python 检查显示系统 `C:\Python314\python.exe` / Python 3.14.5 / Django 6.0.6，报价旧服务原始日志也明确记录 Django 6.0.6。Packing 旧服务日志未单独保存，版本根据当时同一系统 Python 命令及环境确认，并非旧服务日志独立证明。原 6.0.6 文件与结果未覆盖。

本次指定 `D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/.tmp/closeout-python312/Scripts/python.exe`，实际为 Python 3.12.16、Django 6.0.9、openpyxl 3.1.5，见 `verify.raw.log` / `verification.json`；两个 `django.raw.log` 分别记录 Django 6.0.9。锁文件及 requirements 均指定 Django 6.0.9。

使用各自旧合成 SQLite 的新副本，各自的 `DATABASE_URL` 和 `MEDIA_ROOT` 都指向本次 `quote/`、`packing/`，开发身份；不连接业务数据库。`quote/fixture.json` 是旧 fixture 的副本，里面的 database 字符串是旧来源元数据，不是本次实际 DATABASE_URL。报价 seed 是测试合成 ORM fixture，不代表业务写入或真实认证；真实 HTTP 只验证读取导出路径。

- 报价：真实 Chrome 156.0.8078.80，HTTP 200，下载文件名 `QHTTP-20261105-001.xlsx`；同次响应和浏览器下载各 10,143 字节、SHA-256 `27a048cc3b81d8b99392b35171d69225f8d2b6dd2e5e6a2de6a47abf086641c5`，逐字节一致。两文件 ZIP CRC、PI 型号 `QHTTP-MODEL`、数量 2、单价 12.5、金额与小计 25 均通过。路径长度、事件时间线和原始命令输出见 `quote/browser-result.json` 与 `quote/chrome.raw.log`。
- Packing：真实 Chrome 156.0.8078.80 点击 10 次；10 次 HTTP 200、下载成功、与各自同次响应逐字节一致；10 份 ZIP CRC、16 列、发货/订单号、混装数量、箱数及公式检查通过。各文件哈希和结果见 `packing/chrome-results.json`、`verification.json`。此脚本捕获响应后在内存比较，没有保存单独的 HTTP 响应文件；其 `chrome.raw.log` 为空是因为脚本正常运行不输出文本，结构化结果另存 JSON。

命令与退出码：

| 工作目录 | 命令 | 退出码 / 日志 |
|---|---|---|
| backend | 指定 Python `manage.py runserver 127.0.0.1:18462 --noreload`，quote 专属数据库 | 服务人工中断；工具会话 1，`quote/django.raw.log` |
| backend | 指定 Python `manage.py runserver 127.0.0.1:18464 --noreload`，packing 专属数据库 | 服务人工中断；工具会话 1，`packing/django.raw.log` |
| frontend | `npm run dev -- --host 127.0.0.1 --port 18463 --strictPort`，代理 18462 | 服务人工中断；工具会话 1，`quote/vite.raw.log` |
| frontend | `npm run dev -- --host 127.0.0.1 --port 18465 --strictPort`，代理 18464 | 服务人工中断；工具会话 1，`packing/vite.raw.log` |
| frontend | `node ../docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/quote/chrome-control.cjs` | 0，`quote/chrome.raw.log` / `quote/chrome.exit.txt` |
| frontend | `node ../docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/packing/chrome-check.cjs` | 0，`packing/chrome.raw.log` / `packing/chrome.exit.txt`；结果见 JSON |
| 工作树根 | 指定 Python `docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/verify.py` | 0，`verify.raw.log` / `verify.exit.txt` |

报价和 Packing 都有 `response.body()` 诊断钩子，可能影响时序；报价还调用 `download.path()`。这些定向诊断不替代无钩子的完整套件，不能消除既往取消记录或证明所有时序可靠。未触碰原测试、运行器、业务源码或正在运行的全量套件；未触发 CI。报价文件沿用应用模板，可能含模板中预配置卖方资料，分享前检查。
