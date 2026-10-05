# SUNJACK-ERP Product Optimization Phase 2C-4 — PCR-012

## 验收状态

**实现与自动化回归已完成；PCR-012 整体状态为待真实 UI UAT，不标记 PASS。** 必须完成的 UAT-P2C4-001 至 009 尚未执行，原因是本轮 Browser 插件的 REPL 已重置且没有可复用的 Browser agent。按 Browser 插件文档要求，本轮没有改用 Computer use、底层浏览器 RPC 或其他浏览器通道。

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
| UAT-P2C4-001 Dashboard 查看全部 | 未执行 | 待在内置 Browser 中确认 URL 与上下文条。 |
| UAT-P2C4-002 计数一致 | 未执行 | 自动化 API 测试确认 Dashboard 总数等于 due API 完整 count；真实 UI 对照待执行。 |
| UAT-P2C4-003 仅当前记录 | 未执行 | 后端自动化覆盖 superseded future/no-date 历史；真实数据行检查待执行。 |
| UAT-P2C4-004 Dashboard 项目打开详情 | 未执行 | 待真实 UI 确认 URL 同时保留 due 与正确 detail。 |
| UAT-P2C4-005 关闭详情 | 未执行 | 自动化路由测试覆盖清理 detail 时保留 due/customer；真实 UI 待执行。 |
| UAT-P2C4-006 待跟进内搜索 | 未执行 | 自动化路由与 API 测试覆盖过滤组合；真实 UI 待执行。 |
| UAT-P2C4-007 清除待跟进筛选 | 未执行 | 自动化路由测试覆盖仅移除 due 并保留其他键；真实 UI 待执行。 |
| UAT-P2C4-008 直接 URL 与刷新 | 未执行 | 路由自动化覆盖直接 URL/remount；真实浏览器刷新待执行。 |
| UAT-P2C4-009 Back/Forward | 未执行 | 自动化路由测试覆盖状态恢复；真实浏览器历史操作待执行。 |

## CI 与限制

- PCR-012 开始基线 commit `6886f635e678beb8b52df1ef41f9d52d1f99442b` 的 CI #131：backend、backend-postgres、frontend 均为 SUCCESS（来自本任务提供的交接记录）。
- 当前变更的 GitHub Actions run 尚未核验。本地未安装 Docker/psql，也没有可用的 PostgreSQL Windows 服务，故未在本机重跑 `backend-postgres`；需要提交推送后查看远端 CI。
- 当前主要限制是必须完成的 9 项真实 UI UAT。完成前不得将 PCR-012 标为 PASS。

## 变更文件

- `backend/crm/querysets.py`
- `backend/crm/views.py`
- `backend/crm/tests/test_followup_current_due.py`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/ResourcePage.vue`
- `frontend/src/views/TaskJ1EntrySafety.test.js`
- `frontend/tests/route-lifecycle.spec.js`
- `docs/Product-Optimization-Phase2C4-PCR012.md`
