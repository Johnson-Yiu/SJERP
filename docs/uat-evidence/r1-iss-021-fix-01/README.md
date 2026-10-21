# R1-ISS-021-FIX-01 验收证据

## 基线与范围

- 分支：`codex/r1-iss-021-dev`
- 修补基线：`a35116d4d218d4bd902a5792e9e92e619ac8a7fe`
- 本轮范围：数量变更响应脱敏、同 SKU 多订单行采购影响合并、空变更拒绝、前端空变更交互。
- 未修改其他开发分支，未合并 `master`，未新增数据库迁移。
- 建议状态：`LOCAL PASS / CI PENDING`，ISS-021 保持 `FIXED_PENDING_REVIEW`。

## 代码修复结果

### 权限与敏感信息

- `redact_quantity_adjustment_response()` 统一处理预览、提交响应和历史响应。
- 无 `finance.view + transactions.view` 时隐藏金额、收款计划、核销和资金影响数值；保留不带金额的安全提示。
- 无 `purchases.view` 时隐藏采购数量、到货/在途/采购过剩明细和采购影响快照；不放宽 `orders.update`。
- 订单工作台内嵌的订单、订单行、数量变更历史和 `OperationLog` 均使用同一策略；未改变普通订单 API 权限。
- 采购人员只需要订单修改权限即可执行合法数量变更，不要求获得财务或采购通用查看权限。

### 采购影响与空变更

- 同一订单内相同 SKU 的订单行按整单 SKU 基础数量聚合，采购过剩提醒只计算一次；不同订单和公司库存归属不混入当前订单。
- 采购单、成本归属、库存流水不会被数量变更自动修改。
- 提交前过滤未变化订单行；全部未变化时返回“数量没有变化”，不增加版本、不写历史、不改付款计划、不重建预留、不记成功审计。
- 交易单位沿用订单保存的历史换算快照，异常精度、超大数和非法输入安全返回 400，不产生部分写入。

## 自动化测试

以下命令均在当前 worktree 执行，结果为实际执行结果：

| 命令 | 结果 |
|---|---|
| `python manage.py check` | 通过，exit 0 |
| `python manage.py makemigrations --check --dry-run --noinput` | 通过，exit 0；No changes detected |
| `python manage.py test crm.tests.test_order_quantity_adjustments --verbosity 1` | **22 tests OK**，exit 0；最终复跑 22/22 通过 |
| `npm run test:unit` | **136 tests passed**，exit 0 |
| `npx vitest run tests/order-quantity-adjustment.spec.js --environment jsdom` | **1 file / 1 test passed**，exit 0 |
| `npm run build` | Vite 构建成功，2004 modules，exit 0；仅有既有 chunk size warning |
| `python manage.py test --verbosity 1`（隔离可写 `MEDIA_ROOT`） | **790 tests，OK，skipped=13**，exit 0；系统检查无问题 |
| `Test-NetConnection 127.0.0.1 -Port 5432` | exit 0，结果 `False`；本机 PostgreSQL 未监听，未伪造通过结果 |

定向后端测试包含：RBAC 脱敏、订单工作台脱敏、审计脱敏、财务错误消息脱敏、采购提醒脱敏、同 SKU 多行合并、空变更、部分收款、已发货下限、交易单位、精度/超大数、事务回滚、幂等和版本冲突。

全量 SQLite 测试使用隔离媒体目录，避免历史附件测试写入默认 `backend/media` 的权限干扰。首次使用不可写服务进程进行浏览器提交时出现 SQLite `attempt to write a readonly database`，数据库未变化；随后以可写隔离后端重启并完成下面的真实 Chrome 提交复测。该环境问题没有修改业务代码。

## 真实 Chrome 验收

真实 Chrome 使用当前安装的 Google Chrome channel。交互验收同时通过 Codex 真实 Chrome 页面操作和 [`capture_real_chrome.mjs`](./capture_real_chrome.mjs) 实际脚本完成。脚本退出码为 `0`，标准输出保存在 [`chrome.stdout.log`](./chrome.stdout.log)，标准错误文件为空 [`chrome.stderr.log`](./chrome.stderr.log)。

实际覆盖：

1. 1440px：150 → 120 合法减少预览，显示数量和金额差额。
2. 1024px：150 → 120 合法减少预览，布局正常。
3. 700px：150 → 60，显示“不能低于已发货数量 70”。
4. 700px：150 → 150，显示“数量没有变化”，预览按钮保持禁用。
5. 真实 Chrome 交互中实际提交 150 → 120，再提交 120 → 150；确认弹窗、取消/确认流程、金额变化和历史记录均可见，订单号仍为 `SO-UAT-021`。

截图：

- [1440px 合法变更预览](./real-chrome-quantity-adjustment-1440.png)
- [1024px 合法变更预览](./real-chrome-quantity-adjustment-1024.png)
- [700px 已发货下限拒绝](./real-chrome-quantity-adjustment-700.png)
- [700px 空变更提示及禁用按钮](./real-chrome-quantity-adjustment-noop-700.png)

最终隔离数据库核对：订单 `SO-UAT-021` 数量 `150.00`、订单总额 `1500.00000000000000`、数量变更版本 `3`、数量变更记录 `3`、已发货 `70.00`、预留 `80.00`；付款计划合计仍为 `1500.0000`，没有新增交易或采购成本归属。

前端真实浏览器使用开发超级管理员身份，仅用于本地视觉和业务流程；正式多账号 RBAC 通过 `RBAC_ENFORCEMENT=true`、`DEVELOPMENT_SUPERADMIN=false` 的后端自动化测试覆盖，未将开发身份冒充为普通员工浏览器验收。

## 未解决事项

- 本机 PostgreSQL 服务不可用，PostgreSQL 回归需在可用环境执行。
- GitHub Actions 按当前额度策略保持 `PENDING`，本轮未反复触发 CI。
- 真实 Chrome 已覆盖本轮要求的单行成功、合法减少、已发货下限拒绝和空变更；同 SKU 多行采购影响的精确聚合由定向后端测试覆盖，未为浏览器验收改造测试数据模型。
- 不关闭 ISS-021，等待 ChatGPT 独立代码、权限、业务和视觉复审。
