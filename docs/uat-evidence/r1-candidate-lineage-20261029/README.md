# R1-CANDIDATE-LINEAGE-01 集成来源核验报告

日期：2026-10-29
固定审查基线：`54e715bdc568b80ba624186fecd866550676cf38`
审查分支：`codex/audit-integration-lineage-20261029`
审查 Worktree：`C:\Users\Johnson\.codex\worktrees\audit-integration-lineage-20261029\森爵照明管理系统`

## 结论

本轮为只读来源审查，没有执行合并、cherry-pick、业务代码修改、Issue 状态修改或 CI 配置修改。

- 七项前序修复来源均已进入固定基线：七个指定来源 SHA 是基线的字面祖先，并分别作为非快进合并的第二父提交进入。
- 五项本轮指定成果也已进入固定基线：其原始来源 SHA 不是基线字面祖先，但每项都有对应的集成提交；`git patch-id --stable` 与来源逐项相同，且集成提交均为基线祖先。这是 cherry-pick 后的正常 SHA 变化，不是缺失。
- 没有发现“只有验收报告、实际实现没有进入候选基线”的指定成果。需要特别区分：R1-REPAIR-03 和 final-cross-module-ux 的来源 tip 主要是证据/文档提交，但它们的代码或测试提交在来源 tip 的祖先链中，均随合并进入基线；final-cross-module-ux 本身没有产品业务代码改动，只有测试夹具/验收证据，符合该任务范围。
- 另一个相似名称的供应商分支 `codex/repair-supplier-purchase-ux-20261028`（`fe1cc16c3950e256fa564ea4508e08414ae8810b`）不是七项指定来源 `codex/repair-supplier-purchase-ux-r2`（`64fb397aa065062e192ceb30040421f59b63a08c`），也不是固定基线的祖先；本轮没有把它误判为已集成。
- 数据库迁移没有来自这十二项来源的新增文件。固定基线的并行迁移编号均有显式 merge migration；未发现由本轮来源造成的同名迁移冲突。

结论只代表来源进入固定候选基线，不代表任何 Issue 已整体 `CLOSED`，也不替代真实员工、生产 PostgreSQL、生产部署、CI 或独立业务/视觉复审。

## 已读取材料

本轮完整读取并按精确基线核对：

1. `AGENTS.md`
2. `docs/REVIEW_PROTOCOL.md`
3. `docs/PROJECT_ISSUES.md`（479 行）
4. `docs/PROJECT_PHASES.md`（587 行）
5. `docs/uat-evidence/integration-r1-repairs-20261028/README.md`
6. `docs/uat-evidence/integration-pre-pilot-01/README.md`

台账与协议的状态边界已保留：`FIXED_PENDING_REVIEW` 不等于 `CLOSED`；阶段成果可封版不自动关闭整体 Issue；未执行、生产阻断和业务待决项不能由本地代码或报告推断为通过。

## 核验方法

在固定基线和新独立分支上执行了以下只读核验：

```text
git show-ref / git rev-parse
git log --first-parent --oneline --decorate 54e715bdc568b80ba624186fecd866550676cf38
git merge-base --is-ancestor <source-or-integrated-sha> 54e715bdc568b80ba624186fecd866550676cf38
git show -s --format='%H%n%P%n%s' <integration-merge>
git diff --name-status <fixed-base> <source>
git show --stat --no-renames <source-or-integrated-sha>
git show <sha> --format= | git patch-id --stable
git ls-tree -r --name-only <fixed-base> -- backend/crm/migrations
git grep -n -I <implementation-keyword> <fixed-base>
```

`merge-base --is-ancestor` 结果和来源/目的提交的 patch-id 均在下表记录。没有用相似分支名称、报告标题或单个截图替代提交证据。

## 七项前序修复来源

### 来源祖先与合并提交

