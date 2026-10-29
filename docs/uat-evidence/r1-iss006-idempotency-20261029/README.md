# R1-ISS006-IDEMPOTENCY-01 验收报告

日期：2026-10-29
基线：`54e715bdc568b80ba624186fecd866550676cf38`
分支：`codex/fix-iss006-request-idempotency-20261029`

## 结论

采购收货和销售发货已增加服务端持久化幂等记录。相同 `Idempotency-Key` 与相同请求内容会返回第一次业务响应；同一标识复用到不同操作、对象、操作者或请求内容会返回 `409`；业务失败会回滚幂等记录和业务副作用。前端在失败或刷新后从 `sessionStorage` 复用同一标识，成功后清除并为新的独立操作生成新标识。

本地 SQLite、隔离媒体目录和真实 Chrome Use 回归已完成。PostgreSQL 并发锁语义未在本机执行，仍需 PostgreSQL 环境验收，不能以 SQLite 结果替代。

## 根因与实现

原实现只在服务层使用业务事务和行锁，没有可持久化的请求标识；视图层的审计记录也在服务事务结束后写入。因此网络响应丢失后的重提交可能创建第二条收货/发货及库存流水，且无法可靠识别并发重复请求。

本次修改：

- 新增 `crm.FulfillmentIdempotency`，唯一约束 `key`，记录操作、目标对象、操作者、规范化请求 SHA-256、状态、原始业务响应和状态码。
- 新增 `0090_fulfillment_idempotency.py`，基于 `0089_operationlog_operator_protect`。
- 将“创建幂等记录、业务服务、审计记录、保存原始响应”放入同一个外层事务；唯一键竞争使用 `select_for_update()`，成功重试返回 `Idempotent-Replay: true`。
- 缺少标识返回 `400`；请求内容或上下文不一致、已有请求仍处理中返回 `409`；没有按日期、SKU、数量、价格等业务字段自动去重。
- 收货和发货页面复用失败请求标识，成功后清除；前端存储只保存请求标识及请求指纹，不保存业务请求正文。

## 交付文件

- `backend/crm/models.py`
- `backend/crm/migrations/0090_fulfillment_idempotency.py`
- `backend/crm/services/fulfillment.py`
- `backend/crm/views.py`
- `backend/crm/tests/test_iss006_idempotency.py`
- `frontend/src/utils/fulfillmentIdempotency.js`
- `frontend/src/views/PurchaseOrderPage.vue`
- `frontend/src/components/OrderDetailModal.vue`
- 既有收货/发货回归测试已补充请求标识，避免旧测试隐式依赖无标识请求。

## 测试结果

| 范围 | 命令/结果 |
| --- | --- |
| 迁移一致性 | `python backend/manage.py makemigrations crm --check --dry-run`：`No changes detected` |
| ISS-006 后端定向 | `python backend/manage.py test crm.tests.test_iss006_idempotency --verbosity 2`：8 项，7 通过，1 项 PostgreSQL 并发在 SQLite 跳过 |
| 履约交叉回归 | `crm.tests.test_fulfillment`, `test_trade_units`, `test_contract_lifecycle`, `test_procurement_data_scope`：72 项通过 |
| CRM 全量后端 | `python backend/manage.py test crm --verbosity 1`：1005 项通过，19 项跳过；隔离 SQLite、隔离 `MEDIA_ROOT`，Django 检查无错误 |
| 前端定向 | `npx vitest run tests/order-detail-shipment-batch.spec.js tests/purchase-editor-receipt.spec.js tests/trade-finance.spec.js --environment jsdom`：35 项通过 |
| 前端单元全量 | `npm run test:unit`：169 项通过 |
| 前端生产构建 | `npm run build`：成功；仅有既有大 chunk 提示 |
| 前端 Vitest 全量尝试 | `npx vitest run --environment jsdom`：67 个文件通过、44 个文件被仓库现有 runner 混用配置拒绝（`No test suite found`，另有 Playwright 文件被 Vitest 载入）；未视为本任务通过项，已改以仓库既有 `npm run test:unit` 完成单元全量 |

新增后端测试覆盖：重复收货、重复发货、同键变更内容、不同键相同业务操作、缺失标识、失败回滚、审计只记录一次，以及 PostgreSQL 并发路径。

## HTTP、数据库及 Chrome 证据

真实 Chrome Use 在隔离 Django/Vite 环境中完成了一次销售发货，页面显示订单 `ISS006-BROWSER-SO` 为“履约：已发货”，采购与发货页显示“已发 2 pcs / 已全部发货”。Chrome Use 截图已在本任务对话中展示；截图由 CUA 以内存 PNG 返回，未被工具写入工作区文件。

隔离数据库中，发货后核对结果为：幂等记录 1 条（`operation=ship`、`status=succeeded`）、确认发货单 1 条、发货库存流水 1 条。

使用同一完整请求正文重放：HTTP `201`，响应头 `Idempotent-Replay: true`，正文仍为原始 `shipment_no`。使用同一标识但将数量从 `2` 改为 `1`：HTTP `409`，正文为“该 Idempotency-Key 已用于不同的收货或发货请求，不能复用。”原始发货和库存记录不变。原始请求及响应摘录见同目录 `http-evidence.txt`。

## 未完成或待环境验证

- 本地没有可用 PostgreSQL 服务，因此真实 PostgreSQL 唯一键竞争、行锁和并发重复请求仍为 `PENDING`；SQLite 定向测试明确跳过该项。
- 未连接、修改或部署生产环境；未触发 GitHub Actions；未创建 PR；未修改 `docs/PROJECT_ISSUES.md` 或 `docs/PROJECT_PHASES.md`。
- Chrome CUA 截图已作为对话证据展示；如审查流程要求仓库存档图片，需要在具备截图文件导出能力的浏览器运行器中补存，不应把截图内存对象伪装成文件路径。
