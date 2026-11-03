# R1-ISS039-SHARED-COST-AUDIT 只读审查

审查日期：2026-11-03（Asia/Shanghai）。精确审查 SHA：`8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`。

工作树：`D:\Codex项目\森爵照明管理系统\.worktrees\r1-iss039-shared-cost-audit-20261103`。分支：`codex/r1-iss039-shared-cost-audit-20261103`。开始时 HEAD 与指定 SHA 相同，`git status --short` 为空。业务代码、既有测试、迁移、正式配置及共享台账均未修改。未连接业务数据库、创建 PR 或触发 CI。所有新增文件均位于本目录；审查取证完成后，由主代理复核并以 `[skip ci]` 提交推送本独立分支。本报告不关闭 Issue。

## 结论与适用范围

当前成本分配接口已实现采购修改员跨销售人员调整成本归属，不再要求逐个 SO 授权。旧 `BLOCKED` 描述不代表当前源码仍有旧权限缺陷。源码、现有权限测试和本轮 APIClient 执行结果相符。

确认一项 P2 规则偏差：公共费用仍可选择按数量分摊，未严格限定为本次用户确认的“按私有采购金额比例”。本轮用不同采购单价、相同数量的两份归属实际复现，见 C-01。未发现本次已测路径中的新增付款、库存流水或销售单据，也未发现候选接口返回客户、销售价或利润。

现有 Django 测试 77 项：76 通过、1 跳过；新增隔离 probe 5 项全通过；前端源码回归 13 项全通过。probe 中的通过表示成功捕获并断言现状，其中“按数量”反例通过不表示规则符合。

这是源码与隔离测试审查，未执行当前基线的 Chrome 视觉/交互验收、正式员工真实登录、PostgreSQL 并发及生产数据库审计触发器验收。没有用历史 Chrome 截图代替当前执行。

## 已读协议、历史及当前规则优先级

- 已读本工作树 `AGENTS.md`、`docs/REVIEW_PROTOCOL.md`，并检索阅读 `docs/PROJECT_ISSUES.md` 的 ISS-039、ISS-024、ISS-043 相关条目，`docs/PROJECT_PHASES.md` 的旧采购权限及 ISS-039-INT 阶段条目。
- 已读 `docs/uat-evidence/iss-039-integration/README.md` 和 `api-evidence.json`；旧基线是 `54925e0a10a48c16ba3b66bbab9e433f48a0e2d7`，不得当作本次审查 SHA。历史浏览器明确采用 mock API，不是正式账号集成证据。
- 已读 `docs/r0-d4b2b-procurement-scope.md`；其“旧、新全部销售归属须满足 orders.view/update + 客户范围”属于旧规则，已被本次用户规则和后续集成实现取代。
- 核对本地代码历史：`ef33bba` 为共享采购成本分配权限集成；早期 `7e5e565` 是旧采购数据范围保护；本轮没有访问远端或触发工作流，远端最新状态不在本次结论内。
- 用户明确禁止本轮修改共享台账，优先于仓库协议中的每轮更新台账要求；文档冲突仅在此报告交接，不改写共享文件。

## 八条规则逐项结论

下表行号均核自本次精确 SHA；路径相对本工作树根目录。

