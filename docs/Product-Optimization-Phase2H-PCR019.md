# Phase 2H / PCR-019 — 产品证书到期提醒

## 交付门槛

基线：`b6a97674c617a08488dc220b518b72d51bfd7845`，CI #150 三个作业 SUCCESS。
本阶段只实现 PCR-019。真实 UI UAT 已完成；最终 HEAD 的三个 CI 作业全部 SUCCESS 后才可关闭。
实现提交及三项 CI 已验证（见末节）；包含本记录的最终文档提交仍须完成三项 CI。最终交付报告在核对该 HEAD 后宣布关闭，不提前将未执行的运行标为 PASS。

## 原风险与实现范围

原有 expires_on 只是被动档案，证书过期或临近到期不易发现。本次增加服务端派生状态、数据库筛选、列表徽章和经营概览提醒。
没有新增模型或迁移；没有持久化提醒字段、邮件、短信、定时任务、通知收件箱或确认流程。
开发超级管理员判定、权限、库存、订单、报价、财务和实际装箱业务规则均未改动。

## 日期语义

以 Django `timezone.localdate()` 为今日，前端不另行计算日期边界。

| 条件 | expiry_status | days_to_expiry | 显示 |
| --- | --- | --- | --- |
| 无有效期 | no_expiry | null | 无有效期 |
| 小于今日 | expired | 负数 | 已过期 · N 天 |
| 今日 | expiring_30 | 0 | 今日到期 |
| 1–30 天，含第 30 天 | expiring_30 | 正数 | N 天后到期 |
| 31–90 天，含第 90 天 | expiring_90 | 正数 | N 天后到期 |
| 大于 90 天 | valid | 正数 | 有效 |

`ProductCertificateSerializer` 提供只读 expiry_status、expiry_status_display、days_to_expiry。
列表、首页和产品详情证书表复用服务端结果。今日到期不属于已过期。

## 数据库筛选与导航

保留 `product=<id>`，可以与 expiry 同时使用：

| expiry | 查询范围 |
| --- | --- |
| attention | 有日期且 <= 今日+90 天，包含所有历史过期证书 |
| expired | < 今日 |
| expiring | 今日至今日+90 天，包含两端 |
| valid | > 今日+90 天 |
| no_expiry | 日期为 null |

以上筛选在数据库执行；筛选结果按 expires_on、id 升序，优先最早过期记录。
无 expiry 的列表保留原模型排序 `-expires_on, name`。
仅证书 ResourcePage 显示全部、需关注、已过期、90 天内到期、无有效期快捷按钮。
Vue Router 更新 query，激活态和上下文随直接访问或刷新恢复。
清除筛选仅移除 expiry，保留 product、detail 等其他 query；原通用详情抽屉继续使用。

## 经营概览

`GET /dashboard/` 新增 summary.certificate_attention / certificate_expired / certificate_expiring。
`certificate_alerts` 最多 5 条，按最早过期日期、id 排序；含证书 ID、产品 ID/名称、证书名称/编号、日期、派生状态/天数。
无有效期记录不计入任一提醒数量。attention = expired + expiring。
查看全部：`/product-certificates?expiry=attention`。
单条：`/product-certificates?expiry=attention&detail=<id>`。
零提醒时中性显示“当前没有 90 天内到期的证书”，不显示红色过期徽章。
原销售指标、待跟进、客户排行和现金流继续保留。

## 真实 UI UAT

执行日期：2026-10-07（服务端本地日期）。使用内置 Browser 技能；无 Computer Use，无 API、数据库或 shell 数据写入捷径。
在现有产品 `UAT-R1 智能面板灯` 下，通过新建记录表单创建六条一次性证书。

| 临时 ID | 名称 | 有效期 | 天数/状态 |
| --- | --- | --- | --- |
| 2 | UAT-P2H-EXPIRED | 2026-10-06 | -1 / expired |
| 3 | UAT-P2H-TODAY | 2026-10-07 | 0 / expiring_30 |
| 4 | UAT-P2H-30DAY | 2026-11-06 | 30 / expiring_30 |
| 5 | UAT-P2H-45DAY | 2026-11-21 | 45 / expiring_90 |
| 6 | UAT-P2H-VALID | 2027-01-06 | 91 / valid |
| 7 | UAT-P2H-NULL | 无 | null / no_expiry |

