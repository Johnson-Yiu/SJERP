# 本轮实际测试与失败原因

## 当前冻结候选 02140bf：最终结果摘要

源码候选：`02140bf46df27ba1abf5b9018507c07aae825769`。以下计数来自该候选对应的结果JSON和封存日志；本报告仍是开发侧证据记录，不是ChatGPT独立复审。

| 检查 | 实际结果 | 证据 |
|---|---|---|
| Backend SQLite / Python 3.12 | PASS，1410项：1338通过、72跳过、0失败 | `backend-full-02140bf-python312-result.json` |
| PostgreSQL 17 | PASS，1410项：1378通过、32跳过、0失败 | `final-pg-02140bf/final-pg-02140bf-result.json`；原始日志`final-pg-02140bf/logs/postgres-final-02140bf-full.log` |
| Node单元测试 | PASS，179通过、0失败 | `final-02140bf-frontend/FAIL-RESULT.json`、`final-02140bf-frontend/logs/npm-test-unit.log` |
| 字体排版测试 | PASS，1通过、0失败 | `final-02140bf-frontend/logs/node-font-typography.log` |
| Vitest | PASS，725通过、0失败（78文件） | `final-02140bf-frontend/FAIL-RESULT.json`、`final-02140bf-frontend/logs/vitest.log` |
| 生产构建 | PASS，退出码0 | `final-02140bf-frontend/logs/npm-build.log`；保留一个压缩后超过500 kB的chunk警告 |
| npm ci | PASS，退出码0 | `final-02140bf-frontend/logs/npm-ci.log`；227个包新增、228个包审计，2项弃用警告、4项moderate审计发现 |
| 适用Playwright全量 | **FAIL**，262通过、1失败、0跳过，9个profiles | `final-02140bf-frontend/FAIL-RESULT.json`、`playwright-suite-summary.json`及封存日志。唯一失败为`quote-editor-isolated`的`download.saveAs: canceled`；其余8个profiles退出码0。原断言保留，未把失败改记为通过。 |
| 打印完整输出与分页 | NOT_RUN_USER_DEFERRED，7个场景 | 用户明确延期；未运行且不计为跳过。 |
| 历史接续真实Google Chrome专项 | PASS，5/5阶段 | `final-02140bf-history-chrome/result.json`；98个本地HTTP请求（90个200、8个201），8张截图，实际下载工作簿存在。独立专项，不并入1410项。 |
| Source invariance专项 | PASS，6/6 | `source-invariance-02140bf-result.json`；独立专项，不并入1410项。 |
| Quote边界补充诊断 | sandbox 1/1 PASS；native 1/1 PASS | `quote-boundary-controls-02140bf-result.json`。两次独立单次诊断不能覆盖全量套件quote失败，也不能证明环境因果。 |
| GitHub CI | NOT_RUN_USER_QUOTA_PAUSED | 本轮按用户要求暂停CI；无新的CI结果。 |

02140bf的Node、字体、Vitest与生产构建结果通过，但Playwright仍有一项失败，故前端全套不标记为PASS。结果JSON记录的7个延期打印场景不是测试跳过。Issue状态为124项：87项FIXED_PENDING_REVIEW、14项NEEDS_VERIFICATION、13项BLOCKED、0项OPEN、10项CLOSED；原86项仍未完成独立复审，ISS-121为新增FPR补充，未关闭。

追加诊断分开计数：quiet-timing诊断01失败，02–04各1/1通过；最后有界中断采集组三次各1/1通过，Chrome156实际临时路径286字符仍成功，未捕获失败当次interruptReason，原因UNKNOWN。它们不并入或改写原全量262/1，不据此关闭ISS-020。诊断01早期发布日志旧字节无法恢复、仅旧指纹保留；原全量失败日志/ZIP完好。运行时另外保留Vue警告：`OrderDetailModal`在Transition内使用非元素根节点；未确认其构成新的业务失败，不把警告当已修复。Node24/npm11与历史CI Node22环境差异仍记录。

## 历史测试记录（保留原始结果；以下不代表02140bf）

本报告区分起点、主审新增修复、后续未交付来源。测试重叠，不将专项通过数累加成更多独立业务场景。Codex及子代理自查不是ChatGPT独立复审。

