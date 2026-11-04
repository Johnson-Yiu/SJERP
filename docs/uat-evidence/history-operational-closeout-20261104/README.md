# 历史业务接续合成验收与独立复审交付

基线：`8087f2c68b19a302a25e814ec8ce6113d91d4750`。本工作包只使用隔离数据库、临时媒体和合成资料，不授权真实数据迁移。

## 范围与风险

| 子项 | 依赖和保护 | 当前状态 |
|---|---|---|
| 已归档资金来源 | 显式账户、原始来源、实际 CNY 金额/日期、私有凭证；正式财务服务复核与记账 | 已实现，合成流程及 PostgreSQL 定向回归通过；待独立复审 |
| 历史应收应付 | 原币未结余额须由原始付款计划与核对依据支持；不得重记已收付款 | 已实现合成逐笔和余额入口及跨模块演练；待独立复审 |
| 库存盘点基准 | 原盘点记录、SKU/单位、仓库与货物归属、批次、成本和凭证；SKU 锁与现有流水/预留隔离 | 已实现盘点、复核、启用和受控撤销；真实 PostgreSQL 并发专项通过 |
| 剩余履约 | 保留历史单据及事实；后续采购、销售和正式修订不得重放历史库存 | 合成部分履约、收货、发货、冲销和数量修订已有自动测试；真实历史状态仍须业务核验 |
| 整组完成状态 | 各交接阶段、重试、撤销、审计与原子性 | 分阶段显示、完成判定、未使用草稿撤销及故障并发已有合成测试；待独立复审 |
| 浏览器及 PostgreSQL 17 | 桌面、390px、真实 PG 并发和迁移升级/拒绝回退 | 桌面及窄屏 Chrome、真实 PostgreSQL 定向与全量回归已执行；待独立复审 |

权限：现有开发身份规则保持；操作入口需历史承接权限与对应财务或库存权限。真实财务记账仍由财务服务验证账户、凭证、来源和权限。历史资金指令须另一名认证用户复核，库存基准也要求不同的复核用户；开发身份审计标注为非实名。

## 已执行的中间检查

