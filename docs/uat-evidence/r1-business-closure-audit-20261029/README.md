# R1-BUSINESS-CLOSURE-AUDIT-01

日期：2026-10-29
固定审查基线：`54e715bdc568b80ba624186fecd866550676cf38`
审查分支：`codex/audit-business-closure-20261029`
审查工作树：本分支独立 worktree；未使用或修改主工作树的脏文件。
范围：ISS-006、ISS-022、ISS-036、ISS-040、ISS-075 及跨模块数量/状态/来源/导出一致性。

## 结论摘要

- ISS-006：发现确认的业务缺陷。相同收货请求和相同发货请求重放时，当前服务会各自新增第二条业务记录和第二条自动库存流水，违反 Phase 3 不变量 I16、I19 及 E38 的“重复提交不得产生重复业务副作用”要求。本轮只取证，未修改产品代码。
- ISS-006 冲销幂等：通过。已冲销收货或发货再次冲销会被拒绝，库存、状态、预留和冲销流水保持不变。
- ISS-022：当前实现与隔离真实 Chrome 场景通过；等于/低于 MOQ、交易单位换算、取消保留草稿、正式下单例外原因和状态结果一致。真实业务样本仍待业务复核。
- ISS-036：当前交易单位、基础数量换算、尾箱/混装和历史快照相关测试通过；缺失或语义冲突快照按歧义处理，不静默推断不可拆分规则。冲突快照的业务优先级仍待确认。
- ISS-040：当前实际 Shipment 导出、混装箱、分批发货、16 列模板、公式、Logo、打印区域、多页结构和长描述样本证据通过；原生 Excel Print Preview 仍为 `PRINT PREVIEW PENDING`，未用 PNG/artifact-tool 渲染冒充原生打印验收。
- ISS-075：当前实现与隔离真实 Chrome 场景通过；常规供应商 UI 不暴露固定付款规则，新 PO 不隐式生成付款阶段，历史显式付款计划保持。真实业务财务样本和生产环境仍待复核。
- 本轮未修改产品业务代码、数据库迁移、共享 `PROJECT_ISSUES.md` / `PROJECT_PHASES.md`，未连接生产、未启用正式 RBAC、未关闭 Issue、未合并 master、未触发 GitHub Actions。

由于 ISS-006 的重复收货/发货副作用是确认缺陷，本提交不建议直接作为下一批统一业务基线；应先完成幂等策略修复并独立复审。

## 规则和历史证据

- `docs/Phase3-业务流程与异常UAT计划.md`：R05–R08、F03–F08、E04、I13–I28、I46–I54，尤其 I16（重复收货不得双增）、E38（浏览器重复提交不得产生重复业务副作用）、E40/E41（重复冲销无第二副作用）。
- `docs/TaskF1-到货库存预留一致性.md`、`docs/TaskF2-超发安全冲销.md`、`docs/TaskC-订单采购草稿闭环.md`、`docs/TaskE-采购成本归属统一.md`：库存、采购来源、分批履约、冲销和成本归属口径。
- 2026-10-24 规则包：`ISS-022_供应商MOQ软提醒和共享PO合计判定.md`、`ISS-036_允许合理尾箱、不得破坏最小计量单位.md`、`ISS-075_取消供应商固定付款规则的常规前端使用.md`、`既有移交原件_2026-10-20/05_ISS-040_按实际发货导出正式Packing List.md`。
- 历史实现/证据：`docs/uat-evidence/iss-022-procurement-moq/`、`docs/uat-evidence/iss-075-payment-terms/`、`docs/uat-evidence/iss-040-integration/`、`docs/uat-evidence/integration-039-037-040/`、`docs/uat-evidence/iss036-fix03/`、`docs/uat-evidence/r1-a/`。

本轮没有实现或改变 ISS-105、ISS-108、ISS-121、ISS-037、ISS-038、ISS-039、ISS-062 的未决业务规则。

## 确认缺陷：ISS-006 重复收货/发货重放

证据脚本：[verify_replay_idempotency.py](scripts/verify_replay_idempotency.py)
原始结果：[replay-idempotency.json](logs/replay-idempotency.json)

隔离条件：一次性迁移 SQLite、独立 `MEDIA_ROOT`、`APP_STAGE=development`、`DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`；没有使用正式数据库或正式员工身份。

可重复步骤：