| UAT | 结果 | 实际证据 |
| --- | --- | --- |
| UAT-P2H-001 | PASS | ID 2 显示已过期 · 1 天 |
| UAT-P2H-002 | PASS | ID 3 显示今日到期；ID 4 显示 30 天后到期，均为紧急色 |
| UAT-P2H-003 | PASS | ID 5 显示 45 天后到期，90 天预警色 |
| UAT-P2H-004 | PASS | ID 6 显示有效 |
| UAT-P2H-005 | PASS | ID 7 显示无有效期，不进入需关注列表或首页数量 |
| UAT-P2H-006 | PASS | 需关注 IDs 2,3,4,5；已过期 ID 2；90 天内到期 IDs 3,4,5；无有效期 IDs 1,7 |
| UAT-P2H-007 | PASS | 直接访问 attention 并刷新；query、需关注激活态和四条记录保留 |
| UAT-P2H-008 | PASS | 首页需关注 4、已过期 1、90 天内到期 3，按 IDs 2,3,4,5 展示 |
| UAT-P2H-009 | PASS | 首页查看全部打开 attention query 与需要关注的证书上下文 |
| UAT-P2H-010 | PASS | 首页过期证书行打开 expiry=attention&detail=2；标题、编号、2026-10-06 日期一致 |

额外回归：从证书详情进入产品详情，证书档案表七条记录正确显示派生徽章；原详情有效期显示正确。
UI 证据：`pcr019-dashboard-uat.png` 与 `pcr019-cleanup-dashboard.png`，存于本任务的 Codex visualizations 目录。

### 清理

通过每条列表记录的删除按钮和确认删除对话框，删除本次 IDs 2–7 共六条临时证书。
清理后列表仅保留原 ID 1 `UAT-R1 CE 合规证书`（CE-UAT-20260930-001、UAT Test Lab、无有效期）。
未编辑或删除原有证书，未创建或修改产品、库存、订单、财务记录。
清理后首页显示“当前没有 90 天内到期的证书”。

## 自动化验证

新增后端 `crm.tests.test_certificate_expiry` 7 项测试，子场景覆盖 null、-1、0、1、30、31、90、91 天、所有 expiry 筛选、产品组合筛选、原排序、首页数量/最早过期/5 条限制、零提醒、只读派生字段及 CRUD。
新增前端 `tests/certificate-expiry.spec.js` 13 项，覆盖徽章及色类、列表呈现、全部快捷路由、直接挂载请求参数/激活态、清除保留其他 query、detail 共存、首页数量/记录/两类链接和零提醒中性状态。

| 命令 | 本地结果 |
| --- | --- |
| backend python manage.py test | 557 项，OK，10 项 PostgreSQL 专用测试本地跳过 |
| backend python manage.py makemigrations --check --dry-run | No changes detected |
| frontend npm run test:unit | 111 项 PASS |
| frontend node --test tests/detail-drawer-typography.spec.js | 1 项 PASS |
| frontend Vitest tests（排除 Node-only typography） | 23 文件 / 175 项 PASS |
| frontend npm run build | PASS；既有大块体积提示 |
| git diff --check | PASS |

全套测试包含 ProductWorkspace、ResourcePage 路由生命周期、首页待跟进、PCR-020 应收入口和 PCR-007 实际装箱回归。
本地未运行 PostgreSQL 专用环境；最终 GitHub backend-postgres 必须 SUCCESS。

## CI

实现提交：`8c435c0773e038e3d884cc473c6ef96de8acf27d`。
已独立读取 GitHub Actions [CI #151](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/37501325266) 的最终结果，headSha 与实现提交完全一致。

| 作业 | 结论 |
| --- | --- |
| backend | SUCCESS |
| backend-postgres | SUCCESS |
| frontend | SUCCESS |

UAT 十项及临时数据清理已完成，实现提交三项 CI 全部通过。
包含本 CI 记录的文档提交将正常推送，再检查它对应的完整工作流；只有最终 HEAD 三项 SUCCESS 后才能交付 PCR-019 PASS。
最终 SHA、最终 CI 运行号和三个结论记录于本次最终交付报告，并可在 [master 工作流记录](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions?query=branch%3Amaster) 按 SHA 核验。
正常 commit / push；遇非快进停止，不 force push、reset 或远程历史 rebase。
