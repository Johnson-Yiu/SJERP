# SUNJACK-ERP 供应商与采购浏览器回归验收

日期：2026-10-28
基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
工作分支：`codex/repair-supplier-purchase-ux-r2`（原请求分支已在另一工作树检出；用户同意改用新分支名）

本报告只覆盖 `frontend/browser-tests/supplier-ux.spec.js`、`iss022-moq-real.spec.js`、`iss075-payment-terms-real.spec.js` 及本目录的验收证据。没有修改业务代码、付款规则、MOQ 审批、采购正式下单二次核验、历史付款计划、供应商备注规则或权限配置。未启用正式 RBAC、未部署、未触发 GitHub Actions。

## 8 项失败归因

| 失败表现 | 归类 | 核实依据与处理 |
|---|---|---|
| `supplier-ux` 在 1440 / 1280 / 1024 视口找不到 `.terms-description` | 过时测试断言 | ISS-075 已移除供应商编辑器内的固定付款规则编辑器。当前 `ResourcePage.vue` 仅保留 200 字付款备注，并明确说明“仅供沟通参考，不生成付款计划”。更新为验证备注存在、固定规则控件不存在。 |
| 创建后读取 `payment_terms_config.map` 抛出 undefined | 过时测试断言 | 当前供应商常规 UI 不提交 `payment_terms_config`。后端模型/序列化器仍保留该字段以兼容旧数据，但 `_supplier_context` 不返回固定规则摘要。更新 mock 使详情上下文匹配 API 契约，并断言创建/更新 payload 不包含该字段。 |
| 找不到供应商编辑器中的“比例 % 1” | 过时测试断言 | 比例编辑只属于采购单逐单付款阶段，不属于供应商主档。供应商测试现验证规则输入不存在；另验证新采购单初始付款阶段为空，用户显式点“新增付款阶段”后仍可编辑本单阶段。 |
| `termsMode=custom` + 第 2 页预期 1 行，实际 25 行 | 过时测试断言 | 供应商固定规则筛选已移除；现有 supplier filter 仅包含搜索和可供分类，`termsMode` 被忽略且不会发送到供应商 API。合成列表有 52 行，因此第 2 页显示 25 行是当前契约。更新为检查 25 行、无规则筛选且请求不带 `termsMode`。 |
| ISS-022 真实浏览器场景超时 | 历史根因仍无法确认；隔离复测未复现产品缺陷 | 原配置只启动 Vite，并把 `/api` 代理到固定端口 `54127`，不负责迁移、seed 或启动 Django。首次运行误连到该端口上预先存在的本地服务，故不作为验收结果。使用新的独立 SQLite、独立 API/Vite 端口后，真实采购工作流 8.8 秒通过。 |
| ISS-075 真实浏览器场景超时 | 历史根因仍无法确认；隔离复测未复现产品缺陷 | 原配置同样只启动 Vite，API `54174` 需要外部预先启动。没有收到历史超时运行的服务日志、网络追踪或迁移记录，无法把历史 120 秒超时归结为某一确切原因。独立 API/SQLite 配置下，真实浏览器流程 10.0 秒通过。 |

因此，已确认的 6 项是与 ISS-075 新产品契约冲突的测试断言；其余 2 项没有在正确准备的隔离环境中复现。不能据此断言历史 120 秒超时的精确根因，也没有证据要求修改采购业务代码。

## 隔离、API 与数据库结果

两个真实场景各自使用新的 SQLite 数据库、媒体目录、开发身份和回环端口；`APP_STAGE=development`、`DEVELOPMENT_SUPERADMIN=1`、`RBAC_ENFORCEMENT=0`。迁移均从空库执行至 `crm.0089_operationlog_operator_protect`。`/api/session/current-operator/` 返回 `development_superadmin=true`、`audit_log_enabled=false`。开发身份不是实名审计操作人；本轮不把它当作正式审计验收。

| 场景 | HTTP / 页面结果 | SQLite 前后状态 |
|---|---|---|
| ISS-022 等于 MOQ | 创建采购草稿 `201`，确认下单 `200`。 | 10 pcs 的合成 PO 最终为 `ordered`，无例外记录。 |
| ISS-022 低于 MOQ | 0.9 箱 × 10 = 9 pcs；无原因下单请求返回 `400`。取消后草稿仍在；填写“客户指定小批量试单，已确认本次需求量。”后下单返回 `200`。 | 低 MOQ PO 最终为 `ordered`，持久化例外原因为合成输入；两张 PO 均没有付款计划。 |
| ISS-075 新 PO | 创建返回 `201`，空付款快照下正式下单返回 `200`；付款视图显示暂无应付计划。 | 新 PO `payment_terms_snapshot=[]`，付款计划数为 0。供应商旧备注和两阶段兼容字段未由 UI 更新。 |
| ISS-075 历史 PO | 详情仍显示首付款、尾款。 | `ISS075-HISTORY-01` 仍为 `ordered`，快照比例 `0.50/0.50`，计划金额 `500.0000 + 500.0000`。 |

