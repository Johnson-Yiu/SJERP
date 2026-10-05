# SUNJACK-ERP Product Optimization Phase 2C-4 — PCR-012

## 验收状态

**PCR-012 实现、自动化回归及真实 UI UAT 均通过；UAT-P2C4-001 至 009 为 9/9 PASS。** 本地代码回归结果见下文。当前 GitHub Actions 运行状态无法核验，单独记录为 CI 限制，不代表远端 job 已通过。

## 当前待跟进定义

对每个 Customer，按 `followed_at DESC, id DESC` 选出最新的一条 FollowUp。只有该条记录代表当前下一步行动。仅当 `next_follow_up IS NOT NULL AND next_follow_up <= timezone.localdate()` 时，记录才属于当前待跟进集合。较早的逾期历史记录一旦被更新的跟进记录取代，就不会继续显示为当前任务；最新记录没有日期时，同一客户的旧逾期记录也不显示。

`GET /follow-ups/?due=true` 是当前待跟进筛选的正式语义。它默认按 `next_follow_up ASC, id ASC` 排序，继续与 `customer=`, `search=`, `ordering=` 服务端过滤组合。无 `due=true` 的 Follow-Up 列表仍显示完整历史记录。

## 实现

- 后端在 `crm.querysets` 提供最新跟进和当前待跟进 queryset，共用于 API 与 Dashboard；无需模型字段或迁移。
- Dashboard 的 `summary.follow_ups_due` 从当前待跟进 queryset 计完整总数；`due_follow_ups` 使用同一 queryset 并仅返回排序最前的 5 条。既有 `Customer.next_follow_up` 同步信号未改动。
- Dashboard「查看全部」跳转到 `/follow-ups?due=true`；单条待跟进跳转到 `/follow-ups?due=true&detail=<id>`。
- 仅 Follow-Up 页面且 `due=true` 时显示「当前筛选：今日及逾期待跟进」上下文条。清除操作只删除 `due`，保留 `detail`、`customer` 和其他查询状态。既有 route query 与搜索请求合并，因此搜索仍由服务端与当前待跟进条件取交集。

## 自动化验证

本地验证结果：

- `python manage.py test crm.tests.test_followup_current_due`：4 项通过，覆盖最新记录判定、同时间戳 ID 决胜、due/customer/search/ordering 组合，以及 Dashboard 完整计数和最多 5 行。
- 后端完整测试：512 项通过，10 项按现有测试条件跳过。
- `python manage.py check`：通过；`python manage.py makemigrations --check --dry-run`：通过，无模型变更。
- 前端 `npm run test:unit`：110 项通过。
- 前端 Vitest 全套：99 项通过，16 个测试文件；路由生命周期聚焦套件 25 项通过。
- `node --test src/views/TaskJ1EntrySafety.test.js`：4 项通过；`node --test tests/detail-drawer-typography.spec.js`：1 项通过。
- `npm run build`：通过。Vite 提示主 bundle 超过 500 KB，这是构建警告，不影响构建结果。
- `git diff --check`：通过。

## UAT-P2C4

| 用例 | 状态 | 记录 |
| --- | --- | --- |
| UAT-P2C4-001 Dashboard 查看全部 | PASS | Dashboard 显示待跟进 4；点击「查看全部」进入 `/follow-ups?due=true`，提示条可见。 |
| UAT-P2C4-002 计数一致 | PASS | Dashboard 数量为 4，筛选页「当前查询结果」为 4，列表显示全部 4 条。 |
| UAT-P2C4-003 仅当前记录 | PASS | 4 条当前项日期分别为 09-30、10-03、10-04、10-05，均不晚于本地日期 2026-10-05。历史列表共 15 条；Alpha 的 2 条逾期记录中，仅最新一条出现在当前列表。CSV Test Customer 的较新记录没有下次日期，其旧的 10-05/10-07 计划未进入当前列表。 |
| UAT-P2C4-004 Dashboard 项目打开详情 | PASS | 点击 Alpha 的 Dashboard 项目后，URL 为 `/follow-ups?due=true&detail=2`，详情标题和客户匹配。 |
| UAT-P2C4-005 关闭详情 | PASS | 关闭详情回到 `/follow-ups?due=true`；提示条及 4 条当前项保留。 |
| UAT-P2C4-006 待跟进内搜索 | PASS | 搜索 `Alpha` 得到 1 条符合记录；清空搜索后恢复 4 条且 `due=true` 提示仍在。 |
| UAT-P2C4-007 清除待跟进筛选 | PASS | 从 `/follow-ups?due=true&customer=1` 清除后变为 `/follow-ups?customer=1`；提示条消失，客户的 2 条历史记录显示。 |
| UAT-P2C4-008 直接 URL 与刷新 | PASS | 直接打开 `/follow-ups?due=true` 并刷新后，提示条和 4 条当前项仍在。 |
| UAT-P2C4-009 Back/Forward | PASS | Dashboard → due 列表 → Back 回 Dashboard → Forward 返回 `/follow-ups?due=true`；提示条和 4 条当前项恢复。 |

## CI 与限制

- PCR-012 开始基线 commit `6886f635e678beb8b52df1ef41f9d52d1f99442b` 的 CI #131：backend、backend-postgres、frontend 均为 SUCCESS（来自本任务提供的交接记录）。
- 代码已推送到 `master`，功能 commit `3f27a99`。通过内置 Browser 打开 GitHub Actions 时页面显示 `Page not found` 并要求登录；`gh run list` 同样返回 HTTP 404。本次远端 run 编号及 backend/backend-postgres/frontend 结果无法核验。基线 #131 的三个 job 均 SUCCESS（来自交接记录）。
- 本地未安装 Docker/psql，也没有可用的 PostgreSQL Windows 服务，故没有在本机重跑 `backend-postgres`。浏览器真实 UI UAT 已全部通过；当前剩余限制仅是本次远端 CI 结果无法读取。

## 变更文件

- `backend/crm/querysets.py`
- `backend/crm/views.py`
- `backend/crm/tests/test_followup_current_due.py`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/ResourcePage.vue`
- `frontend/src/views/TaskJ1EntrySafety.test.js`
- `frontend/tests/route-lifecycle.spec.js`
- `docs/Product-Optimization-Phase2C4-PCR012.md`
