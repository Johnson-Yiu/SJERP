# 首发追加独立复审交付清单

代码集成提交：`1c570164b754db4be0695fc195de3372b9017ffc`（合并父提交 `49189649` 与 `0a3418d7`）。最终证据提交在该提交之后，业务代码相同。

日期：2026-11-09。分支：`codex/first-release-independent-review-02`。基线：`37520998e347afb34b00d725014d0137a49a6920`。本报告不构成对旧任务的整体接受，不关闭任何 Issue。CI、全量测试和部署均为 `NOT_RUN`。

## 来源与接入映射

| 任务 | 来源 SHA | 实际接入/交付 | 可核对证据和范围 |
| --- | --- | --- | --- |
| FIRST-RELEASE-INTEGRATION-01 | `f5a91a5ff0b75f2e5b45a6efcf04a36f57da37f0`，基线 `aa15c9ba7584599e918c1dd14723d31e31158b3d` | `b223c052902463b59e149409cf9941503aeab31f`，为本分支祖先 | `../first-release-integration-01/README.md`：主体、提醒、会话、多标签、真实报价 XLSX、ISS-062 与 PostgreSQL 定向证据。旧报告的范围不扩大。 |
| FIRST-RELEASE-CONSOLIDATION-02 | `945c2ae41ce59d55051bbab4664f3d7a4df0fbba` | 文案补丁 `6cb20a84`；交付 `f9dfcd4c5792c4b0f213aeb0940e7e66efecd33a` | `../first-release-consolidation-02/README.md`：实际银行资金导航、CSV、XLSX；当时预检用临时表单调用 API，没有产品预检页面。 |
| SALES-ORDER-IMPORT-01 | `2bff4790f67b81b35a449f143b8cddb6b24e1821` | 原集成 `37520998e347afb34b00d725014d0137a49a6920`；本次保护补修 `49189649f25fbe4849cf717d8d0118add556d794` 及本报告所在集成提交 | `../sales-order-import-01/README.md` 与本目录 Chrome 文件、PG 日志；原重试权限修复保留，当前范围收窄后不得返回订单。 |
| HISTORY-PREFLIGHT-WEB-01 | `4c29837f42697596c8c67e8c2d34379a5939eebd` | `3ba114aaac7e7293bf9a8f8d3337cb164b8f9a3b` | 完整页面、导航、权限接线和 `workspaceRoutes.js` 的 `/history-preflight`；原 API 依赖已在基线，未重复开发后端。 |
| HISTORY-PREFLIGHT-WEB-FIX-01 | `ecb38a7869ebff35ac76a876ee1f801616a64db0` | `570e3c28df196d8494083072f4af326bfb853a54`，并补工作区请求及卸载检查 | `../history-preflight-web-fix-01/README.md` 是来源证据；本目录实际 CSV 与只读快照为本次接入验证。 |
| 导航改名 | `945c2ae4` | `6cb20a84`，本分支继承 | 来源只有 5 个文件、9 行替换，不能称为全站中文优化。银行资金记录的既有业务能力及权限保留。 |
| 全站中文优化 | `a5869a50`、`0580cd5c`、`01b6fe73` 等独立文案历史 | `01b6fe73` 不是 `37520998` 的祖先；本轮没有整包重放这些改动 | `01b6fe73` 涉及历史/财务工作流与相关测试等 27 文件。全站中文完成情况仍 `NEEDS_VERIFICATION`；下一步按实际文件补丁逐项核对，不能用导航改名替代。原业务术语、持久化值及风险说明继续保留。 |
| FINANCE-RECEIPT-SETTLEMENT-01 | `b75b48cc1b6c9e8e4c9eb359aa36da639bf1a18c` | 原集成 `f886b064c694589acd60e5a910c5858e26846376`；本分支合流保留 | `../finance-receipt-settlement-01/README.md`。共享结汇组件、来源根收款绑定及弹窗行为保留。 |
| FINANCE-TRANSACTIONS-UNIFIED-ENTRY-01 | `52d924b05085e67bf97dc5a5cfac01b6ba48ed70` | 源补丁纳入 `0a3418d7c35bfd006ea70816c71a866646b73aa2`，为本分支合流父分支 | `../finance-transactions-unified-entry-20261107/README.md` 为原验收记录；本轮以真实请求重新复核其金额和组件边界。保留当前首发银行资金导航，没有照搬来源任务的隐藏导航。 |
| FINANCE-INTEGRATION-REVIEW-FIX-01 | A/B 如上，共同祖先 `78bcedb217d3d6ca0a05c9348e72d37c35801312` | `.worktrees/finance-integration-review-fix-01`，`codex/sunjack-finance-integration-review-fix-01`，本轮找回并保存为 `0a3418d7c35bfd006ea70816c71a866646b73aa2`；继续补修纳入本报告所在集成提交 | 上轮没有最终提交和推送。原本地修改完整保留；本轮没有重新开发整包，新增修复、迁移和验收见下。 |

