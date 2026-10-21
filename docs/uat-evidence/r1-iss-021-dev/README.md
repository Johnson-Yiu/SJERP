# R1-ISS-021-DEV 正式销售订单数量变更验收

## 1. 范围与基线

- 分支：`codex/r1-iss-021-dev`
- 开发基线：`origin/master` / `25405e1b25ff8a218b67883acf489ada8a53e146`
- 验收日期：2026-10-21
- 状态：`LOCAL PASS / CI PENDING`
- 本轮未合并 master，也未修改其他开发分支。

本轮实现正式销售订单的专用数量变更流程，不放宽普通订单 PATCH 对正式订单行的保护。变更保留原销售订单编号、原订单行 ID、SKU 与交易快照；使用服务器事务、行锁、版本号和幂等请求键防止重复提交及旧页面覆盖。

## 2. 已实现功能

### 后端

- 新增 `Order.quantity_change_version` 和不可变 `OrderQuantityAdjustment` 记录。
- 新增预览、提交、历史查询接口：
  - `POST /api/orders/{id}/quantity-adjustments/preview/`
  - `POST /api/orders/{id}/quantity-adjustments/`
  - `GET /api/orders/{id}/quantity-adjustments/`
- 仅允许具备 `orders.update` 且在订单数据范围内的操作；普通订单 PATCH 仍不能直接改正式订单商品数量。
- 支持单行及多行调整；多行校验或保存失败时整体回滚。
- 强制非空原因、当前版本校验、有效已发货数量校验、交易单位历史快照换算和合法精度校验。
- 数量增加时仅增加受控应收计划差额；数量减少时只减少未结清计划，已结算金额不被扣减；调整后金额低于已收款时拒绝。
- 调用既有库存预留重平衡服务；采购过剩只作为提醒，不自动取消或改动正式采购单，不改变共享采购成本归属。
- 成功变更记录前后数量、差额、金额、影响统计、原因、操作人和服务器时间；失败事务不写成功操作日志。

### 前端

- 在正式订单详情工作台增加“调整数量”入口和自定义弹窗。
- 展示 SKU、当前/新数量、交易单位、基础数量、已发货/已采购/已到货信息、资金影响及采购过剩提醒。
- 先预览影响，再通过自定义确认弹窗提交；取消不写正式数据。
- 成功后刷新订单工作台并展示数量变更历史；支持 1440px、1024px 与 700px 宽度。

## 3. 实际自动化测试

以下命令均在本隔离工作树执行，退出码为 `0`，除特别说明外使用 SQLite：

| 命令 | 实际结果 |
|---|---|
| `python manage.py check` | 通过，exit 0 |
| `python manage.py makemigrations --check --dry-run --noinput` | 通过，exit 0 |
| `python manage.py test crm.tests.test_order_quantity_adjustments --verbosity 1` | **10 tests OK**，exit 0 |
| `python -c "... call_command('test','crm.tests.test_cash_events.CashMigrationTests',...)"`（隔离 `MEDIA_ROOT`） | **1 test OK**，exit 0；0076/0077 历史行与 Decimal 字段保持一致，测试 finally 恢复最新迁移目标 |
| `python -c "... call_command('test',verbosity=1)"`（隔离 `MEDIA_ROOT`） | **779 tests，OK，skipped=13**，exit 0，耗时约 294 秒 |
| `npm run test:unit` | **136 tests passed**，exit 0 |
| `npm run build` | Vite 构建成功，2004 modules；仅有既有 chunk size warning，exit 0 |

全量 SQLite 首次未设置隔离媒体目录时出现 2 个环境/历史测试夹带失败：附件测试无法写入默认媒体目录，以及历史迁移测试使用当前模型读取 0077。随后使用隔离 `MEDIA_ROOT` 并修正历史迁移测试改用对应历史 migration app registry，复跑全量为上述 778 项通过；没有删除、跳过或弱化断言。

PostgreSQL：本机 5432 未监听，环境中没有可用 PostgreSQL 服务或连接变量，因此未伪造 PostgreSQL 通过结果；正式 PostgreSQL CI 留待额度恢复后执行。GitHub Actions 本轮按项目策略保持 `PENDING`，未反复触发。

## 4. 关键业务矩阵

