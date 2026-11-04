# 本轮实际测试与失败原因

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