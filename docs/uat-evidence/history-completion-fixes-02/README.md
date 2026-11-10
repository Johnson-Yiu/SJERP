# HISTORY-COMPLETION-FIXES-02 验收记录

2026-11-10。来源分支 `codex/release-integration-repair-01` fetch 后为 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`，与已审基线一致。独立分支 `codex/history-completion-fixes-02`。

## 历史分类

两条各 100 的正式销售明细使用同一冻结分类。基线换掉一个产品当前分类后，复现原数字键和快照键各得 100。修复后换分类、改名和删除均保持原快照键、单组 200，筛选与下钻合计 200，CSV 同组 200。采购、历史分析及仪表板使用同一分类键生成函数。原有 `snapshot:`、`source:` 与未知键继续使用。仅含当前主档编号的旧销售和采购分类键返回 400 并提示重新选择。没有迁移或回填。

## 追溯更正

迟到记录、审计更正、补交凭证使用中文表单，程序生成现有接口的 details。组件测试覆盖三种提交的字段提示、请求内容和审核依据。后端回归核对原来源行、原销售明细、审核事件与提交事件关联、资金记录数量及库存流水。审核与提交仍使用现有后端校验。

## 执行记录

- 基线反例，backend 执行 `python manage.py test crm.tests.test_reporting.ReportingTests.test_category_snapshot_identity_survives_master_changes --verbosity 1`，预期失败，实际拆成 100 + 100。
- 修复后，backend 执行 `python manage.py test crm.tests.test_reporting crm.tests.test_history_takeover crm.tests.test_dashboard_import --verbosity 1`，共 65 项，64 通过、1 跳过。
- frontend 执行 `npm exec -- vitest run tests/history-takeover.spec.js --reporter=dot`，12 通过。测试环境报告 RouterLink 未注册警告。
- frontend 执行 `npm run build`，通过，Vite 报告主包体积警告。
- `git diff --check` 通过。
- Chrome 打开本机隔离测试库登录页。为避免测试口令进入工具日志，未在本轮浏览器工具中输入口令，登录后视觉和窄屏仍待验收。

本包交 A2 集成历史报表及追溯更正页面。公共布局、台账和 B2 财务范围由对应包处理。验收使用合成测试数据，正式导入和部署未执行。
