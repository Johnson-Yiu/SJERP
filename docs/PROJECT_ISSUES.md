# SUNJACK-ERP 项目问题台账

## 2026-11-05 新增授权需求（待开发）

以下为用户当日明确授权的新工作包，状态均为 `AUTHORIZED_NOT_STARTED`；不是已完成成果，也不改变现有 ISS 状态或关闭条件。已检索本台账与阶段计划，未发现同名需求记录；不新建重复 ISS 编号。两包固定起点均为 `10afcf16fbfc1d0c01a175094012b4b696483cfb`，分别使用独立工作树。

| 工作包 | 分支 | 授权范围与边界 | 后续验收与下一步 |
| --- | --- | --- | --- |
| NEW-PRODUCT-REMINDERS-01 | `codex/new-product-reminders-20261105` | 在客户跟进中记录新品需求，固定标签、关键词搜索和关联跳转；默认有效，允许作废并留痕，作废项浅灰且明确标识，禁止删除。不自动匹配新品、不向客户发消息。 | 审查现有跟进与权限后实施模型、API、专属组件；验证新增、检索、关联、作废与审计、删除拒绝、数据范围和桌面/窄屏，再等待独立审查。 |
| INTERNAL-WORKSPACE-TABS-01 | `codex/internal-workspace-tabs-20261105` | ERP 内部多标签工作区；先盘点现有前端和本地工作树，保持标签的独立草稿/上下文、未保存保护、导航一致性、账号隔离与资源回收。此次授权替代旧的全部 Issue 修完后再开发排期。 | 先核对入口与壳层，实施后验证多标签切换/关闭、未保存保护、刷新与导航、账号切换/会话失效、资源回收及桌面/窄屏，再等待独立审查。 |

标签页包拥有壳层/导航/工作区状态，新品包拥有需求模型/API/专属组件；主体和身份包分别拥有主体修订与认证权限。`ResourcePage`、`DocumentPage`、路由和应用壳层仅协商局部接线，不整文件覆盖。新包稳定后另行集成并检查迁移图、入口、草稿隔离、会话失效和业务回归；不打断当前冻结候选，不代表上线就绪。

## LOCAL-RELEASE-VALIDATION-03 进展（2026-11-05）

核心冻结候选 `c95601eebfc83597da044ca60a0ad362c57237d0` 的 Node 全量 178 通过、1 项取消：双工作树并发启动时两套迁移分别约 93/101 秒，120 秒总限额先到；两套隔离进程均终止清理。单独将测试文件串行仍是 178/1，不能说串行已修复。测试/入口提交 `2ed5c4343b62e3b419142e98ffbf35d423a28389` 保留两个工作树真实并发和全部断言，将总限额调整为 300 秒并增加 60 秒无输出保护及专属进程树清理测试；未提交版本的 Node 全量试运行 180/180，仍须在固定提交上复验。[失败与试运行日志](uat-evidence/local-release-validation-20261105/node-runner-progress-evidence/publication-manifest.json)。

导入 CSV 下载取消在 `d7d9276` 全套中真实发生，根因 UNKNOWN。隔离导入文件测试依次为 6/6、5/6（客户页 `load` 超时）、加入 DOM 就绪及链接/Blob/字体事件诊断后 6/6；保留中间失败，不以定向成功覆盖全套。一次新运行中外部 Google Fonts 请求完成后页面触发 load，仅为该次时序，不能证明旧超时原因；诊断代码 `44b01cd04e2a08ad69337cdfbc5f8b5454a2b848` 不改导入业务。见[原始哈希及脱敏日志](uat-evidence/local-release-validation-20261105/import-download-diagnostics/publication-manifest.json)。

诊断候选 `d7d927658e26727b6ebef135708d77278b9ee258` 完整浏览器九配置为 257 通过/9 失败（其中主套件 233/8，图片导出 0/1），整体 FAIL；构建和历史 Chrome 通过。原失败含页面 load 超时、资金审核级联及导入/报价下载取消，详细日志和截图已保存，具体 load 阻塞资源及下载取消归因 UNKNOWN。核心来源在该测试后才合入，该结果不代表核心集成候选。

SKU 只读浏览器用例在候选 `d7d9276` 等待整页 load 时超时，快照已有 SKU 标题；测试提交 `4463ef8ca85871fa39c73941b608b66c57597f97` 保留原只读权限断言并等待 DOM 就绪，独立 Chromium 文件回归 17/17 通过。阻塞 load 的具体资源未知，不覆盖原全套失败；详情见[证据](uat-evidence/local-release-validation-20261105/core-sku-target-evidence/publication-manifest.json)。

来源 `81cb56c18e6183b357af5b9845a4d56d6e6dd96b` 的隔离权限审查确认：ISS-097 最高角色经通用 PATCH 可修改 code；ISS-003/055 普通授权客户 `.json` 路径与无后缀授权不一致；ISS-105 两个财务 `.json` 列表返回 500。最高角色保护属于内测前安全阻断，后两项为已复现兼容性缺陷，现有证据不证明未授权数据泄露。权限包负责修复，本集成不修改其专属实现、不启用正式 RBAC；修复后必须将保护性断言纳入默认发现，不再保留要求错误行为成功的观测断言。[原审查与原始测试](uat-evidence/access-readiness-20261105/INTEGRATION-NOTE.md) 已保存，不自行关闭原 Issue。

本地候选 `d7d927658e26727b6ebef135708d77278b9ee258` 浏览器主套件还出现应付布局重载等待 `load` 超时、ISS-105 资金候选首个页面导航超时；失败页面快照中应付筛选及原值已显示。资金测试后续审核条数不足由首个测试未完成造成，不能据此判定业务缺陷。改以 DOM 就绪和原有业务断言为准后，隔离财务布局 10/10、真实 Chrome 资金候选 2/2 通过；具体阻塞资源仍 UNKNOWN，原全套失败保留，等待稳定候选全量。导入 CSV 与正式报价 XLSX 在同次套件亦出现浏览器下载 canceled，分别保留原始失败，不将其简单归为同一已证实根因。

本地诊断候选 `d7d927658e26727b6ebef135708d77278b9ee258` 浏览器主套件中，历史经营分析用例在等待整页 `load` 时 30 秒超时；失败快照已显示页面标题与多张明细表，具体阻塞资源 UNKNOWN。测试修复 `d7d37de82f492f0e128f85ee28577f8e3e3a058d` 改为 DOM 就绪并保留原页面、表格和布局断言；隔离定向 2/2 通过，但不能覆盖集成失败。等待当前全套完整结果并重新验证稳定候选，不改变业务 Issue 状态。

ISS-020 最终候选 `d5a6a23394397775d3aab0f237163d4000bce224` 适用浏览器全套 265 通过/1 失败：报价保存并导出时 `download.saveAs: canceled`。本次 API 200，下载开始后约149毫秒取消，页面及上下文当时仍开放；进程、端口和专属临时目录后续清理成功。真实 Chrome 与默认浏览器各一次有诊断对照均成功，不能覆盖全套失败；根因及产品/运行器归属 UNKNOWN。下一步捕获实际失败时的导航、Blob 生命周期与请求失败，定位后最小修复并重跑集成；不关闭 ISS-020。见本轮[报告](uat-evidence/local-release-validation-20261105/README.md)。

ISS-002 维持原 NEEDS_VERIFICATION：最终候选锁文件的 `npm ci` 安装成功并报告 4 项 moderate；该输出未逐项核实公告、可达性或影响，不代表安全审计完成，未运行自动修复。下一步沿用原 ISS-002，对精确锁文件逐项复核并保留证据。

ISS-067 本轮仅改权限浏览器测试的截图输出路径，隔离定向运行 1 通过/1 超时失败：导航链接已定位但等待稳定时耗尽整项 30 秒预算，原因未确定。保留失败日志及截图，最终集成全量尚在执行，不更改原 Issue 状态；下一步结合全量重现现场核对页面与运行器。

用户转述 ChatGPT 2026-11-05 定向复审：ISS-105 财务概览导出独立错误状态、期间捕获及防重复提交补修合理，保留新增回归与真实 CSV 证据，不改变财务计算、权限或 API；ISS-020 导出来源 `56ce3588f544fcfeb98d431fb71d7e2d937f67db` 的本次适用 9 配置 266 通过/0 失败/0 跳过，打印 7 项用户延期未运行，这不证明旧报价取消根因消除。旧失败和根因 UNKNOWN 保留；若最终集成再次失败，需记录失败当次下载、页面与上下文生命周期、路径和进程清理，辨别产品与运行器后最小补修，不以定向成功覆盖全套失败。ISS-018 运维环境检测和合成交接脚本可接收；该脚本未在 Linux 执行且不执行正式数据库恢复，本机 PG 演练不等于跨 UID 完整链。真实 Linux 跨 UID 及完整恢复链保留上线前最终专项，不重复 Windows 模拟。本次有限接受不整体关闭 ISS-018、ISS-020 或 ISS-105。新 CORE-BUSINESS、PARTY-VERSION、ACCESS-READINESS 工作包不阻塞本轮，后续稳定后另行集成；本轮不改其专属实现。

ISS-121 保持 `FIXED_PENDING_REVIEW`，不得自行关闭。此前候选预审标出的来源编号边界已复现：SQLite 接受超长来源系统/组编号并创建申请，可能与 PostgreSQL 字段长度不兼容；修复检查点 `b27b9a0fddfe20b706bf4762e9e38168ac0333d1` 对 120/160 字符边界、复合行编号、预检、提交与旧申请执行增加保护，不截断原值。真实 PG17.11 定向55项及合成财务/历史新表备份恢复通过；完整集成候选仍须重跑全量并由独立审查。来源范围依然是系统/类型/编号三元组，业务语义需负责人确认。 已记账资金的合成审计更正已验证保留原事实及审核事件链接；更正详情为自由字段，来源/事实 ID 与凭证真实性不自动核验，退款/更正业务规则仍待确认，不宣称全部接通。首次失败和通过日志见[本包报告](uat-evidence/local-release-validation-20261105/README.md)。

用户新约定：日常以本地完整测试为准并提交 `[skip ci]`，GitHub Actions `NOT_RUN`；上线前冻结候选后另运行完整 CI 与专项。真实 Linux 跨 UID、目标部署/恢复、真实资料和独立复审仍是各自门槛。完整打印与分页继续用户延期，报价 XLSX 和财务 CSV 等实际导出不延期。运维及导出稳定来源均已合入；最终统一全量正在执行。旧 262/1 浏览器失败以及本轮候选 a46 的两项浏览器超时均不得改记通过。

## INTEGRATION-CLOSEOUT-02 当前核实（2026-11-05）

统一分支`codex/r1-prelaunch-consolidation-20261104`。完整稳定财务来源e301a86044ffe56b72172a94dc3b00ae09401b05、Linux来源4a4f338b09e9a464f1e66c24a905c35c970729bf、历史来源ba4274742727a6794608dc8581a49b3692d865a6均已合入。当前已冻结并完成本轮全量的候选为02140bf46df27ba1abf5b9018507c07aae825769；仅两处前端下载生命周期补修，无数据库、金额、日期、权限逻辑变化。

最终候选实际结果：Python3.12 SQLite1410项1338通过72跳过（含8项原生PG备份命令）；真实PG17.11全量1410项1378通过32跳过，均0失败/错误。102表1218行133迁移5文件恢复一致，三类恢复及9项不可变保护通过并清理；追加独立源状态专项6/6，在操作末尾实际重读102表1218行100序列与5文件，前后相同，不追认此前1410运行曾做该末尾重读。Node179、字体1、Vitest725/78文件及构建通过。适用Playwright9profiles实际262通过1失败0跳过，报价仍saveAs canceled，当前继续诊断；不能把之前单次定向PASS当彻底修复。整份打印7项NOT_RUN_USER_DEFERRED，原断言未删。

同一02140历史Chrome5/5脚本、98个本地HTTP请求、live及脱敏副本只读核验通过，8图、实际XLSX、数据库/媒体及日志已封存，进程/端口/私有任务目录清理完成。SQLite发布副本102表1091条业务/审计行，删除2个session行但业务表未改；不与PG1218行混为同一数据集。不把开发身份、合成双session或Django admin当作真实员工ERP登录。

当前124唯一ID：FIXED_PENDING_REVIEW87、NEEDS_VERIFICATION14、BLOCKED13、OPEN0、CLOSED10。原86项仍待独立复审，ISS-121完整实现及集成验收证据已补，校准为FIXED_PENDING_REVIEW；新增待复审1项，与原86项队列分开记录；没有关闭Issue。报价浏览器交付子项归ISS-020，财务CSV归ISS-105，附件重开归ISS-007、回执跨UID归ISS-018，不创建重复ID。原86入口365条与当前代码存在性核对不等于业务接受。

用户明确GitHub额度不足：后续提交[skip ci]，不触发、等待或重跑Actions，不改workflow规避；CI暂停不记PASS。历史906/41855319673成功只对应旧源码。旧运行中/未交付描述位于后面的明确历史章节，不覆盖当前事实。

真实Linux补修后跨UID尚未执行：只读检查未找到docker命令，沙箱外wsl列表退出1只返回安装帮助，没有已验证Linux环境。正式认证/RBAC、真实启用资料、生产配置及真实迁移执行分别需目标环境或单独授权；历史代码未完成不能归为缺凭证，退款/已记账反向映射只按已支持范围，不宣称全部支持。打印完整成品与分页继续用户延期，不合master、不部署、不导入真实资料、不宣布上线就绪。

[当前报告](uat-evidence/integration-closeout-02/README.md)、[原86复审包](uat-evidence/integration-closeout-02/REVIEW-BACKLOG.md)、[ISS121补充](uat-evidence/integration-closeout-02/ISS121-REVIEW-SUPPLEMENT.md)、[实际日志](uat-evidence/integration-closeout-02/TEST-RESULTS.md)。

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

### 2026-11-04 REVIEW-INTEGRATION-BATCH-01 复核记录（综合回归进行中）

固定起点4388947d70d26bca66ca0bfc76b2383a2fc0d404与CI41782956426已核实。当前已完整接收打印b3d0d386de70d9efd77bf62cdbd87877fbccbfb8、核心工作区e302199f7890c686a309f54aebe8cc31b6202f52、财务3a07e7ef1a9e63c98077d45492ba23b798c7fcdd、运维d289de36a3da3e4bd6531c812ec21a05f046d570、历史a0729a0965850028fe52f5b6fcc3e825f23b1289；各自远端/精确三CI已重新核实，六个固定来源（含起点）均为集成673ae3724b5db8d69018acbcea3e26c904c3fea3的祖先。来源CI不替代集成CI，详见[综合证据](uat-evidence/review-integration-batch-20261104/README.md)和source-receipts.json。

ISS-007三项修前失败已保留。ce74f8b、0914002、a866c29补修覆盖存储/审计/事务失败补偿、提交结果探测、锁释放、恢复目录链接边界及下载原名；真实一次性PG17专项42/42。财务合入阶段全量1249项中1189通过、60跳过、0失败。后续319941c05e4682d80cd718f577514a39231fabfa增强银行来源回退及财务凭证备份引用校验；PG17新专项13/13，94表1027行4文件恢复一致，10张新财务表有合成记录，序列和凭证字节一致且源媒体未变、清理完成。不能以专项替代全来源最终全量或目标存储验收。

全来源673ae37的Vitest720/720、字体规范1/1、生产构建通过；财务集成Chrome审批/私有凭证2/2与开发资金页面2/2。历史Chrome完成审核执行并保存合成DB（12源记录、三个not_connected、正式资金/库存/履约0）；首轮因沙箱拒绝Google Fonts整体失败，沙箱外保持全部断言重开同申请通过。日志与失败原因在TEST-RESULTS.md，不删除失败或用来源结果代替集成结果。最终综合Backend/PG/Frontend与同SHA三CI仍待完成。

ISS-105、ISS-108已有完整实现及集成证据，校准为FIXED_PENDING_REVIEW，原行在文末引用历史保留；不再根据旧“未实施”重复派工。其余124个唯一ID重新计数：FIXED_PENDING_REVIEW86、NEEDS_VERIFICATION14、BLOCKED14、CLOSED10、OPEN0。未关闭GitHub Issue。Codex及子代理自查均不是ChatGPT独立复审。正式账户/启用日期/余额/凭证、目标Linux媒体栅栏、HTTPS/运行角色、异地副本/告警仍分别待验。ISS-037仅完整打印及分页按用户决定延期，其余快照主体不延期，未追加催办。

最新综合实测：后端代码1f189c3f74fda2908620dd3860230d860f1cbb43的SQLite全量1312项1251通过/61跳过/0失败，PG17.11全量1312项1282通过/30跳过/0失败；99表1081行128迁移4文件、历史/财务新表/序列/凭证恢复一致，真实恢复HTTP4/4，额外8项备份命令专项8/8，源不变且临时集群清理完成。候选CI41829100528 Backend/PG成功、Frontend270项中268通过/2失败（ISS039快照子进程）。03b524db7392ab989c699e31586484fd33a95fcb最小修复有界缓冲/诊断，Node179/179及Chrome2/2；7a896d0f824a361287cf981c377b07731c45f879修证据根目录，财务Chrome4/4。原全部业务/全库/权限断言保留，产品代码tree与全量已验1f完全一致；最终精确SHA三CI以交付回执核实，不提前登记通过。

### 2026-11-04 PRELAUNCH-CONSOLIDATION-CLOSEOUT 当前核实

ISS-018 继续 **BLOCKED / DEPLOYMENT_VERIFICATION_PENDING**：备份来源 `0692f4db292bd6fdeea1997562fb79c662f03ae7` 的隔离命令和证据已按原 `9250b066` 后的增量集成；锁定 Django 6.0.9 的本机真实 PG17 命令专项 8 项通过。旧表中“真实 PostgreSQL 待验”指生产或目标部署环境，不能再描述为从未做过隔离 PostgreSQL 演练。进程内媒体锁不等于生产多进程写入暂停，生产异地副本、密钥、权限、调度、告警和 RPO/RTO 仍须目标环境验收。

ISS-121 的预检初版及整单 partial 修复继续保留；预检不等于正式迁移或审批，真实启用日期及余额须由财务提供，已确认业务原则不重新列为待决。ISS-037 继续 **NEEDS_VERIFICATION**：保存报价的合成 Chrome/实际 XLSX 定向核对与实际 UI 打印成品分开；打印任务当前明确尚未完成，稳定 SHA 未交付，不以阶段提交或独立渲染 PDF 冒充成品。ISS-105/108 及其未完成实施与外部材料要求不变。未新建或关闭 Issue，历史记录保留；后续动作与证据见[启用前门槛](uat-evidence/r1-prelaunch-consolidation-20261104/READINESS-GATES.md)。

### 2026-11-04 启用前整合：第一部分

固定起点 `d5abc64750d00c89d685bf12c0f8f67d4ba10a97` 的 [BATCH-02 CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41671231926) 在同一 SHA 上 Backend、PostgreSQL 17、Frontend 均成功。按用户转述的 ChatGPT 复审结论，历史预检 `partial` 整单误报的定向修复通过；完整初版及 FIX-01 的代码、路由、流式上传限额、模板和测试取自 `951adda34b5c60b303725702514cdacac17cc58d`，详见[预检及修复证据](uat-evidence/r1-iss121-history-import-preflight-20261103/FIX-01-REPORT.md)。预检是只读检查，不等于真实历史导入或启用完成，ISS-121 整体仍 BLOCKED。

备份 `9250b066cbd28fd09bd2b1cc1f057604de1f76d9` 的 [PostgreSQL 17 隔离联合演练](uat-evidence/r1-iss018-backup-restore-drill-20261103/POSTGRES-02.md)为受控合成数据、专用临时集群成果，不能当作生产备份命令或全写入者静默证明；ISS-018 仍 BLOCKED。ISS-037 仍 NEEDS_VERIFICATION：真实打印最终成品和历史原件仍须验收；ISS-105 仍 OPEN：内部转账、退款更正、期初及账户核对等仍待实施和验收。下一步及已确认规则见[启用前剩余门槛](uat-evidence/r1-prelaunch-consolidation-20261104/READINESS-GATES.md)。不关闭 ISS-018/037/105/121，不重新将已确认业务原则列为待决。

### 2026-11-03 R1-RULE-GAP-BATCH-02 补充记录

基线 `a55469c1b07e4f13037c6644c69d8a35ef0496a0`。本轮在独立工作树补充 [ISS-037 卖方/模板版本](uat-evidence/r1-iss037-seller-template-freeze-20261103/README.md)、[ISS-105 银行疑似重复核实](uat-evidence/r1-iss105-bank-duplicate-detection-20261103/README.md) 和 [ISS-039 真实 PostgreSQL 预留竞争](uat-evidence/r1-iss039-reservation-concurrency-20261103/README.md)。ISS-037 仍 NEEDS_VERIFICATION：历史原件归档、打印实际文件及完整主体/审批仍须核验；ISS-105 仍 OPEN：内部转账、退款更正、启用余额、分类、账户核对和凭证绑定等未被本次去重覆盖。ISS-039 成本金额比例和采购修改权限规则不变，定向并发证据待独立复审；不关闭任何议题。ISS-108/121 已确认原则继续有效，实际余额和启用日不作猜测。三项合并迁移及精确最终 SHA 的完整 CI 尚待核实，不以专项 CI 替代集成结论。

### 2026-11-03 R1-RULE-GAP-FIX-BATCH-01 最新核实

统一源码基线 `8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`。上一轮三份独立审查已推送并在本集成分支完整保留：[ISS-105](uat-evidence/r1-iss105-actual-cash-audit-20261103/README.md)（远端 `1cad93d0cb0297c33f764f6cb68d5c610512d9e4`）、[ISS-037](uat-evidence/r1-iss037-snapshot-audit-20261103/README.md)（`c88a121298465fcb04e11f9b65ef9ad251eadf3f`）、[ISS-039](uat-evidence/r1-iss039-shared-cost-audit-20261103/README.md)（`2d5164287672d9a57a6496761c3ea0d026088072`）。旧审查使用Python3.14/Django6.0.6；本轮用真实CPython3.12.16，全部16项Python锁定版本逐项一致、pip check通过，不能互相替代环境证据。

本轮仅补修独立银行手续费可选结汇关联、历史未知买方修订继承、公共费用新增/修改仅按金额分摊；各项最终测试、截图、HTTP、来源提交及同一SHA三项CI见[集成交付报告](uat-evidence/r1-rule-gap-fix-batch-20261103/README.md)。ISS-105整体保持OPEN；ISS-037整体为NEEDS_VERIFICATION；ISS-039本轮定向补修待独立复审，不自动关闭。按每个ID最后一条表格记录归一化核对共124项：OPEN 1、BLOCKED 16、NEEDS_VERIFICATION 17、FIXED_PENDING_REVIEW 80、CLOSED 10；新增0、关闭0。仅ISS-037/039两项从旧BLOCKED校准，其他状态不变；不覆盖下方历史时点统计。

ISS-105仍保留内部转账公司毛流量排除、银行六维重复候选、待分类、现金/银行分离、启用基准余额、账户核对、凭证文件绑定及完整操作审计；ISS-037仍保留卖方/模板冻结、完整双方字段、历史来源可信度、主体版本/修订及发起审批分离。不得把本次三个最小修复作为整个议题完成。

ISS-108/121的已确认原则不是重新待决事项：按原D01–D08及本轮用户规则，已确认银行事实不可覆盖，退款/更正保留原始记录和凭证，不推测来源或自动解除额度；启用余额是银行对账单独立基准、不计新流入，未知历史保持待核实，现金与银行区分。后续是受控实施、核实凭证和部署验收；实际启用日、真实账户/余额和具体更正原件仍须财务提供，不能从合成资料猜测。历史段落“规则未明确”保留其当时来源，不作为向业务负责人重复询问已确认原则的依据。本轮不修改这两项安全拒绝代码、不配置启用日、不迁入真实数据、不启用正式RBAC。