## 主审财务反例与补修

产品修前代码：8087f2c68b19a302a25e814ec8ce6113d91d4750；补修：90683506f5d9447974302d83c89ba27351d5dfd4。API回归只使用合成数据，经正式服务产生事实，不绕过状态机造正式资金。

| 实际运行 | 通过 | 失败 | 错误 | 跳过 | 结论与原始证据 |
|---|---:|---:|---:|---:|---|
| 初版3个API用例，修前 | 0 | 2 | 1 | 0 | 两项产品反例失败；旧/新混合夹具切换MEDIA_ROOT后旧凭证不可读导致1错误，不能称为第三个产品失败。 |
| 媒体夹具修正后3用例，产品未修 | 0 | 3 | 0 | 0 | 普通和历史混合匹配错误接受已分类对外支出（201而非400）；新增本金匹配后核对仍completed而非needs_review。 |
| 首次修后相关SQLite30项 | 30 | 0 | 0 | 0 | 原3条断言及既有财务/真实性负路径全部保留。 |
| 扩展后相关SQLite32项 | 32 | 0 | 0 | 0 | 5条新API/兼容回归，加既有27项。新增历史匹配重核、余额不变和无匹配旧摘要兼容。 |
| 同SHA真实PG17.11专项 | 12 | 0 | 0 | 0 | 新API5、真实性2、既有真实并发5；10.655秒。此数量不包括随后新增的有序锁专项。 |

本机Python3.14.5 / Windows；正式CI为Python3.12 / Linux，二者分别列出。

- [SQLite完整前后日志及精确测试源码](coordinator-finance-sqlite-logs.zip)，[逐轮计数和摘要](coordinator-finance-sqlite-manifest.json)。
- [PG完整日志](coordinator-finance-postgres-logs.zip)，[实际结果与恢复清单](coordinator-finance-postgres-result.json)。
- PG恢复99表、1081行、128迁移及4文件一致，序列/凭证字节核对，恢复后真实HTTP匿名403、无权403、授权200且SHA一致、公开media直链404；源未变且自有临时集群cleanup complete。
- [代码只读交叉检查](FINANCE-FIX-REVIEW.md)提出有序锁竞争、截止日两侧、既有匹配旧核对保守重核证据缺项；没有把已有5项普通并发当成这些新场景通过。

## 普通角色路由补修与有序锁专项

第三项反例ADV-03由财务候选2e20报告提出；主审只读审查该候选，尚未作为稳定来源合入。主审在906独立角色回归6项中1通过/5失败，授权读者/创建者/更新者/导出者均因未知模块被拒绝。最小修复9af2a32fa81df3aa975424b70a887057e40b6b22仅声明财务模块、可信POST动作映射和既有finance或reports导出契约，原全局财务/流水查看、global scope、停用profile拒绝不变，不启用运行环境正式RBAC。

| 实际运行 | 通过 | 失败 | 跳过 | 证据 |
|---|---:|---:|---:|---|
| 角色修前6项 | 1 | 5 | 0 | finance-role-before.log |
| 角色修后相关SQLite（首次） | 91 | 0 | 0 | 42.077秒 |
| 补导出拒绝边界后同组SQLite | 91 | 0 | 0 | 54.708秒 |
| 干净9af精确检出真实PG17 | 64 | 0 | 0 | 88.782秒；角色6及既有功能权限/财务数据范围 |
| 有序锁测试草稿SQLite | 4 | 0 | 3 | 7项中3项PG专属；不是PG通过 |
| 已提交a840精确PG专项 | 25 | 0 | 0 | 28.854秒；新有序锁/截止日7、原新API5、角色6、既有并发5、真实性2 |

完整证据：[角色SQLite](coordinator-finance-role-sqlite-logs.zip)、[角色PG](coordinator-finance-role-postgres-logs.zip)、[PG64结果](coordinator-finance-role-postgres-result.json)、[PG25日志](coordinator-finance-lock-order-logs.zip)、[PG25结果](coordinator-finance-lock-order-result.json)、[三个真实阻塞PID证据](coordinator-finance-lock-order-pids.json)。两轮均验证99表1081行128迁移4文件及恢复HTTP4/4，源未变且临时集群清理完成。