## 本次修复与定向验收

- 历史预检每个响应、错误和 CSV 下载都绑定文件对象及选择版本，并使用工作区 API；卸载后旧结果不会更新页面或触发下载。自动回归覆盖 A 未完切 B、B 先返 A 晚到、下载中换文件及错误晚到。Chrome 从产品页面保存 `integrated-history-preflight.csv`，实际内容包含 `FIXB-SO-1`、没有 `FIXA-SO-1`，有 UTF-8 BOM。订单、流水、应收应付、库存流水和承接申请的前后 API 快照相同；更广模型和私有媒体不变性另有来源证据与后端专项。
- 销售预览、确认和提交均进入路由、工作区关闭及刷新保护；确认返回和提交前检查存活、文件、预览对象和操作代次。卸载后的确认回调不会创建订单。提交前保存按账号分区的原预览身份和文件元数据，不保存订单内容；不同文件的待核对身份分开保留。同文件的另一预览不能覆盖尚待核对身份。重开选择原文件后按原令牌核对结果。过期令牌仅可读取已有批次，仍执行操作人、文件摘要和当前客户范围检查，不能发起新建单。
- Chrome 通过真实 UI 预览、确认，故障注入在同一已认证会话向真实服务提交同一文件与令牌，待服务端已保存后丢弃浏览器响应；重开后再次确认返回同一 `batch_id`。故障转发明确重建 multipart 原始文件字节，避免浏览器拦截桥将二进制工作簿转成文本。实际 XLSX 模板、错误 CSV、结果 JSON 和截图在 `browser/sales-order-import-real.spec/`。
- 实收与核销拆分：现金 980、我方手续费抵扣 20、核销 1,000；普通退款上限仍是实际可退现金。手续费只计入费用/利润一次，不新增虚构现金支出；抹零及其更正不计现金。商业超额退款沿用既有性质、依据和审批入口。
- `NotFound` 已导入；关联收款缺失、无权、类型和币种异常走 4xx。扩大核销额度需要有效用途、文件完整性与来源绑定的凭证。PG 专项覆盖缺文件、损坏、错误 scope 和来源绑定，及部分分配、多订单、多次退款、作废和重试。
- 抹零更正保留原记录，追加更正、原因、操作身份和审计；沿用原财务授权。更正受原记录剩余额度约束，支持部分、累计、同请求幂等、并发竞争和审计失败回滚，恢复计划状态及原流水操作条件。没有降低既有适用双人复核规则，也没有把开发身份冒充员工审批人。
- 共享结汇组件同时保留 `source_receipt_id`、`gross_rmb_amount`、`actual_rate`。Chrome 找到并修复了三个交互缺口：收款保存前结汇必填字段阻断父表单；关联模式缺少系统请求编号；空核对说明可登记成无法确认的草稿。新增按钮也在保存结束前禁用，避免连续录入时点击无响应。来源额度仍只取原币实收；人民币仅按已确认净额计入一次。

## 数据库、测试及迁移证据

