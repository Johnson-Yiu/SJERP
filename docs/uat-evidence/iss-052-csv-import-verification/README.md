# ISS-052 CSV 导入独立验收报告

## 结论

客户、产品、SKU、财务流水四类 CSV 导入均完成了真实本地 UI 的上传、预览、确认执行和数据库核对。成功路径均可用；预览不会写入业务数据，失败预览不会产生执行凭证，执行阶段的数据状态冲突会拒绝写入，财务流水不会覆盖已有流水号。

本次实际复现并修复 1 个缺陷：SKU 引用不存在的 `product_code` 时，HTTP API 原始错误曾直接返回 `Product matching query does not exist.`，而前端另行翻译成中文，导致 API 与 UI 错误契约不一致。修复仅增加 `Product.DoesNotExist` 的稳定中文错误映射，并增加回归测试；没有修改导入业务规则、权限设置、数据库结构或历史订单逻辑。

开发身份的持久化审计在本次环境中不可用，见“审计缺口”。

## 范围与排除项

- 基线：`46353a5436637832f5adadb7bdef6b45cdeada23`
- 分支：`codex/verify-iss052-csv-import`
- 范围：`customers`、`products`、`skus`、`transactions`
- 明确排除：历史销售订单/采购订单批量导入（`REQ-HIST-IMPORT-01` 不属于本任务）
- 本地执行，未合并 `master`、未关闭 Issue、未连接用户业务库、未启用正式 RBAC

## 隔离环境

后端使用基线工作树代码，SQLite 使用单独文件：

```text
C:\Users\Johnson\.codex\worktrees\iss052-csv-import\森爵照明管理系统
C:\Users\Johnson\.codex\visualizations\2026\10\27\01a17c27-46e2-7012-887d-510445a37440\iss052-db\iss052.sqlite3
```

本地服务端口：后端 `8101`，真实 Chrome UI `5192`。Vite 因托管工作树目录权限需要写临时缓存，前端源码复制到同一临时目录运行；复制内容来自上述基线，没有前端代码修改。

启动配置：`APP_STAGE=development`、`DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`、`AUDIT_LOG_ENABLED=false`。数据库从零执行完整迁移后，只建立以下合成基线资料：

| 类型 | 编号 | 初始资料 |
|---|---|---|
| 客户 | `CUST-OLD` | `历史客户`，备注 `不可覆盖备注` |
| 产品分类 | — | `灯具` |
| 产品 | `PRD-OLD` | `历史产品`，状态 `active` |
| SKU | `SKU-OLD` | 产品 `PRD-OLD`，规格 `历史规格`，成本价 `5`，售价 `10` |

初始没有订单、采购单或库存流水。所有导入文件均使用 `ISS052` 前缀的合成编号。

## 测试数据

有效文件：

| 文件 | 行数 | 预期 |
|---|---:|---|
| `customers-valid.csv` | 2 | 更新 `CUST-OLD`，新增 `CUST-NEW` |
| `products-valid-retry.csv` | 2 | 更新 `PRD-OLD`，新增 `PRD-NEW` |
| `skus-valid-retry.csv` | 2 | 更新 `SKU-OLD` 价格，新增 `SKU-NEW` |
| `transactions-valid.csv` | 1 | 新增 `ISS052-T01`，关联 `CUST-NEW`，无订单引用 |

失败与冲突文件：

| 文件 | 覆盖场景 |
|---|---|
| `customers-duplicate.csv` | 文件内 `code` 重复 |
| `products-invalid-category.csv` | 不存在的产品分类引用 |
| `products-valid.csv` | 已有 SKU 的产品修改销售型号前缀，状态冲突 |
| `skus-invalid-reference.csv` | 不存在的 `product_code` |
| `skus-invalid-type.csv` | `cost_price=not-a-number` |
| `skus-valid.csv` | 已有 SKU 的身份字段规格变更，状态冲突 |
| `transactions-duplicate.csv` | 已存在的流水号，验证不得覆盖 |
| `customers-invalid-encoding.csv` | GBK/非 UTF-8 编码 |
| `customers-mixed-invalid.csv` | 一行有效、一行缺少客户名称，验证预览原子性 |
| `customers-state-conflict.csv` | 预览后外部改变历史资料，验证执行状态冲突 |

