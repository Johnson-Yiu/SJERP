# R1-ISS121-HISTORY-IMPORT-PREFLIGHT-01 验收记录

状态：`FIXED_PENDING_REVIEW`。本分支提供历史资料模板及只读预检；没有执行正式迁移，不代表已批准或可直接导入。

## 基线与范围

- 仓库：`Johnson-Yiu/SUNJACK-ERP`
- 固定基线：`a55469c1b07e4f13037c6644c69d8a35ef0496a0`
- 分支：`codex/r1-iss121-history-import-preflight-20261103`
- 数据库迁移：无；没有新增核心模型或修改既有业务表。
- 公共 `PROJECT_ISSUES.md`、`PROJECT_PHASES.md`、`AGENTS.md` 未修改。
- 未导入真实历史资料；未连接生产数据库；未启用 RBAC；未触发 CI；未部署。

## 现状核对与选择

既有历史订单/采购 API 会创建业务记录；现有 CSV 预览会写入预览审计。两者都不符合“无业务副作用的历史全量只读预检”，本任务因此新增独立预检模块，没有修改共享导入核心。

入口：`POST /api/import/history-preflight/`，multipart 字段 `file`；默认返回 JSON，添加 `?report=csv` 可下载逐行 CSV。上传沿用现有流式大小限制；本入口只在内存中解析，不保存工作簿、附件、哈希、预检批次或永久报告。

权限采取 fail-closed：复用 `development_superadmin_enabled()`；其他用户必须通过 `imports:import`、全量数据范围及全部相关模块完整查看权限。未授权请求在解析工作簿前拒绝。结果只返回原行号、来源编号、分组号、检查原因和候选记录类型/ID/状态，不返回上传行中的客户联系人、地址、财务金额或附件内容。

解析只接受本模板的 `.xlsx`、工作表及精确表头；拒绝公式/错误单元格、无效压缩结构、超限文件、超限解压体积及超过 5,000 条数据行。精确主档编码仅作为候选；仅名称命中、重名、冲突或缺失需人工核实，且不会自动创建/修改主档或用当前主档覆盖历史快照。金额、数量、交易单位语义及小数/整数位按当前模型精度校验。CSV 报告中的公式危险前缀会转义。

模板包含 9 张数据表：`分组`、`销售订单`、`销售明细`、`采购订单`、`采购明细`、`收付款计划`、`收付款流水`、`履约记录`、`库存盘点`，以及 `使用说明`。各数据表表头直接从预检代码 `SHEET_SCHEMAS` 生成；模板预设 100 个录入行，服务端限制全文件最多 5,000 条数据行。

## 规则覆盖

- 行号、必填字段、严格日期、币种格式、模型 DecimalField 小数与整数精度、交易单位换算/不可拆分语义。
- 客户、供应商、SKU 编码匹配、仅名称候选、重名/歧义、未找到主档；保留 ISS-037 客户/供应商历史快照，不以现值回填。
- 来源分组、订单与明细、计划与单一父单、流水与计划/父单、履约/冲销与原订单行依赖；文件内来源编号/行编号重复。
- ERP 既有订单/收付款编号、库存流水、日期/单据/SKU/数量相同候选。业务字段相同只产生人工核实提示，不据此自动去重。
- 开放、部分完成、已完成、已取消订单；开放、已结清、已取消计划；有效、已取消/未知履约；实盘范围覆盖。
- 真实/模拟/待核实状态、凭证引用、覆盖不完整、付款计划核销与真实且已确认流水金额对账。
- 只累计真实且已确认资金；待核实/未确认流水不进入已确认资金或订单余额。真实有效履约与冲销按原事件成组核对，冲销不得超过原数量。
- 同一工作簿再次提交会重新执行只读预检；接口不保存文件指纹。已存在业务编号由数据库候选检查识别；不静默复用或自动去重。

银行期初余额、账户余额、真实启用日期及其凭证核验不在模板/接口范围内，必须由财务依据银行对账单另行确认，绝不猜测。库存表只记录盘点基准；库存与订单分配/预留分离。预检不创建余额、采购建议、通知、履约或资金记录。

## 合成预检样例

对合成 `G-1` 关联组中的一张开放销售订单及一条精确匹配 SKU 的销售明细，API 返回结构要点为：