| 规则 | 判定 | 当前证据与边界 |
| --- | --- | --- |
| 1. 共享采购按私有采购金额比例分摊公共成本 | 部分实现 | `backend/crm/services/purchase_costs.py:88` `cost_summary()` 先按采购行金额及归属数量算 `base_amount`，`:103` 对 `method=amount` 按该金额分配费用，`:72` `split_amount()` 处理分币尾差；但 `:63` 允许 `quantity`，前端 `frontend/src/components/PurchaseCostAllocationModal.vue:103` 同样公开数量选项。C-01 已实际复现偏离金额比例。这里的金额是采购商品成本，不是销售价。 |
| 2. 有 purchases.update 的员工可调整跨销售人员成本归属 | 已实现 | `backend/crm/procurement_scope.py:26` `validate_cost_writes()` 只检查采购修改权限和目标存在；`backend/crm/views.py:417` `cost_allocation()` 保存调用此函数。现有 `test_iss039_shared_purchase_costs.py:104` 证明没有 orders.view/update 仍可跨客户归属，普通销售 API 403。本轮执行通过。 |
| 3. 不需逐个 SO 授权 | 已实现 | 专用预览 `views.py:406`、保存 `:417` 和候选 `:445` 不调用 `require_order_writes()`；`procurement_scope.py:14` 的旧式函数仍供普通采购编辑使用，非专用分配路径残留。`test_procurement_data_scope.py:26`、`:38`、`:113` 实际断言跨范围和没有销售权限的成本保存成功。部分测试名称沿用旧语义，须看断言而非名称。 |
| 4. 无采购修改权限不得改 | 已实现 | `procurement_scope.py:20` 候选要求 update，`:26` 执行分配要求 update；`backend/crm/permissions.py:157` `action_for_request()` 对动作 POST 归 update，`:204` `ModuleActionPermission` 执行模块权限。现有 `test_iss039_shared_purchase_costs.py:133`、`:146` 和 probe 的只读 POST 预览/保存均 403，分配及版本不变。开发超级管理员按既有规则例外，不改变正式配置。 |
| 5. 不泄露无权客户信息、销售价、利润 | 已实现（本轮范围） | `views.py:445` 候选仅白名单 `id/order_no/status/status_display`；`purchase_costs.py:88` 摘要仅采购成本及归属，不读取客户或销售单价。`procurement_scope.py:43` `scoped_cost_summary()` 对只读受限销售链接隐藏订单 ID/编号；采购修改员可识别归属所需订单，但不获得客户、销售价格和利润。`serializers.py:249` 起采购日志脱敏；现有测试 `test_iss039_shared_purchase_costs.py:104`、`:146`、`:219` 通过。该结论不扩大为全站自由文本、附件、全部报表安全验收。 |
| 6. 操作人、时间、前后值审计 | 部分实现（开发身份例外） | 已认证且启用审计时完整实现：`views.py:427` 起在行锁事务内取 before、保存、写 after；`backend/crm/audit.py:41` `record_operation()` 写 operator/前后值/变更字段；`backend/crm/models.py:84` `created_at` 自动时间。现有 `test_iss039_shared_purchase_costs.py:219` 及本轮 probe 验证真实操作人、时间、版本前后值和审计失败整体回滚。但当前开发环境 `config/settings.py:75` 默认关闭审计，`audit.py:11` 还要求真实已认证操作人；匿名开发操作不留正式操作人审计。此为已确认开发约定的边界，不应伪造 Johnson 为真实登录人，也不建议本轮开启正式 RBAC。 |
| 7. 金额、公共费用总额守恒 | 已实现（有效输入和已测边界） | `purchase_costs.py:72` 最大余数按稳定行顺序分配分币尾差；`:116` `prepare_costs()` 拒绝跨 PO 明细、超分、取消目标、旧版本，余量自动归库存；`:150` 保存事务包含计算失败回滚。现有 `test_purchase_costs.py:45`、`:56`、`:97`、`:113` 通过；零采购额按金额分摊非零费用会拒绝，不能将其解释为成功分配。数量法同样守恒，但不满足规则1。 |
| 8. 不生成额外付款、库存、销售单据 | 已实现（单据层面） | `purchase_costs.py:150` 只替换成本归属、更新 PO 费用/版本并重算预留；`test_iss039_shared_purchase_costs.py:196` 验证库存流水/交易/付款计划计数不变；本轮 probe 比较除明确允许变化模型外 63 张 CRM 模型表的完整 values，付款、库存流水、销售及收发货等数据均不变。`:164` 调用 `fulfillment.py:419` `rebalance_sku_reservations()`，会删除重建派生库存预留，不应宣称完全没有任何库存相关写入；这不是生成额外库存单据。已收货且有竞争需求时的预留结果尚未专项复核。 |

