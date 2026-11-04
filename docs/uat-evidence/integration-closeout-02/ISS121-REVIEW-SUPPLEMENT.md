# ISS121 复审补充：集成证据与关闭缺项

日期：2026-11-05
对象：ISS-121，历史资料资金、库存基准与剩余履约承接
性质：Codex 开发侧证据归纳与定向预审；不是 ChatGPT 独立接受、Issue 关闭或上线批准；协调方仅校准为待独立复审。

## 当前状态与范围

当前协调状态为 `FIXED_PENDING_REVIEW`（此前 `OPEN`）。依据完整历史来源、同一02140集成PG与真实Chrome接续证据，开发侧实现和隔离验收已具备复审条件；不是独立接受或关闭。ISS-121不在原86项队列中，作为新增1项独立补充，当前待复审合计87项；124唯一ID与原10项CLOSED不变。真实启用条件仍单列，不把它们当作代码未实现的原因。

历史承接完整稳定来源为 `ba4274742727a6794608dc8581a49b3692d865a6`，已作为历史来源完整合入 `447d7816ead2e971e249cb2e762b1a6f7009b9c0`。财务完整稳定来源是 `e301a86044ffe56b72172a94dc3b00ae09401b05`；`3a07e7ef1a9e63c98077d45492ba23b798c7fcdd` 是其较早祖先，不是最终交付来源。Linux 运维稳定来源为 `4a4f338b09e9a464f1e66c24a905c35c970729bf`。`application-equivalence-447d.json` 记录三来源均在 447d 的应用来源祖先链上。最终 Chrome 候选为 `02140bf46df27ba1abf5b9018507c07aae825769`，完整集成父节点为 447d；`application-candidate-02140bf.json` 记录 02140 与 447d 的 backend Git 对象完全相同，本轮与最终 Chrome 运行期间没有修改冻结应用代码。

## 当前入口

- 前端页面和路由：冻结候选 `frontend/src/views/HistoryTakeoverPage.vue`、`frontend/src/router.js`（`/history-takeover`）。
- 正式 API 路由：`backend/crm/urls.py` 的 `import/history-takeovers/`、template、detail、review-report 与 group action 路由；请求处理在 `backend/crm/history_takeover_api.py`。
- 归档上传、分组预检/审批/执行、来源登记、纠正/追加事件：`backend/crm/history_takeover.py`；模型与唯一性约束：`backend/crm/history_takeover_models.py`。
- 资金来源核实和正式资金服务桥接：`backend/crm/history_operational_finance.py`，最终记账经 `backend/crm/services/finance_closeout.py`；未结余额/草稿合同：`backend/crm/history_operational_contracts.py`；库存基准和撤销：`backend/crm/history_operational_inventory.py`。
- 迁移链：`backend/crm/migrations/0104_historical_inventory_baseline.py` 至 `0108_protect_history_truncate.py`，依赖从 0103 汇合迁移连续到 0108。

## 正常、拒绝、幂等与事务证据

02140 冻结版真实 Google Chrome UAT 已完成五个原验收脚本阶段：operation、history workflow、fulfillment、inventory-location、template；均 exit 0，Chrome `156.0.8078.80`。live 和复制后只读业务核验均 exit 0。实际记录 98 个 HTTP 请求（90 个 200、8 个 201）及 8 张桌面/390px 截图。最终报告为 `final-02140bf-history-chrome/FINAL-HISTORY-CHROME-02140BF.md`，机器结果为 `final-02140bf-history-chrome/result.json`。

合成正常路径状态：历史申请执行完成，12 条来源行、16 条历史事件；两个开发隔离 session 分别完成合成提交/复核。财务产生 287.43 元收入和 35.00 元支出两条正式合成事实，私有凭证文件字节数和 SHA 与复制文件匹配；库存 API 生成 SKU `SKU-000001` 并创建一条基准、两条库存流水和两份接续合同；收货 3 件、发货 6 件的重复请求均得到成功结果，应收 40、应付 6。下载模板 14,077 bytes，SHA-256 `791723d6644a697d8d8657018c5807a8c7de3e59a6f2fe813d41b31c50454720`。这些是隔离合成数据，不是实际历史资金、员工身份或公司余额。

拒绝与原子性由集成源码测试覆盖，并由 447d 的隔离 PostgreSQL 全量回归提供运行证据：

