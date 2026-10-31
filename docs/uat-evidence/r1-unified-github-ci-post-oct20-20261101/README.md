# R1-UNIFIED-GITHUB-CI-POST-OCT20

日期：2026-11-01

分支：`codex/unified-github-ci-post-oct20-20261101`

基线：`25405e1b25ff8a218b67883acf489ada8a53e146`（任务开始时远端 `master`）

## 范围与集成判定

本轮候选来自 2026-10-20 之后已推送且已有代码/验收的集成成果。按 Git 祖先关系、来源集成报告、文件树及提交差异复核；不以分支名称相似作为集成证据。历史任务分支的一些 tip 不是当前集成分支的直接祖先，因为成果曾在后续集成中按最新代码重放/适配；以已进入当前候选祖先的集成提交、源文件差异与随附验收材料共同核实。没有将待做、废弃、重复的报告同步分支计为独立产品成果。

### 主集成来源

| 已集成远端集成分支 | 本轮核实来源 SHA | 覆盖范围 |
|---|---|---|
| `codex/integration-021-029-027` | `28ba758388429f57c2e3516e12385a88ce6646a3` | ISS-021、029、027 |
| `codex/integration-020-022-051` | `f12b591cb90d6a5d8ebfedf1c559703377c92d84` | ISS-020、022、051 |
| `codex/integration-024-019-008` | `b3559f3bf83b967d06166bd409b00fc92e4e5902` | ISS-024、019、008 |
| `codex/integration-026-107-017` | `af018ac63cf71143d223b9f6db4a087707495693` | ISS-026、107、017 |
| `codex/integration-039-037-040` | `71ec4a4c2d860b9944624a1434d9d7580e9a6d38` | ISS-039、037、040 |
| `codex/integration-043-075-023` | `8b2b5c19e517addd9604b239211e199a789b739e` | ISS-043、075、023 |
| `codex/integration-047-097-080` | `7951ecb8c6196f773128ad5978bfcd0a5b30c6b5` | ISS-047、097、080 |
| `codex/integration-018-036-025` | `46353a5436637832f5adadb7bdef6b45cdeada23` | ISS-018、036、025，含后续 ISS-036-FIX-03 核实 |
| `codex/integration-036-002-003-052-058` | `054bd82518039a5bc0e0c14234964a14d7fbbfd8` | ISS-036、002、003、052、058 |
| `codex/integration-049-053-067` | `54925e0a10a48c16ba3b66bbab9e433f48a0e2d7` | ISS-049、053、067 |
| `codex/integration-r1-repairs-20261028` | `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` | 七项 R1 修复及其报告/证据 |
| `codex/integration-pre-pilot-01` | `54e715bdc568b80ba624186fecd866550676cf38` | Issue 状态校准、ISS-008-FUP-01、ISS-002、ISS-028/035、ISS-045 |
| `codex/integration-pre-pilot-02` | `d189084554a2a2da0d701b488a34ebc50723fa17` | 仅集成验证报告；无独立产品代码 |
| `codex/integration-r1-iss006-052-ux-pw-auth` | `bd324a8c3fb64af245c3afcabbd4301c84f7711c` | ISS-006/052 与大范围 UX/Playwright 集成 |

上述集成报告分别位于 `docs/uat-evidence/integration-*/README.md`。单项原始实现/修复中，本候选另核实并包含：ISS-018 恢复安全 `ca2cf58`、ISS-036 快照歧义 `f0c41d9`、ISS-052 上传限制/413/审计链 `403f4a3`、`1c9a86a`、`66ffa7b`、`2f5b7a3`、`ab9ce88`、ISS-006 请求幂等 `1025c0c` 及后续存储失败安全 `f83f9b0`。集成后续防并发/原子性核实提交包括 `94402f9`、`7429c96`、`a4eea21`、`13e8b4b`。

### 增补来源分支及精确远端 tip

