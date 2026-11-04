# 历史业务接续候选预审

## 范围与来源

只读比较基线 `8087f2c68b19a302a25e814ec8ce6113d91d4750` 与候选对象 `e8fcc5f7a9b4afdda762810a83134657b9589e93`。候选尚未明确稳定交付，本报告不表示接收或合入。完整提交链：

- `438bc5b8526bb43b48445b4646e82ead0b2caaa6` — Implement reviewed historical operational handoffs
- `bf7ad52f6758b9a18be882a83dff7bb188a1f13b` — Verify historical handoffs and isolate postgres fixtures
- `e8fcc5f7a9b4afdda762810a83134657b9589e93` — Complete historical lifecycle and inventory location evidence

Git 对象差异共 71 个文件（5845 additions / 46 deletions），包括后端接续服务、0104–0107 迁移、前端历史承接页、测试和候选证据。此次没有 checkout、合并、运行测试或读取工作树中的未提交源码；结论只针对上述固定对象。

## 代码中已看到的契约

### 正式资金承接与真实性隔离

`backend/crm/history_operational_finance.py` 的 `submit_source` 先锁定已归档、真实、完整的关联组和资金 handoff，再用 `verified_source` 对照原始行、解析结果及已归档资料。来源须为真实、已确认且有凭证引用；输入字段固定为账户、凭证、实际日期、人民币金额和核实依据。服务把真实性设为 `verified`，调用 `finance_closeout.submit`、`approve`、`post` 等正式服务，不直接创建 FinanceFact。

`backend/crm/services/finance_closeout.py` 对历史来源增加“必须已批准才能 post”的检查；审批服务要求认证用户且发起人不能审批自己的指令。提交、映射和审计处于同一事务；历史事件使用单独的 FinanceFact 来源标识，FinanceFact 唯一约束防止同一来源二次记账。待核实来源被拒绝的测试见 `backend/crm/tests/test_history_operational_finance.py`。测试还覆盖同请求重放、变更请求冲突、来源快照变化、审计失败回滚，以及 PostgreSQL 并发用例。

**凭证关联证据缺项：** 服务只要求来源有非空 `voucher_reference`，并要求用户选择一个有效 FinanceVoucher；代码没有验证所选上传文件与归档引用指向同一凭证。测试用合成文件并传入 `voucher_checked=True`，没有覆盖错配凭证拒绝。需要确认正式流程由审核人如何核对并留存这项对应关系；当前只能说有人工复核标记，不能说系统自动保证附件对应。

### 来源标识、长度与幂等

`HistoryTakeoverSourceRecord` 对 `(source_system, record_type, source_record_id)` 有全局唯一约束；`_source_key` 将此三元组规范序列化后 SHA-256，固定为 64 字符。请求键为 `history-cash:<hash>`，修订时追加前一指令 ID；在数据库字段上限内，不随最长来源编号增长。源记录 max length 为 160，当前测试覆盖同源重复、并发重复、内容变更冲突和来源快照变更。

**边界证据缺项：** 未见 160 字符来源编号、不同关联组同三元组冲突、来源键/请求键长度边界的显式测试。全局唯一约束意味着产品契约须保证编号作用域确实是 source system + record type + record ID；若编号只在组内唯一，则组标识缺席会形成拒绝冲突。需要业务负责人确认编号作用域并补边界用例。

### 库存基准与剩余履约

`backend/crm/history_operational_inventory.py` 启用前要求每条导入盘点来源有明确 SKU、单位、仓库、货物归属、数量、成本、批次/无批次结论和凭证；执行时锁 SKU，并拒绝已有库存流水、预留或未撤销基准的 SKU。库存读取把未撤销的自有货物基准并入数量；收货、发货、手工流水和冲销保留仓库类型及批次。相关服务及序列化逻辑见 `backend/crm/services/fulfillment.py`、`backend/crm/serializers.py`、`backend/crm/views.py`。

