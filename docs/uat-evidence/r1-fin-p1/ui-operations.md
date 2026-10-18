# R1-FIN-P1 原始证据说明与真实操作记录

日期：2026-10-18，时区Asia/Shanghai。当前合成环境：Vite 5206 → Django 8136 → r1-fin-p1-isolated.sqlite3。真实UI使用开发超级管理员，无正式账号或RBAC配置。

## REAL_UI_ACTION

1. 内置浏览器进入`/finance`，等待数据完成。核对7988.00、391.90、7596.10及合同12780.00、应收1704.00；查看月度/分类/当前待结，保存01全页。
2. 进入`/transactions`，等待流水完成，核对原币CNY100/20、EUR10/参考78、USD12.34/参考87.90及既有退款40/参考284，保存02全页。点击“新增记账”，没有输入或提交；确认“流水发生日期”“参考折算汇率”“1原币对应人民币，仅用于账面折算”，保存03；点击取消正常关闭。
3. 进入`/reports?source=cash&group_by=direction&date_field=transaction_date&title=旧保存净现金流&view=table&metric=amount&date_from=2026-10-01&date_to=2026-10-18`。观察旧标题/查询保留，收入7988、支出-391.9、净7596.1；UI检查发现表格/指标选择的通用人民币标签未补齐，修正为cash专用参考标签后重载，再保存04全页。点击“导出 CSV”，观察“CSV 已生成，请查看浏览器下载。”。没有保存或覆盖用户图表配置。
4. Chrome初期创建页、读取CDP页面树超时。自动回归结束后新建Chrome任务页恢复。`/finance`确认口径和金额；CDP全页截图仍超时，改用工具支持的原生getScreenshot，成功保存05实际可见区域。点击概览“导出 CSV”；本页没有可靠新增反馈文本，导出以实际HTTP200及CSV响应留档核对，不冒称有未观察到的提示。
5. Chrome `/transactions`保存06；打开新增记账，读出真实表单“流水发生日期”“参考折算汇率”及单位说明，保存07；取消，没有写入。
6. Chrome打开步骤3同一旧配置URL，读出全部报表金额和reference note，保存08可见区域（查询区）；点击导出，观察“CSV 已生成，请查看浏览器下载。”。完整结果区原图见04。
7. Chrome `/receivables`，FUP02-500行待结USD40，点击登记收款，观察原币40、参考汇率7.1及“汇率仅用于账面折算，不表示已完成银行结汇或实际到账。”，保存09；取消，不确认登记。
8. Chrome `/`，等待加载完成，通过实际AX读取经营概览销售与账面参考口径，原生滚动到账面收支，保存10。对应7988.00、391.90、7596.10与概览相同。

图片均为截图接口返回的原始JPEG字节，未裁切、重排、重新编码或修改内容；尺寸/哈希见screenshots.json。IAB全页尺寸为页面内容尺寸，Chrome为原生可见区域，不把两者虚报为同一精确视口。01–04为IAB，05–10为Chrome。已人工检查，无乱码或遮挡主要口径；流水表在较窄屏使用既有横向表格滚动，不修改布局。

## REAL_API_OBSERVATION / DATABASE_VERIFICATION

- before/after.json及CSV由Django APIClient调用真实应用处理链，在同一合成库运行，属于进程内API观察。
- http-*.json/csv由urllib对运行中8136发起只读HTTP GET，状态/响应头/哈希见http-observations.json，三次200。不是模拟API。
- capture.py遍历全部CRM模型按主键记录序列化，前后SHA256一致。verify.py按Decimal核对所有金额及CSV数字单元格，verification.log为原始输出。
- 数据准备发生于before快照之前。真实UI不提交业务单据，不把准备脚本当作UI验收。

## MOCKED_TEST / 限制

- 新Playwright用after.json作为route mock，在1440和1024覆盖相同页面标签、旧配置及无主区域溢出；这些是模拟自动测试，不作为银行实收证据。Vitest的API也为mock。
- SQLite全量测试包含真实服务/数据库事务用例；PostgreSQL只能由最终GitHub CI证明，不冒称本地PG执行。
- 初期Chrome连接和CDP全页截图失败保留为工具异常事实，最终原生Chrome截图成功；不留下虚假缺图PASS。
- setup_fixture.py仅获准的一次性隔离合成库准备；不会清空主业务库，不可对真实数据库运行。