完整 API 状态记录位于 `screenshots/iss-022/browser-log.json`、`screenshots/iss-075/browser-log.json`。提交的补充原始证据位于 `logs/`：包括两次隔离运行的 Django 请求日志、迁移输出、只读数据库摘要及后端/Node 单元测试日志。`database-post-run-checks-ascii.log` 中 MOQ 例外原因使用 Unicode 转义；前端 Vitest、交易单位和构建结果在本报告中记录，原始日志保留在本地。

### 首次非隔离运行的安全说明

首次 ISS-022 运行使用了原测试固定代理端口 `54127`。该端口当时被另一已运行的本地 Django 服务占用；预期隔离 SQLite 查询为 0 张采购单，而 HTTP API 来自不同数据库。首跑在“状态筛选预期 2 行、实际 4 行”处失败，随后该 API 返回 `PO-2026-00001` 至 `PO-2026-00004` 四行。由于运行前没有对该服务数据库拍摄快照，我不能证明这四行全部由首跑新建，也没有删除或修改它们；原服务和数据库均未被我停止或清理。

我已单独向用户询问是否删除这四张记录，等待明确选择。首次运行日志保留在本地 `logs/iss022-playwright-run.log`，但因连接到含未知现存记录的服务，不纳入提交，也不作为通过证据。PowerShell 原始乱码摘要和空的启动尝试日志同样只保留在本地。正式复测改用专用端口和核验过的临时 SQLite；测试配置临时副本未纳入提交。

## 本地验证结果

| 命令 / 验证 | 结果 |
|---|---|
| `npx playwright test --config playwright.config.js browser-tests/supplier-ux.spec.js --reporter=list` | 8 passed；包含 1440 / 1280 / 1024 视口及供应商关联采购流程。 |
| `npx playwright test --config playwright.iss022.isolated.config.js` | 1 passed；MOQ 等于/低于边界、装箱换算、取消、原因留痕与窄屏。实际测试 8.8 秒。 |
| `npx playwright test --config playwright.iss075.isolated.config.js` | 1 passed；供应商 UI、空付款阶段、正式 PO、历史计划和窄屏。实际测试 10.0 秒。 |
| Django `test_purchase_moq`、`test_purchase_payment_terms`、`test_supplier_terms_display`、`test_purchase_safety` | 19 passed。测试数据库位于任务临时目录。 |
| `npm run test:unit` | 156 passed。 |
| 供应商 / 付款条件 / 采购工作台 / 采购安全 / 交易单位 Vitest 集合 | 6 个文件、42 passed。 |
| `npm run test:trade-units` | 4 passed。 |
| `npm run build` | 成功；2018 modules transformed。已有 chunk-size warning：主 JS 1,126.03 kB（gzip 393.55 kB），本轮未做性能重构。 |
| `git diff --check` | 通过。 |

原始测试配置的 `webServer` 只启动 Vite，不启动 Django；运行真实 API 场景前必须单独迁移并启动 API。验收使用的临时 Playwright/Vite 配置只改 API 和前端监听端口，复测后不纳入分支。

## 真实 Chrome 截图

所有下列 PNG 均由 Playwright 的 Chrome 通道在真实页面操作时直接保存，未拼图、重绘或后处理。`supplier-ui` 目录使用 API mock，但数据全部是本地合成数据；ISS-022 / ISS-075 截图来自隔离 SQLite 的真实 API。