- `test_history_takeover.py::test_rejection_missing_dependencies_conflicts_and_simulated_data_never_execute`：拒绝模拟/缺依赖/冲突来源。
- `test_history_takeover.py::test_failure_in_later_business_write_rolls_back_the_whole_group`、`test_history_takeover.py::test_audit_events_are_database_append_only_and_development_identity_is_not_real_operator`：后续写失败回滚；历史审计追加属性。
- `test_history_operational_finance.py::test_unconfirmed_source_cannot_create_instruction`、`test_changed_source_does_not_create_finance_instruction`、`test_audit_failure_rolls_back_instruction_and_mapping`：未确认、快照改变、审计失败均不得留下资金指令/映射。
- `test_history_operational_finance.py::test_explicit_amount_review_post_and_idempotent_replay`：不同人员审批、记账后重放返回同一事实；测试断言只有一条 FinanceInstruction、FinanceFact 和记账事件。
- `test_history_operational_finance.py::test_concurrent_same_source_submission_is_idempotent`、`test_concurrent_post_creates_one_fact_and_one_history_event`、`test_history_takeover.py::test_postgres_concurrent_execute_is_serialized_by_group_lock`：并发源提交、记账和组执行路径。
- `test_history_operational_inventory.py::test_audit_failure_rolls_back_entire_group`、`test_source_change_after_approval_is_rejected`、`test_same_group_concurrent_replay_creates_one_baseline`；`test_history_operational_contracts.py::test_failure_rolls_back_links_drafts_and_plans`、`test_reversal_is_idempotent_and_preserves_records`、`test_reversal_rejects_formal_downstream_work`、`test_reversal_audit_failure_rolls_back_all_changes`：库存/合同原子性、重放和拒绝路径。

实际运行证据分来源和 SHA 记录，不能混成 02140 本轮重跑：

1. 历史稳定来源 `ba427...` 的原始报告 `docs/uat-evidence/history-operational-closeout-20261104/README.md` 记录 PostgreSQL 17 UTF-8 全量 1,342 项（1,311 pass、31 skip、0 error）、90 项 guard 专项通过，以及旧库升级、0108 有数据升级、TRUNCATE/危险回退拒绝证据。首轮 1,341 项 11 errors 是旧失败，保留且未当作通过。
2. 集成锚点 447d 的真实 PostgreSQL 17.11 全量 `final-pg-447d/final-pg-447d-result.json`：1,410 项，1,378 pass、32 skip、0 fail；完整恢复 102 表、1,218 行、133 migrations、5 个媒体文件，cleanup complete。三份 history/finance/history-operational 恢复验证均 PASS。历史运营恢复包括三张新表共 2/1/2 行，9/9 个 UPDATE/DELETE/TRUNCATE guard probe 被拒且数据不变。原日志：`final-pg-447d/logs/postgres-final-447d-opseed-receipt-relation.log`；恢复详情：`final-pg-447d/artifacts/postgres-backups/history-operational-restored-447d7816ead2.json` 与 `finance-restored-447d7816ead2.json`。
3. 447d SQLite 全量 1,410 项为 1,330 pass、80 skip、0 fail，记录在 `README.md` / 相关运行收据。它与 PostgreSQL 结果分开。02140 backend blob 与 447d 相同，因此可复用此 backend 证据作为代码等价来源；这不表示已在 02140 再跑 PostgreSQL。

## 迁移、旧数据与新表恢复

`INTEGRATED-SOURCE-REVIEW-447D.md` 记录迁移图无冲突、0103→0104→0105→0106→0107→0108 唯一叶节点为 0108，0104–0108 五个迁移 blob 在完整历史来源 ba427 与 447d 集成代码中相同。历史来源旧数据升级日志为 `docs/uat-evidence/history-operational-closeout-20261104/logs/postgres17-legacy-upgrade.log`（含旧合成客户、SKU、订单、仓库和数量）；带历史数据升级及回退拒绝还见 `postgres17-0108-upgrade.log`、`postgres17-0108-guard-final.log`、`postgres17-migration-guards.log`。集成版的实际新表填充/备份恢复由上文 447d PG restore artifacts 证明。

02140 Chrome run 自身另有隔离 SQLite 快照：`final-02140bf-history-chrome/artifacts/isolated-sanitized.sqlite3`，102 表、1,091 条业务/审计行；发布副本清除了 2 条 `django_session`，只读 integrity 检查为 `ok`、session 数为 0。其媒体副本包含一张合成凭证（55 bytes）。这是 Chrome 合成 UAT 的 SQLite 数据集，与 447d PostgreSQL 恢复的 1,218 行是不同数据库、不同 seed 和不同阶段；两个数字不应互相替代或作差异异常解释。

## 财务更正、源编号及凭证匹配范围

正式 `finance_closeout.post()` 要求 history 来源指令先由另一名授权用户批准、请求指纹未变、真实性为 `verified` 且凭证检查通过；已 posted 重放返回同一 FinanceFact。对已记账事实的更正走正式 finance correction 指令，不覆盖原事实；仅在保留同账户原事实关联且原事实无后续事实、转账/历史转账本金匹配、既有退款等阻断关系时允许进入该受控流程，并依赖审批/记账步骤。来源 `backend/crm/services/finance_closeout.py` 与 `backend/crm/tests/test_finance_closeout.py::test_approved_correction_replaces_effective_fact_without_fake_cash_outflow`、`test_separation_of_duties_and_cancelled_revision` 支持该窄范围。

