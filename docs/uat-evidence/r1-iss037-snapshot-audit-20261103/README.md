# R1-ISS037-HISTORICAL-SNAPSHOT-AUDIT（任务 B）

审查日期：2026-11-03。精确审查 SHA：`8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`。

工作树：`D:\Codex项目\森爵照明管理系统\.worktrees\r1-iss037-snapshot-audit-20261103`。
分支：`codex/r1-iss037-snapshot-audit-20261103`。开始时工作区干净；本轮仅在本目录新增报告、复现 probe 和日志 ZIP，业务源码、已有测试、迁移、正式配置与共享台账均未改动；未创建 PR、触发 CI 或连接业务库。审查取证完成后由主代理复核并以 `[skip ci]` 提交推送本独立分支。

## 结论与判定边界

现有实现确实包含销售订单六项客户快照、采购单五项供应商快照，以及报价买方/商品/图片快照和报价修订链。本轮现有定向测试 **116 项通过、0 skip、exit 0**；补充行为 probe **3 项通过、0 skip、exit 0**；历史迁移 probe **2 项通过、0 skip、exit 0**。probe 的通过表示成功验证观察到的行为，**不表示七项规则通过**。首次行为 probe 有 1 个证据脚本错误，原始失败日志保留，详见测试章节。

当前不能据此将 ISS-037 全范围关闭：已复现历史空买方的新修订被当前主档填入、同一保存报价的卖方随共享模板改变；旧 0012 迁移的回填来源也无法等同交易时主体。完整双方字段、主体修订审批分离及法律主体变更流程属于当前规则要求下的范围缺口，应与这两项当前行为缺陷区分。

没有执行 Chrome、PostgreSQL、真实员工、生产数据或 CI 验收；本报告不是产品封版或上线验收。历史报告的 Chrome/PG/CI 状态不移植为本轮结果。

## 已读规则与历史证据

- 本工作树 `AGENTS.md`、`docs/REVIEW_PROTOCOL.md`、`docs/PROJECT_ISSUES.md` 和 `docs/PROJECT_PHASES.md` 的相关 ISS-020/021/029/037、权限、迁移和集成条目。
- `docs/uat-evidence/r1-iss-037-p1/README.md`、`INTEGRATION-README.md`、`r1-iss-037-p1-fix-01/README.md`。
- `docs/uat-evidence/iss-020-quote-export/README.md`、`iss-029-quote-recipient-snapshot/README.md`。
- `docs/Product-Completion-Review-Phase1.md:123` 起的快照边界、`docs/Product-UX-Second-Review.md:403`、`:477` 起的历史 UAT。

历史结论仅用于定位：旧“订单只有实时客户关系”的记录已经被六项快照实现取代；原有收件人空值、非空买方导出及图片快照测试有效，但没有覆盖本轮发现的**买方公司名称本身为空**。旧未发布 `0078_formal_party_snapshots` 不是当前迁移；当前为 `0080_formal_party_snapshots`，依赖 `0079_shared_report_template`。按用户本轮限制，不执行协议中写共享台账、提交、远端/CI 的步骤，由主审复核后处理。

## 风险与验收矩阵

| 范围/入口 | 正常路径核实 | 拒绝/历史边界核实 | 本轮方式 |
|---|---|---|---|
| Quote/QuoteItem、指定报价 PI API/XLSX | 保存版本买方及商品、图片、金额、币种；修订保留父版 | 保存报价禁止 PUT/PATCH/删除；无权限导出；历史空值 | 现有测试；3 项行为 probe；源码 |
| Order/OrderItem、正式确认 | 来源报价买方五项与确认时客户国家，或无报价时主档六项一次捕获 | 快照只读、正式商业字段禁改、失败回滚、无权脱敏 | 现有测试；源码 |
| PurchaseOrder/Item、正式下单 | 供应商五项一次捕获、采购来源行快照 | 正式商业字段禁改、同内容 PUT 不重建行、无权脱敏 | 现有测试；源码 |
| 主体修改/审批 | 现有报价修订、数量调整、金额变更各自边界 | 主体名称修订、双方完整字段、发起人与审批人分离 | 行为 probe + 源码，缺失要求另列 |
| 迁移/旧数据 | 新内存库全迁移、0080 升降级、现金历史迁移 | 0012 回填来源、0080 不猜测历史 | 现有迁移测试 + 2 项真实 MigrationExecutor probe |

