# R1-ISS039-AMOUNT-ALLOCATION-FIX-01

日期：2026-11-03。结论：本轮金额分摊定向补修已完成本地验证，**FIXED_PENDING_REVIEW**；不代表 ISS-039 整体关闭或集成 CI 已通过。

## 基线、范围及交接状态

- 分支：`codex/r1-iss039-amount-allocation-fix-20261103`。
- worktree：`D:\Codex项目\森爵照明管理系统\.worktrees\r1-iss039-amount-allocation-fix-20261103`。
- 审查/修改基线：`8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`。协调线程复核后以 `[skip ci]` 提交推送本独立分支；精确代码 SHA 由最终交付核对远端HEAD，集成分支统一执行三项CI。
- 原审查：[ISS-039 报告，精确 SHA 2d5164287672d9a57a6496761c3ea0d026088072](https://github.com/Johnson-Yiu/SUNJACK-ERP/blob/2d5164287672d9a57a6496761c3ea0d026088072/docs/uat-evidence/r1-iss039-shared-cost-audit-20261103/README.md)。本轮针对 C-01，不重复开发已实现的跨销售采购修改权限。
- 已读本树 AGENTS、REVIEW_PROTOCOL、PROJECT_ISSUES/PROJECT_PHASES 相关记录及原报告。旧台账逐 SO 委托阻塞已被后续专用成本分配实现取代；共享台账及阶段记录由协调维护，本树不改。
- 无迁移、无锁文件/生产配置/权限配置/工作流修改，无真实业务数据库操作，无采购单删除。没有触发 CI、创建 PR、合并或部署。

## 修改清单与规则核对

| 规则 | 实施与证据 |
| --- | --- |
| 新增/修改公共费用只用 amount | `backend/crm/services/purchase_costs.py` 的 `ExpenseInput.method` 只接受 amount，非法值中文 400；`prepare_costs()` 再保护直接服务调用。预览与保存均校验，非仅 UI 隐藏。 |
| 历史 quantity 原样读取 | `cost_summary()` 历史分支及历史 JSON 不变，不迁移、不回填、不自动重算。新增历史读取测试重复 GET 仍为 quantity、500/500，版本/归属不变。 |
| 显式转换、确认、预览、取消 | `PurchaseCostAllocationModal.vue` 加载历史数量法后锁定编辑及保存，展示“本次保存将按金额比例重新计算”。确认后才把本地待提交费用改 amount；成功预览的 payload 指纹必须与当前输入一致才能保存。取消转换、取消未保存编辑均不写库；修改输入/失败/旧预览不能解锁保存。 |
| 新前端费用统一 amount | 不再提供 quantity 选项，显示分摊依据；新费用默认 amount；历史显示“按数量比例（历史记录）”。已转换提示与原算法提示分开，避免将新预览说成历史结果。 |
| 零金额边界 | 正公共费用明确拒绝：“采购金额为零，不能分摊正公共费用；请核对采购金额或移除公共费用。”不回退数量/平均法；无公共费用的零金额归属仍成功。 |
| 金额/尾差守恒 | 仍用原最大余数算法；等数量、单价1000/100、公共费用1000，结果909.09/90.91，总成本12000；分币尾差回归保留。 |
| 权限/版本/生命周期 | 未改专用 `purchases.update` 权限，不恢复逐 SO 授权。既有跨销售、最小候选、只读拒绝、取消目标、旧版本原子性均回归。 |
| 审计、预留、无额外单据 | 认证测试员工且启用审计时，验证 quantity→amount 的 before/after、operator、时间；注入审计失败后所有注册 CRM 模型完整 values 恢复。存在5件合成库存及两条预留时验证回滚和成功重算，成功仍预留3/2件。除 PO、成本归属、审计、派生预留外63个注册 CRM 模型 values 不变，不生成额外付款、库存流水或 SO。 |

改动业务文件仅 `backend/crm/services/purchase_costs.py`、`frontend/src/components/PurchaseCostAllocationModal.vue`。测试修改 `backend/crm/tests/test_purchase_costs.py`、`test_iss039_shared_purchase_costs.py`、`frontend/tests/purchase-costs.spec.js`；新增 `frontend/browser-tests/iss039-amount-allocation-real.spec.js`。其他新增均在本证据目录。

原零金额测试要求 quantity 新保存成功，已依本轮明确规则改为 quantity 拒绝、无费用保存成功；不是删除历史兼容断言，另加历史数量法原样读取、金额转换及预览无写入的强断言。没有删除、skip 或弱化权限/守恒/安全测试。

## 实际环境

- 真实 CPython **3.12.16**：`C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe`；只复用，不安装或修改该环境。
- `verify_environment.py` 实测 requirements.lock **16个精确 pin 全部一致**，包括 Django **6.0.9**、DRF **3.18.3**、Pillow **13.0.0**；pip check：`No broken requirements found.`。不是原审查的全局 Django6.0.6 环境。
- Node **v24.16.0**；本树 `npm ci` 安装227个包，锁文件无差异。安装器报告5个 moderate 风险及 glob/lucide 弃用提示，本轮不升级、不运行 audit fix。
- 真实 Google Chrome **156.0.8078.48**，测试 `test.use({channel:'chrome'})`；无 API mock、无模拟页面、无拼图。
- 后端测试显式 `APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:`、新 TEMP MEDIA_ROOT；权限/审计 override 仅在测试作用域。
- 浏览器通过原隔离运行器先完成直接 Django、Vite、真实 `/api` 代理身份、SQLite 路径、MEDIA_ROOT 及迁移验证。测试 `beforeAll` 在同一已验证运行时调用本目录 `fixture.py` 自建合成数据，脚本再次 `verify_isolated_runtime(settings=..., database_must_exist=True)`。无需专属 seed profile、手动 seed 或共享运行器变更，默认全业务套件也可发现并执行。

## 命令、结果和原始日志索引

以下输出保存在 [execution-logs.zip](execution-logs.zip)，保留失败和原始空白；仅把已清理运行的48位临时隔离 token 脱敏，未改测试状态/报错。松散日志及 runner artifacts 被本目录 `.gitignore` 排除，不提交 trace/临时产物。归档脚本为 [archive_logs.ps1](archive_logs.ps1)。

| 项目 | 最终结果 | ZIP 内日志 |
| --- | --- | --- |
| Python/锁文件/pip check | 16/16 pin 一致、exit0 | `environment.log` |
| Backend 定向综合 | **80项，79通过、1跳过，0失败/错误**；70.167秒 | `backend-final.log` |
| Vitest 相关行为 | **4文件、36通过** | `vitest.log` |
| Node 全量 | **171通过、0跳过**，显式设置锁定 ISOLATED_TEST_PYTHON | `node-final.log` |
| Chrome+真实隔离 API | **1440px、390px共2通过**；49.3秒，exit0 | `browser-complete.log` |
| Django system check | 无问题，exit0 | `check.log` |
| 迁移差异检查 | No changes detected，exit0；浏览器新库全量迁移及 migrate --check 亦成功 | `migrations.log`、`browser-complete.log` |
| 生产构建 | 成功；保留原大于500kB chunk警告，主JS1133.47kB/gzip395.85kB | `build.log` |
| git diff --check | 通过；无共享台账/迁移/锁文件差异 | 交接工作区检查 |

Backend 唯一跳过：`AuditTrailTests.test_postgres_trigger_rejects_raw_update_and_delete`，原因为 `requires a PostgreSQL database; SQLite cannot prove the production DB guard`。本树未跑 PostgreSQL，不用 SQLite 宣称数据库触发器或真实并发通过。原 `test_postgres_concurrency.py::test_purchase_cost_save_allows_one_writer_and_rejects_stale_writer` 保留，由协调集成 PostgreSQL 回归验证。

在 backend cwd 设置上述隔离环境后，以锁定解释器绝对路径执行：

```text
python manage.py test crm.tests.test_purchase_costs crm.tests.test_iss039_shared_purchase_costs crm.tests.test_procurement_data_scope crm.tests.test_integration_039_037_040 crm.tests.test_supplier_allocation crm.tests.test_audit crm.tests.test_functional_rbac --verbosity 2 --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
```

这里的 python 均指上方完整绝对路径，非 PATH/global Python。前端在本树 frontend cwd：

```powershell
npm ci
npx --no-install vitest run tests/purchase-costs.spec.js tests/purchase-workbench.spec.js tests/purchase-safety.spec.js tests/purchase-order-navigation.spec.js --environment jsdom
$env:ISOLATED_TEST_PYTHON='C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe'
npm run test:unit
npm run build
$env:ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT=(Resolve-Path '../docs/uat-evidence/r1-iss039-amount-allocation-fix-20261103').Path
$env:ISS039_EVIDENCE_ROOT=Join-Path $env:ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT 'browser'
node scripts/run-isolated-browser-tests.mjs --business-test iss039-amount-allocation-real.spec.js
```

### 失败过程不隐瞒

初版真实流程两视口通过（`browser-run.log`，尚未补强跨订单 UI 选择）。补强时 `browser-final.log` 两项失败：调用日志明确停在 `.cost-item.first().getByLabel('成本归属', {exact:true})`，未找到选择框；对应 label 包含 select 内的选项文案，精确名称匹配不成立。服务端已有成功200、预期拒绝400，没有该节点的业务提交。将测试定位改为对应商品行 `.cost-row select` 的目标/订单选择框，保持原操作和断言、不增加120秒上限；最终 `browser-complete.log` 两视口跨订单流程通过。失败 error-context 一并归档，不能把中途失败写为产品缺陷或默默删除。运行中修改定位导致失败堆栈源码摘录可能显示新行，原 Call log 仍准确显示旧 getByLabel 定位。

`backend-tests.log` 是增加实有库存/预留断言前的80项通过日志，最终以后者 `backend-final.log` 为准。`node-tests.log` 是未显式设置解释器的先行171项结果，不用于锁定环境声明；最终 `node-final.log` 已显式设置上方绝对路径。完整保留这些先行输出以便复核。

## 真实浏览器/HTTP/数据库证据

最终运行 ID：`9e0ab787-19e5-407d-aaa5-c5a7d181c10b`。API端口10894，Vite端口10896。隔离 SQLite：`C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-3O5oKU\db.sqlite3`，媒体为同根 `media`；运行结束只清理该运行自己的资源和监听进程，端口释放检查通过。没有停止其他工作树服务。

- [桌面HTTP](browser/1440-http.json)、[390px HTTP](browser/390-http.json)：仅合成请求正文、方法、路径、状态、响应，不保存 headers/cookies/身份 token。包含真实 UI GET/POST 及 APIRequestContext 拒绝路径；并非mock。
- [桌面fixture](browser/1440-fixture.json)、[390px fixture](browser/390-fixture.json)：按视口独立的合成 PO/SO/采购行 ID。
- [桌面最终数据库](browser/1440-database-final.json)、[390px最终数据库](browser/390-database-final.json)：67个注册 CRM 模型的持久化 values。测试还在取消转换、预览后、放弃编辑、非法请求后逐次与内存中的前值完整比较，而非仅比较行数；成功保存后允许4个目标/派生模型变化，其他63个模型值不变。非自动注册的 M2M through 表未作全库镜像，不能称为全部物理表逐字节验收。
- 两行数量均10、单价1000/100；旧数量法分500/500，确认转换预览及保存为909.09/90.91。新建费用通过 UI 保存 amount 并分配到两个不同 SO；HTTP/DB 保存值与预览一致。零基数正费用400、无费用200；quantity 的预览/执行均400，完整状态无变化。

### 截图索引

以下全部为实际 Chrome 视口截图，未编辑；所有可见资料为合成数据。桌面1440×1000、窄屏390×844。已人工查看桌面及390px历史说明、转换提示、结果/页脚，按钮文字可读可点击。窄屏结果表保留既有横向滚动，不宣称全部列可同时显示或全局布局已验收。

| 场景 | 桌面 | 390px |
| --- | --- | --- |
| 历史数量法只读、明确转换提示、保存禁用 | [01](browser/1440-01-legacy-readonly.png) | [01](browser/390-01-legacy-readonly.png) |
| 已确认转换、预览完成但未保存 | [02](browser/1440-02-amount-preview.png) | [02](browser/390-02-amount-preview.png) |
| 转换保存成功、历史提示消失 | [03](browser/1440-03-amount-saved.png) | [03](browser/390-03-amount-saved.png) |
| 新费用金额法保存、跨订单归属 | [04](browser/1440-04-new-amount.png) | [04](browser/390-04-new-amount.png) |
| 金额预览结果及守恒，未写库 | [05](browser/1440-05-amount-result.png) | [05](browser/390-05-amount-result.png) |

## 审计边界、剩余风险及后续

- 真实 Chrome 运行器默认 `AUDIT_LOG_ENABLED=0`、开发超级管理员；**没有声称该 UI 写入正式员工审计**，没有伪造默认姓名为真实操作人。真实账号 operator/before/after、失败回滚由 `SharedPurchaseCostPermissionTests` 认证 APIClient 且 AUDIT=true 的隔离测试证明；不是浏览器真实会话审计验收。
- 本地 SQLite 只证明版本过期串行拒绝及事务回滚，不能证明 PostgreSQL 行锁/两个并发提交/死锁行为。最终同 SHA Backend/PostgreSQL/Frontend CI 及全部相关业务套件由协调统一执行。
- 本树不关闭 ISS-039，不改共享台账或全局权限，不扩展供应来源管理/费用付款/库存规则；ISS-006预留并发、ISS-043生产审计防篡改和真实员工权限验收仍分别保留。
- 当前新 API 调用不接受 quantity；历史客户端若直接重发历史 JSON 也会400，需要按提示主动改金额法，不能静默转换服务端算法。UI确认/预览是交互保护，不新增服务端签名凭证/审批协议。
- 历史数量法记录保持原算法直至有权人员明确保存，不扫描或重算业务历史。此报告仅覆盖合成夹具及已列边界，真实业务金额、生产环境、复杂并发/所有汇率不在本轮结论内。

交接：代码、测试及独立证据留在本工作树，供协调复核后统一提交/推送及集成；子任务不提交、不推送、不触发 CI。完成后停止写入，等待独立复审。