主树最初PG角色运行因另一个未提交测试文件被clean-backend保护正确拒绝，0项测试执行；随后改用本任务自建干净9af检出，没有放宽保护。子代理曾启动带进程内clean-check例外的有序锁草稿，在提醒后中止且未进入测试，日志保留但不采信任何PG结果；旧906草稿阻塞观察失败也不扩展为当前验收。主审提交完整测试a840后，实际25项运行使用原保护、无allowlist，三个并发均验证独立PG PID、真实阻塞关系、锁前预读及拒绝/审计/余额原子一致。

[角色代码侧审](FINANCE-ROLE-FIX-REVIEW.md)没有确认绕过；非规范export大小写/别名与资金CSV响应的既有一致性边界已挂公共ISS-105，当前契约为小写csv，不当API漏洞或擅自扩格式。

## 精确代码9068350的完整CI

[CI41855319673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41855319673)三项SUCCESS，主审实际读取job日志和artifact head SHA。

| 套件 | 通过 | 失败 | 跳过 | 其他 |
|---|---:|---:|---:|---|
| Backend | 1259 | 0 | 58 | 1317项，365.744秒 |
| PostgreSQL17 | 1287 | 0 | 30 | 1317项，383.263秒 |
| Node | 179 | 0 | 0 | 默认脚本 |
| Node-only字体 | 1 | 0 | 0 | 单列 |
| Vitest | 720 | 0 | 0 | 77文件 |
| Chrome / Playwright | 270 | 0 | 0 | 主245及隔离25 |
| 生产构建 | PASS | — | — | 3.21秒，大chunk告警保留 |

[回执](ci-9068350-receipt.json)、[完整日志](ci-9068350-logs.zip)、[同SHA artifact元数据](ci-906-artifact-metadata.json)。日志只脱敏6个测试凭据字段，原始本机字节及发布摘要分别记录；不发布令牌、不改写失败为成功。

这不是三个待交付来源的最终集成测试，也不表示86项Issue独立复审通过。

## 证据与台账完整性

- 86个FPR集合与原台账完全匹配；原10个CLOSED不变。124唯一ID：FPR86、NEEDS14、BLOCKED13、OPEN1、CLOSED10，ISS-121按已授权待实施校准OPEN。
- 361条代码入口在a840 Git tree及工作树存在；相对引用重新按docs/原上下文定位，不能把最初40条错误“未找到”当丢失证据。两条正则截断片段剔除为非独立文件；两个历史CI jobs重新查询均三项成功，历史HEAD未重新查询。
- 187图逐字节摘要、可解码性和实际尺寸，以及58项操作文件摘要已验证；空态/历史截图/失败CI和最新精确8087财务图明确分组，不冒称906新增截图或独立视觉接受。
- 8份改写前报告逐字节归档，Git源文本及摘要一致。原始业务失败日志、截图与数据库未重写。
- 校验脚本新增目录引用检查首轮失败：把证据目录当成文件读取触发PermissionError；修正为目录仅作导航、文件另验字节后通过。此为证据校验器错误，不是产品数据库或业务失败；前后输出留档。

运行：`python docs/uat-evidence/integration-closeout-02/verify_evidence.py`（需项目Pillow依赖）。当前结果见[ledger-current.json](ledger-current.json)，其PASS仅指证据/台账一致性，不替代产品回归。

## 未提前计入通过的范围

历史实际资金/未结/库存/履约接续、Linux真实内核/受限角色/恢复签名回执，以及财务反例完整来源，只在明确交付稳定SHA后接收并对整合版执行。原生完整打印成品及分页继续按用户决定延期，不追加测试操作。正式鉴权/RBAC、真实资料及生产执行仍分开处理，不宣布上线就绪。


## A840 Backend / PostgreSQL 全量回归（本地、最终整合前）

A840 全量结果按 `a8400fb8deb1bfeaaf99e0498d8b4aa34ef48f3f` 归档。Backend日志内存SQLite测试库、PostgreSQL为17.11。环境是 **Python 3.14.5 / Windows 10**，不是CI的Python 3.12/Linux；本轮是最终整合前的本机回归，不能替代完整来源合入后的最终SHA CI。

