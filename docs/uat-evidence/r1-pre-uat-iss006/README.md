# R1-PRE-UAT-ISS006 库存安全复测与最小补修

## 范围与基线

- 固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`
- 工作分支：`codex/pre-uat-iss006-inventory-safety`
- Worktree：本报告所在独立 worktree
- 数据库：仅使用本轮新建的隔离 SQLite 数据库；未连接现有业务数据库
- 约束：未修改 `PROJECT_ISSUES.md`、`PROJECT_PHASES.md`，未合并 master，未部署，未触发 GitHub Actions

已阅读 ISS-006 历史记录、`docs/R1-A-核心业务历史Issue核实与修复.md`、R1-A 验收材料及库存相关协议。R1-A 已覆盖入库冲销、已销售消耗后的拒绝、部分收货/冲销/重新收货、发货冲销、超量到货/赠品和手工盘盈；其明确未覆盖网络响应丢失、跨客户端并发和竞态。本轮没有重复实现这些库存冲销规则，而是先复现该剩余风险。

## 先复现：已确认缺陷

在基线新建隔离数据库，使用同一业务请求连续发送两次，模拟第一次写入成功但客户端未收到响应后重试：

| 场景 | 第一次 | 第二次 | 基线结果 |
|---|---:|---:|---|
| 收货 5 pcs | HTTP 201 | HTTP 201 | 产生 2 条收货、2 条入库流水，实际库存由 0 变为 10 |
| 发货 5 pcs | HTTP 201 | HTTP 201 | 产生 2 条发货、2 条出库流水，实际库存由 10 变为 0 |

原始 JSON：[baseline-duplicate-repro.json](./baseline-duplicate-repro.json)

这不是过时测试：两个请求都通过了原有业务校验并分别完成了库存写入，确实会把一次网络重试解释为两次业务动作。

## 最小修复

新增可选的 `request_key` 和请求指纹字段：

- `GoodsReceipt`、`Shipment` 各自保留可空、唯一的 `request_key`，兼容旧历史记录和旧调用方。
- 收货、发货接口使用请求内容指纹判断重试：同 key 且同内容返回原结果 HTTP 200，不重复写入；同 key 但内容不同返回 HTTP 409，不允许复用幂等键改写事实。
- 并发唯一键冲突也按同一规则重放原记录。
- 前端收货和发货在一次提交生命周期内保留同一 key；请求失败重试不会生成新的业务动作，成功或关闭窗口后才结束该生命周期。
- 未修改库存流水类型、数量计算、预留、冲销、财务金额、采购状态、销售状态或既有审计流程。

迁移为 `crm.0090_fulfillment_request_idempotency`，依赖现有 `0089`，未覆盖或重写已发布迁移。

## 修复后真实 API 与数据库证据

修复后同样的连续请求结果：

| 场景 | 第一次 | 第二次 | 修复后结果 |
|---|---:|---:|---|
| 收货 5 pcs | HTTP 201 | HTTP 200 | 两次响应均指向同一收货和同一流水；数据库只有 1 条收货、1 条入库流水，实际库存为 5 |
| 发货 5 pcs | HTTP 201 | HTTP 200 | 两次响应均指向同一发货；数据库只有 1 条发货、1 条出库流水，实际库存从 10 变为 5 |

同一 key 改变数量的 409 冲突也由后端回归测试覆盖。原始 JSON：[fixed-idempotency-repro.json](./fixed-idempotency-repro.json)

最终隔离数据库快照：[database-final.json](./database-final.json)

最终快照核对：

- 采购单：`partial`，已收 5、剩余 5、收货记录 1 条。
- 销售单：`confirmed`，已发 5、预留 5、发货记录 1 条。
- 收货 SKU：实际 5、预留 0、可用 5、在途 5。
- 发货 SKU：实际 5、预留 5、可用 0、在途 0。
- 流水保留原始手工入库 10、一次采购入库 5、一次销售出库 5，引用号与业务单号一致。

复现脚本：[baseline_duplicate_repro.py](./baseline_duplicate_repro.py)；数据库快照脚本：[database_final.py](./database_final.py)。

## 已保留并复测的库存规则

R1-A 已有冲销逻辑未被重写。定向及全量后端测试继续覆盖：

- 未被销售消耗的入库允许冲销；已消耗入库拒绝且不产生反向流水。
- 部分收货、冲销、重新收货保持原语义。
- 发货冲销恢复实际库存/预留并保留历史。
- 超量到货、赠品和手工盘盈使用原有正向/反向流水模型。
- 采购、销售、库存之间的 source/source_no 引用保持可追溯。

本轮没有发现新的库存数量、状态转换或财务金额缺陷。

## 自动化测试

| 检查 | 结果 |
|---|---|
| ISS-006 幂等 + 冲销/履约定向后端 | 48 tests passed |
| Django 全量 | 1003 tests passed, 18 skipped |
| `manage.py check` | passed |
| `makemigrations --check --dry-run` | no changes detected |
| 全新 SQLite 迁移 | 从零执行至 `crm.0090` passed；`0081` 分支、`0082` merge 及后续迁移均已应用 |
| Node unit | 169 passed |
| trade-units | 4 passed |
| 有效 Vitest 全量 | 67 files, 662 tests passed；排除了仓库中明确标记为基础设施/非 Vitest 的 3 个文件 |
| 相关 Vitest 定向 | 7 files, 101 tests passed |
| 生产构建 | passed，2018 modules transformed；仅有既有主 chunk 体积提示 |
| `inventory-ux.spec.js` Chrome 回归 | 9/9 场景通过；所有场景完成后测试 runner 的 webServer teardown 未自行退出，随后手动终止 runner，未改变已通过的断言结果 |

全量测试和浏览器服务日志：

- [backend-browser.log](./backend-browser.log)
- [backend-browser-error.log](./backend-browser-error.log)
- [frontend-browser.log](./frontend-browser.log)
- [frontend-browser-error.log](./frontend-browser-error.log)

## 真实 Chrome 证据

使用隔离后端、隔离 SQLite、真实 Chrome channel 和桌面/窄屏视口生成，未复用旧截图：

- 采购工作台桌面：[chrome-purchase-workbench-desktop.png](./screenshots/chrome-purchase-workbench-desktop.png)
- 收货明细桌面：[chrome-purchase-receipt-desktop.png](./screenshots/chrome-purchase-receipt-desktop.png)
- 收货明细窄屏：[chrome-purchase-receipt-narrow.png](./screenshots/chrome-purchase-receipt-narrow.png)
- 销售发货桌面：[chrome-order-fulfillment-desktop.png](./screenshots/chrome-order-fulfillment-desktop.png)
- 库存工作台窄屏：[chrome-inventory-narrow.png](./screenshots/chrome-inventory-narrow.png)

网络与控制台采集：[browser-network.json](./browser-network.json)；生成脚本：[capture_chrome_evidence.mjs](./capture_chrome_evidence.mjs)。页面 API 请求均完成，日志中只有一个无 Packing Plan 数据的预期 404、一个外部资源被本地环境拒绝，以及既有 Vue transition warning，没有发现本轮接口 5xx 或浏览器 page error。

窄屏截图显示库存页沿用现有左侧导航宽度，内容区域存在横向裁切/滚动；本轮未为该既有布局另行重构，也没有把它误报为库存数据一致性缺陷。

## 剩余风险与后续条件

1. 本轮使用隔离 SQLite，未进行 PostgreSQL 行锁和真实多客户端并发验收；正式 UAT 前仍应在与生产一致的 PostgreSQL 环境执行并发/故障注入测试。
2. `request_key` 对旧 API 调用保持可选，因此未携带 key 的外部旧调用无法可靠去重；当前官方前端路径已携带 key。切换为强制字段需要单独的 API 兼容评审，不在本轮擅自改变。
3. 本轮“网络超时”通过第一次写入后重新发送同一请求模拟，验证了业务层重试安全性；未在生产代理或真实网络设备上制造丢包。
4. 未运行 GitHub CI、未验证生产 PostgreSQL、未连接生产数据库、未部署。

交付 SHA 以本分支最终提交为准。该提交不代表关闭 Issue 或具备未经 PostgreSQL/独立审查的最终生产放行资格。