1. 在空 SQLite 中执行 `python manage.py migrate --noinput` 至 `crm.0089_operationlog_operator_protect`。
2. 创建 10 件已下单采购明细和 5 件已确认销售订单明细，使用同一 SKU。
3. 两次调用 `record_receipt`，payload 均为 `receipt_date=2026-10-29, quantity=4, unit_cost=5`。
4. 两次调用 `confirm_shipment`，payload 均为 `shipment_date=2026-10-29, items=[{order_item:..., quantity:2}]`，不显式指定随机生成的发货单号。

实际结果：

| 操作 | 第一次 | 重放后 | 预期 |
|---|---:|---:|---:|
| 收货记录 | 1 条，`purchase_in=1`，actual=4 | 2 条，`purchase_in=2`，actual=8 | 同一业务请求只产生 1 条记录/流水 |
| 发货记录 | 1 张 Shipment，`sale_out=1`，actual=6 | 2 张 Shipment，`sale_out=2`，actual=4 | 同一业务请求只产生 1 张发货/流水 |

相同请求没有请求幂等键，服务端也没有用业务请求身份阻止第二次写入。当前浏览器保存锁只能降低重复点击风险，不能覆盖网络重试、刷新重放或客户端超时后再次提交。影响范围包括库存 actual、采购/销售履约数量、订单状态、预留及后续 Packing List/成本核对；本轮未推断自动修复策略，也未修改任何业务实现。

同一脚本随后验证：首次收货/发货冲销成功后，第二次冲销分别被“已经冲销”拒绝，第二次冲销前后快照完全一致；因此“冲销重复操作”与“创建业务请求重放”是两个不同结果，不能用前者覆盖后者。

## 各 ISS 核验结果

### ISS-006

- 已通过：收货部分/完整、超到、收货冲销、下游出库后拒绝冲销、发货分批、库存不足原子失败、正常发货冲销、异常原流水整单拒绝、重复冲销不产生第二副作用。
- 确认缺陷：相同收货/发货创建请求重放会双写，见上节。
- 未完成：真实 PostgreSQL 多客户端并发、真实网络断线后重试、生产部署层；这些不是本 SQLite 结果可替代的验收。

### ISS-022

- 隔离真实 Chrome：1/1 通过，覆盖等于 MOQ、低于 MOQ、10 件箱换算为 9 pcs、草稿保存、取消后草稿保留、填写例外原因后正式下单、状态筛选、700px 窄屏。
- 后端测试覆盖同 SupplierSKU 合计、基础单位比较、无 MOQ 不造阈值、例外原因/操作员/时间/明细快照持久化；定向套件通过。
- `BUSINESS_VERIFICATION_PENDING`：尚未使用真实业务采购样本复核同一真实 PO 的跨销售订单合计口径；当前隔离证据不能替代业务数据确认。

### ISS-036

- 定向后端测试覆盖基础单位/交易单位换算、分数交易单位、不可拆分规格、250/100/50 尾箱、混装箱、不同规格、缺失/非法/冲突历史快照以及失败不写回。
- 当前基线对缺失或语义冲突快照不从当前主档推断不可拆分限制；这是已有明确安全口径，不在本轮改变。
- `BUSINESS_VERIFICATION_PENDING`：同系数但不同 `base_unit`、`unit` 或 `allow_fraction` 的历史快照冲突时，业务尚未给出优先级/人工处理规则。

### ISS-040

- 当前独立证据目录中的样本：[samples/iss040](samples/iss040/)；截图：[screenshots/iss040](screenshots/iss040/)。
- 结构验证包含普通纸箱、混装箱、同 SKU 不同箱规、同 SO 分批 Shipment、60 行多页及长英文/中英文混合描述；`xlsx-structure-validation.json` 的 16 列双语表头、公司信息、Logo、VML、公式、打印区域、重复表头、页脚和多页检查均为 `true`。
- 与当前集成基线一起保存的真实 Chrome 桌面/700px 窄屏页面显示实际 Shipment、实际装箱明细和导出入口；截图不是 Excel 打印预览。
- `DEPLOYMENT_VERIFICATION_PENDING` / `PRINT PREVIEW PENDING`：本轮没有可用的原生 Excel UI，未实际检查打印分页、混装箱行不跨页及 Page X of Y 的打印渲染；不能把结构解析或图片渲染写成原生打印通过。

### ISS-075