**覆盖边界：** 完整范围由导入组 coverage、来源行和 API 的 `complete_sku_inventory` 确认值共同表达；没有看到它与全体 SKU 主档做目录级对账的测试。需以实际导入模板/预检规则证明“完整盘点”覆盖范围不会漏掉应纳入的 SKU。PostgreSQL 下基准启用与并发库存写入的互斥也没有成功运行证据。

`backend/crm/history_operational_contracts.py` 通过归档剩余快照生成接续草稿，并要求每份合同及每条有余量明细都明确映射。逐笔余额核对来源计划的已确认流水净额与 settled amount；余额承接则必须人工填写金额和依据。新增测试断言合成销售/采购剩余数量为 6/3、启用未结计划、后续结算及付款金额变化；也覆盖已取消合同不重建履约、收货/发货冲销恢复库存、撤销未使用草稿和关键失败原子性。

取消范围受限于未进入正式业务的接续草稿；一旦确认、收货、发货或产生资金业务，服务拒绝直接撤销。已记账历史资金也不能通过该桥接服务取消或替换；应使用正式更正/退款流程。**缺少该后续资金更正如何继续关联原历史来源、保持余额与 handoff 状态一致的测试和操作证据。** 这不是“已完整支持历史资金冲销”的证据。

`execute`、资金提交/推进、库存基准执行及撤销均使用事务；测试包含接续计划创建失败、财务审计失败、撤销审计失败时的回滚断言。数据库并发结论仍取决于真实 PostgreSQL 运行，不能由 SQLite 代替。

## 迁移、不可变性与备份

`backend/crm/migrations/0104_historical_inventory_baseline.py` 依赖 `0103_merge_finance_and_history`；0105、0106、0107 依次依赖前一迁移。迁移新增库存基准/撤销、历史操作合同和采购历史财务语义，并为库存位置加字段；存在有数据时拒绝危险回退的保护。0104/0105 的 PostgreSQL 保护是行级 UPDATE/DELETE trigger，没有 TRUNCATE trigger；若数据库角色能对这些表执行 TRUNCATE，应用层 append-only 和行触发器不能阻止整表清空。需核实实际数据库权限，或补 statement-level 防护及 PG 用例。

**新表备份/恢复未验：** 候选没有提供迁移到 0107 后的 PostgreSQL 备份恢复结果。候选报告 `docs/uat-evidence/history-operational-closeout-20261104/README.md` 明确写明本机 PostgreSQL 17 不可用，迁移、并发及完整回归 BLOCKED。附带 `django-full.log` 是 SQLite 1335 项运行（66 项跳过），不是新表 PostgreSQL restore 证据。README 记录的 CI 41868099905 PostgreSQL 作业因临时目录缺失失败；41872716953 三作业步骤为空、测试未启动。故候选没有成功的 PostgreSQL 迁移、并发、回退或包含这些新表的备份恢复证明。

## 关闭前需补的证据

1. 明确来源编号唯一性作用域，并加入最大长度/跨组冲突测试。
2. 明确源凭证引用与 FinanceVoucher 的核对记录；增加错配拒绝或可复核人工证据测试。
3. 在 PostgreSQL 17 上执行迁移升级、并发争用、危险回退拒绝及新库备份恢复；确认新增历史表、关联与私有凭证均可恢复并校验。
4. 核实数据库角色是否可 TRUNCATE 历史基准/接续表；确认历史资金已记账后的退款/更正是否需保留到源记录映射，并提供实际业务用例。
5. 由业务负责人确认库存 coverage 的全量定义，以及 `balance_only` 金额由谁核实、凭据如何留存。
6. 来源若交付更晚 SHA，复核该 SHA 相对本候选的增量；本报告不覆盖未交付来源及正式整合验收。

本报告为候选源码预审，未执行测试，不是 ChatGPT 独立复审或最终验收；未修改代码、公共台账或 Git。