“已实现”限定在该规则列出的代码与本轮已测路径，不代表产品封版；本次没有判为完全未实现的规则。

## 接口及权限边界：避免误判旧逐单保护

| 用途/入口 | 权限与数据边界 | 本轮核实 |
| --- | --- | --- |
| GET `/api/purchase-orders/cost-allocation-orders/` | 采购查看及修改；可跨销售人员；最小订单字段 | `views.py:445`、`procurement_scope.py:20`；采购员 200，只读 403 |
| GET `/{po}/cost-allocation/` | 采购查看；编辑能力由服务端 can_edit 判断 | `views.py:417`、`procurement_scope.py:43`；只读保留采购金额且隐藏无权订单身份 |
| POST `/{po}/cost-allocation-preview/` | 采购修改；无销售逐单授权；无持久化 | `views.py:406`；现有 preview 测试与 probe 验证正常/拒绝 |
| POST `/{po}/cost-allocation/` | 采购修改；目标存在/生命周期、数量、版本、事务保护 | `views.py:417`、`purchase_costs.py:116`、`:150`；跨销售成功/取消拒绝/旧版本拒绝/故障回滚 |
| 普通 PUT/PATCH `/api/purchase-orders/{po}/` | 原始来源关联、合同字段修改的独立保护 | `serializers.py:712`、`:719` `require_order_writes()` 保护重绑或草稿合同成本字段，不是专用成本归属接口；`:519` `validate_contract_edit()` 和 `:811` 起 update 保留合同保护 |
| 普通 PUT/PATCH 内直接提交 additional_costs/cost_allocation_version | 模型字段 editable=False，DRF 自动只读 | `models.py:1344`、`:1345`；最终 probe 实测 PATCH 200 但两个伪造字段均被忽略，费用和版本不变；不能只因 serializers Meta 使用 fields=__all__ 就误报为成本写入绕过 |
| SO 行供应来源 `/api/orders/{order}/items/{item}/supplier-allocation/` | 修改销售订单行的采购来源，仍要求 SO 范围与相应模块权限 | `backend/crm/sku_management.py:229`、`:232`、`:279`；`services/supplier_allocation.py:74` 修改来源快照；客户优先来源另需 suppliers.update。它不是 PO 成本归属分配，不能把其逐单保护当成本规则2/3缺陷 |

`supplier_allocation.py:128` 输出采购来源价格，`sku_management.py:243` 的包装对无 purchases.view 用户隐藏采购价格等字段。源码与 `test_procurement_data_scope.py:76`、现有 supplier_allocation 套件一致。没有为满足本任务规则而取消此销售行来源管理的保护。

## 前后端字段与日志一致性

- 前端 `PurchaseOrderPage.vue:111` `openCostAllocation()` 先判断采购修改权限，`:115` 只加载专用最小候选；`:487` 将 costOrders 传入弹窗。不会把普通订单列表的客户名作为成本归属选项展示。
- 弹窗 `PurchaseCostAllocationModal.vue:19` `payload()` 仅传 version、采购行、目标类型、订单 ID、数量、其他归属名称及 expenses；`:41` 预览、`:63` 保存分别走专用接口。`:90` 对只读且 sales_link_restricted 展示受限说明，编辑者可选订单；`:103` 的数量法与后端字段契约一致，但二者共同偏离当前金额比例规则。
- `procurement_scope.py:43` 编辑者能获得必要订单 ID/编号；只读无权者清空这两个字段。保存日志取脱敏之前的完整 before/after，`views.py:431`、`:432` 转 JSON 后再写入；响应最后才脱敏，避免破坏存储审计快照。
- `serializers.py:249` 起对采购 OperationLog 采用更严格条件：Data Scope 非 all，或 orders/finance/transactions/suppliers/skus 任一查看权限不足时，将 before_data、after_data、metadata、changed_fields 清空。采购员可执行分配而不能读取原始敏感审计，是有意区分操作授权与日志可见性，不是不一致漏洞。操作历史仍保留；`serializers.py:380` 起另按 employees.view 处理操作人显示。
- 手工名称/费用名是用户输入，不能把此静态字段白名单结论扩大为“任意自由文本绝不含个人信息”。本轮未做自由文本内容分类或历史业务数据扫描。