- 隔离真实 Chrome：1/1 通过，覆盖供应商列表不显示固定付款规则/筛选、新 PO 空付款阶段、空快照正式下单后无虚拟应付计划、历史 50%/50% 付款计划保留、700px 窄屏。
- 后端测试覆盖显式逐单付款阶段、空快照、金额/日期校验、历史计划和无计划采购单实际付款路径；定向套件通过。
- `BUSINESS_VERIFICATION_PENDING`：未连接真实财务业务数据库核对历史付款计划与实际付款/退款样本；`DEPLOYMENT_VERIFICATION_PENDING`：未进入生产 PostgreSQL/代理环境。

## 跨模块一致性

当前基线已有的 `crm.tests.test_integration_039_037_040` 通过，验证正式订单主体快照、采购来源快照、成本分配金额守恒、成本分配不新增银行交易/付款计划、实际 Shipment 及 Packing List 16 列/公式/Page 页脚。结合本轮 135 项核心定向测试和 63 项可靠性/跨模块测试，未发现 ISS-022、036、040、075 改写银行资金事实、历史采购来源或正式单据快照的现象。

但 ISS-006 的收货/发货重放缺陷会改变库存和履约事实，因此在修复前不能把一次通过的单次跨模块链路扩大解释为重复请求安全。

## 测试索引

### 后端

- [backend-focused.log](logs/backend-focused.log)：`135` 项通过；库存冲销、采购安全/MOQ、采购流程、付款、交易单位、实际装箱、Packing List、成本分配。
- [backend-reliability-cross-module.log](logs/backend-reliability-cross-module.log)：`63` 项通过；R1-A 可靠性、贸易/财务安全、统一 039/037/040 集成。
- [sqlite-migrate-replay.log](logs/sqlite-migrate-replay.log)：独立空库迁移至 `0089` 通过。
- [django-check-migration-check.log](logs/django-check-migration-check.log)：`check`、`makemigrations --check --dry-run`、`migrate --check` 均通过。
- [backend-full-crm.log](logs/backend-full-crm.log)：尝试 Django `crm` 全量；运行在 CSV 导入相关输出后长时间无新进展，人工中断，没有失败摘要，因此不标记为全量 PASS。

### 前端和真实 Chrome

- [frontend-node-test-unit.log](logs/frontend-node-test-unit.log)：Node 单元测试 `169/169` 通过。
- [frontend-vitest-valid.log](logs/frontend-vitest-valid.log)：排除两个基线非有效 Vitest 文件后的有效集合 `65 files / 636 tests` 通过。
- [frontend-vitest-all-initial.log](logs/frontend-vitest-all-initial.log)：原始 `tests/` 集合 `66 passed / 1 no-suite failure`；失败文件为既有 `detail-drawer-typography.spec.js`，不是业务断言失败。
- [frontend-build.log](logs/frontend-build.log)：生产构建成功，保留既有大 chunk warning。
- [playwright-iss022.log](logs/playwright-iss022.log)：真实 Chrome，隔离 runner，`1 passed`。
- [playwright-iss075.log](logs/playwright-iss075.log)：真实 Chrome，隔离 runner，`1 passed`。
- [screenshots/iss022](screenshots/iss022/)：9 张 MOQ 桌面/窄屏业务截图、fixture 和 API 日志。
- [screenshots/iss075](screenshots/iss075/)：4 张付款规则桌面/窄屏业务截图、fixture 和 API 日志。

## 审查边界和遗留事项

1. `ISS-006 / CONFIRMED_DEFECT`：实现服务端可验证的创建请求幂等策略后，至少重复收货、重复发货、网络重试、刷新重提交和并发请求重新执行；关闭条件是库存/履约/订单状态/预留/流水前后快照证明单次副作用，并保持正常分批收货/发货。
2. `ISS-040 / PRINT PREVIEW PENDING`：在具备原生 Excel UI 的验收机上打开 `samples/iss040/sample-e-multipage-60-rows.xlsx`，检查真实分页、每页重复表头、Page X of Y、混装箱行不跨页、Description 可见，并保存原生打印预览证据。
3. ISS-022、ISS-036、ISS-075 的真实业务数据/生产 PostgreSQL/部署代理验证继续按 `BUSINESS_VERIFICATION_PENDING` 或 `DEPLOYMENT_VERIFICATION_PENDING` 处理；本轮未改写其未决规则。
4. Django 全量命令在本环境未完成，不能用定向通过替代全量结果；应在独立、可控的测试运行时重新定位 CSV 导入之后的长时间运行点。

本报告及其脚本、日志、截图和样本是本审查分支唯一新增内容。共享 Issue 台账保持原样，未新增或关闭 Issue。