| 远端分支 | 核实 HEAD | 纳入内容 |
|---|---|---|
| `codex/repair-history-recipient-typography` | `c3739e77562c5dd8995228d5c3e7375a6728d316` | R1-REPAIR-03 |
| `codex/repair-browser-navigation-timeouts` | `e20f8a7bc506c299644b6c828c9b5574ee688f46` | R1-REPAIR-04-FIX-01 |
| `codex/fix-iss055-chinese-404` | `9c5f1f821cfc1b436f5fffe0b681991fa056b34d` | R1-REPAIR-05 |
| `codex/repair-playwright-isolation` | `5ad252c537dfb0b3f95150e76e471c9fe3fd0a99` | R1-REPAIR-06-FIX-01 |
| `codex/repair-orders-390-layout` | `58541e94918e2d912c2b75d2371a8d625e1fc9d4` | R1-REPAIR-07 |
| `codex/repair-final-cross-module-ux` | `45df13b8fd229427229a58d64d0ae2bec30a00cb` | final-cross-module-ux |
| `codex/repair-supplier-purchase-ux-r2` | `64fb397aa065062e192ceb30040421f59b63a08c` | supplier-purchase-ux-r2 |
| `codex/fix-iss006-request-idempotency-20261029` | `083b99d1f3be5ed6796b71f7dfd5108b2fc12b3a` | ISS-006 persisted request idempotency |
| `codex/r1-iss006-frontend-idempotency-20261029` | `74b1ac29e85a80efbc0ed2200a1653ad19b4bfae` | ISS-006 front-end request identity/storage handling |
| `codex/r1-iss006-frontend-idempotency-bd324-20261030` | `f83f9b08a5f516f860655bc08b6c7d5f0787c35e` | fail-closed browser retry identity |
| `codex/r1-iss006-frontend-storage-chrome-verify` | `bf3d4e4fb1d8bf3e5f944071f4336929ff68beae` | Chrome storage exception/retry verification |
| `codex/r1-iss052-csv-limit-bd324-20261030` | `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b` | CSV limits and audit logging |
| `codex/r1-iss052-http-413-bd324-20261031` | `8cff96af9f1f2e09dcbc0a29f361017ee23ffb75` | HTTP 413 real browser verification |
| `codex/r1-iss052-import-audit-fix-20261031` | `f2b7fd6487459be69be687ccfeab09e7947df995` | import audit traceability |
| `codex/r1-iss052-audit-hardening-20261031` | `70fe8ee1d4ffbd7786f1908804ea7142461d5286` | audit immutability/PG guard evidence |
| `codex/r1-iss007-followup-files-uat-20261031` | `e3b1eeb6cff69b7b77bc35c83661df052e028b41` | ISS-007 attachment-flow UAT |
| `codex/r1-iss007-image-snapshot-uat-20261031` | `d48df222271059721bfa6b9f5f61f395e57db45b` | ISS-007 image snapshot UAT |
| `codex/r1-iss006-inventory-chrome-uat-20261031` | `fb683934cab97d3d721575b4452cb21df2ccc94a` | ISS-006 库存/采购 Chrome UAT 脚本与 1440/390 证据 |
| `codex/r1-iss006-audit-atomicity-bd324-20261030` | `a4eea21dc3e21096950b08439dcbee26ce506e86` | ISS-006 fulfillment audit atomicity |
| `codex/r1-iss006-inventory-reversal-audit-atomicity-20261030` | `7429c9630305bfad61f16475dd5617c13c07959e` | ISS-006 inventory reversal audit atomicity |
| `codex/r1-iss006-po-locking-bd324-20261030` | `13e8b4bed06d0c1d099f007696a81260dfb2d3ef` | ISS-006 receipt/order concurrency locking |
| `codex/r1-iss052-pg-truncate-bd324-20261030` | `bbbb7169e21233fd691af246db722875989d9453` | ISS-052 PostgreSQL TRUNCATE guard |

这些独立远端 tip 已通过候选祖先关系或在后续集成提交中的差异/验收材料确认；其成果已经由上方主集成候选吸收或按当前接口重整，不因最终 tip 未直接作为祖先就误判遗漏。

其中 ISS-006 库存 Chrome UAT tip 是证据包/隔离辅助脚本，不修改产品业务代码；本轮以原样合并保留其报告、API/数据库快照、截图及辅助脚本。该证据不替代 PostgreSQL concurrency UAT。

