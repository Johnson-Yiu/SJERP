# 0078 迁移兼容性核验

## 现状

当前 `codex/r1-moq-02` 只有 `crm.0078_purchase_moq_exceptions`，其依赖为 `crm.0077_rmb_cash_events`。
R1-SKU-01 PR #1 的 `crm.0078_sku_cost_verification` 也依赖 `crm.0077_rmb_cash_events`。

## 隔离 worktree 实测

在临时 worktree 中以当前分支为基线，仅恢复 PR #1 的 `0078_sku_cost_verification.py`，执行：

```text
python manage.py shell -c "from django.db.migrations.executor import MigrationExecutor; print(sorted(MigrationExecutor(connection).loader.graph.leaf_nodes()))"
python manage.py makemigrations --check --dry-run
```

结果确认 `crm` 出现两个并列 leaf：

```text
0078_purchase_moq_exceptions
0078_sku_cost_verification
```

`makemigrations --check --dry-run` 报告 multiple leaf nodes，确认存在迁移图冲突。未修改、删除或重写任一已发布迁移。

在同一临时 worktree 仅加入未提交的验证文件 `0079_merge_0078_sku_cost_verification_purchase_moq_exceptions.py`，依赖两个 0078 且不包含 operations 后，迁移图只剩 0079 leaf，`showmigrations crm` 同时列出 0076、0077、两个 0078 和 0079。验证完成后该临时文件和 worktree 已删除，未进入本分支。

## 安全合并顺序

1. 先合并或使 PR #1 的 `0078_sku_cost_verification` 成为目标分支祖先。
2. 在同时包含两个 0078 的分支中新增 0079 空 merge migration，依赖两个 0078。
3. 部署时执行正常 `migrate`，不重排历史迁移，不删除已执行迁移；已有数据库中两个 0078 哪个先执行都不改写业务数据，0079 只负责收敛依赖图。
4. 继续保留 SKU 成本核实字段与采购 MOQ 例外字段，两项功能均由各自 0078 migration 创建。

当前 PR #2 不擅自引用尚未成为祖先的 PR #1 migration，也不合并 PR #1、PR #2 或 master。因此最终迁移整合需按上述 PR #1 先行顺序完成，当前状态记录为集成顺序阻断，不影响本轮 MOQ 前端修复和单分支测试。
