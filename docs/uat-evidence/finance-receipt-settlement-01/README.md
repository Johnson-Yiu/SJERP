# FINANCE-RECEIPT-SETTLEMENT-01 验收记录

日期：2026-11-07
基线：`b223c052902463b59e149409cf9941503aeab31f`
分支：`codex/finance-receipt-settlement-01`
工作树：`.worktrees/finance-receipt-settlement-01`

本包简化人民币资金录入与详情，共用新增和收款关联的结汇表单；系统继续生成隐藏的请求身份并对上传凭证做文件校验。界面保留到账日、银行净额、手续费、账户名称、参考号、凭证与核对说明。未配置账户时提示维护财务台账账户并联系管理员。历史凭证缺失时要求补传实际文件。确认继续走原查重、来源核验、权限和凭证规则。

所有 Vue 页面移除遮罩自身点击关闭事件。客户收款选外币后可展开结汇区；展开不会保存。明确点击“保存收款并继续”才先保存收款，之后在原窗体继续预览、登记和确认结汇。后端以保存后的收款根流水绑定对应拆分家族并派生订单关系；拆分产生的未分配预收仍为独立来源。收款结果不明时先按原流水查询；收款已保存后，父窗体不再提交收款，失败重试只走结汇步骤。

## 定向自动验证

后端在 Django 临时测试数据库执行，4 项通过，0 失败：

```powershell
python manage.py test crm.tests.test_cash_events.CashEventTests.test_linked_receipt_uses_saved_split_family_and_keeps_unallocated_advance_distinct crm.tests.test_cash_events.CashEventTests.test_cash_account_choices_return_configured_readable_names_only crm.tests.test_cash_events.CashEventTests.test_c_partial_60_40_and_overallocation crm.tests.test_cash_events.CashEventTests.test_i_idempotency_lookup_conflict_cancel_and_immutable_confirm_payload --verbosity 0
```

覆盖拆分收款及未分配预收绑定、只返回已配置账户名称、部分来源额度、同请求幂等和新请求重复占用拒绝。

前端 Node 定向回归 12/12 通过：

```powershell
node --test src/views/CashEventPage.test.js src/views/TransactionPage.test.js src/utils/customerReceiptSettlement.test.js src/utils/modalBackdropBehavior.test.js
```

组件遮罩点击回归 1/1 通过：

```powershell
npx vitest run src/components/CashEventEntryForm.spec.js --environment jsdom
```

相关前端生产构建通过：

```powershell
npm run build
```

构建报告有既有的单个 JavaScript chunk 超过 500 kB 提示；构建退出码为 0。未运行全量测试、CI 或其他专项；CI 状态为 `NOT_RUN`，符合本包指令。

## 浏览器检查

使用 Codex 内置浏览器打开本工作树 Vite 页面 `http://127.0.0.1:5202/`，代理到绑定独立临时 SQLite 数据库的本工作树 Django 服务 `127.0.0.1:8114`。未连接开发库；测试操作员显示为开发身份 `codex`。数据库没有资金账户或业务流水，因而未提交任何业务记录。

- 人民币资金页的新增表单只显示用户业务字段和“预览结汇信息”；账户为空时显示配置指引。输入临时银行参考号后，点击窗体外的灰色遮罩区域，窗体仍打开且输入保留。显式关闭会继续显示“未保存修改”确认。
- 新增记账表单显示“其他期间费用（如水电费、物业费、软件订阅费等）”；其持久化分类仍为“其他期间费用”。CNY 客户收款显示“本笔收款无需登记外币结汇”；切换 USD 后显示“登记收汇记录”。
- 点击“登记收汇记录”只在原弹窗内向下展开结汇信息；界面显示“关联订单：保存后读取”和“财务流水：收款保存后读取”，以及无匹配账户的维护说明。没有点击保存；收款和结汇 API 均未写入业务记录。
- 在展开的结汇区填入临时核对说明，点击弹窗外主内容遮罩，窗体和输入仍在；当前事务流水条目仍为 0。详情、确认及补传凭证的规则由共享组件和后端定向测试覆盖。

此浏览器证据仅代表该精确工作树在隔离 SQLite 中显示并交互的页面；没有使用真实银行凭证、账户或订单数据。等待独立复审。
