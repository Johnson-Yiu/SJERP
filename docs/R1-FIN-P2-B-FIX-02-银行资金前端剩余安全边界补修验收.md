# R1-FIN-P2-B-FIX-02 银行资金前端剩余安全边界补修验收

日期：2026-10-19  
基线：`aef3425ec97b78c3a312f54010d9de60613e75a4`  
范围：只修复恢复草稿的未保存保护、来源金额与人工核实一致性、本地草稿保存安全；不修改P2-A后端资金计算、历史财务数据、核销、库存、权限策略或数据库模型。

## 1. 审查发现与处理

| Issue | 根因 | 本轮处理 | 状态 |
|---|---|---|---|
| ISS-115 | 恢复草稿时未建立新建空白基线，`useUnsavedChangesGuard` 的 baseline 仍为 `null`，直接关闭可能绕过未保存提示 | `openCreate` 在恢复前对空白新建状态调用 `formGuard.markClean()`；恢复后内容保持 dirty。取消关闭保留表单和请求键，确认放弃才清理快照；新增真实Playwright回归 | `FIXED_PENDING_REVIEW` |
| ISS-116 | 来源分配金额改变后原 `verified` 状态仍可保留，人工核实不再对应当前金额 | 金额输入立即撤销该来源核实状态，并以来源金额基线追踪深度变更；30→50必须重新核实并重新预览，后端额度/状态校验不变 | `FIXED_PENDING_REVIEW` |
| ISS-117 | 本地快照保存整个表单，缺少过期初始化清理和敏感字段边界 | 改为版本化字段白名单；不保存凭证引用、SHA256、人工核实说明；页面初始化清理过期/损坏快照；恢复后要求重新填写凭证资料；稳定请求键仍保留 | `FIXED_PENDING_REVIEW` |

ISS-105 仍为 `OPEN`，ISS-108 仍为 `BLOCKED`，ISS-109 仍为 `FIXED_PENDING_REVIEW`；本轮没有关闭历史Issue。

## 2. 真实操作矩阵

| 步骤 | 证据类型 | 结果 |
|---|---|---|
| 恢复隔离浏览器草稿并点击取消 | `REAL_UI_ACTION` | 恢复的金额和请求键保留；出现“未保存修改”对话框，选择“继续编辑”不丢数据 |
| 恢复草稿后确认放弃 | `REAL_UI_ACTION` | 仅在确认“放弃修改”后关闭并清理本地快照；再次新建生成新的请求键 |
| 来源分配30，人工核实并完成预览 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | 预览成功，来源金额和核实状态一致 |
| 将同一来源30改为50 | `REAL_UI_ACTION` | 该来源立即恢复“待核实”，旧预览消失；未重新核实时不会发送新的预览登记请求 |
| 重新核实50并预览 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | 重新预览后才允许继续登记；后端仍重新校验来源额度、币种和权限 |
| 页面初始化遇到25小时旧快照 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | 快照在页面初始化阶段清理，不恢复过期请求键 |
| 检查新快照字段 | `DATABASE_VERIFICATION`（浏览器localStorage核对） | 仅保存必要表单字段、请求键和分配金额/核实状态；不含凭证引用、SHA256、人工核实说明或登录资料 |
| 刷新/结果不明回查 | `REAL_UI_ACTION` | 稳定请求键仍沿用原值；不自动创建第二个事件 |

## 3. 代码和数据边界

- `CashEventPage.vue` 在恢复前建立空白基线，恢复内容由 guard 识别为未保存修改；`requestClose` 的取消分支不执行清理回调。
- 来源金额编辑通过 `markAllocationEdited` 和 `allocationAmountBaseline` 同步撤销人工核实；`eventPayload` 仍只发送用户明确勾选的 `verified=true`。
- 本地快照字段白名单为事件号、请求键、类型、币种、方向、日期、银行净额、手续费、受控账户标识、银行参考号、参考汇率及费用关联；凭证引用、SHA256和人工核实说明要求恢复后重新填写。
- 过期、损坏或缺少稳定请求键的快照在页面初始化和恢复读取时清理；成功登记、请求键回查、确认和明确放弃继续清理快照。
- 未修改 `RmbCashEvent`、`CashSourceAllocation`、`Transaction`、`PaymentPlan`、`AdvanceAllocation`、库存和历史金额；没有迁移和后端金额计算变更。

## 4. 自动化结果

| 检查 | 结果 | 证据 |
|---|---:|---|
| Node `npm run test:unit` | 134/134 PASS | `node-unit.log` |
| Vitest 完整 jsdom | 63文件、633/633 PASS | `vitest-full.log` |
| Vitest 交易单位 | 4/4 PASS | `vitest-trade-units.log` |
| 定向银行资金 Playwright | 7/7 PASS | `playwright-cash-events.log` |
| 完整 Playwright | 154/154 PASS | `playwright-full.log` |
| Backend SQLite | 764 PASS、13 SKIP、0 FAIL | `backend-sqlite.log` |
| Frontend Build | PASS，2003 modules | `frontend-build.log` |
| Backend PostgreSQL | 本地服务不可用；以精确HEAD CI核验 | `backend-postgresql.log` |

完整Playwright保留历史139通过/8失败日志和本轮154项日志，没有删除或跳过历史用例。完整套件中的现有Vue Transition警告为既有非阻断告警，不属于本轮资金页面修改。

## 5. 真实截图和原始证据

真实Chromium使用隔离API和合成SQLite数据生成，截图等待业务内容加载完成，覆盖1440、1280、1024视口。关键新增截图包括恢复草稿待放弃、关闭取消后的保留状态、30→50金额修改后的待核实状态、重新预览、初始化清理过期快照和确认后的只读详情。证据目录：[`docs/uat-evidence/r1-fin-p2-b-fix-02/`](uat-evidence/r1-fin-p2-b-fix-02/)。

证据分类严格区分：合成数据准备为 `FIXTURE_SETUP`；浏览器页面交互及HTTP状态为 `REAL_UI_ACTION` / `REAL_API_OBSERVATION`；localStorage字段、期限和数据库前后记录为 `DATABASE_VERIFICATION`；仅路由延迟竞态模拟保持 `MOCKED_TEST`，不作为真实数据库写入证据。

## 6. CI和遗留边界

本报告提交后的精确HEAD、Backend、Backend PostgreSQL、Frontend三项CI链接以最终交付消息和GitHub运行记录为准。ISS-115至ISS-117保持 `FIXED_PENDING_REVIEW`，等待ChatGPT独立代码和视觉复审；不自行转为 `CLOSED`。

本轮不进入P2-C、P3、正式RBAC、员工UAT或部署。结汇更正、退款来源不明及ISS-108安全拒绝边界保持原状。