| 套件 | 实际通过 | 失败 | 错误 | 跳过 | 用时 | 结果 |
|---|---:|---:|---:|---:|---:|---|
| Backend | 1266 | 0 | 0 | 64 | 1253.084秒 | `Ran 1330`，`OK (skipped=64)` |
| PostgreSQL 17.11 | 1300 | 0 | 0 | 30 | 1496.750秒 | `Ran 1330`，`OK (skipped=30)`，`POSTGRES_REGRESSION_EXIT=0` |

原始日志及SHA见[`full-a840-result.json`](full-a840-result.json)。Backend摘要在第2795–2797行；其后55行是P2A数据库/迁移核验与CORE_HTTP响应记录，最终请求`/api/transactions/2/void/`为200，没有后续失败标记。PostgreSQL摘要在第2903–2905行，尾部还记录合成备份SHA、历史/财务恢复PASS和`cleanup: complete`。

跳过原因：Backend 64项中，60项要求PostgreSQL专属数据库/锁语义、PG17工具或owned drill环境，4项受Windows POSIX权限或symlink能力限制。PG套件30项中，21项只适用于SQLite文件备份测试，8项要求本地PG17二进制，1项受Windows symlink能力限制。精确理由和示例测试在JSON `skip_reasons` 中；跳过未计入通过。

A840 PostgreSQL运行开头包含合成历史seed 5表/21行、财务seed 13表/22行。辅助目录中的封闭备份、manifest、恢复结果和私有HTTP结果已复制到[`full-pg-a840/`](full-pg-a840/)；源/目标SHA逐文件一致。两份A840原始全量日志打包在[`full-a840-original-logs.zip`](full-pg-a840/logs/full-a840-original-logs.zip)，扫描没有发现显式临时凭据，未做脱敏。

### d4e858675b90 后续财务来源关闭证据

以下是财务来源合入后的独立补充，不并入A840的1330项统计：`finance-original-repros-after.log`为SQLite 3/3通过、0.524秒；`finance-delivered-pg-with-bin.log`为PostgreSQL 17.11 30/30通过、0跳过、70.872秒。其归档/恢复尾记录核实99表、1081行、128迁移、4个媒体文件且cleanup complete。相应备份/恢复工件与三份日志已复制到[`full-pg-a840/finance-source-d4e858/`](full-pg-a840/finance-source-d4e858/)。

首次启动拒绝日志`finance-delivered-pg.log`收录在[关闭日志包](full-pg-a840/finance-source-d4e858/logs/finance-source-d4e858-logs.zip)中：调用缺少必需`--postgres-bin`，CLI拒绝启动，0项测试；原日志与后续30/30成功日志分开，不计为测试失败或通过，日志未记录进程退出码。所有原始日志均无显式临时凭据命中，未脱敏。

主审执行位置补充：两份A840全量都在独立冻结的`.tmp/role-pg-clean-9af` detached A840检出执行，期间没有切换该检出；证据维护时主树已移动至D4，不影响A840运行。PG备份manifest另外绑定A840。首次D4漏参数启动的外层exec工具实际退出码为2（原日志本身没有该字段），0项测试开始；后续带参数运行退出0。
## f928当前阶段前端与附件回归（不是最终历史集成版）

Node24.16.0/npm11.13.0、Windows，npm ci成功（227安装/228审计，保留4 moderate与lucide弃用告警）；Node179/179、字体1/1、Vitest78文件721/721（167.11秒），全部0失败/跳过；构建2.25秒通过，大chunk告警保留。不宣称Node22/Linux CI通过。见frontend-f928-result.json和frontend-f928-full-logs.zip。

**历史错误判定原文（已废弃，后文勘误为准）：** 真实Google Chrome156必须显式PLAYWRIGHT_CHANNEL=chrome：f928原三场景与新增附件可见性断言3/3通过（19.5秒），10张实际截图及HTTP字节结果保留。之前两轮78b为默认Chromium，分别3/3通过23.9/21.4秒，不能称Google Chrome；首次路径表达式错误还导致默认Python及临时证据随正常清理删除。错误与成功范围明确区分，未追改日志。附件修前确定性Vue0/1失败、修后相关27/27和Node9/9日志共同封闭在attachment-regression-logs.zip，仅12处关闭的隔离令牌脱敏，原/发布摘要另列attachment-regression-result.json。