- SQLite 内存数据库：资金与库存首轮定向 10 项通过；较早输出见 `logs/sqlite-finance-inventory-initial.log`。后续代码变更后必须重跑，不把此记录当成最终验收。
- 补充 SKU 库存显示及既有可用量回归：18 项通过；该运行在后续来源一致性检查之前，尚需重跑。
- 前端历史承接 Vitest：4 项通过；后续界面变更后须重跑。Vite 构建成功，已有大 chunk 警告。
- 锁定依赖的 SQLite 定向测试：24 项运行，19 项通过、5 项 PostgreSQL 专项跳过；详见 `logs/sqlite-locked-final-focused.log`。此后新增 PostgreSQL 合同并发专项及采购公共费用测试，须分别补验。
- 前端 Node：179 项通过；按 CI 的有效 Vitest 选择运行，77 个文件、722 项通过。后续变更已另外运行定向回归。
- Chrome 156 在一次性 SQLite 和独立媒体目录中完成合成组的审核、归档及三个接续入口的读取；[1440px 截图](screenshots/history-operational-1440.png)、[390px 截图](screenshots/history-operational-390.png)、[运行记录](screenshots/chrome-run.json)。此项只证明所列浏览器操作和布局，不代表浏览器已完成全部资金与履约链。
- 采用 [EDB PostgreSQL 17.10 Windows 便携包](https://get.enterprisedb.com/postgresql/postgresql-17.10-2-windows-x64-binaries.zip)（本次下载 SHA256 `ef9b1e5e23d2e8a83914ba13d9dc536a72210fba53fd1808ff1f7e06bb22b106`），在临时目录创建仅监听 `127.0.0.1` 的专属集群及随机测试库；并非系统服务或业务数据库。锁定依赖下历史接续及原归档工作流共 43 项真实 PostgreSQL 测试通过、无跳过，进程正常退出，见 `logs/postgres17-history-final.log`。包含资金同源并发提交与记账、库存同组重试及跨组同 SKU 竞争、合同并发执行、原归档并发、拒绝回退及权限／原子性。
- 独立临时 PostgreSQL 库完成 0103→0107 升级，见 `logs/postgres17-upgrade.log`；在该库建立合成记录后，0107 的位置、0106 的历史采购口径及 0105 的接续合同分别阻止有数据回退，数据保留并恢复最新迁移，见 `logs/postgres17-migration-guards.log`。首次 43 项测试断言虽全部通过，但因测试线程未显式关闭连接导致测试库清理失败；修复测试连接关闭后重跑通过，首次失败保存在 `logs/postgres17-history.log`。
- 另一个临时 PostgreSQL 库先迁移至 0103，写入合成客户、SKU、订单和库存流水，再升级至 0107；客户、关联关系、仓库和数量保持不变，新增仓库字段使用兼容默认值，见 `logs/postgres17-legacy-upgrade.log`。
- PostgreSQL 定向命令（先将 `DATABASE_URL` 指向新建的本机隔离 PostgreSQL、`MEDIA_ROOT` 指向临时目录，并设置一次性测试密钥）：`python manage.py test crm.tests.test_history_operational_contracts crm.tests.test_history_operational_finance crm.tests.test_history_operational_inventory crm.tests.test_history_takeover --verbosity 2`。此次使用隔离 staging 设置验证认证和授权，不影响开发环境或正式 RBAC。
- 公共费用可先建立接续草稿，再经现有采购成本分配保存；有待登记费用的草稿在费用保存前不能正式下单，见 `logs/sqlite-shared-cost.log`。
- 本报告逐项区分合成验证、真实业务数据待核验以及 GitHub CI 未执行的情况。
- 基础提交 `438bc5b8526bb43b48445b4646e82ead0b2caaa6` 的 [GitHub CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41868099905) 中 PostgreSQL 作业失败：6 个新增并发/迁移测试在上传夹具时使用了此前 CSV HTTP 测试已经删除的临时目录，报 `FileNotFoundError`，尚未运行到并发断言。已为本包 PostgreSQL 测试单独指定系统临时上传目录，需在后续提交的真实 PostgreSQL CI 重验；不得把首轮失败视为通过。
- 同一 CI 的前端作业在 `iss007-attachment-real.spec.js` 失败：合成附件上传后再次打开编辑框时，5 秒内未显示文件名，两个后续场景未运行。本机锁定依赖、隔离 SQLite 和真实 Chrome 的首次复跑出现相同失败；第二次独立复跑 3 项全部通过（上传重开、SKU 与报价图片快照、失败重试）。保留两次脱敏日志 `logs/chrome-iss007-recheck-redacted.log`、`logs/chrome-iss007-retained-redacted.log` 和第二次截图，暂按不稳定现象交集成方调查，不能据此认定根因或宣称首轮 CI 通过。本包未修改跟进附件界面。
- 后续提交 `bf7ad52f6758b9a18be882a83dff7bb188a1f13b` 的 [GitHub CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41872716953) 三个作业均标为 failure，但作业步骤均为空，测试未启动。
- `e8fcc5f7a9b4afdda762810a83134657b9589e93` 的 [GitHub CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41874838749) 三个作业也都没有运行任何步骤。GitHub 对三个作业的失败注释均说明近期账户付款失败或支出限额需要提高；具体账户问题需在 GitHub Billing & plans 核实，不能把此状态描述为测试通过。
- 锁定依赖的本地完整 Django 回归：1335 项运行、66 项环境跳过，其余通过；执行时早于整体进度判定及后续小修，后续改动需定向复验。日志包含合成请求和故障注入输出，不是生产数据。
- 合成合同“已取消、零余额”和“履约已完成但有核实未结余额”场景均通过：不重建剩余发货或收货，按明确余额创建计划，见 `logs/sqlite-lifecycle.log`。

## 同组合成业务演练

真实 Chrome 使用隔离 SQLite、独立媒体目录和两个合成开发身份：完成组审核和归档，两笔历史资金分别保存、由另一身份复核及经正式财务服务记账；审核并启用库存基准；逐笔承接未结计划；建立并确认销售、采购接续单。随后通过同一 Chrome 会话请求正式 API 完成采购收货 3、销售发货 6，以及后续收款 20 USD、付款 4 USD。相同请求键重放收货和发货均返回原记录。结果与请求证据见 [Chrome 工作流记录](screenshots/chrome-workflow.json)、[履约前后状态](screenshots/chrome-fulfillment.json)、[桌面截图](screenshots/history-operational-settled-1440.png)、[390px 截图](screenshots/history-operational-settled-390.png)。

只读复核合成数据库的 [日志](logs/browser-database-verification.log) 显示：两条历史资金事实、两条启用后新收付款、一个库存基准、各一条收货和发货、两条库存流水；原盘点 18，加收货 3、减发货 6 后实际库存 15，预留为 0。原销售和采购行数量仍分别为 10、5，接续行分别为 6、3；已核实的初始未结 60/10 USD 在新收付后为 40/6 USD。两条库存流水保留来源仓库及批次，采购成本归属关联接续销售单。事务失败和冲销验证见自动测试；以上截图不证明真实服务器或真实历史资料已验收。

手工库存流水新增仓库类型及批次输入；未选择类型时保留原接口默认行为，启用过盘点基准的 SKU 则须明确填写。真实 Chrome 仅检查输入与布局、没有提交库存流水：[桌面](screenshots/inventory-location-1440.png)、[390px](screenshots/inventory-location-390.png)。窄屏明细表可水平滚动；服务端位置校验及冲销见 `logs/sqlite-location-api.log`。

共享文件冲突点：本包在 `backend/crm/services/finance_closeout.py` 为历史来源增加复核后才能记账的服务边界检查，并在 `backend/crm/services/finance.py` 接入已审核历史未结计划。统一集成时必须与财务包共享服务逐行核对；不得通过删除该检查允许其他 API 绕过双人复核。

## 真正迁移前仍需提供和核验

需要经授权的来源系统导出、来源编号与单据行对应表、可访问的原始凭证、客户／供应商／SKU 唯一匹配资料、每笔真实收付款及实际人民币金额与账户、未结计划或余额核对依据、盘点日期与完整仓库／批次／所有权／成本资料，以及启用时已发生履约和后续业务记录。需由真实授权人员完成独立复核、备份恢复和生产环境权限／部署验收；开发身份不代表实名审核。当前没有授权导入这些真实资料。

从隔离服务实际下载的 [承接模板](history-takeover-template.xlsx)，SHA256 `9b44e5b072797c12e7b2ad44bb46dcdb3456f04c524b6cf1b1c252ad5a3f1e01`；工作簿包含使用说明和九个来源工作表。模板中的历史事实先经归档及审批，具体接续仍按页面和服务的校验办理。

真实 PostgreSQL 17 并发和带数据迁移回退拒绝已有上述本地证据。完整 PostgreSQL 首轮运行 1341 项，31 项跳过、11 项报错；报错均来自 Windows 默认 GBK 解码子进程 UTF-8 输出，见 `logs/postgres17-full.log`。使用 `PYTHONUTF8=1` 和新增迁移后重新完整运行：1342 项、31 项环境跳过，其余通过，见 `logs/postgres17-full-utf8.log`。不得将跳过项或空步骤 CI 失败作为通过。

本报告供独立代码与业务复审；真实业务资料、正式部署与 GitHub CI 仍须按上述条件另行验证。

## PostgreSQL 追加写入防护与角色边界

独立预审确认 0104/0105 仅保护 UPDATE 和 DELETE，未保护 TRUNCATE。增量迁移 0108 对历史盘点、盘点撤销、接续合同三表增加 PostgreSQL 语句级保护，有记录时拒绝回退；隔离测试清理仅在严格绑定的一次性测试库中暂时停用、事务内恢复并校验触发器。该触发器不约束能禁用触发器、修改迁移或拥有超级用户权限的数据库管理员；正式部署仍需配置最小权限的应用角色、独立迁移角色并实际验证，不能假设已经配置。

- 新迁移后的真实 PostgreSQL 17 定向回归：历史接续、原归档、测试库清理和数据库设置共 90 项通过、无跳过，见 `logs/postgres17-guard-focused-final.log`。三张表实际各有合成记录，逐表执行 `TRUNCATE ... CASCADE`，确认抛出追加保护错误且所有原记录保留；`SET CONSTRAINTS ALL IMMEDIATE` 先处理测试事务中待发生的外键事件，避免被关系占用错误抢先拦截。首次未处理延迟外键的失败见 `logs/postgres17-truncate-first.log`，首次定向失败见 `logs/postgres17-guard-focused.log`。
- 在已有合成合同的临时 PostgreSQL 库应用 0108 后，验证合同记录保持、清空被拒、带记录回退被拒，见 `logs/postgres17-0108-upgrade.log`、`logs/postgres17-0108-guard-final.log`；可复核脚本为 `verify-pg-0108-upgrade.py`。该迁移依赖 0107，统一集成时须检查其他工作包并行迁移编号。
- Windows 子进程编码修正后，包含前次 11 个报错用例的设置测试及三表 TRUNCATE 测试共 17 项通过，见 `logs/postgres17-truncate-and-encoding.log`；原全量首轮错误保留在 `logs/postgres17-full.log`。
- 新迁移后的 SQLite 定向回归共 60 项、跳过 14 项 PostgreSQL 专项，其余通过；`makemigrations --check --dry-run` 无差异，见 `logs/sqlite-0108-focused.log`。SQLite 不能证明 PostgreSQL 保护。

用户在本次交付时明确要求节省不足的 CI 额度，因此最终证据提交使用跳过 CI 标记；该提交的三项 CI 均不作为已通过验收。此前精确 SHA 的账单阻断状态仍如上记录。

集中复审还提出需继续核查：新历史表实际填充数据的备份恢复、来源编号 160 字符及跨组唯一作用域、真实凭证与业务事实的人工对应，以及已记账历史资金更正的关联链。这些事项不以合成演练或 CI 状态代替核验，业务规则及集成范围由协调任务确认；本包不另改公共财务服务。