| 场景 | 实际结果 |
|---|---|
| 100 → 150，无采购/发货 | 通过；订单总额与开放应收增加差额，订单号和订单行 ID 保持不变 |
| 100 → 60，无发货 | 通过；未结应收安全减少，历史已结算金额不被改写 |
| 100 → 60，已发货 50 | 通过；允许调整，低于已发货的部分不会被删除 |
| 100 → 60，已发货 70 | 通过拒绝；服务端和真实 Chrome 均显示“不能低于已发货数量 70” |
| 已付款金额高于调整后合同金额 | 通过拒绝；订单、支付计划和调整历史保持不变 |
| 已正式采购且减少数量 | 通过；保留采购事实，返回采购过剩提醒，不自动取消或改量正式采购单 |
| 同一 SKU 交易单位变化 | 通过；使用订单保存的交易单位快照和换算因子，不读取当前 SKU 包装参数替代历史含义 |
| 多行调整一行非法 | 通过回滚；没有部分数量、金额或历史记录写入 |
| 重复请求/旧版本提交 | 通过；相同请求幂等返回，旧版本返回冲突 |
| 取消预览/确认 | 通过；数据库数量、金额、应收与历史调整记录不变 |
| 既有正式采购成本归属 | 通过服务测试；数量变更不修改已有 `PurchaseCostAllocation`，其他订单/库存归属保持 |

数量变更服务只通过既有库存预留服务重平衡受影响 SKU，不直接写库存流水；不创建采购、付款、发货或银行流水。服务测试核对了订单金额、应收计划、预留统计、采购过剩提醒和成本归属前后结果。

## 5. 真实 Chrome 验收

使用当前工作树启动的隔离服务：Django `127.0.0.1:8127`、Vite `127.0.0.1:5287`，隔离 SQLite 已迁移至 0078 并使用合成客户、SKU `UAT-SKU-021` 和订单 `SO-UAT-021`。

人工真实 Chrome 流程：

1. 打开订单详情，点击“调整数量”。
2. 输入 `150`，填写“客户追加需求”，执行预览并确认提交。
3. 页面刷新后显示数量 `150`、订单总额 `1500`、应收计划 `1500`、原订单号不变，并出现一条 `100.00 → 150.00` 历史记录。
4. 再次打开预览输入 `120` 后取消；数量仍为 `150`，历史记录仍只有一条。
5. 在隔离数据库中加入已确认发货 70 件，刷新页面后输入 `60` 预览；真实 Chrome 显示服务端拒绝提示，未提交非法变更。

自动化真实 Chrome 采集脚本为 [`capture_real_chrome.mjs`](./capture_real_chrome.mjs)，使用本机 Chrome channel，对 1440/1024/700 三个宽度执行实际打开、填写、预览和断言，输出成功：

```text
{"width":1440,"result":"increase-preview-visible"}
{"width":1024,"result":"increase-preview-visible"}
{"width":700,"result":"shipped-quantity-rejection-visible"}
```

截图：

- [1440px 数量调整成功预览](./real-chrome-quantity-adjustment-1440.png)
- [1024px 数量调整成功预览](./real-chrome-quantity-adjustment-1024.png)
- [700px 已发货下限拒绝](./real-chrome-quantity-adjustment-700.png)

浏览器最终数据库核对：订单仍为 `SO-UAT-021`、数量 `150.00`、版本 `1`、应收计划 `1500.0000`、已发货 `70.00`、数量变更记录 `1`、资金交易记录 `0`。已发货记录是在数量调整后作为隔离测试数据直接加入的，因此其预留值保留种子时的 `100.00`；这不被解释为一次完整的到货/发货生命周期测试通过。

## 6. 迁移与跨分支兼容

本分支新增 `0078_order_quantity_change_version_and_more.py`，只依赖已发布的 0077；没有修改 0076/0077 或其他历史迁移。历史现金迁移测试已改为保存实际最新 CRM leaf migration targets，并在 finally 恢复全部最新迁移，且用 0076/0077 对应的历史模型比较历史数据。

已检查未合并分支：R1-ISS-037-P1、R1-ISS-039、R1-INV-03、R1-MOQ-02、R1-PO-04。它们存在并行的 0078 或共同修改文件：

- 各 0078 迁移均依赖 0077，整合时必须保留每个独立迁移；所有相关 0078 到齐后再生成新的 merge migration，不能重写或删除已发布迁移。
- `OrderDetailModal.vue` 与 ISS-037-P1 有共同修改；数量调整弹窗必须与主体快照展示人工合并。
- `views.py` 与 ISS-039/INV-03 有共同修改；数量调整 action 与采购/库存 action 需按功能保留后人工合并。

本轮没有临时合并这些正式分支，也没有推送临时整合代码。上述计划是后续整合前置条件，不构成本轮阻断。

## 7. 未完成项与边界

- 本机 PostgreSQL 不可用，未运行本地 PostgreSQL 回归。
- GitHub Actions 额度暂不可用，本轮为 `LOCAL PASS / CI PENDING`。
- 当前开发环境按项目约定使用开发超级管理员，未声称正式 RBAC 多账号 UAT 已通过；服务端权限检查、订单数据范围、版本锁和事务回滚由自动化测试覆盖。
- 浏览器流程覆盖成功变更、取消和已发货下限拒绝；完整真实多用户并发及正式采购/到货生命周期仍需独立环境验收。

ISS-021 不关闭，建议状态为 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立代码、业务和视觉审查。
