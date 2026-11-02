# R1-POSTGRES-SUPPLIER-FIXTURES-FULL-01

日期：2026-11-02
分支：`codex/r1-postgres-supplier-fixtures-full-20261102`
基线：本轮从 `codex/r1-postgres-test-isolation-20261102` 的 `9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2` 创建。

## 结果

已修复测试数据违反 `Supplier.code(max_length=2, unique=True)` 的问题，没有修改生产模型、生产逻辑或字段长度。

用户指定的此前已审查修复对应六文件提交 `e8e5d1199067a339d9cf6719310c9b32294b44f1`；其后文档提交 `e2e7e017a5a2675af44b47fc93650b3837971755` 不含这六个文件的代码修改。本分支按文件移植了该六文件修复，并补齐两个 ISS-006 测试模块。

另在全后端测试目录和浏览器测试 seeder 范围搜索发现 `backend/seed_iss006_frontend_storage_browser.py` 也曾按运行 ID 生成超长供应商编码。现改为从 36×36 两字符编码空间选择未占用值，优先起点由运行后缀散列确定；空间耗尽时明确失败，不截断或复用编码。

## 文件修改

- `backend/crm/tests/test_finance_drill.py`：`FIN-DRILL-S` → `FD`
- `backend/crm/tests/test_historical_orders.py`：`HIST-P-S` → `HP`
- `backend/crm/tests/test_integration_039_037_040.py`：`INT-039-037-040-S` → `I4`
- `backend/crm/tests/test_iss039_shared_purchase_costs.py`：`ISS039-S` → `C9`
- `backend/crm/tests/test_order_quantity_adjustments.py`：四个超长编码分别替换为 `Q1`、`Q2`、`Q3`、`Q4`
- `backend/crm/tests/test_purchase_moq.py`：`ISS022-S` → `M2`
- `backend/crm/tests/test_fulfillment_audit_atomicity.py`：`ISS006-AUDIT-S` → `FA`
- `backend/crm/tests/test_iss006_pre_uat.py`：`ISS006-TEST-SUPPLIER` → `I6`
- `backend/seed_iss006_frontend_storage_browser.py`：两字符未占用编码选择器，保留隔离数据库中跨运行唯一性
- `frontend/tests/sku-management.spec.js`：supplier-candidate API mock 的供应商 `code` 从 `SUP-1` 改为 `SM`（非 SupplierSKU 编码）

## 全面搜索

使用 AST 检查 `backend` 下 `test*.py`、`*_test.py`、`conftest.py` 和 `seed*browser*.py`，审计 92 个 Supplier `create` / `get_or_create` / `update_or_create` 调用点；另检查前端 supplier-candidate API fixture：

- 超过两字符的静态编码：0。
- 动态编码表达式 3 处，逐项核实：
  - `test_purchase_cost_allocation_migration.py` 的 `M{suffix}`：后缀来自每次迁移测试中递增的采购单数量，实际创建值为 `M1` 等两字符编码。
  - `test_sales_data_scope.py` 的 `U{code[-1]}`：调用参数末字符各异，结果为两字符编码。
  - ISS-006 浏览器 seeder：候选始终由两个 base-36 字符组成，创建前检查数据库唯一性。
- 测试内其他供应商编码均为不超过两字符的字面量。数据库唯一约束仍负责最终防止重复记录。
- 前端 supplier-candidate mock 现使用两字符代码 `SM`；SupplierSKU 的 `supplier_sku_code` 不属于 Supplier.code，保持原值。

## 验证

命令：

```powershell
$env:APP_STAGE = 'development'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:MEDIA_ROOT = Join-Path $env:TEMP 'r1-postgres-supplier-fixtures-full-20261102-media'
python backend/manage.py test crm.tests.test_finance_drill crm.tests.test_historical_orders crm.tests.test_integration_039_037_040 crm.tests.test_iss039_shared_purchase_costs crm.tests.test_order_quantity_adjustments crm.tests.test_purchase_moq crm.tests.test_fulfillment_audit_atomicity crm.tests.test_iss006_pre_uat --verbosity 1 --noinput
python backend/manage.py check
vitest run tests/sku-management.spec.js --environment jsdom
git diff --check
```

结果：SQLite 定向测试 `67/67 PASS`；Django system check 无问题；AST 语法解析和 Supplier 编码扫描通过；`sku-management.spec.js` Vitest `9/9 PASS`；`git diff --check` 通过。Vitest 执行器来自本机现存 node_modules，为 4.1.11，而仓库 package.json/package-lock.json 锁定 4.1.12；本轮未重装前端依赖。定向 Django 测试中的预期 HTTP 4xx 和注入审计/库存故障日志由相应负向测试产生，Django 测试进程最终退出码为 0。

本轮未运行 PostgreSQL 测试，SQLite 结果不代表 PostgreSQL 并发或部署验收。未触发 CI、未创建 PR、未合并 master、未部署。

## 提交

最终提交 SHA 将在任务交付中报告；提交信息带 `[skip ci]`，不会触发 GitHub Actions。
