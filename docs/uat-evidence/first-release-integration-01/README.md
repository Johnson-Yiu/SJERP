# SUNJACK-ERP FIRST-RELEASE-INTEGRATION-01

## 范围与集成

- 首发集成基线：`aa15c9ba7584599e918c1dd14723d31e31158b3d`。
- 接入来源：`f5a91a5ff0b75f2e5b45a6efcf04a36f57da37f0`，在独立工作树和分支 `codex/sunjack-first-release-integration-01` 完成。
- 保留基线的多工作区标签、登录会话/当前操作人接线和新品提醒路由/API。`0118_merge_party_reminders` 合并两个 `0109` 迁移分支。另将新品提醒迁移作为 `0115_party_replacement` 的依赖，保证拒绝主体数据回退时不会先撤掉提醒表；当前升级及回退保护均在隔离 PostgreSQL 复验。
- 未改开发身份规则、启用正式 RBAC、导入真实数据、部署或关闭 Issue。

## 定向验证

### PostgreSQL 17.10

使用本轮拥有的一次性集群和合成资料，从 `0109_new_product_reminders` 起步，建立一条旧报价和一条新品提醒后升级到 `0118_merge_party_reminders`。保存的买方名称、收件人、地址不变；`buyer_tax_id` 保持 `NULL`；提醒记录仍在。`migrate --check`、`makemigrations --check --dry-run`、Django system check 通过，测试数据库无泄漏，集群已停止并清理。

首轮 243 项 PostgreSQL 主体/报价/Dashboard 定向集合中，除一个跨迁移回退保护测试外，其余通过。该测试的五个子断言发现回退拒绝前可能先撤掉无关的提醒迁移。修正 `0115_party_replacement` 依赖后，重新升级并通过回退保护类 2 项；再把 ISS-062 新用例加入最终 PostgreSQL 确认，最终升级、迁移检查、模型检查及定向测试全部通过。最终确认共 3 项：回退保护 2 项、ISS-062 重算 1 项。此处没有重跑全部 243 项集合。

证据：`postgres-final-confirmation/result.json`、`party-and-quote-postgres-tests.log`。首轮失败保留在 `postgres-escalated/`；不以最终聚焦通过掩盖首轮发现。

### SQLite、前端与 Chrome

- ISS-062 Dashboard 定向：5/5。覆盖截至日期窗口、部分数量取消、跨期合同修订、订单日期更正后按期重算，以及自定义未来期间报表。
- Vitest 定向：7 个文件、86/86（工作区管理、主体变更/详情/替换、新品提醒、报价可用性和列表）。日志：`frontend-targeted.log`。
- 已安装的 Google Chrome 通道 `156.0.8078.80`，隔离 SQLite 与合成资料：报价保存/导出 1/1；工作区标签页 6/6；会话、新品提醒与多客户并行草稿 4/4；独立登录、权限边界、过期和退出 4/4。浏览器均使用一次性隔离 API、数据库和媒体目录。
- 登录流程使用隔离环境中的合成账号，验证真实 Django 登录会话、`current-operator` 和 `development_superadmin=false` 接线；不代表真实员工姓名或正式账号验收。
- 人工检查报价编辑器 1440px 和 390px 截图。桌面和窄屏文案简短自然；保存、预览、导出操作名称清楚。390px 与 320px 操作区断言无横向溢出，侧栏完全收起。
- 本地全量与 GitHub Actions 按用户要求 `NOT_RUN`。

浏览器证据：`browser/quote-editor-mobile-actions.spec/`、`browser/workspace-tabs-real.spec/`、`browser/workspace-integration-real.spec/`、`browser/evidence_dir/`。

## 报价文件与主体字段影响

真实 Chrome 点击“保存并导出 Excel”：保存请求 HTTP 201，导出接口 HTTP 200，浏览器收到并保存实际文件。OpenPyXL 可读出 PI 工作表 `A1:M35`，报价号 `SJ20261106DE002`、型号 `R1-QA-MODEL`、数量 `1`、单价/金额 `12.5`，无替换字符。文件为 `browser/quote-editor-mobile-actions.spec/downloaded-quote.xlsx`；解析结果和 SHA-256 在 `xlsx-inspection.json`。本样本为合成数据。

常用 `standard_en_no_discount` 和 `standard_en_with_discount` 两个模板的快照、PI/XLSX 生成及批准后修订路径均有定向覆盖。字段齐全的样本可生成文件。代表性历史报价若买方税号为 `NULL`，PI 和 XLSX 均返回 HTTP 422；数据库值仍是 `NULL`，不从客户主档补写。当前模板没有买方国家、联系人、账单地址和收货地址的独立位置，非空值也会阻止输出。历史卖方资料存在缺失或无法映射时同样可能被拒绝。

结论：这些限制会阻断受影响报价的 PI/XLSX 出单；在现有 API 验证中，它们**不阻断销售订单保存和确认**，未知税号会原样带到确认后的报价修订中。未查询真实历史库，受影响报价数量及首发客户覆盖未知；首发若必须输出此类旧报价，仍须按授权核实历史值或确定可安全表达未知/扩展字段的处理方式，不能自动填补。

## ISS-062 补验场景

冻结服务端日期 `2026-11-06`。先把 10 件订单部分取消到 6 件，订单总额变为 600；批准金额 `+200`、到期日 `2027-01-15` 的跨期合同修订。当前 Dashboard 计入 5760 RMB，品类金额 4320 RMB。将订单日期更正到 `2025-11-05` 后，本年归零并计入上年同期；再改为 `2026-10-31` 后，金额进入 2026 年本年与 10 月、11 月归零。SQLite 5 项和最终 PostgreSQL 精确场景 1 项均通过。此项只补回归，不更改日期或会计口径。

## 仍待首发处理

1. 真实历史报价中 `NULL` 必填字段及当前模板未映射的非空主体字段会阻止 PI/XLSX；尚无真实数据覆盖统计或经授权的修订方案。
2. 本轮只跑相关定向集合。项目已记录的完整浏览器套件曾出现报价 XLSX `saveAs canceled` 且根因未知；本轮实际 Chrome 单次保存导出成功，但不替代全套复核。正式启用前仍需执行其余项目既定上线验收、独立复审及正式身份/RBAC验收。

以上限制没有被本次分支交付自动关闭；不宣称系统整体首发就绪。