## 按严重性分列缺陷与缺失要求

### P0/P1

本轮未确认 P0/P1 缺陷。未证明 PostgreSQL、并发、真实登录等范围全部通过，见未覆盖边界。

### P2：C-01 公共费用允许按数量分摊，偏离金额比例规则

性质：已复现的业务规则偏差，归属 ISS-039，本报告内部定位 C-01，不擅自分配新的共享 Issue ID。

定位：`backend/crm/services/purchase_costs.py:63` `ExpenseInput.method` 允许 quantity，`:103` `cost_summary()` 以数量作为费用权重；`frontend/src/components/PurchaseCostAllocationModal.vue:103` 公开“按数量比例”。

最小复现：同一共享采购创建两行，数量均 10，单价分别 1000 和 100，全部归属订单 A/B，公共费用 1000。有 purchases.update、无销售查看/修改的测试员工通过真实 Django APIClient 保存 `method=quantity`，返回 200，A/B 各分 500.00；相同归属下一版本改 `method=amount`，返回 200，A/B 分 909.09/90.91。金额总额都守恒，但数量法使公共成本归属与私有采购金额比例不同。见 `probe.py` 的 `test_quantity_is_accepted_but_not_amount_proportional` 和 `probe.raw.zip` 中 `QUANTITY_RULE_COUNTEREXAMPLE`。

影响：有权采购员可以在正常 UI 中改变公共成本分担口径，影响跨销售人员订单预估成本/利润口径。不是销售价格泄露，也不是额外银行付款。

最小修复建议（未实施）：新增或调整共享采购费用时，服务端限定公共费用使用 amount，前端移除该场景 quantity 选项；保留既有数量法历史记录的可解释读取，不自动改写历史账面或产生补单。补一条异价等数量回归及 API 非法 method 拒绝测试。现有 `test_purchase_costs.py:56` 的零成本 quantity 成功断言与本次严格规则冲突，需主审明确历史兼容/零成本处理后调整，不能只修改 UI、也不能直接重算全部历史费用。

### P3：C-02 台账和阶段摘要对旧跨单限制的描述冲突

性质：文档事实冲突，不是当前仍存在的逐单授权缺陷。

定位：`docs/PROJECT_ISSUES.md:98` 仍将 ISS-039 写为 BLOCKED，并称无订单级委托授权；`docs/PROJECT_PHASES.md:345`、`:349` 已记录只需采购修改及 FIXED_PENDING_REVIEW；`docs/uat-evidence/r1-status-reconcile-20261028/README.md:88`、`:182` 又保留旧“委托未支持”。当前 `procurement_scope.py:26` 及 77 项本轮相关回归支持已移除旧限制。

风险及建议：避免下一轮按旧 BLOCKED 重复开发或错误引入逐单 SO 授权。建议主代理统一台账叙述与规则、本轮证据，在独立复核前不要直接 CLOSED。本轮按用户指令没有改共享台账、阶段或状态统计。

### 邻接风险/未完成要求（不混记为共享成本已确认缺陷）

- 审计开发身份边界：规则6按当前默认开发身份只能判部分实现。`audit.py:11` 明确关闭审计/未认证时不写日志，既有 `test_audit.py:21` 也断言开发模式不记正式日志。若未来要求开发匿名操作也留痕，应另定义可区别真实账号的开发审计身份；本轮不实施，不伪造正式操作人。
- 供应来源操作的前值：`sku_management.py:320` 起“为销售订单行分配供应商”记录调用未提供 before，`audit.py:41` 默认 before_data={}；可留 after 快照和 metadata，但不能证明该相邻动作也具备完整前后对照。本次规则6的核心 PO 成本分配已经提供 before/after；若全链路规则拟覆盖 SO 供应来源，建议单列需求并在改源前抓取原快照，新增专项审计测试。本轮仅源码确认该边界，未将其当作 PO 成本分配审计失败。
- 预留派生写入：`purchase_costs.py:164` 重算每个受影响 SKU 预留，`fulfillment.py:419` 删除重建 InventoryReservation；不生成出入库单，但不是“库存相关所有表完全不写”。与 ISS-006 并发/锁序回归关联，需 PG 实测，不能用空预留 fixture 的回滚证明所有竞争场景。

