# 两分支临时集成记录

## 验证输入

- 库存分支：`codex/r1-inv-03`，`2731e7b678f40d82a00a0c868a0db992bd535f82`
- MOQ 分支：`codex/r1-moq-02`，`aa35db2a49b6152e35f57b74edff95914735864d`
- 临时 worktree：`C:\Users\Johnson\.codex\worktrees\r1-inv-03-fix-02-integration`
- 临时分支：`codex/tmp-r1-inv-03-fix-02-integration`

临时 worktree 从库存分支建立，再执行：

```powershell
git merge --no-commit --no-ff codex/r1-moq-02
```

没有合并 `master`，没有修改两个正式开发分支。

## 冲突及处理

Git 报告的冲突只有：

- `frontend/src/views/PurchaseOrderPage.vue`
- `frontend/src/views/PurchaseOrderPage.test.js`

临时解决方式：保留库存分支的 `PurchaseSkuReference`、当前 SKU 和库存参考渲染，同时保留 MOQ 分支的实时 MOQ 提醒、例外确认相关渲染和两组测试。解决后通过 `git diff --check` 及未解决冲突标记检查。

临时冲突处理没有回写正式分支，也没有提交临时合并代码到远端。

## 联合行为核对

在同一采购编辑流程中验证了：库存参考和 MOQ 提醒同时出现；SKU A/B 切换后两项信息跟随当前 SKU；同一来源按基础数量计算；采购数量 12、MOQ 100、差额 88 的提醒正确显示；取消 B 选择后原数量仍为 12；保存/采购数量没有被库存参考自动改写。

迁移图能够同时解析两分支现有代码中的 `0076 → 0077 → 0078_purchase_moq_exceptions` 路径。库存分支本身不包含 SKU-01 的另一条 `0078_sku_cost_verification`，因此本次仅验证 INV + MOQ 两分支；SKU-01 的三分支迁移整合仍应按既有计划在正式合并前单独处理，不能在本次证据工作中擅自合并。

## 清理

临时 worktree 和临时分支在证据收集后删除；正式库存分支只保留本目录证据文件。
