# R1-A-FUP-02 原始操作记录

2026-10-18；REAL_UI_ACTION使用Codex内置浏览器5202，Chrome补充视觉；服务器8132经8131只读观察代理。全部为独立可销毁数据库r1a-fup02-isolated.sqlite3。身份为既有开发超级管理员，未启用正式RBAC、未创建员工账号。

FIXTURE_SETUP：fixture_setup.py、fixture-setup.log、fixture-ids.json。库存100pcs通过采购确认/收货服务建立；主订单FUP02-500为10pcs×USD50；另准备已收齐未发货、草稿、取消、历史completed欠款和零金额订单。准备数据不视为UI验收。

1. REAL_UI_ACTION：订单1→采购与发货→批量发货→默认10pcs基础单位→确认发货。主订单变shipped，出库10，货值USD500。01-shipped-unpaid.jpg。
2. REAL_UI_ACTION：关闭详情→财务流水→新增记账→客户收款→搜索/选择FUP02-500→金额340，汇率7.1，备注FUP02 REAL_UI partial receipt 340→保存。REAL_API_OBSERVATION：POST transactions 201，拆为150和190两笔，对应默认两计划。点击流水关联订单回到概览，shipped、已收340、待收160，02原图。
3. DATABASE_VERIFICATION：database_before_complete.json。REAL_UI_ACTION：完成履约→履约已完成，待收160仍在，逾期提醒仍在，且不再有完成/采购/发货待办；03内置浏览器、04 Chrome原图，已人工查看。database_after_complete.json逐行核对计划、流水、库存、发货、预留均未变。
4. REAL_UI_ACTION：点击当前待办“查看/登记本单应收”→URL receivables?order=1→仅看逾期→查询。只显示FUP02-500尾款计划：350/已核销190/待结160；05原图。日期来自fixture的过去日期，不通过改余额制造逾期。
5. REAL_UI_ACTION：登记收款→金额160→备注FUP02 REAL_UI tail receipt 160→确认登记收款。逾期列表清空。点击查看订单，重新GET工作台，履约仍completed、款项已结清、已收500、待收0，无收款待办；06原图，database_settled.json。
6. REAL_UI_ACTION：关闭详情→财务流水→新增记账→客户退款→搜索并选择FUP02-500→金额40，备注FUP02 REAL_UI refund 40→保存。点击流水关联订单，原履约completed不变，已收460、待收40、逾期40、收款链接恢复；07原图。reload页面后仍一致。database_refunded.json。
7. REAL_UI_ACTION：读取fixture订单2，已收500且未发货，履约confirmed，只有待发货，不显示完成履约；08原图。REAL_API_OBSERVATION：complete订单2返回400，不修改任何余额或状态；api-rejections.json。
8. REAL_UI_ACTION：读取历史completed订单5，回款100/待收200/逾期200；09原图。读取草稿3、取消4、零金额6，分别尚未生效/已取消/零金额订单无应收计划；10、11、12原图。以上只读，不执行确认/取消等额外业务动作。
9. REAL_API_OBSERVATION：重复complete订单1返回400；与订单2拒绝一起，database_after_rejections.json对比database_refunded.json全表逐行相等。UI快速重复完成使用MOCKED_TEST受控pending检查两入口禁用且仅一个POST；实际completed后无完成按钮。
10. REAL_UI_ACTION：客户管理→合成客户详情→订单记录6→FUP02-500（默认明细页）→概览，显示completed及待收40→应收跳转。13原图。客户关联列文案改“履约状态”后重新取数显示正确，17原图。
11. REAL_UI_ACTION / 受控真实服务故障：应收页点击查看订单前停止本轮独立Django服务；客户端只读GET按既有策略重试，最终显示加载失败/服务器暂时不可用/重试，无旧回款卡。14原图、browser-api-failure.json、api-failure-observer.log包含连接拒绝。恢复同库服务→点击重试→completed及部分收款40恢复；15原图。没有注入伪造API成功响应或修改业务库。
12. REAL_UI_ACTION：财务概览显示待收2笔、1704人民币（40+200原币×7.1），到期列表含主订单40及历史订单200；16原图。既有“实际收入”人民币折算口径不在本轮改动，仍由ISS-105跟踪。

MOCKED_TEST：Vitest权限矩阵、未授权恶意未脱敏payload；Playwright订单/应收返回、结清/退款reload、保存中禁用及重复、500重试；后端权限分支以测试patch控制。真实环境未降权或创建正式用户，不将这些证据写成正式RBAC/员工UAT通过。

原始HTTP请求/响应/状态：http-events.jsonl；数据前后及Decimal断言：database-*.json、database*.json、database-verification.log。截图为原始JPEG，不做图片编辑；screenshot-manifest.json提供尺寸与SHA256。