## 实际执行环境、命令与结果

真实环境：Windows PowerShell，`C:\Python314\python.exe`，Python **3.14.5**，Django **6.0.6**；不是 Python 3.12，未新装依赖。前端 Node **v24.16.0**。

所有 Django 执行显式设置 `DATABASE_URL=sqlite:///:memory:`、`APP_STAGE=development`，实际测试库为 Django 新建的 `file:memorydb_default?mode=memory&cache=shared`。新建独立 TEMP MEDIA_ROOT，未使用业务库/业务媒体目录。既有权限测试的 `@override_settings` 将测试作用域切到 production/RBAC/已认证测试员工，退出测试恢复设置；本轮没有修改任何正式 RBAC 配置、开发权限或创建真实业务账号。probe 复用既有测试 fixture 的同类 override，未启服务连接业务库。

| 执行项 | 命令 | 结果与证据 |
| --- | --- | --- |
| 既有 Django 定向回归 | 工作树根目录：`powershell -NoProfile -ExecutionPolicy Bypass -File docs/uat-evidence/r1-iss039-shared-cost-audit-20261103/run_existing.ps1` | 77 项，76 通过，1 skip，0 failure/error；测试耗时 64.563 秒；Django/脚本 exit 0；`existing-tests.raw.zip` |
| 隔离额外 probe | 工作树根目录：`python -B docs/uat-evidence/r1-iss039-shared-cost-audit-20261103/probe.py` | 最终 5 项，5 通过，0 skip/failure/error；测试耗时 0.800 秒；exit 0；`probe.raw.zip` |
| 既有前端采购页源码回归 | 工作树根目录：`python -B docs/uat-evidence/r1-iss039-shared-cost-audit-20261103/frontend_probe.py`，内部 frontend cwd 执行 `node --test src/views/PurchaseOrderPage.test.js` | 13 项，13 通过，0 skip/failure；exit 0；`frontend.raw.zip`。这是 Node 源码断言，不是浏览器渲染测试 |
| 工作区检查 | 工作树根目录：`git diff --check`、`git diff --name-only`、`git status --short` | 已有 tracked 文件无差异；仅新增本目录；没有提交 |

既有 Django 命令在 backend cwd 实际执行：

```powershell
python manage.py test crm.tests.test_iss039_shared_purchase_costs crm.tests.test_purchase_costs crm.tests.test_procurement_data_scope crm.tests.test_supplier_allocation crm.tests.test_integration_039_037_040 crm.tests.test_audit crm.tests.test_functional_rbac --verbosity 2 --noinput
```

现有套件计数：共享成本权限6、采购成本9、采购数据范围10、供应来源6、039/037/040集成1、审计8、功能权限37，共77。唯一 skip 是 `crm.tests.test_audit.AuditTrailTests.test_postgres_trigger_rejects_raw_update_and_delete`，原因原文为 `requires a PostgreSQL database; SQLite cannot prove the production DB guard`。本轮 **PostgreSQL 未跑**，无 PG 通过结论。

最终媒体路径：既有回归 `C:\Users\Johnson\AppData\Local\Temp\iss039-audit-1d58c91d-10a4-4340-b827-ea267ee7812a`；最终 probe `C:\Users\Johnson\AppData\Local\Temp\iss039-probe-dbsr8k8z`。二者仅测试隔离目录；未清理或修改既有媒体文件。