### 审阅但不作为本轮产品变更纳入的远端分支

| 远端分支 / SHA | 分类与处理 |
|---|---|
| `codex/r1-iss052-http-413-20261031` / `18a18035d1021d5306f5c47d3d55e333f2ea719d` | 不纳入该后续修订：它把 CSV 越限分支改为 `StopUpload(connection_reset=True)`，与原验收“真实客户端收到 HTTP 413，不是连接重置”直接冲突。该修订的浏览器报告记录的是此前 `8cff96a` 版本，不能证明本修订仍返回 413。候选保留已经测试的 `connection_reset=False` 版本，并由 `csv-upload-http-413.spec.js` 及当前完整浏览器套件复验；18a 分支仍须单独修正/复验后再评估。 |
| `codex/r1-iss006-postgres-concurrency-20261031` / `4b43ed561952381bd96dc11abe87392375fb5abd`、`codex/r1-iss006-postgresql-concurrency-uat-20261101` / `10ba6e38a03c955e20be13f303799b30000e6ce3` | 仅 UAT 日志/报告；环境探测未提供 PostgreSQL，明确 BLOCKED。没有可纳入的产品代码；PostgreSQL concurrency 不报告为通过。 |
| `codex/r1-iss052-postgresql-uat-20261101` / `a34bed75edd4e4b07c7a7780f6821a650b06f68c` | 仅 PostgreSQL 阻断报告，无产品代码；保留触发器、原生 SQL、迁移回退的部署验收待办。 |
| `codex/r1-iss028-035-category-verify-20261031` / `5da8d351129e775563aced753fd05efbfc39d893` | 追加的是已有浏览器断言当前 UI 文案及独立截图/日志；本分支的同一断言已按当前文案对齐并在完整 Chrome 隔离套件通过，故不重复导入截图包。 |
| `codex/r1-iss002-python312-verify-20261031` / `8c5840651ab4d40132a1470972ff966340ff1461`、`codex/r1-iss045-python312-verify-20261031` / `a2aaf7d53e73bba8bb4414f8f9c2f8020c88ffb1` | Python 3.12 复验报告/日志；相关实现已由 `pre-pilot-01` 纳入，本轮 CI Backend job 会在 Python 3.12 重新执行。 |
| `codex/r1-iss002-security-audit-final-20261101` / `427d2a2c38516a52d460f50e60e0fb635f23a4c2`、`codex/r1-iss105-financial-audit-20261031` / `7f00efd8a019d1a273675287f53fa73783d73695` | 安全/财务来源审计报告与日志，无产品代码变更；问题状态和审计结论不在本次 CI 集成中修改。 |
| `codex/r1-iss008-aliases-bd324-20261031` / `cffee7e1031f495031f2a4f5040261a398344021` | 国家别名成果已由 pre-pilot-01 集成；该 tip 只追加已执行的测试日志，不重复导入。 |
| `codex/r1-status-reconcile-bd324-20261031` / `ae0f7e073d2ef6cb8b98164920697ecd4bac73be` | Issue 状态对账报告分支；无产品实现差异，台账内容不在本次 CI 分支改写。 |
| `codex/r1-ledger-consolidation-20261031` / `4e762070f825f4545f454a542365ea085f06f2e0`、`codex/r1-issue-ledger-update-20261031` / `dd3b31445ab9dddb42c7ac8d095692df45efde24`、`codex/r1-ledger-review-accept-20261031` / `c8eb1efa2399768ef8933ca402120bee21ebe7f6`、`codex/r1-ledger-sync-20261101` / `bbf98726b550bdb6753d4c72ed7cbd58203e0c20` | 仅共享 Issue/Phase 台账状态更新；未混入产品/测试集成分支，以免本任务改写其他任务的验收状态。 |

ISS-007 附件/图片、ISS-008 国家别名及 ISS-028/035 的后续测试范围由当前源代码、浏览器阶段和既有提交覆盖；未重复导入仅有报告/重复输出的证据副本。ISS-052 PostgreSQL UAT 报告保留为独立阻断证据，不声称已在 PostgreSQL 验证。被废弃、重复或尚未完成的分支不计为通过成果。`audit-ux-visual-20261029` 属审计测试/证据分支，无产品 UI 变更；其审查范围由当前综合浏览器回归及既有独立修复证据覆盖。

