# INTEGRATION-CLOSEOUT-02 当前状态

统一分支：`codex/r1-prelaunch-consolidation-20261104`。固定起点`8087f2c68b19a302a25e814ec8ce6113d91d4750`，其CI41839476121三项成功已由用户转述ChatGPT实际核实；本轮定向审查不等于86项待复审全部接受。

当前冻结候选 **02140bf46df27ba1abf5b9018507c07aae825769**：在完整集成447d之上最小修复报价/财务浏览器下载生命周期。原测试不改，定向财务2/2、报价1/1，另真实Google Chrome报价1/1及实际XLSX解析通过。同一SHA SQLite1410项1338通过72跳过、PG1410项1378通过32跳过，均0失败；历史Chrome5阶段与实时/副本只读核验通过。但适用前端9profiles为262通过1失败0跳过：报价仍saveAs canceled，不能称下载缺陷已彻底修复；继续调查。

上一完整集成锚点 **447d7816ead2e971e249cb2e762b1a6f7009b9c0** 的1410项SQLite/PG结果与两项浏览器下载失败均保留。e768仅测试遥测、应用树与447d相同；02140随后实际改变两处前端源码，不能再将02140整体应用树称与447d相同。原财务、Linux、历史完整稳定来源全部保留。

用户2026-11-05明确GitHub额度不足：后续提交使用`[skip ci]`，不再触发、等待或重跑Actions，不修改workflow配置来停用。**CI：额度暂停/未执行，不记PASS。** 本地全量、专项、实际文件及真实Chrome继续；不能本机执行的真实Linux/目标环境范围单独保留。

发布完整性补记：使用Windows扩展路径恢复原17项及错误上下文共18项新证据，并核实447d原5项误报缺失；[恢复审计](RECOVERY-AUDIT-EXTENDED-PATH-20261105.json)和两份frontend `PUBLISHED-EVIDENCE-MANIFEST-v2.json`保留v1原件，不改原套件失败。已核对692个相关Git暂存blob哈希。诊断04误将独立输出写入冻结证据根目录，现按[隔离补记](DIAGNOSTIC-ISOLATION-ADDENDUM.json)单列并确认不在原326项来源对账中；不混入全量262/1。诊断01的一份早期发布日志字节曾被脱敏覆盖，原字节不可恢复，仅旧指纹保留；此限制见独立诊断报告，原全量失败日志及ZIP未受影响。

源码与交付提交区分：本页测试实际运行于02140候选；[应用对象回执](DELIVERY-SOURCE-IDENTITY.json)记录backend/frontend/templates/workflow对象。后续证据/台账提交不冒称重新执行应用测试；最终推送提交SHA在交付回复和远端分支中核实。

旧本地操作证据发布补齐：12份曾被ignore排除的文件现有[公开ZIP及逐项对账](legacy-local-business-evidence-publication.json)，9份原XLSX/CSV逐字节、3份公开SQLite仅移除Django session而其他表逐行不变；原始文件保留本地未修改，原索引快照和原SHA仍存。最后一组[报价中断采集](quote-download-interrupt-capture-02140bf/INTERRUPT-CAPTURE-REPORT.md)3/3通过，但没有失败当次中断原因，仍不能消除原262/1的失败，不改安全策略或降低原断言。

## 当前状态表