## 真实 UI 证据

入口：`http://127.0.0.1:5192/import`。页面显示开发身份 `Johnson`，并明确显示“先校验 CSV，再确认写入；预览不会保存业务数据”。每类均按以下真实 UI 流程操作：选择类型 → 选择文件 → `预览并校验` → `确认执行导入` → 对话框 `确认导入`。

成功路径的页面原文和结果：

| 类型 | UI 预览结果 | UI 执行结果 |
|---|---|---|
| 客户 | `共 2 行，将新增 1，将更新 1，错误 0` | `导入成功：共 2 行，新增 1，更新 1` |
| 产品（重试文件） | `共 2 行，将新增 1，将更新 1，错误 0` | `导入成功：共 2 行，新增 1，更新 1` |
| SKU（重试文件） | `共 2 行，将新增 1，将更新 1，错误 0` | `导入成功：共 2 行，新增 1，更新 1` |
| 财务流水 | `共 1 行，将新增 1，将更新 0，错误 0` | `导入成功：共 1 行，新增 1，更新 0` |

状态冲突和重试的 UI 原文：

- 产品修改已有 SKU 的销售型号前缀：`该产品已有 SKU，销售型号前缀请使用预览并确认流程修改。`；重新上传 `products-valid-retry.csv`、预览后成功。
- SKU 修改已有身份规格：`检测到身份字段变化（规格顺序/内容）。请确认这是一次 SKU 身份变更；系统将保留旧版本快照。若只是批次或资料差异，请使用备注/版本信息，不要修改 SKU 身份。`；重新上传 `skus-valid-retry.csv`、预览后成功。

失败预览的 UI 原文均显示 `校验未通过，不会写入任何数据。`，包括：

- `customers-duplicate.csv`：`文件内业务主键 code 重复：ISS052-DUP（首次出现在第 2 行）。`
- `products-invalid-category.csv`：`产品分类不存在，请先建立分类。`
- `skus-invalid-reference.csv`：修复后的 UI/API 统一显示 `找不到所引用的产品，请核对 product_code。`
- `skus-invalid-type.csv`：`无效金额：not-a-number`

## HTTP 原始证据

模板接口：

```text
GET /api/import/templates/ -> 200
{"customers":["code","name","country","source","website","address","notes"],"products":["code","name","sales_model_prefix","category","description","status"],"skus":["sku","product_code","specification","unit","cost_price","default_price","currency"],"transactions":["transaction_no","transaction_date","direction","category","amount","currency","exchange_rate","customer_code","order_no","payment_method","reference","notes"]}
```

预览接口对行级校验错误返回 HTTP 200，但 `errors` 非空且不签发 `preview_token`；文件级读取错误返回 HTTP 400：

```text
customers-duplicate.csv -> 200
{"total":2,"created":1,"updated":0,"errors":[{"row":3,"message":"文件内业务主键 code 重复：ISS052-DUP（首次出现在第 2 行）。","key":"ISS052-DUP"}]}

products-invalid-category.csv -> 200
{"total":1,"created":0,"updated":0,"errors":[{"row":2,"message":"产品分类不存在，请先建立分类。","key":"ISS052-BAD-P"}]}

skus-invalid-reference.csv（修复前原始 API） -> 200
{"total":1,"created":0,"updated":0,"errors":[{"row":2,"message":"Product matching query does not exist.","key":"ISS052-BAD-S"}]}

skus-invalid-reference.csv（修复后） -> 200
{"total":1,"created":0,"updated":0,"errors":[{"row":2,"message":"找不到所引用的产品，请核对 product_code。","key":"ISS052-BAD-S"}]}

skus-invalid-type.csv -> 200
{"total":1,"created":0,"updated":0,"errors":[{"row":2,"message":"无效金额：not-a-number","key":"ISS052-BAD-T"}]}

transactions-duplicate.csv -> 200
{"total":1,"created":0,"updated":0,"errors":[{"row":2,"message":"该流水号已存在，不能通过导入覆盖财务记录。","key":"ISS052-T01"}]}

customers-invalid-encoding.csv -> 400
{"detail":"CSV 文件无法读取，请使用 UTF-8 或 UTF-8 BOM 编码。"}
```

