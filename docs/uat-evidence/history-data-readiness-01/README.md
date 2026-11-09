# HISTORY-DATA-READINESS-01

状态：本包代码与自动/合成数据验收已完成并提交；Chrome 桌面及 390px 视觉验收因浏览器控制策略停止，未通过；没有真实资料副本，没有正式历史承接或生产导入。

## 边界与来源

- 仓库：`Johnson-Yiu/SUNJACK-ERP`
- 共同开发基线：`c90cacaa99a468d92dd61c41437834c5d8acb094`
- 工作分支：`codex/history-data-readiness-01`
- 独立 worktree：`.worktrees/history-data-readiness-01`
- 所有本包提交使用 `[skip ci]`；不触发 Actions、不合并 master、不进行生产数据导入。
- 保留 c90 已有销售订单导入、过期预览令牌授权恢复、历史预检、导航和异步保护；不按 37520998 或祖先关系整包重做。
- 公共菜单/路由/权限/全局样式、最终迁移图与全局接线交 A；共享公共台账由 A 单独更新。本目录给出建议，不并发改写台账。
- 历史财务接续调用现有 `history_operational_finance` → `services.finance_closeout`；不复制旧财务入账逻辑。B 接口需求见 [HANDOFF-B.md](HANDOFF-B.md)。

## 交付状态

| 验收面 | 状态 | 范围 |
|---|---|---|
| 代码完成 | 完成 | 导入结果 CSV、恢复/异步保护、历史页面状态与主档选择、历史维度快照与统计、候选迁移 |
| 合成数据验证 | 自动与文件核对通过；浏览器视觉未通过 | 隔离 SQLite、真实 `codex` 会话、自动回归、XLSX/CSV 内容与只读核对通过；桌面/390px Chrome 截图未能取得，详见 [CHROME-VISUAL-REVIEW.md](CHROME-VISUAL-REVIEW.md) |
| 真实资料核对 | 未执行 | 当前 worktree 没有经授权的真实资料副本；不把历史合成样例视作真实抽样 |
| 正式承接/入账 | 未执行 | 没有承接审批、正式业务写入、资金记账或库存启用 |
| 完整打印分页视觉验收 | 延期 | 仍需独立验证正式打印与分页；XLSX/CSV 文件输出验收不延期 |

## 已接入能力与本包补修

基线 c90 已包含销售订单 XLSX 模板、预览、错误行、草稿创建、结果下载/重开恢复，以及历史资料只读预检入口、导航和异步保护。本包保留其批次身份与权限绑定恢复规则。

本包补修清单以最终提交后的固定 SHA 为准，包含：

- 导入页业务中文列名、模板字段对照、CSV 错误列与行级处理说明；切换文件与预览乱序的保护；确认回调收到账号、权限或页面变化后不继续执行。
- 增加完整订单导入结果 CSV（订单摘要与逐行错误、UTF-8 BOM、公式注入转义）；保留单独错误清单 CSV。
- 历史预检/承接中文状态与未知值“待核实”；主档关联用现有客户/供应商/SKU 搜索选择；普通界面隐藏完整 SHA、数据库 ID 与请求身份，原系统记录/关联组编号保留用于回查。
- 正式销售单在确认时、正式采购单在下单时冻结国家与产品主分类。旧记录无证据仍为空并按“待核实”统计；不从现有主档回填。报表、明细、导出、历史汇总和仪表板统一使用快照。
- 修复预检解析器覆盖 v2 文件历史分类和供应商国家快照的缺陷；CSV 关联明细移除数据库 ID/请求身份类字段，保留原系统记录号与来源关联组编号。
- 候选迁移仅加字段，不含任何历史回填；会明确处理 SQLite 既有防护触发器与表结构变更的兼容性。

## 历史口径规则

- 销售客户国家/主体：销售订单正式确认时冻结 `customer_country_snapshot`（原已有字段）；交易对手名称沿用原有正式快照。草稿允许在确认时按确认所用的资料冻结。
- 销售/采购商品主分类：对应明细随父单正式确认/下单时冻结分类来源编号与名称快照。草稿阶段不宣称为已确认历史事实。
- 采购供应商国家/地区：采购单正式下单时冻结 `supplier_country_snapshot`。
- 历史资料承接只接受来源工作簿提供的快照；无原始证据则为空/“待核实”，不读取当前主档为其补值。
- 历史报表按有效快照匹配；旧快照值与当前主档已不同时，分类键同时保留快照名称，避免旧分类随主档改名/改关联漂移。未知维度单列“待核实”。
- 不回写财务快照，不重写既有不可变业务事实，不用当前客户/产品值填充旧空值。迁移没有数据迁移函数；部署前后应核对旧空值保留率及新增确认记录的快照覆盖率。

## 首发数据准备