| 范围 | 状态 | 已完成 / 仍缺 |
|---|---|---|
| 当前报告、台账、历史保留 | PASS（文档一致性） | 124唯一ID，87 FPR、14 NEEDS、13 BLOCKED、0 OPEN、10 CLOSED；原86队列保持，ISS-121凭完整实现与隔离证据单独增加待复审1项；未自行关闭Issue。 |
| 集中复审包 | 待独立复审 | 原86项按R1 35/R2 43/R3 8及12模块整理，365条代码入口在02140树存在；ISS-121单独补充。不以存在或CI成功替代逐项接受。 |
| 财务反例与普通角色补修 | 已修复，待独立复审 | 原三反例默认发现；SQLite3/3、完整财务PG30/30；旧错误匹配存量未扫描或自动改写。 |
| Linux完整来源 | 已合入，补修后专项待验 | 来源真实Linux三专项已成功；新增正式CLI回执跨UID交接补修0037b8c，本机27通过/2 POSIX跳过，真实Linux补修路径未执行。 |
| 附件保存后重开 | 已修复，待独立复审 | 确定性修前0/1失败，修后相关Vue27/27；实际Chrome156原三场景3/3及可见附件截图完成。 |
| 历史实际接续 | FIXED_PENDING_REVIEW | 稳定ba427474完整合入447d；02140 PG全量、实际非空历史表恢复/拒绝保护、真实Chrome五阶段接续及live/发布副本核验通过；ISS-121单独补充复审，不是独立接受或上线批准。 |
| 视觉 | 开发侧证据已补，独立待验 | 215份既有/定向图及62操作文件，另151份447d实际页面补充索引；逐图源码/尺寸/数据/边界明确，失败场景不冒充正向完成，历史通道标签另有勘误。 |
| 447d阶段后端全量/备份 | PASS（本地隔离） | 447d SQLite1410项1330通过/80跳过/0失败；PG1410项1378通过/32跳过/0失败，102表1218行133迁移5文件恢复一致，历史/财务/实际接续恢复PASS，源未变、cleanup complete。 |
| 最终02140候选 | FIX REQUIRED | 后端全量及历史Chrome通过；适用Playwright262通过/1报价下载失败/0跳过。9profiles实际结果不覆盖为通过，原print7延期，继续修复报价。 |
| 打印完整成品与分页 | 用户明确延期 | 不追加尝试或催办，既有源断言不删除，不扩大到其他业务。 |

## 完整来源与代码修复

| 来源/修复 | 精确SHA | 接收/验收边界 |
|---|---|---|
| 本轮固定起点 | 8087f2c68b19a302a25e814ec8ce6113d91d4750 | 已验基线；原五来源及迁移汇合成果保留。 |
| 历史实际接续完整来源 | ba4274742727a6794608dc8581a49b3692d865a6 | 完整合入447d7816；从远端重读核实，不取移动HEAD或最后单补丁。 |
| 财务反例完整来源 | e301a86044ffe56b72172a94dc3b00ae09401b05 | 完整合入087fe34d；来源CI41862778457三成功，来源失败证据不改。 |
| Linux运维完整来源 | 4a4f338b09e9a464f1e66c24a905c35c970729bf | 完整合入536789f6；来源CI41866028447、Linux41866028480各三成功，不是集成补修通过。 |
| 有效分类匹配/核对指纹 | 90683506f5d9447974302d83c89ba27351d5dfd4 | 新/旧本金匹配锁内重验、核对失效，金额/日期/原事实不改；ISS-105。 |
| 普通财务角色路由/动作 | 9af2a32fa81df3aa975424b70a887057e40b6b22 | 只读preview、create/update隔离、原finance或reports导出契约；未启用正式RBAC。 |
| 有序锁/截止日/旧摘要测试 | a8400fb8deb1bfeaaf99e0498d8b4aa34ef48f3f | 原保护检查下PG25/25，三个真实独立阻塞PID；旧失败草稿另列。 |
| 原三财务反例默认发现 | d4e858675b907fe881186d4e45c6676df8c003cb | 原defect_repros.py不改，三断言进入默认测试。 |
| 受控回执只读属组 | 0037b8c5899554819943944a9cf9e4ea952d2bae | 默认0600、显式现存POSIX组0640，权限/发布失败不签发正式文件；ISS-018。 |
| 跟进摘要重开取完整详情 | 78b1eb0cbf05bec5865d98803fb9cebf62cb0202 | 避免把摘要缺失字段/附件作为空表单；ISS-007。 |
| 浏览器实际下载生命周期 | 02140bf46df27ba1abf5b9018507c07aae825769 | 仅报价anchor/Blob URL延后清理、财务CSV附DOM后清理；原断言保留，ISS-020/105。全量262通过/1报价失败，财务CSV两视口通过；不称报价已彻底解决。 |
| 附件可见性强断言与视口截图 | f92824b814012783a8c992bf50f95f2e4e1ceae9 | 原三场景不删不弱化；新增实际附件区桌面/窄屏截图。 |