- 真实 PostgreSQL **17.11**、数字回环地址、独立集群和合成库。`combined-postgres-tests.log`：财务 37 项与销售导入 10 项合计 **47/47**，包括真实并发来源额度竞争、同请求防重、抹零更正竞争和业务/审计失败回滚。没有将 SQLite 标为 PostgreSQL。
- 保留主体与销售导入各自的 `0110`，及财务来源迁移 `0109` / `0110` / `0111`；`0119_merge_finance_and_party`、新增现金拆分/抹零更正 `0120`、历史手续费分配现金纠偏 `0121`，最终由 `0122_merge_sales_and_finance_review` 汇合销售 `0119` 与财务 `0121`。没有重写原已应用迁移。
- PG 测试库从空库完整安装到合并叶；已有隔离库从财务 `0120` 升至 `0122`，新增销售支线，Customer/Order/PaymentPlan/Transaction/FinanceAccount 的逐字段有序 JSON 完全一致（7,700 字符）。原始合成快照为 `upgrade-before.json`。`makemigrations --check --dry-run` 无变化。
- 前端定向 Vitest：历史竞态 6、销售离开/恢复 5、既有 CSV 状态 1，共 **12/12**；财务入口 Node 专项 **11/11**。必要生产构建通过，保留既有大 chunk 提示。没有运行全量或 GitHub Actions，CI 为 `NOT_RUN`。
- 真实 Chrome 专项 **4/4**：销售响应丢失恢复、历史 A/B 竞态与下载换文件、收款内联结汇、三种手续费/退款拒绝/抹零更正。`evidence-manifest.json` 记录实际下载与截图的字节数和 SHA256。
- Chrome 身份为真实登录的测试超管 `codex`，`development_superadmin=false`，测试库 RBAC 配置保持既有状态。截图为真实 Chrome，人工检查文件名、金额、表格、风险说明及桌面/390px 销售导入，无横向溢出。主结汇流程确认净到账 6,928，仅一笔；订单实收仍 980，计划余额 0。

## 本地历史上传实例单列

实际读取 `D:\SUNJACK-HISTORY-UPLOAD-01\instance.json`：`app_candidate_sha=b37fbaa76564e0d281c237ab71ceaf5f1add5c58`，对应分支 `codex/local-history-upload-env-01`，不是本轮产品集成分支。原本机浏览器记录包含 `ecb38a78` 页面修复，3 行、2 通过、1 警告、0 阻断；19 模型及媒体不变，合成主档已清理且备份恢复通过。实际保留 CSV 本轮重新计算为 **550 字节**，SHA256 `05fe40ea66d1c1ffc5c5248155591b14eb2a613d0d35ee82d4cc8f43e7d7c048`，与原记录一致。

证据准确映射见 `local-upload-instance-verification.json`。私有原件位于实例 `logs/manual-chrome-evidence.json` 和 `logs/manual-chrome-evidence/history-preflight.csv`。原 JSON 同时保留了早期 `PENDING_OWNER_MANUAL_CHROME` 字段和后续 PASS 字段，报告明确保留此记录一致性缺口。本轮只读核对已有证据，没有启动、升级或部署实例，也没有用产品代码已合入冒充实例升级验收；当前活进程 SHA 未重新证明，下一步由实例专项核对其进程、HTTPS 健康与清理后的基准。

## 保留的限制与下一步

- ISS-006/052：本次导入防重与生命周期修复待独立复审；不扩大为所有导入或所有异步页面验收。
- ISS-121：预检页面已接入，但预检通过不代表承接审批、正式迁移或真实资料入账已通过。本轮只使用隔离合成数据。
- ISS-105/108：保持 `FIXED_PENDING_REVIEW`；财务整体、垫付报销、押金及其他本轮未覆盖范围继续保留原状态和后续专项，不因本次通过关闭。
- 真实历史报价的 NULL 税号、不能映射到模板的主体字段仍可能使 PI/XLSX 返回 422；保留未知值。见首发原报告的常用模板和代表性旧报价证据。下一步核实受影响范围，并按授权更正历史资料或明确模板的安全表达方式；不能自动从主档补值。本轮没有再读取真实业务库。
- 全站中文及本地实例当前运行验收按上述范围另行核对。原始来源记录、首轮验收脚本失败、Chrome 找到的交互缺口和后续修复不相互覆盖；最终等待独立复审，不部署、不合并 master。
