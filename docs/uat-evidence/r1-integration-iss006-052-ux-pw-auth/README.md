# R1-INTEGRATION-ISS006-052-UX-PW-AUTH

集成基线：`54e715bdc568b80ba624186fecd866550676cf38`；目标分支：`codex/integration-r1-iss006-052-ux-pw-auth`；用于本轮回归的集成代码提交：`f9ccfbbdec5df26b269596b50f07eef590fed0f6`。六个远端来源 HEAD 在集成开始前核对，均与下表一致。报告提交自身的最终 SHA 以分支 HEAD 和交付回复为准，避免在提交内容中自指。

| 来源 | 指定 SHA |
|---|---|
| ISS-006 | `083b99d1f3be5ed6796b71f7dfd5108b2fc12b3a` |
| ISS-052 | `dc2bbbb2b29fbc8ffc26c392659e79319c86d592` |
| 财务汇总 UI | `0f440a784130be326357cdf569ccb8959a560771` |
| 报价编辑器 UI | `776d90bcc050bc6ab3ae96a3c8c994e0064e7291` |
| Playwright 稳定性 | `68ceb2953b19f1831e06f7d161e8364902308e4b` |
| ISS-051 认证审查 | `be0a0a392b27efbbcf41a8feed82fb493d52d2a7` |

## 冲突与迁移

- `backend/crm/models.py`：同时保留 `FulfillmentIdempotency`、`CSVImportBatch`、`CSVImportRowAudit`、其索引及追加保护。
- `backend/crm/views.py`：自动合并保留收货/发货幂等调用与 CSV 批次、行级快照及原子事务；定向和全量测试用于验证两侧实际行为。
- `0090_fulfillment_idempotency` 与 `0091_csv_import_audit` 均依赖 `0089_operationlog_operator_protect`；新增无操作 `0092_merge_fulfillment_and_csv_audit`，同时依赖两个分支。新 SQLite 全部迁移成功，CRM 叶节点唯一为 `0092`；另一隔离库在 `0089` 写入哨兵用户后升级，哨兵和三个模型表均保留。日志见 `logs/backend-*`。
- `frontend/scripts/run-isolated-browser-tests.mjs`、`frontend/infrastructure-tests/runner-validation.test.mjs`：保留报价专用 seed 映射、ISS-055 seed 与受控 RBAC 模式，以及独立数据库、媒体目录、端口、代理身份、进程树清理验证。报价用例在完整套件中单独分组，防止共享夹具污染。
- 财务截图改由隔离运行器指定本报告目录；报价截图同样写入本目录。来源分支截图不作为本次视觉验收证据。
- 保留 `docs/ISS-051-正式内部试用认证方案对比.md`，未实施正式登录架构或启用正式 RBAC。

## 当前验证结果

| 项目 | 状态 | 证据 |
|---|---|---|
| Django check、makemigrations、全新迁移、0089 升级及叶节点 | PASS | `logs/backend-*.log`、`backend-migration-results.json` |
| ISS-006 定向 SQLite | PASS / BLOCKED | 7 通过，1 项 PostgreSQL 并发测试跳过；`logs/backend-iss006.log` |
| ISS-052 定向 SQLite | PASS | 18 通过；`logs/backend-iss052.log` |
| 后端全量 | PASS / BLOCKED | 1023 项：1004 通过、0 失败、19 跳过；`logs/backend-full.log`、`backend-test-results.json`。跳过项不能计为通过 |
| 前端单元 | PASS | 171/171，`logs/frontend-unit.log` |
| 隔离运行器 | PASS | 14/14，`logs/isolated-runner-verify.log` |
| 财务卡片定向 / Chrome 截图 | PASS | 12/12，`logs/finance-targeted.log`；`browser/r1_ux_finance_summary_evidence_dir/` |
| 报价编辑器定向 / Chrome 截图 | PASS | 1/1；首次在后端高负载下触及 30 秒总时限，空闲后以原断言和时限 19.8 秒通过。`logs/quote-targeted.log`、`logs/quote-targeted-rerun.log`；`browser/quote-editor-mobile-actions.spec/` |
| 全量 Playwright | FIX REQUIRED | 212 项：211 通过、1 失败、0 跳过；整套命令退出码 1。`suite-run-summary.json` 和 `logs/*-isolated.*.log`、`logs/business-suite.*.log` |
| 前端生产构建 | PASS | `logs/frontend-build.log`；有大于 500 kB 的既有包体警告 |
| git diff --check | FIX REQUIRED | 指定基线至集成代码有来源 Playwright 报告中的两处 Markdown 硬换行空格；新增原始日志与错误现场也有工具输出的尾随空格。排除原始日志和现场后的本报告暂存差异检查通过；原始证据未改写 |
| PostgreSQL 幂等并发、CSV 审计触发器 | BLOCKED | 本机未发现 PostgreSQL 或 Docker 可执行环境；SQLite 结果不能替代 |

测试使用本次工作树、本地 Chrome 156.0.8078.48、Python 3.14.5、Django 6.0.8、Node 24.16.0 和临时 SQLite/MEDIA_ROOT。财务卡片在 1024px 对 200 亿元合成金额的最后一位数字换到新行，完整内容未被截断；该可读性观察保留供后续评估。

### 浏览器全量分组与剩余问题

常规业务组 201/201、报价编辑器 1/1、ISS-022 1/1、ISS-028/035 2/2、ISS-055 6/6 均通过；共享报表模板 0/1。ISS-055 使用独立员工、真实 Django 测试登录会话及仅针对临时库的受控 RBAC 设置，并非生产权限验收。各组日志均记录本轮自有进程树停止、端口释放以及临时数据库和媒体目录清理。

**FIX REQUIRED：** `shared-report-templates.spec.js` 在 30 秒总时限内覆盖两个浏览器上下文的多次编辑、发布和刷新。全量执行在员工刷新后的模板断言处超时；原断言、原时限的隔离复测仍超时，但推进至后续取消发布后的刷新。失败现场分别见 `artifacts/a4269d39-dd60-4c13-83c9-f5afdcfd03f3/`、`artifacts/c382ac13-614a-49de-84f4-41112a7ffa54/`，原始及复测日志见 `logs/shared-report-templates-isolated.*.log`、`logs/shared-report-targeted-rerun.log`。目前证据只能说明测试在该机器上无法稳定在现有限时完成，尚不能认定业务数据缺陷或确定耗时根因；建议后续分析页面加载、截图及运行环境负载并修复稳定性后重新全量回归，不应仅通过增加超时掩盖。重跑结果不替代全量命令的失败结果。

**NEEDS VERIFICATION：** 本机仅发现 Python 3.14，未在 Python 3.12 环境复测。Chrome 测试输出还出现订单详情抽屉 `Transition` 非元素根节点动画警告，以及无序分页警告；本轮未确认其生产影响，应另行评估。

首次后端全量执行 1023 项、11 项失败、19 项跳过；失败全部来自运行脚本将 `AUDIT_LOG_ENABLED=0` 传给模拟 staging/production 的配置子进程，使其先触发审计配置校验。原始输出保存在 `logs/backend-full-first-attempt.log`。移除该环境覆盖后，配置定向测试 16/16 通过，全量重跑 1004 通过、19 跳过、0 失败。第一次 `0089` 升级夹具因只应用 `auth.0001` 而无法写入用户；`logs/backend-upgrade-seed-first-attempt.log` 保留该失败，补齐 auth 迁移后的独立重跑通过。