| 范围 | 结果 | 原因/解释 |
| --- | --- | --- |
| 关联组 `G-1` | 通过 | 覆盖状态完整，分组唯一 |
| 来源订单 `SO-SRC-1` | 警告 | 原业务仍未结，只能核实承接剩余状态 |
| 来源明细 `1` | 通过 | SKU 编码精确匹配，数量/单位字段有效 |
| 总体摘要 | 警告 | 3 行：通过 2、警告 1、待核实 0、阻断 0 |

固定响应字段包含 `preflight_only=true`、`approval_or_migration=false`、`business_write_performed=false`、逐行 `results` 和组摘要。预检通过仅表示本次规则检查通过，不代表审批或迁移。

## 数据副作用证据

自动化测试使用合成客户、供应商、产品、SKU、订单/收付款/库存/履约记录，并通过隔离 Django 测试数据库和临时 `MEDIA_ROOT` 调用真实 URL 路由。每个关键只读场景比较前后业务模型计数及订单、SKU、计划、流水、库存流水快照；同时检查 `OperationLog`、CSV 导入审计表和媒体目录未变化。模板空表单被安全拒绝；将合成数据写入模板副本后通过同一 API 解析并得到预期警告结果，业务快照仍不变。

这里的“API”证据是 Django `APIClient` 经 URL 路由/认证/解析器/视图的隔离测试，不是生产网络服务或真实浏览器会话。没有新增 UI，因此 Chrome 桌面/390px 验收不适用；随附 PNG 是工作簿渲染预览，不冒充浏览器截图。

## 测试记录

运行环境：本地锁定 Python 虚拟环境；`DATABASE_URL=sqlite:///:memory:`，`APP_STAGE=development`；Django 测试运行器另建并在结束时销毁内存测试数据库。合成媒体目录独立临时创建并清理。

| 命令 | 结果 |
| --- | --- |
| `python manage.py test crm.tests.test_history_import_preflight crm.tests.test_csv_upload_http_413 crm.tests.test_safe_csv_import --verbosity 1` | 最终代码版本 54 tests，72.193s，全部通过；含 HTTP 413/403 和 CSV 上传安全回归 |
| `python manage.py test crm.tests.test_history_import_preflight --verbosity 1`（模板加入“空模板拒绝 + 填入合成行后成功”回归后） | 最终代码版本 19 tests，25.537s，全部通过 |
| `python manage.py check`（内存 SQLite） | 无问题 |
| `python manage.py makemigrations --check --dry-run`（内存 SQLite） | `No changes detected` |
| 两个 Python 文件的 `ast.parse` | 通过 |
| 最终暂存变更 `git diff --cached --check` | 通过 |

开发期间，模板回归曾发现预格式化造成的工作表范围超限，以及导出 XLSX 未写 dimension 元数据时 streaming reader 的边界问题。服务端限制没有放宽：模板格式范围已收窄到录入区，并在元数据缺失时安全计算实际工作表范围。另一次 500 是移除未使用参数时遗漏了一处调用参数；已修复并由最终 19 项定向及 54 项合并回归覆盖。一次测试 harness 的 `load_workbook` 漏导入也已修复。早期一次未显式指定内存 `DATABASE_URL` 的迁移检查给出无法打开本地数据库文件的警告；随后在内存 SQLite 环境重跑无警告且 `No changes detected`。

PostgreSQL 未执行；本任务无模型迁移，SQLite 测试不被描述为 PostgreSQL 验收。没有实际生产代理/存储/员工数据验证，也没有导入真实资料。

## 文件与后续依赖

- 后端实现：`backend/crm/history_import_preflight.py`
- 路由：`backend/crm/urls.py`
- 上传前置限额路径：`backend/crm/upload_handlers.py`
- 定向测试：`backend/crm/tests/test_history_import_preflight.py`
- 模板与预览：本目录 `ISS-121-history-import-template.xlsx`、`template-instructions-preview.png`、`template-sales-orders-preview.png`

建议后续统一集成任务只追加记录：ISS-121 仍为 `BLOCKED`；本轮只完成模板和只读预检，不解除基准/启用阻断。既定规则（期初余额不算收入、现金银行分离、仅已确认资金影响确认口径）继续保持已确认，不重新列为待决。正式导入仍依赖财务实际启用日、真实账户/银行对账单基准、凭证覆盖及样本核实；同时需要另行审查受控导入授权、结果审计、正式业务写入/回滚和上线验收方案。ISS-121-ADD、ISS-037/038/105/108 的现有业务约束保持不变。
