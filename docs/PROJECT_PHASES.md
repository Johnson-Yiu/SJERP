# SUNJACK-ERP 阶段计划与验收状态

## 2026-11-10 RELEASE-INTEGRATION-REPAIR-01 补验

补齐同一浏览器标签页内库存未知提交恢复，复验 Chrome 原生 100%／125% 和长记录，并完成隔离 PostgreSQL 真实恢复、加密签名及保留策略。前端全量定向门禁通过；SQLite 后端全量未通过，前向迁移复验结果单列。正式目标环境未核验，详见[补验记录](uat-evidence/release-integration-repair-01-followup/README.md)。

## 2026-11-09 RELEASE-INTEGRATION-REPAIR-01

以 `c90cacaa` 为共同基线，已合入 A、B、C、D，迁移在 `0128` 汇合。PostgreSQL 17 和 SQLite 各完成空库、c978、c90 三入口定向复验；真实 Chrome codex 定向验收及实际 XLSX/CSV 下载已记录。阶段为集成完成、待补发布验收；未执行项及测试口径见[本轮验收记录](uat-evidence/release-integration-repair-01/README.md)。旧证据和旧阶段状态保留。

## 2026-11-09 首发追加独立复审

从 `37520998` 创建独立分支 `codex/first-release-independent-review-02`。已接入 `4c29837f`/`ecb38a78` 完整预检页面，局部接入工作区路由与 API 生命周期；销售离开保护及结果恢复补修 `49189649` 后继续完善。找回财务未提交工作树并保存 `0a3418d7`，合流来源 A/B，新增 `0122` 合并迁移保留主体、销售和财务各自迁移历史。PG 47/47、真实 Chrome、实际下载和现有库升级证据按[统一交付清单](uat-evidence/first-release-independent-review-02/README.md)逐项解释；不以导航改名代替全站中文，不以产品集成代替本地历史上传实例验收。完成提交推送后等待独立复审；旧 Issue 不自行关闭，CI=`NOT_RUN`。

## 2026-11-08 SALES-ORDER-IMPORT-01 集成

以 FIRST-RELEASE-CONSOLIDATION-02 的 `f9dfcd4c5792c4b0f213aeb0940e7e66efecd33a` 为基线接入 `2bff4790f67b81b35a449f143b8cddb6b24e1821`。保留原销售订单 XLSX 导入行为，新增重复确认时对当前操作者及订单数据范围的校验，并以 `0119_merge_sales_order_import` 汇合主体版本 `0110` 支线、历史提醒和销售导入 `0110` 支线。相关验收：SQLite 7 项通过、PostgreSQL 17.11 9/9、真实 Chrome codex 超管 1/1，前端定向 9/9。实际 CSV、XLSX 和桌面/窄屏截图保存在 [验收证据](uat-evidence/sales-order-import-01/README.md)。本地全量和 GitHub Actions 为 `NOT_RUN`；等待独立复审，不部署、不导入真实业务数据。

## HISTORY-PREFLIGHT-WEB-FIX-01（2026-11-06，修复完成，待独立复审）

基于已推送页面提交 `4c29837f42697596c8c67e8c2d34379a5939eebd` 新建独立工作树 `.worktrees/history-preflight-web-fix-01` 和分支 `codex/history-preflight-web-fix-01`。修复文件选择世代和预检来源文件绑定：切换文件立即使旧预检/下载请求失效并清空其展示，B 可在 A 仍未返回时启动；旧 A 成功或失败晚到都不会改写 B 的汇总/行级结果；CSV 仅从当前汇总所对应的工作簿请求。

定向 Vitest 两文件 10/10、`npm run build` 通过。三个场景由延迟 Promise 测试验证。内置浏览器实际选择 `workbook-B-duplicate.xlsx`，页面显示其 4 行/4 阻断及 `FIXB-SO-1` 行；点击下载后保存实际文件 `history-preflight.csv`（1,912 字节）。解析 CSV 与 B 工作簿的销售订单来源编号多重集完全相同：两条均为 `FIXB-SO-1`，没有 A 的 `FIXA-` 编号。隔离 SQLite/私有媒体快照前后 SHA-256 相同。完整复现步骤、命令和文件见[验收报告](uat-evidence/history-preflight-web-fix-01/README.md)。

未运行全量测试或 GitHub Actions；提交使用 `[skip ci]`，CI 为 `NOT_RUN`。新修复待独立复审，不改 Issue 计数/状态、不合并 master、不部署。上一轮完整 Chrome 下载证据缺口由本轮实际文件核验补足。

## HISTORY-PREFLIGHT-WEB-01（2026-11-06，已实现，待独立复审）

从固定 SHA `b7ce265833320cc62a7b9aa57e08880f6013203f` 创建独立工作树 `.worktrees/history-preflight-web-01` 和分支 `codex/history-preflight-web-01`。新增只读「历史资料预检」页面，复用 `POST /api/import/history-preflight/` 与 `?report=csv`，提供文件选择、汇总、行级问题和 CSV 报告；入口与「历史资料承接」明确分开。没有数据库迁移、真实资料导入或权限架构变更。

定向验收：后端预检 23/23、前端页面及历史承接回归 8/8、前端生产构建通过；真实 Chrome 观察成功、重复来源、错误文件、页面内容及两个入口之间的导航。既有后端未授权用户得到 403。Chrome UI 点击 CSV 后真实请求返回 200；浏览器自动化桥接未暴露本地保存的下载事件，所以额外将同一端点响应保存成 CSV 并检查附件响应头、BOM、列头和 3 行内容，不声称已从 Chrome 下载栏取回文件。前后状态快照严格一致：19 张模型表、库存流水、应收/应付、销售/采购订单及私有媒体均无变化；基线包含合成用的客户/商品/SKU主数据。完整操作、命令与证据文件见[专属验收记录](uat-evidence/history-preflight-web-01/README.md)。

按用户“只跑定向测试”约束，不运行全量套件；依据项目额度约定提交 `[skip ci]`，GitHub Actions `NOT_RUN`。新包待独立复审，不创建或关闭 Issue；当前总数仍 124 项，FIXED_PENDING_REVIEW 87、NEEDS_VERIFICATION 14、BLOCKED 13、OPEN 0、CLOSED 10。浏览器中现有「历史资料承接」页的列表 API 在当前匿名开发会话返回“身份认证信息未提供”，本包未修改该既有认证路径，故只确认入口清晰分开，不宣称提交页通过端到端验收。未合并 master、未部署、未启用正式 RBAC。

## FINANCE-RECEIPT-SETTLEMENT-01（2026-11-07，已实施，待独立复审）

基线 `b223c052902463b59e149409cf9941503aeab31f`，独立分支 `codex/finance-receipt-settlement-01`。人民币资金新建、预览、确认和详情共用简化表单；系统处理事件身份和上传文件校验，账户按可读名称选择，缺少配置时给出维护指引。新增记账的其他期间费用仅调整显示文案，分类值不变。所有 Vue 业务弹窗不再由遮罩点击关闭；显式关闭仍走既有未保存保护。

客户收款选择外币后可在原窗体展开同一套结汇组件；展开不保存，显式“保存收款并继续”后先保存客户收款，使用实际保存后的流水和其拆分家族建立结汇来源。后端校验收款根流水、订单关系、币种、来源家族及额度；未分配预收单独列出；保存结果不明时先按原流水核实。专项测试和 Codex 内置浏览器证据见 `docs/uat-evidence/finance-receipt-settlement-01/README.md`。依用户要求未执行全量测试或 CI；CI 记 `NOT_RUN`。下一步：独立复审按专项报告核对已推送 SHA；不更改现有 Issue 状态，不代表进入内测或上线。

## 2026-11-05 新授权并行开发（待实施）

用户明确授权 `NEW-PRODUCT-REMINDERS-01` 和 `INTERNAL-WORKSPACE-TABS-01` 并行开发，均从固定起点 `10afcf16fbfc1d0c01a175094012b4b696483cfb` 分别创建独立工作树和分支 `codex/new-product-reminders-20261105`、`codex/internal-workspace-tabs-20261105`。这里登记的是授权和计划，不代表分支已创建、功能已实现或验收通过。此次标签页授权替代旧的“全部 Issue 修复后再开发”排期；历史阶段中的当轮排除仍为当时记录。

- 新品提醒：围绕客户跟进记录产品需求，提供固定标签、关键词搜索、关联跳转、作废留痕与禁止删除；默认有效，作废浅灰且明确标识。不自动匹配新品，不自动向客户发送消息。
- 内部工作区标签页：先审阅前端与本地工作树并盘点入口，再实现 ERP 内多标签、独立草稿和上下文、未保存保护、导航一致性、账号隔离及资源回收。
- 文件归属：标签页包负责壳层、导航、工作区状态；新品包负责需求模型、API 和专属组件；主体包负责主体和修订；身份包负责认证、权限和登录。`ResourcePage`、`DocumentPage`、路由及应用壳层只作协商后的局部接线，不整文件重构或相互覆盖。
- 集成顺序：当前 LOCAL-RELEASE-VALIDATION-03 冻结候选照常执行和交付，不因新需求重启。新包稳定后另建集成候选，复核迁移图、入口、草稿隔离、会话失效及业务回归，再执行适用本地全量；GitHub Actions 保留至上线前最终验证。此授权不代表进入正式 RBAC、部署或上线。

