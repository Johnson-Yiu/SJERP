# FINANCE-INVENTORY-CONSISTENCY-01 工作记录（未完成）

基线：`c90cacaa99a468d92dd61c41437834c5d8acb094`；对照：`c978758f37db8b8acf5e751fc7aa836287163a6b`。本记录不是验收通过证明。

已处理：按用户选择的应收计划优先核销；流水创建、计划收款和预收分配的写入与审计处于同一事务；手续费独占计划使用原收款关联的非现金分配，退款仅回退实际现金；订单状态和利润计算考虑有效抹零及其更正。

隔离 PostgreSQL 17 上，相关写入、回滚及退款定向测试 12 项通过；该组不包含并发测试。SQLite 定向测试 13 项通过。更大一组 130 项在最终格式修正前有三项失败：抹零更正金额格式、分配结果测试预期缺少 `remaining_amount`、列表逐行查询；第一项修正后单独通过，后两项尚未修复。CI：NOT_RUN。

必须继续：两条分支的收款优化能力逐项合流；全链路稳定请求身份及并发；跨模块银行事实关联和防重；原收款退款完整闭环；财务页面；三个 PostgreSQL 迁移起点；真实页面验收及所有其他用户指定的验收场景。当前不应合并或部署。

迁移原型：c978 的 `crm.0120_advanceallocation_cash_amount_and_more` 依赖 `crm.0119_merge_20261108_1834`，c90 的 `crm.0120_finance_actual_receipt_and_writeoff_correction` 依赖 `crm.0119_merge_finance_and_party`。两条 0120 均添加 `AdvanceAllocation.cash_amount` 和 `fee_credit_amount`；仅追加 merge 不能修复前面的重复 DDL。当前原型保留两条迁移身份，以受控的结构检查避免重复添加并保留现有现金拆分，再由 `crm.0123_merge_finance_receipt_histories` 合流。共享字段迁移不允许逆向删除。

隔离 PostgreSQL 17 已分别从空库、使用原 c978 代码迁移至 `crm.0120_advanceallocation_cash_amount_and_more`、使用原 c90 代码迁移至 `crm.0122_merge_sales_and_finance_review` 三个入口升级。后两个入口插入合成数据后，核对了现金拆分、抹零、优惠明细及其凭证、缺失汇率、抹零更正和三项拆分约束；三条路径均成功。可重复检查脚本为 `backend/test_support/finance_inventory_migration_probe.py`，仅允许运行于本机 `fic_*` PostgreSQL 库。此验证尚未覆盖 A/D 新模型、全面历史样本、并发升级及所有读取场景，请 A 暂勿据此实施全局汇合。

迁移回退回归尚有一项失败：既有 `DuplicateMigrationTests.test_reverse_refuses_existing_audit_and_preserves_row` 期望更早历史迁移的具体拒绝信息，而当前共享字段保护更早抛出不可逆异常。不得把该项记为通过；需明确回退顺序和对已有审计的保护后重新验证。

给 A/D 的接口契约尚未完成。公共台账尚未改动；建议在最终通过独立验收后再按项目审查协议记录。
