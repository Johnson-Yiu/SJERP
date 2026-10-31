# R1-ISS006-INVENTORY-CHROME-UAT 验收报告

## 范围与环境

- 仓库：SUNJACK-ERP
- 基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 分支：`codex/r1-iss006-inventory-chrome-uat-20261031`
- 浏览器：桌面版 Google Chrome，真实 UI 和 HTTP 服务
- 视口：1440×1000、390×844
- 数据库：独立 SQLite `backend/iss006-chrome-uat.sqlite3`；仅使用合成 SKU、订单、采购单及合成操作人
- Django：`127.0.0.1:8127`；前端 Vite：`127.0.0.1:5237`
- 审计日志开关仅在本地隔离 UAT 服务中开启。未连接生产环境。
- 产品业务代码未修改。本分支只含隔离测试夹具、快照/截图辅助工具和验收证据。

本轮查阅 ISS-006 的历史验收台账及 R1-A 证据。此前若干业务规则已有后端或 in-app browser 证据；本轮针对真实 Chrome、浏览器交互与数据库/API 联动补证，不重跑无关的全量业务测试。

## 验收结果

| 场景 | 实际结果 | 证据 |
|---|---|---|
| 部分收货、部分冲销、重新收货 | 收货 4 + 3；冲销第二笔 3；再次收货 3。原收货及冲销流水均保留，当前有效到货 7/10，采购单为部分到货。 | `database-after-partial-reversal.json`、`database-after-rereceipt.json`；`receipt-partial-rereceived-390.jpg` |
| 重复冲销 | 对已冲销收货记录再次 POST，HTTP 400；提示“该入库记录已经冲销，不能重复操作。”前后快照完全一致：流水 4→4、操作日志 4→4。 | `api-duplicate-reversal.json`、`database-before-duplicate-reversal.json`、`database-after-duplicate-reversal.json` |
| 冲销已被销售出库消耗的采购入库 | 对已收 4、已发 4 的入库尝试冲销，HTTP 400，UI 提示“当前 SKU 实际库存不足以冲销，请先处理后续出库。”数据库前后快照完全一致：实际库存 0、预留 0、订单已发数量 4、采购状态已完成；流水 6→6、日志 6→6。 | `consumed-reversal-rejected-1440.jpg`、`database-before-consumed-reversal.json`、`database-after-consumed-reversal-rejected.json` |
| 销售发货冲销及库存恢复 | 发货 HTTP 201；冲销发货 HTTP 200。原出库流水保留并标记已冲销，另生成 +4 冲销流水；库存 0→4、预留 0→4、订单状态 shipped→confirmed、已发 4→0。 | `shipment-reversed-1440.jpg`、`shipment-reversal-inventory-ledger-1440.jpg`、`shipment-reversal-ledger-390.jpg`、`database-before-consumed-reversal.json`、`database-after-shipment-reversal.json` |
| 供应商赠品超收 | 采购数量 2，验收入库 3；明确勾选超到并选择“供应商赠品”。记录超到 1、当前有效到货 3、库存 +3，采购单进入已完成；采购金额仍为 USD 25.00。 | `gift-overreceipt-form-1440.jpg`、`gift-overreceipt-complete-1440.jpg`、`gift-overreceipt-complete-390.jpg`、最终数据库快照 |
| 手工盘盈 | 对同一合成 SKU 另建独立盘盈 +2，成本参考 8.5、独立参考号和备注；库存由赠品收货后的 3 增至 5，流水来源标记“手工登记”，没有混入采购收货记录。 | `manual-positive-adjustment-form-1440.jpg`、`manual-positive-adjustment-result-1440.jpg`、`manual-inventory-ledger-390.jpg` |
| 操作日志与历史流水 | 成功业务事件保留操作人、时间、请求路径及相应业务元数据；部分收货冲销记录了原因、原收货和冲销流水 ID。订单 UI 保留发货确认及冲销两条历史。被拒绝的两次冲销没有新增流水或操作日志。 | `shipment-operation-history-1440.jpg`、`database-after-final-scenarios.json`、`api-http.log` |

### 最终 SQLite 快照摘要

| 合成 SKU | 实际库存 | 预留 | 可用 | 在途采购 |
|---|---:|---:|---:|---:|
| `ISS006-UAT-REC` | 7 | 0 | 7 | 3 |
| `ISS006-UAT-SHIP` | 4 | 4 | 0 | 0 |
| `ISS006-UAT-GIFT` | 5 | 0 | 5 | 0 |

最终共 9 条库存流水、9 条操作日志。发货冲销后的原出库及新建恢复流水分别为 -4 和 +4，数量守恒；订单保留 4 件有效预留，故可用库存为 0。

## API 与状态一致性

`api-http.log` 区分了 Django runserver 原始 stdout 摘录和由持久化幂等记录/操作日志核实的请求。`api-duplicate-reversal.json` 保存重复冲销的 HTTP 400 响应体。所有相关请求均指向隔离 SQLite 服务。

`database-before-duplicate-reversal.json` 与 `database-after-duplicate-reversal.json`，以及 `database-before-consumed-reversal.json` 与 `database-after-consumed-reversal-rejected.json`，除快照阶段字段外逐字段一致。比较结果见 `snapshot-comparison.json`。

## 测试与检查

- 隔离数据库迁移至仓库当前最新迁移 `0092`：通过。
- `python manage.py check`：通过，0 项问题。
- `python manage.py makemigrations --check --dry-run`：通过，`No changes detected`。
- Chrome 业务流程：以上场景均按表格结果完成；关键提交 HTTP 状态和最终数据库状态交叉核验。
- 未重跑 Django 全量/专项单元测试。产品代码未修改，且历史专项测试已有记录；本任务的新增验收重点是 Chrome 真实交互和跨层状态证据。
- 390px 下长表格采用容器内横向滚动；库存页的移动端概览卡片可纵向浏览。本轮只记录现状，不改 UI。

## 环境观察及未解决项

1. 第一次收货请求因本地 Vite 来源未加入隔离服务的 `CSRF_TRUSTED_ORIGINS` 返回 403；该次未创建业务数据。仅调整本地测试服务配置后，用原表单重试成功。重试后旧错误提示短暂残留，刷新页面后消失。此项属于测试环境修复后的 UI 提示清理观察，未修改业务模块，建议独立评估。
2. `/api/orders/1/packing-plan/` 在本次访问中返回 404，但页面核心工作台、采购计划、履约和本任务流程均正常；该端点不属于本次库存验收范围，未据此判定库存缺陷。
3. Vite 控制台反复出现 Vue warning：`OrderDetailModal` 在 `<Transition>` 中渲染非元素根节点，抽屉动画无法应用。未阻塞本轮操作；不属于本次库存状态修复范围，留待独立 UI 任务评估。
4. 本报告仅为隔离开发环境 UAT；不替代员工权限、真实业务数据或生产环境验收。Issue 状态未修改。

## 本目录文件

- 截图：本目录内 `*.jpg`，均从真实 Chrome 页面直接保存。
- 数据库快照：`database-*.json`。
- HTTP 证据：`api-http.log`、`api-duplicate-reversal.json`。
- 快照核对：`snapshot-comparison.json`。
- 合成数据与快照工具：`seed_synthetic_uat.py`、`snapshot_uat.py`；截图接收器为 `screenshot_receiver.py`。