详细需求及验收入口见 [需求台账](PROJECT_ISSUES.md#2026-11-05-新增授权需求待开发)。

## INTEGRATION-CLOSEOUT-02 当前核实（2026-11-05）

统一分支`codex/r1-prelaunch-consolidation-20261104`。完整稳定财务来源e301a86044ffe56b72172a94dc3b00ae09401b05、Linux来源4a4f338b09e9a464f1e66c24a905c35c970729bf、历史来源ba4274742727a6794608dc8581a49b3692d865a6均已合入。当前已冻结并完成本轮全量的候选为02140bf46df27ba1abf5b9018507c07aae825769；仅两处前端下载生命周期补修，无数据库、金额、日期、权限逻辑变化。

最终候选实际结果：Python3.12 SQLite1410项1338通过72跳过（含8项原生PG备份命令）；真实PG17.11全量1410项1378通过32跳过，均0失败/错误。102表1218行133迁移5文件恢复一致，三类恢复及9项不可变保护通过并清理；追加独立源状态专项6/6，在操作末尾实际重读102表1218行100序列与5文件，前后相同，不追认此前1410运行曾做该末尾重读。Node179、字体1、Vitest725/78文件及构建通过。适用Playwright9profiles实际262通过1失败0跳过，报价仍saveAs canceled，当前继续诊断；不能把之前单次定向PASS当彻底修复。整份打印7项NOT_RUN_USER_DEFERRED，原断言未删。

同一02140历史Chrome5/5脚本、98个本地HTTP请求、live及脱敏副本只读核验通过，8图、实际XLSX、数据库/媒体及日志已封存，进程/端口/私有任务目录清理完成。SQLite发布副本102表1091条业务/审计行，删除2个session行但业务表未改；不与PG1218行混为同一数据集。不把开发身份、合成双session或Django admin当作真实员工ERP登录。

当前124唯一ID：FIXED_PENDING_REVIEW87、NEEDS_VERIFICATION14、BLOCKED13、OPEN0、CLOSED10。原86项仍待独立复审，ISS-121完整实现及集成验收证据已补，校准为FIXED_PENDING_REVIEW；新增待复审1项，与原86项队列分开记录；没有关闭Issue。报价浏览器交付子项归ISS-020，财务CSV归ISS-105，附件重开归ISS-007、回执跨UID归ISS-018，不创建重复ID。原86入口365条与当前代码存在性核对不等于业务接受。

用户明确GitHub额度不足：后续提交[skip ci]，不触发、等待或重跑Actions，不改workflow规避；CI暂停不记PASS。历史906/41855319673成功只对应旧源码。旧运行中/未交付描述位于后面的明确历史章节，不覆盖当前事实。

真实Linux补修后跨UID尚未执行：只读检查未找到docker命令，沙箱外wsl列表退出1只返回安装帮助，没有已验证Linux环境。正式认证/RBAC、真实启用资料、生产配置及真实迁移执行分别需目标环境或单独授权；历史代码未完成不能归为缺凭证，退款/已记账反向映射只按已支持范围，不宣称全部支持。打印完整成品与分页继续用户延期，不合master、不部署、不导入真实资料、不宣布上线就绪。

[当前报告](uat-evidence/integration-closeout-02/README.md)、[原86复审包](uat-evidence/integration-closeout-02/REVIEW-BACKLOG.md)、[ISS121补充](uat-evidence/integration-closeout-02/ISS121-REVIEW-SUPPLEMENT.md)、[实际日志](uat-evidence/integration-closeout-02/TEST-RESULTS.md)。

## 2026-11-06 SUNJACK-ERP FIRST-RELEASE-INTEGRATION-01

以 `aa15c9ba7584599e918c1dd14723d31e31158b3d` 为基线接入主体版本 `f5a91a5ff0b75f2e5b45a6efcf04a36f57da37f0`，独立分支 `codex/sunjack-first-release-integration-01`。保留多工作区标签、实名会话/当前操作人接线和新品提醒；修正 0115 回退保护与 0109 提醒迁移的顺序。隔离 PG17.10 最终升级、回退保护和 ISS-062 三项定向测试通过；Vitest 86/86、真实 Google Chrome 定向 15/15。实际下载 XLSX 已解析留档。部分历史主体未知/未映射资料仍使 PI/XLSX 返回 422，但未知值不改写且销售订单仍能保存确认；真实历史覆盖量待核查。全量、GitHub Actions 按用户要求 `NOT_RUN`。详见 [本轮验收报告](uat-evidence/first-release-integration-01/README.md)。不关闭 Issue、不宣称系统整体首发就绪。

## 历史章节：此前阶段摘要（非当前状态）

### 本轮首页此前阶段说明（原文保留，非当前状态）

用户最新CI约定（2026-11-05）：GitHub额度不足，当前后续提交使用[skip ci]，不再触发、等待或重跑Actions，不改workflow配置。旧运行保留实际结果；最终CI标记额度暂停/未执行，不能记为通过。继续本地全量、隔离PG17、真实Chrome和专项；无法本地执行的真实Linux跨UID/目标环境验收另列NEEDS VERIFICATION。独立复审及上线授权边界不变。

当前接收与回归更新（2026-11-05）：财务完整稳定来源e301a86044ffe56b72172a94dc3b00ae09401b05、Linux完整稳定来源4a4f338b09e9a464f1e66c24a905c35c970729bf均已合入（当前接收锚点536789f6dbafb2874b1abfd33ade2b30faa123a4），来源各自CI均成功，不能替代集成CI。a840冻结版本SQLite1330项1266通过/64跳过、PG1330项1300通过/30跳过，均0失败；合入财务来源后d4e8586的三条原反例SQLite3/3及财务PG30/30通过。Linux预审新发现0600签名回执跨UID交接缺口，归ISS-018，集成内最小修复及真实Linux回归中。历史接续仍在开发验收，未交付完整稳定SHA；当前不能称最终集成完成。最后已核实的统一分支三CI仍为906/41855319673，后文该CI只覆盖其精确SHA。

## INTEGRATION-CLOSEOUT-02 当前核实（2026-11-04—05）

最新主审已推送代码90683506f5d9447974302d83c89ba27351d5dfd4，[CI41855319673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41855319673)三项SUCCESS：Backend1259通过/58跳过，PG1287通过/30跳过，均1317项0失败；Node179、字体1、Vitest720、Chrome270及构建通过。主审读取原始日志/精确SHA artifact核对；不称ChatGPT已独立复审906或86项全部接受。两项财务反例的协调修复、原失败与32项SQLite/12项PG专项见本轮报告，三个后续稳定来源接收仍继续。

已交付代码`8087f2c68b19a302a25e814ec8ce6113d91d4750`；[CI41839476121](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41839476121) Backend、backend-postgres、Frontend均SUCCESS，用户已转述ChatGPT实际核实。Backend1254通过/58跳过/0失败，PG1282通过/30跳过/0失败；Node179、Vitest720、Playwright270均通过，生产构建通过。同SHA补充PG15/15与恢复HTTP4/4另列；不将旧失败或来源CI写成新版本通过。

当前124个唯一ID：FIXED_PENDING_REVIEW86、NEEDS_VERIFICATION14、BLOCKED13、CLOSED10、OPEN1（ISS-121已授权待实施）。86项FIXED_PENDING_REVIEW仍逐项等待独立复审，本次定向复审不等于整体接受。代码入口、最新证据及具体关闭缺项见[本轮清单](uat-evidence/integration-closeout-02/REVIEW-BACKLOG.md)，当前状态/新增缺陷与计数见本轮最终校验。未自行关闭任何Issue，保留10项原关闭状态。

ISS-121校准：历史资金、未结、库存基准与剩余履约接通是**已授权开发和合成验收、当前待实施**，不是缺真实凭证；当前归档执行器仍为三个not_connected。真实启用资料、生产配置及真实迁移执行才是外部/单独授权边界。接收历史实际接续、Linux运维、财务反例完整稳定SHA后逐项核查迁移汇合、正式财务服务、组原子性、幂等、新表/文件备份、兼容和权限审计；未交付的移动HEAD不合并。财务公共服务缺陷由统一集成协调，不由历史/财务包同时修改。

仅完整打印成品与分页按用户决定延期；不重试或催办，不扩大延期范围。不合并master、不部署、不启用正式RBAC、不导入真实资料、不宣布上线就绪。[当前报告](uat-evidence/integration-closeout-02/README.md)。

### 更早阶段摘要

以下保留原文及原时点结论，历史“运行中/待提交/尚未实施”不覆盖上述当前摘要。原始报告逐字节副本及摘要见[历史清单](uat-evidence/integration-closeout-02/history-manifest.json)。

### REVIEW-INTEGRATION-BATCH-01（2026-11-04，综合回归进行中）

五项稳定完整来源（打印、核心工作区、财务、运维、历史）与起点均已完整包含于673ae3724b5db8d69018acbcea3e26c904c3fea3。逐源固定SHA、精确三CI、冲突处理与新0103财务/历史汇合迁移见[专属综合报告](uat-evidence/review-integration-batch-20261104/README.md)。保留已有预检、备份、迁移及历史证据；不取移动HEAD，不把开发者自查当独立复审。

本地阶段：财务合入后端1249项1189通过/60跳过；全来源Vitest720、字体规范1、构建通过。附件PG42项与新财务PG13项均通过；后者实际填充10张新财务表，94表1027行与4个私有文件恢复一致，序列与凭证摘要一致。财务Chrome两组各2/2。历史Chrome新审核执行首轮受外部字体网络拒绝导致失败；沙箱外重开原脚本通过，保存真实合成DB和XLSX，不声称正式资金/库存交接已连接。

ISS-105/108改为FIXED_PENDING_REVIEW，其余议题不自行关闭。当前124项：FPR86、NEEDS14、BLOCKED14、CLOSED10、OPEN0。最终全量Backend/真实PG17、跨包契约/历史原子性/加密归档专项和最终精确SHA三CI继续执行。目标环境外部条件、正式历史导入与正式RBAC仍未授权；打印完整成品/分页由用户明确延期，不扩大到ISS-037主体。

最新综合实测：后端代码1f189c3f74fda2908620dd3860230d860f1cbb43的SQLite全量1312项1251通过/61跳过/0失败，PG17.11全量1312项1282通过/30跳过/0失败；99表1081行128迁移4文件、历史/财务新表/序列/凭证恢复一致，真实恢复HTTP4/4，额外8项备份命令专项8/8，源不变且临时集群清理完成。候选CI41829100528 Backend/PG成功、Frontend270项中268通过/2失败（ISS039快照子进程）。03b524db7392ab989c699e31586484fd33a95fcb最小修复有界缓冲/诊断，Node179/179及Chrome2/2；7a896d0f824a361287cf981c377b07731c45f879修证据根目录，财务Chrome4/4。原全部业务/全库/权限断言保留，产品代码tree与全量已验1f完全一致；最终精确SHA三CI以交付回执核实，不提前登记通过。

### PRELAUNCH-CONSOLIDATION-CLOSEOUT（2026-11-04）

沿用 `codex/r1-prelaunch-consolidation-20261104`，在规则提交 `147de7400c87d4790ddfcd448fd0b808b9374ab9` 上，保留 BATCH-02 两条 0096 与 0097 汇合迁移及 ISS-121 初版/FIX-01；备份命令仅移植来源 `0692f4db292bd6fdeea1997562fb79c662f03ae7` 相对 `9250b066` 的增量。来源的自动 CI [#41772634041](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41772634041) Backend 和 PostgreSQL 成功、Frontend 因报表测试失败，后端 CI 中隔离备份专项按条件跳过，不能冒充已执行。本机单独执行真实隔离 PG17 命令专项与锁定依赖回归；报表测试对实际响应同步，保留原 CSV 内容断言及确定性竞态用例。最终同一 SHA 的 CI、测试和文件证据以本轮专属报告为准，不能预写通过。

打印工作包当前明确尚未完成；用户已操作界面生成合成草稿 PDF，但发现近乎空白的第二页，原因及正式单据完整矩阵仍待核验。不把其移动中或阶段报告 SHA 当作稳定最终成果。历史预检不授权正式导入；ISS-018 生产部署验收、ISS-037 打印成品及其他启用门槛保持[分别追踪](uat-evidence/r1-prelaunch-consolidation-20261104/READINESS-GATES.md)。未关闭 Issue、合并 master、部署或启用正式 RBAC。

### R1-PRELAUNCH-CONSOLIDATION-01 第一部分（2026-11-04）

独立集成起点 `d5abc64750d00c89d685bf12c0f8f67d4ba10a97`；完整移植历史只读预检初版与 FIX-01 至 `951adda34b5c60b303725702514cdacac17cc58d`，以及隔离备份演练六项提交至 `9250b066cbd28fd09bd2b1cc1f057604de1f76d9`。保留 BATCH-02 两条 0096 和 0097；新库 SQLite 迁移至 0097 成功。锁定 CPython 3.12.16 环境定向 90 项、4 项跳过，system check、迁移一致性检查通过。备份 PG17 既有成功记录仅限独立合成演练；本次未重新运行真实 PG 备份命令。预检 partial 误报定向修复按用户提供的 ChatGPT 复审结论通过，不等于 ISS-121 整体关闭。

第二部分须等待已完成并推送的 `R1-ISS018-RESTORE-COMMAND-ACCEPTANCE-03` 和 `R1-ISS037-PRINT-OUTPUT-ACCEPTANCE-01`，不猜测其 SHA；其后再完成最终综合回归和同一最终 SHA 的三项 CI。[门槛及第一部分核验](uat-evidence/r1-prelaunch-consolidation-20261104/README.md)。本部分未部署、未启用正式 RBAC、未导入真实历史数据或关闭议题。

## R1-RULE-GAP-BATCH-02 集成核验（2026-11-03）

以 `a55469c1b07e4f13037c6644c69d8a35ef0496a0` 为基线，独立集成卖方/模板冻结、银行疑似重复核实和采购预留 PostgreSQL 竞争证据，未覆盖旧阶段记录。两项独立 0096 迁移通过新合并迁移汇合，迁移测试恢复全部叶节点；有审计历史时仍拒绝逆向删除。隔离 SQLite 全量 1148 项、42 跳过，Node 177 项及前端构建通过；跳过的 PostgreSQL 场景不以 SQLite 替代。专项 PostgreSQL 17 及 Chrome 证据分别见三个报告。相同精确集成 SHA 的 Backend、PostgreSQL、Frontend CI 须待推送后核实，不预写成功。ISS-037/105 不整体关闭，打印最终文件、历史原件归属、部署权限及独立审查仍待完成；不部署、不启用正式 RBAC。

## R1-FIRST-BATCH-BUSINESS-AUDIT-01 / R1-RULE-GAP-FIX-BATCH-01（2026-11-03）

从固定源码 `8d3ca5faa16fb74de95dbc716f5556a5d51bbe79` 建立三个独立补修工作树及集成分支 `codex/r1-rule-gap-fix-integration-20261103`，不使用或清理master。上一轮三份已推送审查的精确远端SHA已重新fetch核对，并完整纳入集成历史：ISS-105 `1cad93d0cb0297c33f764f6cb68d5c610512d9e4`、ISS-037 `c88a121298465fcb04e11f9b65ef9ad251eadf3f`、ISS-039 `2d5164287672d9a57a6496761c3ea0d026088072`。各报告与原始日志索引见[本轮集成验收](uat-evidence/r1-rule-gap-fix-batch-20261103/README.md)。旧审查的Python3.14/Django6.0.6结果仅作历史，本轮使用真实CPython3.12.16及逐项匹配全部16个pin的锁定运行环境；前端由npm ci恢复锁定依赖，没有依赖升级。

本轮实施范围严格为：独立CNY银行手续费的结汇关联改为可选，保留来源/凭证/父事件验证和一次统计；历史未知买方在普通保存、普通修订及订单触发修订时保留未知，首次新报价明确预填与快照只读/正式导出关键字段校验不变；公共费用新提交只接受amount，历史quantity按原法读取，主动确认并预览转换、取消不写、零基数正费用拒绝，保留采购修改权限跨销售归属与审计/库存预留事务保护。不新增迁移，不自动重写历史，不生成额外资金/库存单据。

当前已核实的原有实现不再列为旧业务阻断：ISS-037已有客户六项/供应商五项快照；ISS-039专用成本分配不要求逐SO授权。三个议题均不整体关闭。ISS-105的内部转账、银行重复识别、待分类、现金银行边界、启用基准/账户核对、凭证绑定审计仍待后续实施；ISS-037卖方及模板冻结、完整双方信息、历史来源可信度、正式主体版本/审批分离仍保留。ISS-108/121的原D01–D08与本轮确认原则不重新列作待决；具体启用日、真实余额和更正凭证尚需外部真实证据，不推测、不配置。本轮不进入标签页开发、正式RBAC、部署或master合并。

每项先在独立分支定向验收并以 `[skip ci]` 推送，来源为A `321cb77d0179888a4788408d32c77d789504fbdd`、B `1a9666010c370dda08e2719e2c70caf6ee6c1b11`、C `aadd2ff3a7a15bc2a6601238ac6cea58d921c741`。逐项cherry-pick无冲突；模型/序列化/共享测试没有覆盖式丢失。集成本地Backend1114项（33跳过）、Node177项、Vitest69文件681项、单独typography1项、生产构建和两组真实Chrome5项通过；Django/迁移/diff检查通过，原有大chunk警告保留。取证脚本Unicode及错误证据根目录传播造成的先行失败、修正与成功复跑均保留，不改业务断言。最终集成提交不带跳过标记，按同一精确SHA核实Backend、Backend PostgreSQL、Frontend；本报告写入时CI待推送，不预写SUCCESS。Chrome桌面/390px、真实HTTP、原始日志与最终CI结果由集成验收报告和最终交付提供。台账124项：OPEN1、BLOCKED16、NEEDS_VERIFICATION17、FIXED_PENDING_REVIEW80、CLOSED10，新增0/关闭0。历史阶段记录原样保留，完成后停止等待独立复审。

## R1-POSTGRES-AUTH-CONTRACT-FIX-02（2026-11-02）

在 `codex/r1-postgres-integration-validation-20261102` 上修复唯一 PostgreSQL CI 回归断言，代码 SHA `7ab9913e03f1bde341158237e51aeebf77a86abc`。测试只对 `historical_analysis.cls` 设置 `SessionAuthenticationWithChallenge`；匿名请求要求 401，认证用户无订单分析权限继续要求 403。生产认证、业务逻辑、迁移与数据均未改。

本地 CPython 3.14.5 + 隔离 SQLite：历史订单 9/9，全量 Backend 1098 项、33 跳过、0 失败；Django check、迁移检查、diff check 通过。本机无 PostgreSQL 服务。GitHub run [#41432846693](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41432846693) 精确绑定代码 SHA：Backend SUCCESS（1098、30 跳过）、Backend PostgreSQL 17 SUCCESS（1098、21 跳过，目标认证测试 ok）、Frontend SUCCESS（unit/Node/Vitest/隔离 Playwright/build 全通过）。完整 job 日志 ZIP 与 SQLite 原始日志见[FIX-02 验收记录](uat-evidence/r1-postgres-integration-validation-20261102/README.md)。前一 run #41424016735 的旧 SHA 失败不被抹除，作为已修复前的历史证据保留。无 Issue 状态改变；ISS-006、ISS-018、ISS-052 等既有验收缺口保持。未创建 PR、未合并 master、未部署、未启用正式 RBAC、未连接业务数据库。

## R1-POSTGRES-INTEGRATION-VALIDATION-01（2026-11-02）

从固定基线 `9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2` 建立独立分支 `codex/r1-postgres-integration-validation-20261102`，按来源 SHA 精确整合四项已审查测试变更：Supplier 夹具 `644f6a908a755f9d2293dba74c609471f86fcd5d`、ISS-018 边界 `0c326ba7e7bfb3c4022f57e9f5680ce1cffbfc93`、CSV 审计 TRUNCATE `1aba37600cadbdf88aebe787d742310bac1a333f`、RBAC 认证契约 `3a79e1a68988aa2099159d9f393f22766280f68f`。B/C 仅应用指定提交补丁，未合并其父分支历史；A/D 修改全部保留。对重叠的 `test_order_quantity_adjustments.py` 逐项确认 Supplier 两字符编码与匿名 401 / 已认证未授权 403 断言同时存在。

本地检查使用隔离内存 SQLite、临时 MEDIA_ROOT、CPython 3.14.5（本机无 Python 3.12 与 PostgreSQL 服务）：Django check、迁移检查、后端全量 1098 项（33 跳过）、Supplier 67 项、ISS-018 22 项（3 个 Windows 平台条件跳过）、RBAC/认证组 130 项均通过；CSV PostgreSQL 专项 2 项在 SQLite 下正确跳过。前端依赖按锁文件 `npm ci` 安装，Node 171 项、Supplier SKU Vitest 9 项和生产构建通过。测试统计、命令和环境边界见[集成验收报告](uat-evidence/r1-postgres-integration-validation-20261102/README.md)。

集成前后确认 `backend/crm/test_runner.py`、`backend/crm/postgres_test_cleanup.py` 和 `.github/workflows/ci.yml` 与基线一致；未修改生产业务逻辑、数据库迁移、认证/审计保护。GitHub CI 结果以本节后续补充的精确集成 SHA 运行链接和原始日志为准。ISS-006、ISS-018、ISS-052 等现有未关闭状态与部署/独立复审缺口保留；未创建 PR、未合并 master、未部署、未启用正式 RBAC、未连接实际业务数据库。

GitHub Actions run [#41424016735](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41424016735) 已对集成代码提交 `e6b40cadb04c54ef3376307daba19f78276a913d` 完成验收：Backend SUCCESS（全量1098项），Frontend SUCCESS（Node 171/171、Node-only 1/1、Vitest 69文件、Playwright主套件216项与隔离套件25项、build成功），Backend PostgreSQL 17 FAILURE（1098项、21跳过、1失败）。唯一失败为未合入本次认证来源文件清单的 `test_historical_orders.py:205` 仍对匿名请求断言403，实际401；该差异属于历史测试预期未随认证契约更新，不是数据库/runner故障或生产业务缺陷。已认证无权限403断言位于同一失败用例后半段，因首断言失败未执行；其他专用401/403权限契约测试通过。没有在失败后继续修改或重跑，暂停进一步集成等待独立审查。完整日志和建议的最小补修见[报告](uat-evidence/r1-postgres-integration-validation-20261102/README.md)。ISS-006/018/052 状态及部署验收缺口保持不变。

## R1-ISS052-AUDIT-HARDENING-02 审计防篡改集成（2026-10-31）

基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c`，新分支 `codex/r1-iss052-audit-hardening-20261031`。按来源历史集成 `a6c5b56a00326234681399a3405efa2117198f76`（d08 的父依赖）、用户指定 d08 `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b`、HTTP 413 `8cff96af9f1f2e09dcbc0a29f361017ee23ffb75`、审计 `f2b7fd6487459be69be687ccfeab09e7947df995`。实现提交 `ab9ce886094a065766a24b35d9b82c7a7c0fd067`：冲突处理保留有界流式读取、超限 413、正式导入审计和前端重试上下文；新增迁移 0094，在 Batch/RowAudit/PreviewAudit 三张表增加 PostgreSQL TRUNCATE 防护，并在存在任一审计行时拒绝回退审计保护迁移。既有 0091 的 Batch/RowAudit UPDATE/DELETE 与 0093 的 PreviewAudit UPDATE/DELETE 触发器均保留。

验证使用 `DATABASE_URL=sqlite:///:memory:` 的 Django 隔离测试数据库；全量 1041 项、1021 通过、20 跳过、0 失败；CSV/413/审计迁移定向 36 项、35 通过、1 项 PostgreSQL 专项跳过；Django check、`makemigrations --check --dry-run crm`、前端 Vitest 1/1、Node 171/171、生产构建及 `git diff --check` 通过。0094 空数据回退/前向恢复成功；存在预览、批次、行数据时回退被拒且三类记录保留。前端包仍有 >500 kB 警告。

PostgreSQL 原始 SQL UPDATE/DELETE/TRUNCATE 测试已新增，但本机本轮仅配置 SQLite，故数据库触发器运行时验收明确为 `POSTGRESQL_VERIFICATION_PENDING`；不得将 SQLite 结果作为 PostgreSQL 通过证据。真实 Chrome 413 截图及原始浏览器/HTTP日志沿用 8cff 来源证据（本轮未重新生成）；集成后的三入口 HTTP 413、临时文件为空和无业务写入由本地 LiveServer 回归核验。ISS-052 保持 `FIXED_PENDING_REVIEW`，真实 PostgreSQL、真实业务库、正式 RBAC 和生产验收仍未执行。完整提交谱系、冲突说明、测试命令和日志见[本轮报告](uat-evidence/r1-iss052-audit-hardening-20261031/README.md)与[测试日志](uat-evidence/r1-iss052-audit-hardening-20261031/logs/test-results.md)。未连接真实业务数据库、未启用正式 RBAC、未触发 CI、未创建 PR、未合并 master、未部署、未关闭 Issue；交付后等待独立审查。

## R1-ISS-052 超限 CSV HTTP 413 回归（2026-10-31）

基于 `codex/r1-iss052-csv-limit-bd324-20261030` 的 `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b` 创建独立 worktree / `codex/r1-iss052-http-413-bd324-20261031`。将 CSV 超限上传处理器设为不重置连接，使 Django 以有界块耗尽未读请求体后返回明确 HTTP 413。真实 HTTP 覆盖 preview、execute、legacy 三个入口；均返回 413、无导入副作用且临时上传目录为空。真实隔离 Chrome 对页面预览入口上传超限文件收到 413，无 request failure。后端相关回归 117/117、前端单元测试 171/171、Chrome 1/1、构建及 diff check 通过。构建仍有主 JS 包超过 500 kB 警告；生产代理限制/超时、PostgreSQL 和部署环境仍待验证。完整日志及截图见 [R1-ISS-052 HTTP 413 证据](uat-evidence/r1-iss052-http-413-bd324-20261031/README.md)。未修改 Issue 台账、未运行 CI、未合并 master、未部署。

## R1-ISS-052-HTTP-413 真实浏览器超限上传验收（2026-10-31）

基于 `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b` 创建独立 worktree。先在隔离 Django 上传处理器测试中复现：64 KiB 上限下，旧处理器越限前已将 65,319 字节转交后续处理器，且临时文件处理器已打开文件。最小修复改为 CSV 专用有界内存缓冲，由 `StopFutureHandlers` 阻止 Django 内建内存/临时处理器初始化；超限立即丢弃已缓冲前缀并停止 multipart 解析，保留真实 HTTP 413 响应。未改变导入业务核心、模型或迁移。

内置 Chromium 浏览器通过真实 Axios multipart 请求访问本地 Vite 代理和隔离 Django HTTP 服务：预览、兼容预览、正式导入均对 10 MiB+35 B 与 20 MiB+1 B 文件返回 JSON 413，浏览器 `network_error=null`；Django 服务访问日志对应记录三路由 413。64 B 正常客户 CSV 的预览及正式导入均返回 200，隔离 DB 新增一条测试客户。超限正式执行只有空 SHA、零行的失败批次；业务表无对应新增。上传临时目录为空；逐入口定向测试验证零字节转发、内建内存 handler 未激活、临时 handler 无文件、解析未执行和业务数据未写。

定向/跨模块 Django 测试 86 项通过；Django check、迁移一致性、Vitest 4 项和生产构建通过。Node 单测 171 项中 169 项通过、2 项因隔离浏览器运行器依赖 `@playwright/test/cli.js` 在共享只读依赖树缺失而失败；共享 Vite 实际为 8.2.0、锁文件为 8.3.5，构建在已安装版本通过。准确浏览器结果、隔离 DB 快照、日志与限制见[ISS-052 HTTP 413 验收报告](uat-evidence/r1-iss052-http-413-20261031/README.md)。ISS-052 保持 `FIXED_PENDING_REVIEW`；真实员工身份与正式审计验收继续待办。本轮未触发 CI、未连接生产、未部署、未关闭 Issue。

## R1-INTEGRATION-036-002-003-052-058 五项任务集成（2026-10-27）

固定基线 `46353a5436637832f5adadb7bdef6b45cdeada23`，创建独立工作树和 `codex/integration-036-002-003-052-058`。集成前核对五个远端来源分支 HEAD 与指定 SHA 一致：ISS-036 `b64c54b07908d4bb462c64f120c351d148e06f6f`、ISS-002 `4e4ca504ee398da85fe23cc53d534c6008807e5c`、ISS-003 `2111d193ef3a69db05c23e27813cfbf26d9034d7`、ISS-052 `93736e0773ca2136d4070a604e62324cf832dc6f`、ISS-058 `742692a6e4887e4b8352736e69a52b1ebe8d066f`。保留五项代码/测试/报告/依赖；PROJECT_ISSUES 的 ISS-002 冲突逐条合并，PROJECT_PHASES 保留各历史记录并追加本轮日志。ISS-052 七个 JPEG 原图仅由 `.png` 重命名 `.jpg`，签名检查确认未重编码。

后端在 Python 3.12.14 干净虚拟环境中安装 `backend/requirements.txt`，隔离 SQLite 下 Django check、`makemigrations --check --dry-run` 和全量 `manage.py test` 通过；测试 989 项、18 项跳过。前端 `npm ci`、两项 audit、Node 156、Vitest 661、交易单位 4 和生产构建通过；detail drawer typography 测试失败 1 项，Playwright 164/184 通过，20 项失败。ISS-058 集成构建主 JS 为 1,126,035 bytes / gzip 393,552 bytes，对原始报告变化为 -183 / +75 bytes；Vite 的 >500 kB 警告仍在，不声称真实用户体验改善。完整测试命令、Playwright 失败明细、性能差异与验收缺口见[本轮集成报告](uat-evidence/integration-036-002-003-052-058/README.md)。

推送提交 `4a83ec1455cbe4e927ae39252477fa095cf329ca` 触发 [GitHub Actions CI #40535678568](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40535678568)，run 的 head SHA 精确匹配。backend、backend-postgres、frontend 三个 job 全部 failure，约 3 秒结束，GitHub 返回 `runner_id=0`、`steps=[]`，没有运行日志。各 check-run 的原始 failure annotation 均为：`The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings`；故本轮 CI 状态为 `BLOCKED`（GitHub 报告账户近期付款失败或消费限额需增加，具体子原因未区分），需账户所有者手动核查 `Billing & plans` 并重跑。文档更新提交 `7ff7fdb51fba99796a6823817774d1ddfdb2eeaa` 的 [Actions CI #40536898954](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40536898954) 再次确认三项 job 均在 runner 分配前失败，三个 job 的 check-run 注释相同；后续最终文档/空白清理提交的精确 SHA / run 在交付时核对。ISS-036 保持 `FIXED_PENDING_REVIEW`，ISS-002 `NEEDS_VERIFICATION`，ISS-003 `BLOCKED`，ISS-052 `NEEDS_VERIFICATION`，ISS-058 `P3 / NEEDS_VERIFICATION`。Pillow `11.3.0` 风险未解决，Python 依赖无完整 lock；ISS-003 的真实员工/生产权限验收、ISS-052 的开发身份审计（`AUDIT_LOG_ENABLED=false`、`OperationLog=0`）仍缺失。GitHub API 已核验七张截图均以 `.jpg` 命名且远端字节签名为 JPEG；本机 Chrome 会话打开私有仓库网页返回 404，网页 UI 预览尚未目视复核。无新增迁移；未合并 master、未关闭 Issue、未部署、未启用正式 RBAC，完成核验后等待独立审查。

## ISS-003 员工权限与数据范围隔离验收（2026-10-27）

基于统一基线 `46353a5436637832f5adadb7bdef6b45cdeada23` 创建独立 Worktree 和分支 `codex/verify-iss003-employee-permissions`。本轮先核对现有 `permissions.py`、`sales_scope.py`、采购/财务范围服务、API ViewSet/Serializer 及前端路由守卫；没有修改 `DEVELOPMENT_SUPERADMIN`、`RBAC_ENFORCEMENT`、角色模板或任何业务代码。

在隔离 SQLite 与合成账号下，以 `DEBUG=false`、`DEVELOPMENT_SUPERADMIN=false`、`RBAC_ENFORCEMENT=true` 执行 `test_functional_rbac`、`test_sales_data_scope`、`test_procurement_data_scope`、`test_finance_data_scope`、`test_reporting`，共 `131` 项通过。覆盖 `self`、`department`、`department_tree`、`all`，缺模块权限、匿名拒绝、列表、详情、搜索、报价导出、报表 CSV、跨模块关联、财务流水、采购共享成本分配和字段脱敏。Django system check、`makemigrations --check --dry-run` 及全新 SQLite 连续迁移至 `0089` 通过。

本轮没有发现能由当前代码与测试明确证明、且可安全最小修复的权限缺陷；采购共享路径仍只开放必要识别字段，不扩大客户、报价、利润或资金信息。并行 Django 全量测试在克隆 SQLite 数据库阶段因托管 Worktree 路径无法打开数据库而未进入断言，不记为全量 PASS；前端依赖缺失，真实员工 Chrome 桌面/窄屏 UI 也未冒充通过。完整矩阵、拒绝/通过路径、命令和边界见 [`ISS-003 验收报告`](uat-evidence/iss-003-employee-permissions/README.md)。

ISS-003 仍保持 `BLOCKED`：正式员工账号、真实组织树、生产 PostgreSQL、部署层会话/文件 URL 和真实 Chrome UI 尚未验证；不使用开发超级管理员或 SQLite 结果替代这些证据。本轮未主动运行或查询 GitHub CI，最终提交使用 `[skip ci]`；未连接生产、未合并 `master`、未关闭 Issue，交付后等待独立审查。

## ISS-021 正式销售订单数量变更集成（2026-10-26）

从统一基线 `b3559f3bf83b967d06166bd409b00fc92e4e5902` 创建独立 worktree / `codex/next-iss-021-integration`，比较旧开发与审查分支后只迁移所需差异。新增迁移 0085 接续 0084，不复制旧分支 0078、不改写已发布迁移；保留 ISS-037 主体快照和 ISS-039 共享采购规则。正式 SO 原编号/行保留，支持数量增减、已发货下限、已收款保护、版本冲突、幂等、历史与人工采购处理提示；不新增复杂审批。

SQLite 全量 904 项（跳过 13）、定向 38 项、Node 151 项、Vitest 650 项、最终数量组件 2 项及构建通过。隔离真实 API、桌面/390×844 内置浏览器验证增减、取消、刷新、发货下限和已收款拒绝；Chrome Use 连接与其他对话冲突后，用户明确授权使用内置浏览器。采购/归属/收货/发货/库存流水/资金事实逐字段前后哈希相同，原主体快照不变。新库及 0084→0085 升级/空表回滚重放验证完成；本地 PostgreSQL 与独立视觉审查未完成，不冒充通过。证据和差异说明见 [ISS-021 交付索引](uat-evidence/iss-021-integration/README.md)。

ISS-021 更新为 `FIXED_PENDING_REVIEW`。未改其他任务分支、未部署、未合并 master、未关闭 Issue，交付后等待统一独立代码/业务/迁移/权限/视觉审查。

远端 CI run `40257290673` 三个 job 均在启动步骤前失败，GitHub 注释明确为账户付款/消费限额问题，原始证据已归档。CI/PostgreSQL 验收保留 BLOCKED，需仓库所有者处理后重跑最终 SHA；没有改计费设置或工作流，不以本地通过冒充 CI 成功。

## ISS-029 报价收件资料版本保存（2026-10-25 测试，2026-10-26 交付）

实现与原始证据 SHA：`fbdb9c58987d5040c97923784ce2cf622dfe8755`。GitHub CI `40254982268` 三任务均未启动；backend check-run 注解明确账号付款/额度问题，不能宣称 CI 或 PostgreSQL 通过。此后仅补充交付文档，等待账号恢复后重跑及独立审查。

从统一基线 `b3559f3bf83b967d06166bd409b00fc92e4e5902` 创建独立 worktree 和 `codex/iss-029-quote-recipient-snapshot`。完整读取用户桌面 2026-10-24 规则包的 ISS-029 原文，核对 ISS-037、ISS-020 及既有创建、草稿、正式状态、修订、PI 和 Excel。仅修复已确认的显式空邮箱被预填替代、异步联系人预填覆盖手工输入或较新客户资料两类缺口。继续复用现有 Quote 四字段与修订链，无新模型、迁移、客户主档回写或生命周期更改。

报价/快照定向 72 项、Django 全量 881 项（13 项跳过）、前端 Node 151 项、有效 Vitest 652 项（65 文件）、生产构建及真实 Chrome 连接隔离 Django 的 A/B 完整场景通过。已保存真实 HTTP 响应、1440px/700px 截图、三份实际下载 XLSX 和数据库单元格对账；主联系人/客户地址修改及未保存编辑均未改变旧版资料。模型和已执行迁移检查通过。证据及具体命令见 [ISS-029 验收](uat-evidence/iss-029-quote-recipient-snapshot/README.md)。

ISS-029 从 `NEEDS_VERIFICATION` 更新为 `FIXED_PENDING_REVIEW`；无新增 ID、无关闭事项。按唯一表格 ID 最新状态核对共 123 项：OPEN=5、BLOCKED=22、NEEDS_VERIFICATION=24、FIXED_PENDING_REVIEW=62、CLOSED=10。其他任务状态、原有工作树及分支保持。GitHub CI 需按最终提交核对；本地 SQLite 通过不代表 PostgreSQL/生产验收，等待独立代码、权限和视觉审查，不合并 master。

最新只读审查：R1-READINESS-01（2026-10-19），基线199a21e0f407ba9ad772a5dec86e0b30dbd0c9b5。全系统试用准备审查完成；R1-FIN-P3-B按授权记录阶段性验收通过，但不等同生产就绪。ISS-105 OPEN、ISS-108/121 BLOCKED；真实员工试用门槛为ISS-003、ISS-018、ISS-055。未修改业务代码，不启动正式员工UAT、RBAC或部署。详见[R1-READINESS-01审查报告](R1-READINESS-01-全系统试用准备与业务阻断问题审查.md)。

上一轮：2026-10-18至19 R1-FIN-P2-A，基线1b2ca0eb5b1947dd53f5ab995828dd33f514e0d4，前置三项CI SUCCESS。用户已正式批准D01–D08，完成最小人民币银行净额事实/来源分配、增量两表迁移、人工确认/幂等/事务/数据范围及退款、作废、替代保护。真实隔离HTTP与旧数据对比、迁移保护、PG实际并发和全量回归见[P2-A验收](R1-FIN-P2-A-人民币资金事实与结汇后端验收.md)。ISS-105保持OPEN；新增ISS-108 BLOCKED待更正/来源解除等细则，新增ISS-109待复审登记全量CI跨日旧测试修正，其他既有状态不变。无前端产品UI变更，无报表来源/历史金额/精度/核销/履约/利润/库存算法变更；不设启用日、不配置真实账户或启用正式RBAC。精确HEAD三项CI后停止，等待ChatGPT独立复审，不自动进入P2-B、员工UAT或部署。

最新实施：2026-10-18 R1-FIN-P1，基线ad3a08ebd47ad4b94ffe8f6ebfed5f083b9ac57e。现有混合币种统计统一澄清为账面人民币折算参考，页面/API/CSV一致，包含原币CNY既有流水；不代表银行实际到账或已结汇。相同隔离合成数据前后金额及CRM记录哈希一致；未改模型、迁移、金额、核销、退款、利润、成本或开发权限。ISS-105保持OPEN；当时新增ISS-107 BLOCKED登记模型元数据与兼容遗留，2026-10-24跟进已完成最小元数据修复并更新为FIXED_PENDING_REVIEW。见[P1验收](R1-FIN-P1-现有财务统计口径澄清验收.md)。推送并核实精确HEAD三项CI后停止，等待ChatGPT独立代码和视觉复审；不自动进入P2、正式RBAC、员工UAT或部署。

最新准备：2026-10-18 R1-FIN-P0。基线da39ea3aa986df9faa12e79b1da3adece03260b7三项CI经重新核实SUCCESS；已确认原币辅助/人民币实际资金/折算参考边界。仅完成源码审查、两类增量记录方案、精度与历史风险、分阶段任务及D01–D08待决清单，见[准备报告](R1-FIN-P0-财务统计口径确认及实施准备.md)。无核心代码、迁移、数据库或历史金额变更；ISS-105保持OPEN，001/106仍待复审，其他状态不变。提交文档后停止等待ChatGPT独立审查，不自动实施后续P1/P2/P3、正式RBAC、员工UAT或部署。

最新补修：2026-10-18 R1-A-FUP-02-FIX-01，基线7faafcf142827ee4e94aa1aaa8d04e68e77e3726。仅恢复报价/订单共享表头边界，并补no_plans/review只读核对提示和未知金额显示。ISS-001保持FIXED_PENDING_REVIEW；审查新发现的文案回归登记ISS-106待复审，其他Issue状态不变。详见[本轮验收](R1-A-FUP-02-FIX-01-独立审查补修验收.md)。不修改财务统计口径、历史计划或余额；完成后停止等待独立复审。

最新实施：2026-10-18 R1-A-FUP-02。用户确认FUP-01已独立复审通过，方案A已正式批准；修复ISS-001 completed欠款待办、回款派生状态及权限显示，完成履约规则/财务口径不变。真实隔离UI及数据库前后证据见[FUP-02验收](R1-A-FUP-02-订单履约财务分离验收.md)。仅ISS-001转FIXED_PENDING_REVIEW，其他Issue状态不变；最终HEAD三项CI后停止等待ChatGPT独立审查，不进入下一阶段。

最新只读审查：2026-10-18 R1-FIN-AUDIT-01，仅财务统计血缘、银行结汇兼容与精度实施方案；新增ISS-105 OPEN，既有Issue状态不变。见[审查报告](R1-FIN-AUDIT-01-财务统计与结汇兼容性审查.md)。未修改业务代码/数据库，未实施FUP-02；提交后停止等待独立复审，不进入RBAC、员工UAT或部署。

最新补修：2026-10-18 R1-A-FUP-01，基线 f9a9cfb076f581ecb1e2f758b2284fe4dcf525fd。财务表单真实快照、结果不明确保护及证据更正；ISS-104新增待复审，ISS-004保持待复审，ISS-001保持BLOCKED。见[FUP-01验收](R1-A-FUP-01-财务重试安全验收.md)。完成后等待独立审查，不执行FUP-02或R1-B。

最新授权：2026-10-18 R1-A。用户转述R0-F1至R0-F9经独立代码、业务证据及截图复审允许有条件封版；本轮只核实ISS-001/004/005/006/054，ISS-001业务规则不改。R1-A实施与证据见[R1-A报告](R1-A-核心业务历史Issue核实与修复.md)。本轮交付后等待ChatGPT独立审查，未进入R1-B、正式RBAC、员工UAT或生产部署。下文前序阶段记录按历史保留，不扩大验收范围。

当前核对基线：R0-F9从master / b916fab613806a9fd00636cc87496803557d45a8（2026-10-16）开始。F8C代码、自动与已覆盖操作经用户转述独立复审通过，有条件封版；CI #38909906403三项SUCCESS。F9完成全站盘点、局部列表样式收尾及可审查原图基线；独立代码和图片尚待审，ISS-099/100待核实。交付后停止，不进入历史集中修复、正式RBAC、员工UAT或生产部署。

## 用户批准的最新开发路线

用户于 2026-10-13 明确批准以下顺序：

1. **整体前端 UI/UX 收尾**。按 R0-F1 财务、R0-F2 概览/报表、R0-F3 库存、R0-F4 供应商、R0-F5 联系人与客户跟进等 Part 继续；全部前端完成前不得进入集中历史 Issue 修复。

2. **集中核实和修复历史 Issue**。须等待当前 Part 的 ChatGPT 独立审查，并在后续 Part 按台账处理；保留所有旧 Issue ID。

3. **全系统综合审查**。

4. **修复综合审查发现的问题**。

5. **正式内测**。只有用户另行明确授权后才进入；不启用 RBAC 或配置正式测试角色，除非该授权明确涵盖。

该路线授权在当前 UI/UX 路线内按 Part 顺序继续，不需要每个模块重复开工确认；用户明确规定的等待独立审查仍是阶段门槛。它不授权生产部署或改变重大业务规则。

## 当前项目状态

| 阶段 | 当前状态 | 依据与边界 |
|---|---|---|
| R0-A 至 R0-D2 | 各自范围已记录完成 | 对应安全、数据完整性、导入、导航和未保存修改记录；完成只覆盖各文档列出的检查。 |
| R0-D4 | 有条件完成，等待完整阶段复审/封版决定 | 财务、采购及跨模块 API 权限已增量实施并有矩阵/回归；历史财务归属、跨权限成本委托、部署文件 ACL 仍见 [`PROJECT_ISSUES.md`](PROJECT_ISSUES.md)。不要因三项 CI 成功而关闭这些业务/部署事项。 |
| R0-E1 | **PARTIAL PASS** | 隔离 SQLite 真实 UI 主链和对应自动测试通过；订单欠款完成后催收待办消失为已复现 P1。文件、导出内容、受限角色和多个边界流程仍未充分验收。精确结果见 [R0-E1 报告](R0-E1-综合业务回归与内测准备.md)。 |
| R0-F1 UI/UX | **财务代码/已覆盖交互有条件封版；截图视觉证据待补** | 首轮范围为财务流水、应收/应付计划、财务概览；已更新查询状态、财务指标信息结构、交互反馈并添加回归。全站路由矩阵见 [R0-F1 覆盖盘点](R0-F1-前端UX覆盖盘点.md)。不代表全站 UX 已完成。 |
| R0-F2 UI/UX | 独立代码/自动回归 PASS，有条件封版；独立视觉 BLOCKED | 经营概览与报表中心及关联组件；见 [R0-F2 验收](R0-F2-经营概览与报表中心验收.md)。统计范围缺口 ISS-062 保留，视觉续验 ISS-066 保留。 |
| R0-F3 UI/UX | 独立代码与已覆盖操作回归 PASS，有条件封版；独立视觉 BLOCKED | 最终 `ca486be` / CI #38507649163 三项 SUCCESS；ISS-068、069 记录通过范围，ISS-070 与旧库存业务事项保留。 |
| R0-F4 UI/UX | 代码及自动化/已覆盖交互 PASS，有条件封版；独立视觉 BLOCKED | 用户转述 ChatGPT 独立复审 PASS；最终 `8cb265e`；CI #38539359761 三项 SUCCESS。ISS-071、072 按限定代码/交互范围关闭；ISS-073 截图 BLOCKED、ISS-074 待核实。 |
| R0-F5 UI/UX | 独立代码与自动回归 PASS，有条件封版；独立视觉另待审 | 最终 `86650adc` / [CI #38605116907](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38605116907) 三项 SUCCESS。按用户本轮明确接受关闭 ISS-079；ISS-080、ISS-007 及其他历史未关闭项保留。 |
| R0-F6 UI/UX | 独立代码、自动化及已覆盖交互PASS，有条件封版；独立图片视觉待审 | 最终`0b721fcd` / [CI #38669003578](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38669003578)三项SUCCESS。ISS-081–083保留；参数1440截图纠正单独见ISS-084。 |
| R0-F7A UI/UX | 独立代码/已覆盖回归PASS，有条件封版；独立图片视觉待审 | 最终79841e3 / [CI #38697043429](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38697043429)三项SUCCESS。依据用户明确接受关闭ISS-088代码/回归范围。ISS-085、086已覆盖操作通过但图片待审；ISS-087待核实，历史问题保留。 |
| R0-F7B UI/UX | 独立代码/自动及已覆盖交互通过，有条件封版；独立图片视觉待审 | 最终a2cbdec / [CI #38752391875](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38752391875)三项SUCCESS；ISS-089–091记录通过范围，视觉复核事项保留；历史业务事项不自动关闭。 |
| R0-F8A UI/UX | 独立代码及自动回归PASS，有条件封版；独立图片视觉待审 | 最终82514b1 / [CI #38761364221](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38761364221)三项SUCCESS；ISS-092/093已覆盖代码及交互接受，图片及文件边界保留。见[R0-F8A验收](R0-F8A-产品证书与HS编码验收.md)及[全站覆盖清单](R0-F8A-全站前端UX覆盖清单.md)。最终SHA/精确CI结果绑定交付消息及对应commit checks。 |
| R0-F8B UI/UX | 代码、自动及已覆盖真实CSV接受，有条件封版；独立图片待审 | 最终10158f89b50ad477026f4ee2d4d4fd8177d5edcd / [CI #38878347385](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38878347385)三项SUCCESS；ISS-094仅独立视觉待复核，ISS-052保留。见[R0-F8B验收](R0-F8B-数据导入验收.md)。精确HEAD和CI绑定交付提交检查。 |
| R0-F8C UI/UX | 独立代码、自动与已覆盖操作通过，有条件封版；独立图片待审 | 组织/部门/岗位只读展示、角色草稿/保存保护/回读、矩阵滚动及访问状态恢复；ISS-095/096已覆盖代码/交互接受，独立图片待审；ISS-097仍待核实。见[R0-F8C验收](R0-F8C-组织权限与访问状态验收.md)；无正式员工账号或权限策略变更。 |
| R0-F9 UI/UX | 全站覆盖与证据基线已建立；等待独立代码与图片审查 | 27路由×3视口、表单/详情/异常原图及HTML索引；局部修正产品/SKU状态、报价客户列及订单筛选。ISS-098待复审，ISS-099/100待核实；历史100个ID持续追踪，无批量关闭。见[R0-F9最终审查](R0-F9-全站UIUX最终审查.md)。 |
| 内测 / 生产部署 | 未授权、未开始 | 保留开发超级管理员机制；正式 RBAC、真实员工角色、部署和生产数据迁移均不得从此文档推定已获授权。 |

## 指定阶段历史记录

只记录有来源支持的阶段信息。`UNKNOWN` 表示现有 Git、阶段报告和本次提供的历史对话无法确认；相关提交或下一阶段基线不自动等同阶段最终 SHA，某次 CI 成功也不自动证明最终 HEAD 通过。

| 阶段 | 阶段状态 | 最终 Commit SHA | CI Run / 结果 | 独立审查结论 | 主要遗留 Issue ID | 证据与说明 |
|---|---|---|---|---|---|---|
| R0-D3 | 实现与视觉证据存在；阶段最终状态 UNKNOWN | UNKNOWN（相关实现提交 `8ccdc07`；不是已确认的最终提交） | UNKNOWN | UNKNOWN | UNKNOWN（尚未建立一对一映射） | 仅找到截图证据提交 `b596c7e`、`9cc8ee5`；未找到阶段验收摘要及最终 SHA/CI 记录。 |
| R0-D4A | 功能实现和 UAT 证据存在；阶段最终状态 UNKNOWN | UNKNOWN（相关实现提交 `6736c67`；不是已确认的最终提交） | UNKNOWN | UNKNOWN | ISS-003（权限角色真实业务 UI 验收仍待补） | 找到功能 RBAC 与截图提交 `f5f82ff`、`fc5aa6e`；未找到可确认的阶段最终 SHA、CI Run 和独立结论。 |
| R0-D4B1 | 完成并封版（据用户历史陈述） | `3d5d290`（作为后续 B2-A 用户指定基线；未找到单独封版记录） | UNKNOWN | PASS（ChatGPT 独立审查，据用户历史陈述；审查记录未入 Git） | ISS-055 | 未找到可追溯 CI Run；客户越权 404 的英文文案由历史审查提出，当前列为 OPEN。 |
| R0-D4B2-A | 完成（据用户历史陈述） | `073d3a6` | CI #38208167344：SUCCESS（Backend、Backend PostgreSQL、Frontend；对应阶段 SHA 经 GitHub 核对） | PASS（ChatGPT 独立审查，据用户历史陈述） | ISS-038、ISS-053 | CI SUCCESS 不替代完整采购/财务业务验收；ISS-053 仍需当前显示复核。 |
| R0-D4B2-B | 完成（据用户历史陈述） | `7e5e565` | CI #38232779023：SUCCESS（Backend、Backend PostgreSQL、Frontend；对应阶段 SHA 经 GitHub 核对） | PASS（ChatGPT 独立审查，据用户历史陈述） | ISS-039、ISS-054 | 独立审查 PASS；ISS-054 的收货冲销提示仍按台账待复验。 |
| R0-D4B2-C | R0-D4 权限开发有条件完成（据用户历史陈述） | `81273c0` | CI #38289225525：SUCCESS（Backend、Backend PostgreSQL、Frontend；对应阶段 SHA 经 GitHub 核对） | R0-D4 整体有条件封版；C 单项独立结论 UNKNOWN | ISS-003、ISS-017、ISS-046、ISS-055 | 权限矩阵及本阶段 CI 不覆盖所有文件部署 ACL 风险；不扩大为无条件封版。 |
| R0-E1 | PARTIAL PASS（据用户历史陈述及验收报告） | `cdaa8f0` | CI #38356269083：SUCCESS（Backend、Backend PostgreSQL、Frontend；对应阶段 SHA 经 GitHub 核对） | PARTIAL PASS（ChatGPT 独立复审，据用户历史陈述） | ISS-001–008、ISS-019–029、ISS-052；继承项见问题台账 | CI SUCCESS 不替代未覆盖的业务、文件、导出、受限角色及边界流程验收；范围见 [E1 报告](R0-E1-综合业务回归与内测准备.md)。 |
| R0-F1 UI/UX（本轮） | 财务 Part 实现及代码验收完成，等待 ChatGPT 独立复审；截图归档和多尺寸视口验收 BLOCKED | `bf79ef8` 基线；实现/测试提交 `439b5b36e458bde63ba15eaa39bbe94ce742616a` | 本地：Node 121/121、Vitest 494/494、Node-only typography 1/1、财务/报表后端回归 76/76、销售范围后端回归 28/28、Vite build SUCCESS。最终实现提交 CI #38426397966：Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。此前 CI #38424190013 的 PostgreSQL 测试假失败由错误的字符串子串断言造成，已改为 Decimal 精确值检查并在本提交通过 | UNKNOWN（待独立审查） | ISS-001 等历史 Issue 全部保留；新增 ISS-057（待复审）、ISS-058（性能待核实） | 财务流水、应收/应付和概览已在隔离 SQLite 与 Codex 内置浏览器跑通。截图归档和多尺寸视口仍 BLOCKED，替代证据与场景明细见 [R0-F1 盘点](R0-F1-前端UX覆盖盘点.md)。 |
| R0-F4 UI/UX（独立复审记录） | 代码及自动化/已覆盖交互 PASS，有条件封版；截图独立视觉 BLOCKED | `8cb265e` | [CI #38539359761](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38539359761)：Backend、Backend PostgreSQL、Frontend 全部 SUCCESS | PASS（据用户转述 ChatGPT 独立代码/自动回归审查） | ISS-073、ISS-074、ISS-075；旧业务事项保留 | ISS-071、072 按已覆盖代码和交互范围关闭；截图缺口 ISS-073 继续独立跟踪。 |
| R0-F5 UI/UX（本轮） | 实现、自动回归、隔离 SQLite 与 Codex 内置浏览器操作记录完成；截图已归档，等独立复审 | 实现 `92e8c46d4ce01e18cd164e152d345c58433c9305`；台账 `0ec186b71f0395d52526b308e385b189a582ead6`；2026-10-15 截图补证提交另见 Git 历史 | [CI #38596225877](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38596225877)：Backend、Backend PostgreSQL、Frontend 全部 SUCCESS | UNKNOWN（待 ChatGPT 独立复审） | ISS-007、ISS-073–078 及历史未关闭项 | 13张截图解除R0-F5归档缺口；实际附件文件选择器及内容访问未完整验收，独立视觉仍不能由 Playwright/Codex 目视替代。详见 [R0-F5 验收](R0-F5-联系人与客户跟进验收.md)。 |

## 2026-10-24 ISS-017 私有附件专项

本轮在 `codex/iss-017-private-files` 独立 worktree 基于 `71ec4a4c2d860b9944624a1434d9d7580e9a6d38` 完成应用层私有媒体审查与最小补修：跟进附件、报价图片、SKU 图片/缩略图和产品证书均由认证 API 按模块权限返回；证书新增 ERP 私有文件字段并拒绝外部 URL；银行凭证现有模型仅为权限控制的引用、哈希与说明。Django 定向 API 回归 68 项、定向 Vitest 8 项、Chrome 通道浏览器回归 13 项（含 390px）和 Vite build 通过；Chrome Use 已实际检查证书列表及上传表单。证据见 [ISS-017 私有附件验收](uat-evidence/iss-017-private-files/README.md)。由于没有目标环境对象存储/CDN/Nginx/反向代理配置，ISS-017 仍为 BLOCKED；本轮不宣称生产安全通过，不部署、不合并、不关闭 Issue。

## 依赖次序

以下仅为问题台账的建议依赖，不是自动开工许可：

1. **R0-E1 补验准备**：由业务负责人先决定订单“完成”语义（ISS-001）。补跑美元直接记账、独立采购闭环、库存冲销边界、媒体文件、CSV 导入/导出和 PI 实际文件验收（ISS-004–007、ISS-019–020、ISS-052）；核实采购状态中文显示并修复收货冲销旧提示、越权客户英文错误（ISS-053–055）。仅在用户明确授权的路线内按 Part 验收结果自动推进，不以本依赖建议作为新阶段授权。

2. **安全/角色验收**：重跑 npm advisory 审查并评估当前依赖（ISS-002）。只有用户明确进入内测并授权测试账号后，才执行受限角色真实 UI/API 全流程验收（ISS-003）；不改当前开发人员权限。

3. **业务待决**：合同变更审批范围、SupplierSKU MOQ、历史销售流水归属、跨权限成本重分摊、历史合同主体快照由业务负责人决策（ISS-021、022、037–039）。决策前保持安全现状，不推导新模型或流程。

4. **部署准备**：只有另行明确进入部署阶段后，运维处理外部媒体 ACL、备份恢复、生产安全配置、审计日志防篡改、媒体拓扑和 PostgreSQL staging/数据迁移（ISS-017–018、043–047、051）。本阶段不执行生产部署或真实数据迁移。

5. **低优先级体验/增强**：P2 和 P3 事项按实际使用影响排期；Enhancement-Later 先作业务决定，不进入当前必做范围。

## 阶段准入与退出规则

- 新路线/阶段必须由用户明确提出；若用户已明确授权一条包含多个 Part 的路线，可在完成当前 Part 验收后自动进入该路线下一 Part。不得超出路线或进入用户明确排除的 Part；阶段计划、前序 CI 或 `PASS` 本身不构成授权。

- 进入内测、生产部署或改变重大业务规则必须获得用户明确授权；不能由路线图或 Part 自动授权。

- 开始实施前先读 `AGENTS.md`、`PROJECT_ISSUES.md` 和本文件，确认基线、未关闭阻塞、业务决定与允许范围。

- 进入内测需先满足项目权限约定：全站服务端鉴权与数据范围真实验收；用户明确授权创建真实测试角色后再配置。开发超级管理员身份不继承给新账号。

- 阶段验收只对声明的流程、对象、权限和数据环境负责。自动测试、PostgreSQL CI、真实 UI、文件内容和部署环境是不同证据，不得相互替代。

- 退出阶段时必须列出新增、已修复待复审、未关闭、BLOCKED、延期和未测试事项。历史事项必须逐 ID 更新，不能因阶段 PASS 批量清空。

- `FIXED_PENDING_REVIEW` 只有独立复审或用户明确接受后才可转 `CLOSED`。问题若被新证据重现，恢复活动状态并保留历史。

## 当前阻塞和阶段决策

- 内测角色验收仍是阶段门槛；开发身份照常保留，待用户明确进入内测并授权隔离账号后执行（ISS-003）。

- 订单完成/收款语义、供应商 MOQ、合同变更审批范围、历史财务归属、跨权限成本委托和订单历史主体展示需要业务决定（ISS-001、021、022、037–039）；冲销反馈和越权客户错误提示仍需后续复验/修复（ISS-054–055）。ISS-053 已完成当前基线核实，仍待统一独立复审。

- 对象存储 ACL、联合备份恢复、生产安全配置、审计防篡改和 staging 数据迁移属于部署准备，当前不可把它们表述为已验收（ISS-017、018、043、044、047、051）。

- R0-E1 独立复审为 PARTIAL PASS；本轮治理文件通过独立审查前不宣称 R0-E1 或 R0-D4 阶段封版。

## 2026-10-14 R0-F1 财务定向复修

基线 `master` / `0ab4ac7`，仅处理同批复审问题。修复筛选栏合法 Grid、收付款成功文案、完整订单编号保留与旧成功提示；加强 ISS-056 的实际序列化金额泄漏检测。新增 ISS-059–061；ISS-056、ISS-057 和新增项均待 ChatGPT 独立复审。全量自动化与内置浏览器实际检查见 [定向复修验收](R0-F1-定向复修验收.md)。截图归档仍受支持接口限制，未绕过。交付后停止，不进入下一模块；三项精确提交 CI 以交付链接为准。

## 2026-10-14 R0-F1 复审与 R0-F2 开始

用户本轮明确转述：R0-F1 财务模块代码及已覆盖交互经 ChatGPT 独立复审 PASS，允许有条件封版。最终提交 `4298c31ec043b2f3fc2d690768455d7df417de08`，[CI #38433549045](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38433549045) 三项 SUCCESS。按 REVIEW_PROTOCOL 关闭 ISS-056、ISS-059、ISS-060、ISS-061；ISS-057 继续 FIXED_PENDING_REVIEW，截图归档 BLOCKED，不宣称完整独立视觉验收。

R0-F2 基线 `master` / `4298c31`，范围为经营概览 Dashboard、报表中心 ReportsPage 和直接关联图表/筛选组件。延续整体 UI/UX 路线；统计计算、数据范围、后端权限、模型及历史快照不改。交付 push master 后停止等待 ChatGPT 独立复审，不进入集中历史 Issue 修复、内测或部署。

## R0-F2 实现与验收边界

本轮完成办公文案、概览分组、刷新/空/错误状态、报表分步条件、已查询条件、URL 恢复、图块本地保存与载入/排序/移除/撤销、图块下钻期间和返回、图表展示及权限一致入口。后端计算、数据范围、模型、正式 RBAC 和历史快照未改。新增 ISS-062（统计边界 OPEN）、ISS-063–065（FIXED_PENDING_REVIEW）、ISS-066（内置续验 BLOCKED）。此前未关闭项全部保留。

R0-F1 最终独立结论与关闭项见上一节，允许有条件封版，不宣称完整独立视觉验收。本轮完整矩阵、测试和截图限制见 [R0-F2 验收](R0-F2-经营概览与报表中心验收.md)。最终提交及三项 GitHub CI 在交付中给出；交付后停止等待 ChatGPT 独立复审。

## 2026-10-14 R0-F2 独立复审与 R0-F3

用户转述 ChatGPT 对 R0-F2 `04d3526` 独立代码及自动回归 PASS，允许有条件封版；CI #38503175230 三项 SUCCESS。ISS-062、ISS-066 继续保留，独立视觉证据 BLOCKED，ISS-063–065 补记代码结论但保留待视觉复核。旧报表 URL 无权来源可能残留表单的风险登记 ISS-067 / NEEDS_VERIFICATION，未宣称复现。

2026-10-23 在统一基线 `c356e57014d28295485d52df23612c2fe6c02444` 的独立 worktree 中核实 ISS-067：真实 Chrome 下无权员工打开销售旧 URL 时，来源选择器仅保留有权来源并显示不可访问提示，未发出无权来源查询；后端强行请求返回 403 且不含业务 rows。切换有权来源、刷新、返回、保存、重载及 ISS-042 共享模板路径均通过。仅新增回归测试和证据，ISS-067 仍保持 NEEDS_VERIFICATION，等待独立复审；详见 [`ISS-067 核实报告`](uat-evidence/iss-067-report-permission/acceptance-report.md)。

R0-F3 按历史库存 Phase A/B 框架增量优化：概览与流水分页、基础单位与预留展示、窄桌面工作台、日志失败与重试、手工调整加载/保存交互及冲销反馈。计算、收货/发货、预留、冲销业务规则、历史、成本、模型和权限配置不变。新增 ISS-068–069 待复审；ISS-070 为截图归档/独立视觉缺口。旧库存 ISS-006、013–015 等保留。

验收详见 [R0-F3 库存验收](R0-F3-库存概览与库存流水验收.md)。自动布局、Codex 内置浏览器实际目视、ChatGPT 独立视觉分别记录。交付 push master 并核对三项 CI 后停止，等待独立审查，不进入历史 Issue 集中修复、内测或生产部署。

## 2026-10-14 R0-F3 独立复审与 R0-F4

R0-F3 最终 `ca486be514744d8d00344cb997a1f0c1389129f0`，[CI #38507649163](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38507649163) Backend / PostgreSQL / Frontend 三项 SUCCESS。用户转述独立代码、自动化与已覆盖操作 PASS，允许有条件封版。ISS-068、069 记录已覆盖范围通过；独立截图视觉仍按 ISS-070 BLOCKED，不关闭旧库存业务事项。

R0-F4 仅优化供应商列表/新建/编辑/详情、付款条款组件、分类与已有采购/SKU关联导航。复用 ResourcePage、EntityDetailModal、PaymentTermsEditor、CategoryMultiPicker 和既有分页组件。只改变展示/前端操作反馈；供应商与供货身份、价格/MOQ、付款计算、成本分摊、历史快照/计划、模型及权限范围不变。新增 ISS-071、072 待独立审查；ISS-073 记录截图独立视觉缺口；ISS-074 为模拟关联新采购取消确认时序待核实，历史 P2/P3 延后。

覆盖矩阵见 [R0-F4 供应商验收](R0-F4-供应商管理验收.md)。完成精确 HEAD 三项 CI SUCCESS、push master 后停止等待 ChatGPT 独立复审，不进入下一模块、集中历史修复、正式内测或生产部署。

## R0-F6 交付边界（2026-10-15）

复用 ProductPage、CategoryPage、ResourcePage 和统一未保存/保存状态机制。保留前缀变更预览、分类属性冻结/引用限制和排序确认，不扩展 SKU/包装优化。自动化布局、Codex 实际浏览器操作/目视、ChatGPT 独立视觉分别记录。归档正常保存 JPEG 原始字节，没有安全拒绝或绕过。历史业务 Issue 保留；本轮 push master 后停止等待独立复审。

## R0-F7B 本轮交付边界

包装共享模板、交易单位和SKU包装操作增量优化；不修改模型、身份、换算、成本、装箱、快照、权限。ISS-088仅依明确接受关闭，ISS-089–091待独立审查。截图归档、Codex目视、自动布局与ChatGPT独立视觉分开，后者待审。尚未专项覆盖：产品证书、HS编码、导入、组织权限和访问状态页；报价/订单/客户/采购历史专项的边界保留。完成后停止，不自行进入下一Part、集中历史修复、内测或部署。

## R0-F8B 范围与证据（2026-10-16）

仅优化ImportPage前端，后端只追加同token重放拒绝断言。没有修改模型、导入写入/校验核心、SKU身份、财务规则或权限。独立SQLite真实CSV新增/更新、错误拒绝、取消、状态冲突恢复及下载内容已核对；自动化、Codex目视、ChatGPT独立图片分开记录。ISS-052正式审计和完整HTTP证据尚缺，继续NEEDS_VERIFICATION，不提交关闭申请。完成Push及精确HEAD CI后停止等待独立复审。

## R0-F8C 范围与停止边界（2026-10-16）

只修改OrganizationPage.vue、AccessDeniedPage.vue及其测试/证据。使用专用SQLite r0f8c-ux.sqlite3、Django8117/Vite5204；仅创建不绑定员工的合成角色和组织展示样本。只读核对预置角色/权限未变、成员为0、开发超级管理员启用、RBAC关闭。受限入口/401/403等以模拟API回归标注，不是正式UAT。完整模块/独立视觉/未覆盖状态与历史缺口见最新[全站清单](R0-F8A-全站前端UX覆盖清单.md)。完成Push及精确HEAD三项CI后停止等待独立复审；不根据前端路线走到此处自动进入集中历史修复或内测。

## R0-F9停止门槛（2026-10-16）

本轮交付后等待ChatGPT独立代码与原始证据审查。全站UI路线的审查范围已列齐，不把已有专项或CI成功扩大为所有动态状态、文件内容、正式员工权限或业务规则通过。ISS-099的SKU初始化提示、ISS-100的图片像素/元数据来源说明必须有独立处置结论；ISS-098要独立接受局部修正。F1–F4当前页面原图已补，历史特定状态缺口按各Issue保留。

进入历史集中核实/修复阶段的必要条件：最终精确HEAD三项CI成功；ChatGPT独立代码/证据审查接受本轮基线；未通过项逐项修复或被明确接受并保留边界；用户确认下一阶段范围。当前不满足独立复审门槛，不自动继续。正式RBAC、员工UAT、内测、生产部署仍需单独明确授权。

## R0-F9-VIS-01 交付与停止边界（2026-10-17）

基线9d05a70。27路由完成态三请求视口重新采集，最终81张中63张尺寸符合请求，18张仍为截图接口技术BLOCKED；没有覆盖旧573原图。新目录368张含诊断过程，最终图、代表表单/详情与诊断角色分开；重点12张加载图、69张尺寸异常图均有逐项对照。ISS-099两入口实际未复现，保留NEEDS_VERIFICATION；ISS-100 BLOCKED，101/102待独立复审，103既有动画警告待核实。

仅增加4项SKU初始化/关闭保护回归、采集校验及文档，未修改运行组件或共享守卫。完整Backend720（跳过10）、Node121、Vitest607、Playwright139、Build通过；PostgreSQL及最终精确HEAD的三项CI按交付记录核对。实际错误/恢复只覆盖隔离API服务中断，未重新执行全部历史业务写入/全部路由错误组合，不扩大为正式UAT。

完整27路由矩阵、已通过/未通过、原因、前后对照、浏览器与自动化边界见[R0-F9-VIS-01报告](R0-F9-VIS-01-全站视觉复核与补充截图.md)；[新原图索引](uat-evidence/r0-f9-vis-01/index.html)。最终Push master并核验同SHA三项CI成功后停止，等待ChatGPT再次独立代码与证据审查。当前不满足全项视觉封版；历史集中修复、正式RBAC、员工UAT和生产部署仍禁止自行进入。

## R1-FIN-P2-B-FIX-01 银行资金前端安全流程补修（2026-10-19）

基于P2-B精确基线 `47c9f20ad4e9643c22c62bc93e4ffcb0a38d905f`，仅处理独立审查指出的四类前端安全缺口：预览请求指纹与字段失效、预览不等于保存及刷新恢复、来源逐条人工核实与最终确认摘要、来源异步请求竞态。未修改P2-A资金计算、历史金额、Transaction/PaymentPlan/AdvanceAllocation、报表口径、权限策略或数据库。

新增ISS-110至ISS-113，均为 `FIXED_PENDING_REVIEW`；ISS-114记录此前139/8全量Playwright失败与本轮复现分类，保持`NEEDS_VERIFICATION`。ISS-105仍OPEN，ISS-108仍BLOCKED，ISS-109仍FIXED_PENDING_REVIEW；未关闭其他问题。新增Playwright用例覆盖未核实来源拒绝、金额修改使预览失效、确认勾选、刷新恢复稳定请求键和输入；当前完整套件共150项全部通过（包含本轮3项新增），另保留历史失败日志供独立复核。

本轮完成后停止，等待ChatGPT独立代码、真实Chrome截图、隔离数据库及精确HEAD三项CI复审；不得进入P2-C、P3、正式RBAC、员工UAT或部署。

## R1-FIN-P2-B-FIX-02 银行资金前端剩余安全边界补修（2026-10-19）

基线为 `aef3425ec97b78c3a312f54010d9de60613e75a4`。本轮只处理三项前端安全边界：恢复草稿前建立新建空白基线，保证恢复内容继续触发未保存保护；来源分配金额变化立即撤销该来源的人工核实状态，必须重新核实并重新预览；本地快照使用字段白名单和版本标记，初始化即清理过期记录，不保存凭证引用、SHA256或人工核实说明，恢复后要求重新填写。P2-A后端资金计算、历史数据、核销、权限策略和数据库模型均未修改。

新增ISS-115至ISS-117，均为 `FIXED_PENDING_REVIEW`。新增真实浏览器回归覆盖恢复草稿关闭取消/确认放弃、30→50来源金额修改、过期快照初始化清理和敏感字段不落本地。当前完整Playwright为154项全部通过；Node、完整Vitest、后端SQLite及构建通过，PostgreSQL以精确HEAD CI核验。完成提交并等待ChatGPT独立代码与视觉复审；不得自动进入P2-C、正式RBAC、员工UAT或部署。

## R1-FIN-P2-C 银行资金记录与结汇完整业务闭环验收（2026-10-19）

基线 `9cd57800ce524d8e0ead90f245215ac4153cf144` 的三项 CI 均为 SUCCESS。本轮在隔离 SQLite、合成业务记录和真实 Chromium 中验收外币分次结汇、同币种合并、预收核销、手续费、CNY直接收付、确认/放弃、请求键回查、重复/超额/退款/作废拒绝、历史4位和JPY精度。结汇只新增合法人民币资金事件及来源分配，不生成第二笔客户收款、不重复核销、不改订单履约、库存、历史金额或既有参考统计。完整矩阵、数据库前后对比、原始截图和日志见[R1-FIN-P2-C验收](R1-FIN-P2-C-银行资金记录与结汇完整业务闭环验收.md)。

本轮新增并登记ISS-118（旧localStorage敏感字段清理）、ISS-119（独立银行手续费关联选择器）、ISS-120（浏览器Decimal字符串序列化），均保持 `FIXED_PENDING_REVIEW`。完整Playwright 155项、Vitest 633项、Node 134项、Backend SQLite 764项通过；本地PostgreSQL无服务，以最终精确HEAD CI核验。ISS-105仍OPEN、ISS-108仍BLOCKED；P2-C完成后停止等待ChatGPT独立代码、业务和视觉复审，不自动进入P3、正式RBAC、员工UAT或部署。

## R1-FIN-P3-A 人民币实际资金统计与独立报表（2026-10-19）

用户授权从P2-C进入本阶段。基线`c895e1d0d758c1a9c158e940975689dc4b0ae0d6`；在隔离SQLite与真实浏览器中新增并核对只读`/api/actual-rmb-cash/`、`actual_cash`报表来源、财务概览实际资金区域、CSV和逐笔下钻。后端只聚合`RmbCashEvent.status=confirmed`的`bank_net_amount`并按`bank_date`统计，含扣手续费不重复扣除，旧`cash`来源仍是账面人民币折算参考。没有设置统计启用日，不显示公司余额，不修改旧财务金额或历史记录。Backend SQLite 766（跳过13）、Node136、Vitest633、Playwright155、Build通过；本机PostgreSQL未运行，精确HEAD的CI需在push后复核。新增ISS-121 BLOCKED，等待财务负责人明确启用日期和全公司覆盖政策；ISS-105/108及其他历史Issue保留。完成后等待ChatGPT独立代码、财务口径和视觉复审，不进入P3-B、RBAC、员工UAT或部署。

## R1-FIN-P3-A-FIX-01 实际人民币资金统计安全与容错补修（2026-10-19）

基线 `470eb34e161d97f68ff8a1151870a6ab687f32ea`。本轮仅处理两项已确认安全缺陷：`FinanceDashboardPage.vue` 将旧财务概览与实际银行资金统计拆为独立请求，实际资金失败显示独立错误/重试且不阻断旧概览；按主请求与实际资金请求版本丢弃日期切换产生的旧响应，清空旧期间数据后再加载。`actual_cash_api.py` 的CSV导出复用既有 `safe_csv`，保护银行参考号、事件文本和可控说明，保留正常参考号可读性及API/数据库原文。报表中心既有CSV保护保持不变，P2-A资金计算、历史金额、核销、启用日期和权限策略不变。

定向Vitest共5项通过，新增Playwright容错/快速切换2项通过；后端实际资金CSV危险前缀和权限403共4项通过。隔离数据库真实HTTP观察、真实Chrome正常页面截图、错误/重试与日期竞态日志见[P3-A-FIX-01验收](R1-FIN-P3-A-FIX-01-实际人民币资金统计安全补修验收.md)。新增ISS-122、ISS-123均为`FIXED_PENDING_REVIEW`；ISS-105保持OPEN，ISS-108和ISS-121保持BLOCKED；完成后停止等待ChatGPT独立代码、财务口径和视觉复审，不进入P3-B、正式RBAC、员工UAT或部署。

## R1-FIN-P3-B 财务统计最终业务闭环与兼容性验收（2026-10-19）

基线 `c27abcb2e95b833c3a4f4c59161c3fcc7c1d4f64` 的三项先验 CI 均为 SUCCESS。本阶段只做隔离数据库业务验收、兼容性核对和证据归档，没有改变D01-D08、统计启用日期、旧金额、核销、订单、库存或银行账户余额边界。已确认银行事件按银行日期和人民币净额统计，账面折算参考继续独立保留；外币分次/合并结汇、CNY、手续费、pending/cancelled、跨月跨年、精度、权限、旧报表/CSV和安全拒绝均有真实 API、数据库快照及 Chromium 截图。完整报告见[R1-FIN-P3-B验收](R1-FIN-P3-B-财务统计最终业务闭环验收.md)。

ISS-122、ISS-123 的独立复审通过结论已同步为 CLOSED；ISS-105 OPEN、ISS-108/121 BLOCKED 保留。Backend SQLite 768（跳过13）、定向资金/权限62（跳过3）、Node136、Vitest635、Playwright157、Build通过；本机PostgreSQL未安装/监听和真实网络超时注入在报告中明确为BLOCKED，等待最终精确HEAD CI与ChatGPT独立复审。完成后停止，不进入P3-C、正式RBAC、员工UAT或部署。

## R1-READINESS-01 全系统试用准备与业务阻断问题审查（2026-10-19）

基线为 `199a21e0f407ba9ad772a5dec86e0b30dbd0c9b5`。本轮只读复核全系统模块、当前代码/测试、权限、部署配置和 123 个唯一 Issue 的最后一次状态；未修改业务代码、模型、迁移、历史金额或权限执行策略。R1-FIN-P3-B 已按授权记录为财务功能阶段性验收通过，但不等同于生产就绪。ISS-105 保持 OPEN，ISS-108 和 ISS-121 保持 BLOCKED。

当前只具备开发超级管理员身份下的隔离合成数据演练条件，不具备真实员工内部试用条件。A 类门槛为 ISS-003 正式员工身份/数据范围、ISS-018 数据库与媒体联合备份恢复、ISS-055 跨客户 API 范围；其余 Issue 的 A–D 分类、模块边界、最小试用方案和退出条件见 [R1-READINESS-01 审查报告](R1-READINESS-01-全系统试用准备与业务阻断问题审查.md)。本轮没有启动正式员工 UAT、RBAC 或部署，完成文档后停止等待 ChatGPT 独立审查。

## ISS-041-A 报表中心两级交叉分组基础能力（2026-10-22）

基线为 `codex/iss-062-date-window` / `9edbb6488a66a0801ecc1e5bc842df7866c6c7dc`，在独立 worktree 和 `codex/iss-041-multidim-01` 分支实施。依据 2026-10-20 业务整理稿，本轮在现有单维度报表引擎上增量支持可选第二统计维度：后端交叉聚合、独立分组结构、去重单据数、分单位数量、CSV 双分组列、维度权限校验；前端第二维度选择、旧 URL/localStorage 兼容、两级表格/条形图和双向基础下钻。没有新增数据库迁移，没有修改实际银行人民币资金事件口径、账面人民币折算参考、预计利润、自定义报表未来日期查询能力或 ISS-121 状态。

本轮自动化与真实 Chrome 证据已归档到 `docs/uat-evidence/iss-041-multidim-01/`，当前状态为等待独立代码审查；ISS-041 仍保持 `Enhancement / BLOCKED（延期）`，本节不代表关闭 ISS-041。原始销售订单/商品明细独立详情列表及客户、产品、SKU 详情页经营分析入口继续作为后续 ISS-041 子任务。

## ISS-041-B 经营分析原始明细下钻与业务详情页入口（2026-10-22）

基于 `codex/iss-041-multidim-01` / `66338b701afed071bd6482a33a8cca8ebc20bfa2` 创建独立 worktree 和 `codex/iss-041-detail-drill` 分支。本轮在 ISS-041-A 两级分组基础上增量增加销售/采购原始明细 API、服务端页大小限制、排序、空状态、原始订单详情链接、商品行与订单金额调整分离，以及客户、产品、SKU详情弹窗到现有报表中心的安全入口；保留日期、金额、历史订单隔离、数据范围、个人图表、URL恢复、CSV和既有下钻行为，不新增数据库迁移。

后端32项报表测试、前端定向15项 Vitest、Node 143项、前端生产构建、报表中心真实 Chrome 15项和 ISS-041-B 1440/700截图测试均已通过，证据归档至 `docs/uat-evidence/iss-041-detail-drill/`。当前仅将 ISS-041-B 记为 `FIXED_PENDING_REVIEW` 说明，等待独立代码、权限与视觉复审；ISS-041 仍为 `Enhancement / BLOCKED（延期）`，不提前关闭，不进入 ISS-042/ISS-048。

## ISS-042-DEV 团队共享报表模板（2026-10-23）

基于 `codex/iss-041-detail-drill` / `0bba34c0e7139b77a88d2e838dbf921eff427373` 创建独立 worktree 和 `codex/iss-042-shared-reports` 分支。本轮在既有报表引擎、ISS-041-A 两级分组和 ISS-041-B 明细能力之上增量实现共享报表模板：新增 `SharedReportTemplate` 模型及迁移 `0079_shared_report_template`，服务端配置白名单/维度、来源和报表权限校验，草稿/发布/取消发布、版本冲突保护、OperationLog 审计和历史读取；前端新增团队模板列表、使用、创建、编辑、发布、取消发布、删除及冲突提示，保留旧 localStorage 图表、旧 URL、日期范围和当前查询的兼容性。共享模板只保存配置，不保存结果快照或日期，实际查询仍由当前用户权限和当前报表逻辑执行。

后端共享模板 7 项、既有报表 32 项、SQLite 全量 799 项（跳过 13 项）、前端定向 Vitest 7 项、旧概览报表 Vitest 15 项、Node 143 项、生产构建、共享模板真实 Chrome 跨会话测试和旧报表中心 Chrome 15 项已通过；1440px、1024px、700px 截图及日志归档至 `docs/uat-evidence/iss-042-shared-reports/`。本轮不新增共享审批/复制/版本回滚治理，不改变实际银行人民币资金统计或 ISS-121 状态。当前标记为 `FIXED_PENDING_REVIEW`，等待独立代码、权限、审计与视觉复审；ISS-042 仍为 `Enhancement / BLOCKED（延期）`，不提前关闭。

## ISS-042-FIX-01 共享模板并发版本与删除审计集中补修（2026-10-23）

基于 `codex/iss-042-shared-reports` / `6d5ce10a2ce8a432b427371542eac7378daca655` 继续修复发布/取消发布未递增配置版本、旧版本并发操作缺少原子冲突保护，以及删除模板后历史接口依赖现存模板的问题。发布、取消发布和编辑均在行锁事务内校验提交版本；重复状态操作返回 409 且不生成虚假审计；管理权限可按原模板 ID 读取删除后的完整模板审计，普通查看权限无法读取删除后的配置历史，通用操作日志也保持实体范围隔离。

本轮新增/补强并发、重复操作、删除后历史、权限和非法 ID 测试；SQLite 全量 800 项（跳过 13 项）、共享模板 8 项、报表回归 32 项、前端定向 7 项、Node 143 项、生产构建、真实 Chrome 共享模板 1 项及报表中心回归 15 项通过，证据归档至 `docs/uat-evidence/iss-042-fix-01/`。Chrome 仍区分 mock API 交互验收与真实 Django APIClient 权限/并发验收；真实 Django 跨账号浏览器集成因当前环境无登录测试服务账号保留待办。当前标记为 `FIXED_PENDING_REVIEW`，ISS-042 仍为 `Enhancement / BLOCKED（延期）`，不提前关闭。

## ISS-048 财务概览指标下钻（2026-10-23）

基于 `codex/iss-042-shared-reports` / `fb859b91f68bb62c539d5439c65b52c06f13a58c` 创建独立工作树和 `codex/iss-048-finance-drill` 分支。本轮逐项核对财务概览卡片来源、金额计算、日期依据和权限：对有可靠来源的合同销售额、订单采购归属成本、订单费用、预计订单利润、账面收支、应收应付和未核销预收预付新增服务端分页/排序构成明细；详情复用既有正式订单、已确认流水、计划和数据范围过滤，并链接现有订单/财务流水路由。银行实际人民币资金不复制统计逻辑，卡片入口定位到既有已确认银行事件明细和原始事件链接，继续使用 `bank_date`/`bank_net_amount` 及确认状态规则。无可靠依据的会计利润、银行账户余额和未确认凭证未伪造下钻。

新增财务下钻后端测试、数据范围/权限测试和前端交互测试；SQLite 全量 808 项（跳过 13 项）、财务/RBAC 定向 65 项、Node 143 项、财务 Vitest 12 项、生产构建、ISS-048 真实 Chromium mock API 桌面/窄屏 2 项、既有财务/报表 Chrome 回归 21 项均通过。真实 Django APIClient 权限与口径测试、真实 Chromium 页面截图和原始日志归档至 `docs/uat-evidence/iss-048-finance-drill/`；浏览器测试使用 mock API，跨账号 Django 浏览器集成待集成环境服务账号，PostgreSQL/CI 按约定保持 PENDING。当前仅记录为 `FIXED_PENDING_REVIEW`，ISS-048 仍保持 `P3 / BLOCKED（延期）`，等待独立代码、财务口径、权限和视觉复审，不提前关闭。

## ISS-048-FIX-01 最小权限一致性补修（2026-10-23）

基于 `codex/iss-048-finance-drill` / `f2a44dafabdd5cc7b4c5b95abed3865867fd9e7b`，仅修复应付款财务指标的概览与下钻权限不一致：`payable_count`、`payable_rmb` 改为沿用采购查看权限，不再额外要求订单查看权限；采购成本、订单费用、预计利润、销售、应收和其他财务指标保持原权限矩阵。应付款明细按采购侧展示供应商和采购单链接，并继续复用既有财务计划数据范围过滤。

新增无订单权限但有采购/财务权限、无采购权限反向拒绝、既有范围一致性和前端权限边界测试。后端 67 项财务/RBAC 定向测试、前端 Node 144 项、财务 Vitest 12 项、生产构建及真实 Chromium 6 项回归通过。证据见 `docs/uat-evidence/iss-048-finance-drill/fix-01/`。ISS-048 仍保持原有 `P3 / BLOCKED（延期）` 和 `FIXED_PENDING_REVIEW`，不提前关闭；PostgreSQL、CI 和真实 Django 跨账号浏览器集成仍待外部环境验收。

## ISS-053 采购单状态中文显示核实（2026-10-23）

基于统一基线 `c356e57014d28295485d52df23612c2fe6c02444` 建立独立 worktree 和 `codex/iss-053-purchase-status` 分支。本轮仅核实，不修改采购业务代码：`PurchaseOrder` 继续保存英文枚举，序列化器提供 `status_display`，采购列表、详情、草稿编辑工作台、状态筛选、采购实体上下文、销售订单关联采购单均通过 API 和真实 Chrome 验证中文显示；`ordered` 的筛选与存储值仍保持 `ordered`。后端采购相关 39 项、前端定向 Vitest 52 项、Chrome Playwright 11 项和生产构建通过，截图/API/日志见 `docs/uat-evidence/iss-053-purchase-status/`。当前没有确认仍存在的缺陷，也没有本轮业务修复；历史英文显示在当前基线未复现，ISS-053 保持 `NEEDS_VERIFICATION`，等待统一独立审查，不自行关闭。

## ISS-049 / ISS-053 / ISS-067 统一集成验收（2026-10-23）

在统一基线 `c356e57014d28295485d52df23612c2fe6c02444` 上使用独立 worktree 建立 `codex/integration-049-053-067`，按无冲突的 `--no-ff` 顺序合并 ISS-049、ISS-053、ISS-067。三项源码、测试、截图及历史证据均保留；文档台账仅补齐 ISS-049 当前状态，并修正阶段阻塞描述与 ISS-053 当前核实结果的一致性。完整 API 响应、浏览器观察、测试日志和剩余风险见 [`统一集成验收报告`](uat-evidence/integration-049-053-067/README.md)。

## R1-ISS-037-P1 正式商业单据主体快照修复（2026-10-21）

基于最新 `origin/master` 创建独立分支 `codex/r1-iss-037-p1`，仅修复正式销售订单和采购订单的主体快照缺口。Order 在正式确认时保存客户名称、国家/地区、地址、联系人、电话和邮箱；PurchaseOrder 在正式下单时保存供应商名称、地址、联系人、电话和邮箱；Supplier 增加可选地址字段。没有数据迁移回填，历史缺失值保留未知；正式页面显示真实快照，当前主档仅作为明确标注的参考。Quote/QuoteItem/PI 既有修订链、主体及 SKU 行级快照未重构，真实 Chrome 已核对报价/PI导出文件使用历史主体。

旧开发分支新增未发布的 `0078_formal_party_snapshots`，未修改已发布迁移。SQLite 0076→0077→0078→0077→0078 迁移循环、后端 773 项（跳过13）、前端单元 138 项和构建均通过；本机无 PostgreSQL 5432 监听，PostgreSQL 与 GitHub Actions 保持待环境可用后复核。该 `0078` 与 R1-SKU-01、R1-MOQ-02 同号迁移均依赖 0077，已作为旧分支历史保留；实际整合须重新核对基线迁移图，不复制同号迁移或改写已发布迁移。ISS-037 保持 `FIXED_PENDING_REVIEW`，不关闭，等待独立代码、数据权限和视觉复审。

## R1-ISS-037-P1-FIX-01 历史商业单据展示遗漏补修（2026-10-21）

在 `codex/r1-iss-037-p1` 上完成定向展示修复，提交 `126be74d5a2269a8f947570ca0803771feab6a1e`。报价列表和详情优先显示保存的 `buyer_company_name`；正式采购关联卡片优先显示 `supplier_name_snapshot`；缺失快照明确显示“历史主体未记录”，实时主档仅以单独标签显示。未新增模型或迁移，未改写历史单据、金额、搜索或权限规则。SQLite 后端、前端 140 项单元测试、构建及真实 Chrome/PI Excel 证据已完成；PostgreSQL 与 GitHub Actions 仍待环境/额度恢复。ISS-037 继续保持 `FIXED_PENDING_REVIEW`。

## R1-ISS-037 集成兼容性验收（2026-10-24）

基于统一基线 `54925e0a10a48c16ba3b66bbab9e433f48a0e2d7` 在独立 worktree 创建 `codex/next-iss-037-integration`。审查发现该基线已使用 `0078_historical_contract_scope` 和 `0079_shared_report_template`，因此没有复制旧分支同号迁移；正式主体快照字段以新的 `0080_formal_party_snapshots` 依赖 `0079` 接入，未修改或删除既有迁移。最初尝试用同号迁移汇合时，回退到旧迁移会出现字段重复删除；该真实兼容问题已通过上述迁移重编号修正，前进、回退和旧资金记录保护回归均通过。

集成保留报价/PI既有主体与 SKU 快照，并保留销售订单六项客户主体快照、采购单五项供应商主体快照、缺失历史时“历史主体未记录”及当前主档单独参考的规则。当前隔离数据库中将客户/供应商主档改名后，报价 `QT-2026-001`、订单 `SO-2026-001` 和采购单 `PO-ISS037-001` 的 API、真实 Chrome 列表/详情仍显示原快照；PI Excel 导出保留 `ISS037 Buyer Before Rename`。未修改 ISS-021 数量变更代码、生命周期转换规则或正式 RBAC策略。完整命令结果、API摘要、导出和截图索引见 [`ISS-037 集成验收`](uat-evidence/r1-iss-037-p1/INTEGRATION-README.md)。ISS-037 仍保持 `FIXED_PENDING_REVIEW`，不自行关闭。

## ISS-039-INT 共享采购成本分摊与跨订单权限集成（2026-10-24）

本轮从统一基线 `54925e0a10a48c16ba3b66bbab9e433f48a0e2d7` 创建独立 worktree 和 `codex/next-iss-039-integration`，对照旧分支 `codex/r1-iss-039` 的成果逐文件迁移，不覆盖新代码，也未触碰其他任务分支。原问题已先复现：采购修改员没有销售订单查看/修改权限时，旧成本分配保存路径返回 403。

按已明确的 ISS-039 规则完成最小补修：成本归属写入仅要求 `purchases.update`；新增只返回 ID、订单号、状态的候选接口；采购成本 UI 不再显示客户名、销售价格或利润；只读/无权来源继续脱敏或拒绝。商品数量、商品金额、公共费用和总成本守恒；版本冲突、取消目标和保存失败保持原子；审计保留操作人、时间和前后记录；不修改银行付款、库存、销售单据、金额计算或审批层级。

后端 ISS-039/采购成本/数据范围定向测试 25 项、前端 Node 单元 146 项、生产构建和真实 Chrome 3 项通过。Chrome 覆盖授权采购员、只读采购员、无权角色、旧详情 URL、刷新恢复、候选来源、实际 403 和 1440/700 窄屏截图；证据见 `docs/uat-evidence/iss-039-integration/`。浏览器角色使用隔离 mock API，真实 Django 权限/金额/原子性/审计由 APIClient 覆盖，跨账号真实登录浏览器服务账号仍是环境边界，未伪称为已完成。

ISS-039 台账更新为 `FIXED_PENDING_REVIEW`，不关闭 Issue；本轮不合并 master，提交并推送后等待统一独立代码、权限、业务、审计和视觉复审。

## ISS-026 供应商生命周期与禁止业务硬删除（2026-10-24）

基于统一基线 `71ec4a4c2d860b9944624a1434d9d7580e9a6d38` 在独立 worktree 创建 `codex/iss-026-supplier-lifecycle`。本轮先核实供应商主档、`SupplierViewSet`、采购候选来源、采购单主体快照和前端 `ResourcePage`；仓库未发现独立的“2026-10-24 规则包”文件，故以用户本轮明确的 ISS-026 规则为验收依据，不补造缺失规则。

供应商新增 `is_active` 字段及 `0081_supplier_lifecycle` 迁移；普通 `DELETE` 统一返回 405，前端删除入口移除，改为停用/启用动作。停用/启用在行锁事务中写入操作审计；规则、Supplier SKU、历史采购和人工来源候选均排除停用供应商；新采购序列化与确认路径拒绝停用供应商。现有采购单的 `PROTECT` 外键及供应商名称/地址/联系人快照未改动，历史采购、付款和来源保留；未修改 ISS-039 成本分配或 ISS-037 历史快照规则。

验收证据见 [`ISS-026 验收记录`](uat-evidence/iss-026-supplier-lifecycle/README.md)：供应商生命周期专项后端 4 项、相关候选/采购/快照/ISS-039/037/040 回归 33 项、前端 Node 150 项、生产构建、全新数据库顺序迁移检查和真实 Chrome 桌面/390×844 窄屏操作均通过。Playwright 供应商浏览器套件未能启动，原因是隔离 worktree 没有 `@playwright/test`，补依赖时受 Windows 文件锁阻断；不将该套件宣称为通过。ISS-026 仅记录为 `FIXED_PENDING_REVIEW`，不关闭、不合并 master，等待统一独立审查。

## ISS-107 实际银行人民币与账面折算参考金额区分（2026-10-24）

基于 `71ec4a4c2d860b9944624a1434d9d7580e9a6d38` 创建独立 worktree 和 `codex/iss-107-finance-labels`。逐项复核财务概览、财务流水、报表、银行资金、API、CSV、模型元数据和历史共享报表配置后，确认公开数据路径已经使用“人民币折算参考”和“银行实际人民币资金”两套口径；本轮真实缺陷是 `Transaction.rmb_amount` 的模型 verbose_name 仍称“实际人民币金额”，以及资源入口描述不够明确。

最小修复为模型元数据迁移 `0081_transaction_rmb_reference_label` 和资源描述澄清。旧英文 API 键、`source=cash`、旧报表配置和 ISS-048 统计/权限逻辑均保留；未改写任何金额、汇率、流水或银行事实，不把两种金额相加。合成批次为账面 USD 100 × 7.1 + CNY 250 = ¥960.0000，银行已确认人民币净额为 ¥705.00；迁移前后同一批数据库业务金额哈希均为 `2c10f1295ccfb73c4f8c89773b37004f20d5f206732fee5e219ce02062f55fa7`。完整 API/CSV、测试和截图索引见 `docs/uat-evidence/r1-fin-p1/ISS-107-FOLLOWUP.md`。ISS-107 更新为 `FIXED_PENDING_REVIEW`，不关闭、不合并 master，等待独立复审。

## ISS-026 / ISS-107 / ISS-017 统一集成验收（2026-10-24）

基于统一基线 `71ec4a4c2d860b9944624a1434d9d7580e9a6d38` 建立独立 `codex/integration-026-107-017` Worktree，已核实并集成三个源提交：ISS-026 `3625f472b028146c062823990322de32a98759a1`、ISS-107 `60df1b045c06c7f2146b44e4a60866b1786024cc`、ISS-017 `c5fc1c11b9728655a363a4f2a5ba0544584a8d07`。三个 `crm.0081` 并行叶节点均依赖 `0080`，仅新增无操作 `0082` merge migration；全新库、既有库升级以及回滚重放均通过，未改写已发布迁移。

ISS-026 供应商停用/恢复、禁止硬删除、采购候选/历史快照与审计规则；ISS-107 银行实际人民币净额与账面折算参考口径；ISS-017 私有附件入口与证书外链拒绝规则均保留。Django 全量 862 项（13 跳过）通过，前端 Node 151、Vitest 645、生产构建和真实 Chrome 关键页面回归通过。旧证书测试中与 ISS-017 规则冲突的一处外部 URL 200 断言已最小同步为 400 并验证数据不变。完整报告见 `docs/uat-evidence/iss-026-supplier-lifecycle/INTEGRATION-026-107-017.md`。

三个源任务 GitHub CI 均为失败状态；集成提交 `3571d374adb8e41d515265a5c429639d5b8f4904` 对应 CI 运行 `40067690763` 的 backend、frontend、backend-postgres 也在可见步骤前失败，且本地没有 PostgreSQL/生产代理环境。因此集成分支继续保持 `FIXED_PENDING_REVIEW`，不作为 master 合并条件，不关闭 Issue，等待统一独立代码、数据库、权限和部署安全审查。

## ISS-019 经营报表 CSV 准确性复核（2026-10-24）

基于统一基线 `af018ac63cf71143d223b9f6db4a087707495693` 在独立 worktree 创建 `codex/iss-019-report-csv`。先审查 ISS-041、ISS-042、ISS-048、ISS-062、ISS-107 的报表、下钻、共享模板、财务口径和既有 CSV 证据；确认草稿/已提交查询状态、币种说明、单位分开、账面/银行实际资金分离、公式注入防护和共享模板当前权限复核原本已存在。本轮不重建报表引擎，不修改 ISS-041/042/048/062/107 的业务规则。

确认的唯一真实缺陷是 `report_data` 的 CSV 请求在 DRF 识别为 `export` 动作时，显式检查了 `reports.export` 但未在函数内再次要求 `reports.view`；已最小补充查看权限检查，并新增 `export=true`、`view=false` 的 403 回归。真实端点生成的 CSV 含 UTF-8 BOM，客户名 `=2+2` 输出为 `'=2+2`；API 与 CSV 金额均为 145、单据数均为 2、数量分别为 `2.00 pcs / 3.00 box`。新增浏览器用例验证未提交客户筛选不进入 CSV 请求，真实 Chrome 16/16 通过。后端 863/863、Node 151/151、有效 Vitest 645/645、生产构建通过；完整索引见 [`ISS-019 CSV 准确性复核`](uat-evidence/iss-019-report-csv/README.md)。ISS-019 更新为 `FIXED_PENDING_REVIEW`，不关闭 Issue、不合并 master，等待独立复审。

GitHub CI run `40073371582` 在 frontend、backend、backend-postgres 三个 job 的可见 steps 前失败，保持为 CI/环境剩余风险，不将本地测试冒充 CI 或 PostgreSQL 通过。

## ISS-008 国家编码及模糊搜索选择框（2026-10-24）

基于统一基线 `af018ac63cf71143d223b9f6db4a087707495693` 创建独立 worktree 和 `codex/iss-008-country-select`。本轮先审查客户 `country/region` 字段、既有 ComboInput、报价编号/修订链和 `pycountry` 使用；没有新增迁移，也没有批量改写历史客户国家资料。

新增本地版本化 249 条 ISO 3166-1 目录、英文/中文/代码/简称搜索别名和歧义保护；客户交互式新建/编辑必须明确选择并保存 alpha-2，未知历史导入文本原样保留。客户列表显示和筛选兼容标准代码、旧文本和待确认历史值；新报价编号使用保存后的国家代码，历史报价编号和修订版不变。

后端 SQLite 全量 871 项（跳过 13）、ISS-008/导入/报价/客户回归 24 项、前端 Node 151 项、有效 Vitest 16 项、生产构建均通过。真实 Chrome 已完成客户桌面与 `390×844` 窄屏候选/保存/刷新回归，并检查报价列表和新建报价表单；截图及命令记录见 [`ISS-008 验收记录`](uat-evidence/iss-008-country-select/README.md)。本轮未执行 PostgreSQL/CI；直接未筛选 Vitest 入口存在仓库既有 node:test/jsdom 配置噪声，不纳入通过项。ISS-008 保持 `FIXED_PENDING_REVIEW`，等待统一独立代码、数据兼容、权限和视觉复审。

## ISS-027 跟进日期可选与旧计划保护（2026-10-26）

基于 `b3559f3bf83b967d06166bd409b00fc92e4e5902` 创建独立 worktree/分支 `codex/iss-027-followup-date`，读取桌面 2026-10-24 规则包原文。复用已存在的 keep/set/clear、日期可空和当前待办查询，仅修复分段日期非法输入仍能提交旧 modelValue，以及 keep 新增/编辑/删除重放历史安排覆盖客户当前计划的问题；无新增迁移、无批量改写数据。后端相关 79 项、前端有效 Vitest 30 项、Node 151 项、生产构建通过。ISS-049 URL筛选与员工数据范围回归保留。

Chrome Use 成功读取客户当前计划及默认 keep，但后续表单输入和截图在多个标签反复超时，桌面/390×844 截图与真实操作验收仍为 PENDING。用户要求仅用 Chrome Use 后未继续原生电脑控制。证据和真实测试日志见 [ISS-027](uat-evidence/iss-027-followup-date/README.md)。ISS-027 保持 NEEDS_VERIFICATION，状态计数不变；代码待独立审查，未关闭 Issue、未合并 master。

## ISS-024 / ISS-019 / ISS-008 统一集成验收（2026-10-25）

基于统一基线 `af018ac63cf71143d223b9f6db4a087707495693` 建立独立 worktree 和 `codex/integration-024-019-008`，按 ISS-024 → ISS-019 → ISS-008 顺序集成。ISS-008 原预期分支首次核验时不在 GitHub，已确认本地成果后推送并用 `git ls-remote` 核实 `a14d3d929e0c64dbb06d375d9a0ffa832526af92` 远端可见；旧 `fix/quote-country-iso-resolution` 未冒充本轮成果。三项实现、测试与历史证据均保留，未改写 0080–0084 迁移链；ISS-008 没有新增迁移。

集成只发生 `backend/crm/views.py` 与本阶段文档冲突，已保留客户级供应商偏好/停用过滤和本地国家目录两套逻辑，以及 ISS-019、ISS-008 两套阶段记录。全新 SQLite 迁移至 0084、已有库从 0082 升级至 0084、Django 全量 877 项（跳过 13）、前端 Node 151 项、有效 Vitest 74 项、生产构建和正确集成服务上的桌面/窄屏 Chrome 回归均通过。ISS-024 的供应商隔离与成本分配、ISS-019 的查看/导出权限和 CSV/API 对账、ISS-008 的国家代码/报价编号/历史快照兼容均由定向测试覆盖。集成分支最终 SHA 见交付报告；GitHub Actions run `40203282554` 的 backend、frontend、backend-postgres 均在可见 steps 前失败，记录为 CI/环境遗留风险，不将本地通过结果冒充 CI/PostgreSQL 通过。完整命令、文件和证据索引见 [`ISS-024/019/008 统一集成验收`](uat-evidence/integration-024-019-008/README.md)。三项保持 `FIXED_PENDING_REVIEW`，等待统一独立审查，不关闭 Issue、不合并 master。

## ISS-021 / ISS-029 / ISS-027 统一集成验收（2026-10-26）

基于统一基线 `b3559f3bf83b967d06166bd409b00fc92e4e5902` 创建独立 worktree 和 `codex/integration-021-029-027`，按 ISS-021 → ISS-029 → ISS-027 顺序集成已审查成果。`serializers.py` 同时保留数量变更的敏感字段保护和报价收件人快照继承；阶段文档冲突保留三项记录；ISS-021 的 0085 接续当前 0084，未复制旧迁移或改写已发布历史。

ISS-021 的正式 SO 数量、付款限制、采购保留、历史主体快照和资金/库存不变规则由全量及定向后端回归覆盖；ISS-029 的原始报价、修订收件人、空邮箱、PI 与 Excel 导出在真实 Chrome 和 API 中核对；ISS-027 在真实 Chrome 完成保存、改期、清除、非法日期、后端中断后的保存失败重试、客户列表同步以及桌面/390px窄屏截图。全量 Django 911（跳过13）、定向后端104、Node151、有效 Vitest656、生产构建、全新 SQLite 和 0084→0085 升级均通过。完整日志和截图见 [`ISS-021/029/027 统一集成验收`](uat-evidence/integration-021-029-027/README.md)。

本机 PostgreSQL 未执行，标记 `BLOCKED`；本地 GitHub token 当前无效，不能读取精确 HEAD CI，历史可核实 CI 仍为账户付款/Actions spending limit 阻断。本轮不修改账户、工作流或 master。三个任务保持 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立代码、权限、业务和视觉复审；不关闭 Issue。

## ISS-020 正式报价与 PI 导出一致性（2026-10-26）

基于 `28ba758388429f57c2e3516e12385a88ce6646a3` 创建独立 worktree/分支 `codex/iss-020-quote-export`，先读取 2026-10-24 规则包并审查报价导出 DTO、PI 预览、Excel 模板、ISS-029 收件人快照和 ISS-037 历史主体边界。先行复现确认两个真实问题：关键买方/币种缺失的已保存报价会错误返回 XLSX；逐行分币舍入后的正式文件小计可能与旧预览不一致。

最小修复集中在报价导出 DTO、PI data/export 错误响应和未保存编辑器金额展示：正式预览与 XLSX 共用保存版本校验、逐行金额舍入、运费/折扣/总额与英文金额大写；关键字段缺失返回 422 字段提示，不生成错误文件。未改报价核心查询引擎、金额业务计算、修订链、ISS-029 共享模板或 ISS-037 尚未决策的正式主体规则。

独立 SQLite/API 证据实际生成两个版本 XLSX，核对收件人、型号、数量、价格、币种、图片、金额大写和历史主档改动不覆盖；空邮箱保持空值。Django 全量 915（跳过13）、ISS-020/报价专项25、权限与跨客户定向2、Node151、有效 Vitest12 和生产构建通过。真实 Chrome Use 已完成保存修订版 PI 桌面及 390×844 窄屏预览；浏览器下载事件未在等待窗口返回，以 API 实际文件证据为准。推送后 CI run `40286651906` 的 frontend/backend/backend-postgres 均在可见 steps 前失败，未提供日志，不能视为通过。生产 PostgreSQL、代理、真实员工账号和 Excel 桌面打印未验证，证据及原始日志见 [`ISS-020 导出一致性`](uat-evidence/iss-020-quote-export/README.md)。

ISS-020 更新为 `FIXED_PENDING_REVIEW`，不关闭 Issue、不合并 master，等待统一独立代码、权限、文件和视觉审查。

## ISS-023 Sales Model 自动生成与人工设置（2026-10-26）

基于统一基线 `f12b591cb90d6a5d8ebfedf1c559703377c92d84` 创建独立 worktree 和分支 `codex/iss-023-sales-model`，读取用户 2026-10-24 规则包原文，并核对 ISS-087、ISS-035、ISS-020、ISS-037 的 SKU 身份、模板、报价快照和 PI/XLSX 现状。确认的唯一实际代码缺口是参数编辑会用新规则预览覆盖已保存的人工型号。

最小修补使后端只在保存值仍等于旧参数自动生成值时刷新型号；人工型号和明确空型号不被覆盖。前端提交保存型号，身份确认和组合预览继续显示保存值与当前规则预览的差异。未新增迁移、未批量重命名旧 SKU、未修改报价编号/修订链、正式单据快照或财务统计。后端 SKU 专项最终 31 项、Node 154 项、相关 Vitest 48 项、Django 全量 933 项（13 跳过，条件修补前全量）和生产构建通过；独立 SQLite 全新迁移及 `makemigrations --check` 通过。真实 Chrome 完成桌面人工型号保存、普通字段编辑保留型号和 `390×844` 窄屏回归，截图及测试日志见 [`ISS-023 验收记录`](uat-evidence/iss-023-sales-model/README.md)。

真实生产 SKU 主数据完整性、正式账号/数据库和部署环境仍需后续业务抽查及独立复审；本轮不关闭 Issue、不合并 `master`。

## ISS-051 开发与生产环境安全分离（2026-10-26）

基于统一基线 `28ba758388429f57c2e3516e12385a88ce6646a3` 创建独立 worktree 和 `codex/iss-051-environment-isolation`。读取 2026-10-24 规则包原文，审查 Django 配置、开发身份、数据库、RBAC、登录、媒体和 CI 配置；没有连接真实生产数据库、创建生产账号或写入真实密钥。

本轮最小修复使 `APP_STAGE`、DEBUG、secret、数据库、主机、来源、RBAC、媒体目录和 Cookie/HTTPS/HSTS 配置按环境隔离；生产启动拒绝不安全默认值，生产业务 API 使用 Session 认证，匿名受保护 API 返回 401，已登录无模块权限返回 403。开发身份仍统一复用 `development_superadmin_enabled()`，不修改开发账号或正式 RBAC 方案；ISS-017 私有附件继续使用既有授权入口。新增配置说明、环境占位样例和自动化测试，未新增迁移。

完整 Django 916 项（跳过 13）、安全定向 15 项、Node 151 项、有效 Vitest 656 项、生产构建、迁移检查以及 Chrome Use 桌面/`390×844` 窄屏只读回归通过；实现提交为 `d366224`，证据见 [`ISS-051 验收记录`](uat-evidence/iss-051-environment-isolation/README.md)。本分支 GitHub Actions run `40264628939` 的 backend、backend-postgres、frontend 均在可见 steps 前失败且无日志，记录为 CI/环境遗留风险，不把本地结果冒充 CI 通过。托管 Worktree 默认媒体目录存在 ACL 限制，完整测试改用临时 `MEDIA_ROOT` 通过，不属于应用失败。本机真实生产服务器、反向代理 HTTPS、PostgreSQL、Cookie、密钥轮换、实名创始合伙人账号和部署日志仍为 `DEPLOYMENT_VERIFICATION_PENDING`；ISS-051 保持 `BLOCKED`，等待 ChatGPT 独立代码、安全和部署复审。不合并 master，不关闭 Issue。

## ISS-022 采购 MOQ 软提醒与共享 PO 合计验收（2026-10-26）

基于统一基线 `28ba758388429f57c2e3516e12385a88ce6646a3` 创建独立 worktree/分支 `codex/iss-022-procurement-moq`，读取用户 2026-10-24 规则包原文。核实后直接将本地已验证提交 `6e7aaedd2cccef3150a5c7ee3135fd5f37dcee47` 集成到 `codex/integration-020-022-051`，没有使用落后的 `codex/r1-moq-02` 或重新开发 MOQ。独立分支的 GitHub 推送受 TLS/HTTP 传输故障阻断，未声称独立远端分支已交付。

新增接续 `0085` 的 `0086_purchase_moq_exception`，不复制、删除或改写既有迁移。草稿和计划按同供应商来源、同 SupplierSKU、基础单位合计；交易单位先换算，不自动补量；没有可靠 MOQ 不提示。低于 MOQ 仍可保存草稿，正式下单要求填写例外原因，采购单保存原因、明细快照、时间、采购单和已认证操作员；价格、内部参考成本、状态转换、ISS-024/ISS-039 采购来源与成本逻辑不变。

统一集成全量 Django `crm` 932 项（跳过 13）、MOQ/报价定向 82 项、Node 153 项、有效 Vitest 657 项、生产构建和真实 Chrome 均已执行；迁移额外验证了新库和 `0085→0087` 升级。完整命令、网络响应、隔离夹具及截图见 [`ISS-020 / ISS-022 / ISS-051 集成验收`](uat-evidence/integration-020-022-051/README.md)。本轮不合并 master、不关闭 Issue，ISS-022 保持 `FIXED_PENDING_REVIEW`，等待统一独立审查。

## ISS-043 重要业务操作日志防篡改（2026-10-26）

基于统一基线 `f12b591cb90d6a5d8ebfedf1c559703377c92d84` 创建独立 worktree 和 `codex/iss-043-audit-protection`，先读取 2026-10-24 规则包原文并复核 Phase4 `RISK-AUDIT-01`。基线的 API 只读和敏感快照脱敏已经存在，但复现确认 Django admin 仍有默认删除权限，OperationLog ORM 可通过实例/QuerySet 改删，且数据库没有 append-only 防护；非开发环境也可静默关闭审计写入。

本轮最小补修新增 OperationLog 实例与 QuerySet 追加写保护、admin 明确禁止新增/修改/删除、PostgreSQL 0088 触发器、0089 操作人 PROTECT 和非开发环境审计 fail-fast；保留开发超级管理员约定、ISS-021/ISS-026 历史操作、业务事务回滚和现有权限脱敏。新增 PostgreSQL 运行账号最小权限与独立维护 runbook，不执行真实生产授权，不引入外部审计平台。

SQLite 定向审计测试 8 项通过（其中 PostgreSQL 原始 SQL 保护 1 项因本机无 PostgreSQL 跳过），迁移至 0089、系统检查和迁移检查通过。真实生产 PostgreSQL 运行账号权限、角色继承、触发器现场验证、备份恢复及特殊维护演练为 `PENDING`；证据见 [`ISS-043 验收记录`](uat-evidence/iss-043-audit-protection/README.md)。本轮保持 ISS-043 `BLOCKED`，不关闭 Issue、不合并 master，等待部署证据和独立审查。

## ISS-043 / ISS-075 / ISS-023 统一集成验收（2026-10-26）

基于统一基线 `f12b591cb90d6a5d8ebfedf1c559703377c92d84` 创建独立 Worktree 和 `codex/integration-043-075-023`，按 ISS-043 → ISS-075 → ISS-023 顺序完整移交已审查提交：ISS-043 `dea057ce0c98fc32da44b72999beb4af78a58176`、ISS-075 `771307b19667256453c7c22ebf60256ffd2a26dd`、ISS-023 `c6a1415437fb2a020ec31d655fe8ce274aa93912`。没有整文件覆盖；`serializers.py` 和两份公共台账自动合并后逐段复核。0088 依赖 0087、0089 依赖 0088，迁移历史完整。

集成后 Django 定向 117（跳过1）及全量 940（跳过14）、Node 154、有效 Vitest 657、生产构建、SQLite 全新迁移、0087→0089 升级、`makemigrations --check` 和真实 Chrome 桌面/390×844 回归通过。Chrome 隔离数据核对了空付款阶段 PO、历史 500/500 付款计划、SKU 页面和窄屏菜单收起；控制台无 error/warning。证据见 [`ISS-043 / ISS-075 / ISS-023 统一集成验收`](uat-evidence/integration-043-075-023/README.md)。

本轮不关闭 Issue、不合并 master、不部署。延期台账仅更新原有 ISS-043、ISS-075、ISS-023：ISS-043 真实 PostgreSQL 与最终 CI 为 `DEPLOYMENT_VERIFICATION_PENDING`；ISS-075 真实业务财务数据的无付款阶段跨模块抽查为 `BUSINESS_VERIFICATION_PENDING`；ISS-023 真实 SKU 型号完整性抽查为 `BUSINESS_VERIFICATION_PENDING`。ISS-023 窄屏菜单可用性已通过，不作为遗留事项。三项等待统一独立审查。

## ISS-047 单服务器私有文件存储（2026-10-26）

基于统一基线 `8b2b5c19e517addd9604b239211e199a789b739e` 创建独立 Worktree 和 `codex/iss-047-private-storage`，读取用户 2026-10-24 规则包，并复核 ISS-017 私有附件、ISS-018 联合备份和 ISS-051 环境隔离约束。基线已有的认证媒体 API、记录/客户范围、旧 `/media/` 不可用、私有缓存头和 SKU 缩略图权限均保留，没有公开 `MEDIA_ROOT`。

本轮最小补修要求部署阶段显式注入绝对 `MEDIA_ROOT`；生产缺失、相对路径或与 `STATIC_ROOT` 重叠时 fail-fast。显式配置 `STORAGES["default"]`/`MEDIA_STORAGE_BACKEND` 保留未来对象存储迁移接缝；新增只读 `private_media_manifest` 管理命令，以相对路径、大小和 SHA256 支持 ISS-018 恢复核对，并拒绝媒体根目录外的符号链接。新增 Nginx 拒绝 `/media/` 静态直链的未部署样例和单服务器持久卷交接说明，不引入多服务器集群或真实备份任务。

定向附件权限回归基线 7 项通过；本轮新增私有媒体清单、重启模拟、配置隔离和数据库设置测试将在交付日志中记录，`python manage.py check`、Django 全量和生产构建随后执行。真实生产持久卷、服务重启、磁盘/inode 告警、Nginx/反向代理 ACL、PostgreSQL+媒体联合备份恢复和未来对象存储迁移均为 `DEPLOYMENT_VERIFICATION_PENDING`；证据见 [`ISS-047 验收记录`](uat-evidence/iss-047-private-storage/README.md) 和 [`单服务器私有文件存储交接说明`](deployment/ISS-047-单服务器私有文件存储.md)。本轮不部署、不合并 `master`、不关闭 Issue，等待独立审查。

## ISS-097 超级管理员权限显示一致性（2026-10-26）

基于 `8b2b5c19e517addd9604b239211e199a789b739e` 创建独立 Worktree 和 `codex/iss-097-admin-permissions`，读取 2026-10-24 规则包，并复核 ISS-003、ISS-043、ISS-051。确认历史 `superadmin` 保存模板的新增模块勾选不完整，但服务端有效权限规则对最高业务角色返回全部 ERP 模块；问题是页面把存储模板当成有效权限显示，而不是已确认的授权漏洞。

最小修复新增 API 的 `has_all_permissions` / `effective_permissions` 元数据，前端按有效矩阵呈现最高角色全部 24 个模块和六类动作，并明确显示“包含全部ERP业务权限，不受普通勾选项限制”。最高角色保持不可编辑；普通角色继续读取保存模板；没有新增迁移、补写权限行或改变 `development_superadmin_enabled()`、审计保护和正式 RBAC 规则。

隔离 SQLite 全新迁移至 `0089`，Django 权限专项 39 项、最高角色 API 定向 2 项、Node、有效 Vitest 658 项、生产构建和真实 Chrome 桌面核验通过。Chrome 实测页面为 24/24、全选、只读，API 实测有效矩阵 24 个模块；截图、原始命令和边界风险见 [`ISS-097 验收记录`](uat-evidence/iss-097-admin-permissions/README.md)。普通员工/销售员/采购员/财务员使用现有受限 RBAC 夹具核对，未扩大数据范围；真实员工会话、生产 PostgreSQL/基础设施权限仍保持 ISS-003/ISS-051 的原有待验收状态。

本轮不关闭 Issue、不合并 `master`、不部署，等待独立审查。

## ISS-018-FIX-01 备份文件访问控制与安全恢复（2026-10-27）

基于 `ad64eed9e00810beb2734e23f4e58cb6b4533bb8` 在独立 Worktree 创建 `codex/fix-iss018-backup-safety`。保留原 ISS-018 一致性契约和 SQLite/PostgreSQL fail-closed 边界，仅补现有安全缺口：POSIX 备份目录新建/显式收紧为 `0700`，备份及恢复文件为 `0600`；已有不安全目录默认拒绝；Windows 不把 `chmod` 当 ACL 证明，生产/预发布必须外部核验 NTFS ACL。

`restore_consistent_backup` 现在要求正式目标不存在，在同一文件系统的临时 staging 中完成解包、路径/CRC、数据库、媒体和配置核验后原子切换；非空或空目标都不删除、不写入。默认失败/成功结构化报告写到目标目录旁，显式 `--result-file` 可指定外部位置。新增回归覆盖非空目标内容和原 `restore-result.json` 不变、外部失败报告、磁盘写入失败无正式目标/残留 staging、篡改归档、路径穿越、权限和重试。目标策略从“新或空目录”收紧为“必须不存在”，已在运行手册和验收记录说明。

FIX-01 定向测试 `crm.tests.test_iss018_backup_recovery` 为 15 项通过、1 项平台条件跳过；最终 Django 全量 `965` 项通过、`16` 项跳过。生产 PostgreSQL、真实媒体卷、生产 POSIX/NTFS ACL、加密异地副本、定时器/告警、RPO/RTO 仍未连接或部署，ISS-018 继续保持 `BLOCKED` 和 `DEPLOYMENT_VERIFICATION_PENDING`。本轮不启用生产任务、不上传备份、不合并 `master`、不关闭 Issue，等待独立审查。

## ISS-018-FIX-02 恢复结果路径安全与备份目录检查（2026-10-27）

基于 `a73273f49aa32d8be8040d1c444045ff51a67c65` 在独立 Worktree 创建 `codex/fix-iss018-restore-edge-cases`。本轮按用户指定的已核实实现提交 `35c42fcef672d76e8ad9f27da650ae64ea3a3c02` 校正文档引用；不覆盖已发布迁移和其他 Issue 历史。

FIX-02 在解析前检查用户指定恢复报告路径的原始符号链接，拒绝报告指向恢复目标本身或其内部；默认报告继续位于目标目录外。恢复失败不会创建缺失目标，成功原子提交后将恢复结果和报告写入结果分别表达，报告写入失败不再把已完成的恢复伪装成 FAILED。备份清理对不存在、非目录或符号链接路径明确失败，默认 dry-run 和 7/4/3 保留策略保持不变。

定向回归 `crm.tests.test_iss018_backup_recovery` 22 项通过、3 项平台条件跳过；ISS-018/047/051 交叉回归 28 项通过、4 项平台条件跳过。`python manage.py check` 通过，`python manage.py makemigrations crm --check --dry-run` 无模型差异；本地已有 SQLite 文件访问 RuntimeWarning 不影响退出码。生产 PostgreSQL、私有媒体卷、POSIX/NTFS ACL、独立加密副本、定时器/告警和 RPO/RTO 仍为 `DEPLOYMENT_VERIFICATION_PENDING`，ISS-018 保持 `BLOCKED`。本轮不部署、不合并 `master`、不关闭 Issue，等待独立审查。

## ISS-080 客户联系人疑似重复提醒（2026-10-27）

基于 `8b2b5c19e517addd9604b239211e199a789b739e` 创建独立 Worktree 和分支 `codex/iss-080-contact-duplicates`，读取用户 2026-10-24 规则包原文，并复核联系人新增、编辑、搜索、分页及 ISS-025、ISS-027、ISS-029 相关规则。确认原有实现只对当前已加载的联系人列表计算提示，搜索、客户筛选或分页会遗漏同一客户的其他联系人。

本轮最小修复复用既有 `/contacts/?customer=<id>` 授权查询和 `listAll` 分页机制，在新建/编辑选择客户后获取该客户全部授权联系人；前端按邮箱、保留国际区号的电话、相同或明显相近姓名给出可解释原因，编辑排除自身，提供“查看联系人”入口，且提醒不阻断人工继续创建。不同客户不比较，不合并联系人，不改历史跟进或报价快照，不新增迁移；后端范围测试确认员工不能通过客户过滤泄露无权联系人。

Django `crm` 全量 942 项（跳过14）、定向后端2项、前端有效 Vitest 658 项、前端定向61项、生产构建、迁移检查、Playwright CRM 11/11，以及真实 Chrome Use 桌面和 `390×844` 窄屏验证均通过。Chrome Use 在搜索结果为空时仍显示同一客户全量联系人提示，并验证手动继续保存；完整命令和证据见 [`ISS-080 验收记录`](uat-evidence/iss-080-contact-duplicates/README.md)。托管 Worktree 默认 media 目录 ACL 不可写，完整测试使用临时 `MEDIA_ROOT`，应用无相关失败。实现提交为 `efb2546b69ae4ace60715dcb97803145248d3a1b`。

ISS-080 更新为 `FIXED_PENDING_REVIEW`，真实生产账号/数据库及跨员工真实业务数据抽查属于后续独立复审范围；不关闭 Issue、不合并 master、不修改其他工作树。

## ISS-047 / ISS-097 / ISS-080 统一集成验收（2026-10-27）

基于统一基线 `8b2b5c19e517addd9604b239211e199a789b739e` 创建独立 Worktree 和 `codex/integration-047-097-080`，按 ISS-047 → ISS-097 → ISS-080 顺序集成。ISS-080 仅移植功能提交 `efb2546b69ae4ace60715dcb97803145248d3a1b` 与证据/台账提交 `9fe9f479bc47fd7470c80822c89fa59d7d71cbf5`，未覆盖旧分支。冲突仅发生于公共阶段文档，已保留三项记录；0088/0089 迁移完整保留。

集成后 Django 全量 `950` 通过、`15` 跳过，定向三项后端 `59` 通过/`1` 跳过，Node `154`、有效 Vitest `659`、Playwright CRM/RBAC `27`、生产构建、SQLite 空库迁移和 0087→0089 升级均通过，`makemigrations --check` 无差异。真实 Chrome 已补充 ISS-080 桌面/390px 联系人提醒和 ISS-097 桌面/390px 权限矩阵独立图片。Vitest 中既有 `detail-drawer-typography.spec.js` 为 node:test 文件，已明确排除，不将错误 suite 运行结果冒充全量 Vitest 通过。

ISS-047 真实生产卷/Nginx/容量告警/联合备份恢复与 PostgreSQL、ISS-097 正式员工与生产会话、ISS-080 真实员工跨客户数据抽查均保留原记录的部署或业务待验状态。最终 HEAD 的 GitHub Actions 必须另行核对；测试步骤前失败时不标记 CI PASS。完整命令、冲突、截图和遗留事项见 [`ISS-047 / ISS-097 / ISS-080 统一集成验收`](uat-evidence/integration-047-097-080/README.md)。本轮未部署、未合并 master、未关闭 Issue，等待 ChatGPT 独立审查。

本轮 `npm install` 重新暴露依赖安全快照（2 moderate、9 high），沿用既有 ISS-002 记录为 `NEEDS_VERIFICATION`；未运行自动修复或无授权升级，不把该数量当作已确认生产漏洞。

## ISS-002 依赖安全审计（2026-10-27）

在独立 Worktree `codex/audit-iss002-dependency-security` 按基线 `46353a5436637832f5adadb7bdef6b45cdeada23` 完成前后端依赖审计。初始 npm 锁树的 11 个 advisory 已按直接/传递、生产/开发和源码实际路径拆分；axios、Vue、Vite、Vitest 及相关转依赖采用同大版本或补丁更新，最终 `npm audit` 和 `npm audit --omit=dev` 均为 0。Django/DRF 最低安全版本更新后，干净环境为 Django 6.0.9、DRF 3.18.3；Django 全量 984 通过、前端 Node 156 通过、有效 jsdom 定向 4 通过、生产构建通过。Pillow 11.3.0 的真实图片解析风险需跨重大版本，保留延期；Python lock、CI/PostgreSQL 和生产外部暴露仍未验证。完整 advisory、命令和关闭条件见 [`ISS-002 依赖安全审计`](uat-evidence/iss-002-dependency-audit/README.md)。本轮未触发 GitHub CI、未部署、未合并 master、未关闭 Issue。

## ISS-018 数据库与附件一致性备份恢复（2026-10-27）

基于统一基线 `7951ecb8c6196f773128ad5978bfcd0a5b30c6b5` 创建独立 Worktree 和 `codex/iss-018-backup-recovery`，先读取 2026-10-24 规则包，并复核 ISS-047 私有媒体 SHA256 清单、ISS-051 环境隔离和 ISS-043 审计备份边界。当前仓库没有生产 PostgreSQL、快照服务、Nginx 实例、systemd 定时器或独立异地存储，本轮没有连接或修改生产环境。

新增 `backup_recovery` 服务及 `create_consistent_backup`、`restore_consistent_backup`、`prune_erp_backups` 管理命令。备份不是把两份独立文件冒充快照：必须显式确认应用写入静默；SQLite 事务快照前后重新核对 ISS-047 媒体清单；数据库、媒体、恢复配置白名单和清单进入同一个 ZIP；恢复先核对归档 CRC、数据库 SHA256/`integrity_check`、媒体逐文件 SHA256 和配置 SHA256，全部通过后才写入新隔离目录。生产 PostgreSQL 未提供同一数据库/文件系统快照适配器时命令 fail-closed。age 加密、公网/异地复制、自动定时器和告警只提供未部署 runbook，不放入密钥或真实凭证。

定向测试 `crm.tests.test_iss018_backup_recovery` 7 项通过，ISS-018/047/051 交叉回归 27 项通过（1 项既有 symlink 条件跳过）；隔离管理命令实际运行并核对订单金额 `5000`、库存 `42`、附件 `followups/invoice.pdf` 及媒体 manifest SHA256；ISS-047 现有私有媒体权限/清单实现未被覆盖。实际生产 PostgreSQL、私有持久卷、独立加密副本、systemd/告警、恢复 RPO/RTO 和 ISS-043 生产审计备份仍为 `DEPLOYMENT_VERIFICATION_PENDING`；证据见 [`ISS-018 隔离演练`](uat-evidence/iss-018-backup-recovery/README.md) 和 [`ISS-018 运行手册`](deployment/ISS-018-数据库与附件一致性备份恢复.md)。功能提交为 `da2a0af54a69dbaeab5ffd4a44abb87d2d39740f`，本台账绑定提交随后生成；本轮不关闭 Issue、不合并 `master`、不部署，等待独立审查。

## ISS-036 尾箱、混装箱与最小计量单位（2026-10-27）

基于统一基线 `7951ecb8c6196f773128ad5978bfcd0a5b30c6b5` 创建独立 Worktree 和分支 `codex/iss-036-carton-units`，读取 2026-10-24 规则包原文，并复核 SKU 交易单位、采购数量、实际装箱、ISS-040 Packing List、ISS-022 MOQ 及 ISS-075 付款规则。确认的真实缺口是：实际装箱接口对已保存的明确不可拆分交易单位接受非法小数；旧的 `[object Object]` 风险在当前前端错误展开逻辑中未复现，但补充了回归测试。

最小修复仅在 `ShipmentPackageSerializer` 对同一 SKU 的一致、明确、不可拆分交易单位快照执行整数倍校验，返回自然中文原因；基础单位尾箱、合法混装、允许分数或缺失/冲突快照不凭空添加限制，不自动取整、不丢失输入，不修改 SO 数量、采购 MOQ、付款规则、Packing List 汇总或状态流转。新增后端专项和前端嵌套错误回归测试，未新增迁移。

Django 全量 `952` 通过、`15` 跳过；装箱/单位/包装/MOQ/集成定向 `92` 通过；有效 Vitest `660` 通过；实际装箱组件 `25` 通过；生产构建、SQLite 迁移至 `0089`、`makemigrations --check` 和真实 Chrome 非法/成功装箱回归通过。实际混装 XLSX 已生成并核对箱数、重量、CBM 只计一次；截图和原始日志见 [`ISS-036 验收记录`](uat-evidence/iss036/README.md)。实现提交为 `31b58cd9ca971ebe4183e378a1a82e517ac7c1fe`。

本轮只使用隔离 SQLite、开发身份和本地 Chrome；生产 PostgreSQL、生产代理、真实物流数据、CI 和窄屏物流实机尚未验证，登记为后续独立复审风险。ISS-036 保持 `FIXED_PENDING_REVIEW`，不合并 `master`、不关闭 Issue。

## ISS-036-FIX-02 不完整交易单位快照安全处理（2026-10-27）

基于 `codex/fix-iss036-factor-one` 的 `6db1ef53e4b78c20156e66071b37b7e6f29a6476` 创建独立 Worktree 和分支 `codex/fix-iss036-invalid-snapshot`。复现确认异常历史快照存在三种风险：有效与无法解析 factor 混合时可能错误执行不可拆分限制；factor 缺失会被默认成 1；非字典快照调用 `.get()` 可触发 HTTP 500。

最小修复要求快照为字典、factor 存在、可解析、有限且大于零；否则将对应 SKU 标记为 `ambiguous_indivisible`，不擅自推断不可拆分规则。保留 FIX-01 的 `factor=1` 修复、factor=5、允许分数、缺失交易单位和冲突快照语义；未修改库存、发货数量、订单金额、财务、采购、付款、尾箱、混装或 Packing List。

新增有效/非法混合、缺失 factor、非字典快照回归；后端相关定向测试 `99` 项通过，前端实际装箱测试 `26` 项通过，生产构建、Django check、`makemigrations --check` 和真实 Chrome factor=1 拒绝/成功回归通过。实现提交为 `f0c41d9e83ed7396686b0ec574eed0cdf1acd2be`，证据见 [`ISS-036-FIX-02 验收记录`](uat-evidence/iss036-fix02/README.md)。

本轮只使用隔离 SQLite、开发身份和本地 Chrome；生产 PostgreSQL、代理、真实物流数据、CI 和窄屏物流实机仍未验证。冲突快照的关闭条件是业务明确同一发货中同 SKU 多个历史交易单位快照的归属/优先级并提供可复核历史规则。ISS-036 保持 `FIXED_PENDING_REVIEW`，不合并 `master`、不关闭 Issue。

## ISS-036-FIX-01 不可拆分单位系数边界（2026-10-27）

基于源分支 `codex/iss-036-carton-units` 的 `3fe05aa1fe08f859cd6b737150d67b4c1066b248` 创建独立 Worktree 和分支 `codex/fix-iss036-factor-one`。复核确认原实现把明确 `factor=1`、`allow_fraction=false` 的交易单位当作歧义并跳过实际装箱整数倍校验；本轮仅移除该特殊跳过条件。

新增后端回归覆盖 `factor=1` 的 `0.5/1`、`factor=5` 的 `2.5/5`、允许分数、缺失快照和同 SKU 冲突快照；前端回归确认自然中文错误、无 `[object Object]` 且失败后输入保留。冲突快照仍不增加限制，关闭条件是业务明确同一发货中同 SKU 多个历史交易单位快照的归属/优先级，并提供可复核历史数据规则。未新增迁移，未修改库存、发货数量、财务金额、采购状态、付款规则、尾箱、混装或 Packing List。

相关后端定向测试 `96` 项通过，前端实际装箱组件 `26` 项通过，生产构建、Django system check 和 `makemigrations --check` 通过。真实 Chrome 已完成 `0.5` 拒绝并保留输入、`1` 保存成功的独立截图；实现提交为 `a59573e0396fbb6b324628d8826b5a2234ee065b`，完整证据见 [`ISS-036-FIX-01 验收记录`](uat-evidence/iss036-fix01/README.md)。

本轮只使用隔离 SQLite、开发身份和本地 Chrome；生产 PostgreSQL、代理、真实物流数据、CI 和窄屏物流实机仍未验证。ISS-036 保持 `FIXED_PENDING_REVIEW`，不合并 `master`、不关闭 Issue。

## ISS-025 客户生命周期中文名称一致性（2026-10-27）

基于统一基线 `7951ecb8c6196f773128ad5978bfcd0a5b30c6b5` 创建独立 Worktree 和分支 `codex/iss-025-customer-status-labels`，读取 2026-10-24 规则包原文，并核对客户列表、详情、筛选、跟进、报表及关联企业展示。基线问题仍可复现：列表使用“已联系”，详情使用“联系人”；返单客户也存在“公司客户”与“返单客户”的展示差异。

本轮以展示层最小修复统一客户生命周期展示映射，并在客户 API 提供 `status_display`。保留数据库原始状态代码、状态选项、迁移、自动推进规则、联系人数量规则、历史跟进/报价资料和筛选 URL 参数；`联系人` 仍只用于 Contact 业务实体。代码提交为 `a8dd277609d7364d301d1a330f717f00962d8619`，未新增迁移、未批量改写旧客户资料。

最终改动后定向后端 92 项通过，`makemigrations --check --dry-run` 无变化；Django `crm` 全量 952 项通过、15 项跳过；Node 154 项、有效 Vitest 659 项、前端生产构建通过。Chrome Use 已完成客户列表/详情、关联企业、跟进 URL 恢复和报表筛选的桌面与 `390×844` 窄屏检查，隔离 SQLite 样本证据见 [`ISS-025 验收记录`](uat-evidence/iss-025-customer-status-labels/README.md)。

ISS-025 原记录更新为 `FIXED_PENDING_REVIEW`，未创建重复 Issue。真实生产数据库、员工账号和全量业务数据抽查登记为 `BUSINESS_VERIFICATION_PENDING` / `DEPLOYMENT_VERIFICATION_PENDING`；本轮不合并 master、不关闭 Issue、不部署，等待独立代码、业务、权限和视觉复审。

## ISS-025-FIX-01 客户状态标签全页面一致性核查（2026-10-27）

基于源分支 `codex/iss-025-customer-status-labels` 的提交 `1fac93f09e3b5c578a030df5c0736e5d0552e4cc` 创建独立 Worktree 和分支 `codex/review-iss025-status-consistency`。本轮逐项核对客户列表、状态筛选、详情、联系人关联企业、跟进筛选、报表/经营分析、API `status/status_display` 以及刷新、分页和 URL 恢复；未重复修改已经正确的页面。

核查发现经营分析按客户生命周期分组仍直接使用模型旧文案，`contact`/`company` 会显示“联系人”/“公司客户”。在 `backend/crm/reporting.py` 中仅对客户来源的状态标签复用现有 `customer_status_display()`，并补充后端报表断言及前端映射测试。修补提交为 `20981f91de0a30a9bc3ba0ccd603233d36457f42`；未新增迁移、未改状态编码、自动推进、联系人数量规则或历史数据。

Django `crm` 全量 953 项通过、15 项跳过；Node 156 项、有效 Vitest 659 项、生产构建、`makemigrations --check --dry-run` 和 `git diff --check` 通过。真实 Chrome Use 已完成桌面及 `390×844` 窄屏检查，隔离 SQLite 样本覆盖五种状态、客户筛选、详情、关联企业、跟进 URL 恢复和报表结果。完整证据见 [`ISS-025-FIX-01 全页面核查`](uat-evidence/review-iss025-status-consistency/README.md)。

ISS-025 原记录已更新，没有创建重复 Issue。其他状态名称简化登记为 `BUSINESS_VERIFICATION_PENDING`；真实生产数据库、真实员工权限和全量业务数据抽查保留 `BUSINESS_VERIFICATION_PENDING` / `DEPLOYMENT_VERIFICATION_PENDING`。本轮不合并 master、不关闭 Issue、不部署，等待独立代码、业务和视觉复审。

## ISS-025-FIX-02 客户状态报表视觉证据补齐（2026-10-27）

基于已审查提交 `d5d0d15c03d55a718f11a298e08f29a9b9d0c4b0` 使用独立 Worktree 和分支 `codex/iss025-report-visual-evidence`。本轮不修改报表逻辑、客户状态编码、销售/采购/财务报表状态名称或权限，仅补齐经营分析客户按状态分组的真实浏览器视觉证据。

全新隔离 SQLite 创建 5 条唯一客户样本，覆盖 `lead/contact/opportunity/customer/company`，查询 `2026-10-01` 至 `2026-10-31`，API 返回 5 行且每行数量为 1；五个中文标签与编码一一对应。真实 Chrome 默认桌面视口及 `390×844` 窄屏均核验通过；报表区域无“联系人”“公司客户”旧生命周期标签。窄屏实测页面 `scrollWidth=375`、可用宽度 375，无页面级横向溢出；结果表两列 `scrollWidth=clientWidth=313`，状态标签未被遮挡。补跑 ISS-025/报表 Django 定向测试 36 项、Node 156 项和生产构建均通过；两张本轮直接生成的截图见 [`ISS-025-FIX-02 证据`](uat-evidence/review-iss025-status-consistency/README.md)。证据提交为 `f9e2c7493ba86007fb6969d826d336dc4077edb7`。

本轮仅执行全新 SQLite 迁移、本地 Django API 和 Vite/真实 Chrome 回归，未触发 GitHub CI、未连接生产数据库、未合并 master、未关闭 Issue、未部署。ISS-025 继续保持 `FIXED_PENDING_REVIEW`，真实生产数据库、真实员工权限、全量业务数据和独立视觉复审仍按原台账等待后续核验。

## INTEGRATION-018-036-025 统一集成验收（2026-10-27）

基于统一基线 `7951ecb8c6196f773128ad5978bfcd0a5b30c6b5` 创建独立 Worktree 和 `codex/integration-018-036-025`，按 ISS-018 → ISS-036 → ISS-025 顺序集成。三条来源 HEAD 均已核实为集成分支祖先；ISS-018 的备份/恢复报告路径安全、ISS-036 的不可拆分单位与异常快照校验、ISS-025 的状态映射和报表视觉证据均保留。`serializers.py` 自动合并后复核两项逻辑同时存在。

公共 `PROJECT_PHASES.md` 在两次合并中发生冲突，均以保留双方完整历史记录方式解决；`PROJECT_ISSUES.md` 和各任务证据目录未被覆盖。集成提交为 `b58af55`、`47c97d8`、`ef9b457`，均带 `[skip ci]`。没有新增迁移。

本地后端定向 60 项通过、3 项跳过；临时 `MEDIA_ROOT` 下 Django `crm` 全量 984 项通过、18 项跳过；Django check、迁移一致性检查、Node 156 项、有效 Vitest 661 项、前端生产构建均通过。默认 Worktree media ACL 首次全量运行有 1 个附件写入环境错误，已用隔离临时目录重跑通过；首次缺依赖和未指定 jsdom 的失败均已记录，不作为代码回归。截图沿用来源证据路径，未新增浏览器实测。

ISS-018 保持 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING`；ISS-036 的冲突历史快照业务待确认项保留；ISS-025 保持 `FIXED_PENDING_REVIEW` 及真实员工/生产数据待验。完整命令、冲突、截图路径和延期事项见 [`INTEGRATION-018-036-025 验收记录`](uat-evidence/integration-018-036-025/README.md)。本轮不触发 GitHub CI、不合并 `master`、不关闭 Issue、不部署，等待统一独立审查。

## ISS-036-FIX-03 历史交易单位快照语义冲突（2026-10-27）

基于统一集成基线 `46353a5436637832f5adadb7bdef6b45cdeada23` 创建独立 Worktree 和分支 `codex/fix-iss036-snapshot-conflicts`。复核 `TradeUnitLine`、`SKUTradeUnit`、`normalize_trade` 与 `ShipmentPackageSerializer.validate` 后确认，原实现只比较历史快照 `factor`，同 factor 但 `base_unit`、`unit` 或 `allow_fraction` 不同的历史语义会被错误视为一致。

本轮最小修复以 `factor`、`base_unit`、`unit`、`allow_fraction` 组成完整语义键；展示用 `name` 不参与语义比较，供应商/启用/默认/备注字段不在该历史快照中，也不影响单位换算或可拆分判断。缺失、非字典、单位字段无效或 factor 无效的快照继续按歧义处理；语义冲突不选择快照、不推断优先级、不增加不可拆分限制。完全一致的有效快照仍执行限制，`factor=1`、合法尾箱、混装及允许分数保持原规则。未修改库存、发货数量、采购、财务金额、付款规则或历史数据，未新增迁移。

新增相同 factor 的 base unit、交易单位和允许分数语义冲突回归，并验证完全一致快照（仅名称不同）仍拒绝非法分数；既有不同 factor、缺失/非字典/非法 factor、factor=1、factor=5、尾箱、混装和允许分数回归继续保留。后端装箱定向测试 39 项通过，交易单位交叉回归共 55 项通过；Django check、迁移检查、Node 156 项、交易单位 Vitest 4 项、生产构建及 `git diff --check` 均通过。Vite 首次非提升权限运行因 Worktree 临时目录 EPERM 失败，权限重试通过；本轮未运行 GitHub CI，未连接生产 PostgreSQL 或部署。完整命令见 [`ISS-036-FIX-03 验收记录`](uat-evidence/iss036-fix03/README.md)。

ISS-036 保持 `FIXED_PENDING_REVIEW`；冲突历史快照的业务归属/优先级仍待业务明确。ISS-018 最近核实引用修正为集成验证 HEAD `46353a5436637832f5adadb7bdef6b45cdeada23`，其 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING` 状态不变。

## R1-REPAIR-CONSOLIDATION-01 统一集成验收（2026-10-28）

以固定基线 `054bd82518039a5bc0e0c14234964a14d7fbbfd8` 创建全新独立 worktree 和分支 `codex/integration-r1-repairs-20261028`。集成前核实并按指定精确 SHA 合并：R1-REPAIR-03 `c3739e77562c5dd8995228d5c3e7375a6728d316`、R1-REPAIR-04-FIX-01 `e20f8a7bc506c299644b6c828c9b5574ee688f46`、R1-REPAIR-05 `9c5f1f821cfc1b436f5fffe0b681991fa056b34d`、R1-REPAIR-06-FIX-01 `5ad252c537dfb0b3f95150e76e471c9fe3fd0a99`、R1-REPAIR-07 `58541e94918e2d912c2b75d2371a8d625e1fc9d4`、final-cross-module-ux `45df13b8fd229427229a58d64d0ae2bec30a00cb`、supplier-purchase-ux-r2 `64fb397aa065062e192ceb30040421f59b63a08c`。七个 non-ff 合并均无文本冲突，逐项复核差异和业务断言；来源均无 migration 文件，集成后迁移检查通过。

另审查与 R2 无祖先关系的供应商分支 `codex/repair-supplier-purchase-ux-20261028` / `fe1cc16c3950e256fa564ea4508e08414ae8810b`。只将其 ISS-075 测试中两条外部 Google Fonts 路由拦截保留到 R2 版测试；没有删改规则断言，没有合并其余提交。集成调整仅为在 R1-06 隔离运行器允许列表中安全准备既有合成测试 fixture，以及把证据输出导入本轮目录；未修改产品业务代码、正式财务/采购语义或共享权限设置。

综合回归：Django system check 和 migrations check 通过；Django 全量发现 1,000 项、982 通过、18 按套件标记跳过、0 失败；隔离 runtime 10/10；Node 169/169；Vitest 66 文件/657 项；trade-unit 4/4；Typography Node 1/1；隔离 runner 自测 13/13；Playwright 隔离冒烟 1/1；完整可运行 Playwright 31 个 spec、189 项通过、0 失败。ISS-055 真实员工/RBAC 浏览器 spec 因不得启用正式 RBAC 而未运行，保留后续授权环境补验。构建通过，主 JS 为 1,126.05 kB、gzip 393.59 kB，Vite 大 chunk 警告仍存在；本轮没有声称实际用户性能改善。首次 Vitest 错误扫描范围、Django 继承到 `AUDIT_LOG_ENABLED=0` 的环境失败以及后续正确范围/干净隔离环境重跑均保留原始日志，详见[集成报告](uat-evidence/integration-r1-repairs-20261028/README.md)。

真实 Chrome/Chromium 截图、隔离 API fixture、XLSX/API 核对和原始测试日志已归档；证据总计 79 个截图/诊断文件（51 PNG、25 JSON、3 XLSX）。ISS-022、ISS-029、ISS-055、ISS-075 均保持 `FIXED_PENDING_REVIEW`；ISS-041 仍为 `Enhancement / BLOCKED（延期）`；ISS-002 的 Pillow 11.3.0/依赖锁定风险、ISS-003 的真实员工与 RBAC 验收、ISS-052 的审计身份/行级审计缺口、ISS-058 的真实用户性能测量均未被本轮宣称解决。

没有触发或重试 GitHub Actions；本地结果不代替 CI。11 月 1 日仅对推送后的精确最终 SHA 核对 `backend`、`backend-postgres`、`frontend` 三个既有 job，并保留运行链接/状态和外部启动错误。未合并 master、未部署、未启用正式 RBAC、未操作实际业务数据库、未关闭 Issue。来源验收及本轮日志/截图索引见[验收索引](uat-evidence/INDEX.md)。

## R1-STATUS-RECONCILE-01 状态对账（2026-10-28）

基于固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` 创建独立 worktree 和分支 `codex/reconcile-issue-ledger-20261028`。读取用户提供的 Excel 工作簿 `SUNJACK-ERP_Issue修复状态校准与下一轮计划_2026-10-28.xlsx`，并对照当前 `PROJECT_ISSUES.md`、本文件、`REVIEW_PROTOCOL.md`、实际分支 HEAD 和验收报告，逐项核对 124 个 Issue（含 `ISS-008-FUP-01`）及 46 条业务规则。

本轮只修改状态台账、阶段记录和 `AGENTS.md` 协作规则，未修改产品业务代码、模型、迁移、前端或部署配置。规范状态从固定基线归一化的 OPEN 4、BLOCKED 20、NEEDS_VERIFICATION 17、FIXED_PENDING_REVIEW 73、CLOSED 10 校准为 OPEN 2、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 78、CLOSED 10。实际状态变化仅为 ISS-024、ISS-040、ISS-042、ISS-048、ISS-052、ISS-062；旧状态、旧失败和历史验收结论在对账报告中保留。

ISS-042 团队共享模板基础版和 ISS-048 财务可靠指标下钻分别记录为阶段成果可封版并进入 `FIXED_PENDING_REVIEW`，不代表整体 `CLOSED`。ISS-040 的 Packing List 导出保留实现成果，但原生 Excel Print Preview 仍 PENDING。ISS-024 从滞后 OPEN 校准为 `FIXED_PENDING_REVIEW`。ISS-062 的日期窗口实现已有证据，但业务日期口径仍未确认，改为 `P2 / BLOCKED`。ISS-006、ISS-007、ISS-028、ISS-035、ISS-055、ISS-074、ISS-105、ISS-114 等重点项只补足精确 SHA 和证据边界，不因旧报告、未执行项或本地回归自动关闭。

逐项旧状态、新状态、校准依据、SHA、46 条规则摘要及未执行/业务阻断清单见 [R1 状态对账报告](uat-evidence/r1-status-reconcile-20261028/README.md)。本轮未连接生产数据库、未执行 PostgreSQL、未触发 GitHub Actions、未合并 master、未部署、未关闭 Issue。

## R1-ISS006 并发测试夹具补修（2026-10-31）

在现有独立工作树和分支 `codex/r1-iss006-po-locking-bd324-20261030`（用户指定基线 `94402f951e4d4243276f018cc3a6051f0f6f2c57`）只修正 `backend/crm/tests/test_postgres_concurrency.py`：移除两个采购收货并发场景中重复插入的默认成本分配，并增加一条且归属/数量正确的断言。`backend/crm/services/fulfillment.py` 等生产业务代码未改。

锁定依赖下，一次性 SQLite 定向回归 74 项：61 通过、13 个 PostgreSQL 专项跳过、0 失败；库存预留、采购收货、冲销、库存流水及成本分配相关可执行测试通过。原始日志和夹具修复细节见 [`C-po-locking 验收记录`](uat-evidence/r1-five-fixes-migration-20261030/C-po-locking/README.md)。本机未发现 PostgreSQL 工具/服务或 Docker，`127.0.0.1:5432` 不可连接；因此两个新并发用例的实际执行、锁顺序与最终采购/库存/流水/预留一致性仍为 `BLOCKED`，不可把 SQLite skip 视为 PASS。ISS-006 保持 `NEEDS_VERIFICATION`；解除条件为在 PostgreSQL 环境运行两个目标用例并审查一致性断言。本轮不触发 CI、不合并 master、不关闭 Issue。

## R1-ISS006-INVENTORY-REVERSAL-AUDIT-ATOMICITY（2026-10-30）

基于 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 创建独立工作树和分支 `codex/r1-iss006-inventory-reversal-audit-atomicity-20261030`。来源为用户指定的 2026-10-30 ChatGPT 独立代码审查；未猜测更早的首次发现日期。确认发货冲销服务提交后才写审计、手工库存冲销服务提交后才写两条审计的事务缺口。仅为两个 API action 加外层事务；既有冲销业务规则、接口响应、权限和幂等行为不变。

锁定依赖环境下，隔离内存 SQLite Django system check 通过；相关库存/履约定向 106 项全通过。销售发货正常/重复冲销、发货审计失败回滚、手工库存正常/重复冲销、手工冲销第一条与第二条审计故障注入均已验证。原始日志及报告见 [`R1-ISS006 冲销审计原子性`](uat-evidence/r1-iss006-reversal-audit-atomicity-20261030/README.md)。SQLite 结果不代表 PostgreSQL 并发验收；本轮未运行 CI、未合并 master、未创建 PR、未部署、未关闭 Issue。

本问题属于既有 ISS-006 的库存冲销原子性范围，不新增 Issue ID；ISS-006 全局保持 `NEEDS_VERIFICATION`，本子范围 `FIXED_PENDING_REVIEW`，交付后等待独立审查。

## R1-ISS007-FOLLOWUP-ATTACHMENT-UAT（2026-10-31）

从固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 创建独立 Worktree/分支 `codex/r1-iss007-followup-files-uat-20261031`。使用全新 SQLite、独立临时媒体目录、合成客户/历史附件及普通非超级用户测试身份；只在测试服务器启用 RBAC 和审计，不改开发人员权限或生产配置。

真实 Chrome 156 桌面 1440×900 和窄屏 390×844 完成上传、保存、刷新重开、文本预览、二进制下载、有效历史附件、直链授权/拒绝及路径/DB/操作日志核对。发现 UTF-8 纯文本响应没有 charset，导致真实中文预览乱码；已最小修复受保护文件响应头，并增加中文内容、字节和响应头回归。Django 相关 6 项、附件 Vitest 12 项、生产构建及新库迁移检查通过。HTTP：上传 201；授权文件 200；匿名 403；认证无权限 404；旧 `/media/` 404。证据、截图、命令、SHA256 和首次失败分类见 [R1-ISS007 附件 UAT](uat-evidence/r1-iss007-followup-files-uat-20261031/README.md)。

删除/替换步骤未执行，等待用户对一次性合成文件 `ISS007-delete-target.txt` 当次确认；状态因此仍为 `NEEDS_VERIFICATION`，ISS-007 未关闭。生产代理/CDN/对象存储 ACL 不在本地 UAT 可证明范围，继续按 ISS-017 单独部署验收。本轮未连接生产库/媒体、未运行 PostgreSQL/CI、未合并 master、未部署。

## R1-ISS007-ATTACHMENT-DELETE-UAT（2026-11-01）

后续收到用户明确授权后，在全新一次性 SQLite 和隔离 `MEDIA_ROOT` 中重新建立合成客户、跟进及普通非超级用户测试账号；没有复用或删除真实历史附件。只通过真实 Chrome 删除本轮专门创建的 `ISS007-delete-target.txt`，取消确认路径先验证仍保留；确认后 DELETE 204，目标数据库记录与文件均消失，旧私有 URL 返回 404。删除审计保留隔离认证操作人的用户外键、`DELETE` 路径及附件 ID/文件名。随后上传独立替代附件 201，桌面 1440×900 和 390×844 窄屏刷新后均可见；原有三份合成附件的 ID、路径、DB/磁盘大小及 SHA256 完全不变。证据提交 `9a4d70e1425928358be7001ece43327c00557b0c`；Python 锁定环境检查、迁移、Django 定向测试、Node 语法和浏览器 UAT 日志/截图见 [ISS-007 验收报告](uat-evidence/r1-iss007-followup-files-uat-20261031/README.md)。没有发现新的产品缺陷，未触发 CI、未部署、未连接生产数据或清理其他媒体目录。ISS-007 保持 `NEEDS_VERIFICATION`，等待独立复审；真实反向代理/对象存储 ACL 仍按 ISS-017 单独验收，Issue 状态计数不变。

## R1-ISS007-SKU-QUOTE-IMAGE-UAT（2026-10-31 至 2026-11-01）

基于固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 建立独立 worktree 和 `codex/r1-iss007-image-snapshot-uat-20261031`。使用本机真实 Google Chrome、隔离 SQLite、专属临时 `MEDIA_ROOT` 和合成客户/SKU/报价/订单；没有接触真实历史 SKU、报价或订单，也未改产品业务代码。

1440×1000 与 390×844 浏览器流程验证 SKU 图片上传/缩略图、替换及原图身份，非法图片 HTTP 400 且现有 SKU 图片不变；已接受报价的历史图快照在 SKU 替换后保持 SHA 不变。报价工作台导出的实际 XLSX 可打开，PI 工作表内嵌图片 SHA 与历史快照一致。确认订单仍关联已接受报价，关联报价快照保持不变；`OrderItem` 没有独立图片快照字段，因此没有把此结果表述为订单行另存图片。缺失历史图片 API 返回 404，预览仍可渲染且没有 JS 异常，但可见浏览器默认破图占位。定向 RBAC 测试通过：授权路径可读，SKU-only/客户范围不足的历史图片请求返回 404。Django 9/9、Node 隔离运行器 14/14、锁定依赖 `pip check` 通过；具体测试日志、DB 前后快照、XLSX 和八张桌面/窄屏截图见 [R1-ISS007 UAT 报告](uat-evidence/iss-007-image-snapshot-uat-20261031/README.md)。

ISS-007 保持 `NEEDS_VERIFICATION` 并等待独立审查；跟进附件等其他文件类型及生产反向代理/持久卷或对象存储 ACL 不在本轮结论内，部署验证沿用 ISS-017 边界。本轮未触发 GitHub Actions、未创建 PR、未合并 master、未部署、未启用正式 RBAC、未关闭 Issue。

## R1-ISS-008-FUP-01 国家中文名称与别名补齐（2026-10-31）

以指定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 创建独立 worktree 和分支 `codex/r1-iss008-aliases-bd324-20261031`。对照历史成果 `80dc73ae4ae47f9e04969f39b441af206d34306b`，逐文件确认国家注册表、249 项 Django 覆盖测试、国家选择器 Vitest 和既有 Chrome 场景已经存在于新基线且相关差异一致；没有业务代码需要迁移。只扩展 `frontend/browser-tests/iss008-chinese-aliases.spec.js`，增加编辑客户国家、保存 alpha-2 `HK`、刷新后重新打开确认标准显示的回归；测试提交为 `dba4a81c10a464012aa004a539a16378f7517b0e`。

项目锁定依赖下，Django 国家选择专项 11/11 通过（含 249 条逐项子测试），Vitest 4/4 通过，真实 Chrome 桌面 1440×844 与 390×844 回归 2/2 通过。Chrome 覆盖编辑中文选择/保存/刷新回显、客户新建国家选择和报价客户选择；截图及原始日志见[验收记录](uat-evidence/r1-iss008-aliases-bd324-20261031/README.md)。逐张目视检查了编辑、新建和报价页面；窄屏表单可滚动、无横向溢出，保存操作可用。

后端注册表、历史客户数据、alpha-2/alpha-3 对照、报价编号和数据库迁移均未修改；`America` 仍需用户明确选择，未知旧国家文字保留供人工确认。使用隔离内存 SQLite 与合成浏览器 API fixture；未连接生产数据库、未运行 PostgreSQL/全量套件/生产构建或 GitHub CI。ISS-008-FUP-01 更新为 `FIXED_PENDING_REVIEW`，等候独立复核；不关闭 Issue、不合并 master。

## R1-ISS006-POSTGRES-CONCURRENCY-GAPS（2026-11-01）

基于 `7402ad38cf40d1eea0adb076e67021c31be8ac1e`，在独立 worktree/分支 `codex/r1-iss006-postgres-concurrency-gaps-20261101` 补齐 PostgreSQL TransactionTestCase：同收货重复冲销、同幂等键收货、同明细合法部分收货和超额竞争；既有收货/冲销竞争增强 API 审计、认证操作人及状态快照校验。工作线程独立连接/Barrier/超时，新增场景验证 PostgreSQL backend PID 不同。未改业务代码或迁移。

静态语法、Django check 和禁止连接数据库的测试发现通过（24 项发现、0 项执行）。本机 PostgreSQL/Docker 缺失，真实锁、最终库存/预留/流水/操作日志及事务清理验证保留 `BLOCKED`。静态发现基线 0094 的审计 TRUNCATE 触发器与 TransactionTestCase flush 的潜在冲突，后续须在专用 PostgreSQL 测试库核实；本轮未绕过保护。完整命令和限制见[本轮报告](uat-evidence/r1-iss006-postgres-concurrency-gaps-20261101/README.md)。ISS-006 仍 `NEEDS_VERIFICATION`，未关闭，未触发 CI、未合并 master、未部署。

## R1-ISS006-POSTGRES-CONCURRENCY-REVIEW-FIX-01（2026-11-02）

沿用原独立分支，从 `657a65c10e0234345a2c648998f6d283c500d1b4` 修正四个并发用例的最终采购明细读取：工作线程完成后刷新对象再断言数量。加强失败请求幂等、库存流水和审计无残留检查；独立 PostgreSQL 连接/PID、Barrier、Future 传播机制保留。未改生产代码、模型、迁移或 ISS-052 审计保护。

隔离 SQLite 相关回归 64 通过、17 个 PostgreSQL 专项跳过，0 失败；语法、Django system check、静态导入/发现及 diff 检查通过，详见[原验收报告补修节及完整日志](uat-evidence/r1-iss006-postgres-concurrency-gaps-20261101/README.md)。PostgreSQL 实际执行仍 `BLOCKED`；数据库清理问题留待集成 `R1-POSTGRES-TEST-ISOLATION-01`。本轮断言补修待独立审查，ISS-006 状态仍 `NEEDS_VERIFICATION`。提交含 `[skip ci]`，不触发 CI、不创建 PR、不合并 master、不部署。

## R1-POSTGRES-TEST-ISOLATION-01（2026-11-02）

从指定 `2e25b743884123d7ae5599c89586988a12791bf4` 创建独立 worktree/分支 `codex/r1-postgres-test-isolation-20261102`。完成锁定版 Django 6.0.9 flush/建库/销毁机制审查，新增仅供 runner 新建随机临时 PostgreSQL 库使用的 teardown 清理机制；独占锁覆盖指定触发器临时启停和恢复，事务失败回滚，普通 flush 和测试正文不启用。追加建库/销毁归属、连接覆盖拒绝、失败配置恢复及剩余库显式报告；多别名/镜像/并行/已有库复用等未验证组合明确拒绝。未修改生产逻辑、模型、迁移、配置或工作流，0094 审计保护保持原样。

锁定依赖 16 项精确匹配；相关 SQLite 综合回归 113 通过、24 个 PostgreSQL 专项跳过（总 137），0 失败；语法、Django system check、迁移检查及禁止数据库连接的静态导入发现通过。完整报告和原始日志见[本轮验收](uat-evidence/r1-postgres-test-isolation-20261102/README.md)。本机无 PostgreSQL，真实 SQL/DDL 回滚/锁和清理后的保护均未实测，仍为 `BLOCKED`，不能声称彻底解决冲突；下一步在专用本地 PostgreSQL 验证本轮六项生命周期回归及原 ISS-006/052 专项，再作全量 PostgreSQL 回归与独立审查。ISS-006/052 状态和历史保留，不关闭 Issue；提交含 `[skip ci]`，未触发 CI、创建 PR、合并或部署。

## R1-POSTGRES-SUPPLIER-FIXTURES-FULL-01（2026-11-02）

基于 `codex/r1-postgres-test-isolation-20261102` 的 `9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2` 创建独立分支 `codex/r1-postgres-supplier-fixtures-full-20261102`。移植此前已审查的六文件测试夹具修复（代码变更来源 `e8e5d1199067a339d9cf6719310c9b32294b44f1`；用户提供的 `e2e7e017` 为后续文档提交），并将 `test_fulfillment_audit_atomicity.py`、`test_iss006_pre_uat.py` 中的供应商编码缩至两字符。全面搜索另发现 ISS-006 浏览器 seeder 生成超长编码，已改为散列起点加数据库查重的两字符未占用编码选择，不截断、不复用。生产 `Supplier.code(max_length=2, unique=True)`、业务逻辑和数据库迁移均未修改。

AST 审计 backend 测试文件及浏览器 seeder 共 92 个 Supplier 创建/获取调用点，另检查一个前端 Supplier API mock：0 个超长静态编码，3 个动态表达式逐一核验为两字符且符合场景唯一性。隔离 SQLite 定向回归 67/67 通过；`sku-management.spec.js` Vitest 9/9 通过；Django system check、AST 语法检查及 `git diff --check` 通过。Vitest 本机现存版本 4.1.11，仓库锁定 4.1.12，本轮未重装依赖。完整范围、命令和验收结果见[独立报告](uat-evidence/r1-postgres-supplier-fixtures-full-20261102/README.md)。未运行 PostgreSQL/CI；不将 SQLite 结果表述为 PostgreSQL 验收。Issue 全局状态不变，未创建 PR、未合并 master、未部署。

### REVIEW-INTEGRATION-BATCH-01 早期阶段原文留档

> ## REVIEW-INTEGRATION-BATCH-01（2026-11-04，进行中）

>

> 沿用远端已核实 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`，其CI 41782956426三项成功；保留预检、备份及0096/0097汇合迁移。本轮推进全量Issue证据归一化、集中独立复审包、合成核心闭环和失败原子性测试，见[专属报告](uat-evidence/review-integration-batch-20261104/README.md)。新增附件故障注入已复现ISS-007失败一致性缺口，修前结果保留；修复/新测试不以基线CI冒充通过。

>

> 财务、历史、运维来源尚未交付完整稳定SHA时不按移动HEAD合并。运维5d13f33明确为阶段性成果，不作为完整交付。打印完整验收和分页改进按来源对话中用户明确指令延期，ISS-037其余范围不延期；有效成果保留等待稳定交接。新增核心工作区UX包负责相关前端页面，本包不同时修改其页面。最终集成需对同一最终SHA重新核实三项CI及实际执行的专项，仍待ChatGPT集中独立复审。

## LOCAL-RELEASE-VALIDATION-03（2026-11-05，进行中）

沿用统一分支，基线 `bcdcb57545f121b8a4102f352c74008b47372035`；新测试约定记录在 `AGENTS.md`。历史来源长度缺口在合成 SQLite 重现并最小修复，PG17 专项55项及含历史/财务新表的备份恢复通过；运维稳定来源 `250c3b7f55585acccb73b2efc1b0993605be0b0b` 已合入。87 项复审索引及测试入口见[专属报告](uat-evidence/local-release-validation-20261105/README.md)。以上均不替代稳定来源全部整合后的完整回归。

导出稳定来源已完整合入；最终同候选本地全量正在执行，逐项独立复审仍待完成；旧前端262/1失败和本轮候选浏览器超时保留。真实 Linux 跨 UID 及目标环境门槛、用户延期打印、正式 RBAC/上线授权继续分开记录。日常 CI 为 NOT_RUN，不运行或重跑 Actions，不关闭 Issue。

用户转述 ChatGPT 对导出及运维来源的有限复审：财务概览错误状态、期间捕获及防重复提交补修合理；导出来源本次 266/266 不消除旧报价取消根因 UNKNOWN。运维环境检查与合成 UID 交接脚本可接收，但未在 Linux 运行、未执行正式恢复；上线前须真实 Linux 跨 UID 完整链专项。ISS-018/020/105 不整体关闭。新 CORE-BUSINESS、PARTY-VERSION、ACCESS-READINESS 包不阻塞本轮，稳定后另行集成。

2026-11-05 本地全量候选 `d5a6a23394397775d3aab0f237163d4000bce224` 数据库、备份、Node、Vitest、构建和历史 Chrome 通过；适用浏览器 265/1，报价下载取消根因未知，整体 FAIL。ISS-020 原记录继续跟踪，保留当次网络、下载、页面及清理证据；单次真实 Chrome 和默认浏览器成功不替代全量失败。后续诊断修改仅测试文件，不宣称修复。详见[本轮报告](uat-evidence/local-release-validation-20261105/README.md)。

本地候选 `d7d927658e26727b6ebef135708d77278b9ee258` 浏览器全套发现历史经营分析等待 `load` 超时；失败页面已呈现标题与明细表，具体阻塞资源未确认。测试等待修复 `d7d37de82f492f0e128f85ee28577f8e3e3a058d` 的隔离定向 2/2 通过，完整集成仍须重跑；保留原失败。

`d7d9276` 浏览器进行中另发现财务重载/资金页面导航等待 `load` 超时与导入、报价下载取消；两类现象分别留证。财务测试改为 DOM 就绪且保留业务断言后，隔离布局 10/10、真实 Chrome 资金重复核查 2/2 通过，不覆盖原全套失败。

2026-11-05 接收 CORE-BUSINESS 完整来源 `78bcedb217d3d6ca0a05c9348e72d37c35801312`（8 个提交），合并提交 `eab047ddc8055bc3ff3ff13442f242bf8b389d5f`；C01 库存位置、C02 成本锁与 C03 付款审计的来源测试不能替代集成交叉与全量，Issue 不自动关闭。主体来源 `792edff6b696c4ad1f5bc65f9e91f623b5b964c0` 尚未接入且仅为部分成果，等待稳定增量。权限审查 `81cb56c18e6183b357af5b9845a4d56d6e6dd96b` 原报告和测试原件只存证，不将已知失败及错误行为观测断言原样纳入默认发现；最高角色通用 PATCH、授权 `.json` 不一致及财务后缀 500 由权限包修复，均保持原 Issue 待办。

核心候选 `76c98873f8ba4e521941f497fbd170c9b2bdb689` 的隔离 SQLite 跨库存/历史/采购成本/审计共 71 项，64 通过、7 项 PostgreSQL 专属跳过、0 失败；真实 PostgreSQL 交叉仍运行。核心来源改动了共享 `backend/crm/views.py`（采购付款）及 `backend/crm/serializers.py`（库存路径）；后续权限包若触及这些文件，须按函数级合并及跨模块测试，不覆盖任一成果。SKU 测试等待修复 17/17 定向通过，整合全量待执行。

核心合入冻结候选 `76c98873f8ba4e521941f497fbd170c9b2bdb689` 的真实 PostgreSQL 17 交叉测试 76/76、0 跳过；覆盖库存位置竞争、取消/出货、采购取消/收货、成本分配保存与取消竞争、付款第二条审计失败回滚后正常重试，并完成合成历史/财务/运营恢复核对。SQLite 同范围 71 项、7 项 PostgreSQL 跳过。源包及交叉结果均不代替最终整合全量；已有正式主体快照与数量调整兼容专项另行运行，部分主体新模型未纳入。

核心候选 `76c98873f8ba4e521941f497fbd170c9b2bdb689` 的现有正式主体快照、订单数量调整及核心流程 PostgreSQL 兼容测试 47/47，通过合成恢复核对。主体来源 `792edff6b696c4ad1f5bc65f9e91f623b5b964c0` 仍未接入，本结果不验证其新增模型或证明主体闭环。

诊断候选 `d7d927658e26727b6ebef135708d77278b9ee258` 的完整本地验收结束：SQLite 1419 项（80 跳过）、PostgreSQL 1419 项（32 跳过）、独立 PG 备份 8/8、Node 179/179、Vitest 725/725、构建和历史 Chrome 通过；适用浏览器 257 通过、9 失败，整体 FAIL。失败及随后的定向结果均保留，未将单次成功覆盖全量失败。核心稳定来源已在其后合入，结果不得归属于核心候选。

新增跨仓位测试提交 `9012a9d6b149e0f22ab554afe747b7421d2b669a`：试运行隔离 SQLite 2/2，既有默认仓流水阻止盘点重复入账，盘点启用后默认仓扣减不得借用历史仓；该次为提交前试运行，固定提交及 PostgreSQL 仍须验证。导入下载诊断和页面就绪测试提交 `44b01cd04e2a08ad69337cdfbc5f8b5454a2b848` 的定向结果和中间失败均已记录，不能覆盖集成失败。

核心候选 `c95601eebfc83597da044ca60a0ad362c57237d0` 的默认仓旧流水与历史盘点仓位交叉专项在真实 PostgreSQL 17 上 2/2 通过：已有流水阻断重复盘点承接；盘点启用后默认仓扣减不能借用历史仓库存。合成恢复核对通过；正式主体新增模型仍待稳定来源。本地全量在相同冻结候选继续运行。

`c95601ee` 的 Node 全量 178 通过、1 取消，双隔离工作树的迁移已持续推进但耗尽 120 秒总限额；单独串行文件仍失败。`2ed5c4343b62e3b419142e98ffbf35d423a28389` 对测试增加 60 秒无输出保护和实际进程退出断言，总限额改为 300 秒并串行测试文件；未提交版本试运行 180/180，不能替代固定候选全量。

### 2026-11-06 INTEGRATION-VALIDATION-04

权限来源 `bbfe475ef546b5d0fc3db8dbda0f456f0b042e9d`、新品提醒来源 `f63e984f33b86fb00c0de1daeb6a66fd4d42fc78` 已整合，核心修复保留；定向证据及限制见 [验收报告](uat-evidence/int04/README.md)。用户要求停止本地全量后仅运行定向；完整默认浏览器业务套件及 GitHub Actions 为 NOT_RUN，旧下载取消根因仍 UNKNOWN，原生打印和真实 Linux 恢复继续待验。既有 Issue 状态不变，不能据此关闭或宣称上线就绪。

### 2026-11-06 PARTY-VERSION-INTEGRATION-01

主体来源 `7cc8c4bf0249a3de53809836b7b3f233476a1648` 与新品提醒已集成并新增迁移合流；隔离 PG 升级、旧快照保值、主体替换及 PI/XLSX 定向结果见 [验收报告](uat-evidence/party-int01/README.md)。旧报价未知税号及模板无法表达的主体字段导致输出 422，首发使用该类报价为条件性阻断，真实数量和业务范围待核实；不改变现有 Issue 状态。`aa15c9ba7584599e918c1dd14723d31e31158b3d` 为后续多标签及身份接线对照，尚未合入。全量和 CI 按用户要求 NOT_RUN。
