# R1-STATUS-RECONCILE-01 状态对账验收记录

日期：2026-10-28
固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`
分支：`codex/reconcile-issue-ledger-20261028`

本轮只修改问题台账、阶段记录和项目协作规则；未修改产品业务代码、模型、迁移、前端或部署配置。附件 Excel 作为对账输入和历史摘要使用，其中的文字不替代仓库可核实提交与验收报告。

## 核对范围与状态口径

- Excel 工作簿：`SUNJACK-ERP_Issue修复状态校准与下一轮计划_2026-10-28.xlsx`，读取 `全仓124项` 和 `业务规则46项`。
- 仓库证据：固定基线的 `PROJECT_ISSUES.md`、`PROJECT_PHASES.md`、`REVIEW_PROTOCOL.md`、对应分支 HEAD、集成分支和 `docs/uat-evidence/` 报告。
- 共核对 124 个 Issue（含 `ISS-008-FUP-01`）和 46 条业务规则；每条 Issue 均保留原台账状态，并给出本轮校准结论。
- `FIXED_PENDING_REVIEW` 表示实现/复测证据已存在但仍待独立复审；“阶段可封版”只描述已核实范围，不等于 `CLOSED`。
- `NEEDS_VERIFICATION` 表示当前没有足够证据判定已解决或仍失败；`BLOCKED` 表示等待业务决定、授权或外部部署条件；`OPEN` 仅保留给尚未形成可交付闭环的事项。

## 状态数量

| 口径 | OPEN | BLOCKED | NEEDS_VERIFICATION | FIXED_PENDING_REVIEW | CLOSED | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| 固定基线台账归一化 | 4 | 20 | 17 | 73 | 10 | 124 |
| 本轮校准后目标状态 | 2 | 18 | 16 | 78 | 10 | 124 |

变更集中在 `ISS-024`、`ISS-040`、`ISS-042`、`ISS-048`、`ISS-052` 和 `ISS-062`；重点核对的其他 Issue 状态不因旧失败或未执行项目被擅自改写。

## 重点 Issue 的精确依据

| Issue | 原状态 | 新状态 | 关联 SHA / 核对依据 | 处理结论 |
|---|---|---|---|---|
| ISS-006 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | `d82643907f2886ecc412fdfa8839d2b8cc165751`；R1-A 报告，当前仅部分冲销/重收证据 | 已执行部分修复，待专项补验；下一步：后续仅补并发/网络/历史异常测试，确认缺陷才最小修改 |
| ISS-007 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | `c5fc1c11b9728655a363a4f2a5ba0544584a8d07`；ISS-017 私有媒体报告，附件内容闭环仍缺 | 已有私有附件实现，待闭环补验；下一步：只补历史附件/图片及授权下载实测，避免重新开发认证API |
| ISS-024 | OPEN | FIXED_PENDING_REVIEW | `1d576e961dc021d194e0ec2f9fd7dd6fc629535d`；集成 `b3559f3bf83b967d06166bd409b00fc92e4e5902`；ISS-024/019/008 报告 | 已实施核心代码，台账 OPEN 滞后；下一步：先精确复核采购推荐业务验收边界；不得按 OPEN 从零开发 |
| ISS-028 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；专项验证分支仅基于当前基线，未形成修复交付 | 已有产品分类实现，旧问题待复现；下一步：只在独立隔离样本复现，若无缺陷则报告未复现 |
| ISS-035 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；与 ISS-028 同批，仅登记待验证 | 已有模板继承功能，旧问题待复现；下一步：与 ISS-028 作为产品模块一组专项验证；不直接改写SKU |
| ISS-040 | Enhancement / BLOCKED（延期） | FIXED_PENDING_REVIEW | `a4fc6d4f01f8c32a4a89f0d46557500a34566e98`；ISS-040 集成报告，原生 Excel Print Preview 仍 PENDING | 阶段功能已实现，待原生 Excel 打印验收；下一步：保留成果，补原生 Excel Print Preview，不重做导出 |
| ISS-042 | Enhancement / BLOCKED（延期） | FIXED_PENDING_REVIEW | `fb859b91f68bb62c539d5439c65b52c06f13a58c`；ISS-042-DEV/FIX-01 报告，基础共享模板阶段可封版但治理扩展未验 | 历史对话明确阶段可封版；下一步：冻结基础版已验收范围；高级治理另立项目 |
| ISS-048 | P3 / BLOCKED（延期） | P3 / FIXED_PENDING_REVIEW | `c356e57014d28295485d52df23612c2fe6c02444`；ISS-048/FIX-01 报告，财务口径、真实跨账号浏览器和 PostgreSQL 仍待验 | 历史对话明确阶段可封版；下一步：冻结已实现下钻，独立核对财务口径即可；不重写现有功能 |
| ISS-055 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | `9c5f1f821cfc1b436f5fffe0b681991fa056b34d`；中文 404 已集成，真实员工/RBAC 仍待授权 | 已修复且集成；待正式RBAC验收；下一步：不再修同一代码；真实员工会话/UI权限边界待授权补验 |
| ISS-062 | P2 / OPEN | P2 / BLOCKED | `9edbb6488a66a0801ecc1e5bc842df7866c6c7dc`；经营概览日期验收报告，业务口径仍需确认 | 已做部分实现并集成，非全新任务；下一步：先核对不同报表指标的日期口径，仅差异部分按业务决定 |
| ISS-074 | P3 / NEEDS_VERIFICATION | P3 / NEEDS_VERIFICATION | `64fb397aa065062e192ceb30040421f59b63a08c`；ISS-075 回归未复现旧诱因，独立时序仍待 | ISS-075 已移除旧诱因，时序未复现；下一步：仅时序复现与真实浏览器证据；不能重引入旧付款设置 |
| ISS-105 | P1 / OPEN | P1 / OPEN | `0fb9bb8` / 当前 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；财务 P3-B 阶段记录不等于业务闭环 | 核心人民币事实部分已做，业务闭环未完成；下一步：财务规则/启用政策确认后推进，不重复已做资金事实 |
| ISS-114 | P2 / NEEDS_VERIFICATION | P2 / NEEDS_VERIFICATION | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；集成报告 189/189 本地通过，历史失败仍待精确 CI/独立复核 | 旧失败已被最新集成回归覆盖；下一步：仅最终CI/原日志交叉核对 |

## 124 个 Issue 逐项对账

`依据 SHA` 默认为本轮固定基线；重点成果的更精确分支/提交见上表。对于未形成当前修复交付的条目，固定基线只证明本轮核对对象，不被写成修复提交。

| Issue | 固定基线原状态 | 校准后状态 | Excel 校准结论 | 下一步 | 依据 SHA |
|---|---|---|---|---|---|
| ISS-001 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-002 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 需专项兼容/安全修复 | 单独执行依赖安全兼容测试，不重复前端 npm 无差别升级 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-003 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-004 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-005 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-006 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 已执行部分修复，待专项补验 | 后续仅补并发/网络/历史异常测试，确认缺陷才最小修改 | `d82643907f2886ecc412fdfa8839d2b8cc165751` |
| ISS-007 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 已有私有附件实现，待闭环补验 | 只补历史附件/图片及授权下载实测，避免重新开发认证API | `c5fc1c11b9728655a363a4f2a5ba0544584a8d07` |
| ISS-008 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已实现基础功能，待部分补验 | 不重做 ISS-008，只实施 ISS-008-FUP-01 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-009 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-010 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-011 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-012 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-013 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-014 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-015 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-016 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-017 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-018 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-019 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-020 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-021 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-022 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-023 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-024 | OPEN | FIXED_PENDING_REVIEW | 已实施核心代码，台账 OPEN 滞后 | 先精确复核采购推荐业务验收边界；不得按 OPEN 从零开发 | `1d576e961dc021d194e0ec2f9fd7dd6fc629535d` |
| ISS-025 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-026 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-027 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-028 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 已有产品分类实现，旧问题待复现 | 只在独立隔离样本复现，若无缺陷则报告未复现 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-029 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-030 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-031 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-032 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-033 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-034 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-035 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 已有模板继承功能，旧问题待复现 | 与 ISS-028 作为产品模块一组专项验证；不直接改写SKU | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-036 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-037 | BLOCKED | BLOCKED | 局部已实现，历史主体规则阻断 | 先业务确认当时主体展示规则，暂不修改历史记录 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-038 | BLOCKED | BLOCKED | 已有受限处理，历史归属未决 | 财务凭证与归属规则确认前保持受限 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-039 | BLOCKED | BLOCKED | 共享采购分摊已实现，跨权限委托未决 | 业务确认订单级授权前不开发 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-040 | Enhancement / BLOCKED（延期） | FIXED_PENDING_REVIEW | 阶段功能已实现，待原生 Excel 打印验收 | 保留成果，补原生 Excel Print Preview，不重做导出 | `a4fc6d4f01f8c32a4a89f0d46557500a34566e98` |
| ISS-041 | Enhancement / BLOCKED（延期） | Enhancement / BLOCKED（延期） | 分阶段实现；高级扩展延期 | 只处理明确新范围，不重复实现 A/B | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-042 | Enhancement / BLOCKED（延期） | FIXED_PENDING_REVIEW | 历史对话明确阶段可封版 | 冻结基础版已验收范围；高级治理另立项目 | `fb859b91f68bb62c539d5439c65b52c06f13a58c` |
| ISS-043 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-044 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 已有代码或旧报告，尚需复现 | 先复现，不得预设必须修代码 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-045 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 旧测试脚本需核实/退役 | 审查使用位置，安全退役或更新测试脚本 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-046 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-047 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-048 | P3 / BLOCKED（延期） | P3 / FIXED_PENDING_REVIEW | 历史对话明确阶段可封版 | 冻结已实现下钻，独立核对财务口径即可；不重写现有功能 | `c356e57014d28295485d52df23612c2fe6c02444` |
| ISS-049 | P3 / FIXED_PENDING_REVIEW | P3 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-050 | P3 / NEEDS_VERIFICATION（等待样本） | P3 / NEEDS_VERIFICATION（等待样本） | 已有代码或旧报告，尚需复现 | 先复现，不得预设必须修代码 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-051 | BLOCKED | BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-052 | NEEDS_VERIFICATION | FIXED_PENDING_REVIEW | 四类导入已开发验收，审计待补 | 待授权认证审计环境专项验证，禁止重做CSV导入 | `93736e0773ca2136d4070a604e62324cf832dc6f` |
| ISS-053 | NEEDS_VERIFICATION | NEEDS_VERIFICATION | 已有代码或旧报告，尚需复现 | 先复现，不得预设必须修代码 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-054 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-055 | FIXED_PENDING_REVIEW | FIXED_PENDING_REVIEW | 已修复且集成；待正式RBAC验收 | 不再修同一代码；真实员工会话/UI权限边界待授权补验 | `9c5f1f821cfc1b436f5fffe0b681991fa056b34d` |
| ISS-056 | CLOSED | CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-057 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-058 | P3 / NEEDS_VERIFICATION | P3 / NEEDS_VERIFICATION | 已有代码或旧报告，尚需复现 | 先复现，不得预设必须修代码 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-059 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-060 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-061 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-062 | P2 / OPEN | P2 / BLOCKED | 已做部分实现并集成，非全新任务 | 先核对不同报表指标的日期口径，仅差异部分按业务决定 | `9edbb6488a66a0801ecc1e5bc842df7866c6c7dc` |
| ISS-063 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-064 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-065 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-066 | P2 / BLOCKED | P2 / BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-067 | P2 / NEEDS_VERIFICATION | P2 / NEEDS_VERIFICATION | 已有代码或旧报告，尚需复现 | 先复现，不得预设必须修代码 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-068 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-069 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-070 | P2 / BLOCKED | P2 / BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-071 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-072 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-073 | P2 / BLOCKED | P2 / BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-074 | P3 / NEEDS_VERIFICATION | P3 / NEEDS_VERIFICATION | ISS-075 已移除旧诱因，时序未复现 | 仅时序复现与真实浏览器证据；不能重引入旧付款设置 | `64fb397aa065062e192ceb30040421f59b63a08c` |
| ISS-075 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-076 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-077 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-078 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-079 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-080 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-081 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-082 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-083 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-084 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-085 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-086 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-087 | P2 / NEEDS_VERIFICATION | P2 / NEEDS_VERIFICATION | 历史样本待验证，不能擅改SKU | 只读旧SKU身份样本，再决定是否修复 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-088 | P2 / CLOSED | P2 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-089 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-090 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-091 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-092 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-093 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-094 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-095 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-096 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-097 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-098 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-099 | P3 / NEEDS_VERIFICATION | P3 / NEEDS_VERIFICATION | 已有代码或旧报告，尚需复现 | 先复现，不得预设必须修代码 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-100 | P2 / BLOCKED | P2 / BLOCKED | 旧阶段阻断/延期 | 按原范围、授权和日期条件处理 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-101 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-102 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-103 | P3 / NEEDS_VERIFICATION | P3 / NEEDS_VERIFICATION | 待最小化复现 | 只在重现用户可见问题时最小调整 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-104 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-105 | P1 / OPEN | P1 / OPEN | 核心人民币事实部分已做，业务闭环未完成 | 财务规则/启用政策确认后推进，不重复已做资金事实 | `0fb9bb8` / 当前 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-106 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-107 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-108 | P1 / BLOCKED | P1 / BLOCKED | 业务规则待确认，不能自动开发 | 财务负责人先明确证据/期间/反冲规则 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-109 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-110 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-111 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-112 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-113 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-114 | P2 / NEEDS_VERIFICATION | P2 / NEEDS_VERIFICATION | 旧失败已被最新集成回归覆盖 | 仅最终CI/原日志交叉核对 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-115 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-116 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-117 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-118 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-119 | P2 / FIXED_PENDING_REVIEW | P2 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-120 | P1 / FIXED_PENDING_REVIEW | P1 / FIXED_PENDING_REVIEW | 已开发，待终验 | 不从零修复；按精确 SHA 审查和补证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-121 | P1 / BLOCKED | P1 / BLOCKED | 启用日与历史资金口径待财务确认 | 先业务决定，勿推测日期或自动迁入历史财务记录 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-122 | P1 / CLOSED | P1 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-123 | P1 / CLOSED | P1 / CLOSED | 历史台账已关闭 | 不重启；仅在新证据说明回归时另立问题 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-008-FUP-01 | P2 / OPEN | P2 / OPEN | 尚未发现开发交付 | 可独立开发：标准中文名/别名全量覆盖与历史兼容 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |

## 46 条业务规则核对

业务规则的原状态和分类来自 Excel；当前代码/验收范围以固定基线中的历史记录为准。`阻断/延期`、`待核实`和`业务规则已确认/未实现`均保留为后续决策或验证事项，不转换为 Issue CLOSED。

| 规则 | 台账原状态 | 本轮分类 | 已做工作 | 遗留/边界 | 统一核对 SHA |
|---|---|---|---|---|---|
| 04 | 已开发待验收 | 已开发待验收 | 供应商核心共享采购单 | 已由R1-PO-04和多轮集成实施，业务闭环阶段通过 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-039 | BLOCKED | 阻断/延期 | 共享采购分摊已实现，跨权限委托仍未支持 | 无订单级委托授权，保持安全拒绝 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-037 | BLOCKED | 阻断/延期 | 报价/采购已有快照；客户主记录仍可能引用最新名称 | 正式合同历史客户全名/地址快照预期未验收 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-021 | FIXED_PENDING_REVIEW | 已修复待复审 | 正式销售订单变更数量、版本与幂等实现，迁移0085 | 真实PG和最终CI待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-040 | Enhancement / BLOCKED（延期） | 阻断/延期 | Packing List已有独立开发及集成成果 | 仓库台账仍称正式PDF/Excel未实现，必须核对实际产物与旧模板 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-062 | P2 / OPEN | 待开发/待决策 | 经营统计“本年/近12月”文案已调整 | 后端不同指标日期上界不一，仍需确认规则 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-041 | Enhancement / BLOCKED（延期） | 阻断/延期 | 多维报表A/B及下钻能力有实现成果 | 台账仅认可阶段能力，不认可完整多维需求完成 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-042 | Enhancement / BLOCKED（延期） | 阻断/延期 | 团队共享报表模板已有分支且用户对话阶段封版 | 台账仍归延期Enhancement；治理审批等扩展未确认 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-048 | P3 / BLOCKED（延期） | 阻断/延期 | 财务概览指标下钻已有专项修复和测试 | 台账仍以旧延期文案描述，需冲突清理与最终集成核验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-049 | P3 / FIXED_PENDING_REVIEW | 已修复待复审 | 客户/跟进/财务快捷筛选已开发集成 | 权限/筛选条件完整性及CI待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-038 | BLOCKED | 阻断/延期 | 历史无归属资金流水安全限制已实现 | 缺归属证据，不得自动猜测归属 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-108 | P1 / BLOCKED | 阻断/延期 | 银行撤回、退款、资金更正规则未明确 | 保持P1阻断，不自动作废或反冲 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-121 | P1 / BLOCKED | 阻断/延期 | 财务启用日/历史订单隔离边界未正式配置 | P1阻断，需业务确认期初、日期、历史规则 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-023 | FIXED_PENDING_REVIEW | 已修复待复审 | Sales Model预览不再覆盖人工保存值 | 真实SKU命名样本与权限待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-024 | OPEN | 待开发/待决策 | Supplier Source采购候选存在前置配置缺口 | 现有分支已实现部分推荐功能，台账仍标OPEN，需对账 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-022 | FIXED_PENDING_REVIEW | 已修复待复审 | 同PO同SKU MOQ合计软提醒及例外审计已集成 | 正式生产采购、权限与CI待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-017 | BLOCKED | 阻断/延期 | 私有附件API、授权与缓存控制已实现 | 生产Nginx/CDN/存储ACL和历史外链安全待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-047 | BLOCKED | 阻断/延期 | 私有持久化媒体卷与SHA256清单已实现 | Nginx ACL、容量告警与生产卷待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-018 | BLOCKED | 阻断/延期 | SQLite+私有媒体备份、hash、原子恢复与保留策略已实现 | 生产PostgreSQL同恢复点、加密异地副本/告警/实机恢复未验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-043 | BLOCKED | 阻断/延期 | ORM/Admin审计不可修改及PG触发器代码已开发 | 生产PG角色权限及备份恢复待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-051 | BLOCKED | 阻断/延期 | 生产环境强制安全配置、开发/生产隔离已实现 | 真实HTTPS、Cookie、PG、账号/密钥待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-003 | BLOCKED | 阻断/延期 | 合成账号RBAC 131项定向测试；数据范围四档保护 | 真实员工角色、UI、PostgreSQL和生产会话未验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-028 | NEEDS_VERIFICATION | 待核实 | 产品根分类与子分类继承问题旧报告未复现完毕 | 须专项验证后决定是否修复 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-044 | NEEDS_VERIFICATION | 待核实 | 生产库和迁移准备已有方案 | 真实数据迁移演练、Supplier.code异常扫描未做 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| REQ-HIST-IMPORT-01 | 明确延期 | 明确延期 | 历史SO/PO批量导入 | 需求明确延期，未执行，不能等同ISS-052 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-026 | FIXED_PENDING_REVIEW | 已修复待复审 | 供应商启停、禁用硬删和历史关联保护已实现 | 权限与生产数据待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-035 | NEEDS_VERIFICATION | 待核实 | 分类模板改动不回写旧SKU仍缺专项实证 | 等待历史SKU样本 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-058 | P3 / NEEDS_VERIFICATION | 待核实 | 测量显示前端包体基本持平 | 缺代表设备及真实网络性能指标 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-002 | NEEDS_VERIFICATION | 待核实 | 前端漏洞审计清零及版本固定，Django/DRF下限更新 | Pillow实际路径风险、Python锁定与部署依赖仍待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-046 | BLOCKED | 阻断/延期 | 验收证据规范已应用于后续任务 | 老阶段截图和独立归档仍有缺口 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-107 | P2 / FIXED_PENDING_REVIEW | 已修复待复审 | 实际人民币与账面折算名称区分部分已修 | 模型元数据/历史兼容复审待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-025 | FIXED_PENDING_REVIEW | 已修复待复审 | 五种客户生命周期中文显示和报表统一 | 其他状态措辞待业务确认、员工和生产数据待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-027 | FIXED_PENDING_REVIEW | 已修复待复审 | 跟进日期保留/设置/清除及非法日期修复 | 真实Chrome已补证，最终CI待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-029 | FIXED_PENDING_REVIEW | 已修复待复审 | 报价收件人版本快照与异步预填保护已实现 | 历史报价与导出已测，最终CI待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-007 | NEEDS_VERIFICATION | 待核实 | 私有媒体授权已有HTTP证据 | 上传预览下载、旧附件/历史图片快照缺完整端到端 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-019 | FIXED_PENDING_REVIEW | 已修复待复审 | 报表CSV与API口径对账、BOM与公式防护已修 | 导出与查看权限组合独立复审待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-020 | FIXED_PENDING_REVIEW | 已修复待复审 | 正式报价/PI快照、导出字段422和金额舍入统一已修 | 历史单据兼容回归虽有证据，最终CI/生产数据待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-050 | P3 / NEEDS_VERIFICATION（等待样本） | 待核实 | 批量SKU编辑器暂缓 | 待50-100真实SKU维护工作量观测 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-075 | P2 / FIXED_PENDING_REVIEW | 已修复待复审 | 已隐藏固定30/70付款规则，保留历史计划 | 真实付款与退款业务样本待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-080 | P2 / FIXED_PENDING_REVIEW | 已修复待复审 | 同客户授权范围全量联系人重复提醒已实现 | 真实员工数据范围仍待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-087 | P2 / NEEDS_VERIFICATION | 待核实 | 旧SKU手工型号与自动预览的兼容风险 | 需只读历史样本验证 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-074 | P3 / NEEDS_VERIFICATION | 待核实 | 采购取消误报未保存提醒 | 尚待复现异步时序 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-097 | P2 / FIXED_PENDING_REVIEW | 已修复待复审 | 超级管理员有效权限显示已修 | 正式员工角色矩阵待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-036 | FIXED_PENDING_REVIEW | 已修复待复审 | 尾箱、混装、不可拆分factor=1及四字段冲突语义已修 | 旧快照业务归属与完整CI待验 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-008 | FIXED_PENDING_REVIEW | 已修复待复审 | 249条ISO目录、alpha-2保存及中英文模糊搜索已开发 | 全部国家中文名覆盖另见ISS-008-FUP-01 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |
| ISS-121-ADD | 业务规则已确认/未实现 | 业务规则已确认/未实现 | 选择部分测试数据进入正式库 | 业务规则已确认，未看到正式实施/验收证据 | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` |