## 七项规则逐条结论

| 规则 | 状态 | 当前证据与不足 |
|---|---|---|
| 1 报价、SO、PI、PO 及正式导出对应版本快照 | **部分实现** | Quote/QuoteItem 有保存版本及修订链，PI 买方/商品 DTO 使用指定 Quote；SO/PO 有确认/下单快照。卖方来自当前共享模板/前端常量，未绑定版本；未发现 SO/PO 独立完整双方正式文件导出实现，不能用 API 字段或 PI 导出来代替。见 D2、M1。 |
| 2 完整买卖双方名称、地址、联系人、联系方式、账单/收货地址、收件人、税务注册信息 | **部分实现** | 六项客户/五项供应商及 Quote 买方五项已实现；双方完整结构、分离账单/收货地址、税务注册快照未实现；PI tax_id 明确为空，卖方来自模板/常量。见下表及 M1。 |
| 3 正式确认或签发冻结 | **部分实现** | 已有字段在报价保存后即禁止原地改，SO 确认、PO 下单在事务内冻结且序列化只读；但冻结未覆盖不存在的完整主体字段、卖方、模板版本及文件内容。不是“现有六/五项未冻结”。 |
| 4 正式修改新版本并保留旧版 | **部分实现** | Quote 修订保留 root/parent/revision_no/summary，收件人四字段可独立修订。buyer_company_name 只读，提供新名称也被忽略；SO/PO 正式主体字段禁止直接修改，但无对应主体修订版本流程。数量版本/金额变更不等同主体版本。见 M2。 |
| 5 发起与审批分离 | **未实现（主体变更范围）** | 未见主体变更申请及独立审批状态/身份；Quote revise 直接创建版本。ContractChangeRequest 是金额变更，不能承载主体变更，模型无发起/审批身份字段，approve 服务不比较两人身份。不是对开发超级管理员授权的否定，不要求本轮启用 RBAC。见 M3。 |
| 6 历史未知待核实，不以当前主档冒充 | **部分实现** | 0080 新字段空值保留未知，SO/PO UI 明确提示；非空保存买方和收件人空值不回落主档。但买方公司为空的修订触发当前主档回填（D1），旧 0012 迁移也将当时主档写为快照、无来源标记（H1）。 |
| 7 区分主档更新和法律主体变更 | **未实现（业务流程层）** | 界面“当前主档参考”已能区分当前资料与旧快照，但 Customer/Supplier 普通修改没有法律主体变更类型、有效期、证据、审批或版本链接。资料改正与合同主体替换未建立不同流程。见 M2/M3；禁止以直接修改旧快照补齐。 |

## 主体字段到正式文件的实际覆盖

| 主体/字段 | 保存与冻结 | 正式文件消费情况 |
|---|---|---|
| Quote 买方：公司、收件人、地址、邮箱、电话 | `models.py:889`、`:898`；创建缺省预填 `QuoteSerializer.create`（`serializers.py:1996`），显式空值保持；保存后 update 拒绝（`:2020`） | `quotation_export_dto.py:126`–`:132` 原值进入 buyer；`views.py:1885` 起 PI API；模板 B3/B4/B5/B7/B8 写入买方字段。正常导出无 Customer/Contact 兜底。 |
| SO 买方：名称、国家、地址、联系人、电话、邮箱 | `models.py:1046`–`:1051`；`order_lifecycle._capture_order_party_snapshot:46`、`confirm_order:81`。有报价时五项来自报价，国家来自确认时当前客户（`:59`），Quote 不保存国家 | 已核实 API、列表/详情消费者；不是独立 SO 正式文件全字段覆盖证据，也不能由报价 PI 推导 SO 文件已具备同样快照。 |
| PO 卖方：名称、地址、联系人、电话、邮箱 | `models.py:1356`–`:1360`；`purchase_lifecycle.place_purchase_order:93`、`:106`–`:120` 下单捕获 | 已核实 API 和采购详情；没有发现独立 PO 正式文件导出及完整买方（我方）快照消费者。供应商国家在主档 `models.py:1234` 有值，但不在五项快照中。 |
| PI 卖方：名称、销售联系人、地址、邮箱、电话 | Quote/SO/PO 无对应卖方版本快照；前端 `QuotePreviewModal.vue:11`–`:17` 为常量 | XLSX `templates/quotation/报价单模板_无折扣.xlsx` 的 I3/I4/I5/I6/I7 为固定文本；`render_quote_xlsx:293` 每次加载当前模板。PDF 按 `QuotePreviewModal.vue:42` 的 window.print，卖方来自当前前端常量，不是后端保存版本。 |
| 税务/注册、独立账单地址、收货地址及各自收件人 | 三类单据主体模型无完整结构；shipping_details 自由文本不等于独立结构化主体地址快照 | DTO `quotation_export_dto.py:130` 的 tax_id 永远空；模板 B6 映射税号却无保存源；前端 `QuotePreviewModal.vue:63` 税号显示空。既有一个 buyer_address 不能同时证明多个地址的历史真实性。 |
| 行级商品/供应来源 | QuoteItem `models.py:987`、`quote_snapshots.create_quote_items:19`；OrderItem `models.py:1112`、`:1159`；PO Item `models.py:1421`、`:1461` | PI DTO 商品来自 QuoteItem 保存值，图片来自 image_snapshot；供应来源名称/型号/条码不等于完整法律主体快照。不能用行级 supplier_name_snapshot 替代 PO 双方资料及主体修订。 |

