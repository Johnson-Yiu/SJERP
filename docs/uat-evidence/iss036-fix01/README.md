# ISS-036-FIX-01 不可拆分单位系数边界验收记录

日期：2026-10-27  
源分支：`codex/iss-036-carton-units`  
基线：`3fe05aa1fe08f859cd6b737150d67b4c1066b248`  
新分支：`codex/fix-iss036-factor-one`  
实现提交：`a59573e0396fbb6b324628d8826b5a2234ee065b`

## 结论

复核确认原实现把 `factor=1` 当作歧义快照并跳过校验。对于明确交易单位、`factor=1`、`allow_fraction=false` 的快照，这会错误接受 `0.5`。本轮只移除这一处特殊跳过条件；其余“快照不足不推断”和“冲突快照不增加限制”逻辑保持不变。

校验仍只针对实际装箱数量，数据库中的库存、发货数量、订单金额、财务金额、采购状态和付款规则均未改变。没有新增迁移，也没有改动尾箱、混装箱或 Packing List 汇总逻辑。

## 边界覆盖

- 明确 `factor=1`、`allow_fraction=false`：`0.5` 返回 400 和中文“数量必须是其整数倍”，`1` 返回 201。
- 明确 `factor=5`、`allow_fraction=false`：`2.5` 拒绝，`5` 允许；原有混装箱回归保留。
- `allow_fraction=true`：合法 `2.5` 仍允许。
- 无交易单位、缺少历史快照：不推断不可拆分规则，合法分数仍允许。
- 同一 SKU 出现不同系数历史快照：不擅自增加限制，分数装箱仍允许。
- 前端错误展示：factor=1 错误为自然中文，输入 `0.5` 保留，未出现 `[object Object]`。

冲突快照边界的关闭条件：业务明确同一发货中同 SKU 多个历史交易单位快照的归属/优先级，并提供可复核的历史数据规则后，另行设计针对性校验；在此之前继续保持不推断、不新增限制。

## 测试与真实 UI 证据

- `backend-targeted.log`：装箱、交易单位、Packing List、包装、MOQ 与交叉集成定向测试 `96` 项通过。
- `frontend-actual-packing.log`：实际装箱组件 `26` 项通过。
- `frontend-build.log`：Vite 生产构建通过；仅有既有大 chunk 警告。
- `backend-check.log`：Django system check 无问题。
- `backend-makemigrations-check.log`：`No changes detected`。
- `chrome-invalid-factor-one.png`：真实 Chrome 中输入 `0.5` 被拒绝，中文提示可见且输入保留。
- `chrome-success-factor-one.png`：真实 Chrome 中输入 `1` 保存成功，显示“装箱完成”和“已装 1 / 发货 1 pcs”。

测试使用本 Worktree 的隔离 SQLite、开发身份和本地 Chrome；没有连接生产 PostgreSQL、生产代理、真实物流数据或 CI。npm 安装仅用于本地回归，报告的依赖安全提示未执行自动升级。

ISS-036 保持 `FIXED_PENDING_REVIEW`，等待独立代码、业务和视觉复审；本轮不合并 `master`、不关闭 Issue。