来源完整链、文件审查及范围见[来源回执](stable-source-ci-receipt.json)、[财务审查](REVIEW-FINANCE-ADVERSARIAL-SOURCE.md)、[Linux审查](REVIEW-LINUX-STABLE-SOURCE.md)、[历史候选预审](REVIEW-HISTORY-CANDIDATE.md)。候选预审为历史时点；最终接收后的[447d集成来源审查](INTEGRATED-SOURCE-REVIEW-447D.md)与[source-equivalence](source-equivalence-447d.json)另列，候选不是接收凭据。

## 实际本地结果（各自源码，不混计）

| 源码 / 套件 | 通过 | 失败/错误 | 跳过 | 证据 |
|---|---:|---:|---:|---|
| 447d冻结检出 SQLite全量1410 | 1330 | 0 | 80 | backend-full-447d-python312-result.json；900.061秒，独立Python3.12/UTF8 |
| 447d冻结检出 PG17.11全量1410 | 1378 | 0 | 32 | [final-pg-447d结果](final-pg-447d/final-pg-447d-result.json)及原日志ZIP；1309.665秒，102表1218行133迁移5文件恢复一致 |
| 447d Node / 字体 / Vitest | 179 / 1 / 725 | 0 | 0 | final-447d-frontend/FINAL-FRONTEND-447D.json；构建成功，725项属78文件 |
| 447d 适用Playwright | 261 | 2 | 0 | 同上；两项导出saveAs canceled调查中，延期打印spec7项未运行另列 |
| a840冻结检出 SQLite全量1330 | 1266 | 0 | 64 | full-a840-result.json；1253.084秒 |
| a840冻结检出 PG17.11全量1330 | 1300 | 0 | 30 | 同上；1496.750秒，99表1081行128迁移4文件恢复一致，cleanup complete |
| d4完整财务来源+原三断言 PG专项 | 30 | 0 | 0 | full-pg-a840/finance-source-d4e858；70.872秒，含七组并发及真实HTTP |
| 0037回执/签名/保留/信任根 | 27 | 0 | 2 | receipt-handoff-python312-result.json；7.123秒，Windows/Python3.12，不替代Linux跨UID |
| f928 Node | 179 | 0 | 0 | frontend-f928-result.json |
| f928 字体 | 1 | 0 | 0 | 同上 |
| f928 Vitest（78文件） | 721 | 0 | 0 | 同上；167.11秒 |
| e768 Google Chrome156（应用代码与447d一致） | 3 | 0 | 0 | attachment-google-chrome-e768-result.json；23.7秒，CDP版本及同进程实际Google exe启动记录，进程/端口/数据清理完成 |

f928 `npm ci`成功、生产构建2.25秒通过。Node24.16.0/npm11.13.0不是Node22 CI镜像；保留4项moderate开发依赖、lucide弃用及大chunk警告。a840运行于Windows/Python3.14.5，不能称Python3.12/Linux全量。独立Python3.12锁定依赖安装、pip check、system check和迁移差异检查已通过，最终历史整合后另验。

所有失败、修前/修后和环境限制见[TEST-RESULTS](TEST-RESULTS.md)。原有序锁草稿五轮各4通过/3失败，带未提交测试例外，绝不当作原guard通过；[原日志与来源说明](LOCK-DRAFT-PROVENANCE.md)保留。首次缺PG参数退出2/0测试、未定位OpenSSL的环境错误及浏览器路径/默认Chromium标签更正也明确记录。

## 视觉与复审入口

[REVIEW-BACKLOG](REVIEW-BACKLOG.md)及[机器清单](review-backlog.json)逐项列原86项入口、最新证据和具体关闭缺项。ISS-007、ISS-018及ISS-121的新增发现按原ID在公共台账登记，不仅留在专属缺陷报告。

