# Django 6.0.9：Packing List 390px Chrome 补充

锁定版本原复核只含 1440px；原 390px 证据使用 Django 6.0.6。本次使用指定 closeout-python312 的 Python 3.12.16 / Django 6.0.9 / openpyxl 3.1.5（`versions.raw.log`，退出 0；Django 服务日志亦记录 6.0.9），从原合成 SQLite 复制到本目录，用本目录独立数据库和媒体目录、开发身份以及 Django 18466 / Vite 18467；未连接业务数据库。

真实 Chrome 156.0.8078.80 headless，视口 390×844，截图 `chrome-packing-390.png` 显示装箱完成与可见导出按钮。实际导出 `download-390.xlsx`：HTTP 200，建议文件名 `PackingList-SH-PL-01.xlsx`，64,719 字节，SHA-256 `eefffd251045bea2e91893b5f9d100970990a3bb7f0d5a80b5d5db1c906d6416`，与同次响应逐字节相同。ZIP CRC、openpyxl、16 列、发货/订单号、混装数量 3/2/4、箱数 1/1/空和小计公式均通过。`chrome-results-390.json` 与 `xlsx-verification-390.json` 记录结果。

原 `packing/chrome-390.cjs` 仅复制到本目录后调整 Playwright 模块相对路径和服务端口；原有动作与断言未减少。`verify-390.py` 原样复制，断言不变。旧结果及源码均未覆盖。

| 工作目录 | 命令 | 退出码及原始输出 |
|---|---|---|
| frontend | `node ../docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/packing-390/chrome-390.cjs` | 0；`chrome-390.raw.log`、`chrome-390.exit.txt` |
| 工作树根 | 指定 Python `docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/packing-390/verify-390.py` | 0；`verify-390.raw.log`、`verify-390.exit.txt` |
| 工作树根 | 指定 Python `-c` 打印解释器、Python、Django、openpyxl 版本 | 0；`versions.raw.log`、`versions.exit.txt` |
| backend | 指定 Python `manage.py runserver 127.0.0.1:18466 --noreload` | 任务完成后中断，工具会话退出 1；`django.raw.log` |
| frontend | `npm run dev -- --host 127.0.0.1 --port 18467 --strictPort`，代理 18466 | 任务完成后中断，工具会话退出 1；`vite.raw.log` |

`response.body()` 为诊断钩子，可能影响时序；单次通过不代替完整套件或证明其他时序无竞态。未触发 CI。