这不等于历史承接拥有通用的“撤销已记账资金”能力，也没有证明更正后 HistoryTakeoverSourceRecord、handoff 状态与原始资金凭证在所有历史数据场景中都维持业务所需关联。依赖/已匹配/已退款事实被拒绝后，需通过财务负责人确认的正式逐笔更正/退款路径处理；未覆盖的历史来源关系仍是关闭缺项。

历史来源记录以 `(source_system, record_type, source_record_id)` 全局唯一，并以规范序列化 SHA 派生请求键；重复提交和内容变化冲突已有测试。但业务负责人仍需确认来源编号在此三元组作用域确实唯一；现有预审指出 160 字符最大长度、跨组同三元组冲突和请求键长度边界缺少显式边界用例。

服务检查来源行有 `voucher_reference`，且要求选择有效私有 FinanceVoucher、人工核实标记及权限流程；代码没有自动证明选择的上传文件与归档源行所写凭证编号/原件完全一致。Chrome 合成记录只证明合成文件 bytes/SHA 与本次复制一致。关闭前需要保留逐来源的人工凭证编号—文件 SHA—复核人对应记录，或增加明确错配拒绝证据；不能称系统已自动完成凭证对应。

## 状态建议与尚缺事项

本补充未发现新的、可据现有证据确定为缺陷的集成问题；以下是仍需收敛的独立接受/业务证据，不以推测代替：

1. **独立复审**：由指定独立复审者核查 02140 精确产品来源、历史财务/库存/合同正常与拒绝路径、迁移及恢复材料，并单独决定状态；本 Codex 侧报告不能关闭 Issue。
2. **业务语义确认**：确认 source_system/record_type/source_record_id 唯一范围、库存完整盘点 coverage、历史余额的人工核实责任，以及归档凭证引用与私有上传文件的逐笔对应程序。
3. **更正延续性**：对已记账历史资金的允许更正、退款、原来源映射及 handoff 状态定义具体业务场景和证据；现有代码只支持受控条件范围，不等同历史资金所有冲销/更正类型均可用。
4. **真实启用资料**：真实导入文件、真实来源日期、真实银行账户/余额、真实凭证及启用/切换日期都未由合成 UAT 提供；取得并核验这些资料仍需业务负责人授权。不得把开发超管或两个 synthetic session 当作真实员工认证、双人身份或正式 RBAC 验收。
5. **独立视觉关闭**：现有 8 张真实 Chrome 桌面/窄屏截图和运行报告可复用；仍需独立视觉复审对页面状态、按钮/提示、工作流和 1440/390 视口出具接受结论。截图存在不等于视觉复审已关闭。
6. **目标环境执行**：真实环境的迁移执行、最小数据库角色/保护器所有权、生产附件/对象存储 ACL、正式备份恢复与身份/RBAC需在目标环境另行验收。隔离 PostgreSQL 17.11 合成证据不是生产连接或部署验收。

状态建议：ISS-121 继续 `OPEN`。本报告只提供供父级协调者/独立复审使用的可追溯证据；由父级在完整集成闭环与独立复审范围收敛后决定是否调整为 `FIXED_PENDING_REVIEW`。不估算或改写任何全局 Issue 总数。

## 本轮日志封存

已将 `final-02140bf-history-chrome/logs/` 的 13 份已发布日志封存至 `final-02140bf-history-chrome-published-logs.zip`；逐文件发布 SHA-256、原始 SHA-256（取自原 `result.json`）、token redaction 次数、ZIP CRC32、文件大小及归档 SHA-256 见同名 `...-manifest.json`。归档 SHA-256：`171df07db165dc13d50d3d3e76ce53c4863bfeddc047a72d40c0949039ca5a50`；1 个发布日志记载 2 次 redaction。

r01/r02/r03 共 32 份已有发布日志合并封存于 `legacy-r01-r03-history-chrome-published-logs.zip`，逐条 CRC/SHA 与 redaction 字段在对应 manifest；归档 SHA-256：`1da64cccccc564360676c4dde4180fa3ff99f0647fb23f63ff567928e6cebcd2`；三份 API 日志共记载 6 次 redaction。ZIP testzip 与逐文件 SHA/CRC 校验均通过。发布日志内容未改。各轮未保留的未脱敏源文件路径一律标为 `UNKNOWN`；manifest 仅转录当时 `result.json` 留下的 raw SHA/bytes 和 redaction 计数，没有重建或另存未脱敏日志。