用户于2026-11-05明确CI额度不足，当前后续提交使用[skip ci]，不再触发/等待/重跑Actions。最终CI记额度暂停，不记PASS；所有本地适用验证和独立复审门槛保留。

## 最终集成447d实测（2026-11-05；CI额度暂停）

产品代码447d7816ead2e971e249cb2e762b1a6f7009b9c0；后续e768仅浏览器测试/遥测，应用树一致。Python3.12.16/UTF8，Windows，一次性合成数据库，不连接真实业务库。

| 套件 | 实际通过 | 失败/错误 | 跳过 | 证据 |
|---|---:|---:|---:|---|
| SQLite全量1410 | 1330 | 0 | 80 | backend-full-447d-python312-result.json；900.061秒 |
| PostgreSQL17.11全量1410 | 1378 | 0 | 32 | postgres-final-447d-opseed-receipt-relation.log；1309.665秒 |
| Node / 字体 / Vitest | 179 / 1 / 725 | 0 | 0 | final-447d-frontend/FINAL-FRONTEND-447D.json |
| 适用Playwright | 261 | 2 | 0 | 同上；原9 profiles，未弱化断言，两项saveAs canceled正调查 |
| e768实际Google Chrome附件三场景 | 3 | 0 | 0 | attachment-google-chrome-e768-result.json；23.7秒 |

PG恢复102表1218行133迁移5私有文件（254字节），历史归档、财务及实际接续验证均PASS；源媒体未变，cleanup complete。三张新历史表实际填充后恢复与不可变性另见封存最终PG工件，不能由全量退出码推断未执行专项。

延期打印整份spec静态声明7项，NOT_RUN_USER_DEFERRED，不混为已通过或测试skip。前端实际Node24.16/npm11.13与CI Node22不同，4项moderate开发依赖、glob/lucide弃用及主chunk>500kB警告保留，构建成功。

上节f928“外层PLAYWRIGHT_CHANNEL=chrome即实际Chrome”的判断已纠正：原runner覆盖外层变量，f928及78b均默认Chromium，原3/3结果、日志、图像字节不变。e768文件级chrome配置、支持的CDP版本和pw:browser同进程Google exe记录才证明本轮实际Google Chrome。f3e首次随机Vite1719触发Node fetch bad-port（0测试），第二次不支持Browser.getBrowserCommandLine导致1失败2未运行；均保留，修正仅测试遥测，不改产品或保护。

SQLite第一次从仓库根运行发现0测试，虽然退出0但不计PASS；正确backend cwd全量结果才是1410项。PG前两次辅助seed因缺客户contacts、receipt关系字段查询错误失败，0测试并清理完成；修正仅验收辅助脚本后第三次从全新集群完整运行。上述准备失败保留，不作为产品回归通过。

恢复后不可变性实证：三张实际非空历史表各UPDATE/DELETE/TRUNCATE，共9/9次被原历史guard拒绝，SQLSTATE均55000；逐次SAVEPOINT回滚，完整数据库状态/序列比较未变。证据为final-pg-447d中的history-operational-restored-447d7816ead2.json，不并入1410单元测试数量，不声称已验证生产受限角色。

最终447d备份命令补充专项：8/8通过、0失败/错误/跳过，326.359秒，Python3.12/真实PG17.11。原始校验和、损坏归档、缺媒体、版本、工具失败、错误环境、production-stage拒绝及正常恢复断言均保留；各任务目录清理完成。原全量32跳过不改写，这8项单独列出。首轮沙箱1通过7失败（pg_ctl restricted token87，尚未seed，source_unchanged=null），获工具审批在沙箱外按原断言复跑通过；两个原始日志及逐case结果封存于final-backup-command-447d-result.json和ZIP。

证据索引工具补充：扩展最终日志ZIP哈希核验时，首轮因SQLite manifest使用sha256而另一manifest使用published_sha256导致KeyError，尚未完成整体验证；按实际两种字段读取后重新核验通过，未改变日志/哈希或产品断言。首轮输出只在工具调用记录，独立原始日志文件路径UNKNOWN，不伪造原始文件。最终verify_evidence仅证明字节/台账一致，不计作产品测试通过。