执行过程说明：首次 runner 使用 PowerShell `$ErrorActionPreference='Stop'`，Django 将正常建测试库提示写 stderr 导致外层提前 exit 1，未得到完整测试结果；调整的只是本目录取证 runner 的 stderr 处理，随后得到上述 77 项正式结果。原始最终日志保留 PowerShell 对 stderr 的 NativeCommandError 包装文字，最终 `OK (skipped=1)` 与 `EXIT=0` 可核实。最初前端取证包装打印 Unicode 到 GBK 终端曾 exit 1，Node 已执行成功；改本目录包装按原始字节输出后重新运行获得最终 exit 0。没有改业务代码去让测试通过。probe 增加普通 PATCH 边界前先执行4项通过，最终重新执行5项的日志作为交付证据。

原始最终日志保存在 ZIP，未裁剪或清洗原文空白；`existing-tests.raw.zip` 内为 PowerShell 实际捕获文本，`probe.raw.zip` 为 Django stdout/stderr 捕获，`frontend.raw.zip` 保留 Node 输出字节。运行器和 probe 都保存在本目录便于复核。

## probe 具体证据

1. 异价等数量反例：数量法 `[500.00, 500.00]`，金额法 `[909.09, 90.91]`，两次保存均200，确认 C-01。
2. 保存前后比较63张其他 CRM 模型表完整记录，未变；明确排除预期变化的 PurchaseOrder、PurchaseCostAllocation、OperationLog、InventoryReservation，不把排除项描述为未写。审计 operator=真实测试采购员工，created_at 存在，changed_fields=`[cost_allocation]`，after版本1。
3. 对 `crm.views.record_operation` 故障注入抛 RuntimeError，验证分配、版本、费用、预留及日志整体回滚。
4. 有权预览200无写入；只读预览/保存403无写入。
5. 普通 PATCH 提交伪造 additional_costs 和 version，响应200但字段被只读机制忽略，原费用和版本保持；没有专用接口绕过。

## 依赖 ISS、冲突与建议主审后续

- ISS-039：已实现跨销售成本归属，建议复核 C-01 后再决定有限范围验收。旧 SO 逐单授权不应恢复；本轮不请求新的订单级委托模型。
- ISS-024/ISS-026：SO 供应来源与客户级偏好、启停过滤是相邻但独立功能；本轮仅执行供应来源既有相关回归，不替代逐 SKU 真实来源准备验收。
- ISS-037：039/037/040 集成回归验证历史主体快照、成本、发货导出/银行状态的既有流程；不能据此关闭历史主体全部事项。
- ISS-043：OperationLog 应用只读/ORM保护/操作人PROTECT本轮回归通过；真实 PG 触发器、生产运行账号、防篡改和备份恢复仍依赖部署验收。
- ISS-006：成本分配会触发预留重算，需结合 PG 库实际锁顺序和并发测试；本轮 SQLite 结果不能替代。
- 文档冲突见 C-02；主代理维护共享台账时应引用当前精确 SHA、当前规则、当前测试，并保留未覆盖边界。无需基于过时 BLOCKED 重复开发跨单权限。

## 未覆盖边界

- PostgreSQL 行锁、死锁/并发取消目标与保存、两个采购员同时保存的真实事务隔离；SQLite 只能验证串行版本拒绝，不能证明 PG 正确。
- 已收货且多个订单竞争同 SKU 库存时的预留具体变化；本轮确认调用及原子性，未完成实有预留竞争矩阵。
- 当前基线 Chrome 桌面/窄屏视觉、真实会话与多角色 HTTP 浏览器集成。前端本轮只做源码及 Node 断言；无 UI 修改，不将旧 Chrome/mock证据表述为本轮通过。
- 历史数量法费用的数据量、历史业务金额与真实客户资料；未连接业务库，未作历史账面重算。
- 候选接口全量订单性能、超大采购行/费用数组、极大金额溢出、复杂汇率/跨币种批量组合及所有自由文本内容；不把有限 fixture 覆盖扩大为全量边界。
- 全站 RBAC/附件/导出完整验收、真实生产账号、数据库维护权限和备份恢复，不在本任务完成范围。

后续最小动作是独立主审复核本报告 C-01 的规则偏差和 C-02 的台账冲突；本轮只提交取证材料，没有实施业务修复、触发 CI 或合并。