| 项目 | 指定来源分支 / 精确 SHA | 来源链中的代码/测试提交 | 基线中的合并提交 | 结果与差异 |
|---|---|---|---|---|
| R1-REPAIR-03 历史收件人/排版 | `codex/repair-history-recipient-typography` / `c3739e77562c5dd8995228d5c3e7375a6728d316` | `39067e5d4c706d0fb2689c1cf62dae9036f26a3d` | `cee0bca64c1ac20ac06010f48977604dee16c853`，第二父为来源 SHA | **已集成**。`c373...` tip 是日志/XLSX/验收证据提交；修复 `39067...` 在其祖先链中，实际页面组件与测试随合并进入。 |
| R1-REPAIR-04-FIX-01 浏览器导航/报表/库存 | `codex/repair-browser-navigation-timeouts` / `e20f8a7bc506c299644b6c828c9b5574ee688f46` | `ce6bbf5a05d47000a06962b0bf2f444d84e7e5ca` | `d94aa3619d384406d89aa529af744ed54639a01f` | **已集成**。来源含测试与证据修订；无迁移文件。 |
| R1-REPAIR-05 ISS-055 中文 404 | `codex/fix-iss055-chinese-404` / `9c5f1f821cfc1b436f5fffe0b681991fa056b34d` | 来源 tip 同时包含后端实现、测试和证据 | `b9b949c19604938c9f84ae1e3fa30e66ea99250c` | **已集成**。`context.py`、`views.py`、错误文案、范围测试及浏览器证据均在来源差异中。 |
| R1-REPAIR-06-FIX-01 Playwright 隔离 | `codex/repair-playwright-isolation` / `5ad252c537dfb0b3f95150e76e471c9fe3fd0a99` | `315bd32dac9b1aa2f1e2f7e7d9e0584d55b1828c`、`10902fcda27c2784f627d40f8fc84858a2d70847` | `57ebeb2ebae364b40d408265837284f8e13ab70f` | **已集成**。隔离 runtime、Vite/Playwright 配置和 runner 自测完整保留。 |
| R1-REPAIR-07 390px 订单布局 | `codex/repair-orders-390-layout` / `58541e94918e2d912c2b75d2371a8d625e1fc9d4` | 来源 tip 同时包含 `DocumentPage.vue`、浏览器测试和多视口证据 | `8487adb59979aa2ac7f2c6be40eec3a510be0d96` | **已集成**。产品页面一行布局修复、测试和 DOM/截图证据均在基线。 |
| final-cross-module-ux | `codex/repair-final-cross-module-ux` / `45df13b8fd229427229a58d64d0ae2bec30a00cb` | `aa4140291aa46db9b8b17fce762d4e52aa31f17e` | `18bf5c302c1e0956c7c7ea082303fbc72c996a47` | **已集成**。来源 tip 主要恢复台账并附截图；代码差异是 `final-cross-module-ux.spec.js` 的 mock/夹具对齐，没有产品业务代码。 |
| supplier-purchase-ux-r2（ISS-022/075） | `codex/repair-supplier-purchase-ux-r2` / `64fb397aa065062e192ceb30040421f59b63a08c` | 来源 tip 为测试、日志和截图证据 | `5a536d46dc8e747b942fa15aaffe00b9e34767e0` | **已集成**。供应商/采购浏览器测试与回归证据在基线；`84da66e963414002576b653cf8d9340dafcbc2d6` 另补隔离 fixture 支持。 |

七次 merge 的共同特点是来源 SHA 为第二父，均可通过 `git merge-base --is-ancestor <source> <baseline>`；没有用目标分支的同名报告替代来源代码。合并提交均带 `[skip ci]`。

### 相似但未指定的分支

`codex/repair-supplier-purchase-ux-20261028` 的 tip 为 `fe1cc16c3950e256fa564ea4508e08414ae8810b`，对固定基线的字面祖先核验为 `False`。前序集成报告明确只抽取了其中两条 Google Fonts 路由拦截到 R2 测试，没有合并该分支其余提交；本轮保留这一差异，不把它列为遗漏，也不把分支名相似当作已集成。

## 五项指定成果

