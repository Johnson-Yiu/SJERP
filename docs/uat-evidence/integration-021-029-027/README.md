# ISS-021 / ISS-029 / ISS-027 统一集成验收

日期：2026-10-26
统一基线：`b3559f3bf83b967d06166bd409b00fc92e4e5902`
集成分支：`codex/integration-021-029-027`
独立 worktree：`C:\Users\Johnson\.codex\worktrees\integration-021-029-027\森爵照明管理系统`

## 集成结果

按 ISS-021 → ISS-029 → ISS-027 的顺序从统一基线集成，未覆盖整文件，未修改其他任务分支或 master。

| 任务 | 已审查成果 | 集成提交映射 | 结果 |
| --- | --- | --- | --- |
| ISS-021 | `a662500c06807151bb39ca990ebe17ae8d05ef54` | `3ec2692`、`afc6d17`、`0d3a3b2` | 保留正式 SO 数量调整、付款/采购保护、历史快照、0085 迁移和证据 |
| ISS-029 | `bb68ead4fd248fc446c259a5a142b798b4cd124a` | `273d4a3`、`35517ab` | 保留报价收件人快照、修订继承、PI/Excel 导出和证据 |
| ISS-027 | `5a05a8b0c4d856c9378cad452b1e98307bd135c0` | `d022e35` | 保留跟进日期保留/改期/清除、非法日期校验和全局日期组件改动 |

冲突处理：`backend/crm/serializers.py` 同时保留 ISS-021 的敏感字段脱敏与 ISS-029 的收件人快照继承逻辑；`docs/PROJECT_PHASES.md` 保留三个任务各自阶段记录；`docs/PROJECT_ISSUES.md` 只新增本轮要求的 `ISS-008-FUP-01` 登记。0085 接续当前 0084，未复制旧的冲突迁移或改写已发布迁移。

## 自动化验证

| 验证 | 结果 | 原始记录 |
| --- | --- | --- |
| Django 全量 | PASS：911 tests，skipped=13 | `backend-full.log` |
| ISS-021/029/027 定向后端 | PASS：104 tests | `backend-targeted.log` |
| `makemigrations --check --dry-run` | PASS：No changes detected | `backend-migrations.log` |
| Node | PASS：151/151 | `frontend-node-final.log` |
| 有效 Vitest | PASS：67 files，656 tests | `frontend-vitest-all.log` |
| 生产构建 | PASS；保留既有大 chunk advisory | `frontend-build-final.log` |
| 全新 SQLite 迁移 | PASS：迁移至 0085 | `sqlite-migration.log` |
| SQLite 0084 → 0085 | PASS：先停在 0084，再升级 0085 | `sqlite-migration.log` |

## ISS-027 真实 Chrome 验收

使用 Chrome 扩展连接的真实 Chrome 页面，服务端为独立 SQLite `integration-browser.sqlite3`，前端 28332、后端 28331。合成客户为 `ISS-INTEGRATION-C`，不接触用户业务库。

- 保存：新增“保存验证：保留当前计划”，页面出现“跟进记录已保存”，记录进入列表。
- 改期：新增“改期验证：更新客户计划”，列表显示 `设置新的跟进日期 · 2026-12-05`。
- 清除：新增“清除验证：结束当前计划”，列表显示 `暂不安排后续跟进 · 未安排日期`；客户列表“下次跟进”为 `—`。
- 非法输入：输入 `2026/02/31`，表单显示 `请填写有效且完整的日期。`，点击保存后表单仍在且没有新增记录。
- 保存失败重试：停止本轮自有后端后点击保存，显示 `服务器暂时不可用，请稍后重试。`，输入内容保留；重启同一服务后再次点击保存成功，记录进入列表。
- 客户列表/待办同步：清除场景后的客户 API `next_follow_up=null`，客户列表截图显示 `—`。

截图：

- `followup-save-desktop.png`
- `followup-reschedule-desktop.png`
- `followup-clear-desktop.png`
- `followup-invalid-date-desktop.png`
- `followup-invalid-date-narrow-390.png`
- `followup-save-failure-retain-form.png`
- `followup-save-retry-success.png`
- `customer-list-after-clear.png`

## ISS-029 真实 Chrome 验收

- 新建报价 `SJ20261026DE001`，手工收件人 `集成手工收件人` 和邮箱 `manual-recipient@example.com` 保存成功。
- 创建修订版 `SJ20261026DE001-1`，手工改为 `集成修订收件人`、清空邮箱、填写修订说明；版本谱系显示 2 个版本，修订说明保留。
- PI 预览显示修订收件人 `集成修订收件人`、Email `—`、金额 `USD 10.00`。
- Chrome 页面点击 `导出 Excel`；同一真实服务 API 复核 `/api/quotes/2/export/` 返回 HTTP 200、10236 bytes、Excel Content-Type，文件名 `SJ20261026DE001-1.xlsx`。

截图：`quote-recipient-saved-desktop.png`、`quote-revision-pi-desktop.png`。ISS-029 原有完整 API、PI、Excel 和权限证据仍保留在 `docs/uat-evidence/iss-029-quote-recipient-snapshot/`。

## API / 数据库证据

详见 `browser-api-evidence.json`。最终隔离库事实：客户 `next_follow_up=null`；5 条跟进记录包含原有 `2026-11-12`、改期 `2026-12-05`、清除 `null`、失败重试保存成功；报价修订 `SJ20261026DE001-1` 的 `recipient_name` 为 `集成修订收件人`，`buyer_email` 为空，`revision_no=1`，修订说明保留。

ISS-021 的数量、付款限制、采购保留、历史快照、资金/库存不变证据继续引用 `docs/uat-evidence/iss-021-integration/`；本轮全量后端回归再次通过。

## CI、PostgreSQL 与遗留风险

- 本机未执行 PostgreSQL，明确标记 `BLOCKED`；SQLite 通过不等同 PostgreSQL 验收。
- 当前 `gh auth status` 报告本地 GitHub token 无效，GitHub API 返回 401；`gh run list` 无法读取当前 runs，因此本轮不能虚报精确 HEAD 的 CI 结果。
- 仓库已有的最近可核实证据记录 `40257290673`：三个 job 在启动步骤前失败，原始注释指向账号付款/Actions spending limit；本轮未修改账户、额度或工作流。待仓库所有者恢复认证/Actions 额度后，对最终 SHA 重跑 backend、frontend、backend-postgres。
- 前端 build 的既有 chunk >500 kB advisory 保留，不影响构建成功。

## ISS-008-FUP-01

已在 `docs/PROJECT_ISSUES.md` 登记：`ISS-008-FUP-01 | P2 / OPEN`。本轮仅登记，不开发、不重复创建；说明 249 条 ISO 国家目录已实现，但完整中文标准名称与别名覆盖仍待后续验收。

本轮完成后等待 ChatGPT 独立代码、业务、权限和视觉复审；不合并 master、不关闭 Issue、不部署。
