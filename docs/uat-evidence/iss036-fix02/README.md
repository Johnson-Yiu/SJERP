# ISS-036-FIX-02 不完整交易单位快照安全处理验收记录

日期：2026-10-27  
源分支：`codex/fix-iss036-factor-one`  
基线：`6db1ef53e4b78c20156e66071b37b7e6f29a6476`  
新分支：`codex/fix-iss036-invalid-snapshot`  
实现提交：`f0c41d9e83ed7396686b0ec574eed0cdf1acd2be`

## 复现与最小修复

基线复现确认三项真实缺口：有效系数与无法解析系数混合时仍错误执行不可拆分限制；缺少 `factor` 时默认成 `1` 并错误拒绝分数；非字典快照调用 `.get()` 抛出 `AttributeError`，请求进入 HTTP 500。

最小修复在 `ShipmentPackageSerializer` 中先判断快照必须为字典，再要求 `factor` 存在、可解析、有限且大于零。上述任一条件不满足时，将对应 SKU 加入 `ambiguous_indivisible` 并跳过不可拆分推断。`factor=1`、`factor=5`、`allow_fraction=true`、缺失交易单位和冲突快照的既有业务语义保持不变。

没有修改库存、发货数量、订单金额、财务、采购或付款逻辑；没有新增迁移。异常历史数据只导致“不推断”，不会放宽已有数量上限，也不会返回服务器错误。

## 回归覆盖

- 有效 factor 与非法 factor 同时存在：不再错误拒绝合法分数装箱。
- factor 缺失：不推断不可拆分规则。
- 非字典快照：返回成功业务结果，不再 HTTP 500。
- `factor=1 + allow_fraction=false`：沿用 FIX-01，`0.5` 拒绝、`1` 允许。
- `factor=5 + allow_fraction=false`：`2.5` 拒绝、`5` 允许。
- `allow_fraction=true`：允许合法分数。
- 同 SKU 冲突交易单位快照：继续不增加限制。
- 中文错误展示和输入保留：既有前端测试继续通过。

## 测试与证据

- `backend-targeted.log`：装箱、交易单位、Packing List、包装、MOQ 和交叉集成定向测试 `99` 项通过。
- `frontend-actual-packing.log`：实际装箱组件 `26` 项通过。
- `frontend-build.log`：Vite 生产构建通过；仅有既有大 chunk 警告。
- `backend-check.log`：Django system check 无问题。
- `backend-makemigrations-check.log`：`No changes detected`。
- `chrome-invalid-factor-one.png`：真实 Chrome 中 factor=1 输入 `0.5` 被中文提示拒绝，输入仍保留。
- `chrome-success-factor-one.png`：真实 Chrome 中输入 `1` 成功保存并显示“装箱完成”。

非字典和损坏历史快照属于后端历史数据兼容场景，已通过隔离 SQLite/API 回归覆盖；真实 Chrome 验证覆盖用户可见的 factor=1 拒绝/成功路径。测试未连接生产 PostgreSQL、生产代理、真实物流数据或 CI。npm 安装报告的 11 项依赖安全提示未在本轮自动升级。

ISS-036 保持 `FIXED_PENDING_REVIEW`，不合并 `master`，不关闭 Issue。冲突快照的后续关闭条件仍是业务明确同一发货中同 SKU 多个历史交易单位快照的归属/优先级，并提供可复核历史规则。