2026-11-02 R1-POSTGRES-AUTH-CONTRACT-FIX-02：在集成分支 `codex/r1-postgres-integration-validation-20261102` 的代码提交 `7ab9913e03f1bde341158237e51aeebf77a86abc` 仅修正历史订单分析测试认证契约：针对函数视图真实包装类设置 `SessionAuthenticationWithChallenge`，匿名 401、已认证无权限 403 均断言通过。SQLite 专项 9/9、SQLite 后端全量 1098（33 跳过）、Django check、迁移检查及 `git diff --check` 通过；精确 SHA 的 GitHub run [#41432846693](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41432846693) Backend、Backend PostgreSQL 17、Frontend 三项 SUCCESS，PostgreSQL 全量 1098（21 跳过）且目标失败用例为 `ok`。未修改生产逻辑或 Issue 状态；历史 run #41424016735 的失败记录保留为旧 SHA 的事实。问题总数与状态不变：124 项，OPEN 1、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 79、CLOSED 10。证据及原始日志见[验收报告](uat-evidence/r1-postgres-integration-validation-20261102/README.md)的 FIX-02 小节。

2026-11-02 R1-POSTGRES-INTEGRATION-VALIDATION-01：从统一基线 `9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2` 整合四项指定测试修改；生产业务逻辑、模型/迁移、认证/审计保护、`test_runner.py`、`postgres_test_cleanup.py` 和 CI workflow 未变。CI run [#41424016735](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41424016735) 对精确提交 `e6b40cadb04c54ef3376307daba19f78276a913d`：Backend SUCCESS（1098 项，0 失败）；Frontend SUCCESS（Node 171/171、Node-only 1/1、Vitest 69 文件、Playwright 主套件216项及隔离套件25项、build成功）；Backend PostgreSQL 17 FAILURE（1098 项、21 跳过、1 失败）。唯一失败是 `test_historical_orders.py:205` 的匿名历史报表请求仍断言403，staging 实际401，符合已确认认证契约；这是未更新的旧测试断言，不是环境或业务逻辑失败。该失败测试中的已认证403断言未执行；其他专用认证测试的401/403路径通过。按用户要求失败后未继续修改或重跑，等待独立审查。PostgreSQL 的 ISS-018 fail-closed、三张 CSV 审计表 TRUNCATE 拒绝且行保留、测试清理保护均通过；Supplier 编码无长度错误。ISS-006 `NEEDS_VERIFICATION`、ISS-018 `BLOCKED`、ISS-052 `FIXED_PENDING_REVIEW` 等状态均不变。归一化总表124项：OPEN 1、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 79、CLOSED 10。完整 job 日志、逐项命令、来源 SHA 和失败分类见[本轮验收报告](uat-evidence/r1-postgres-integration-validation-20261102/README.md)及其 `logs/`。

2026-10-31 R1-ISS-008-FUP-01：在指定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 与历史成果 `80dc73ae4ae47f9e04969f39b441af206d34306b` 的相关文件比对中，249 项国家/地区目录、标准中文名/别名和既有覆盖测试已完整包含，无需重复移植业务实现；只补客户编辑保存/刷新回显的真实 Chrome 回归。249 项后端逐项覆盖、选择器 Vitest 及 Chrome 桌面/390px 测试通过，America 歧义、未知历史文本保留及报价编号不变规则均保留。ISS-008-FUP-01 更新为 `FIXED_PENDING_REVIEW`，等待独立审查；按每个 ID 最后一条记录统计共 124 项：OPEN 1、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 79、CLOSED 10。证据见[R1-ISS-008-FUP-01验收记录](uat-evidence/r1-iss008-aliases-bd324-20261031/README.md)。

2026-10-28 R1-STATUS-RECONCILE-01：在固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` 读取 Excel 全仓124项/业务规则46项，并核对当前台账、实际分支 HEAD 与验收报告。仅将 ISS-024、040、042、048、052、062 的规范状态按可核实证据校准；ISS-042/048 的阶段成果不等于整体 CLOSED，其余重点项保留原状态并补足证据边界。当前归一化统计：OPEN 2、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 78、CLOSED 10。详见 [R1 状态对账报告](uat-evidence/r1-status-reconcile-20261028/README.md)。

2026-10-31 R1-ISS052-AUDIT-HARDENING-02：在固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 整合 CSV 流式限额、HTTP 413 与导入审计来源，并新增 PostgreSQL TRUNCATE 触发器和迁移回退保护。ISS-052 保持 `FIXED_PENDING_REVIEW`，不关闭；独立 PostgreSQL 原始 SQL 运行因本地仅配置隔离 SQLite 而未执行，保留 PostgreSQL 验收待办。未改变 Issue 集合或状态，本轮状态计数无变化；最新可核实总表统计仍为 OPEN 2、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 78、CLOSED 10。完整来源、测试命令、限制和截图出处见[本轮报告](uat-evidence/r1-iss052-audit-hardening-20261031/README.md)及[测试日志](uat-evidence/r1-iss052-audit-hardening-20261031/logs/test-results.md)。

2026-10-28 最新核实：R1-REPAIR-CONSOLIDATION-01 已集成七个指定来源并完成本地综合回归；ISS-055 从 OPEN 更新为 FIXED_PENDING_REVIEW（仍待独立审查，未关闭），其余 Issue 状态均按各自验收缺口保留。按每个 ID 最后一条记录统计共 124 项：OPEN 5、BLOCKED 21、NEEDS_VERIFICATION 20、FIXED_PENDING_REVIEW 68、CLOSED 10。完整来源 SHA、回归、截图、日志及 11 月 1 日 CI 待办见[集成验收报告](uat-evidence/integration-r1-repairs-20261028/README.md)。

2026-10-27 ISS-036-FIX-03 更新：在 FIX-02 基础上补齐历史交易单位快照的完整语义冲突识别；ISS-020、ISS-021、ISS-027、ISS-029 及既有集成项保持原状态。非字典、缺少 factor、factor 无法解析或非有限的历史快照，以及缺少 `base_unit`、`unit`、`allow_fraction` 的快照继续统一标记为歧义；同 factor 但单位语义不同也不再错误套用不可拆分限制。完全一致的有效快照仍执行不可拆分规则，`factor=1` 和允许分数语义保持不变。新增 factor、base_unit、unit、allow_fraction 冲突及一致快照回归，ISS-036 继续为 `FIXED_PENDING_REVIEW`。ISS-043、ISS-075、ISS-023 已在 `codex/integration-043-075-023` 完整集成，仍等待独立审查。ISS-043 的真实 PostgreSQL/最终 CI 为 `DEPLOYMENT_VERIFICATION_PENDING`；ISS-075 无付款阶段 PO 的真实业务财务抽查、ISS-023 真实 SKU 型号完整性抽查为 `BUSINESS_VERIFICATION_PENDING`。ISS-023 窄屏菜单收起可用性已通过，不登记为未修复。ISS-020 已补齐保存版本 API/XLSX、历史图片、关键字段 422、金额一致性及真实 Chrome 桌面/390px窄屏证据。ISS-027 的真实 Chrome 保存、改期、清除、非法日期、失败重试、客户列表同步及桌面/390px窄屏证据已补齐。ISS-097 已完成最高角色有效权限显示专项修复，保持 `FIXED_PENDING_REVIEW`，正式员工与部署边界风险仍保留。新增 ISS-008-FUP-01 为 `P2 / OPEN`，仅登记不开发。按每个 ID 最后一条表格记录归一化统计，共 124 个：OPEN 6、BLOCKED 21、NEEDS_VERIFICATION 20、FIXED_PENDING_REVIEW 67、CLOSED 10；下方历史轮次统计保留原时点，不作为当前统计。证据见 [ISS-036-FIX-03 验收记录](uat-evidence/iss036-fix03/README.md) 及既有集成报告。

最新轮次：R1-READINESS-01（2026-10-19），基线199a21e0f407ba9ad772a5dec86e0b30dbd0c9b5。完成全系统试用准备和业务阻断审查；仅更新本轮报告/台账记录，不修改业务代码或历史Issue状态。当前不具备真实员工内部试用条件；A类门槛为ISS-003、ISS-018、ISS-055。R1-FIN-P3-B按授权记录阶段性验收通过，ISS-105保持OPEN，ISS-108和ISS-121保持BLOCKED。证据见[R1-READINESS-01审查报告](R1-READINESS-01-全系统试用准备与业务阻断问题审查.md)。

上一轮：R1-FIN-P2-A（2026-10-18至19），基线1b2ca0eb5b1947dd53f5ab995828dd33f514e0d4。按D01–D08授权新增银行资金事实/来源分配后端、必要API及安全保护；旧金额/核销/报表不改，ISS-105保持OPEN。新增ISS-108 BLOCKED登记尚未明确的更正与来源解除细则；新增ISS-109待复审记录CI跨日测试修正，见[P2-A验收](R1-FIN-P2-A-人民币资金事实与结汇后端验收.md)。不进入P2-B、正式RBAC、员工UAT或部署。

上一轮：R1-FIN-P1（2026-10-18），基线ad3a08ebd47ad4b94ffe8f6ebfed5f083b9ac57e。仅现有账面人民币折算参考口径的页面/API/CSV说明澄清，金额、计算、历史数据和权限不变；ISS-105保持OPEN。该轮新增ISS-107登记暂缓的模型元数据旧称；详见[P1验收](R1-FIN-P1-现有财务统计口径澄清验收.md)。2026-10-24跟进已完成最小元数据修复，当前状态以ISS-107条目为准，等待独立代码与视觉复审，不进入P2。

上一轮：R1-FIN-P0（2026-10-18），基线da39ea3aa986df9faa12e79b1da3adece03260b7。仅财务口径确认与实施准备文档，ISS-105保持OPEN，其他Issue状态不变；未修改核心财务代码、数据库或历史金额。

上一轮核对基线：R0-F9从master / b916fab613806a9fd00636cc87496803557d45a8（2026-10-16）开始。F8C代码、自动与已覆盖操作经用户转述独立复审通过，有条件封版；CI #38909906403三项SUCCESS。ISS-095/096独立图片仍待审，ISS-097保持NEEDS_VERIFICATION。本轮只做全站UI/UX审查、局部样式修正及证据补全；完成后停止等待独立审查，不进入历史集中修复、正式RBAC、员工UAT或生产部署。

当前轮次：R0-F9-VIS-01（2026-10-17），基线9d05a70c07d1d8eb9d080dd1d75ea608209a799b。仅测试和证据采集修正，27路由完成态已补；18张精确尺寸BLOCKED，ISS-099未复现仍待核实。旧573原图哈希保持不变，独立再次审查待完成。

## 状态和优先级

- `OPEN`：当前证据确认仍有缺陷，或尚未完成的准备任务。

- `BLOCKED`：依赖业务/用户/运维决策、获准的测试前提或外部部署配置；“延期”事项也用此状态，并在记录中注明延期原因。

- `NEEDS_VERIFICATION`：历史失败、风险或本轮未覆盖项尚无足够当前证据确认修复或仍然失败。

- `FIXED_PENDING_REVIEW`：修复和复测证据已记录，仍等待独立 ChatGPT/用户复审；Codex 不得自行关闭。

- `CLOSED`：只供有验收证据且完成所需独立复审的记录使用。当前表只列未关闭事项；已关闭历史见下文。

优先级以影响而非发现年代决定：P0 为立即重大损害/暴露；P1 为核心业务、安全或内测门槛；P2 为有实质影响但可通过流程/受控范围缓解；P3 为较低紧急度的可用性或效率改进。Enhancement 表示未承诺范围，保留原分类，不强行映射为 P 级。

负责人使用职责角色，不虚构个人分配。每项关闭前须满足记录的关闭条件并更新证据；有“待复审”标记的事项只能由独立复审或用户明确接受后关闭。每项记录还必须保留首次发现来源和日期、最近核实情况、明确下一步、计划阶段及关闭依据；来源或日期未能从原始证据确认时明确写 `UNKNOWN`。下面的“最近核实”是证据记录核对，不等同于重新执行测试。

## 当前问题台账（包含本轮复审后已关闭记录）

### P1：核心业务、安全与内测门槛

| ID | 状态 | 首次发现来源 / 日期 | 最近核实（日期 / HEAD） | 影响与当前证据 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|---|
| ISS-001 | FIXED_PENDING_REVIEW | [R0-E1 §问题](R0-E1-综合业务回归与内测准备.md)；[Phase 3 状态机 GAP](Phase3-业务流程与异常UAT计划.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-18 R1-A-FUP-02：业务负责人方案A明确；用户确认FUP-01已独立复审通过。真实USD500全部发货、收340欠160时完成履约，应收/逾期/待办保留；尾款收齐及退款40后状态正确恢复。根因是orderTasks对completed提前返回空数组，已修复并增加只读财务派生状态与权限保护；不改完成条件或历史余额。证据：[FUP-02验收](R1-A-FUP-02-订单履约财务分离验收.md)。 | E1 UI 已复现：全部发货但欠 USD 160 时仍可完成订单；工作台随即没有待办，应收仍未结。可能让业务人员停止催收。 | 前端/后端/财务QA已按方案A完成最小修复及正常/拒绝路径回归；等待ChatGPT独立代码、原图和数据库证据审查，不自行关闭。 | R1-A-FUP-02 / 待独立复审 | completed欠款可继续追踪、逾期与应收导航准确；收齐后待办消失、退款后恢复；无财务权限不泄露；未发齐不得完成、重复请求无副作用；最终精确HEAD三项CI及独立复审通过。 |
| ISS-002 | NEEDS_VERIFICATION | R0-E1依赖审计及后续锁定修复3961ef6c4b0499adb0689f14be73372692ddac3f；最新稳定运维来源d289de36a3da3e4bd6531c812ec21a05f046d570 | 当前Pillow13.0.0/Django6.0.9及16项精确Python锁已包含；运维来源同日CPython3.12.16实测与pip-audit-final.log公开漏洞库返回无已知漏洞，当前requirements和前端lock与该来源Git字节一致（本包dependency-audit-reuse.json）。已验8087f2c68b19a302a25e814ec8ce6113d91d4750 / CI41839476121的Python3.12.15 CI Backend1312项1254通过/58跳过、PG1282通过/30跳过；图像路径纳入全量，不能把旧Pillow11.3.0/无lock/pip-audit不可用当当前派工。 | 保留风险：Python锁缺发行包哈希；生产镜像和真实暴露路径未验证；当前本包npm4项moderate开发依赖、无high/critical，旧审计快照不当成当前安全声明。 | 保持NEEDS_VERIFICATION；核对目标镜像解析版本/软件公告适用性及依赖维护策略；独立复审后决定是否关闭。 | 目标环境验证和安全复审 | 来源证据docs/uat-evidence/operations-readiness-batch-20261104/pip-audit-final.log、runtime-versions.log；本包README/TEST-RESULTS.md。无已知漏洞返回只代表该次公开库覆盖，不是绝对安全。 |
| ISS-003 | BLOCKED | [R0-E1 RBAC 覆盖](R0-E1-综合业务回归与内测准备.md)；[D4-C API 矩阵](r0-d4b2c-api-permission-matrix.md)；[AGENTS 权限约定](../AGENTS.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-27 / `codex/verify-iss003-employee-permissions` / 精确来源 SHA `2111d193ef3a69db05c23e27813cfbf26d9034d7`：隔离合成账号定向后端 `131` 项通过；system check、迁移检查和全新 SQLite 迁移通过。证据：[ISS-003 员工权限与数据范围隔离验收](uat-evidence/iss-003-employee-permissions/README.md) | 当前代码已对 self、department、department_tree、all、缺模块权限、跨模块关联、列表/详情/搜索/导出及采购共享路径提供可复核的服务端边界；本轮没有发现可明确安全最小修复的代码缺陷。真实员工会话、正式组织树、生产 PostgreSQL、真实业务数据和真实 Chrome UI 仍未验收，不能把合成账号 API 结果扩大为内测通过。 | 内测负责人提出进入内测及真实测试账号授权；获授权后由 QA 按真实员工 self/department/department_tree/all、缺模块权限、跨模块关联、导出、文件 URL 及桌面/窄屏 UI 执行隔离验收。保留当前开发超级管理员机制，不得自行启用正式 RBAC、降权开发身份或关闭本项。 | 内测准备（须用户明确授权） | 真实隔离账号 UI/API 矩阵、网络状态和业务流程证据完整；拒绝与正常共享业务路径都通过；用户/独立审查确认。 |
| ISS-004 | FIXED_PENDING_REVIEW | [真实用户 E2E §P1](真实用户E2E-UAT-20260923.md)；[R0-E1 财务覆盖](R0-E1-综合业务回归与内测准备.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测）；2026-10-18 R1-A：USD直接记账、计划拆分、合法无计划预收及超额已真实成功；新增稳定流水号/保存中保护；同表单重试复用编号。跨刷新、全站并发幂等与真实提交后断网仍未完整覆盖。 证据：[R1-A报告](R1-A-核心业务历史Issue核实与修复.md)。 | 旧 UAT 的“新增记账”美元客户收款曾失败；应收计划登记可绕行。后续服务层和财务测试覆盖 USD，但 E1 未重新执行该直接 UI 入口。 | 财务 QA 用隔离订单，在“新增记账”走 USD 正常创建、校验失败无副作用及计划关联；确认 UI 金额、汇率和服务端流水一致。；R1-A下一步：按报告未覆盖分支补验，并交ChatGPT独立审查；不得自行关闭。 | R0-E1 补验 | 直接记账与应收计划两条合法路径均真实 UI 成功；无效金额被清晰拒绝且流水/余额保持不变；自动测试及独立复审通过。 |
| ISS-005 | FIXED_PENDING_REVIEW | [R0-E1 采购覆盖](R0-E1-综合业务回归与内测准备.md)；[Round 1 独立采购 SUP05](UAT-Round1-正式业务全流程测试.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测）；2026-10-18 R1-A：隔离真实UI完成无Sales Order的双SKU采购（含无来源明细）、交易单位、部分收货/冲销/重收及分批付款；265USD全结清。保存断网与全部来源组合仍需补验。 证据：[R1-A报告](R1-A-核心业务历史Issue核实与修复.md)。 | E1 完成了共享采购链；旧 UI 只证明无来源的独立采购草稿可建，尚未证明独立采购从下单、到货、库存到付款的整条闭环。无销售订单的共享采购人员仍须可工作。 | 采购 QA 在隔离库走无关联订单的采购、部分/全部收货、应付及库存回查，不借 API/脚本替代 UI。；R1-A下一步：按报告未覆盖分支补验，并交ChatGPT独立审查；不得自行关闭。 | R0-E1 补验 | 独立采购全闭环真实 UI 成功；库存、成本和付款统计一致；权限边界下仍可访问共享采购；自动化和复审通过。 |
| ISS-006 | NEEDS_VERIFICATION | [R0-E1 库存覆盖](R0-E1-综合业务回归与内测准备.md)；[Phase 3C](Phase3C-不变量故障注入执行记录.md)；[Round 1 P2 Re-UAT](UAT-Round1-正式业务全流程测试.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；关联 R1-A 精确 SHA `d82643907f2886ecc412fdfa8839d2b8cc165751`。既有冲销/重收证据仍为部分覆盖，并发、网络和全部历史异常未执行；保持 NEEDS_VERIFICATION。 历史台账结论保留：UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测）；2026-10-18 R1-A：已补未消耗入库冲销、销售消耗后拒绝、部分收货冲销重收、销售冲销、赠品超到及手工盘盈冲销UI和Decimal数据库证据；网络/并发及全部历史异常仍未覆盖。 证据：[R1-A报告](R1-A-核心业务历史Issue核实与修复.md)。 | E1 证实已被销售出库消耗的到货不能冲销；未在本轮验证未消耗到货成功冲销、发货冲销、超到和手工盘点完整 UI 路径。历史部分冲销/冲销后重收有证据，不能覆盖全部当前流程。 本轮仅做状态对账，不扩大为生产/正式员工验收。 | 库存/采购 QA 用隔离记录执行成功及拒绝分支，核对库存、预留、采购状态、流水历史和重复操作原子性。；R1-A下一步：按报告未覆盖分支补验，并交ChatGPT独立审查；不得自行关闭。 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | R0-E1 补验 | 每种冲销的允许/拒绝路径、重复操作、余额/数量快照和 UI 反馈均通过；历史记录不被覆盖；PostgreSQL 与独立复审通过。 |
| ISS-007 | NEEDS_VERIFICATION | [R0-E1 文件覆盖](R0-E1-综合业务回归与内测准备.md)；[UX 第二轮附件复测](Product-UX-Second-Review.md)；[D4-C 文件矩阵](r0-d4b2c-api-permission-matrix.md)；[R1-ISS007 附件 UAT](uat-evidence/r1-iss007-followup-files-uat-20261031/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-11-01 / `codex/r1-iss007-followup-files-uat-20261031`，基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c`；删除/替换证据提交 `9a4d70e1425928358be7001ece43327c00557b0c`。旧上传、预览、下载和权限验收保持；在独立 SQLite/MEDIA_ROOT 中对新建合成目标完成真实 Chrome 删除、刷新、替代上传及直链核验。 | 仅删除本轮合成 `ISS007-delete-target.txt`：DELETE 204，目标 DB 行/磁盘文件均不存在，旧 URL 404；隔离普通认证用户的“删除跟进附件”审计保留 operator 外键、DELETE 路径和文件名元数据。替代上传 201；删除前已有三份合成附件的 ID、路径、大小、SHA 均不变。桌面 1440×900、窄屏 390×844 截图及原始日志见验收报告。无新增产品缺陷；生产 Nginx/CDN/对象存储 ACL 仍未验证，按 ISS-017 单独跟踪。 后续历史来源438bc5b8526bb43b48445b4646e82ead0b2caaa6的CI41868099905出现既有iss007-attachment-real.spec.js保存成功后立即重开编辑弹窗，原spec第49行5秒未找到已上传文件名且表单内容为空，后两场景未运行；来源未改附件代码，根因UNKNOWN，不能凭后续账单导致0步骤失败称已修。此新增回归失败归本ID，最终集成须保留原断言并真实复核，主审已独立读取GitHub frontend job126707482414原日志确认失败定位，确定性竞态复现继续；来源完整日志待稳定交付归档。 | 等待 ChatGPT 独立复审；生产代理/对象存储访问策略仅由 ISS-017 部署验收。未操作真实历史附件、业务数据库或其他媒体目录。 | R1-ISS007 附件删除/替换 UAT；独立复审前 | 隔离合成目标 DB/文件删除一致、审计操作者正确、旧 URL 拒绝、刷新与替代上传可见、其他合成附件不变；独立复审通过。生产代理/对象存储 ACL 另按 ISS-017 验收。 |
| ISS-008 | FIXED_PENDING_REVIEW | [旧国家报价失败](真实用户E2E-UAT-20260923.md)；[`ISS-008 验收记录`](uat-evidence/iss-008-country-select/README.md)；[`test_issue_008_country_select.py`](../backend/crm/tests/test_issue_008_country_select.py)；[UX2 FR-002](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-24 / `codex/iss-008-country-select` / 实现提交 `90f30d5` | 本轮从 `af018ac63cf71143d223b9f6db4a087707495693` 增量实现本地 249 条 ISO 目录、别名模糊候选、明确选择保存 alpha-2；America 保持歧义不自动保存；历史客户国家文本与导入原值保留。报价新编号使用保存后的代码，历史报价/修订编号不改。后端 871 项全量（跳过13）、ISS-008/报价/客户回归及前端定向测试通过；真实 Chrome 桌面和 390×844 窄屏已核验。 | 独立复审检查国家目录来源、歧义/未知输入、旧数据兼容、报价编号唯一性、权限范围及截图证据；无需批量改写客户资料。 | R1-ISS-008 增量修复 | 本轮完成代码与验收证据后保持 `FIXED_PENDING_REVIEW`；不合并 master、不关闭 Issue，等待统一独立复审。 |
| ISS-008-FUP-01 | P2 / FIXED_PENDING_REVIEW | 本轮统一集成业务复核；来源：用户 2026-10-26 明确要求检查 ISS-008 国家中文别名覆盖；首次发现日期：2026-10-26 | 2026-10-31 / `codex/r1-iss008-aliases-bd324-20261031` / 浏览器测试提交 `dba4a81c10a464012aa004a539a16378f7517b0e`；基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` | 指定基线已包含历史提交中的 249 项 ISO/地区中文名与别名实现；本轮未重复移植生产业务代码。后端 11/11（包含逐项 249 覆盖）、选择器 Vitest 4/4、真实 Chrome 桌面及 390×844 回归 2/2 通过。America 仍要求明确选择，未知旧国家文本保留；历史客户数据、alpha-2/alpha-3 映射、数据库迁移及历史/修订报价编号未改。证据：[FUP-01验收记录](uat-evidence/r1-iss008-aliases-bd324-20261031/README.md)。 | 等待独立代码、目录来源、歧义处理、旧数据兼容及真实截图复审；不关闭记录。 | R1-ISS-008 后续补验 | 独立复核确认 249 项中文搜索覆盖及截图/日志；America 不自动猜测；未知旧值保留；历史客户国家、报价编号及迁移不变；接受后再决定关闭。 |
| ISS-009 | FIXED_PENDING_REVIEW | [UX2 FR-001](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 创建跟进后客户详情刷新而客户列表日期陈旧；已记录修复和真实 Chrome AFTER。 | 前端负责人保留修复；独立复审核对同页无刷新时列表/详情同步。 | UX 第二轮复审 | 修复证据、自动回归与独立复审均通过。 |
| ISS-010 | FIXED_PENDING_REVIEW | [UX2 FR-002](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 空/无效国家报价错误曾只显示英文；已改善中文指引并保留表单，当前有效国家映射仍由 ISS-008 追踪。 | 独立复审验证错误文案和输入保留，不重复扩大国家映射范围。 | UX 第二轮复审 | 错误 UI 回归和独立复审通过；ISS-008 单独关闭。 |
| ISS-011 | FIXED_PENDING_REVIEW | [UX2 FR-003](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 同 SKU 多订单行采购/到货进度容易被解释成重复数量；已记录显示修复和 Chrome AFTER。 | 采购/销售 QA 核对聚合口径和行级身份仍准确。 | UX 第二轮复审 | 同 SKU、多订单真实 UI 和自动回归通过，独立复审接受。 |
| ISS-012 | FIXED_PENDING_REVIEW | [UX2 FR-004](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 部分发货后 readiness 提示不准确；已修复并记录部分发货 Chrome AFTER。 | 销售 QA 验证剩余量/预留量边界。 | UX 第二轮复审 | 足量、部分和不足库存场景均正确，独立复审接受。 |
| ISS-013 | FIXED_PENDING_REVIEW | [UX2 FR-005](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 收货冲销后原库存流水状态显示陈旧；已修复显式关联并有 AFTER 证据。 | 库存 QA 复核原始流水及冲销流水的来回导航和状态。 | UX 第二轮复审 | 重开和当前详情均展示同一冲销关系，测试与独立复审通过。 |
| ISS-014 | FIXED_PENDING_REVIEW | [UX2 FR-006](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 库存流水筛选后返回丢失列表上下文；已修复路由筛选保持。 | 库存 QA 验证搜索、排序、SKU 与返回路径。 | UX 第二轮复审 | 浏览器返回与刷新都恢复筛选上下文，独立复审通过。 |
| ISS-015 | FIXED_PENDING_REVIEW | [UX2 FR-007](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 手工流水冲销后仍打开的原详情状态陈旧；已记录修复后 Chrome AFTER，修复前截图缺失。 | 独立复审以现有原始观察记录和 AFTER 证据评估；不补造 BEFORE 图。 | UX 第二轮复审 | 状态同步回归通过且独立复审明确接受证据限制。 |
| ISS-016 | FIXED_PENDING_REVIEW | [UX2 FR-008](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 新建订单可选预计交期留空时曾报日期格式错误；已修复并有真实 UI AFTER 与自动回归。 | 销售 QA 复核空值、有效日期及错误路径。 | UX 第二轮复审 | 空值按约定保存、有效日期不变、独立复审通过。 |

### P1：生产上线前置风险（当前不进入部署）

| ID | 状态 | 首次发现来源 / 日期 | 最近核实（日期 / HEAD） | 影响与当前证据 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-017 | BLOCKED | [D4-C C-08](r0-d4b2c-api-permission-audit.md)；[D4-C 矩阵](r0-d4b2c-api-permission-matrix.md)；[本轮私有附件验收](uat-evidence/iss-017-private-files/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-24 / 本分支最终 SHA 待交付：独立 worktree 完成认证媒体 API、证书私有上传、旧外部 URL 拒绝、缓存头、Chrome Use 桌面核验、Chrome 通道 13 项含 390px 回归；API 定向 68 tests OK。 | 应用层已收口且本地未授权/静态 `/media/` 场景通过；但仓库没有生产对象存储/CDN/Nginx/反向代理 ACL，生产直链和缓存安全仍无法证明。银行凭证当前是受控 API 中的引用、SHA256 和核实说明，没有可下载文件字段。 | 运维确认存储桶、CDN、反向代理访问策略并完成未授权直链/缓存实测；业务负责人确认历史外部证书链接清理和银行凭证文件化策略。 | 部署前安全验收 | 部署环境配置审计、未授权直链/缓存实测和证书链接策略有记录；安全复审通过。 |
| ISS-018 | BLOCKED | [Phase 4A BLOCKER-DR-01](Phase4-生产化加固审计与实施计划.md)；[ISS-018 隔离演练](uat-evidence/iss-018-backup-recovery/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-27 / `codex/integration-018-036-025` / `46353a5436637832f5adadb7bdef6b45cdeada23` | 原有单归档 SQLite+私有媒体一致性备份、恢复、SHA256、状态记录和 7/4/3 保留计划保持；FIX-01 的 POSIX `0700`/`0600` 权限收口和同文件系统 staging 原子切换继续保留；FIX-02 新增恢复报告路径的原始符号链接检查、拒绝指向目标目录本身或内部、恢复成功与报告写入状态分离，并禁止清理命令为不存在的备份目录自动建目录。定向回归覆盖目标冲突、报告符号链接、失败恢复不创建目标、报告写入失败、非目录/符号链接备份目录和默认 dry-run。后续8087f2c / CI41839476121的真实PG17全量1282通过/30跳过，另同SHA隔离专项15/15、99表1081行128迁移4文件恢复及HTTP4/4；原始证据见integration-closeout-02/baseline-8087-ci-receipt.json。目标部署 PostgreSQL运行角色、生产媒体卷、加密异地副本、定时器/告警和 RPO/RTO 仍为 `DEPLOYMENT_VERIFICATION_PENDING`。  本轮已完整接收Linux稳定来源4a4f338b09e9a464f1e66c24a905c35c970729bf（合并536789f6dbafb2874b1abfd33ade2b30faa123a4）：自填restore_verified_sha256不能授权删除，改为实际解密/恢复后独立签名及root受控公钥信任根。来源CI41866028447与真实Linux专项41866028480各三项SUCCESS，原失败及真实文件见uat-evidence/linux-operations-acceptance-20261104/README.md。集成预审另确认正式CLI默认0600回执无法被分离的保留/监控UID直接读取，旧演练经stdout重写未验证交接；此明确接通缺口归本ID，已授权最小修复及真实跨UID回归，当前不记完成。详见uat-evidence/integration-closeout-02/REVIEW-LINUX-STABLE-SOURCE.md及stable-source-ci-receipt.json。来源成功不是集成或目标部署成功。| 已授权Linux运维包继续一次性真实Linux/受限角色/恢复回执验收；目标环境另行完成 PostgreSQL 与媒体同一恢复点、独立故障域加密副本、自动任务/告警、恢复记录、POSIX/NTFS 权限和金额/库存/附件关系核对；不能用 SQLite 或开发 Windows ACL 代替。 | 部署前运维验收 | 真实备份可恢复且 DB/媒体关系完整，恢复演练、权限、告警、RPO/RTO 与回滚证据经独立复审。 |
| ISS-051 | BLOCKED | [Phase4A production blockers](Phase4-生产化加固审计与实施计划.md)；[AGENTS development identity rule](../AGENTS.md)；[ISS-051配置说明](ISS-051-环境隔离与部署配置.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-26 / 实施提交 `d366224`：独立 worktree 完成开发/生产配置 fail-fast、生产 Session 401 challenge、权限 403、ISS-017 私有附件回归、迁移检查、Django/Node/Vitest/构建及 Chrome Use 桌面/窄屏只读回归。 | 本地代码级安全边界通过；生产默认 DEBUG/开发超级管理员/关闭 RBAC/通配符主机/HTTP 来源/弱密钥/SQLite 均拒绝，生产数据库、媒体目录和密钥配置分离。真实服务器、反向代理 HTTPS、生产 PostgreSQL、Cookie、密钥轮换和正式实名账号仍未验收，保留 `DEPLOYMENT_VERIFICATION_PENDING`。 | 运维/安全负责人按实际目标环境做配置审计；开发超级管理员约定不在本开发任务中更改，生产开关必须在明确部署授权后处理。等待统一独立审查。 | 部署前安全验收（未授权） | 目标环境 secret、DEBUG、APP_STAGE、认证与错误路由配置均满足安全策略，真实部署验收及独立复审通过。 |

### P2：未充分验证、业务待决及体验欠账

| ID | 状态 | 首次发现来源 / 日期 | 最近核实（日期 / HEAD） | 影响与当前证据 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-019 | FIXED_PENDING_REVIEW | [R0-E1 报表覆盖](R0-E1-综合业务回归与内测准备.md)；[D4-C 矩阵](r0-d4b2c-api-permission-matrix.md)；本轮证据：[ISS-019 CSV 准确性复核](uat-evidence/iss-019-report-csv/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-24 / `cb2a90d36dbbecc062becbf13d879703b6856456` | 已取得真实 CSV 字节并与同条件 API 对账：金额 145、去重单据 2、数量按 `pcs`/`box` 分开；UTF-8 BOM 和公式注入防护通过；Chrome 验证未提交筛选不影响导出。确认的缺陷是 RBAC `export=true`、`reports.view=false` 时直接 CSV API 未在函数内复核查看权限；已新增 `reports.view` 检查和回归。ISS-041/042/048/062/107 既有口径保持。 | 等待独立代码与权限复审；不关闭 Issue。 | R0-E1 补验 | 多种报表来源的文件内容与 UI/API 聚合一致；view-only 和无 report view 的导出均被拒；正向下载真实 HTTP 与文件通过。 |
| ISS-020 | FIXED_PENDING_REVIEW | [R0-E1 Quote/PI 覆盖](R0-E1-综合业务回归与内测准备.md)；[Round1 PI Re-UAT](UAT-Round1-正式业务全流程测试.md)；本轮证据：[ISS-020 导出一致性](uat-evidence/iss-020-quote-export/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-26 / `codex/iss-020-quote-export`，基线 `28ba758388429f57c2e3516e12385a88ce6646a3` | 先行复现确认关键买方/币种缺失仍能 200 导出、逐行金额舍入会让预览与 XLSX 小计不一致；已最小修复为保存版本 DTO 校验、422 字段提示、预览/XLSX 共用金额和图片快照。两个历史版本实际 XLSX/API、历史主档改动后图片/型号/收件人、空邮箱、无权 403 和跨客户拒绝已核对；Chrome Use 桌面及 390px 窄屏截图已完成，浏览器下载事件另标注未返回。  INTEGRATION-CLOSEOUT-02确认原浏览器saveAs canceled为下载生命周期时序缺口；02140bf46df27ba1abf5b9018507c07aae825769仅将报价anchor/Blob URL共同延后清理，原场景1/1及额外实际Google Chrome1/1通过，保存XLSX由openpyxl核对合成编号/型号/数量/单价；最终同SHA全量仍执行，独立复审未完成。证据：integration-closeout-02/download-investigation-20261105/DOWNLOAD-CANCELLATION-INVESTIGATION.md。  最终02140适用Playwright实际262通过1失败：本报价场景仍saveAs canceled，前述单次定向通过不能证明彻底修复；该浏览器交付子项FIX REQUIRED，由统一集成继续调查，不关闭Issue。 | 等待独立代码、权限、实际文件和视觉复审；不关闭 Issue。 | R0-E1 补验 | 实际文件可打开、内容与保存版本一致；历史图片不随 SKU 现图变化；独立复审通过。 |
| ISS-052 | FIXED_PENDING_REVIEW | [R0-E1 import coverage](R0-E1-综合业务回归与内测准备.md)；[R0-C3 Safe CSV Import](R0-C3-Safe-CSV-Import.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-31 / 分支 `codex/r1-iss052-audit-hardening-20261031`；实现提交 `ab9ce886094a065766a24b35d9b82c7a7c0fd067`，基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c`。合入来源 `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b`、`8cff96af9f1f2e09dcbc0a29f361017ee23ffb75`、`f2b7fd6487459be69be687ccfeab09e7947df995` 及前置父提交 `a6c5b56a00326234681399a3405efa2117198f76`。CSV 限额/HTTP 413 与导入预览、批次、行级审计链均保留；SQLite 全量回归 1041 项（1021 通过、20 跳过、0 失败），定向 36 项（35 通过、1 项 PostgreSQL 专项跳过）。此句所述历史时点已被后续8087f2c / CI41839476121更新：0091–0094迁移与PG raw SQL审计/回退用例纳入真实PG17全量1282通过/30跳过，0失败；集成Playwright270（混合通道）/270。原历史SQLite结果不冒称新PG结果。 | 历史台账结论保留：2026-10-27 / `codex/verify-iss052-csv-import` / 精确来源 SHA `93736e0773ca2136d4070a604e62324cf832dc6f`：隔离 SQLite、合成数据下四类导入真实 UI 上传/预览/确认执行和 HTTP/数据库核对均有验收记录；七张真实 Chrome JPEG 原图已在集成分支更名为 `.jpg`，未重编码。历史状态对账时曾记录开发身份 `authenticated=false`、`AUDIT_LOG_ENABLED=false`、`OperationLog=0`；本轮之后已补充认证执行人审计及批次/行级审计。证据：[历史 CSV 导入报告](uat-evidence/iss-052-csv-import-verification/README.md)、[集成复核报告](uat-evidence/integration-036-002-003-052-058/README.md)及[本轮报告](uat-evidence/r1-iss052-audit-hardening-20261031/README.md)。 | 当前实现保留失败解析、失败执行、重试和成功批次之间的预览/批次/行审计外键与操作人；审计写失败回滚业务写入。PostgreSQL `CSVImportBatch`、`CSVImportRowAudit`、`CSVImportPreviewAudit` 的原始 SQL UPDATE/DELETE/TRUNCATE 测试已纳入套件，但本轮 SQLite 测试不能证明 PostgreSQL 触发器运行行为。历史四类导入 UI 验收、SKU/客户敏感资料范围与已记录的导入数据映射结论不作扩展。 | 等待独立复审；具备专用隔离 PostgreSQL 时运行新增原始 SQL 测试及 0091/0093/0094 正反向迁移核对，并记录触发器拒绝证据。不得连接真实业务数据库、启用正式 RBAC 或自行关闭 Issue。 | R1 ISS-052 审计加固 / PostgreSQL 与独立复审待验 | 四类导入 UI/API 与 CSV 历史行为保持；解析、执行失败、重试、成功、真实认证操作人、事务回滚及三张表数据库追加保护通过；迁移回退不静默删除审计历史；独立审查后再决定关闭。 |
| ISS-021 | FIXED_PENDING_REVIEW | [R0-E1 ContractChange](R0-E1-综合业务回归与内测准备.md)；[Phase3 UI COVERAGE GAP-01](Phase3-业务流程与异常UAT计划.md)；首次日期：UNKNOWN；本轮依据用户 2026-10-24 规则包 ISS-021 原文及明确任务，不引入复杂审批 | 2026-10-26 / `codex/next-iss-021-integration`，基线 `b3559f3bf83b967d06166bd409b00fc92e4e5902` | 已按差异迁移正式 SO 数量变更、版本/幂等、历史与专用 UI；新增 0085 接续 0084，既有迁移及 ISS-037 快照保留。全量 904、定向 38、Node 151、Vitest 650 通过；真实 API/内置浏览器和数据库事实哈希见[验收证据](uat-evidence/iss-021-integration/README.md)。Chrome 连接冲突后经用户授权改用内置浏览器；本地 PostgreSQL 未验证 | 独立审查人员核对业务、迁移、权限、截图与最终提交 CI；不得自动关闭 | 本轮独立集成，等待统一独立审查 | 增减、已发货下限、付款保护、采购人工处理、回滚、冲突、审计和主体快照复核接受；不改已有资金/库存事实；由用户或独立审查决定关闭 |
| ISS-022 | FIXED_PENDING_REVIEW | [Phase3 POLICY GAP-01](Phase3-业务流程与异常UAT计划.md)；[Task C](TaskC-订单采购草稿闭环.md)；[R0-E1 P2](R0-E1-综合业务回归与内测准备.md)；用户 2026-10-24 规则包 ISS-022；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / `codex/repair-supplier-purchase-ux-r2` 精确来源 SHA `64fb397aa065062e192ceb30040421f59b63a08c`，集成真实隔离 API/Chrome MOQ 场景 1/1 通过；全量浏览器套件中的对应 spec 亦通过。截图和日志见 [本轮集成报告](uat-evidence/integration-r1-repairs-20261028/README.md)。 | 用户已明确 MOQ 按同供应商、同真实 PO、同适用 SKU/采购单位合计，低于 MOQ 为可填写原因的软提醒。等于 MOQ 可正常继续；低于 MOQ 显示软提醒，正式下单时须提供例外原因；取消例外仍保留草稿。价格、内部参考成本、采购状态值和生命周期规则不变。 | 保持 FIXED_PENDING_REVIEW，等待独立代码、业务、权限和视觉复审；不关闭 Issue。 | 历史业务待决转专项复核 | 低于/等于/高于、共享 PO 合计、单位换算、无 MOQ、越过原因/时间/操作员/采购单、权限和成本不变均经独立审查接受后再决定关闭。 |
| ISS-023 | FIXED_PENDING_REVIEW | [R0-E1 SKU 覆盖](R0-E1-综合业务回归与内测准备.md)；用户 2026-10-24 规则包；本轮证据：[ISS-023 Sales Model 验收](uat-evidence/iss-023-sales-model/README.md)、[统一集成验收](uat-evidence/integration-043-075-023/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-26 / `codex/integration-043-075-023`，源提交 `c6a1415437fb2a020ec31d655fe8ce274aa93912`，基线 `f12b591cb90d6a5d8ebfedf1c559703377c92d84` | 已修复参数变更时自动预览覆盖人工保存型号的缺口；自动型号仍仅在保存值与旧生成值一致时刷新，人工型号和明确空型号保留。SKU 身份、报价/订单/采购商品快照、PI/XLSX 导出和权限入口不变；Chrome 窄屏菜单收起可用性已通过。真实生产 SKU 型号完整性仍为 `BUSINESS_VERIFICATION_PENDING`，未批量改写旧数据。 | 等待独立代码、业务、权限、数据与视觉复审；业务负责人另行抽查真实产品前缀和型号完整性，不关闭 Issue。 | SKU 主数据与身份安全复核 | 自动/人工/历史空型号及参数变化均符合规则；报价、订单、采购商品和 PI 历史快照不变；真实代表性 SKU 抽查与独立复审通过。 |
| ISS-024 | FIXED_PENDING_REVIEW | [R0-E1 供应来源覆盖](R0-E1-综合业务回归与内测准备.md)；[E2E 供应来源说明](真实用户E2E-UAT-20260923.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；采购推荐成果 `1d576e961dc021d194e0ec2f9fd7dd6fc629535d`，集成验收基线 `b3559f3bf83b967d06166bd409b00fc92e4e5902`。客户+SKU推荐、一次性来源、客户长期偏好、停用过滤和成本口径已有证据；将滞后 OPEN 校准为 FIXED_PENDING_REVIEW，仍待独立业务/代码复审，不关闭。历史台账结论保留：UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | Supplier Source 是 SKU 级采购候选前置条件；只建供应商主档不会自动为每个 SKU 生成候选，容易导致采购草稿没有可选来源。 本轮仅做状态对账，不扩大为生产/正式员工验收。 | 采购负责人逐 SKU 建立/核对供应来源；培训材料简明说明配置位置与候选范围。 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | 内测数据准备 | 目标 SKU 采购候选清单核验完成，操作人员能按说明找到并选择来源。 |
| ISS-025 | FIXED_PENDING_REVIEW | [UX2 客户阶段标识](Product-UX-Second-Review.md)；[R0-E1 P2](R0-E1-综合业务回归与内测准备.md)；2026-10-24 用户规则包；[原验收证据](uat-evidence/iss-025-customer-status-labels/README.md)；[ISS-025-FIX-01 全页面核查](uat-evidence/review-iss025-status-consistency/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-27 / `codex/iss025-report-visual-evidence` / 证据提交 `f9e2c7493ba86007fb6969d826d336dc4077edb7`，基于 `d5d0d15c03d55a718f11a298e08f29a9b9d0c4b0` 的本轮真实 Chrome 视觉补验；新截图及 API/窄屏测量见 [ISS-025-FIX-02 证据](uat-evidence/review-iss025-status-consistency/README.md) | 已核实源分支的列表、详情、筛选、关联企业、跟进和客户 API 映射正确；经营分析按状态分组在隔离数据下实际显示五个规范中文标签，`lead/contact/opportunity/customer/company` 与“线索/已联系/商机/正式客户/返单客户”一致；报表区域无“联系人”“公司客户”，销售/采购/财务状态名称未改动。保留原始状态代码、数据库迁移、自动推进、联系人数量规则及历史跟进/报价资料；筛选和 URL 恢复兼容。 | 等待独立代码、业务、权限和视觉复审；“商机/正式客户/返单客户”的简化措辞登记为 `BUSINESS_VERIFICATION_PENDING`，真实生产数据、员工权限和部署环境另行核验，不自行关闭 Issue。 | 后续 UX 与业务措辞复核 | 客户列表、详情、关联企业、筛选、跟进、报表/API 及刷新/URL 恢复显示一致；状态代码、筛选 URL、历史资料和事件推动逻辑不变；独立复审通过。 |
| ISS-026 | FIXED_PENDING_REVIEW | [Round1 SUP04](UAT-Round1-正式业务全流程测试.md)；本轮专项规则与验收：2026-10-24 | 2026-10-24 / `codex/iss-026-supplier-lifecycle`：供应商新增 `is_active` 生命周期；API 永久删除统一 405；启用/停用事务审计、候选过滤、新采购拦截、历史采购/付款/来源保留及前端生命周期操作均通过；证据见 [ISS-026 验收](uat-evidence/iss-026-supplier-lifecycle/README.md)。 | 供应商不得通过普通业务路径硬删除；停用供应商不进入新采购候选，历史主体和关联记录仍可读。 | ChatGPT 独立代码、权限、历史数据和视觉复审；不得以本轮结果自行关闭 Issue。 | 历史 Issue 集中核实阶段 | 有无历史采购均拒绝 DELETE；停用/启用、候选过滤、历史查看、API 权限、审计及真实 UI 通过；独立复审接受后再关闭。 |
| ISS-027 | FIXED_PENDING_REVIEW | [真实用户 E2E P2](真实用户E2E-UAT-20260923.md)；[R0-C1](R0-C1-Followup-Safety.md)；2026-10-24 用户规则包；首次日期：UNKNOWN | 2026-10-26；统一集成分支 `codex/integration-021-029-027` | 已复用三种跟进安排，补修非法分段日期误提交旧值、keep 重放历史覆盖当前计划。统一集成后后端全量911（跳过13）、定向104、Node151、有效Vitest656及构建通过；真实 Chrome 已完成保存、改期、清除、非法日期、保存失败重试、客户列表同步和桌面/390×844截图。证据见[统一集成验收](uat-evidence/integration-021-029-027/README.md)。 | 等待独立代码、权限、业务与视觉复审，不自行关闭 | CRM UX；本地 PostgreSQL/精确 HEAD CI 待环境恢复 | 空值/清除规则明确，历史日期不改，UI/API一致；独立复审接受后再决定关闭。 |
| ISS-028 | FIXED_PENDING_REVIEW | [真实用户 E2E P2](真实用户E2E-UAT-20260923.md)；[业务回归报告](业务流程与修改回归测试报告-20260922.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-11-04 核对已验8087f2c68b19a302a25e814ec8ce6113d91d4750：集成修复47fcab0f6f37f52475074e65ab7ab188352ae8ce已含根分类直接选择、属性继承及真实HTTP/截图证据（uat-evidence/iss-028-035-category-schema/）；当前基线CI三项成功，等待独立复审。历史时点记录（不再作为当前未修复结论）：2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；`codex/verify-iss028-035-category-schema` 当前仅指向该基线，未形成修复提交。本轮未把旧分类报告当作当前缺陷，保持 NEEDS_VERIFICATION，等待隔离样本复现。 历史台账结论保留：UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测）；最终集成CI41839476121三项SUCCESS，独立复审未完成。 | 47fcab0f6f37f52475074e65ab7ab188352ae8ce的根/子分类、属性继承及SKU保存修复已包含；最新CI与实际分类/SKU图像可复核，不按旧E1未测记录重复开发。 | 等待ChatGPT独立复核当前代码、已有正常/拒绝路径及实际证据；不重复开发。原计划记录：产品 QA 以根分类和子分类分别建产品、重开并检查分类、属性继承及过滤。 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | 后续产品主数据回归 | 两类分类归属/继承符合当前规则，自动回归与真实 UI 通过。 |
| ISS-029 | FIXED_PENDING_REVIEW | [真实用户 E2E P2](真实用户E2E-UAT-20260923.md)；[Task H1 快照规则](TaskH1-客户跟进报价链路.md)；2026-10-24 用户规则包 ISS-029；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / R1-REPAIR-03 精确来源 SHA `c3739e77562c5dd8995228d5c3e7375a6728d316`；集成后历史订单收件人及 ISS-029 API/XLSX 浏览器场景分别 2/2、1/1 通过，真实浏览器证据见 [本轮集成报告](uat-evidence/integration-r1-repairs-20261028/README.md) 与 [来源验收记录](uat-evidence/r1-repair-03-history-recipient-typography/README.md)。 | 创建时空邮箱不得被主联系人替代，异步预填不得覆盖手填/较新客户资料。复用既有 Quote 字段与修订链，无新模型/迁移；本轮仍核对主档修改后 PI/XLSX 版本资料、空邮箱保留及历史收件人快照。 | 保持 FIXED_PENDING_REVIEW，等待独立代码、权限及实际文件/视觉复审，不自行关闭；CI 按最终提交核对。 | 单据快照校验 | Quote/API/PI/实际 XLSX 四字段及版本号一致；手填不回写主档，空邮箱保留、错误邮箱原子拒绝、历史版本不变；独立审查接受。 |
| ISS-030 | FIXED_PENDING_REVIEW | [UX2 Final Polish](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 只读汇率/单位成本小数末尾零显示已规范化，不改数值；有自动测试和真实页面证据。 | 独立复审检查可读性和精度不变。 | UX 第二轮复审 | 独立复审确认展示简化且无精度/业务值变化。 |
| ISS-031 | FIXED_PENDING_REVIEW | [UX2 Final Polish](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 订单/采购草稿重复确认入口已收敛；无重复业务提交被观察到。 | 独立复审检查保留主操作和待办信息。 | UX 第二轮复审 | 页面路径及业务动作回归通过，独立复审接受。 |
| ISS-032 | FIXED_PENDING_REVIEW | [UX2 Final Polish](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 订单完成/取消与采购缺口 helper 文案已按状态调整；E1 另确认完成订单欠款催收任务仍缺，见 ISS-001。 | 独立复审区分 helper 文案与待办业务缺口，不以此关闭 ISS-001。 | UX 第二轮复审 | 状态提示准确、ISS-001 独立解决后复审。 |
| ISS-033 | FIXED_PENDING_REVIEW | [UX2 Final Polish](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 报价/订单明细名称、SKU 和交易/基础数量层级及间距已调整；保存值不变。 | 独立复审查看窄宽视口与长编号。 | UX 第二轮复审 | 视觉层级可读、内容无裁切，自动与人工复审通过。 |
| ISS-034 | FIXED_PENDING_REVIEW | [UX2 Final Polish](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 已保存 PI 预览标题区分编辑草稿与历史报价；金额和导出逻辑未改。 | 独立复审核对已保存/未保存两种状态。 | UX 第二轮复审 | 两种预览状态正确，独立复审通过。 |
| ISS-035 | FIXED_PENDING_REVIEW | [Phase4 UX ISSUE-01](Phase4-生产化加固审计与实施计划.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-11-04 核对已验8087f2c68b19a302a25e814ec8ce6113d91d4750：47fcab0f6f37f52475074e65ab7ab188352ae8ce已含分类模板变化、SKU保存重开、API/数据库快照及桌面/窄屏证据（uat-evidence/iss-028-035-category-schema/）；等待独立复审。历史时点记录（不再作为当前未修复结论）：2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；与 ISS-028 同批验证尚未形成修复提交。本轮未改写已发布 SKU，保持 NEEDS_VERIFICATION，等待历史 SKU/模板样本。 历史台账结论保留：UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测）；最终集成CI41839476121三项SUCCESS，独立复审未完成。 | 同一分类/SKU来源47fcab0f6f37f52475074e65ab7ab188352ae8ce已包含schema/分类模板一致性修复；当前为已有实现待独立复审，不将旧审计“可能改变、未找到关闭”当作未开发。 | 等待ChatGPT独立复核当前代码、已有正常/拒绝路径及实际证据；不重复开发。原计划记录：产品 QA 在已发布 schema 和模板变更各做一次真实 UI 操作，检查影响说明和确认语义。 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | 后续产品 UX 复核 | 当前两处提示一致准确，避免用户误解已发布 SKU 影响；独立复审通过。 |
| ISS-036 | FIXED_PENDING_REVIEW | [Phase4 UX ISSUE-02](Phase4-生产化加固审计与实施计划.md)；[ISS-036 验收记录](uat-evidence/iss036/README.md)；[ISS-036-FIX-01 验收记录](uat-evidence/iss036-fix01/README.md)；[ISS-036-FIX-02 验收记录](uat-evidence/iss036-fix02/README.md)；[ISS-036-FIX-03 验收记录](uat-evidence/iss036-fix03/README.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-27 / `codex/fix-iss036-snapshot-conflicts` / 精确来源 SHA `b64c54b07908d4bb462c64f120c351d148e06f6f` | 最终指定提交保留完整快照语义键修复与装箱回归：`factor`、`base_unit`、`unit`、`allow_fraction` 一致才作为同一语义；缺失、无效或冲突快照不推断不可拆分规则。`factor=1/5`、允许分数、尾箱、混装及历史异常证据保留；业务数量、库存、订单/财务金额、采购状态和付款规则不改。集成后的全量回归及构建结果见[本轮集成报告](uat-evidence/integration-036-002-003-052-058/README.md)。 | 保持 FIXED_PENDING_REVIEW，等待独立代码、业务和视觉复审；真实 PostgreSQL、代理、真实物流数据和最终 CI 状态另行核验。冲突快照的业务归属/优先级仍待明确。 | R1 集成 / 后续采购包装复核 | 不完整或冲突历史快照不触发 500 或擅自限制；语义完全一致的有效快照仍执行限制；允许分数、尾箱、合法混装和基础单位数量守恒；独立复审接受。 |
| ISS-037 | NEEDS_VERIFICATION | [Product Completion Review §snapshot](Product-Completion-Review-Phase1.md)；[UX2 snapshot checks](Product-UX-Second-Review.md)；首次日期：UNKNOWN | 2026-11-03 / 审查源码`8d3ca5f`；[独立审查](uat-evidence/r1-iss037-snapshot-audit-20261103/README.md)及[本轮补修/集成](uat-evidence/r1-rule-gap-fix-batch-20261103/README.md)  本轮只读候选补充：财务包CI41857369306（源码3c34d9e121e751af39267fc28338bf2233178fc3）既有原生打印spec第74行1440px/headers=false发生30秒超时，主业务套件244通过/1失败，构建未执行；根因UNKNOWN。完整原始发布日志在候选2e20bfdccb711bdd5f9028cb60e287ee742c77c5:docs/uat-evidence/finance-adversarial-review-20261104/ci-frontend-print-timeout.published.log及manifest中，当前仅Git对象只读审查尚未接收来源。不将前后绿色解释为稳定性已修，打印完整成品/分页仍按用户决定延期，不追加原生打印或催办，保留全量CI原断言。| 已有销售订单六项客户/采购单五项供应商及报价买方、商品、图片快照；正式历史使用对应版本规则已确认，旧“当前主档还是快照待决”已过时。本轮只修历史空买方被新修订静默填入；卖方/模板冻结、完整双方字段、历史迁移来源可信度、主体版本与审批分离仍未覆盖。 | 后端/业务QA按独立报告逐项验收已有实现和本轮空值修订，再实施剩余范围；不重复开发六/五项快照，不批量填历史，不解除正式只读。 | 定向补修待复审 / 后续完整主体治理 | 普通与订单触发修订保留未知和非空旧值；新建预填/显式空值/正式导出校验/旧版不变/回滚通过；剩余主体要求逐项补证并独立接受后方可整体关闭。 |
| ISS-038 | BLOCKED | [D4-B2-A Finance](r0-d4b2a-finance-scope.md)；[focused repair](r0-d4b2a-focused-repair.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 一部分历史销售类型流水缺客户、订单或计划关联，当前数据结构不能安全推断归属。受限用户已按规则隐藏；all+相应模块权限人员可查。 | 财务负责人逐笔核对原始业务凭证，决定补充关联还是确认公共费用；禁止按备注/参考号自动猜测或改历史金额。 | 财务数据治理（获业务授权后） | 每笔记录由业务凭证确认归属并留审计；无法确认者继续保留受限访问策略，不假定为已关闭。 |
| ISS-039 | FIXED_PENDING_REVIEW | [D4-B2-B Procurement](r0-d4b2b-procurement-scope.md)；首次日期：UNKNOWN | 2026-11-03 / [独立审查](uat-evidence/r1-iss039-shared-cost-audit-20261103/README.md)；源码`8d3ca5f`已具备采购修改权限跨销售分配，详见[本轮补修/集成](uat-evidence/r1-rule-gap-fix-batch-20261103/README.md) | 旧逐SO委托阻断已由后续实现和明确规则取代：purchases.update可跨销售分配，不要求orders.view/update；只读仍拒绝且敏感资料脱敏。本轮补修新费用仅amount、历史quantity原法读取、主动确认预览转换、零基数安全拒绝；不自动改历史。 | 采购QA/独立审查按真实HTTP/桌面390px、比例909.09/90.91、权限、守恒、版本冲突、审计回滚及预留重算证据复核；正式身份/部署边界继续保留，不恢复逐SO授权。 | 本轮金额法补修待独立复审 | 新quantity请求400无副作用；历史读取/取消不变、明确确认和预览后保存有前后审计；无额外资金库存流水、尾差守恒、零费用合法分配；精确SHA综合回归和独立接受，不自行关闭。 |
| ISS-043 | BLOCKED | [Phase4 `RISK-AUDIT-01`](Phase4-生产化加固审计与实施计划.md)；2026-10-24规则原文；本轮复核 2026-10-26 | `codex/integration-043-075-023`，源提交 `dea057ce0c98fc32da44b72999beb4af78a58176`，基线 `f12b591cb90d6a5d8ebfedf1c559703377c92d84`：已补 admin/ORM 保护、0088 PostgreSQL 触发器、0089 操作人 PROTECT 和非开发审计 fail-fast；定向及全量 SQLite 回归通过。后续8087f2c / CI41839476121的PG17审计触发器拒绝及迁移用例已执行，全量1282通过/30跳过；不等于真实最小权限角色或生产验收。真实生产运行账号、角色继承及目标备份恢复仍为 `DEPLOYMENT_VERIFICATION_PENDING`。 | 运维/安全负责人按 [ISS-043 验收证据](uat-evidence/iss-043-audit-protection/README.md)、[统一集成验收](uat-evidence/integration-043-075-023/README.md) 和 [PostgreSQL runbook](deployment/ISS-043-PostgreSQL审计防篡改.md) 在隔离 staging/生产前实测运行账号权限、触发器、备份恢复和独立维护留痕；不得以 SQLite 代替。 | 部署前审计加固 | 应用 UI/API/admin/ORM 正常与拒绝路径通过；实际 PostgreSQL 运行账号不能 UPDATE/DELETE，备份可恢复，特殊维护有独立授权和额外审计；最终精确 HEAD CI 可核对；经独立复审后再改变状态。 |
| ISS-044 | NEEDS_VERIFICATION | [Phase4B `DATA-MIGRATION-RISK-01`](Phase4B-PostgreSQL兼容性执行记录.md)；[Phase4A PostgreSQL risk](Phase4-生产化加固审计与实施计划.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | PostgreSQL 17 CI 及并发测试通过；生产数据迁移演练未做。旧风险特别要求迁移前扫描真实数据 `Supplier.code` 是否超过 2 字符，且禁止静默截断；staging 业务数据、金额/库存和恢复流程仍未核实。 | DBA/运维用只读检查报告异常，再在隔离 staging 演练迁移和序列校准；不可改开发库或擅自迁移。 | 迁移/部署准备（尚未授权） | staging migration、行数、金额、库存、编码映射、序列和回滚校验均通过，独立复审接受。 |
| ISS-045 | FIXED_PENDING_REVIEW | [Phase3 `LTD-02/04/06`](Phase3-业务流程与异常UAT计划.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-11-04 核对已验8087f2c68b19a302a25e814ec8ce6113d91d4750：72a6b27f3f855424f16cd9657996055c68b5ca95退役旧流程命令并保留历史源码；6ec1a50ee14fd17a64de4f68cd63e2b2c426b47b限制seed_demo开发SQLite/已验证隔离目标、额外alias和非默认路径；test_legacy_qa_tools纳入当前全量。证据uat-evidence/r1-iss045-qa-tools-bd324-20261031/README.md。待独立复审，不将历史脚本成功作为业务闭环。历史时点记录：UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测）；最终集成CI41839476121三项SUCCESS，独立复审未完成。 | 历史两套业务脚本已经安全退役并保留源码/证据；seed_demo已有开发隔离限制，CI不将旧脚本作为正式门禁。72a6b27f3f855424f16cd9657996055c68b5ca95及6ec1a50ee14fd17a64de4f68cd63e2b2c426b47b已包含，待独立接受安全边界，不重新实现旧业务脚本。 | 等待ChatGPT独立复核当前代码、已有正常/拒绝路径及实际证据；不重复开发。原计划记录：QA/开发确定保留、更新或废弃；在其完成前以当前 UI/API/自动测试为验收源。 | QA 工具维护 | 脚本与当前业务约束同步并通过对照，或明确下线且 CI/文档不再把它当门禁。 |
| ISS-046 | BLOCKED | [D4-C final evidence](r0-d4b2c-api-permission-matrix.md)；[R0-E1 evidence limitation](R0-E1-综合业务回归与内测准备.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | R0-D4-C 截图上传在浏览器策略下被拒；E1 截图仅在内置浏览器查看，没有独立文件。禁止绕过浏览器安全策略；这不否认已记录的 HTTP/UI 结果，但限制离线视觉复审。 | 复审人使用应用允许的证据附件方式，或接受文本/HTTP 可验证记录；不得从浏览器原始命令导出。 | 独立复审证据整理 | 在合规方式下形成可访问证据或独立审查明确接受限制；不伪造截图。 |
| ISS-047 | BLOCKED | [Phase4 `RISK-MEDIA-01`](Phase4-生产化加固审计与实施计划.md)；[D4-C C-08](r0-d4b2c-api-permission-audit.md)；[ISS-047 验收记录](uat-evidence/iss-047-private-storage/README.md)；[单服务器私有文件存储交接说明](deployment/ISS-047-单服务器私有文件存储.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-26 / 基于 `8b2b5c19e517addd9604b239211e199a789b739e` 的 `codex/iss-047-private-storage`：应用层私有媒体回归、路径穿越/静态直链拒绝、生产 `MEDIA_ROOT` fail-fast、媒体根与静态根隔离、服务重启模拟、SHA256 清单及恢复核对接口已实现并定向验证；最终 SHA 见交付消息 | 当前确定单服务器独立持久化私有媒体卷，Django storage 抽象和 `private_media_manifest` 为 ISS-018 联合备份及未来对象存储迁移预留接口；没有添加 `/media/` 静态路由。真实生产卷、Nginx/反向代理 ACL、容量告警和 PostgreSQL+媒体联合恢复仍未验证。 | 运维在隔离目标环境配置绝对持久 `MEDIA_ROOT`，完成服务重启、磁盘/inode 告警、Nginx 直链拒绝及 DB+media 联合备份恢复；确认备份副本独立故障域。 | 部署架构评审 | 目标拓扑、恢复策略、媒体权限和容量/完整性测试经独立复审接受后再改变状态。 |
| ISS-053 | NEEDS_VERIFICATION | ChatGPT 历史独立审查（R0-D4B2-A；未入 GitHub 问题记录；发现日期 UNKNOWN）；[财务范围记录](r0-d4b2a-finance-scope.md)；本轮证据：[ISS-053 采购状态核实](uat-evidence/iss-053-purchase-status/README.md) | 2026-10-23 / c356e57014d28295485d52df23612c2fe6c02444：独立 worktree 完成 API 状态矩阵、采购列表/详情/编辑/筛选、销售订单关联采购单真实 Chrome 验证；后端 39 项、前端 Vitest 52 项、Chrome Playwright 11 项及生产构建通过。 | 当前未确认显示缺陷：`ordered` API/存储值保持英文，采购列表、详情、编辑工作台、状态筛选、采购实体上下文和销售订单关联采购单均显示“已下单”；其他状态也均返回并显示对应中文。历史英文 `ordered` 在当前基线未复现，因无法重建历史现场，暂记为当前未复现的历史报告，不自行判定关闭。 | 等待统一独立代码、权限、API 与视觉复审；若复审发现历史入口仍有英文，再按证据最小修复。负责人：采购 QA / 前端。 | R0-E1 补验（本轮证据已归档） | ordered 在所有受测采购入口显示“已下单”，筛选/存储值仍为 ordered；API 与 UI 回归和独立复审通过。 |
| ISS-054 | FIXED_PENDING_REVIEW | ChatGPT 历史独立审查（R0-D4B2-B；未入 GitHub 问题记录；发现日期 UNKNOWN）；当前代码：frontend/src/views/PurchaseOrderPage.vue | 2026-10-13 / ecdc9bc：只读检查 openReceiptReversal、submitReceiptReversal、反馈模板及现有收货测试；未运行测试。；2026-10-18 R1-A：真实复现旧收货成功残留；已清冲销打开/提交前旧反馈与错误，成功/失败/重试回归及内置浏览器、Chrome原图完成；后端计算不改。 证据：[R1-A报告](R1-A-核心业务历史Issue核实与修复.md)。 | 旧收货成功提示残留已修复：当前openReceiptReversal和submitReceiptReversal均清除receiptSuccess及旧notice/error；打开、成功、失败和重试的既有回归/原图可复核，不把旧只读缺陷描述为当前代码。 | 独立复核先成功收货再打开/提交冲销、失败重试反馈，仅最新动作呈现；复用R1-A与当前PurchaseOrderPage.vue及purchase-editor-receipt测试，不重做已修前端功能。 | 既有采购反馈修复待独立复审 | 连续完成收货和冲销时只显示与最新动作一致的成功状态；失败不残留虚假成功提示；测试及独立复审通过。 |
| ISS-055 | FIXED_PENDING_REVIEW | ChatGPT 历史独立审查（R0-D4B1；未入 GitHub 问题记录；发现日期 UNKNOWN）；当前代码：backend/crm/views.py、frontend/src/utils/apiErrors.js | 2026-10-28 / 集成基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` 继续包含 `9c5f1f821cfc1b436f5fffe0b681991fa056b34d`。中文安全 404 和合成隔离 API/Chrome 证据保持有效；正式 RBAC、真实员工会话和独立复审未执行，保持 FIXED_PENDING_REVIEW。 历史台账结论保留：2026-10-28 / R1-REPAIR-05 `codex/fix-iss055-chinese-404` 精确 SHA `9c5f1f821cfc1b436f5fffe0b681991fa056b34d`。真实 Chrome 桌面/窄屏证据及合成隔离 API 回归见 [ISS-055 验收记录](uat-evidence/iss-055-customer-404/README.md)；本轮 Django 全量、Node 单测通过。 | 越权对象继续返回 404，不泄露客户是否存在；未命中和无权访问映射为简洁通用中文提示，不显示模型英文名。真实员工/RBAC 浏览器 spec 因本轮禁止启用正式 RBAC 未运行，不能将开发身份浏览器或合成 API 证据扩大为真实员工权限验收。 本轮仅做状态对账，不扩大为生产/正式员工验收。 | 保持 FIXED_PENDING_REVIEW，等待独立代码、隐私/权限及视觉复审；在获授权的隔离 RBAC 环境补充真实员工会话 UI/API 验收后再决定是否关闭。 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | R1 集成 / RBAC 授权环境补验 | 越权详情仍为 404；授权/未授权/未知对象提示均为自然中文且不泄露对象存在性；真实员工数据范围和独立审查通过。 |
| ISS-057 | P2 / FIXED_PENDING_REVIEW | [R0-F1 前端 UX 覆盖盘点](R0-F1-前端UX覆盖盘点.md)；首次发现：2026-10-13，本轮财务页基线实测 | 2026-10-14 / 实现提交 `439b5b3`、CI #38426397966 三项 SUCCESS；Node 121/121、Vitest 494/494、财务/报表后端 76/76、销售范围后端 28/28；Codex 内置浏览器完成财务列表、新增、收付款、核销、作废和概览路径  R0-F9新增当前27路由基线与原图索引，归档已实际完成；仍有ISS-100尺寸限制及历史特定状态/独立图片待审，不能据新图自行关闭。| 财务流水及收付款计划过滤原先缺少统一显式提交/可恢复 URL 状态；财务概览把期间数值与当前余额混排，且部分保存/核销结果反馈不足。本轮已调整页面结构、路由查询状态、字段分组、状态反馈和统计口径说明；财务计算与后端规则未改。截图不能通过当前受支持浏览器接口保存，归档状态 BLOCKED；原轮未完成多尺寸核验；2026-10-14 定向复修现已完成应收/应付 1440、1280、1024、640、390px Chrome 计算布局回归与内置浏览器视觉检查，见 [定向复修记录](R0-F1-定向复修验收.md)。2026-10-14 用户确认代码及已覆盖交互独立复审 PASS，允许有条件封版；截图独立视觉证据缺口仍保留，ISS-057 不关闭。  R0-F9下一步：独立审图明确接受覆盖范围；对未接受的状态/尺寸使用受支持接口重拍。| 代码及已覆盖交互已独立复审 PASS；仅待补独立截图视觉证据或审查人明确接受限制，保持 FIXED_PENDING_REVIEW。负责人：前端 QA / 独立审查。 | R0-F1 财务 Part | 精确提交 HEAD 的 Backend、Backend PostgreSQL、Frontend CI 成功；财务页面主要路径及当前桌面、后续窄视口均有验证记录；自动化覆盖筛选 URL、日期错误、正常保存/核销/作废和反馈；截图限制及替代证据经 ChatGPT 接受；独立复审通过。 |
| ISS-058 | P3 / NEEDS_VERIFICATION | [R0-F1 前端 UX 覆盖盘点](R0-F1-前端UX覆盖盘点.md)；[ISS-058 性能基线报告](uat-evidence/iss-058-frontend-performance/README.md)；首次发现：2026-10-13，本轮生产构建 | 2026-10-27 / `codex/measure-iss058-frontend-performance` / 精确来源 SHA `742692a6e4887e4b8352736e69a52b1ebe8d066f`；集成依赖 `vite 8.3.5` 构建复测：主 JS `1,126,035` bytes，gzip `393,552` bytes，仍触发 Vite >500 kB chunk 警告。 | 对照原基线 `1,126,218` / `393,477` bytes，原始体积减少 `183` bytes，gzip 增加 `75` bytes；变化约 `-0.016%` / `+0.019%`，可视为包体基本持平。没有真实公网、低端设备或可重复用户性能指标，不能据构建体积宣称体验改善。 | 保持 P3 / NEEDS_VERIFICATION；如需优化，先在代表性网络和设备采集可重复首屏及交互指标，再决定是否做最小路由分包。集成 Playwright 的 20 项失败及构建警告见[本轮集成报告](uat-evidence/integration-036-002-003-052-058/README.md)。 | R1 集成复测 / 后续性能测量 | 有代表性环境的可复现性能数据和预算；性能方案通过关键路由、权限和交互回归及独立审查。 |
| ISS-062 | P2 / FIXED_PENDING_REVIEW | 2026-10-14 R0-F2 源码审查，backend/crm/views.py dashboard 的 orders_ytd、monthly_rows、category_sales、customer_rows 与 cash 查询 | 2026-11-04复核：当前4388947d70d26bca66ca0bfc76b2383a2fc0d404已包含9edbb6488a66a0801ecc1e5bc842df7866c6c7dc的统一日期实现；test_dashboard_uses_one_server_date_window_for_operating_metrics覆盖截至今日、排除未来/历史订单及12个月零月补齐，未来自定义报表保留。uat-evidence/iss-062-date-window/acceptance-report.md及API/Chrome图完整，原报告结论为待独立代码审查；本地1182全量及当前基线CI通过，保持待独立复审。历史对账记录（不再作为现行规则待决）：2026-10-28 / 日期窗口成果 `9edbb6488a66a0801ecc1e5bc842df7866c6c7dc` 已并入现行基线；隔离 API、真实 Chrome 和文案证据存在。但各经营指标日期上界仍需业务负责人统一确认，故从 P2 / OPEN 校准为 P2 / BLOCKED；不重复开发、不猜定规则。 历史台账结论保留：基线 `4298c31`：sales_ytd 有年初至今日上界；订单数、品类、客户排行和流水仅年初下界；月度数据从去年年初起，并非固定近 12 个月。本轮未改后端 | 原 UI 的“本年”“近12个月”等说明不准确；未来日期订单/流水可进入部分指标，与截至今日销售额范围不同。本轮按真实返回范围修正文案，未改变计算 本轮仅做状态对账，不扩大为生产/正式员工验收。 | ChatGPT独立复核当前日期边界、真实API及既有截图，不重复开发或要求确认已实施规则。原后续计划（历史）：业务/报表负责人明确是否允许未来日期及月度范围；获明确后端修复授权后补边界回归，再统一 API 名称/口径。负责人：业务产品 / Backend 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | 后续统计口径确认；R0-F2 仅说明 | 日期与未来订单边界有明确业务定义、后端回归和独立复审；不能以本轮文案修正关闭计算缺口。 |
| ISS-063 | P2 / FIXED_PENDING_REVIEW | 2026-10-14 R0-F2 当前 Dashboard.vue 结构与路径审查 | 基线 `4298c31` 营销式欢迎标题、实时同步声明、日期说明不足；本轮改为办公分组、明确口径、刷新时间、保留旧数据的失败反馈及权限一致入口，自动回归见 [R0-F2 验收](R0-F2-经营概览与报表中心验收.md) | 指标与待办层级不清，无法区分页面刷新和实时同步；长名称/大金额的桌面展示需复核 | ChatGPT 独立复核文案、真实口径、大小视口和刷新失败行为；内置续验限制按 ISS-066 保留。负责人：前端 QA | R0-F2 | 代码/自动回归/主要路径通过且独立复审接受；不修改统计或关闭 ISS-062。 |
| ISS-064 | P2 / FIXED_PENDING_REVIEW | 2026-10-14 R0-F2 ReportsPage.vue 操作与保存路径审查 | 本轮分步配置后显式查询；草稿与已查询条件分离，URL 恢复、本地保存/载入/排序/移除/撤销、下钻返回及异步选项回归覆盖 | 基线预设、日期、筛选动作即时查询，未提交条件与图表结果不易区分；从图块下钻可能取到当前草稿日期而不是该图块实际期间 | ChatGPT 复核已应用条件、不同来源切换、原有本地配置兼容和下钻返回；负责人：报表前端 QA | R0-F2 | 不改变 API 数据范围和本地保存机制；配置与实际结果一致，回归及独立复审通过。 |
| ISS-065 | P2 / FIXED_PENDING_REVIEW | 2026-10-14 R0-F2 ReportBlock.vue 状态与展示审查 | 长名称、大金额、轴标签、表格及多图块布局已优化；导出错误独立显示，不隐藏已查询图表；切换配置清除旧显示覆盖；保留后端权限校验 | 导出失败原先复用查询 error 隐藏整个图表；同图形类型切换来源可能残留显示覆盖；大数轴/条形值及长名称可读性欠缺 | ChatGPT 复核图形切换、单位/负值、分页、导出失败和缺权限入口；负责人：图表组件 QA | R0-F2 | 不改汇总/单位/负值计算或 CSV 内容；自动回归与独立复审通过；CSV 文件验收仍见 ISS-019。 |
| ISS-066 | P2 / BLOCKED | 2026-10-14 R0-F2 内置浏览器续验，CUA URL policy 明确拒绝连接标签 | 本轮早期已在内置浏览器查看真实两页并截图目视；续验时安全策略拒绝当前标签；用户手动打开独立地址后仍拒绝。独立服务恢复还遇到本机 5196 端口 EACCES；未换接口绕过  R0-F9新增当前27路由基线与原图索引，归档已实际完成；仍有ISS-100尺寸限制及历史特定状态/独立图片待审，不能据新图自行关闭。| 独立 SQLite 已准备长名称、24 月和大金额展示数据，但该数据集的内置浏览器多视口/导航/保存续验未完成。Chrome 自动回归不等同于独立截图视觉证据  R0-F9下一步：独立审图明确接受覆盖范围；对未接受的状态/尺寸使用受支持接口重拍。| 用户/运行环境提供正常、获准的内置浏览器访问后，前端 QA 补实际数据的 1440/1280/1024px 与保存/恢复/导航验收。不得导出原始浏览器数据或用其它浏览器接口绕过。负责人：运行环境 / 前端 QA | R0-F2 独立视觉验收 | 受支持内置浏览器可读真实页面；补完整操作矩阵，截图可归档或独立审查明确接受证据限制。 |

### P3 / 未承诺 Enhancement

| ID | 状态 | 首次发现来源 / 日期 | 最近核实（日期 / HEAD） | 影响与当前证据 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-040 | FIXED_PENDING_REVIEW | [PCR-007 completion note](Product-Optimization-Phase2G-PCR007.md)；[Phase1 completion review](Product-Completion-Review-Phase1.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；集成成果 `a4fc6d4f01f8c32a4a89f0d46557500a34566e98`。Packing List 导出、16列原始模板、样本和混装/分批回归已存在，阶段成果可封版；原生 Excel Print Preview 仍 PENDING，故改为 FIXED_PENDING_REVIEW，不关闭。 历史台账结论保留：UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 当前已实现实际Shipment的Packing List XLSX导出、16列原始模板、正常/混装/分批/多页/长描述样本及权限数量拒绝；backend/crm/services/packing_list.py与test_packing_list_export.py可核对。不能继续描述为Excel输出未实现。未将XLSX渲染冒充原生打印验收。 | 独立复核既有导出代码、原始模板/样本、数量守恒/权限/不回写及Chrome证据；不再次询问是否需要已有导出。完整打印成品与分页按用户决定延期，不追加Excel Print Preview操作。 | 已实现范围待独立复审；完整打印/分页延期 | XLSX内容/模板/合计/混装分批/错误拒绝与独立复审接受；原生打印范围明确延期保留，不自行关闭。 |
| ISS-041 | Enhancement / BLOCKED（延期） | [Product Completion Review PCR-009](Product-Completion-Review-Phase1.md)；[UX2 reassessment](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认）；2026-10-22 / ISS-041-A 基于 `9edbb6488a66a0801ecc1e5bc842df7866c6c7dc` 完成当前子任务复核 | 2026-10-22 / `codex/iss-041-detail-drill`：基于 `66338b701afed071bd6482a33a8cca8ebc20bfa2` 实施 ISS-041-B 原始销售/采购明细分页下钻、订单金额调整独立列示及客户/产品/SKU详情入口；后端32项、前端定向回归、真实 Chrome 证据已归档，等待独立代码审查 | ProductWorkspace 已有产品销售汇总；客户年度洞察仍是 Enhancement-Later，不属于已承诺功能。ISS-041-A 只完成两级交叉分组基础能力，ISS-041-B 只完成本轮原始明细与入口范围，均不代表 ISS-041 整体完成；原历史延期记录保留。 | 等待独立代码/权限/视觉复审；复审通过后再由产品负责人决定 ISS-041 后续范围和排期。 | Enhancement-Later | 保留 `BLOCKED（延期）` 状态；不得关闭 ISS-041。后续仍需决定是否需要更完整的业务分析详情能力；本轮实现的 ISS-041-B 仅标记 `FIXED_PENDING_REVIEW`，以本轮证据目录逐项复核。 |
| ISS-042 | FIXED_PENDING_REVIEW | [Product Completion Review PCR-018](Product-Completion-Review-Phase1.md)；[UX2 reassessment](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；共享模板最终成果 `fb859b91f68bb62c539d5439c65b52c06f13a58c`。团队共享模板基础版、权限、版本冲突、删除审计和 Chrome 证据可作为阶段成果冻结；审批、复制、回滚和组织治理不在本阶段，改为 FIXED_PENDING_REVIEW，不等于 CLOSED。 历史台账结论保留：2026-10-23 / `codex/iss-042-shared-reports`：基于 `0bba34c0e7139b77a88d2e838dbf921eff427373` 实施 ISS-042-DEV 团队共享报表模板基础版；共享模板模型/迁移、服务端配置白名单与当前权限校验、发布/取消发布、版本冲突、OperationLog 审计、前端管理、旧配置兼容及跨会话 Chrome 验收已完成，等待独立代码审查 | 团队共享模板基础版已交付，含白名单、权限、版本冲突、发布/取消发布和删除审计；旧localStorage描述仅是历史触发背景。审批、复制、回滚和组织治理不在当前基础版承诺范围。 | 等待独立代码、权限、审计与视觉复审；复审通过后再由报表负责人决定是否继续扩展共享模板的审批、复制和治理能力。负责人：报表 QA / 产品 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | 共享模板基础版待独立复审；治理扩展另列范围 | 按fb859b91f68bb62c539d5439c65b52c06f13a58c及当前实现复核配置白名单、正常/拒绝、冲突/审计与跨会话原图；保持FIXED_PENDING_REVIEW，不再引用旧BLOCKED作为当前状态，不自行关闭。 |
| ISS-048 | P3 / FIXED_PENDING_REVIEW | [Product Completion PCR-013](Product-Completion-Review-Phase1.md)；[UX2 reassessment](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；财务下钻成果 `c356e57014d28295485d52df23612c2fe6c02444`。可靠指标下钻与最小权限补修已有证据，可按该范围阶段封版；财务口径、真实跨账号浏览器、PostgreSQL 和独立复审仍待，改为 P3 / FIXED_PENDING_REVIEW，不关闭。 历史台账结论保留：2026-10-13 / R0-F1 工作树，基线 `bf79ef8`；本轮尚未提交 | 所选期间与当前余额已分组，可靠指标下钻及最小权限补修已有c356e57014d28295485d52df23612c2fe6c02444成果；finance_drill服务/测试和finance-drill.spec.js存在，8087最终三CI成功。不能再以缺下钻定义重复派工。 | 独立复核已定义指标的期间/当前余额、跳转目标、同条件合计、无权字段和数据来源拒绝、实际原图；未有可靠定义的额外指标不虚构新下钻。 | 可靠下钻及口径说明待独立复审 | 当前可靠指标、金额/数量范围、期间与余额、最小权限及代码/实际文件/原图经独立接受；目标正式身份验收分开，不自行关闭。 |
| ISS-049 | P3 / FIXED_PENDING_REVIEW | [Product Completion PCR-016](Product-Completion-Review-Phase1.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-10-23 / `9d08009f62920c62399ec48defe7f4d1c2e21411`，并入统一集成分支：客户、跟进、财务流水三类列表的筛选控件、URL 状态和真实 Chrome 页面均完成核验；自动回归与证据见 [ISS-049 测试日志](uat-evidence/iss-049-quick-filters/TEST_LOG.md)。 | 原始记录是筛选能力建议，并非已确认的功能错误；本轮确认筛选可用，未发现需追加修复的缺陷。 | 等待统一独立代码、权限和视觉复审；复审若发现特定列表条件未生效，再按最小范围处理。负责人：CRM QA。 | R0-E1 补验 | 真实业务列表筛选、URL 恢复/重置、自动测试及独立复审通过；不自行关闭。 |
| ISS-050 | P3 / NEEDS_VERIFICATION（等待样本） | [Product Completion PCR-017](Product-Completion-Review-Phase1.md)；[UX2 reassessment](Product-UX-Second-Review.md)；首次日期：UNKNOWN（未从一手记录确认） | UNKNOWN（末次核实日期 / HEAD 未记录；本轮未逐项重测） | 50–100 SKU 的参数、HS、包装维护是否需要批量继承尚无代表性工作量数据。 | 产品数据负责人用真实规模样本测维护时间，再决定是否做批量能力。 | P3-Later | 有记录的 50–100 SKU 观察与业务决定。 |

## R0-F3 新增与复审记录（2026-10-14）

R0-F2 最终提交 `04d3526`、CI [#38503175230](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38503175230) 的 Backend、Backend PostgreSQL、Frontend 均 SUCCESS。用户明确转述独立代码/自动回归 PASS，允许有条件封版。ISS-063–065 补记该结论，仍保留原记录待视觉证据复核，不将代码 PASS 写成完整视觉 PASS；ISS-062、ISS-066 状态不变。F1 已关闭四项及 ISS-057 视觉缺口不变。

| ID | 状态 | 首次发现来源 / 日期 | 最近核实与当前证据 | 影响 | 下一步 / 负责人 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|---|
| ISS-067 | P2 / NEEDS_VERIFICATION | 用户转述 R0-F2 独立复审，2026-10-14 | 2026-10-23，基线 `c356e57014d28295485d52df23612c2fe6c02444`：隔离员工打开管理员销售旧 URL 时，来源选择器切换为唯一有权来源“客户增长”，显示“地址中的报表来源当前不可查看，请重新选择查询”，未发出无权销售查询；强行请求后端返回 403 且无 `rows`。刷新、返回、保存、重载及有权来源查询通过；共享模板路径通过。未复现前端残留缺陷，不据此关闭 | 若成立，表单选择与可用权限不一致；当前证据显示查询权限拒绝与前端状态一致 | 保留现有代码，等待独立复审；如复审发现真实员工/生产配置差异，再按真实请求和状态追加核实；报表 QA | R0-F2 后续核实；普通 P2 延后 | [ISS-067 核实报告](uat-evidence/iss-067-report-permission/acceptance-report.md)中的真实 Chrome、API 403、测试日志和截图经独立复审接受；若缺少正式员工环境证据，继续 NEEDS_VERIFICATION |
| ISS-068 | P2 / FIXED_PENDING_REVIEW | R0-F3 库存 Phase A/B 结构复核，2026-10-14 | 概览与流水原来一次展示全部记录；新增每页 25 条，URL page 恢复与筛选重置；汇总仍覆盖所有筛选结果。指标保留五项，实际库存附已预留，工作台 1280/1024px 用三列；测试及目视见 F3 验收 | 独立审查范围：已覆盖代码/操作通过，截图视觉未通过。多 SKU 与长名称扫描、导航成本高；窄桌面数值需清晰显示 | 用户转述独立代码/已覆盖操作 PASS；剩余独立截图视觉按 ISS-070 补验。前端 QA | R0-F3 | 自动回归、真实内置浏览器主要路径与独立审查接受；无库存计算变化 |
| ISS-069 | P2 / FIXED_PENDING_REVIEW | R0-F3 日志/调整/冲销交互复核，2026-10-14 | 日志请求失败曾显示为无日志；改为错误与重试。调整选项失败阻止保存并支持重试；无订单查看权限不请求可选订单；保存期间关闭禁用；冲销防重复、清旧反馈，保存/冲销刷新详情。隔离实际保存两条、冲销一条并重开核对通过 | 独立审查范围：已覆盖代码/操作通过，截图视觉未通过。失败状态可能误导，重复操作或旧提示影响判断 | 用户转述独立代码/已覆盖操作 PASS；不扩大为完整视觉验收，按 ISS-070 补截图。库存前端 QA | R0-F3 | 输入、交易 Payload 和冲销规则不变；成功与失败回归、刷新一致性及独立复审通过 |
| ISS-070 | P2 / BLOCKED | R0-F3 截图归档能力核查，2026-10-14 | 受支持内置浏览器可访问 F3 独立 SQLite 页面，已工具截图目视；支持 screenshot 返回截图并工具展示，未取得允许写入仓库的归档接口。沿用截图安全限制，未导出原始数据或借其它浏览器绕过  R0-F9新增当前27路由基线与原图索引，归档已实际完成；仍有ISS-100尺寸限制及历史特定状态/独立图片待审，不能据新图自行关闭。| ChatGPT 独立视觉缺少可交付的截图文件；自动布局 PASS 与 Codex 目视不能替代它  R0-F9下一步：独立审图明确接受覆盖范围；对未接受的状态/尺寸使用受支持接口重拍。| 获准归档能力后补截图，或独立审查明确接受限制；运行环境 / 前端 QA | R0-F3 独立视觉验收 | 获准截图文件和完整矩阵，或用户/独立审查明确接受证据限制 |

## R0-F4 开始与新增事项（2026-10-14）

用户转述 ChatGPT 对 R0-F3 `ca486be514744d8d00344cb997a1f0c1389129f0` 独立代码与自动化/已覆盖操作回归 PASS，允许有条件封版；[CI #38507649163](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38507649163) 三项 SUCCESS。ISS-068、ISS-069 补记通过范围，保留待完整视觉复核；ISS-070 BLOCKED 不变。旧库存 ISS-006、013–015 等不因该结论关闭。

| ID | 状态 | 首次发现来源 / 日期 | 最近核实与证据 | 影响 | 下一步 / 负责人 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|---|
| ISS-071 | P2 / CLOSED | R0-F4 ResourcePage 供应商列表结构审查，2026-10-14 | 用户转述 ChatGPT 对 R0-F4 代码和自动化/已覆盖交互审查 PASS；最终 `8cb265e`；[CI #38539359761](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38539359761) 三项 SUCCESS。范围为五组信息列、供应商摘要、分类/规则筛选、分页及 URL 搜索/页码/详情恢复；独立视觉缺口单独由 ISS-073 保留 | 旧通用摘要不适用供应商，多资料难扫描；返回可能丢搜索上下文 | 按用户转述独立代码/交互复审关闭；不声称视觉证据完整 | R0-F4 | 代码和已覆盖交互独立复审通过；ISS-073 持续跟踪截图视觉 |
| ISS-072 | P2 / CLOSED | R0-F4 表单与详情付款条款审查，2026-10-14 | 用户转述 ChatGPT 对 R0-F4 代码和自动化/已覆盖交互审查 PASS；最终 `8cb265e`；[CI #38539359761](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38539359761) 三项 SUCCESS。表单分组和规则说明、分类、安全店铺链接、重复代码与失败反馈、保存保护、付款条款详情以及采购/SKU 导航已覆盖；结构化 Payload / 计算未改；独立视觉缺口由 ISS-073 保留 | 用户需辨别备注不执行；错误输入、重开与关联导航须一致 | 按用户转述独立代码/交互复审关闭；不声称视觉证据完整 | R0-F4 | 规则、历史采购快照/计划不变；代码和已覆盖交互独立复审通过 |
| ISS-073 | P2 / BLOCKED | R0-F4 内置浏览器截图归档能力核查，2026-10-14 | 内置浏览器可访问隔离供应商真实页面并工具截图目视；无获准仓库截图归档接口。遵守限制，未通过原始字节、其它浏览器或 CDP 绕过  R0-F9新增当前27路由基线与原图索引，归档已实际完成；仍有ISS-100尺寸限制及历史特定状态/独立图片待审，不能据新图自行关闭。| 缺可归档独立视觉文件；自动布局与 Codex 目视不可替代 ChatGPT 独立视觉  R0-F9下一步：独立审图明确接受覆盖范围；对未接受的状态/尺寸使用受支持接口重拍。| 获准归档接口后补矩阵截图，或独立审查明确接受限制；运行环境/前端 QA | R0-F4 独立视觉 | 有获准图片文件及独立审查，或明确接受证据限制 |
| ISS-074 | P3 / NEEDS_VERIFICATION | R0-F4 Playwright 供应商→新采购取消回归，2026-10-14 | 2026-10-28 / 付款规则回归成果 `64fb397aa065062e192ceb30040421f59b63a08c`。ISS-075 路径已移除旧异步来源并未复现历史误报，但“加载后不输入即取消”的独立时序仍未执行；保持 P3 / NEEDS_VERIFICATION。 历史台账结论保留：历史模拟 API 场景未在 ISS-075 隔离 Chrome 主链中重现；ISS-075 移除了供应商付款规则异步继承来源，并验证新采购保存/确认路径无额外付款规则写入。尚未单独完成“加载后不输入即取消”的真实时序回放，故不自行关闭本项 | 可能的异步未保存提醒仍需独立时序证据；付款业务保存/规则不受影响 本轮仅做状态对账，不扩大为生产/正式员工验收。 | 单独回放真实自定义/默认供应商、无输入取消、加载中输入和取消后继续编辑；采购前端 QA 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 | 历史 Issue 集中核实阶段 | 有真实 UI 与时序证据；确认是否需调整基线，不能丢失用户实际编辑 |

## R0-F5 联系人与客户跟进（2026-10-14）

R0-F4 的独立代码和自动化/已覆盖交互范围通过，允许有条件封版；截图独立视觉仍 BLOCKED。ISS-071、072 已按用户转述的独立结论关闭，仅覆盖相应代码及交互回归，不表示完整视觉验收；ISS-073、074 保留。最终提交 `8cb265e`，[CI #38539359761](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38539359761) Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。

| ID | 状态 | 首次发现来源 / 日期 | 最近核实与证据 | 影响 | 下一步 / 负责人 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|---|---|
| ISS-075 | P2 / FIXED_PENDING_REVIEW | R0-F4 用户复审提出付款规则筛选/继承语义疑问，2026-10-14 | 2026-10-28 / supplier-purchase-ux-r2 精确来源 SHA `64fb397aa065062e192ceb30040421f59b63a08c`；隔离 API/Chrome 付款快照场景 1/1 通过：常规供应商 UI 无固定规则、新采购单为空付款快照、历史显式付款计划仍显示；真实浏览器证据见 [本轮集成报告](uat-evidence/integration-r1-repairs-20261028/README.md)。 | 固定规则字段/历史记录保留；旧正式 PO 计划与真实付款不改写；空快照不会生成虚构计划，显式快照仍按单生成。ISS-074 单独时序验收仍保留。 | 保持 FIXED_PENDING_REVIEW，等待 ChatGPT 独立审查当前集成代码、业务边界、测试和截图；产品/采购 QA 按授权的真实业务数据补抽查，不关闭 Issue。 | 历史 Issue 集中核实阶段 | 独立审查接受代码、业务边界、截图和原始日志；真实业务财务抽查通过；未来恢复固定规则必须显式开关且不得隐式回填 |
| ISS-076 | P2 / FIXED_PENDING_REVIEW | R0-F5 Codex 内置浏览器截图归档检查，2026-10-14 | 2026-10-15 用户要求修复后，重新读取接口并验证 `tab.screenshot()` JPEG 字节可用标准文件写入保存；此前无专用保存方法即推断安全禁止的判断错误，当前没有截图导出安全拒绝。已归档联系人/跟进列表及新建表单在1440/1280/1024视口共12张和默认视口验证1张，见 [截图目录](uat-evidence/r0-f5/README.md)。应用代码与业务数据未改  R0-F9新增当前27路由基线与原图索引，归档已实际完成；仍有ISS-100尺寸限制及历史特定状态/独立图片待审，不能据新图自行关闭。| 截图可交付缺口已修复；自动化与 Codex 目视仍不替代独立视觉结论  R0-F9下一步：独立审图明确接受覆盖范围；对未接受的状态/尺寸使用受支持接口重拍。| ChatGPT 独立检查归档截图并复审截图流程；前端 QA | R0-F5 独立视觉复审 | 归档文件/来源/尺寸可核验，独立复审接受；不得由 Codex 自行宣布独立视觉 PASS |
| ISS-077 | P2 / FIXED_PENDING_REVIEW | R0-F5 联系人页面结构/交互审查，2026-10-14 | 实现 `92e8c46d4ce01e18cd164e152d345c58433c9305`；CI #38595334483 三项 SUCCESS。联系人列表分组、搜索/筛选及 URL 恢复、分页、长文本布局、重复提示、表单保护、客户/跟进关联入口和返回状态已调整；9 项 Playwright 包含 1440/1280/1024 实际计算布局。隔离 SQLite 内置浏览器实际新增、设主、编辑/删除确认及客户详情往返已检查 | 联系方式难扫描、窄桌面操作入口与关联导航可见性不足 | ChatGPT 独立复审当前提交，核对列表/表单/详情与返回路径；前端 QA | R0-F5 | 独立代码/交互复审通过；视觉证据缺口独立由 ISS-076 跟踪，不扩大验收 |
| ISS-078 | P2 / FIXED_PENDING_REVIEW | R0-F5 客户跟进页面结构/交互审查，2026-10-14 | 实现 `92e8c46d4ce01e18cd164e152d345c58433c9305`；CI #38595334483 三项 SUCCESS。跟进列表筛选与 URL 恢复、日期/方式/客户、记录/回复/下一步分组、设置/保留/清除计划呈现、富文本详情及附件状态已调整；隔离 SQLite 内置浏览器实际新建跟进、设置日期、保存后列表及客户详情同步。Playwright 覆盖编辑、筛选、上传控件和附件删除确认/取消/重开。实际附件文件选择器未通过受支持接口打开；内容访问/上传下载不据此宣称验收，历史 ISS-007 保留 | 跟进历史和下一步安排的扫描、状态理解及客户上下文导航成本偏高 | ChatGPT 独立复审当前提交的已覆盖 UI/交互；附件文件访问按 ISS-007 独立验收；前端 QA | R0-F5 | 独立代码/操作回归通过；独立视觉缺口由 ISS-076 跟踪；附件内容/授权另按 ISS-007 核验 |

历史供应商事项保留：ISS-022 MOQ 业务待决不改；ISS-024 供货来源准备不关闭（本轮增加配置位置说明不代替全部 SKU 核验）；ISS-026 关联删除未在真实 UI 执行，不认定修复；ISS-037 历史主体快照不改变。

## R0-F5 最终定向复修（2026-10-15）

用户转述独立复审：R0-F5主要代码与自动化通过，基线 `7774eeb` / [CI #38598901704](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38598901704) 三项 SUCCESS；仅处理保存关闭竞态。本轮不关闭此前待独立复审项，不开始R0-F6。

| ID | 状态 | 首次发现来源 / 日期 | 最近核实与证据 | 影响 | 下一步 / 负责人 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|---|
| ISS-079 | P2 / CLOSED | 用户转述 R0-F5 独立复审保存关闭竞态，2026-10-15 | 基线ResourcePage仅供应商遮罩关闭检查saving；联系人/跟进可能在请求未返回时确认放弃，路由守卫也缺忙状态。现有统一守卫增加可选busy，CRM保存中拒绝关闭/导航/后退，异步放弃确认返回时复查busy；干净但上传未完成时继续保护。2026-10-15 用户转述 ChatGPT 独立复审通过并明确允许关闭；最终提交 `86650adc795ae18a087996b0bdbe37747397e3e0`，CI #38605116907 三项 SUCCESS。仅关闭保存竞态代码/回归范围，不扩大为独立视觉 PASS。12项新增Vitest和8项Playwright可控异步回归，隔离库真实浏览器保存/失败/重试见 [最终验收证据](uat-evidence/r0-f5-final/README.md) | 用户可能误以为操作取消，但后台请求仍保存；详情/列表及异步返回状态失配 | 已按用户2026-10-15明确转述的独立代码/自动回归结论关闭；独立视觉不包含在此关闭范围 | R0-F5最终定向复修 | 联系人/跟进分别通过遮罩、关闭、跳转/后退、成功刷新、失败保留和双击防重复；精确HEAD三项CI及独立复审通过 |
| ISS-080 | P2 / FIXED_PENDING_REVIEW | 用户本轮独立复审非阻断提示，2026-10-15 | 原缺口已在 `codex/iss-080-contact-duplicates` 修复：新建/编辑联系人按客户授权范围通过 `/contacts/?customer=<id>` 分页拉取全量联系人，脱离当前搜索/筛选/分页；同客户邮箱、国际区号安全电话、相同或明显相近姓名提示，编辑排除自身，并提供查看入口。后端 2 项范围/权限测试、Django `crm` 全量 942（跳过14）、前端有效套件、Chrome Use 桌面与 390px 均通过；实现提交 `efb2546b69ae4ace60715dcb97803145248d3a1b`，2026-10-27，证据见 `docs/uat-evidence/iss-080-contact-duplicates/README.md` | 过去提醒可能不完整的问题已消除；提醒仍为非阻断，不替代服务端唯一性或业务校验 | ChatGPT 独立代码、权限和视觉复审；真实生产账号/数据库及跨员工业务数据抽查另行核实 | 历史Issue集中核实阶段 | 跨分页、搜索/筛选隐藏记录、邮箱/电话/姓名、国际区号、编辑自身、不同客户、权限隔离、手动继续创建均有可重复自动化和 Chrome Use 证据后再关闭 |

## R0-F6 产品主档、分类与参数（2026-10-15）

R0-F5 复审依据由用户提供，ISS-079 按明确接受关闭；ISS-080 / ISS-007 保留。历史 Task I1 冻结、前缀预览/确认及正式属性排序安全流程保留。本轮验收与限制见 [R0-F6 验收](R0-F6-产品主档分类与参数验收.md)。截图归档完成不等于 ChatGPT 独立视觉 PASS。

| ID | 优先级 / 状态 | 首次来源与日期 | 最近核实 | 影响 | 下一步 / 负责人 | 阶段 | 验收依据 |
|---|---|---|---|---|---|---|---|
| ISS-081 | P2 / FIXED_PENDING_REVIEW | 2026-10-15 R0-F6 ProductPage.vue 操作路径审查 | 2026-10-15 用户转述 R0-F6 独立代码/自动化/已覆盖交互 PASS，最终 `0b721fcd` / CI #38669003578 三项 SUCCESS；独立图片视觉待审。基线 `86650adc`：筛选不可从 URL 恢复、详情不写记录 ID、产品表单缺未保存/保存中保护。本轮补显式查询、排序和 URL、可刷新详情、返回、表单分组、长文布局、失败恢复及统一保存锁；Vitest/Playwright 与隔离库实际操作见验收报告 | 筛选/记录位置丢失，保存中可误关闭，长资料扫描困难 | ChatGPT 独立复审代码、矩阵和真实截图；前端 QA | R0-F6 | 三项精确 HEAD CI、关键交互与三尺寸布局，独立审查接受后再关闭 |
| ISS-082 | P2 / FIXED_PENDING_REVIEW | 2026-10-15 R0-F6 CategoryPage.vue 审查 | 2026-10-15 用户转述 `0b721fcd` / CI #38669003578 独立代码/自动化/已覆盖交互 PASS，独立图片视觉待审。分类首载失败只有短暂提示，层级统计随收起/搜索变化，分类保存中可关闭。本轮补持久加载错误与重试、全树最大层级、展开/收起、来源定位、保存/未保存保护、窄桌面、中文名称与 SKU Code 区分；继承只读、冻结拒绝、属性排序预览/确认仍由原规则执行 | 分类层级理解、失败恢复及安全操作上下文不足 | 独立复审树/属性正常与拒绝路径及截图；前端 QA | R0-F6 | 可恢复加载、拖拽状态回归、后端冻结/身份安全回归和独立接受，不改业务限制 |
| ISS-083 | P2 / FIXED_PENDING_REVIEW | 2026-10-15 R0-F6 ResourcePage.vue 产品参数及详情审查 | 2026-10-15 用户转述 `0b721fcd` / CI #38669003578 独立代码/自动化/已覆盖交互 PASS，独立图片视觉待审。原通用摘要含不适用的“启用/进行中”，缺产品筛选、参数用途说明与自然重复提示。本轮补参数专用摘要、产品与搜索 URL、产品关联返回、表单分组、保存保护/重试、重复中文提示和关联产品状态中文显示 | 参数层级混淆、所属产品定位和失败修正成本高 | 独立复审参数列表/新建/编辑/详情/返回/错误与真实截图；前端 QA | R0-F6 | 真实创建/修改/重开/重复拒绝重试、自动回归及三项 CI 通过，独立接受后关闭 |

### R0-F7A 定向 UI/UX 与证据核验（2026-10-15）

| ID | 优先级 / 状态 | 首次发现来源 / 日期 | 最近核实及影响 | 负责人 / 下一步 | 计划阶段 | 关闭依据 |
|---|---|---|---|---|---|---|
| ISS-084 | P2 / FIXED_PENDING_REVIEW | 用户转述 R0-F6 独立审查：两张参数1440截图实际1024×1000；首次日期 UNKNOWN，本轮记录2026-10-15 | 已核实旧文件不符；重拍 create/edit 为真实1440×1000并更新F6清单。原流程按请求宽度命名但未拒绝像素不符；旧记录不能证明底层时序根因。F7A每张核对DOM、JPEG和文件名，并生成哈希  R0-F9新增当前27路由基线与原图索引，归档已实际完成；仍有ISS-100尺寸限制及历史特定状态/独立图片待审，不能据新图自行关闭。| 独立审查者核对两张替换图片及F7A清单；前端QA维持尺寸断言  R0-F9下一步：独立审图明确接受覆盖范围；对未接受的状态/尺寸使用受支持接口重拍。| R0-F7A，关联R0-F6 | 图片真实尺寸和状态相符、独立接受；不推断其余F6旧图已全部改正 |
| ISS-085 | P2 / FIXED_PENDING_REVIEW | R0-F7A SKUPage.vue 与实际浏览器；2026-10-15 | 列表筛选/详情位置不能恢复、只读行缺详情、参数多时查找困难、保存中关闭/重复提交、1024编辑内容撑宽。本轮补URL、详情及库存导航、参数搜索/重复预览、统一保存锁、持久错误与历史重试、三尺寸实际布局回归 | ChatGPT复审代码、操作矩阵、原始截图；前端QA处理本轮引入问题 用户本轮明确转述独立代码与已覆盖操作PASS；图片独立视觉仍待审，保留待复审状态。 | R0-F7A | 完整自动回归、真实UI、精确HEAD三项CI和独立审查接受；身份/生成规则不改 |
| ISS-086 | P2 / FIXED_PENDING_REVIEW | R0-F7A 供应来源与批量绑定操作审查；2026-10-15 | 重复编码报错不自然、来源失败提示短暂、批量候选和实际采购语义易混、保存关闭保护不足。补中文持久错误、输入保留重试、保存锁、候选文案、停用后果确认、窄桌面布局 | 独立审查来源新建/编辑/拒绝/重试、候选绑定和三尺寸截图；前端QA 用户本轮明确转述独立代码与已覆盖操作PASS；图片独立视觉仍待审，保留待复审状态。 | R0-F7A | UI与自动正常/异常路径及精确CI通过，独立接受；不改变价格、MOQ、候选匹配、历史快照 |
| ISS-087 | P2 / NEEDS_VERIFICATION | R0-F7A 隔离旧式SKU样本（无保存缩写）；2026-10-15 | 保存型号F7A-1024与当前缩写预览F7A-1024V可能不同；样本说明兼容风险，不证明正式历史数据已受损。本轮只增加“当前保存型号/预览”说明；普通未改身份保存仍保留原型号 | 产品/QA用只读历史样本核对是否缺缩写、当前预览及普通保存前后身份与快照；明确期望后再排期，不改生成规则 | 历史Issue集中核实阶段 | 提供真实样本、保存前后identity及快照证据和业务决定；无证据不得判定为已复现生产缺陷或关闭 |
| ISS-088 | P2 / CLOSED | 用户转述ChatGPT独立审查，SKUPage.vue约305/748行重复watch及load竞态；首次来源日期UNKNOWN，本轮核实2026-10-15 | 基线9975bf2确有两套search/productFilter/status监听，旧load可覆盖新结果/历史/error/loading。本轮保留一套多源值比较监听（顺便移除重复detail监听），请求版本号控制结果/错误/finally，搜索仍分别获取筛选记录和完整历史，成对提交最新结果；组件与浏览器可控异步回归见验收补充 | 2026-10-15用户明确接受ChatGPT独立代码与回归PASS；最终79841e382c882f33444627e65310170a47a444cf / CI #38697043429三项SUCCESS；按该范围关闭，独立图片视觉不由此通过 | R0-F7A最终定向修复 | 完整Vitest/Playwright及精确HEAD三项CI SUCCESS、真实隔离UI与独立复审接受；不得删去历史请求或改变业务规则 |

R0-F7A 证据见 [验收报告](R0-F7A-SKU管理与供应来源验收.md)。ISS-022 MOQ业务待决、ISS-023型号数据准备、ISS-024来源准备、ISS-026关联供应商删除、ISS-007附件及ISS-080联系人重复提示等全部保留；没有以本轮UI回归关闭历史业务问题。

### R0-F7B 包装与交易单位（2026-10-15）

| ID | 状态 | 首次发现来源 / 日期 | 最近核实与影响 | 负责人 / 下一步 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-089 | P2 / FIXED_PENDING_REVIEW | R0-F7B PackagingPage.vue结构与保存路径审查；2026-10-15 | 原保存遮罩可关闭、失败提示短暂、URL/关联状态恢复不足；本轮补统一busy/dirty守卫、错误重试、复制草稿、变更风险、关联状态及桌面布局；可控异步自动回归和真实API三尺寸截图见F7B报告  2026-10-15用户明确转述独立代码与自动/已覆盖交互审查PASS；最终a2cbdec / CI #38752391875三项SUCCESS；图片独立视觉仍待审，不扩大为完整视觉接受。| 前端QA / ChatGPT独立复核正常与拒绝路径、布局和原始截图 | R0-F7B | 完整回归、精确HEAD三项CI、独立代码及视觉接受；装箱/尾货/历史快照不变 |
| ISS-090 | P2 / FIXED_PENDING_REVIEW | R0-F7B TradeUnitsPage.vue流程审查；2026-10-15 | 基础/交易单位、供应商专用与定义不可变的说明和编辑反馈不足；补SKU上下文、只读定义/备注启停默认编辑、失败保留、统一守卫和5/10/50米卷展示。重复定义仅提示，未改后端策略  2026-10-15用户明确转述独立代码与自动/已覆盖交互审查PASS；最终a2cbdec / CI #38752391875三项SUCCESS；图片独立视觉仍待审，不扩大为完整视觉接受。| 前端QA / 独立审查换算文案、切换/返回/保存保护、异常重试和截图 | R0-F7B | 正常/错误输入、不可变定义、mutable PATCH、换算业务回归、最终CI及独立接受 |
| ISS-091 | P2 / FIXED_PENDING_REVIEW | R0-F7B SKUPage.vue包装子表单及显示来源审查；2026-10-15 | 内联保存缺busy保护与持久错误；打开净重应优先取packaging profile。补父子保存锁、失败原关联保留、真实profile显示和交易单位返回编辑上下文；批量筛选/撤销不改算法  2026-10-15用户明确转述独立代码与自动/已覆盖交互审查PASS；最终a2cbdec / CI #38752391875三项SUCCESS；图片独立视觉仍待审，不扩大为完整视觉接受。| 前端QA / 独立复核内联失败/重试、已保存显示、返回上下文、批量目标及三尺寸截图 | R0-F7B | Vitest/Playwright、真实保存重开和错误路径、最终CI及独立接受；SKU身份/基础单位/换算不变 |

证据：[R0-F7B验收](R0-F7B-包装模板与交易单位验收.md)、[45张原始截图](uat-evidence/r0-f7b/SCREENSHOTS.md)。截图归档成功不等于ChatGPT独立视觉PASS。ISS-087合成旧式缺缩写风险继续待核实；本轮后端拒绝后补齐合成数据，不绕过规则、不推断正式数据受损。历史ISS-007/022/023/024/026/080及全部其他未关闭记录保留。

### R0-F8A 产品证书与HS编码（2026-10-15）

| ID | 状态 | 首次发现来源 / 日期 | 最近核实与影响 | 负责人 / 下一步 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-092 | P2 / FIXED_PENDING_REVIEW | R0-F8A ResourcePage.vue证书列表/表单、EntityDetailModal.vue文件与关联信息审查；2026-10-15 | 原证书页搜索不恢复URL、一般列表请求可逆序覆盖、保存遮罩不受busy保护；有效/临期/空态及关联信息组织不足。本轮复用通用页面，补字段分组、统一守卫、持久中文错误、筛选/排序/分页恢复、请求版本及详情日期状态、安全HTTP(S)文件入口。46张原图和自动/真实记录见F8A报告  用户转述ChatGPT独立代码及自动/已覆盖交互PASS，有条件封版；最终82514b1396e1e53d44bcd9314d19bbb65b0fbeed，[CI #38761364221](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38761364221)三项SUCCESS。独立图片视觉、文件内容和授权缺口继续保留，不扩大验收。| 前端QA / ChatGPT独立复核正常/拒绝、返回导航、三尺寸与截图；ISS-007/017文件内容和授权事项单独保留 | R0-F8A | 完整回归、真实隔离API/UI及最终精确HEAD三项CI通过，独立代码与视觉接受；不改变有效性规则或文件授权 |
| ISS-093 | P2 / FIXED_PENDING_REVIEW | R0-F8A HSCodePage.vue编辑/产品分配路径审查；2026-10-15 | 原弹窗可保存中关闭/重复提交，选择产品较多时缺已选范围/批量操作，失败易丢反馈；本轮补统一dirty/busy守卫、错误保留/重试、只读能力、完整产品分页加载、筛选范围批量操作/已选数与移入提醒、重开同步和关联导航。1024整页溢出由计算布局测试发现并修复为表内滚动  用户转述ChatGPT独立代码及自动/已覆盖交互PASS，有条件封版；最终82514b1396e1e53d44bcd9314d19bbb65b0fbeed，[CI #38761364221](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38761364221)三项SUCCESS。独立图片视觉、文件内容和授权缺口继续保留，不扩大验收。| 前端QA / 独立复核筛选隐藏选择、拒绝恢复、保存保护、产品导航及三尺寸原图 | R0-F8A | 选择/解除关联/启停/重复拒绝和权限边界回归，最终CI及独立接受；HS身份、唯一性、产品关联约束不变 |

证据：[R0-F8A验收](R0-F8A-产品证书与HS编码验收.md)、[截图清单](uat-evidence/r0-f8a/SCREENSHOTS.md)。真实缺失链接打开404只证明该合成地址缺失，不证明真实文件内容、下载、附件授权或部署ACL通过；ISS-007、017等历史事项全部保留。自动只读角色为隔离fixture，后端权限为现有测试覆盖，不启用正式RBAC或员工UAT。

## R0-F8B 数据导入专项（2026-10-16）

| ID | 优先级 / 状态 | 首次发现来源 / 日期 | 影响与当前证据 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-094 | P2 / FIXED_PENDING_REVIEW | R0-F8B ImportPage.vue流程与异步状态审查；2026-10-16 | 原页面缺确认期间锁定、方法级防重、busy离开保护及旧预览失效防线；模板未就绪可下载空文件；失败/校验/写入阶段易混淆。本轮补统一busy守卫、文件/类型版本绑定、显式阶段、完整响应校验、错误表分页及真实UTF-8 CSV下载；只改前端与回归，不改导入核心。真实四类CSV/UI/DB核对、三尺寸原图及自动回归见[R0-F8B验收](R0-F8B-数据导入验收.md)。用户本轮接受代码、自动及已覆盖真实CSV范围，有条件封版；最终10158f89b50ad477026f4ee2d4d4fd8177d5edcd / CI #38878347385三项SUCCESS；独立图片仍待审 | 前端QA / ChatGPT继续独立图片视觉复核；已接受的代码/自动/实际CSV范围不扩大为正式身份审计或完整业务UAT | R0-F8B | 精确HEAD三项CI、自动与真实隔离CSV证据通过，独立接受代码/交互与图片范围；ISS-052历史审计缺口另行处理 |

R0-F8A已按用户转述独立代码/自动回归PASS、有条件封版；ISS-092/093只记录通过范围，独立视觉与文件安全仍待补。本轮没有关闭任何历史Issue；普通P2/P3继续延期，ISS-007及所有业务/权限事项保留。

## R0-F8C 组织权限与访问状态专项（2026-10-16）

| ID | 优先级 / 状态 | 首次发现来源 / 日期 | 当前证据与影响 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-095 | P2 / FIXED_PENDING_REVIEW | OrganizationPage.vue渲染、角色切换和保存路径审查；2026-10-16 | 原渲染会补写本地permissions，切换缺dirty确认、保存中可编辑/重复提交/离开，错误短暂消失；现分离服务端配置与草稿，统一守卫、持久反馈、模块搜索/完整提交、POST后GET角色及当前身份回读、失败保留/纯读取重试。实际隔离合成角色保存/取消/拒绝恢复/重开、固定表头与三尺寸见[R0-F8C验收](R0-F8C-组织权限与访问状态验收.md)  用户于2026-10-16本轮转述ChatGPT独立代码、自动化及已覆盖操作复审通过，允许有条件封版；最终b916fab613806a9fd00636cc87496803557d45a8 / CI #38909906403三项SUCCESS。独立图片视觉仍待审。| 前端QA / ChatGPT独立图片复核；已接受代码、自动及已覆盖操作不扩大为正式权限UAT。 | R0-F8C | 精确HEAD三项CI、可控异步回归、实际隔离UI/DB证据及独立接受；正式RBAC与ISS-003仍单独验收 |
| ISS-096 | P2 / FIXED_PENDING_REVIEW | AccessDeniedPage.vue同时用于两种状态的文案/恢复审查；2026-10-16 | 原权限状态读取失败仍显示403，拒绝与全局错误混淆，重试无单飞保护；现按路由区分拒绝/读取失败，明确错误、无可访问页面及重试状态，仅返回现有firstPermittedPath。真实停服/恢复、模拟401/403/500/网络及防循环测试见F8C报告；未修改router/accessControl核心  用户于2026-10-16本轮转述ChatGPT独立代码、自动化及已覆盖操作复审通过，允许有条件封版；最终b916fab613806a9fd00636cc87496803557d45a8 / CI #38909906403三项SUCCESS。独立图片视觉仍待审。| 前端QA / ChatGPT独立图片复核；已接受代码、自动及已覆盖操作不扩大为正式权限UAT。 | R0-F8C | 自动、实际浏览器、最终CI及独立代码/图片复核通过；不得以模拟受限账号代替正式员工验收 |

本轮未发现经真实正式身份验证的新权限安全漏洞，未修改后端或权限执行策略。ISS-003、007、052及其他历史未关闭事项全部保留；普通P2/P3继续延期。新发现的模板显示疑问只按ISS-097待核实，不自行定性或扩展修复。

## ISS-097 超级管理员权限显示一致性专项（2026-10-26）

| ID | 优先级 / 状态 | 首次发现来源 / 日期 | 当前证据与影响 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-097 | P2 / FIXED_PENDING_REVIEW | R0-F8C最高角色模板与有效权限对照；2026-10-16；本轮复核 2026-10-26 | 确认显示缺陷：历史 `superadmin` 存储模板的部分新增模块为未勾选，但服务端 `has_all_permissions()` 和有效矩阵始终授予最高业务角色全部 24 个模块/六类动作。API 现明确返回 `has_all_permissions` 与 `effective_permissions`；页面显示“包含全部ERP业务权限，不受普通勾选项限制”，24/24 复选框全选且只读。未回写模板、未改变开发超级管理员或普通角色授权。真实 Chrome、Django 定向/权限回归、前端全量 Vitest 和生产构建见 [ISS-097 验收记录](uat-evidence/iss-097-admin-permissions/README.md)。 | QA / 独立复核最高角色显示、受限角色 API 和正式员工会话边界；不得把隔离夹具代替真实员工 UAT，也不得将应用权限推定为服务器/数据库权限 | R0-F8C 后续权限专项 | 独立复核 API 有效矩阵与 UI 一致；最高角色不可编辑且文案明确；普通员工无新增数据范围；正式部署边界按 ISS-003、ISS-051 单独完成后再考虑关闭 |

本专项确认并修复的是显示一致性问题，不把历史“缺少勾选”误报为授权漏洞。ISS-003、ISS-043、ISS-051 的原有正式身份、审计和部署风险不因本专项自动关闭。

## R0-F9 全站收尾审查（2026-10-16）

| ID | 优先级 / 状态 | 首次发现来源 / 日期 | 最近核实与影响 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-098 | P2 / FIXED_PENDING_REVIEW | R0-F9原始截图：products/page-1280、skus/page-1440、quotes/final-page-1280、orders/final-page-1280；2026-10-16 | B类跨模块列表呈现：产品/SKU状态竖排、报价客户列过窄、订单筛选保留原生外观。仅在ProductPage、SKUPage、DocumentPage加局部列宽/不换行/筛选控件样式；新增12项三尺寸布局回归通过。最终代码0f0747a；内置浏览器与真实Chrome原图见F9索引。业务术语、值及权限均未改 | 前端QA / 独立复核三尺寸标签、长客户名、筛选及表内滚动，按精确HEAD完整CI和原图接受；不得自行关闭 | R0-F9待独立复审 | 代码、139项Playwright及完整回归、真实Chrome与独立图片复核通过 |
| ISS-099 | P3 / NEEDS_VERIFICATION | R0-F9空白新建SKU取消旧原图；2026-10-16 | VIS-01于9d05a70运行代码，以内置浏览器和真实Chrome分别测试SKU列表、产品详情入口，空白取消均关闭且无确认；主动修改描述后确认并保留输入。新增4项入口/异步默认值/参数缩写回归，原busy保护不变。本次未复现，原因未证实，未修改守卫；不能称已修复 | 前端QA / 保留旧证据，取得可重放的最小复现及初始化快照差异后再评估；详见VIS-01报告 | R0-F9-VIS-01待核实 | 两入口、异步前后、真实修改/保存中保护及独立接受，不以未复现代替关闭 |
| ISS-100 | P2 / BLOCKED | R0-F9原始JPEG尺寸与请求对照；2026-10-16 | VIS-01逐张复核旧69异常图与573原图哈希/尺寸。新最终81张中63精确尺寸通过、18仍不符；整页滚动时DOM1440/client1425，接口原图1425×990等，重复采集仍如此。另确认视口设置作用于当前标签，最终矩阵断言目标DOM匹配请求。新图不拉伸/补边/裁切/重编码。历史原图保留，尺寸与完成态分开判定 | QA / 截图接口修正或用户明确接受限制前保持BLOCKED；逐项清单dimension-exceptions-69.json及18项新基线见VIS-01 | R0-F9-VIS-01独立证据复审 | 真正27×3请求像素全部匹配，或明确接受具体技术限制；旧元数据更正说明继续保留 |

新增A类缺陷未发现；B类低风险集中修正见ISS-098，疑问见ISS-099；C/D不扩展业务修复；E见ISS-100及历史视觉记录。ISS-095/096仅同步用户接受的代码/已覆盖交互，ISS-097保持NEEDS_VERIFICATION。全部历史ID保留，没有批量关闭。F1–F4当前页面原图已补，历史特定状态和ChatGPT独立视觉不自动通过。详见[R0-F9报告](R0-F9-全站UIUX最终审查.md)、[截图索引](uat-evidence/r0-f9/index.html)、[历史分类快照](uat-evidence/r0-f9/HISTORICAL-ISSUES.md)。

## 本次统计

统计包含全部历史记录：P0=0，P1=19，P2=72，P3=6，Enhancement=3。按状态：OPEN=6，BLOCKED=20，NEEDS_VERIFICATION=28，FIXED_PENDING_REVIEW=38，CLOSED=8。共100条，每个ID只计一次。本轮新增ISS-098修复待独立复审、ISS-099/100待核实；ISS-095/096记录已覆盖代码与操作接受，独立视觉仍待审；ISS-097保持NEEDS_VERIFICATION。未关闭任何历史Issue。

> 注：每条问题均有稳定 `ISS-nnn`。状态数量按每个 ID 只计一次；延期事项仍保留在台账中，不因阶段通过清空。

## 历史已关闭事项（不作为当前缺陷重开）

### R0-F1 独立复审已接受项（2026-10-14）

| ID | 状态 | 首次发现来源 / 日期 | 最近核实（日期 / HEAD） | 影响与当前证据 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|---|
| ISS-056 | CLOSED | [CI #267 Backend 失败](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38384214144)；[`test_sku_context_hides_cost_and_stock_without_source_modules`](../backend/crm/tests/test_sales_data_scope.py)；首次发现日期：2026-10-13 | 2026-10-14 / 用户本轮明确转述 ChatGPT 独立代码与已覆盖交互回归 PASS；最终提交 `4298c31ec043b2f3fc2d690768455d7df417de08`；[CI #38433549045](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38433549045) Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。 | 首次失败断言以 `assertNotIn(str(sku.cost_price), repr(response.data))` 搜索子串 `77`；响应中无成本字段，但无关时间戳 `...210776...` 含有 `77`，导致偶发假失败。影响 Backend CI 可靠性，不代表业务数据泄漏。 | 已按用户本轮明确接受及 REVIEW_PROTOCOL 关闭该代码/回归问题；截图归档缺口仍由 ISS-057 / ISS-046 保留，不扩展为完整视觉验收。 | 后续获授权的 CI 稳定性修复 | 该测试在时间戳变化时稳定通过，且断言仍能在真正泄漏成本值时失败；精确 HEAD Backend、Backend PostgreSQL、Frontend CI 全部 SUCCESS。  用户于 2026-10-14 明确允许关闭；依据上述最终提交与 CI。 |
| ISS-059 | P2 / CLOSED | 2026-10-14 用户转述 ChatGPT 独立代码审查；PaymentPlanPage.vue 无效 minmax 声明 | 2026-10-14 / 用户本轮明确转述 ChatGPT 独立代码与已覆盖交互回归 PASS；最终提交 `4298c31ec043b2f3fc2d690768455d7df417de08`；[CI #38433549045](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38433549045) Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。 | 桌面筛选栏声明被浏览器丢弃，排列不符合设计 | 已按用户本轮明确接受及 REVIEW_PROTOCOL 关闭该代码/回归问题；截图归档缺口仍由 ISS-057 / ISS-046 保留，不扩展为完整视觉验收。 | R0-F1 财务定向复修 | 指定尺寸控件、间距、换行及按钮可见性通过，独立复审接受。  用户于 2026-10-14 明确允许关闭；依据上述最终提交与 CI。 |
| ISS-060 | P2 / CLOSED | 2026-10-14 用户转述 ChatGPT 独立审查；应收/应付及财务流水文案 | 2026-10-14 / 用户本轮明确转述 ChatGPT 独立代码与已覆盖交互回归 PASS；最终提交 `4298c31ec043b2f3fc2d690768455d7df417de08`；[CI #38433549045](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38433549045) Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。 | 重复登记文案不自然；候选清空后订单编号回退数字 ID | 已按用户本轮明确接受及 REVIEW_PROTOCOL 关闭该代码/回归问题；截图归档缺口仍由 ISS-057 / ISS-046 保留，不扩展为完整视觉验收。 | R0-F1 财务定向复修 | 两方向提示准确；完整编号保留且保存仍提交原 ID；独立复审通过。  用户于 2026-10-14 明确允许关闭；依据上述最终提交与 CI。 |
| ISS-061 | P2 / CLOSED | 2026-10-14 本轮按用户审查要求检查操作反馈；PaymentPlanPage.vue | 2026-10-14 / 用户本轮明确转述 ChatGPT 独立代码与已覆盖交互回归 PASS；最终提交 `4298c31ec043b2f3fc2d690768455d7df417de08`；[CI #38433549045](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38433549045) Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。 | 上次成功提示与新操作或失败状态并存，可能误导用户 | 已按用户本轮明确接受及 REVIEW_PROTOCOL 关闭该代码/回归问题；截图归档缺口仍由 ISS-057 / ISS-046 保留，不扩展为完整视觉验收。 | R0-F1 财务定向复修 | 旧成功提示不与新失败状态并存；业务规则不变；独立复审通过。  用户于 2026-10-14 明确允许关闭；依据上述最终提交与 CI。 |

- Round 1 原始 P1：`UAT-ORD-001`、`UAT-PKG-001`、`UAT-SHIP-001`、`UAT-SKU-001`、`UAT-ORD-004` 均有后续修复/复测记录。发货 500 的历史根因及修复见 [UAT Fix Batch 1](UAT-Fix-Batch1-P1.md) 和 Round 1 的定向 Re-UAT；原始失败记录保留。

- Round 1 原始 P2：`UAT-QTE-001`、`UAT-ORD-002`、`UAT-DRILL-001`、`UAT-ORD-003`、`UAT-FUP-001`、`UAT-FUP-002`、`UAT-PUR-001`、`UAT-INV-001`，2026-10-04 各有定向 Re-UAT；旧结果未覆盖，当前关闭结论见 [Round 1 P2 Cleanup Final Status](UAT-Round1-正式业务全流程测试.md)。附件下载通道的后续端到端问题单独由 ISS-007 跟踪。

- PCR-001/002/003/004/005/006/008/010/011/012/014/015/019/020 已在各自 Phase 2 验收记录中完成原定范围；PCR-007 的实际装箱 UI 已验收，未实现的是另列的正式文件导出 Enhancement ISS-040。PCR-009 客户年度洞察与 PCR-018 团队共享图块仍延期。

- 2026-10-23 ISS-042-FIX-01 已在 `codex/iss-042-shared-reports` 基于 `6d5ce10a2ce8a432b427371542eac7378daca655` 完成并记录为 `FIXED_PENDING_REVIEW`：修复共享模板发布/取消发布配置版本并发冲突、重复状态操作虚假审计，以及删除后模板历史安全查询；证据见 `docs/uat-evidence/iss-042-fix-01/`。ISS-042 仍保留 `Enhancement / BLOCKED（延期）`，不得据此关闭。

- Phase 3C 的 I20/I37/I49/I53 及 Phase 4B-1 PostgreSQL 查询兼容、迁移测试隔离/fixture 故障均有修复测试和成功 CI；不与当前 staging 数据迁移风险 ISS-044 混淆。

- R0-A、R0-B1、R0-B2、R0-C1、R0-C2、R0-C3、R0-D1、R0-D2 的各自范围记录未发现仍未处理的本轮事项；这不代表未覆盖的系统范围自动通过。

## 主要历史来源清单

本次逐项对照以下 UAT、审查、阶段验收和风险文档；设计草案与旧计划只用于追溯，不替代当前实现或复测证据。

- 综合/历史 UAT：[`R0-E1-综合业务回归与内测准备.md`](R0-E1-综合业务回归与内测准备.md)、[`真实用户E2E-UAT-20260923.md`](真实用户E2E-UAT-20260923.md)、[`UAT-Round1-正式业务全流程测试.md`](UAT-Round1-正式业务全流程测试.md)、[`UAT-Fix-Batch1-P1.md`](UAT-Fix-Batch1-P1.md)、[`业务流程与修改回归测试报告-20260922.md`](业务流程与修改回归测试报告-20260922.md)、[`添加数据测试.md`](添加数据测试.md)。

- 阶段/风险：[`Phase3-业务流程与异常UAT计划.md`](Phase3-业务流程与异常UAT计划.md)、[`Phase3C-不变量故障注入执行记录.md`](Phase3C-不变量故障注入执行记录.md)、[`Phase4-生产化加固审计与实施计划.md`](Phase4-生产化加固审计与实施计划.md)、[`Phase4B-PostgreSQL兼容性执行记录.md`](Phase4B-PostgreSQL兼容性执行记录.md)。

- UI/UX 审查：[`Product-Completion-Review-Phase1.md`](Product-Completion-Review-Phase1.md)、[`Product-UX-Second-Review.md`](Product-UX-Second-Review.md)、[`Product-UX-Customer-Module-Review.md`](Product-UX-Customer-Module-Review.md)、[`Product-UX-Quote-Module-Review.md`](Product-UX-Quote-Module-Review.md)、[`Product-UX-Order-Module-Review.md`](Product-UX-Order-Module-Review.md)、[`Product-UX-Purchase-Module-Review.md`](Product-UX-Purchase-Module-Review.md)、[`Product-UX-Inventory-Module-Review.md`](Product-UX-Inventory-Module-Review.md)、[`Dialog-Standardization-Audit.md`](Dialog-Standardization-Audit.md)。

- 产品优化验收：[`Product-Optimization-Phase2A-PCR001.md`](Product-Optimization-Phase2A-PCR001.md)、[`Product-Optimization-Phase2B1-PCR003.md`](Product-Optimization-Phase2B1-PCR003.md)、[`Product-Optimization-Phase2B2-PCR002.md`](Product-Optimization-Phase2B2-PCR002.md)、[`Product-Optimization-Phase2B3-PCR011.md`](Product-Optimization-Phase2B3-PCR011.md)、[`Product-Optimization-Phase2C1-PCR004.md`](Product-Optimization-Phase2C1-PCR004.md)、[`Product-Optimization-Phase2C2-PCR005.md`](Product-Optimization-Phase2C2-PCR005.md)、[`Product-Optimization-Phase2C3-PCR010.md`](Product-Optimization-Phase2C3-PCR010.md)、[`Product-Optimization-Phase2C4-PCR012.md`](Product-Optimization-Phase2C4-PCR012.md)、[`Product-Optimization-Phase2C5-PCR014.md`](Product-Optimization-Phase2C5-PCR014.md)、[`Product-Optimization-Phase2D-PCR008.md`](Product-Optimization-Phase2D-PCR008.md)、[`Product-Optimization-Phase2E-PCR006.md`](Product-Optimization-Phase2E-PCR006.md)、[`Product-Optimization-Phase2F-PCR020.md`](Product-Optimization-Phase2F-PCR020.md)、[`Product-Optimization-Phase2G-PCR007.md`](Product-Optimization-Phase2G-PCR007.md)、[`Product-Optimization-Phase2H-PCR019.md`](Product-Optimization-Phase2H-PCR019.md)。

- 安全与权限：[`R0-A-Sales-Safety-Reconciliation.md`](R0-A-Sales-Safety-Reconciliation.md)、[`R0-B1-Purchase-Safety-Reconciliation.md`](R0-B1-Purchase-Safety-Reconciliation.md)、[`R0-B2-Supplier-Payment-Terms.md`](R0-B2-Supplier-Payment-Terms.md)、[`R0-C1-Followup-Safety.md`](R0-C1-Followup-Safety.md)、[`R0-C2-SKU-Save-Integrity.md`](R0-C2-SKU-Save-Integrity.md)、[`R0-C3-Safe-CSV-Import.md`](R0-C3-Safe-CSV-Import.md)、[`R0-D1-Canonical-Workbench-Navigation.md`](R0-D1-Canonical-Workbench-Navigation.md)、[`R0-D2-Unified-Unsaved-Changes-Guard.md`](R0-D2-Unified-Unsaved-Changes-Guard.md)、[`r0-d4b2a-finance-scope.md`](r0-d4b2a-finance-scope.md)、[`r0-d4b2a-focused-repair.md`](r0-d4b2a-focused-repair.md)、[`r0-d4b2b-procurement-scope.md`](r0-d4b2b-procurement-scope.md)、[`r0-d4b2c-api-permission-audit.md`](r0-d4b2c-api-permission-audit.md)、[`r0-d4b2c-api-permission-matrix.md`](r0-d4b2c-api-permission-matrix.md)。

- 业务规则/实现背景：[`TaskC-订单采购草稿闭环.md`](TaskC-订单采购草稿闭环.md)、[`TaskE-采购成本归属统一.md`](TaskE-采购成本归属统一.md)、[`TaskF1-到货库存预留一致性.md`](TaskF1-到货库存预留一致性.md)、[`TaskF2-超发安全冲销.md`](TaskF2-超发安全冲销.md)、[`TaskG1-基础收付款一致性.md`](TaskG1-基础收付款一致性.md)、[`TaskG2-轻量合同金额调整.md`](TaskG2-轻量合同金额调整.md)、[`TaskG3-基础财务报表与利润口径.md`](TaskG3-基础财务报表与利润口径.md)、[`TaskH1-客户跟进报价链路.md`](TaskH1-客户跟进报价链路.md)、[`TaskI1-产品分类与SKU身份边界.md`](TaskI1-产品分类与SKU身份边界.md)、[`TaskI2-供应来源交易单位包装与销售规则.md`](TaskI2-供应来源交易单位包装与销售规则.md)、[`TaskJ1-系统入口与经营视图收敛.md`](TaskJ1-系统入口与经营视图收敛.md)、[`TaskK1-正式测试前系统完整性收尾.md`](TaskK1-正式测试前系统完整性收尾.md)。

## Git 历史核对

核对 `master` 至基线 `ecdc9bc` 的历史及相关修复链。R0-D4 最近关键提交包含 `2a9d6cd`（财务数据范围）、`11fb307`（供应商 Context）、`7e5e565`（共享采购销售关联）、`af386d7`（跨模块权限审查缺口）；`24dc2b1` 关闭 Browsable API 关联泄漏。历史 P1/UI 修复和阶段记录保留在来源文档中。本轮对 ISS-053–ISS-055 只做源码、测试和历史记录检查，未运行相应回归或真实 UI；不通过提交日志推断没有测试过的 UI 流程已经通过。

## R0-F9-VIS-01 补充审查（2026-10-17）

| ID | 优先级 / 状态 | 首次发现来源 / 日期 | 最近核实与影响 | 负责人 / 下一步动作 | 计划阶段 | 关闭验收依据 |
|---|---|---|---|---|---|---|
| ISS-101 | P2 / FIXED_PENDING_REVIEW | 用户独立审图发现12张加载中图片；2026-10-17 | E类采集完成态判定缺失。实际复现DOM完成但首帧仍旧；新流程等待业务状态、连续DOM、轮询原始JPEG尺寸/帧哈希，最终81图稳定。点名12图均补完成数据截图；100的精确尺寸限制仍单列；未发现持续加载程序故障 | 前端QA / 独立复核loading-comparison-12.json、原图/DOM、采集脚本；不可用CI替代图片验收 | R0-F9-VIS-01 | 12项完成态及最终81图经独立接受；诊断图不混入最终 |
| ISS-102 | P2 / FIXED_PENDING_REVIEW | 用户核实chrome/skus-settled-1440与1024同SHA；2026-10-17 | E类跨视口旧帧/归档未校验。旧同SHA确认；本轮复现设置视口后首帧滞后，新增物理尺寸/DOM前后校验与原帧观察，新Chrome1440/1280/1024尺寸正确且SHA不同。旧文件缺内部轨迹，不断言唯一历史成因；未仅改名 | 前端QA / 独立检查Chrome三图布局、尺寸/SHA、diagnostics与采集条件；与100剩余尺寸限制分开接受 | R0-F9-VIS-01 | 当前三视口独立原图及来源被接受，跨视口不复用旧图 |
| ISS-103 | P3 / NEEDS_VERIFICATION | VIS-01真实浏览器console；2026-10-17 | C/E类既有OrderDetailModal在Transition中非单元素根节点警告。运行基线9d05a70未改组件；本轮订单数据完成、关联跳转正常，尚未定位动画影响与全部触发条件；日志browser-console.json，不扩大业务修复 | 前端QA / 最小化根节点与动画复现，评估有无可见回归后单独处理 | 后续核实；不进入历史集中修复 | 警告原因与动画/关闭行为有可重复证据，修复后按协议独立验收 |

最新总计103个唯一ID：OPEN=6，BLOCKED=21，NEEDS_VERIFICATION=28，FIXED_PENDING_REVIEW=40，CLOSED=8；P0=0，P1=19，P2=74，P3=7，Enhancement=3。上述100条统计为2026-10-16历史快照。本轮未关闭历史Issue；095/096既有接受范围不扩大，097不变。新增A类P0/P1未确认。详见[R0-F9-VIS-01报告](R0-F9-VIS-01-全站视觉复核与补充截图.md)与[新索引](uat-evidence/r0-f9-vis-01/index.html)。

## R1-A 当前统计（2026-10-18）

103个唯一ID：OPEN=4、BLOCKED=22、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=43、CLOSED=8。仅001由OPEN转业务BLOCKED，004/005由待核实转待复审，054由OPEN转待复审；006保持待核实。历史统计是各轮快照，未覆盖或旧独立图片事项不自动关闭。详见[R1-A](R1-A-核心业务历史Issue核实与修复.md)。

## R1-A-FUP-01 复审补修（2026-10-18）

| Issue | 优先级 / 状态 | 首次问题与来源 | 当前结果 / 根因 / 修复 | 下一步与最终验收条件 |
|---|---|---|---|---|
| ISS-104 | P1 / FIXED_PENDING_REVIEW | ChatGPT独立复审，基线f9a9cfb：记账请求状态不明后关闭表单，可能丢失稳定流水编号并造成重复记账风险 | 旧guard空快照不能识别修改；网络异常与明确拒绝未区分。现改真实快照、初始化基线、busy拦截、稳定编号显示及结果不明放弃风险确认；真实Django201提交后代理丢弃响应，重试400，数据库逐行不变。修复提交为本节所在Git提交，详见[FUP-01](R1-A-FUP-01-财务重试安全验收.md) | 等待ChatGPT独立代码、原图及数据库证据复审；跨刷新恢复、全站通用幂等不在本轮宣称范围，不自动关闭 |

ISS-004继续FIXED_PENDING_REVIEW：补充本轮原编号重试与表单保护证据，旧空快照通过结论撤回。ISS-001继续BLOCKED，等待业务决定；ISS-005/006/054状态及既有验收范围不变。104个唯一ID：OPEN=4、BLOCKED=22、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=44、CLOSED=8；P1=20，其余优先级计数不变。

## R1-FIN-AUDIT-01 只读审查（2026-10-18）

| Issue | 优先级 / 状态 | 首次来源 / 最近核实 | 影响与根因 | 负责人 / 下一步 / 阶段 | 最终验收依据 |
|---|---|---|---|---|---|
| ISS-105 | P1 / FIXED_PENDING_REVIEW | 2026-10-18用户财务统计审查；原基线财务来源3a07e7ef1a9e63c98077d45492ba23b798c7fcdd；本轮完整反例来源e301a86044ffe56b72172a94dc3b00ae09401b05 | 当前已包含参考折算/实际资金区分、显式账户、独立启用基准、有效完整更正、转账本金及独立手续费、退回/退款审批、账户核对、私有银行凭证。集成c1937da后端1249项1189通过/60跳过；Chrome认证和开发资金页面各2/2。319941c新增回退与凭证备份保护；真实PG17专项13/13，新财务表与文件恢复一致。来源与完整日志见[综合报告](uat-evidence/review-integration-batch-20261104/README.md)、TEST-RESULTS.md及REVIEW-FINANCE-SOURCE.md。  本轮定向反例补充（2026-11-04）：API可将已追加分类为expense的事实匹配内部本金，且新增本金匹配后完成核对不失效；统一集成已在8087产品代码独立复现3/3失败（含新旧混合匹配），原日志finance-counterexamples-before-fixture-corrected.log保留。最小修复90683506f5d9447974302d83c89ba27351d5dfd4：按有效追加分类校验并在共享锁内重验，将新/旧本金匹配纳入核对指纹；未匹配账户指纹保持旧格式，有匹配的旧核对保守要求重核，不改资金/余额。修后SQLite32/32通过（含5项新回归）；同代码9068350的真实PG17.11专项12/12通过（新回归5/真实性2/真实并发5），99表1081行128迁移4文件恢复及私有HTTP4/4；最终SHA CI按本轮最终报告记录，不提前记通过。 第三项本轮确认缺陷ADV-03：finance-ledger未声明模块，普通认证的全局财务授权角色被通用权限层403拒绝；超管成功不能证明角色可用。候选报告2e20bfdccb711bdd5f9028cb60e287ee742c77c5仅只读检查尚未接收；主审在906产品代码独立6项角色回归为1通过/5失败（finance-role-before.log）。最小补修9af2a32fa81df3aa975424b70a887057e40b6b22已覆盖只读预览、create/update分离及既有finance或reports导出契约，相关SQLite91/91、干净9af检出的真实PG17专项64/64通过；恢复99表1081行128迁移4文件、HTTP4/4、源未变且清理完成。主树未提交测试触发的保护拒绝日志保留，未放宽干净源码保护。不启用运行环境正式RBAC，不改开发超级管理员判定。侧审另列非规范export值的既有解析/格式差异：当前受支持契约为小写csv，未证明越权，不在本轮擅自增加格式或别名，按105兼容边界待独立核查。 后续a8400fb8deb1bfeaaf99e0498d8b4aa34ef48f3f已提交有序锁/截止日7测试，原clean guard下真实PG专项25/25通过，包含三个独立backend PID/实际阻塞/锁前预读/审计与余额原子断言；不采信已中止的未提交草稿例外。全量本地/最终SHA三CI单独记录。旧合法匹配的核对摘要兼容/一次重核已验；未扫描目标存量中旧缺陷已造成的错误匹配，也不自动改写不可变历史关系，启用前须只读核查并按受控审查处理，不把新写入口修复宣称为存量自动修复。| 已有实现待ChatGPT独立复审；8087f2c / CI41839476121三CI已实际核实SUCCESS，PG17全量1282通过/30跳过、Playwright270（混合通道）通过；财务反例已统一补修，独立复审仍待完成，真实账户/日期/余额/来源资料由负责人提供；不重新询问已确认资金原则。  事实CSV浏览器下载生命周期补修02140bf46df27ba1abf5b9018507c07aae825769：link附DOM再点击、延后释放；原Google Chrome1440/390两场景2/2，原CSV源编号和123.45断言保留；与API200区分实际文件下载，不改金额/权限/日期。最终新冻结全量另验。 | 实际资金、账面参考和账户余额范围准确；正常/拒绝/并发/审计/历史保护与独立复审通过，不以开发session代替正式身份验收。 |

105个唯一ID：OPEN=5、BLOCKED=22、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=44、CLOSED=8；P1=21，其余优先级计数不变。既有Issue状态保持，本轮未修复/关闭Issue；精度收敛为拟议新政策，旧4位记录不据此认定错误。

## R1-A-FUP-02 当前核实（2026-10-18）

用户正式确认履约与财务结清独立，并明确FUP-01已通过ChatGPT独立复审（仅记录本轮前置依据，不改变ISS-004/104状态）。仅ISS-001由BLOCKED转FIXED_PENDING_REVIEW；105个唯一ID：OPEN=5、BLOCKED=21、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=45、CLOSED=8。优先级计数不变，其他Issue状态及既有验收范围保持。完成后等待独立审查，不进入R1-B、正式RBAC、员工UAT或部署。

## R1-A-FUP-02-FIX-01 独立审查补修（2026-10-18）

ISS-001保持FIXED_PENDING_REVIEW。用户本轮独立审查指出非零有效订单no_plans/review仍显示零待收及空待办；现补只读核对待办、未知待收“待核对”、列表派生状态及财务查看权限，未补建历史计划或改余额。正常500/340/160→结清→退款40真实UI及数据库回归见[补修验收](R1-A-FUP-02-FIX-01-独立审查补修验收.md)。首次问题、前轮修复证据和关闭条件仍按原ISS-001记录保留；下一步由ChatGPT独立复审本轮代码、原图、数据库及精确HEAD CI。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前核实及影响 | 负责人 / 下一步 | 阶段 / 验收条件 |
|---|---|---|---|---|---|
| ISS-106 | P2 / FIXED_PENDING_REVIEW | 用户转述ChatGPT独立审查，DocumentPage报价列名被订单履约文案串改；2026-10-18 | 基线7faafcf复现报价列名“履约状态”；本轮报价恢复“状态”，订单保持“履约状态”，增加共享组件双向切换回归及真实Chrome截图 | 前端QA / ChatGPT独立复核表头、共享页面回归和原图，不自行关闭 | R1-A-FUP-02-FIX-01 / 报价与订单表头分别正确、精确HEAD三项CI成功且独立接受 |

本轮新登记1项ISS-106，修复待复审；未关闭任何Issue，其他已有Issue状态不变。106个唯一ID：OPEN=5、BLOCKED=21、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=46、CLOSED=8；P0=0、P1=21、P2=76、P3=6、Enhancement=3。历史BLOCKED/业务待决及延期不因本轮变化。ISS-105及R1-FIN-AUDIT-01人民币统计/银行结汇方案未实施。仅等待独立审查，不进入下一阶段。

## R1-FIN-P0 口径确认与实施准备（2026-10-18）

当前基线da39ea3aa986df9faa12e79b1da3adece03260b7的Backend、Backend PostgreSQL、Frontend经GitHub重新核实均SUCCESS。用户已确认：原币辅助账保留，银行实际结汇所得CNY才是相应人民币到账事实，参考折算不得冒充实际到账，结汇不重复登记客户收款或核销应收，历史金额不得擅改。

ISS-105仍P1/OPEN，确认方向不等于代码已修复。当前源码仍由原币×汇率生成rmb_amount，概览/CSV语义缺口保留。本轮[准备报告](R1-FIN-P0-财务统计口径确认及实施准备.md)给出两类增量记录最小方案、资金/参考/辅助账边界、新旧精度兼容与分阶段任务。财务负责人下一步回答D01–D08（费用、确认依据、历史cutover、日期/更正、精度与碎分、退款来源、账户范围、损益暂缓），ChatGPT独立复审后再另行授权具体实施。原ISS-105来源、关闭条件和审查记录保留，不自行转为修复完成。

本轮未新增缺陷ID、未修复待关闭或关闭Issue；001/106及全部既有状态保持。按106个唯一ID重新核对状态：OPEN=5、BLOCKED=21、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=46、CLOSED=8。历史BLOCKED/延期和未覆盖范围继续保留；本轮不读取业务库、不执行迁移、不实施结汇、正式RBAC、员工UAT或部署。优先级治理附注：上一轮汇总P3=6，但当前显式P3记录有7项（058/048/049/050/074/099/103），本轮不重定历史优先级，旧汇总作为历史快照保留并待治理复核；不据该统计差异扩大财务开发范围。

## R1-FIN-P1 口径澄清（2026-10-18）

ISS-105保持P1/OPEN。已澄清财务概览、月度/分类、cash来源、流水/计划表单、API口径说明及CSV，统一“账面人民币折算参考”，明确包含原币CNY既有流水，不代表银行实际到账、结汇或账户余额。相同合成数据库前后API/CSV数值和全部CRM记录哈希一致；详见[P1验收](R1-FIN-P1-现有财务统计口径澄清验收.md)。本轮没有银行资金事实或结汇记录，故不满足ISS-105完整关闭条件。其他既有Issue状态及验收范围不变。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前证据与范围 | 负责人 / 下一步 | 关闭验收条件 |
|---|---|---|---|---|---|
| ISS-107 | P2 / FIXED_PENDING_REVIEW | R1-FIN-P1源码核对，2026-10-18 | 已确认缺陷仅为Transaction.rmb_amount模型元数据仍标为“实际人民币金额”，以及资源入口描述未区分银行事实；公开流水序列化标签、财务概览、报表、CSV、旧保存配置已先行澄清且本轮复核通过。稳定API键income_rmb/expense_rmb/net_cash_rmb/rmb_amount及source=cash保留；本轮新增0081仅调整模型显示元数据，不改历史迁移、金额或配置 | 证据见 `docs/uat-evidence/r1-fin-p1/ISS-107-FOLLOWUP.md`；等待独立代码、财务口径和视觉复审，不自行关闭 | 模型元数据及自动生成界面无误导旧称；银行实际净额与账面参考分离；历史金额、API键、CSV和保存报表均不变，独立复审通过 |

107个唯一ID：OPEN=5、BLOCKED=22、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=46、CLOSED=8。新增仅107，不修改其他Issue状态，不因本轮文案澄清宣称实际资金统计已实现。停止等待ChatGPT独立代码与视觉复审。

## R1-FIN-P2-A 后端资金事实与安全闭环（2026-10-18至19）

D01–D08由用户正式确认：银行净额为CNY事实，凭证人工确认，启用日不代选，按银行入扣日期、常用币2位/JPY0位/6位汇率与HALF_UP，旧4位不舍入，未知退款/作废不释放来源，同币种合并/分次，无自动损益或完整银行余额。新增RmbCashEvent/CashSourceAllocation、0077仅增量两表迁移、API及PG并发回归。真实合成HTTP和数据库旧模型哈希相等；来源作废/替代及未知退款有依赖时安全拒绝。见[P2-A实施与证据](R1-FIN-P2-A-人民币资金事实与结汇后端验收.md)。

ISS-105保持P1/OPEN：事实后端不等于实际资金统计已切换；不改既有概览/cash报表/CSV金额、不关闭既有问题。本段记录的2026-10-19历史状态中ISS-107保持BLOCKED；2026-10-24跟进已按独立证据更新为FIXED_PENDING_REVIEW。其余107个既有Issue状态保持。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前证据与影响 | 负责人 / 下一步 / 阶段 | 最终验收依据 |
|---|---|---|---|---|---|
| ISS-108 | P1 / FIXED_PENDING_REVIEW | 用户R1-FIN-P2-A规则D04/D06；已确认原则沿用；完整财务来源3a07e7ef1a9e63c98077d45492ba23b798c7fcdd | 可追溯完整更正、银行退回、敏感退款申请/批准/实际扣款区分、真实双人审批和来源限制已经实现，不再描述为尚未实施。原事实与凭证不可直接覆盖，批准不等于实际扣款，不自动释放未知来源额度；集成Chrome两尺寸及负路径已实跑，精确结果和源码见[财务预审](uat-evidence/review-integration-batch-20261104/REVIEW-FINANCE-SOURCE.md)。 | 8087f2c / CI41839476121三CI已实际核实SUCCESS，PG17全量1282通过/30跳过及同SHA隔离15/15；待财务反例专项及ChatGPT逐项独立复审；真实每笔撤回退款凭证、金额与期间仍需实际资料，不由代码猜测。 | 原始事实不改写、来源及实际期间可核实、不重复核销或释放额度；正常/拒绝/事务原子性/并发与独立复审通过。 |

108个唯一ID：OPEN=5、BLOCKED=23、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=46、CLOSED=8。新增仅108，不关闭或改变其他Issue状态。本轮不设正式启用日，不配置真实账户，不启用RBAC或部署；完成后等待ChatGPT独立复审。

## R1-FIN-P2-A 精确CI跨日回归补修（2026-10-19）

首推8706200632980c7e3a6a5e0b776e81fdac7e1613的SQLite与PostgreSQL全量各764项，仅旧test_multi_plan_decimal_and_overdue跨日断言失败；三个新PG真实并发场景及旧数据迁移保护均通过。原始失败日志保留。本次只为旧测试显式设置固定测试日和两期到期日，并同时断言部分逾期135.32与两期逾期485.32，业务逾期算法不变。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前证据与根因 | 负责人 / 下一步 | 最终验收依据 |
|---|---|---|---|---|---|
| ISS-109 | P2 / FIXED_PENDING_REVIEW | GitHub CI #39144166262，8706200632980c7e3a6a5e0b776e81fdac7e1613；2026-10-19 | 原应收回归测试将第一期设为真实今天前一天，却沿用固定历史第二期交期；跨日后第二期也逾期，期望135.32变实际485.32。已固定fixture测试日和两个到期日，补充未来日期全部逾期断言。只改测试，不改规则/金额 | QA / 独立复核日期边界与精确最终HEAD完整SQLite/PG回归，不自行关闭 | 任意执行日期下均按显式测试日验证正确部分/全部逾期；两类数据库完整CI及独立审查通过 |

109个唯一ID：OPEN=5、BLOCKED=23、NEEDS_VERIFICATION=26、FIXED_PENDING_REVIEW=47、CLOSED=8；既有107项状态不变，108仍BLOCKED，105仍OPEN。该CI修正不扩大资金业务规则范围，不自动进入下一阶段。

## R1-FIN-P2-B 银行结汇及人民币实际资金前端（2026-10-19）

基线 `b79af36dc7140507ef210ea61437dd579ba8de8b` 的三项CI在实施前均为SUCCESS。本轮只增加前端页面和Node回归：人民币资金列表/详情、新建事件两步表单、后端预览、来源额度与历史高精度人工输入提示、稳定请求键、待确认/已确认/已放弃状态和只读详情；真实浏览器在隔离合成库完成登记、放弃、重新登记、预览和确认。前端不推断或计算银行事实，确认仍由P2-A服务端校验，来源金额和银行净额均以Decimal后端结果为准。

P2-B保留旧财务流水、应收应付核销、报表和统计金额；不创建第二笔客户收款，不修改旧Transaction、PaymentPlan、AdvanceAllocation或历史4位金额，不把参考折算变成实际到账。合成数据库记录、来源快照、凭证引用和多尺寸截图见[P2-B验收](R1-FIN-P2-B-人民币资金前端验收.md)。ISS-105继续P1/OPEN，ISS-108继续BLOCKED，ISS-109继续FIXED_PENDING_REVIEW；其他Issue状态不变。交付后停止等待ChatGPT独立代码和视觉复审，不自动进入P2-C、正式RBAC、员工UAT或部署。

## R1-FIN-P2-B-FIX-01 银行资金前端安全流程补修（2026-10-19）

独立审查发现预览内容、未保存保护、来源人工核实和异步来源请求存在安全缺口。本轮仅修复前端流程与回归，不改变P2-A资金计算、历史金额、核销或报表来源；新增证据见[R1-FIN-P2-B-FIX-01验收](R1-FIN-P2-B-FIX-01-银行资金前端安全补修验收.md)。ISS-105仍OPEN，ISS-108仍BLOCKED，ISS-109仍FIXED_PENDING_REVIEW；未关闭任何Issue。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前核实及影响 | 负责人 / 下一步 | 阶段 / 验收条件 |
|---|---|---|---|---|---|
| ISS-110 | P1 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B；2026-10-19 | `CashEventPage.vue`预览成功后修改金额、日期、手续费、来源或凭证仍可沿用旧结果登记，可能造成登记内容未经过对应预览。已增加完整规范化请求指纹、字段变化失效、登记前指纹检查及服务端继续复核；新增Playwright覆盖金额修改和预览失效。 | 前端QA / 独立复核请求指纹覆盖字段、旧预览无法登记及异常网络回归 | R1-FIN-P2-B-FIX-01 / 修改任一资金事实必须重新预览，精确HEAD CI与独立审查通过 |
| ISS-111 | P1 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B；2026-10-19 | 预览成功调用`formGuard.markClean`，把仍未登记的输入误判为已保存，关闭/导航可能静默丢失。已移除预览清洁标记；登记、确认、放弃成功后才清理基线，并以24小时本地临时快照恢复稳定请求键和必要输入。 | 前端QA / 独立复核关闭、遮罩、路由、刷新及响应不明回查；确认不持久化凭据 | R1-FIN-P2-B-FIX-01 / 未保存内容持续受保护，成功保存后可关闭，精确HEAD CI与独立审查通过 |
| ISS-112 | P1 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B；2026-10-19 | 原`eventPayload`把所有选中来源自动标记`verified=true`，页面没有逐条人工核实动作。已改为来源选择与核实分离，逐条勾选后才可预览，最终确认增加完整摘要和显式确认。 | 财务QA / 独立复核来源账户、来源金额、凭证、净额和手续费摘要及后端拒绝路径 | R1-FIN-P2-B-FIX-01 / 未逐条核实不能登记，已确认记录只读，权限与P2-A校验保持有效 |
| ISS-113 | P2 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B；2026-10-19 | 来源币种切换/刷新时旧请求可能覆盖新来源并展示失效额度。已加入请求序号、AbortController、币种一致性检查和失败保留输入。 | 前端QA / 独立复核快速切换币种、重试和网络失败时不显示旧额度 | R1-FIN-P2-B-FIX-01 / 旧响应不能覆盖当前币种，精确HEAD CI与独立审查通过 |
| ISS-114 | P2 / NEEDS_VERIFICATION | P2-B原始全量Playwright记录；2026-10-19 | 2026-10-28 / 固定基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb` 的集成报告记录完整可运行 Playwright 189/189 通过。历史 8 项失败原始记录保留，精确 CI/独立复核未执行；保持 P2 / NEEDS_VERIFICATION。 历史台账结论保留：基线记录曾为139 passed/8 failed（finance-reference-basis 2、finance-retry-safety 1、fulfillment-receivables 5）。本轮在同一隔离工作区先单独复现，8项均通过；随后完整150项（含3项新增）通过，未删除或跳过测试。尚需独立复核精确HEAD及CI是否稳定复现。 | QA / 在精确HEAD三项CI和独立复审中复核历史8项失败是否为环境/跨日不稳定；不得以一次本地通过关闭 本轮仅做状态对账，不扩大为生产/正式员工验收。 | R1-FIN-P2-B-FIX-01 / CI与独立复审确认历史失败分类，保留原始日志和当前全量日志 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 |

本轮新增ISS-110至ISS-114；110–113为修复待复审，114保留NEEDS_VERIFICATION；ISS-105、ISS-108、ISS-109及其他Issue状态不变。114个唯一ID：OPEN=5、BLOCKED=23、NEEDS_VERIFICATION=27、FIXED_PENDING_REVIEW=51、CLOSED=8；P0=0。不得进入P2-C、P3、正式RBAC、员工UAT或部署。

## R1-FIN-P2-B-FIX-02 银行资金前端剩余安全边界补修（2026-10-19）

基于 `aef3425ec97b78c3a312f54010d9de60613e75a4`，仅修复草稿恢复后的未保存保护、来源分配金额与人工核实状态脱节、以及本地草稿快照字段和过期清理边界。未修改P2-A后端资金计算、历史数据、应收应付核销、权限策略或数据库模型；真实截图和日志见[R1-FIN-P2-B-FIX-02验收](R1-FIN-P2-B-FIX-02-银行资金前端剩余安全边界补修验收.md)。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前核实及影响 | 负责人 / 下一步 | 阶段 / 验收条件 |
|---|---|---|---|---|---|
| ISS-115 | P1 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B-FIX-01；2026-10-19 | 恢复本地草稿后 `useUnsavedChangesGuard` 基线仍为 `null`，直接关闭可能不提示而清除草稿。已在恢复前建立空白新建基线，恢复内容保持dirty；取消关闭保留输入/请求键，确认放弃才清理快照，并新增真实Playwright回归 | 前端QA / 独立复核恢复、关闭取消/确认、刷新和成功保存后的边界 | R1-FIN-P2-B-FIX-02 / 恢复草稿直接关闭必提示，取消不丢数据，确认放弃清理快照，精确HEAD CI与独立复审通过 |
| ISS-116 | P1 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B-FIX-01；2026-10-19 | 来源分配金额修改后仍可能保留 `verified=true`，导致人工核实状态不再对应当前金额。已加入金额编辑立即撤销核实、金额基线追踪及30→50 Playwright回归；后端额度/状态校验保留 | 财务QA / 独立复核多来源金额编辑、重新核实、重新预览及后端拒绝路径 | R1-FIN-P2-B-FIX-02 / 30→50必须重新核实和预览后才能登记，精确HEAD CI与独立复审通过 |
| ISS-117 | P2 / FIXED_PENDING_REVIEW | ChatGPT独立审查R1-FIN-P2-B-FIX-01；2026-10-19 | 本地快照此前按整个表单对象保存，缺少初始化过期清理和敏感字段边界。已改为字段白名单、版本化快照、页面初始化清理过期记录；凭证引用/SHA256/人工核实说明不落本地，恢复后要求重新填写；稳定请求键仍可用于结果不明回查 | QA / 独立复核localStorage内容、24小时期限、放弃/成功登记清理及响应不明回查 | R1-FIN-P2-B-FIX-02 / 不保存凭证敏感字段，过期即清理，成功/明确放弃清理，精确HEAD CI与独立复审通过 |

本轮新增ISS-115至ISS-117，均为 `FIXED_PENDING_REVIEW`；ISS-110至ISS-113仍待复审，ISS-114仍为`NEEDS_VERIFICATION`，ISS-105仍OPEN，ISS-108仍BLOCKED，ISS-109仍FIXED_PENDING_REVIEW；不得自行关闭或进入P2-C、正式RBAC、员工UAT或部署。117个唯一ID：OPEN=5、BLOCKED=23、NEEDS_VERIFICATION=27、FIXED_PENDING_REVIEW=54、CLOSED=8；P0=0。

## R1-FIN-P2-C 银行资金记录与结汇完整业务闭环验收（2026-10-19）

基线为 `9cd57800ce524d8e0ead90f245215ac4153cf144`。使用隔离 SQLite、合成客户/订单/银行凭证和真实 Chromium 完成外币分次结汇、同币种合并、预收核销、CNY直接收付、手续费、确认/放弃、请求键回查、超额/重复/退款/作废拒绝、历史4位与JPY精度等场景。原有Transaction、PaymentPlan、AdvanceAllocation、Order和库存未被结汇改写；既有参考统计未混入新资金事实。完整证据见[R1-FIN-P2-C验收](R1-FIN-P2-C-银行资金记录与结汇完整业务闭环验收.md)。

| ID | 优先级 / 状态 | 首次发现 / 最近核实 | 影响与处理 | 下一步 / 关闭条件 |
|---|---|---|---|---|
| ISS-118 | P1 / FIXED_PENDING_REVIEW | P2-C隔离复核；2026-10-19 | 旧版localStorage草稿可能保留凭证引用、SHA256和人工核实说明。恢复后立即用白名单覆盖旧快照；敏感字段不落本地，恢复后重新填写 | ChatGPT独立复核字段、过期清理和恢复边界；不自行关闭 |
| ISS-119 | P2 / FIXED_PENDING_REVIEW | P2-C真实UI；2026-10-19 | 独立手续费允许不关联父结汇；有明确来源时fee_for可选关联。当前cash_events.normalize以payload.get("fee_for")接收空值，保留关联时的权限/来源校验。含扣/另扣不重复扣减，旧“必须关联且无选择器”只属历史背景。 | 独立复核无关联合法手续费、可选已核实来源、不可见批次/无效关联拒绝、含扣/另扣一致且不重复扣费；不把可选关系改成强制，不自行关闭。 |
| ISS-120 | P1 / FIXED_PENDING_REVIEW | P2-C真实UI；2026-10-19 | 浏览器数字输入把`87.60`变为JS `87.6`，服务端Decimal精度校验拒绝。请求体改为规范化字符串，后端规则不变 | 独立复核金额序列化、精度拒绝及历史兼容；不自行关闭 |

ISS-105保持OPEN，ISS-108保持BLOCKED，ISS-109至ISS-117及其他历史Issue状态保持不变。当前唯一ID计数：120个；OPEN=5、BLOCKED=23、NEEDS_VERIFICATION=27、FIXED_PENDING_REVIEW=57、CLOSED=8；P0=0。P2-C完成后停止等待独立复审，不进入P3、正式RBAC、员工UAT或部署。

## R1-FIN-P3-A 人民币实际资金统计与独立报表（2026-10-19）

基线 `c895e1d0d758c1a9c158e940975689dc4b0ae0d6`。本轮新增独立只读`actual_cash`统计来源和`/api/actual-rmb-cash/`：只聚合`RmbCashEvent`中按银行日期人工确认的人民币银行净额，提供总流入/流出/净流量、月度、类型、逐笔下钻和CSV；财务概览与报表中心均保留旧“账面人民币折算参考”并明确两种口径。没有修改Transaction、PaymentPlan、AdvanceAllocation、订单、库存或历史金额，没有设置统计启用日或推测余额。隔离真实HTTP、数据库SHA和1440/1280/1024页面截图见[R1-FIN-P3-A验收](R1-FIN-P3-A-人民币实际资金统计与独立报表验收.md)。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前核实及影响 | 负责人 / 下一步 | 阶段 / 验收条件 |
|---|---|---|---|---|---|
| ISS-121 | P1 / FIXED_PENDING_REVIEW | R1-FIN-P3-A规则及历史启用要求；2026-10-19；INTEGRATION-CLOSEOUT-02用户定向复审2026-11-04 | 完整历史来源ba4274742727a6794608dc8581a49b3692d865a6已合入447d7816ead2e971e249cb2e762b1a6f7009b9c0；资金/未结/库存基准/履约均有正式接续入口，不再是三个not_connected未实施。0108补齐三张新表TRUNCATE保护；0104–0108来源blob与集成一致。集成PG1410项1378通过32跳过，三新表实际填充2/1/2行后102表1218行133迁移5文件恢复一致、源未变、隔离集群清理完成。同一02140集成Chrome五阶段及live/副本只读核验已通过，独立复审仍待完成，源编号边界/凭证人工对应/已记账更正及目标启用须逐项独立接受，暂不自行关闭。见integration-closeout-02/INTEGRATED-SOURCE-REVIEW-447D.md及最终PG证据。 | 已授权历史包开发和合成验收资金、未结、库存基准、剩余履约及组原子性；统一集成接收完整稳定SHA并核对正式服务/财务双人审批/幂等/并发/拒绝路径，不再因缺真实资料停止实施。真实日期、账户余额/凭证和真实导入另受外部资料及单独授权边界约束。 | 已授权实施与合成验收；正式启用另行授权 | 同组合成资料完成归档→批准→接续→后续收付/履约→核对，逐表无重复资金/库存，真实PG17竞争/迁移/故障原子性及Chrome1440/390证据齐全，开发侧实现及隔离证据齐备，现转待独立复审；只有ChatGPT独立接受或用户接受后才可CLOSED，不以真实资料缺失代替代码完成。 |

本轮新增ISS-121，保持`BLOCKED`；ISS-105仍OPEN、ISS-108仍BLOCKED，其他Issue状态不变。当前唯一ID计数：121个；OPEN=5、BLOCKED=24、NEEDS_VERIFICATION=27、FIXED_PENDING_REVIEW=57、CLOSED=8；P0=0。P3-A完成后停止等待ChatGPT独立代码、财务口径和视觉复审，不进入P3-B、正式RBAC、员工UAT或部署。

## R1-FIN-P3-A-FIX-01 实际人民币资金统计安全与容错补修（2026-10-19）

基于P3-A精确基线 `470eb34e161d97f68ff8a1151870a6ab687f32ea`，本轮仅补修财务概览实际资金接口失败隔离、日期快速切换竞态，以及银行实际资金CSV的公式注入保护。旧账面人民币折算参考、P2-A资金事实与结汇计算、历史金额、核销记录、统计启用日期和权限策略均未改变；真实隔离页面、HTTP观察、截图和日志见[R1-FIN-P3-A-FIX-01验收](R1-FIN-P3-A-FIX-01-实际人民币资金统计安全补修验收.md)。

| ID | 优先级 / 状态 | 首次来源 / 日期 | 当前核实及影响 | 负责人 / 下一步 | 阶段 / 验收条件 |
|---|---|---|---|---|---|
| ISS-122 | P1 / CLOSED | P3-A独立审查补修；2026-10-19 | `FinanceDashboardPage.vue`原先用`Promise.all`绑定旧财务概览和实际银行资金接口；实际资金失败会让整页失败，日期切换时旧响应也可能覆盖新期间。本轮拆分请求、清空当前期间旧数据并加入两级请求版本保护；实际资金独立错误和重试保留，旧财务概览继续可用。新增Vitest与Playwright覆盖失败、独立重试和快速日期切换。 | 前端QA / ChatGPT独立复核接口失败、重试、日期竞态及三视口真实页面证据；不自行关闭 | R1-FIN-P3-A-FIX-01 / 旧财务概览在实际资金失败时仍可用，旧期间资金不得显示，精确HEAD三项CI及独立复审通过 |
| ISS-123 | P1 / CLOSED | P3-A独立审查补修；2026-10-19 | `actual_cash_api.py`原先直接写入银行参考号等文本；以`=`,`+`,`-`,`@`等开头的内容可能被表格软件解释为公式。本轮复用既有`safe_csv`，保护说明、表头、事件文本和汇总标签；API/数据库原文不改，正常参考号仍可读；报表中心既有导出已使用同一保护函数。新增恶意银行参考号与权限403回归。 | 后端/财务QA / ChatGPT独立复核CSV原始字节、正常文本可读性、实际资金与报表中心权限边界；不自行关闭 | R1-FIN-P3-A-FIX-01 / 危险前缀加单引号、原文API不变、无权限不泄露、精确HEAD三项CI及独立复审通过 |

本轮新增ISS-122、ISS-123；依据用户提供的独立复审通过结论，二项更新为`CLOSED`。ISS-105仍OPEN，ISS-108和ISS-121仍BLOCKED，ISS-109至ISS-120及其他历史Issue状态不变。当前唯一ID计数：123个；OPEN=5、BLOCKED=24、NEEDS_VERIFICATION=27、FIXED_PENDING_REVIEW=57、CLOSED=10；P0=0。完成后停止等待ChatGPT独立代码、财务口径和视觉复审，不进入P3-B、正式RBAC、员工UAT或部署。

## R1-FIN-P3-B 财务统计最终业务闭环与兼容性验收（2026-10-19）

基于 `c27abcb2e95b833c3a4f4c59161c3fcc7c1d4f64`，在隔离 SQLite、合成外币订单/收款/应收计划/银行凭证和真实 Chromium 中完成 A–O 场景验收。实际资金统计只聚合已确认 `RmbCashEvent.bank_net_amount`，按 `bank_date` 统计；旧 `cash` 来源继续是账面人民币折算参考。分次/合并结汇、CNY直接收付、含扣及独立手续费、pending/cancelled边界、跨月跨年、旧四位和JPY精度、权限和旧报表兼容均有原始 API、CSV、数据库快照和多视口截图。已有关联来源的退款/作废安全拒绝且前后哈希一致；不改Transaction、PaymentPlan、AdvanceAllocation、订单、库存或历史金额。完整矩阵和日志见[R1-FIN-P3-B验收](R1-FIN-P3-B-财务统计最终业务闭环验收.md)。

ISS-122、ISS-123 已依据独立复审通过结论更新为 `CLOSED`。ISS-105 仍 `OPEN`，ISS-108、ISS-121 仍 `BLOCKED`，未自动关闭或修改其他历史Issue。PostgreSQL本地不可用的并发复核和真实网络超时注入保留为报告中的BLOCKED/边界，不伪造通过；最终精确HEAD三项CI作为交付门槛复核。完成后停止等待ChatGPT独立代码、业务和视觉审查，不进入P3-C、正式RBAC、员工UAT或部署。

## R1-READINESS-01 全系统试用准备与业务阻断问题审查（2026-10-19）

基于精确 HEAD `199a21e0f407ba9ad772a5dec86e0b30dbd0c9b5` 进行只读审查，重新按每个 Issue 的最后一次记录核对 123 个唯一 ID：OPEN 5、BLOCKED 24、NEEDS_VERIFICATION 27、FIXED_PENDING_REVIEW 57、CLOSED 10。没有改变任何历史 Issue 状态；没有把 FIXED_PENDING_REVIEW、NEEDS_VERIFICATION 或 BLOCKED 自动转为 CLOSED。

R1-FIN-P3-B 的授权财务功能记录为阶段性验收通过；ISS-105 保持 OPEN，ISS-108 和 ISS-121 保持 BLOCKED。审查结论是当前可做开发身份下的隔离合成数据演练，但尚不具备真实员工内部试用条件。A 类门槛为 ISS-003（正式员工身份/数据范围）、ISS-018（数据库与媒体联合备份恢复）、ISS-055（跨客户 API 数据范围）；其余 Issue 按报告中的 A–D 矩阵登记。完整依据见 [R1-READINESS-01 审查报告](R1-READINESS-01-全系统试用准备与业务阻断问题审查.md)。

本轮不启动正式员工 UAT、正式 RBAC、生产部署或财务无关修改。

## ISS-048 当前子任务实施记录（2026-10-23）

在 `codex/iss-048-finance-drill` 基于 `fb859b91f68bb62c539d5439c65b52c06f13a58c` 完成可靠财务概览指标的构成明细、分页/排序、权限范围复用、原始订单/流水链接及银行事件表定位；SQLite 全量、财务/RBAC 定向、前端、真实 Chromium mock API 证据归档于 `docs/uat-evidence/iss-048-finance-drill/`。原 ISS-048 仍保持 `P3 / BLOCKED（延期）`，本轮只记录为 `FIXED_PENDING_REVIEW`，不提前关闭；未定义的会计利润、银行账户余额和未确认凭证不伪造下钻。下一步为独立代码/财务口径/权限/视觉复审，以及集成环境的真实 Django 跨账号浏览器验收。

## ISS-048-FIX-01 最小权限一致性补修（2026-10-23）

独立审查发现财务概览 `payable_count`、`payable_rmb` 只依赖采购查看权限，但下钻接口和前端入口额外要求订单查看权限。本轮基于 `codex/iss-048-finance-drill` / `f2a44dafabdd5cc7b4c5b95abed3865867fd9e7b` 进行了最小修补：应付款下钻与概览统一使用 `purchases.view`，采购成本/订单费用/预计利润以及销售/应收等其他指标权限不变；应付款明细固定走采购单关联，继续使用原有计划数据范围，未扩大跨部门或跨供应商访问。

新增并通过有采购无订单权限、无采购权限反向拒绝和范围一致性测试；前端同步修正应付款入口可见性。证据见 `docs/uat-evidence/iss-048-finance-drill/fix-01/`。ISS-048 继续保持 `P3 / BLOCKED（延期）`，本修补记录为 `FIXED_PENDING_REVIEW`，等待独立验收；未关闭 ISS-048，未修改其他 Issue 状态。

## ISS-026 / ISS-107 / ISS-017 统一集成验收（2026-10-24）

基于统一基线 `71ec4a4c2d860b9944624a1434d9d7580e9a6d38` 建立独立 `codex/integration-026-107-017` Worktree，并核实三个成果分支已在 GitHub 可见：ISS-026 `3625f472b028146c062823990322de32a98759a1`、ISS-107 `60df1b045c06c7f2146b44e4a60866b1786024cc`、ISS-017 `c5fc1c11b9728655a363a4f2a5ba0544584a8d07`。集成仅发生一处文档追加冲突，已保留双方记录；三条 `0081` 迁移通过无操作 `0082` 汇合，未删除或重写历史。

集成后 Django 全量为 862/862 通过（13 项跳过），Node 151/151、Vitest 645/645、生产构建、SQLite 新库/升级/回滚和真实 Chrome 关键页面回归通过。ISS-017 旧外部证书 URL 测试断言已按现行 400 安全规则同步，记录和有效期保持不变。ISS-026、ISS-107、ISS-017 均仍为 `FIXED_PENDING_REVIEW`；源任务 CI 及集成提交 `3571d374adb8e41d515265a5c429639d5b8f4904` 对应 GitHub CI 均失败且没有可用步骤日志，本地无 PostgreSQL 和生产代理/对象存储，故不宣称 master 合并就绪或生产安全验收完成。完整证据见 `docs/uat-evidence/iss-026-supplier-lifecycle/INTEGRATION-026-107-017.md`，等待统一独立审查。

## ISS-047 / ISS-097 / ISS-080 统一集成台账更新（2026-10-27）

以下均为更新既有 Issue 记录，不新增重复 Issue：

- **ISS-047（P1 / `DEPLOYMENT_VERIFICATION_PENDING`，现有状态保持 BLOCKED）**：来源 `codex/integration-047-097-080`，代码集成 HEAD `512e739ac2beffe90e7153087509b2734c64e853`。应用层私有上传、授权下载/拒绝、路径穿越、SHA256 清单、媒体/静态根隔离和重启模拟已由定向测试及 Django 全量覆盖；实际生产 Nginx/反向代理 ACL、持久卷、容量/inode 告警、PostgreSQL 与 DB+媒体联合恢复尚未具备环境证据。原因是本轮明确不部署、不连接生产；影响为生产文件安全和恢复能力仍不能宣称完成。后续条件是运维提供隔离 staging/生产、真实持久卷、代理和数据库权限；验收标准是直链拒绝、备份恢复、服务重启、容量告警、完整性哈希和 PostgreSQL 权限均有可复核记录，独立复审后再改变状态。

- **ISS-097（P2 / `FIXED_PENDING_REVIEW`）**：来源 `codex/integration-047-097-080`，代码集成 HEAD `512e739ac2beffe90e7153087509b2734c64e853`。真实 Chrome 已核对最高角色 `24 / 24` 有效权限全选且只读，API/UI 矩阵一致；Django 定向权限回归、前端有效 Vitest、组织页桌面/390px截图已归档。正式员工账号、真实会话、生产 RBAC 数据范围和数据库/服务器管理员边界仍需环境验收；这是生产身份待验风险，不是本轮已确认代码缺陷。后续条件是正式测试账号和隔离 staging；验收标准是普通员工权限不扩大、最高角色 UI/API 一致且不可编辑，应用管理员不获得 DB/OS/服务器权限，并保持 ISS-043 审计保护。

- **ISS-080（P2 / `BUSINESS_VERIFICATION_PENDING`，现有状态保持 FIXED_PENDING_REVIEW）**：来源 `codex/integration-047-097-080`，代码集成 HEAD `512e739ac2beffe90e7153087509b2734c64e853`。同客户全量授权联系人、当前筛选之外/跨分页、邮箱/国际区号电话/近似姓名、编辑排除自身、查看入口和非阻断继续创建均通过自动化与真实 Chrome 桌面/390px证据；真实员工跨客户数据范围和生产业务数据抽查仍未完成。原因是本轮只使用隔离合成库和开发身份，不伪造正式数据结论。后续条件是受限员工账号与脱敏业务样本；验收标准是不同客户隔离、无权联系人不泄露、跨分页结果正确且用户确认后仍可保存，独立代码/权限/视觉复审通过。

- **统一 CI 环境待验（关联 ISS-047/097/080，不新增 Issue）**：本地自动化已通过，但最终推送 HEAD 必须查询 GitHub Actions；若测试步骤前失败，登记为环境待验，不得标记 CI PASS。真实 PostgreSQL、生产代理/卷和正式账号同样不由本地 SQLite 或开发身份替代。

## INTEGRATION-018-036-025 统一集成记录（2026-10-27）

基于统一基线 `7951ecb8c6196f773128ad5978bfcd0a5b30c6b5` 创建独立 `codex/integration-018-036-025` Worktree，按 ISS-018 → ISS-036 → ISS-025 集成来源 HEAD `21812b7c1190540a7214d4b77518ede31221180a`、`80a93559852d9d679c86d71250549261c7c2bbd1`、`1480429338d0fc6de20384ea77a43e969a2b7de4`。三项来源及证据提交均已纳入；公共阶段文档两次冲突均保留双方内容，`serializers.py` 的备份无关状态映射与不可拆分单位校验均保留。集成证据见 [`INTEGRATION-018-036-025`](uat-evidence/integration-018-036-025/README.md)。

本地后端定向 60 项通过、3 项跳过；临时 `MEDIA_ROOT` 下 Django `crm` 全量 984 项通过、18 项跳过；Django check、迁移检查、Node 156 项、有效 Vitest 661 项和前端生产构建通过。默认 Worktree media ACL、前端依赖缺失和未指定 jsdom 的首次失败均已区分记录，不冒充代码回归。ISS-018 仍 `BLOCKED`，ISS-036 冲突快照业务待确认项仍保留，ISS-025 仍 `FIXED_PENDING_REVIEW`；三项生产/员工待验状态不因集成本地通过而关闭。本轮不触发 GitHub CI、不合并 master、不关闭 Issue、不部署，等待统一独立审查。

## ISS-006 并发测试夹具补修（2026-10-31）

更新既有 ISS-006 记录，不新增 Issue。来源：用户本轮要求；代码分支 `codex/r1-iss006-po-locking-bd324-20261030`，测试修复提交 `61d857c213d832101a19ca5ed13a16f9d7832107`。在 `test_same_purchase_order_different_sku_receipts_serialize_status_and_reservations` 与 `test_receipt_and_reversal_race_keeps_purchase_stock_and_reservations_consistent` 中删除重复创建的 `PurchaseCostAllocation`；依据是 `PurchaseOrderItem.save()` 在 `cost_allocation_version=0` 时自动创建默认分配。两个夹具现断言每条采购明细恰有一条 allocation，且归属类型、销售订单及数量正确。没有修改生产代码，也没有改变并发场景。

锁定依赖、一次性内存 SQLite 回归共发现 74 项，61 项通过、13 项 PostgreSQL 专项跳过、0 项失败；收货/冲销、库存流水、库存、预留及成本分配相关可运行回归通过，日志见 [`C 并发锁定验收记录`](uat-evidence/r1-five-fixes-migration-20261030/C-po-locking/README.md)。本机无 PostgreSQL 客户端、服务或 Docker，默认 5432 端口未监听；两个目标并发测试及 PostgreSQL 最终一致性验证仍为 `BLOCKED`，SQLite 结果不构成并发证明。ISS-006 保持 `NEEDS_VERIFICATION`；下一步是在 PostgreSQL 恢复后运行两个精确场景并核对采购单状态、实际库存、收货记录、库存流水与预留，不据本轮本地测试改变 Issue 状态。

## ISS-006 补充：冲销审计事务原子性（2026-10-30）

来源为用户指定的 2026-10-30 ChatGPT 独立代码审查；仅记录该已确认来源日期，不推断更早的首次发现日期。复核固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 时确认两个具体缺口：`ShipmentViewSet.reverse` 在 `reverse_shipment` 服务事务提交后才写审计；`InventoryMovementViewSet.reverse` 在 `reverse_manual_inventory_movement` 提交后再写两条审计，可能留下业务冲销但无审计，或第一条审计提交、第二条失败的部分记录。

在独立分支 `codex/r1-iss006-inventory-reversal-audit-atomicity-20261030` 增加两条 API action 外层事务，仅包住原有冲销和审计调用；未改变冲销规则、权限或响应语义。隔离 SQLite 下 Django system check 通过，相关库存/履约回归 106 项全通过。故障注入覆盖发货冲销审计失败、手工冲销第一条及第二条审计失败，并核对业务记录、库存流水、库存/预留和审计行均回滚；正常路径及重复冲销拒绝保持通过。验收报告与原始日志：[`R1-ISS006 冲销审计原子性`](uat-evidence/r1-iss006-reversal-audit-atomicity-20261030/README.md)。

此子范围记为 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立审查；不新建重复 Issue，不关闭 ISS-006。ISS-006 全局仍为 `NEEDS_VERIFICATION`，因为其他库存异常路径和 PostgreSQL 并发验收尚未完成。后续验收依据：独立复审确认事务边界和故障注入结果，且 ISS-006 其余待核验范围逐项有证据后再按协议变更全局状态。未新增 Issue ID，既有状态统计不变。

## ISS-006 PostgreSQL 并发覆盖补齐（2026-11-01）

R1-ISS006-POSTGRES-CONCURRENCY-GAPS 从 `7402ad38cf40d1eea0adb076e67021c31be8ac1e` 创建独立 worktree/分支 `codex/r1-iss006-postgres-concurrency-gaps-20261101`。新增同笔收货并发冲销、相同请求键并发收货、同 PO/SKU/明细的合法部分收货及超额竞争测试；既有收货/冲销竞争增加 API 审计及状态快照一致性断言。只改测试和验收记录，没有改生产业务或迁移。旧幂等测试供应商代码夹具同步满足两字符模型约束。

本机无 PostgreSQL/Docker 工具或服务，5432 不可连接。语法编译、Django 静态检查、禁止数据库连接的导入/发现及 diff 检查通过；发现 24 项，执行 0 项，没有用 SQLite 替代。真实并发仍 `BLOCKED`。另静态识别基线 0094 的 CSV 审计 TRUNCATE 防护与 TransactionTestCase flush 可能冲突，须在专用 PostgreSQL 测试库确认并处理测试清理方案；本轮未削弱审计保护。详见[验收报告与原始日志](uat-evidence/r1-iss006-postgres-concurrency-gaps-20261101/README.md)。ISS-006 保持 `NEEDS_VERIFICATION`，Issue 集合/状态统计不变；下一步为 PostgreSQL 前置清理验证、五个场景及履约审计交叉回归，再交独立审查。未触发 CI、未合并 master、未部署。

### ISS-006 并发断言独立审查补修（2026-11-02）

R1-ISS006-POSTGRES-CONCURRENCY-REVIEW-FIX-01 从 `657a65c10e0234345a2c648998f6d283c500d1b4` 在原独立分支补齐四处采购明细 `refresh_from_db()`，保留超额竞争原有刷新；加强失败键、库存及审计无残留检查。仅修改测试和验收/开发记录，无业务、模型、迁移或审计保护变更。SQLite 81 项发现、64 通过、17 个 PostgreSQL 专项跳过，0 失败；语法、system check、静态发现及 diff 检查通过。完整日志见[更新验收报告](uat-evidence/r1-iss006-postgres-concurrency-gaps-20261101/README.md)。本次补修待独立复审；ISS-006 仍 `NEEDS_VERIFICATION`，真实 PostgreSQL 执行为 `BLOCKED`。下一步由 `R1-POSTGRES-TEST-ISOLATION-01` 处理测试清理隔离，再做真实 PostgreSQL 复测；未关闭/新增 Issue，集合和状态统计不变，未触发 CI、合并或部署。

### ISS-006 / ISS-052 PostgreSQL 测试隔离候选方案（2026-11-02）

R1-POSTGRES-TEST-ISOLATION-01 从 `2e25b743884123d7ae5599c89586988a12791bf4` 新建独立分支 `codex/r1-postgres-test-isolation-20261102`。仅对 runner 本次确认创建的随机本地 PostgreSQL 临时库，在 TransactionTestCase teardown 内以独占锁和单事务完成指定 TRUNCATE 触发器的临时启停/恢复；正文及普通 flush 保持原保护。建库/销毁使用严格维护连接及创建归属快照，拒绝连接覆盖、来源库回退、已有库覆盖和不支持的别名/镜像/并行组合；失败恢复两份配置，回收失败明确报告。未改业务代码、模型、任何迁移或 ISS-052 保护。

锁定依赖 Django 6.0.9 下相关 SQLite 回归最终 137 项发现、113 通过、24 个 PostgreSQL 专项跳过，0 失败；其中本轮控制流程 21 项通过、6 项真实 PostgreSQL 用例未执行。依赖精确核对、语法、Django check、迁移检查及静态发现通过。报告见[测试隔离验收与完整日志](uat-evidence/r1-postgres-test-isolation-20261102/README.md)。**真实 PostgreSQL 清理冲突尚未验收解决，继续 BLOCKED**；下一步在专用 PostgreSQL 17 环境核实六个生命周期/恢复/独立连接场景、ISS-006 并发及 ISS-052 原始 SQL/迁移回归，再运行完整 PostgreSQL 套件。ISS-006 仍 `NEEDS_VERIFICATION`，ISS-052 既有状态不变；无新增/关闭 Issue，集合与状态统计不变。未触发 CI、创建 PR、合并 master 或部署。

### REVIEW-INTEGRATION-BATCH-01 财务原行留档

以下为更新前原行，仅保留历史，不作为当前状态重复计数。

> | ISS-105 | P1 / OPEN | 2026-10-18 用户本轮财务统计审查；基线f779ed858da3bc4dd468645f5405b0fed2556a8d源码核对，未读取真实业务库 | 2026-10-28 / 当前基线 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`；财务 P3-B 阶段记录提交 `0fb9bb8`。核心人民币事实已有阶段成果，但启用政策、历史 cutover、统计覆盖和银行例外业务闭环未完成；保持 P1 / OPEN。 历史台账结论保留：rmb_amount主路径按原币×汇率生成，概览及CSV却称实际人民币收入；无银行结汇事实，无法区分未结汇与实际到账。0值fallback、历史来源及拆分尾差分支待进一步隔离测试，不推断真实损失 | 财务负责人确认统计口径/费用/历史cutover；产品及后端按独立复审后的最小方案另行实施；本轮仅分析，不修业务代码 本轮仅做状态对账，不扩大为生产/正式员工验收。 | 实际CNY与参考折算分开；A–G真实隔离UI/HTTP/Decimal一致；结汇不二次核销、不重复现金；权限/冲销/历史保护及独立复审通过。详见[R1-FIN-AUDIT-01](R1-FIN-AUDIT-01-财务统计与结汇兼容性审查.md) 本轮后续动作：以本轮报告和精确 SHA 为准，不重复派工。 |

> | ISS-108 | P1 / BLOCKED | 用户R1-FIN-P2-A规则D04/D06；2026-10-19；2026-11-03核对既有原则 | 保留原银行事实/凭证、明确银行实际日期、退款/更正不伪造新回款、不自动释放未知来源额度的原则已确认，不再重复列作业务待决。现有代码对未知退款、直接作废/替代活动来源、覆盖/删除/取消已确认事件及零净额安全拒绝；可凭证化更正的增量流程尚未实施。 | 后端/财务QA在后续授权中按已确认原则设计可追溯反向事实和来源映射；财务提供每笔实际撤回/退款凭证及期间，不由代码猜测。保留现有fail-closed，不因本轮可选手续费改为可取消确认事实。 | 原始记录不改写、银行撤回证据/来源分配与记入期间可核实、不重复核销或自动释放额度；正常/拒绝/原子性/真实PG并发及独立复审通过 |

### REVIEW-INTEGRATION-BATCH-01 早期阶段原文留档

> ## 2026-11-04 REVIEW-INTEGRATION-BATCH-01 复核记录（进行中）

>

> 本轮起点 `4388947d70d26bca66ca0bfc76b2383a2fc0d404` 与远端一致，[CI 41782956426](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41782956426) 三项成功。原始日志已归档至[本包证据](uat-evidence/review-integration-batch-20261104/README.md)。PostgreSQL17后端1182项、1152通过、30跳过；0091–0094、三表UPDATE/DELETE/TRUNCATE和回退保护实际执行。ISS-006/043/052 的历史“PG未执行”仅保留为当时记录，不再作为当前重复派工依据；目标部署角色、完整业务范围及独立复审仍分别保留。

>

> ISS-007 新故障注入确认：批量第二文件存储失败残留一条记录和文件；上传审计失败残留两条记录和文件；删除审计失败已删除记录和文件，三项安全一致性断言均失败。修前日志见本包 `logs/attachment-atomicity-20261104-transactiontest.log`。该问题沿用ISS-007，不重复编号；修复与回归进行中，不标为完成。

>

> ISS-037 仅“打印完整验收与分页改进”子范围由用户明确决定延期、后续自行处理，记为 **BLOCKED（用户延期）**；来源为 `ISSUE FIX A02` 对话的用户消息 `01a1a590-5068-7740-a54f-0b7fc821fefe`。其余主体快照要求不延期，现有有效修复、实际PDF及证据保留，仍等待来源稳定交接。未追加催办指令，未关闭ISS-037。各项当前归一化与关闭缺项将集中记录在本包矩阵中；Codex自查不构成ChatGPT独立复审。

### REVIEW-INTEGRATION-BATCH-01 ISS-002原行留档

> | ISS-002 | NEEDS_VERIFICATION | [R0-E1 npm audit](R0-E1-综合业务回归与内测准备.md)；首次日期：UNKNOWN（未从一手记录确认） | 2026-11-04核对：当前4388947d70d26bca66ca0bfc76b2383a2fc0d404已包含Python图像依赖升级/锁定提交3961ef6c4b0499adb0689f14be73372692ddac3f，requirements.txt/lock固定Pillow13.0.0；基线CI41782956426以Python3.12通过全量，当前本地pip check正常。r1-iss002-security-audit-final-20261101/README.md明确后续Python漏洞库复验仍未完成，不能称当前无漏洞。历史时点记录：2026-10-27 / `codex/audit-iss002-dependency-security` / 精确来源 SHA `4e4ca504ee398da85fe23cc53d534c6008807e5c`：初始 npm 锁树的 2 moderate、9 high 已逐项核对直接/传递关系和源码可达性；本轮保留精确前端依赖与锁文件并未运行自动修复。 | Pillow 11.3.0 仍在实际图片上传/缩略图/Excel 图片路径，风险未解决，修复需跨大版本；Python 依赖仍缺乏完整 lock 方案，生产解析版本、CI/PostgreSQL 和外部暴露路径未验证。此前集成分支的 11 项 advisory 快照作为历史记录保留，不把本地 audit 数量当成安全结论。证据：[ISS-002 依赖安全审计报告](uat-evidence/iss-002-dependency-audit/README.md)。 | 保持NEEDS_VERIFICATION；运维包核对当前锁文件的安全公告/可达性、pip-audit与部署镜像实际pin，复用已有兼容测试，不重复Pillow升级、不运行无差别audit fix。原后续计划（历史）：先保持 NEEDS_VERIFICATION；另开 Pillow 大版本兼容与生产镜像依赖冻结验收；不得跨大版本升级 Pillow、运行 `npm audit fix` 或将本轮标记为安全审计通过。 | 内测开放外部访问前 | advisory、可达性、修复和延期项逐项复审；Pillow 关闭条件、Python 依赖冻结、精确 HEAD 三项 CI/生产依赖验证通过。 |