## 本轮集成改动

- CI 的 Backend 与 Backend-PostgreSQL 使用仓库锁定的 `backend/requirements.lock`。
- Frontend job 安装 Playwright Chromium 与 Chrome channel，并执行完整隔离浏览器套件 `npm run test:browser`，证据位置由 `R1_PLAYWRIGHT_EVIDENCE_ROOT` 唯一化。
- 锁定 `typing-extensions==4.16.0`，使 Python 依赖锁覆盖当前图像依赖运行所需版本。
- 对齐已确认过时的浏览器测试断言、无障碍名称和 runner 隔离配置；未删除业务断言、放宽验收或更改产品业务规则。
- 为 ISS-006 存储异常/请求身份重试补充真实 Chrome 回归和隔离 seed/verify 工具。
- 补充 ISS-007 隔离 seed 初始化顺序，避免种子在 Django setup 前导入模型。
- 未增加或改写数据库迁移；未修改 Issue/阶段台账、master、生产配置或真实业务数据。

## 本地验收

最终全量本地浏览器证据：`docs/uat-evidence/ci-local-final-20261101/`。`suite-run-summary.json` 的 `allPassed` 为 `true`，各阶段 stdout/stderr 与浏览器截图、HTTP/API 证据均在目录下。

| 检查 | 结果 |
|---|---|
| Django 全量测试 | 1066 项，成功；22 项按既有条件跳过 |
| Django system check | PASS |
| `makemigrations --check --dry-run` | PASS，无模型漂移 |
| 隔离 SQLite 全迁移 | PASS，迁移图到 `crm.0095_merge_fulfillment_idempotency` |
| `pip check` | PASS，无依赖冲突 |
| `npm run test:unit` | 171/171 PASS |
| CI 对应 Vitest | 69 文件、677 项 PASS |
| Node-only typography | 1/1 PASS |
| Playwright 完整隔离套件 | PASS：业务套件 216 项 + 8 个隔离阶段 25 项，共 241 项通过；共享报表、ISS-006 存储、ISS-007 附件/图片、ISS-022、ISS-028/035 Chrome、ISS-055 RBAC 及报价编辑均覆盖 |
| Playwright browser | 实际 Chrome `156.0.8078.48`；ISS-028/035 Chrome 专项 2/2 PASS |
| ISS-006 库存 Chrome UAT 辅助脚本 | 4 个隔离脚本 `python -m py_compile` PASS；浏览器/API/数据库快照与 1440/390 截图按来源验收包保留 |
| 前端生产构建 | PASS；保留既有主 bundle 1,132.30 kB 的体积警告 |
| `git diff --check` | PASS |

初次完整 Playwright 执行发现若干过期的测试定位器/文案、ISS-007 种子未先初始化 Django、以及 ISS-028/035 未安装 Chrome channel；均已定位并最小修复后重跑完整套件通过。没有通过延长等待、删断言、替换业务预期或改产品业务代码掩盖失败。相关最终原始日志保存在上述证据目录。最初失败输出不作为本轮通过结果。

本地没有 PostgreSQL 服务；本地 PostgreSQL 测试未执行，明确由本次 GitHub `Backend-PostgreSQL` job 验证。完整 CI 结果以推送后精确 SHA 的 Actions run 为准。当前工作流要求的三个 job 为 `backend`、`backend-postgres`、`frontend`；不能用本地测试代替任何失败、跳过或未完成的 CI job。

## 待最终填入

- 最终集成 SHA：推送前由 `git rev-parse HEAD` 记录。
- GitHub Actions run URL / run ID：推送后记录。
- `backend`、`backend-postgres`、`frontend` 的最终结论与失败日志：等待该 SHA 的唯一相关 CI run 完成。
- 若 CI 失败，记录完整失败原因、最小修复提交，并对修复后的新最终 SHA 重新运行完整 CI。

约束：本轮不合并 master、不创建发布、不部署、不关闭 Issue，也不删除历史分支。
