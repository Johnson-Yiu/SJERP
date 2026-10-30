# R1-ISS006-INVENTORY-REVERSAL-AUDIT-ATOMICITY

- 基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 分支：`codex/r1-iss006-inventory-reversal-audit-atomicity-20261030`
- 工作树：`C:\Users\Johnson\.codex\worktrees\r1-iss006-reversal-audit\森爵照明管理系统`
- 发现来源：用户指定的 2026-10-30 ChatGPT 独立代码审查；没有推断或填写更早的首次发现日期。

## 修复范围

为 `ShipmentViewSet.reverse` 和 `InventoryMovementViewSet.reverse` 增加外层 `transaction.atomic`，将既有冲销服务、库存/业务状态变更和该接口原有审计写入纳入同一事务。手工流水仍按原顺序写两条审计；接口状态码、响应体、权限及冲销业务规则未改变，也未增加幂等协议。

## 验收结果

使用项目 `backend/requirements.lock` 创建的锁定 Python 环境（`logs/locked-dependencies.txt` 留存实际安装清单）；`pip check` 无依赖冲突。Django 使用 `DATABASE_URL=sqlite:///:memory:` 一次性内存 SQLite 测试库，`MEDIA_ROOT` 隔离在临时目录中。命令：

```powershell
python backend/manage.py check
python backend/manage.py test crm.tests.test_inventory_reversal_audit_atomicity crm.tests.test_inventory_movement_reversal crm.tests.test_fulfillment crm.tests.test_trade_finance_upgrade --verbosity 2
```

结果：Django system check 通过；定向回归发现 106 项，全部通过、无失败。新增场景覆盖：

- 销售发货冲销成功及重复冲销拒绝；审计失败时，发货单状态/时间/原因、冲销库存流水、订单状态、库存和预留均回滚。
- 手工库存流水冲销成功并写入两条既有审计；重复操作仍返回原有 400 业务拒绝。
- 手工冲销第一条审计写入失败，以及第二条审计写入失败；两种情况下原流水、冲销流水、库存、预留和所有审计记录均保持事务前状态。

详细输出在 `logs/targeted-tests.log`、`logs/system-check.log`、`logs/locked-dependencies.txt`。故障注入产生的预期 `DatabaseError` traceback 后对应测试显示 `ok`；它们不是测试失败。

本轮按要求只执行 SQLite 隔离事务测试；不以 SQLite 结果声明 PostgreSQL 并发验证。未运行前端测试、GitHub Actions、生产数据库或部署。

## 台账处理

未新增 Issue：`PROJECT_ISSUES.md` 已有 ISS-006，范围包含库存收货/发货/冲销及重复操作原子性。本次两个新发现作为 ISS-006 的补充核实记录，保留全局 `NEEDS_VERIFICATION`（其余 PostgreSQL 并发与库存流程验收仍未完成），不关闭该 Issue；该子范围标记为待独立复审。