[VISUAL-EVIDENCE](VISUAL-EVIDENCE.md)及[机器索引](visual-evidence.json)逐图记录实际尺寸、操作、合成数据、源码SHA与覆盖边界。空态、旧失败CI、未知来源、默认Chromium与实际Chrome分开；没有把旧图改成新集成图。真实Chrome的[桌面附件区](attachment-google-chrome-e768/browser/iss007-attachment-real.spec/screenshots/follow-up-saved-attachment-desktop-viewport.png)和[390视口](attachment-google-chrome-e768/browser/iss007-attachment-real.spec/screenshots/follow-up-saved-attachment-390-viewport.png)已开发侧目视确认，仍待ChatGPT独立接受。

本轮447d另外保留[151张实际页面补充索引](integrated-page-evidence-447d.json)，逐张实际尺寸、原图SHA、场景及源码；排除fixture媒体、终止尝试、失败截屏和延期完整打印。它不把混合通道统一称Google Chrome，不把261/2的套件结果写成全通过。

## 剩余门槛

- 历史完整稳定SHA已接收；集成迁移、隔离PG全量、新表非空恢复/不可变性、Chrome接续、独立源状态复核已有上述运行证据，交ChatGPT逐项复审正式财务契约、源编号/幂等、组原子性、权限审计和未覆盖边界。来源结果不替代本轮结果，隔离验收不代表真实启用批准。
- 回执跨UID真实Linux补修验收未执行；本机没有已验证可用的Linux执行环境，GitHub CI按用户最新决定暂停。不得用Windows模拟计作通过。
- 正式认证/员工身份/RBAC、真实启用资料、生产配置、真实迁移执行、目标服务器HTTPS/角色/媒体权限、独立故障域副本/密钥、外部告警及RPO/RTO仍分别待验/需单独授权。历史代码未完成不能归因缺真实凭证。
- 既有错误本金匹配的目标存量未扫描或自动改写；合法旧摘要兼容与新入口拒绝不等于历史错误自动修复。
- 打印完整成品及分页按用户决定延期。未合master、未部署、未导入真实资料、未启用正式RBAC、未关闭Issue、未宣布上线就绪。

## 历史与原始证据

[8份8087原报告历史清单](history-manifest.json)保持逐字节；[改写前阶段首页/状态快照](checkpoint-history/manifest.json)保留本轮各阶段旧描述及原始摘要。旧运行中/未提交描述只作历史，不覆盖当前表。原始失败日志、截图、实际文件与数据库不追改。最后统一分支成功CI为906/41855319673；0037 CI41880236996及Linux41880236963的零步骤账单失败另列[记录](github-billing-blocker.json)，不视为测试通过。用户暂停后不再等待这些运行。

### 浏览器标签勘误

78b两轮和f928一轮均实际使用默认Chromium，外层PLAYWRIGHT_CHANNEL被原隔离runner覆盖。目录旧命名不证明Google Chrome，位图/通过数量不改，元数据已纠正并保留旧标签。f3e首次随机Vite1719被本机Node fetch拒绝（自有探针0请求、bad port），第二次新增命令行遥测因缺enable-automation未运行业务；均保留失败和清理记录。e768改为文件级test.use chrome，使用支持的版本遥测与pw:browser启动日志，在原隔离保护和安全独占端口下3/3通过。旧CI截图标签另按精确producer配置审计，不能因CI装有Chrome就认定每张都是Chrome。

恢复后不可变性实证：三张实际非空历史表各UPDATE/DELETE/TRUNCATE，共9/9次被原历史guard拒绝，SQLSTATE均55000；逐次SAVEPOINT回滚，完整数据库状态/序列比较未变。证据为final-pg-447d中的history-operational-restored-447d7816ead2.json，不并入1410单元测试数量，不声称已验证生产受限角色。

最终447d备份命令补充专项：8/8通过、0失败/错误/跳过，326.359秒，Python3.12/真实PG17.11。原始校验和、损坏归档、缺媒体、版本、工具失败、错误环境、production-stage拒绝及正常恢复断言均保留；各任务目录清理完成。原全量32跳过不改写，这8项单独列出。首轮沙箱1通过7失败（pg_ctl restricted token87，尚未seed，source_unchanged=null），获工具审批在沙箱外按原断言复跑通过；两个原始日志及逐case结果封存于final-backup-command-447d-result.json和ZIP。