| 文件 | 场景 / 结果 |
|---|---|
| [screenshots/iss-022/01-equal-moq-draft.png](screenshots/iss-022/01-equal-moq-draft.png) | 数量等于 MOQ，草稿可保存。 |
| [screenshots/iss-022/02-equal-moq-detail.png](screenshots/iss-022/02-equal-moq-detail.png) | 等于 MOQ 的采购草稿详情。 |
| [screenshots/iss-022/03-equal-moq-ordered.png](screenshots/iss-022/03-equal-moq-ordered.png) | 等于 MOQ 的采购单确认下单成功。 |
| [screenshots/iss-022/04-low-moq-conversion-warning.png](screenshots/iss-022/04-low-moq-conversion-warning.png) | 0.9 箱换算为 9 pcs，显示低于 MOQ 提醒。 |
| [screenshots/iss-022/05-low-moq-exception-dialog.png](screenshots/iss-022/05-low-moq-exception-dialog.png) | 首次确认显示 MOQ 例外原因对话框。 |
| [screenshots/iss-022/06-cancel-keeps-draft.png](screenshots/iss-022/06-cancel-keeps-draft.png) | 取消例外确认后，采购仍为草稿。 |
| [screenshots/iss-022/07-moq-exception-persisted.png](screenshots/iss-022/07-moq-exception-persisted.png) | 填写原因后下单，例外与 1 pcs 差额可查看。 |
| [screenshots/iss-022/08-ordered-filter.png](screenshots/iss-022/08-ordered-filter.png) | 已下单状态筛选。 |
| [screenshots/iss-022/09-narrow-purchase-list.png](screenshots/iss-022/09-narrow-purchase-list.png) | 700px 采购列表，无横向溢出。 |
| [screenshots/iss-075/01-supplier-list-no-fixed-rule.png](screenshots/iss-075/01-supplier-list-no-fixed-rule.png) | 供应商列表没有固定规则列或筛选。 |
| [screenshots/iss-075/02-new-po-empty-payment-terms.png](screenshots/iss-075/02-new-po-empty-payment-terms.png) | 新 PO 的付款阶段为空，可逐单协商。 |
| [screenshots/iss-075/03-history-po-payment-plan.png](screenshots/iss-075/03-history-po-payment-plan.png) | 历史 PO 两笔 500.00 计划保留。 |
| [screenshots/iss-075/04-narrow-supplier-list.png](screenshots/iss-075/04-narrow-supplier-list.png) | 700px 供应商列表，无横向溢出。 |
| [screenshots/supplier-ui/supplier-1440-list.png](screenshots/supplier-ui/supplier-1440-list.png) | 1440px 供应商列表。 |
| [screenshots/supplier-ui/supplier-1440-editor.png](screenshots/supplier-ui/supplier-1440-editor.png) | 1440px 新建供应商，仅保留备注，无固定规则编辑器。 |
| [screenshots/supplier-ui/supplier-1440-detail.png](screenshots/supplier-ui/supplier-1440-detail.png) | 1440px 供应商详情仅展示沟通备注。 |
| [screenshots/supplier-ui/supplier-1280-list.png](screenshots/supplier-ui/supplier-1280-list.png) | 1280px 供应商列表。 |
| [screenshots/supplier-ui/supplier-1280-editor.png](screenshots/supplier-ui/supplier-1280-editor.png) | 1280px 新建供应商，无固定规则控件。 |
| [screenshots/supplier-ui/supplier-1280-detail.png](screenshots/supplier-ui/supplier-1280-detail.png) | 1280px 供应商详情。 |
| [screenshots/supplier-ui/supplier-1024-list.png](screenshots/supplier-ui/supplier-1024-list.png) | 1024px 供应商列表。 |
| [screenshots/supplier-ui/supplier-1024-editor.png](screenshots/supplier-ui/supplier-1024-editor.png) | 1024px 新建供应商，无固定规则控件。 |
| [screenshots/supplier-ui/supplier-1024-detail.png](screenshots/supplier-ui/supplier-1024-detail.png) | 1024px 供应商详情。 |
| [screenshots/supplier-ui/purchase-editor-empty-terms.png](screenshots/supplier-ui/purchase-editor-empty-terms.png) | 新采购单默认无付款阶段，不继承供应商比例。 |
| [screenshots/supplier-ui/purchase-editor-explicit-term-stage.png](screenshots/supplier-ui/purchase-editor-explicit-term-stage.png) | 用户显式添加后，逐单付款阶段编辑器仍可用。 |

## 未解决与后续动作

- 两个历史 120 秒超时没有原始日志/trace，精确历史根因未确认；建议后续让 Playwright 配置显式要求独立 API readiness、迁移和 seed，避免依赖未说明的固定端口服务。
- `audit_log_enabled=false`，开发超级管理员身份没有实名操作人；本轮不把审计归属标记为通过。
- 首次非隔离 ISS-022 运行后，54127 服务返回的四张 PO 等待用户决定；未授权前不会删除。
- 没有确认的产品代码缺陷，因此未修改业务代码；MOQ 例外审批、正式下单校验、历史付款计划及供应商备注规则维持不变。
- 本轮未修改共享 `PROJECT_ISSUES.md` / `PROJECT_PHASES.md`，未合并 master、关闭 Issue、部署或触发 CI。