代码位置均相对于本工作树根目录，行号在精确基线核实，非引用旧报告行号。

## 已复现缺陷（按严重性）

### D1 — P1：历史空买方的新修订被当前主档补成“保存主体”

- 位置：`backend/crm/models.py:911`–`:914`，`Quote.save()` 在 buyer_company_name 为空时无条件读取 `self.customer.name`；`backend/crm/views.py:1812`–`:1831` 的 `QuoteViewSet.revise()` 复制空值后通过 `Quote.objects.create()` 触发该逻辑。
- 真实复现：只在新内存测试库构造旧报价，数据库更新 buyer_company_name 为 `""`，客户改为 `CURRENT MASTER NOT HISTORICAL`，POST `/api/quotes/<id>/revise/` 仅给 revision_summary。HTTP 201；旧版仍为空，新版名称变为当前主档；新版导出 DTO 也采用该值。`snapshot_probe.py` 的 `test_legacy_unknown_buyer_is_replaced_on_revision` 通过。
- 影响：新版本丢失“历史未知”的语义，在未明确确认主体的情况下将当前主档包装为版本主体。旧版本身未被此 API 改写，不夸大为所有历史报价直接漂移。
- 为什么原测试没挡住：`test_quotes.py:348` 只验证 recipient/email/phone/address 空值；`test_formal_party_snapshots.py:160` 验证 SO/PO 的新增空字段，不覆盖空 buyer_company_name 修订。
- 最小建议（未实施）：把“首次新报价预填”与“继承旧版本”分开；继承空值时禁用模型兜底，保留未知并在必要正式导出前提示补证/确认，不从主档静默猜测。补验普通 revise 和 `OrderSerializer._create_quote_revision_if_needed`（`:2254`）的同源路径。后者共享 Quote.create 风险，但本轮没有另行 HTTP 复现，不能计为第二个独立已复现缺陷。

### D2 — P1：同一保存报价重导出的卖方未被冻结

- 位置：`backend/crm/quotation_export_dto.py:41` 的 DTO 仅有 buyer，没有 seller 版本；`backend/crm/quote_xlsx_renderer.py:293`–`:304` 每次从 `quotation_templates` 取当前模板并 `load_workbook`；`backend/crm/quotation_template_config.py:39` 起配置没有历史模板版本绑定；前端 `QuotePreviewModal.vue:11` 和 `:67` 的卖方使用常量。
- 真实复现：同一已发送 Quote 先调用真实 `build_pi_export_payload`，用 openpyxl 读取 XLSX I3。仅在隔离 MEDIA_ROOT 创建模板副本，把该副本 I3 改为 `CHANGED TEMPLATE SELLER`，临时 patch 配置指向副本后再调用原导出服务。原报价/业务模板未修改，两次文件 I3 分别为原卖方名称及新名称。`test_same_saved_quote_reexport_uses_current_template_seller` 通过。
- 影响：共享模板或前端卖方资料更新后，旧报价重新生成的正式文件可能换成新卖方；预览/PDF 与 XLSX 还有两个独立资料来源。不是“PI 买方仍回落客户主档”，正常 buyer DTO 未发现此兜底。
- 最小建议（未实施）：现有版本上增量绑定 seller 快照及模板版本/不可变资源，让 PI API、XLSX、PDF 共用同一已保存主体；历史缺失明确未知或待补证。若要求精确重现签发文件，还需绑定签发文件及内容摘要，不能只保存当前模板 ID。
- 限制：复现为真实服务生成的 XLSX 内存字节及单元格核验，不是 Chrome 下载、PDF 实际打印或模板发布演练；没有永久修改共享模板。