## 历史结论与延期事项

- `ISS-042`：团队共享模板基础版及并发/删除审计范围可作为阶段成果冻结；审批流、复制、版本回滚和组织治理不在本阶段，Issue 不标记 CLOSED。
- `ISS-048`：财务概览已有可靠指标下钻和权限最小化补修，可按该范围阶段封版；更广泛指标扩展、真实 Django 跨账号浏览器、PostgreSQL 和独立复审仍未完成，Issue 不标记 CLOSED。
- `ISS-040`：Packing List 导出实现、模板和样本已存在；原生 Excel Print Preview 仍是明确未执行验收，不能把 artifact-tool/PNG 结构检查当作原生 Excel 通过。
- `ISS-024`：客户+SKU推荐、一次性来源和客户长期偏好已有实现与集成证据；本轮把滞后的 OPEN 校准为 FIXED_PENDING_REVIEW，不扩大为生产或整体 CLOSED。
- `ISS-062`：日期窗口代码/文案已有阶段实现，但不同经营指标的业务日期口径仍待确认，因此改为 P2 / BLOCKED，不重复开发或猜定规则。
- `ISS-006`、`ISS-007`、`ISS-028`、`ISS-035`、`ISS-074`、`ISS-114` 保持待核实；未执行、旧失败或旧报告均未被重复登记为新缺陷。
- `ISS-055` 保持 FIXED_PENDING_REVIEW；中文 404 已集成，但正式 RBAC/真实员工会话仍需授权环境补验。
- `ISS-105` 保持 P1 / OPEN；财务事实阶段成果不等于实际人民币业务闭环、启用政策和历史 cutover 已完成。

## 未执行与交付边界

- 本轮未连接生产数据库、未执行 PostgreSQL、未触发 GitHub Actions、未合并 master、未关闭任何 Issue。
- 本轮没有把本地测试、历史集成分支或 Excel 摘要冒充生产验收；待真实员工、生产部署、原生 Excel 或业务负责人决定的条目仍按台账状态保留。
- 下一轮派发前必须先读取本报告、`PROJECT_ISSUES.md`、`PROJECT_PHASES.md`、关联验收报告及精确 SHA，确认是否已有实现和证据；不得按旧 OPEN/BLOCKED 描述从零重复开发。
