# Packing List 390px Chrome 补充验证

沿用 `isolated.sqlite3` 合成订单 SO-PL-01、发货 SH-PL-01、开发超级管理员；Vite 18243 代理本地 Django 18242。Chrome 156.0.8078.80 headless，390×844。截图 `chrome-packing-390.png` 显示实际装箱完成、两 SKU 和可见导出按钮；导出真实 HTTP 200，下载 65,123 字节，SHA-256 `d4b991288a1df4490b8452af6d4d48d0753c517abf009e19d8eedf1ed5379b4d`，与同次响应逐字节一致，无浏览器下载错误。

在 frontend 目录运行 `node ../docs/uat-evidence/export-stability-closeout-20261105/packing/chrome-390.cjs`，退出码 0；原始标准输出/错误保存为 `chrome-390.raw.log`，退出码见 `chrome-390.exit.txt`。响应对比结果见 `chrome-results-390.json`，文件为 `download-390.xlsx`。

在工作树根目录运行 `python docs/uat-evidence/export-stability-closeout-20261105/packing/verify-390.py`，退出码 0；原始输出见 `verify-390.raw.log`，退出码见 `verify-390.exit.txt`。ZIP CRC、openpyxl、16 列、发货单/订单号、混装数量、箱数和小计公式均通过，详情 `xlsx-verification-390.json`。

浏览器响应读取可能影响时序，单次成功不排除其他时序竞态；未测试原生 Excel 打印、PostgreSQL 或 Linux。桌面脚本、日志和结果未覆盖；没有修改源码及既有测试，也没有提交、推送或触发 CI。