## 历史来源风险（与当前 0080 缺陷区分）

### H1 — P1 历史可信度风险：旧 0012 以迁移时主档生成历史快照

- 位置：`backend/crm/migrations/0012_quote_saved_pi_snapshots.py:8`–`:14`，`populate_saved_pi_snapshots` 明确写入 `quote.customer.name`；`:17` 起商品/图片也从当时 SKU 主档生成。无“迁移回填/历史待核实”的字段来源标记。
- 真实 MigrationExecutor 复现：退到 0011，用历史模型保存 `ORIGINAL NAME` 客户的已发送报价；在迁移前把主档改为 `CURRENT AT MIGRATION`；执行 0012 后 buyer_company_name 是后者，日志含 `GAP_MIGRATION_0012_PROVENANCE`。最后恢复当前 migration leaves，全部仅在内存测试库。
- 定性：这是**既有历史迁移策略的来源风险**，不是本轮 0080 新迁移错误，也不能证明真实业务库任何具体单据已被污染；本轮未连接业务库，无数量、时间分布或既存记录可判定。
- 最小建议（未实施）：不改写已发布 0012；未来通过新增来源/可信度记录或受控核实流程区分“交易时保存”与“迁移时主档推定”，依据外部原件核实，不能批量拿当前主档再填一次。实际受影响集合需独立授权后只读调查。
- 对照：0080 仅增字段、无 RunPython 主档回填；本轮真实 0079→0080→0079→0080 验证原订单/采购全部旧列一致，新客户六项/供应商五项字段为空，未发现该循环破坏旧数据。

## 缺失要求（按严重性；不是重复开发既有快照）

### M1 — P1：完整双方资料与所有正式文件覆盖不足

上表已列实际字段/输出消费链。`models.py:867`、`:1042`、`:1342` 各单据没有完整双方及多地址/税务注册快照；`quotation_export_dto.py:130` 直接输出空税号；完整 SO/PO 文件链未实现。此为七项当前规则扩大后的范围缺口，不推翻旧 P1 对六/五项有限范围的测试 PASS。

最小建议：在已有主体快照结构上补充缺失字段和双方/地址角色，不重复建立六/五项字段；先确认正式 SO、PO 以及 PI 所需双方映射和空值政策，再绑定所有文件消费者。不能把 website、备注或 shipping_details 推断为注册/账单/收货资料。

### M2 — P1：主体修订版本与法律主体变更没有完整表达

- `QuoteSerializer.Meta.read_only_fields`（`serializers.py:1952`）包含 buyer_company_name；`QuoteViewSet.revise:1804` 拒绝换 customer，`:1812` 起仅继承旧公司名称。probe 提交 `buyer_company_name="NEW LEGAL BUYER"` 得到 201，但返回仍为 `OLD BUYER`。这是**当前 API 行为复现支持的能力缺失**，不是越权篡改或已发生错误主体替换。
- 收件人四字段可以新修订，旧值保留（现有测试 `test_quotes.py:295`、`:383`）。因此不能写“现有修订链没有冻结任何主体字段”。
- `validate_contract_edit`（`serializers.py:517`–`:554`）阻止正式 SO/PO 直接换客户/供应商等敏感字段；快照只读分别在 `:2084` 和 `:667` 起。保护正确，但没有正式 SO/PO 主体修订流程；`OrderQuantityAdjustment`、`quantity_change_version` 与金额 ContractChangeRequest 不是主体完整新版本。
- 普通主档修改 `CustomerSerializer:971`、`SupplierSerializer:135` 未区分文字更正、资料变更和法律主体替换；UI 的“当前主档参考”是展示区分，不代表法律关系变更流程已存在。

最小建议：保留禁止原地修改正式快照；增量建立主体变更申请/版本关系、原因、有效时点和旧版保留，区分同主体资料更正与换主体。不得简单解除 buyer_company_name 只读或 customer 变更限制来“修复”。

### M3 — P1：主体变更发起/审批分离尚无流程

