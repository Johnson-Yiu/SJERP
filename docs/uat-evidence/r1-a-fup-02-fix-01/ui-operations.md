# 原始操作与证据分类

2026-10-18。隔离工作区r1-a-fup-02-fix-01；Vite5204→观察代理8133→Django8134。数据库仅r1a-fup02-fix01-isolated.sqlite3，全新migrate；开发超级管理员，未启用正式RBAC或创建员工账号。

| 分类 | 操作与结果 | 原始证据 |
|---|---|---|
| FIXTURE_SETUP | fixture_setup.py在空合成库通过既有服务准备库存、订单及历史样本；历史无计划记录7为模拟导入的completed订单，无迁移、无删除计划；quote_fixture.py准备仅用于表头检查的草稿报价 | fixture-ids.json、脚本、migrate.log、fixture_before_ui.json |
| REAL_UI_ACTION | 内置浏览器读取订单7，当前待办及回款状态明确“应收计划待核对”，当前待收“待核对”，无财务百分比；Chrome复核同样状态 | 01、05原图 |
| REAL_UI_ACTION | 主订单1采购与发货→批量发货10pcs；财务流水→新增记账→客户收款→关联FUP02-500→原币USD340、汇率7.1→保存 | http-events.jsonl真实POST201；before_complete.json |
| REAL_UI_ACTION | 回到订单概览，显示340/160；点击完成履约，状态completed，欠款160及逾期、应收链接保留，无采购/发货待办 | complete200及浏览器实读文本（02仅加载过程截图，不作业务结果截图）、after_complete.json |
| REAL_UI_ACTION | 点击本单应收链接至receivables?order=1，尾款计划350、核销190、待结160；登记收款160成功后通过查看订单链接返回 | receipt201、settled.json、03截图：款项已结清、无收款待办 |
| REAL_UI_ACTION | 财务流水新增记账→客户退款→关联同订单→USD40→保存→关联订单概览 | refund201、04截图、refunded.json：已收460/待收40、逾期40、履约completed |
| REAL_UI_ACTION | Chrome订单列表读取表头“履约状态”；历史订单待收单元格为“应收计划待核对”；侧栏报价管理读取表头“状态” | 06、07原图；真实GET200 |
| DATABASE_VERIFICATION | verify_database.py以Decimal比较160→0→40；完成履约前后全部计划、流水、发货、库存流水和预留逐行不变；历史订单7及其空计划/流水不变 | before/after_complete、settled、refunded、database-verification.log |
| MOCKED_TEST | 后端权限patch分别拒绝finance/transactions，派生状态/收款金额均None；前端恶意未屏蔽JSON亦隐藏金额、核对状态及导航；restricted无待办文案仅称可查看履约待办 | backend-targeted-final.log、Vitest、Playwright；08-mocked-permission.png |
| MOCKED_TEST | review状态、请求失败及重复点击沿用自动化受控API；不伪造异常历史余额来走真实流程 | fulfillment-receivables测试、Playwright日志 |
| BLOCKED | 本地无PostgreSQL实例；由最终精确HEAD GitHub PostgreSQL17 CI执行完整回归，最终结果见交付及GitHub checks | CI日志/链接绑定提交 |

首轮Playwright误复用已运行的旧5195服务，6失败/139通过，不能作为当前代码结论；已保留playwright-initial-wrong-server.log，改显式playwright.fix01.config.js绑定本工作区5204，完整145通过。targeted-initial.log保留测试夹具误打开报价详情导致未处理错误的首轮日志；修正测试URL为无detail后定向及全量通过。Chrome旧tab一度超时，重建新tab后真实Chrome检查及截图正常。

所有原图为浏览器截图原始字节，未重绘。01–04内置浏览器；05–07真实Chrome；08为Playwright模拟权限，不冒充真实员工会话。无计划样本是合成导入历史，缺失发货历史与应收计划，不以其0%履约流水推断真实历史履约完成是否合法；本轮只读显示兼容，不自动修复历史数据。

原图逐张检查补充：02-complete-loading-only.jpg拍在完成后重新加载期间，仅保留加载过程，不证明160状态。其业务结果由本轮真实HTTP200、payment_summary返回340/160及before/after_complete数据库快照证明。03结清、04退款、05核对提示、06/07表头均为有效真实页面原图。
