# ISS-042-DEV 团队共享报表模板验收

日期：2026-10-23
分支：`codex/iss-042-shared-reports`
基线：`codex/iss-041-detail-drill` / `0bba34c0e7139b77a88d2e838dbf921eff427373`

## 本轮范围

- 新增团队共享报表模板模型、迁移、API、当前权限校验和 `OperationLog` 审计。
- 支持草稿、发布、取消发布、编辑、删除、版本冲突保护和历史读取。
- 报表中心支持模板列表、使用、创建、编辑、发布、取消发布和删除。
- 共享模板只保存经过白名单校验的查询配置，不保存结果快照、用户私有数据或日期；实际查询继续经过当前用户的报表、来源、维度和数据范围校验。
- 旧的单维度/两级分组、URL、个人图表 localStorage、CSV 和明细能力未重建或替换。

数据库变更只有独立迁移 `backend/crm/migrations/0079_shared_report_template.py`，依赖现有 `0078_historical_contract_scope`，未覆盖或修改既有迁移。

## 权限和安全边界

`reports.view` 可查看已发布且当前配置仍可用的模板；`reports.create` 可创建并使用自己的草稿；`reports.update` 可查看、编辑、发布、取消发布并查看完整审计；`reports.delete` 才能删除。来源、维度和筛选字段在服务端重新校验，旧 URL 不能绕过取消发布或权限变化。审计详情对非管理用户不返回配置快照。

详细请求/响应见 `api-template-request-response.json`，权限与审计记录见 `permission-and-audit.md`。

## 测试结论

- 后端共享模板测试：7/7 通过；SQLite 全量后端：799/799 通过，跳过 13 项。
- 既有 `crm.tests.test_reporting`：32/32 通过。
- `crm.tests`：22/22 通过（项目当前自定义测试发现范围）。
- 前端定向 Vitest：7/7 通过；旧概览报表 Vitest：15/15 通过。
- Node 单元测试：143/143 通过。
- 前端生产构建：通过，仅保留既有主 chunk 体积提示。
- 真实 Chrome：共享模板跨管理者/普通用户会话 1/1 通过；既有报表中心 15/15 通过。
- 后端同一模板数据范围：`self` 员工只得到本人客户的 100，`department` 员工得到同部门客户的 300/2 单；模板不会使用发布者身份执行查询。
- 后端来源权限：无 `purchases`/`suppliers` 的员工看不到采购模板；无 `transactions` 的员工看不到银行实际资金模板；撤销 `reports.view` 后访问立即拒绝。

完整命令和原始日志见 `test-results.md` 及同目录 `.log` 文件；PostgreSQL 本机未作为本轮本地测试后端，未声称 PostgreSQL 通过。

## 视觉证据

- `manager-1440px.png`：管理者创建/发布/编辑后的桌面报表中心。
- `manager-1024px.png`：中等桌面宽度下模板管理区域。
- `employee-700px.png`：普通用户跨会话使用已发布模板、保存个人图表；侧栏已收起，无遮挡。
- `employee-700px-after-delete.png`：模板删除后普通用户刷新页面，模板不可用而个人保存图表仍保留。

## 已知限制和后续

本轮不实现共享模板审批流、复制、版本回滚、组织级治理和团队模板统计；这些仍属于 ISS-042 后续范围。ISS-042 台账继续保持 `Enhancement / BLOCKED（延期）`，本轮仅记录 `ISS-042-DEV` 已实施、待独立审查。仓库未创建 PR，不合并 master，不触发 CI。

全量 `vitest run` 仍受仓库既有 runner 混用 Node `node:test` 文件影响，出现大量 “No test suite found”；本轮使用项目标准 `npm run test:unit` 和定向 Vitest 完成验证，具体分类见 `test-results.md`。