订单导入只做了边界确认，没有创建订单或导入订单资料：

```text
POST /api/import/csv/preview/ entity=orders -> 400
{"detail":"正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。"}
```

状态冲突与重试的真实 HTTP 结果：

```text
预览 customers-state-conflict.csv -> 200
{"total":1,"created":0,"updated":1,"errors":[],"preview_token":"<signed token>"}

预览后将 CUST-OLD 改为“状态冲突前客户/状态冲突原资料”，使用旧 token 执行 -> 400
{"detail":"数据状态已发生变化，请重新预览后再导入。"}

旧 token 失败后数据库仍为“状态冲突前客户/状态冲突原资料”。
重新预览并使用新 token 执行 -> 200
{"total":1,"created":0,"updated":1}
```

## 数据库前后对比

预览成功但尚未执行时，页面显示 `校验通过，尚未写入`；混合错误行的 HTTP 预览也显示 `created=1`，但这是事务内模拟计数。实际 SQLite 核对如下：

```text
customers-mixed-invalid.csv
before_atomic_count=0
{"total":2,"created":1,"updated":0,"errors":[{"row":3,"message":"该字段不能为空。","key":"ISS052-ERROR"}]}
after_atomic_count=0
```

最终数据库记录（修复后的重试状态）：

| 表 | 记录 |
|---|---|
| 客户 | `CUST-OLD` = `状态冲突重试客户`；`CUST-NEW` = `ISS052合成客户` |
| 产品 | `PRD-OLD` = `历史产品更新`；`PRD-NEW` = `ISS052新产品`，状态 `development` |
| SKU | `SKU-OLD` 规格仍为 `历史规格`，成本价 `6.0000`、售价 `12.0000`；`SKU-NEW` 已新增 |
| 财务流水 | `ISS052-T01`，金额 `25.5000 USD`，客户 `CUST-NEW`，订单为空 |

失败或错误行没有落库：`ISS052-DUP`、`ISS052-BAD-P`、`ISS052-BAD-S`、`ISS052-BAD-T`、`ISS052-ATOMIC`、`ISS052-ERROR` 均不存在。

隔离库最终计数：`Order=0`、`PurchaseOrder=0`、`InventoryMovement=0`、`OperationLog=0`。因此本次没有复制模拟订单、库存或采购资料，也没有意外覆盖历史基线资料；只有明确确认并通过重新预览的客户、产品、SKU、财务流水记录被写入。

## 审计缺口

`GET /api/session/current-operator/` 的关键原文为：

```json
{"name":"Johnson","authenticated":false,"development_superadmin":true,"rbac_enforcement":false,"has_all_permissions":true,"data_scope":"all","audit_log_enabled":false}
```

本地配置明确使用 `AUDIT_LOG_ENABLED=false`。导入执行代码没有为 CSV 行调用 `record_operation`，隔离库 `OperationLog` 最终数量为 0。因此本报告不能提供“开发身份 + 导入批次 + 行级 before/after”的持久化审计证据；这不是本次导入数据一致性失败，但属于验收缺口。

如需补齐审计，需要在审计开启且具备真实认证操作人的专用验收环境中增加或启用导入批次审计；不应在本地开发身份上伪造正式审计人，也不应为本任务启用正式 RBAC。

## 执行命令与验证

主要命令：