`ContractChangeRequest`（`models.py:1556`–`:1571`）只有关联、金额、日期、状态和说明；`ContractChangeRequestViewSet.approve`（`views.py:2969`–`:2978`）检查模块权限后调用 `services/finance.approve_contract_change:438`，后者只验证状态/金额/计划，不接收审批人也不比较发起人与审批人；`finance_scope.ContractFinancePermission:91` 为模块操作权限，并非两人分离。Quote revise 直接创建草稿版本也没有主体审批状态。

定性：本轮只读源码核实的要求缺失；没有执行真实账号自批漏洞演练，不能宣称已复现生产自批。既有金额流程不等于主体变更流程，不应擅自改其规则；开发统一超级管理员仍按用户约定保留。

最小建议：在主体变更流程显式保存发起/审批真实身份并按规则核验分离；开发默认姓名继续标记开发身份，不能伪造真实审批人。具体正式身份落地依赖 ISS-003/018/052 的相关边界，由主审协调，不在本轮配置 RBAC。

### P2 待核实边界/风险

- Quote 没有国家快照，来源报价 SO 的国家取确认时客户主档（`order_lifecycle.py:51`–`:59`）。这是当前明确实现，尚未复现错误国家文件；若要求整个主体严格来自报价签发版本，需要补充来源规则和测试。
- PO 行供应商名称在创建行时捕获（`models.py:1461`–`:1480`），PO 头在下单时捕获。草稿期间改名是否形成同一单据不同名称，需要专门场景；本轮没有动态复现，不登记为已确认缺陷。
- 快照 API 只读与生命周期原子性不等于数据库层不可变。直接 ORM/SQL 改写、管理后台路径及已签文件防篡改未做全覆盖验证；不将其泛化为已发现漏洞。

## 测试环境、命令及真实结果

Python **3.14.5**，实际解释器 `C:\Python314\python.exe`，Django **6.0.6**，SQLite **3.50.4**，Windows PowerShell；不是 Python 3.12，也未把迁移文件生成注释中的 Django 5.2 当成当前运行版本。未新装依赖。`audit_runner.py` 每次子进程设置 `DATABASE_URL=sqlite:///:memory:`、`APP_STAGE=development`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONIOENCODING=utf-8`，以本工作树 backend 为 cwd；每次新建独立 TEMP MEDIA_ROOT。Django 测试显示实际测试库为 `file:memorydb_default?mode=memory&cache=shared`，为 Django 从内存 SQLite 配置派生的测试库，不是磁盘业务库。

三次 TEMP MEDIA_ROOT 分别为 `C:\Users\Johnson\AppData\Local\Temp\iss037-audit-media-1b5d3kyb`、`iss037-audit-media-ax7i4g_5`、`iss037-audit-media-zhfix1ef`。测试媒体及模板副本仅在这些新目录；没有访问现有业务媒体。既有 `test_formal_party_snapshots.py:192` 的 override_settings 拒绝边界按原测试执行，未改正式权限配置。

真实启动命令（工作树根目录）：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python docs/uat-evidence/r1-iss037-snapshot-audit-20261103/audit_runner.py
python docs/uat-evidence/r1-iss037-snapshot-audit-20261103/audit_runner.py --probe-only
python docs/uat-evidence/r1-iss037-snapshot-audit-20261103/audit_runner.py --migration-only
python docs/uat-evidence/r1-iss037-snapshot-audit-20261103/audit_runner.py --verification-only
```

首个子进程实际 Django 命令：

```text
python manage.py test crm.tests.test_formal_party_snapshots crm.tests.test_contract_lifecycle crm.tests.test_quotes crm.tests.test_quote_revision_tree crm.tests.test_iss020_quote_export crm.tests.test_procurement crm.tests.test_purchase_order_related_orders crm.tests.test_cash_events.CashMigrationTests.test_additive_migration_preserves_historical_rows_and_decimal_fields --verbosity 2 --noinput
```

