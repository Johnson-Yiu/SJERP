# FIRST-RELEASE-CORE-UAT-01

- 日期：2026-11-06
- 基线：`aa15c9ba7584599e918c1dd14723d31e31158b3d`
- 分支：`codex/sunjack-first-release-core-uat-01`
数据：隔离工作树 SQLite，仅合成数据；未连接真实业务库、未执行真实收付款或历史导入。

## 执行结果

| 环节 | 实际操作及结果 |
| --- | --- |
| 报价与 XLSX | 在 Chrome 新建并接受报价 `SJ20261106DE001`，合成客户快照、买方和联系人已保存。10 件 × USD 25 = USD 250。导出接口 HTTP 200，实际 XLSX 为 `PI` 工作表、35×13；核对报价号、买方、联系人、型号、数量、单位、单价和总额均正确。 |
| 销售订单 | 由报价生成 `SO-2026-00001`，USD 250，10 件；订单最终为已完成。 |
| 采购与收货 | 建立 `PO-2026-00001`，USD 120，10 件；按采购单两期计划 USD 36 / USD 84。Chrome 验货入库 10 件，仓库 `FRUAT-UAT仓`、批次 `FRUAT-BATCH-01`，采购单完成。 |
| 库存与发货 | 收货后库存 10、预留 10、可用 0；确认发货 `SH-CD6C8877B8B24358` 共 10 件。流水为采购入库 +10、销售出库 -10，期末实存及预留均为 0，销售订单完成。 |
| 收付款及余额 | 仅写入 ERP 合成收付记录：客户两期 USD 75 / USD 175 均结清，应收 USD 250、未收 0；供应商 USD 36 / USD 84 均结清，应付 USD 120、未付 0。按 7.2 汇率计算的 CNY 1,800 / 864 / 净额 936 只作参考折算，不代表实际人民币或银行流水。 |
| 新品提醒入口 | 从客户跟进打开“新品提醒”，URL 保留客户及跟进关联；创建有效合成提醒 `id=1`。没有自动匹配商品，也没有给客户发送消息。 |
| 多工作区会话自然过期 | 临时隔离设置将会话寿命设为 8 秒；在 Chrome 打开客户列表及一个未保存的新建客户工作区（共 2 个内部工作区），等待自然到期后进行正常 API 操作。页面进入 `login?reason=expired`，显示会话过期提示并清空私有工作区。没有清 Cookie；临时测试用户、会话和设置均已清理，开发身份未更改。 |

XLSX 曾包含模板内的公司银行信息；文件只用于本地打开和单元格检查，验证后删除，不纳入仓库。摘要保留文件字节数及 SHA-256，不含该文件内容。详见 [`evidence-summary.json`](evidence-summary.json)。

## 分类与交接

### 阻断首发

- **ISS-020 报价 XLSX 浏览器交付仍需关闭。** 现有最新完整 Playwright 记录在候选 `02140bf46df27ba1abf5b9018507c07aae825769` 为 262 通过、1 失败；报价场景的 `saveAs` 被取消，根因未确认。本次在指定基线上实际操作 Chrome 报价及导出接口并验证 XLSX 内容成功，没有复现取消，也没有推翻上述全场景失败。由于 XLSX 属于本次核心链路，首发验收应保留此项门槛；ISS-020 状态不变，交统一集成/报价导出工作包继续定位并用真实浏览器下载事件验收。
- **有条件的共享启用门槛：** 若首发要导入并启用真实历史数据，ISS-121 仍需历史包独立核对实际导入/启用证据；本轮未调用历史导入，未产生新复现。交 `R1-PRELAUNCH-CONSOLIDATION-01` / 历史接续工作包，沿用 ISS-121，不另建重复问题。
- **有条件的共享启用门槛：** 若首发范围要求正式主体版本和审批分离，ISS-037 仍需主体版本包集成及独立验收；本轮只验证客户、联系人、报价、订单、采购单的静态快照，没有修改或验证正式主体修订。交主体版本工作包（集成分支 `codex/party-version-integration-01`，来源 `f5a91a5ff0b75f2e5b45a6efcf04a36f57da37f0`；报价快照复核分支 `codex/party-version-closeout-20261105`，来源 `7cc8c4bf0249a3de53809836b7b3f233476a1648`），沿用 ISS-037。

除上述已存在的 XLSX 交付门槛及条件性共享门槛外，本轮未复现新的首发阻断，也没有清晰且可独立修复的产品缺陷；因此未改业务代码。

### 可上线后修

- 本次范围没有新增可上线后修的问题。工作区切换时曾看到已有的“相关数据已更新”提示；按提示重新载入后操作正常，不构成阻断，也未另开问题。
- 测试环境缺少 `openssl` 可执行文件，导致额外的 `crm.tests.test_operations_receipt` 专项在测试类初始化时报错；这是独立的签名运维回执测试，不是本次采购收货或财务收付链路。该专项未作为通过项计入。若签名回执属于首发范围，需在具备 OpenSSL 的环境单独验收。

## 定向验证

- 后端：隔离 CPython 3.14.5 / Django 6.0.8，Django system check 通过；共 142 项通过、2 项 PostgreSQL 专项跳过、0 项失败。命令：

  ```powershell
  python manage.py test crm.tests.test_iss020_quote_export crm.tests.test_quotes crm.tests.test_purchase_payment_terms crm.tests.test_fulfillment crm.tests.test_fulfillment_receivables crm.tests.test_new_product_reminders crm.tests.test_access_implementation --verbosity 1
  ```

- 前端：5 个定向 Vitest 文件、64 项通过。运行时 Vitest 4.1.11，锁文件固定为 4.1.12；本机依赖目录为共享 junction，未改依赖或锁文件。命令：

  ```powershell
  npx vitest run tests/new-product-reminders.spec.js tests/workspace-manager.spec.js tests/order-fulfillment-ux.spec.js tests/purchase-workbench.spec.js tests/quote-editor-availability.spec.js --environment jsdom
  ```

- 真实 Chrome：完成报价/导出、新品提醒入口和多工作区自然会话过期的可见操作检查。没有运行完整回归或 GitHub Actions；用户说明 CI 额度暂停，未将 CI 记为通过。
- 原始定向日志：[`backend-core-targeted.log`](backend-core-targeted.log)、[`frontend-targeted.log`](frontend-targeted.log)。首次合并测试命令因 OpenSSL 初始化失败的日志单独保留于 [`backend-targeted.log`](backend-targeted.log)。

## 清理及状态

临时过期会话、测试用户、临时设置、临时服务和导出工作簿已清理。永久保留的只有合成主档播种脚本、测试日志、摘要和本报告；应用记录存于隔离工作树本地数据库，不推入 Git。

本轮没有新增 Issue，也未改变既有 Issue 状态。台账仍为 124 个唯一 ID：`FIXED_PENDING_REVIEW=87`、`NEEDS_VERIFICATION=14`、`BLOCKED=13`、`OPEN=0`、`CLOSED=10`。ISS-020、ISS-037、ISS-121 均保留各自既有状态。