需经业务/财务逐项提供并复核的启用核对表见 [DATA-PREPARATION-CHECKLIST.md](DATA-PREPARATION-CHECKLIST.md)。当前真实账户、启用日、银行期初、未完销售/采购、应收应付、库存与来源映射均没有已授权证据，状态留作待核实；不编造数值、主体、税号或历史状态。

银行期初余额是启用基准，不能当作新业务现金流入。历史已收、已付及已发货资料必须与正式流水/履约核对，不能重复计入。历史报价导出风险和当前可确认范围见 [REAL-SAMPLE-REVIEW.md](REAL-SAMPLE-REVIEW.md)：目前只有旧合成测试证据，没有真实受影响记录数。

## A/B 交接与公共记录建议

- A 的公共接线和台账建议：[HANDOFF-A.md](HANDOFF-A.md)
- B 的统一财务服务接口建议：[HANDOFF-B.md](HANDOFF-B.md)
- 建议 A 在本包最终复核通过后追加一次 HISTORY-DATA-READINESS-01 记录，准确列出本包 SHA、测试/Chrome 证据、migration dependency、真实资料未核对和正式承接未执行；不要关闭 ISS-121，也不要把代码完成扩大成上线数据准备完成。

## 运行证据

## 自动与本地合成验证

以下命令均在独立 worktree 执行；退出码为 0：

- `python manage.py test crm.tests.test_formal_party_snapshots crm.tests.test_historical_orders crm.tests.test_history_import_preflight crm.tests.test_history_takeover crm.tests.test_reporting crm.tests.test_sales_order_import crm.tests.test_access_implementation --verbosity=1`：108 项通过，4 项跳过。
- `npx vitest run tests/sales-order-import-ux.spec.js tests/history-takeover.spec.js tests/import-ux.spec.js --reporter=dot`：23 项通过。
- `npm run build`：通过；Vite 仍报告既有主 JS chunk 大于 500 KB 的建议性警告。
- `python manage.py check`：通过。
- `python manage.py makemigrations --check --dry-run crm`：No changes detected。
- `python manage.py migrate --noinput`：在临时隔离 SQLite 全量迁移通过，包含候选 `0123_history_reporting_snapshots`。
- `git diff --check`：通过。

真实登录和下载文件在临时隔离 SQLite 上执行，账号为本机测试超级管理员 `codex`；`DEVELOPMENT_SUPERADMIN=false`、`RBAC_ENFORCEMENT=true`。凭据从被忽略的本地测试配置读取，未输出或保存。实际 API 返回并保存了 [销售订单 XLSX 模板](downloads/sales-order-import-template.xlsx)、[历史承接 v2 XLSX 模板](downloads/history-takeover-template-v2.xlsx) 和 [合成历史预检 CSV](downloads/synthetic-history-preflight.csv)；逐表/逐列、Content-Disposition 文件名、模板说明、CSV UTF-8 BOM、来源编号及 2024-08 合成期间摘要见 [下载内容清单](downloads/acceptance-manifest.json)。有效/无效输入也留存为 [销售草稿合成工作簿](downloads/synthetic-sales-order-valid.xlsx)、[错误提示合成工作簿](downloads/synthetic-sales-order-invalid.xlsx) 和 [只读预检合成工作簿](downloads/synthetic-history-preflight-sample.xlsx)。

合成销售样本预览为 1 张可导入草稿；无效 SKU 样本返回明确的“找不到 SKU”行级错误，两个预览均未写入业务数据。预检 CSV 来自实际 POST 下载响应；重复核对时所有 CRM 模型记录数与私有媒体文件清单前后完全一致。预检结果为“待人工核实”，因为样本真实性与资料覆盖被明确标为待核实；这不是正式承接候选或批准。

Chrome 页面验证状态与当前阻断见 [CHROME-VISUAL-REVIEW.md](CHROME-VISUAL-REVIEW.md)。本包不能标记为 UI/UX 验收全部通过；必须在可安全读取当前浏览器 URL 的 CUA 会话中补做 `codex` 登录、ImportPage/HistoryPreflightPage/HistoryTakeoverPage 桌面和 390px 窄屏中文与滚动检查并保存截图。完整打印分页验收另行延期。

## 迁移审查

`0123_history_reporting_snapshots` 的依赖为 `0122_merge_sales_and_finance_review`。新增供应商国家和订单明细分类快照字段为空字符串；无数据迁移/回填。SQLite 与 PostgreSQL 使用显式 `ALTER TABLE ADD COLUMN ... DEFAULT ''`；PostgreSQL 随后移除临时默认，避免对旧记录赋予任何历史维度含义，并避开 Django SQLite 表重建可能触发的不相关草稿防改触发器。它仍是本包候选迁移；A 负责并行包依赖统一、最终全局迁移图和全局验收。

截图、账号凭据、真实账户资料与真实历史文件均未写入本目录。凭据不写入本目录、Git、初始化脚本、控制台日志或截图。