| 运行 | 测试数/skip/exit | 真实结果及日志 |
|---|---|---|
| 现有定向 Django 测试 | 116 / 0 / 0 | 51.605s，OK；`raw-evidence.zip/1-stdout-stderr.log`，具体每项名称保留。含新库全迁移、主体五项测试、修订、导出、生命周期、采购、关联订单、现金历史迁移；不是全量后端。 |
| 首次 `python manage.py test snapshot_probe --verbosity 2 --noinput` | 3 / 0 / 1 | 2 成功、1 ERROR；首次卖方扫描只覆盖第 1–2 行而卖方在 I3，StopIteration。扩大扫描至第 7 行后独立重跑；原始失败没有删除/改写。`raw-evidence.zip/2-stdout-stderr.log`。 |
| `python manage.py makemigrations crm --check --dry-run` | 不适用 / 不适用 / 0 | No changes detected；`raw-evidence.zip/3-stdout-stderr.log`。 |
| 行为 probe 重跑 | 3 / 0 / 0 | 0.728s，OK；`probe-rerun-raw.zip/1-stdout-stderr.log`；输出 `GAP_PARTY_REVISION_READONLY`、`GAP_LEGACY_REVISION`、`GAP_SELLER_TEMPLATE_DRIFT`。 |
| `python manage.py test migration_probe --verbosity 2 --noinput` | 2 / 0 / 0 | 43.240s，OK；`migration-raw.zip/1-stdout-stderr.log`。真正执行历史模型/迁移，最后恢复当前 leaves；0080 循环两次对账通过，0012 来源风险复现。 |

每个 ZIP 同时含实际 `environment.json` 和每条命令的 `*-command.json`（argv、exit）。日志原始 stdout/stderr 字节直接压缩，没有去尾空格、替换行尾或删减错误。runner 自身会继续采集后续命令，**不能用 runner 最外层 exit 代替各子进程 exit**；结果取上述 JSON 与 unittest 汇总。成功复跑不覆盖首次失败。

116 项原有测试的关键覆盖：`test_formal_party_snapshots.py:63/109/123/160/193`；`test_contract_lifecycle.py:95/115/143/164/247`；`test_quotes.py:287/295/348/383/498/531/558/1319/1334`；`test_iss020_quote_export.py:137/153/164/223`。负向请求的 Bad Request、Forbidden 及故意故障日志保留，以最终测试汇总判定。

结束时 `git diff --exit-code`、`git diff --cached --exit-code`、`git diff --check` 均 exit 0；`git status --short --untracked-files=all` 仅列本证据目录的新增文件。另对四个新增文本逐一执行 `git diff --no-index --check -- NUL <file>`，仅有 Windows LF→CRLF 提示，无 whitespace error；no-index 的 exit 1 表示与空文件存在差异，不能伪称该命令 exit 0。最终 SHA、状态、版本及各检查的原始输出保存在 `final-verification-raw.zip`。

## 依赖 ISS、冲突及移交

- **ISS-037**：当前报告限定于上述精确 SHA；不新增全局 ID、不写台账、不关闭问题。共享台账 `PROJECT_ISSUES.md:96` 仍有早期 BLOCKED 表格，而 `PROJECT_PHASES.md:335` 起及集成 README 已记录六/五项完成并待复审，存在记录口径不一致。主审应整合有限已完成范围和本轮剩余要求，不按旧 BLOCKED 描述重复开发。
- **ISS-020 / ISS-029**：指定保存版本的买方/商品/金额及收件人空值机制保留；本轮 D1 针对买方公司空值的新修订，不重新登记早已修复的显式空邮箱。D2 属于卖方/模板版本边界，不能扩大旧导出一致性 PASS。
- **ISS-021**：SO 数量调整已有版本和历史，不能当主体修订方案；保持已实现数量/资金/库存规则，不提议重写。
- **ISS-003 / ISS-018 / ISS-052**：真实身份、权限全站验收、审计及审批责任关联边界；本轮不启用 RBAC、不逐人建账号、不把开发姓名当真实发起/审批人。
- 迁移建议只能新增兼容迁移或来源标记，不能改已发布 0012/0080；不复制旧未发布同号 0078，也不重做现有十一项快照字段。
- 原始 UAT 来源与日期/行号如历史记录不全，保持 UNKNOWN；本轮确认的源码和测试日期为本报告日期，不能借此推定历史污染发生日期。

## 未覆盖与剩余动作

未执行：真实 Chrome 视觉/下载、浏览器 PDF、Excel 桌面/打印、PostgreSQL 迁移/并发锁、CI、真实员工权限和两人审批、业务库历史抽样、全部导出/报表/附件入口及真实签发文件存档核验。无 UI 改动，本轮不以源码阅读冒充 Chrome 视觉验收。

下一步由主审复核 D1/D2 和 H1 证据，协调完整双方字段/正式文件需求及主体修订审批的最小增量范围；对历史数据先调查来源再决定补证，不静默重填。上述建议均未实施，业务代码及现有测试保持精确基线状态。