这五项是从 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` 系列集成到固定基线的 cherry-pick 结果。原始来源 SHA 因父提交不同而不是固定基线的字面祖先，但目的提交的补丁 ID 与来源相同，且目的提交是基线祖先。

| 成果 | 原始来源分支 / SHA | 基线中的等价集成提交 | patch-id（来源 = 集成） | 实际差异与结果 |
|---|---|---|---|---|
| Issue 状态对账 | `codex/reconcile-issue-ledger-20261028` / `2bb9d1746d13ce7b1c70e13dee1b8d3b48aaed2e` | `2303c573465701e40db922654e2ae4d25fa5a626` | `dbcee15cddbba600b62c9d06918df11f32289b3c` | **已集成**。只改台账、阶段、协作规则和对账报告，符合该成果的文档范围；不是业务代码提交。 |
| ISS-008-FUP-01 中文国家别名 | `codex/fix-iss008-chinese-aliases` / `80dc73ae4ae47f9e04969f39b441af206d34306b` | `7de261e4e50758b7ba7809170be0a20cb5d384e7` | `506614373f9c90730d80a0c4ada249b096d184fc` | **已集成**。`country_registry.py`、后端/前端测试、浏览器截图和覆盖报告均来自等价补丁；没有迁移。 |
| ISS-002 Python 依赖安全 | `codex/repair-iss002-python-security` / `85adec7d99d725c7c920c728385172d6517730ce` | `3961ef6c4b0499adb0689f14be73372692ddac3f` | `35934818d2874d576ed7874df0f64f62ac4fbee0` | **已集成**。`backend/requirements.txt`、`requirements.lock` 和安全报告均在基线；没有迁移。锁定依赖的干净环境真实安装仍按报告为后续验收，不因文件存在而关闭 Issue。 |
| ISS-028 / ISS-035 分类与 SKU | `codex/verify-iss028-035-category-schema` / `901b762fba20ed558f554cfba37175b303f83db9` | `47fcab0f6f37f52475074e65ab7ab188352ae8ce` | `0e2d30e9d072f31c760fc7b7c0b0e4d3fe566943` | **已集成**。`ProductPage.vue` 的根分类最小修复、隔离 Playwright、API/DB 快照和桌面/窄屏证据均在基线；没有迁移。 |
| ISS-045 旧 QA 工具 | `codex/audit-iss045-legacy-test-scripts` / `966deaa209cd5b115704a67e58aeb12783b9a60` | `72a6b27f3f855424f16cd9657996055c68b5ca95` | `41b5e5ab021a470cb4139407eac9b0760d3ddfff` | **已集成**。两个旧命令的退役保护、`seed_demo` 隔离拒绝、测试和文档均在基线；没有迁移。 |

原始来源与等价集成提交的 `git diff --quiet <source> <integrated>` 不能作为补丁等价判断，因为它们的父树不同；本轮使用 patch-id 和最终文件/提交祖先双重核验。除状态对账这一项外，其余四项均包含实际实现或测试代码，不是只有验收报告。

## 报告与实际代码核对

| 检查项 | 可核实事实 | 判定 |
|---|---|---|
| ISS-008 国家目录 | 固定基线只有一个 `backend/crm/country_registry.py`；`CustomerSerializer`、`CustomerViewSet` 和前端选择器仍引用同一入口。集成报告记录 `/api/customers/country-catalog/` 的列表契约、中文名/别名、alpha-2/alpha-3 和歧义拒绝。 | **代码与报告一致**；完整 249 条中文标准名/别名的独立逐项验收仍是 `ISS-008-FUP-01` 的后续关闭条件。 |
| ISS-002 Python 依赖 | 固定基线存在唯一 `backend/requirements.lock`，且来源 patch 修改 `requirements.txt` 与 lock 文件；pre-pilot 报告记录 lock dry-run 与当前环境 `pip check`，没有把未执行的干净环境安装写成通过。 | **代码与报告一致**；Pillow 兼容、生产镜像和真实部署依赖仍未关闭。 |
| ISS-028 / ISS-035 | 固定基线存在唯一 `frontend/src/views/ProductPage.vue` 和专项浏览器 spec；ProductPage 差异只有根分类直接归类所需的最小改动，快照/历史边界通过证据保留。 | **实际代码已集成**；台账最新行仍是 `NEEDS_VERIFICATION`，这与“专项实现已进入候选基线”并不矛盾，但后续应以最新专项证据校准台账，不得自动 CLOSED。 |
| ISS-045 旧命令 | 固定基线各只有一个 `run_business_flow_checks.py`、`run_edge_business_flow_checks.py` 和 `seed_demo.py`；旧命令抛出 `CommandError`，不是从启动路径删除或重新接入。 | **代码与报告一致**；台账仍是 `NEEDS_VERIFICATION`，表示需独立 QA/协议复审，不是报告丢失。 |
| 七项 R1 修复 | 七个来源 SHA 都在 merge commit 第二父，来源链中的代码/测试提交也在候选历史；报告、测试、截图和实现文件均可从固定基线定位。 | **没有报告-only 遗漏**。R1-03/final-cross-module-ux 的 tip 仅证据/台账或测试夹具的情况已在上表显式标注。 |

## 台账/阶段状态差异（仅记录，不修改）

本轮没有改 `PROJECT_ISSUES.md` 或 `PROJECT_PHASES.md`。核对结果如下：

1. `ISS-028`、`ISS-035` 的最新台账行仍按 2026-10-28 状态对账记录为 `NEEDS_VERIFICATION`，其中写有当时专项分支尚未形成修复交付；随后 pre-pilot 已将 `901b...` 等价补丁集成并记录 2/2 隔离浏览器通过。这里是“台账描述落后于候选基线来源”的差异，不是代码缺失；应在下一轮专门做状态/独立复审校准，不能在本轮擅自改状态或关闭。
2. `ISS-045` 最新台账行仍为 `NEEDS_VERIFICATION`，没有把退役实现自动记为 CLOSED；这是协议要求的待复审状态，代码已存在与状态未关闭需同时保留。
3. `ISS-002` 最新台账仍强调 Pillow、生产依赖和完整 lock/部署验收缺口；固定基线已包含 `requirements.lock`，因此“缺少 lock”这段历史描述需要后续校准，但生产依赖及 Pillow 风险仍真实存在，不能据此改为 CLOSED。
4. `ISS-008-FUP-01` 仍为 `P2 / OPEN`。代码/别名实现进入候选基线不等于 249 条标准中文名称逐项验收完成，状态保留是合理的；后续需要补充完整目录逐项证据。
5. R1-REPAIR-CONSOLIDATION-01 和 R1-INTEGRATION-PRE-PILOT-01 报告都保留 `FIXED_PENDING_REVIEW`、`BLOCKED`、`DEPLOYMENT_VERIFICATION_PENDING`、真实员工/生产数据待验等边界；本报告没有将阶段集成通过扩大成整体封版或生产就绪。

## 数据库迁移图与重复实现

静态检查固定基线 `54e715...` 的 `backend/crm/migrations`：

- 本轮十二项来源的差异均没有迁移文件；来源路径核对结果为 0 个 migration 文件。
- 同编号文件只有历史并行分支：`0021` 两个、`0029` 两个、`0081` 三个。它们分别由 `0022_merge_20260823_2351`、`0030_merge_sku_identity_and_quote_counter`、`0082_merge_iss026_iss107_iss017` 汇合；`0082` 明确依赖三个 `0081` 分支，没有删除或覆盖历史迁移。
- 汇合后链继续到 `0083_customer_supplier_preference`、`0084_alter_orderitem_supplier_allocation_scope_and_source`、`0085_order_quantity_adjustment`、`0086_purchase_moq_exception`、`0087_amount_calculation_compatibility`、`0088_operationlog_append_only`、`0089_operationlog_operator_protect`。这些均不来自本轮五项成果，未见同名新增或重复迁移实现。
- 本轮只读执行 `python manage.py check` 通过；`python manage.py makemigrations --check --dry-run` 返回 `No changes detected`，但因当前 worktree 默认数据库文件无法打开产生一致性历史检查 RuntimeWarning。该命令不能替代隔离新库全量迁移；pre-pilot 报告已有新库/迁移链至 `0089` 的证据，本报告不扩大为生产数据库验证。

重复实现检查结果：`country_registry.py`、`ProductPage.vue`、`requirements.lock`、两个旧 QA command 各只有一个运行时实现；测试/证据文件的多个目录是按任务归档，不是重复业务实现。

## 分类结果与后续建议

### 已集成

- 七项前序修复来源及其代码/测试/证据祖先链。
- Issue 状态对账文档成果。
- ISS-008 中文目录/别名代码与测试。
- ISS-002 Python requirements/lock 变更。
- ISS-028/035 ProductPage 与隔离验证。
- ISS-045 旧 QA 命令退役保护。
- 迁移图中的历史 merge 分支和最新迁移文件均可定位，未出现本轮新增冲突。

### 存在差异

- 五项成果的原始 SHA 与候选基线中的等价集成 SHA 不同，但 patch-id 相同，属于 cherry-pick 后正常差异。
- R1-REPAIR-03、final-cross-module-ux、supplier-purchase-ux-r2 的来源 tip 偏证据/测试；对应实现或测试祖先已核实存在，不能只看 tip 的文件统计。
- `PROJECT_ISSUES.md` 对 ISS-028/035/045/002 的最新文字没有完全反映 pre-pilot 后的来源集成，但仍保留必要的待复审/安全边界；后续应单独做台账校准，不在本审查中修改。
- `codex/repair-supplier-purchase-ux-20261028` (`fe1cc16...`) 与指定 R2 来源不同，未纳入。

### 缺失

对用户指定的七项 + 五项成果，未发现代码/测试/报告来源缺失。该结论仅限固定基线的 Git 来源完整性，不是生产环境功能验收。

### 无法核实 / 保留待验

- 本轮没有连接生产 PostgreSQL、正式员工/RBAC 会话、生产文件/代理或真实部署卷。
- 未触发 GitHub Actions；本地报告中的 CI/计费阻断仍不能改写为 CI PASS。
- 没有重新执行完整浏览器套件、Vitest 全量或干净环境的 lock 实际安装；沿用两份集成报告的原始结果和阻断分类，不把未执行项目写成通过。
- ISS-008-FUP-01 的 249 项标准中文名称逐项覆盖仍需单独验收；ISS-002 的 Pillow/生产锁定风险、ISS-028/035 的独立状态复审、ISS-045 的 QA 工具协议复审仍需后续处理。

## 本轮变更与限制

- 业务代码、模型、迁移、前端实现、Issue 状态及 `.github/workflows/`：未修改。
- 仅新增本报告和验收索引条目。
- 未执行 merge/cherry-pick，不创建 PR，不合并 master，不关闭 Issue，不部署，不触发 CI。
