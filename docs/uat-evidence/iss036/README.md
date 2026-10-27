# ISS-036 尾箱、混装箱与最小计量单位验收记录

日期：2026-10-27  
统一基线：`7951ecb8c6196f773128ad5978bfcd0a5b30c6b5`  
分支：`codex/iss-036-carton-units`  
代码提交：`31b58cd9ca971ebe4183e378a1a82e517ac7c1fe`

## 规则与审查结论

已读取用户 2026-10-24 规则包原文：`ISS-036_允许合理尾箱、不得破坏最小计量单位.md`，并审查 SKU 交易单位、采购数量、实际装箱、ISS-040 Packing List、ISS-022 MOQ 和 ISS-075 付款规则相关实现。

确认的实际缺陷只有一项：实际装箱接口以 SKU 基础单位接收数量，但对已保存的明确“不可拆分”交易单位没有执行整数倍校验。基线复现 5m 整卷以 `2.5` 装箱返回 `201`，响应中保留了 `2.50`。

最小修复位于 `ShipmentPackageSerializer`：当同一 SKU 的发货快照明确为同一不可拆分交易单位时，拒绝非整数倍数量，并返回自然中文原因。基础单位行、允许分数的交易单位、缺失或冲突的历史快照保持不限制，不凭空推断整箱约定；不自动取整、不修改订单数量、不改变采购或付款状态。

历史误报/已正确部分：基础单位 250pcs 可按 100/100/50 装为尾箱；实际装箱支持一个箱内多个 SKU；Packing List 对混装箱的箱数、重量和 CBM 只在首行计一次；前端已有递归错误展开和失败后保留输入的逻辑，本轮仅增加回归测试。未修改 ISS-022 MOQ、ISS-040 导出、ISS-075 付款计划、迁移或财务金额。

## 验收证据

- `backend-full.log`：Django 全量 `952` 通过，`15` 跳过，系统检查无问题。
- `backend-targeted.log`：采购/装箱/单位/包装及相关集成定向测试 `92` 通过。
- `frontend-vitest-effective.log`：有效 Vitest `67` 个文件、`660` 项通过。仓库中的 `detail-drawer-typography.spec.js` 是 `node:test` 文件，未将它冒充 Vitest suite；默认无过滤收集日志另存为 `frontend-vitest.log`。
- `frontend-actual-packing.log`：实际装箱组件 `25` 项通过。
- `frontend-build.log`：生产构建通过；仅有既有大 chunk 警告。
- `backend-migrate.log`、`backend-makemigrations-check.log`、`backend-migrations-applied.log`：SQLite 新库迁移至 `0089`，`makemigrations --check` 无差异。
- `ISS-036-PackingList-mixed-carton.xlsx`：实际生成的 XLSX；混装行的箱数/重量/CBM 仅首行填写，合计公式保留。
- `chrome-invalid-indivisible-roll.png`：真实 Chrome 输入 `2.5` 被拒绝，显示“不可拆分”中文提示，输入仍为 `2.5`，没有 `[object Object]`。
- `chrome-success-indivisible-roll.png`：真实 Chrome 输入 `5` 成功保存，显示已装 `5 / 发货 5 m`，状态为装箱完成。

专项场景覆盖：250pcs/100pcs 尾箱、混装箱、5m 不可拆整卷、非法小数、中文错误、失败输入保留、分批 Packing List，以及数量/物理箱数/重量/CBM 守恒。数据库金额、采购生命周期、MOQ 例外和付款规则未改写。

## 限制与延期事项

本轮使用隔离 SQLite、开发身份和本地 Chrome；未连接生产 PostgreSQL、生产代理、真实物流数据或 CI，因此不宣称生产部署验收。若同一 SKU 在一次发货中存在多个相互冲突的交易单位快照，当前按规则不强行推断限制，需后续业务确认。ISS-036 保持 `FIXED_PENDING_REVIEW`，等待独立代码、业务和视觉复审；本轮未合并 `master`、未关闭 Issue。
