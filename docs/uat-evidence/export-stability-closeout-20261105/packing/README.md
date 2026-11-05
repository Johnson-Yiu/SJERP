# Packing List 导出专项核验

基线 HEAD `bcdcb57545f121b8a4102f352c74008b47372035`；开发超级管理员、独立 SQLite、合成订单 SO-PL-01 与发货 SH-PL-01。未修改产品源码或既有测试、未提交推送、未触发 CI。工作树同时存在其他任务并行修改，本专项未触碰。

- 后端：`python manage.py test crm.tests.test_packing_list_export --verbosity 1`，28/28 通过（Django 测试数据库），覆盖模板、混装、分批、拒绝、权限等现有断言。
- 前端：`npm exec -- vitest run tests/shipment-actual-packing.spec.js --environment jsdom`，26/26 通过，保留原断言。
- 初次28/28与26/26来自工具输出，原日志未单独保存（UNKNOWN）。为交付完整日志，随后在明确的内存SQLite、development和专用合成媒体目录中，以Python 3.12执行 `manage.py test crm.tests.test_packing_list_export --verbosity 1`，28通过、0失败/跳过、退出0；另执行 `npx --no-install vitest run tests/shipment-actual-packing.spec.js --environment jsdom`，26通过、0失败/跳过、退出0。真实重跑日志及SHA分别为 `packing-django.log`、`packing-vitest.log` 和 `test-logs-manifest.json`，不把重跑日志冒充初次日志。
- 日志留存说明：以上两项的原始日志文件路径均为 **UNKNOWN**，本目录未保存对应原始日志。命令及退出码来自本次会话的工具调用记录：后端命令在 `backend` 目录执行，Vitest 命令在 `frontend` 目录执行，二者工具结束结果均为退出码 `0`。工具输出曾显示分别运行 28 项和 26 项通过，但没有可独立读取的原始日志文件；未重新运行或重建日志。
- 真实 Chrome 156.0.8078.80 headless，通过 Vite 与实际 Django HTTP 打开订单装箱页，点击导出两轮各 10 次，未见下载取消；第二轮每次 HTTP 200，浏览器下载字节逐一等于对应响应字节。结果、哈希和文件见 `chrome-results.json`、`download-*.xlsx`。
- 10 份保留文件均通过 ZIP CRC、openpyxl 加载，核对 16 列、订单/发货号、混装数量 3/2/4、箱数 1/1/空及小计公式；详见 `xlsx-verification.json`。`chrome-packing.png` 为页面现场；seed 和浏览器脚本记录运行方法。SQLite 仅含合成数据。

未复现缺陷；原有立即删除链接及零毫秒撤销 URL 仍存在，有限次数通过不证明在所有机器或时序下无竞态。第二轮读取了 HTTP 响应用于字节比较，可能影响时序；第一轮未读取响应，10 次也成功，但其逐次结果被第二轮结果覆盖，不作为逐项保存记录。其他导出入口仅做静态检索，未逐一执行 Chrome；PostgreSQL、Linux、原生 Excel 打印预览及多页实际打印本轮未测。ISS-040 仍待独立复审；不更新公共台账。CI 因额度不足暂停，未执行且不标记通过。