```powershell
# 隔离库迁移
$env:APP_STAGE='development'
$env:DEVELOPMENT_SUPERADMIN='true'
$env:RBAC_ENFORCEMENT='false'
$env:AUDIT_LOG_ENABLED='false'
$env:DATABASE_URL='sqlite:///C:/Users/Johnson/.codex/visualizations/2026/10/27/01a17c27-46e2-7012-887d-510445a37440/iss052-db/iss052.sqlite3'
python manage.py migrate --noinput

# 后端安全导入回归测试
python manage.py test crm.tests.test_safe_csv_import crm.tests.test_dashboard_import

# 前端导入状态回归测试（临时 UI 镜像目录）
npx vitest run tests/import-preview-state.spec.js --environment jsdom
```

结果：后端 `27 tests ... OK`；前端 `1 test file / 1 test ... passed`。

## 最小修复与待验证事项

- 已完成：`Product.DoesNotExist` 映射为稳定中文错误；新增 `test_missing_sku_product_returns_stable_api_message`；重复执行后端安全导入测试，27 个全部通过。
- 未修改：导入字段、预览 token、状态冲突、原子性、财务流水只新增规则、RBAC、账单/账户设置、master、Issue。
- 待验证：审计开启环境下的导入批次和行级审计；不属于本地开发身份可确认范围。
- 当前不需要用户手动操作账户或仓库设置。若后续要求把审计缺口关闭，需要用户另行授权并提供隔离的审计开启环境。

## ISS-052-UI-EVIDENCE 补充截图

本轮继续使用真实 Chrome 页面 `http://127.0.0.1:5192/import`、当前分支代码、隔离 SQLite 和合成数据。截图由实际浏览器视口直接采集，没有使用模拟页面、手工拼图或测试日志替代。截图路径均相对于本 README。

由于隔离库已经包含前一轮的合成记录，本轮财务流水成功场景使用新的合成文件 `transactions-ui-evidence-final.csv`，避免把已存在的 `ISS052-T01`、`ISS052-T02` 和 `ISS052-T03` 重复记录误作成功结果。其他成功场景使用重新上传、预览和执行的现有合成文件。

| 截图 | 场景 | 页面可见结果 |
|---|---|---|
| [01-customers-success.png](screenshots/01-customers-success.png) | 客户导入成功，`customers-valid.csv` | `导入完成，已写入数据库`；`导入成功：共 2 行，新增 0，更新 2` |
| [02-products-success.png](screenshots/02-products-success.png) | 产品导入成功，`products-valid-retry.csv` | `导入完成，已写入数据库`；`导入成功：共 2 行，新增 0，更新 2` |
| [03-skus-success.png](screenshots/03-skus-success.png) | SKU 导入成功，`skus-valid-retry.csv` | `导入完成，已写入数据库`；`导入成功：共 2 行，新增 0，更新 2` |
| [04-transactions-success.png](screenshots/04-transactions-success.png) | 财务流水新增成功，`transactions-ui-evidence-final.csv` | `导入完成，已写入数据库`；`导入成功：共 1 行，新增 1，更新 0` |
| [05-sku-invalid-product-code.png](screenshots/05-sku-invalid-product-code.png) | SKU 引用不存在的 `product_code`，`skus-invalid-reference.csv` | `校验未通过，不会写入任何数据。`；`找不到所引用的产品，请核对 product_code。` |
| [06-stale-token-rejected.png](screenshots/06-stale-token-rejected.png) | 客户预览后隔离库记录发生变化，旧凭证执行 | `数据状态已发生变化，请重新预览后再导入。`；页面要求重新预览，未标记为完成 |
| [07-retry-success.png](screenshots/07-retry-success.png) | 重新预览后使用新凭证执行同一客户文件 | `导入完成，已写入数据库`；`导入成功：共 1 行，新增 0，更新 1` |

本补充证据不改变审计结论：当前开发环境仍为 `AUDIT_LOG_ENABLED=false`，`authenticated=false`，隔离库 `OperationLog=0`。因此审计日志缺口仍是待验收项，不能标记为已通过。
