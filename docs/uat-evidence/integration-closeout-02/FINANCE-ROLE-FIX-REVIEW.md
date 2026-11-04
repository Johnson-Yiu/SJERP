# Finance ledger ordinary-role permission fix — read-only review

核对日期：2026-11-05
审查对象提交：9af2a32fa81df3aa975424b70a887057e40b6b22
侧审早期观察 HEAD：90683506f5d9447974302d83c89ba27351d5dfd4（不是当前主审HEAD）
主审通过只读来源检查取得的财务候选：2e20bfdccb711bdd5f9028cb60e287ee742c77c5；该短标识与本次提交不是同一 SHA，本报告不把审查结论绑定到它。

这是 Codex 的只读侧审，不是 ChatGPT 独立复审。通过 git show 检查了目标提交中的三项变更：backend/crm/finance_closeout_api.py、backend/crm/permissions.py 和 backend/crm/tests/test_finance_integration_permissions.py。没有依赖当前 git diff，也没有修改产品文件、测试、台账或 backlog。没有在本地运行测试。

## 结论

未发现提交 9af2a32 中存在权限绕过或错误放宽的 POST 动作映射。新映射仅供 FinanceCloseoutViewSet 使用，覆盖预览只读及三个创建动作；所有资金入口随后仍执行 ledger.access，继续要求 finance 操作权限、finance.view、transactions.view 和全局财务数据范围。

发现一个低严重度的请求格式一致性边界：共享权限解析器把若干大小写不敏感的 export 值分类为导出，但新 finance 模块选择器和资金 API 仅识别精确小写 csv。对非规范值可能造成拒绝或返回普通 JSON 的语义不一致，不构成权限绕过。见下文。

## 路径审查

### POST 动作映射

finance_closeout_api.py 第75–77行声明：

- preview → view
- accounts、vouchers、instructions → create

permissions.py 第157–190行先保留 export/import 和安全方法处理，再仅对 POST 读取 view 声明的 permission_action_map。映射值必须是 ACTION_FIELDS 中的字符串；未知项落回既有动作判定。全仓检索当前仅此 ViewSet 声明该映射。

FinanceCloseoutViewSet.initial 在执行 handler 前调用 ledger.access（finance_closeout_api.py 第97–102行）。该服务入口再检查对应 finance 操作权限、finance.view、transactions.view 和 global scope（services/cash_events.py 第53–56行；services/finance_closeout.py 第27–31行）。因此，permission_action_map 单独不能授予资金访问；未列出的 POST 动作仍按原 update 规则处理。

### CSV 导出与报告权限

对规范请求 facts?export=csv，模块属性只有在用户没有 finance.export、但有 reports.export 时才返回 reports（finance_closeout_api.py 第79–90行）。action_for_request 仍先将其判为 export（permissions.py 第160–163行）。facts handler 自身还检查 finance.export OR reports.export，再生成 CSV（finance_closeout_api.py 第225行起）。此前的 ledger.access(view) 仍检查 finance.view、transactions.view 和全局范围。由此，reports.export 不会单独授予资金读取权限，finance.export 与 reports.export 两条既有导出授权均保留。

### 开发身份、普通角色和拒绝路径

开发超级管理员短路仍位于 ModuleActionPermission 的模块/动作解析之前（permissions.py 第213–232行），本提交未改变该逻辑。模块缺失仍默认拒绝。active profile 和 active role 仍由现有 effective_permission_matrix 计算。

新测试导入的 RBAC_SETTINGS 明确设置 APP_STAGE=production、DEBUG=False、DEVELOPMENT_SUPERADMIN=False、RBAC_ENFORCEMENT=True。测试账号由 create_user 建立，普通读者测试断言不是 superuser。六个测试方法覆盖普通读者、只读预览及无副作用、create-only、update-only、finance/reports 两种导出授权，以及 finance.view、transactions.view、数据范围和停用 profile 的拒绝。拒绝场景还核对数据/审计计数不变，并检查响应不泄露账户代码。

### 低严重度边界：export 参数规范化不一致

permissions.py 第160行对 export 参数执行 lower()，将 1、true、csv、xlsx 都视为 export。finance_closeout_api.py 第85–88行的模块选择只匹配精确 export=csv；facts handler 也只在精确小写 csv 时返回 CSV。于是 export=CSV、export=true 或 export=xlsx 这类值，可能在权限层被当作 finance.export 请求，但 handler 若获准会返回普通 JSON；拥有 reports.export 而没有 finance.export 的普通角色也不会切换到 reports 模块。

这是输入规范化与响应格式之间的兼容性差异，不是越权路径。新测试仅覆盖小写 export=csv。若其他值不属于支持契约，应明确拒绝并测试；若沿用共享解析器的大小写/别名语义，应让模块判断和 handler 使用一致的规范化规则。此审查未修改代码。

## 测试证据边界

主审提供的结果：91项 SQLite 测试通过，耗时 54.708 秒，包含最终导出拒绝边界；PostgreSQL 64 项专项当时仍在运行。本报告没有复跑，也没有检查对应原始日志。该结论只能视为主审提供的运行结果，PG64 结果仍待交付后再核对。

## 审查限制

审查结论针对提交 9af2a32fa81df3aa975424b70a887057e40b6b22 的三文件改动。没有核实之前提及的 2e20bfd… 候选 SHA，也没有审查同工作树中的其他未提交文件。未发现明显授权绕过不等于 ChatGPT 独立接受，也不代替 PostgreSQL 专项结果。

## 主审后续实际结果（与上文侧审分开）

9af普通角色补修的SQLite91/91、干净9af检出上的真实PG17专项64/64已通过，恢复99表1081行128迁移4文件及私有HTTP4/4通过、源未变/清理完成。后续a8400fb8deb1bfeaaf99e0498d8b4aa34ef48f3f新增有序锁/截止日测试后，以原始clean guard在精确a840执行25/25 PG专项通过，包含三个有真实阻塞PID的有序锁场景；不采信被中止的草稿allowlist过程。实际文件见coordinator-finance-role-postgres-result.json及coordinator-finance-lock-order-result.json；本段不称侧审子任务独立重跑。当前主审HEAD为a840，完整本地回归继续执行。非规范export参数边界已记入公共ISS-105兼容核实子项，小写csv仍为当前受支持契约，未擅自扩大格式/别名。
