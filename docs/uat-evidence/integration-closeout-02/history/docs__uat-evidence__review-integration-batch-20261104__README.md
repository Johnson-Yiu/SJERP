# REVIEW-INTEGRATION-BATCH-01 综合验收

当前状态：**NEEDS VERIFICATION（本地验收完成，前端测试补修待最终CI）**。这是可复核的集成证据包，不是ChatGPT独立复审或上线授权。

集成分支：`codex/r1-prelaunch-consolidation-20261104`。后端全量已验代码及前一候选SHA：`1f189c3f74fda2908620dd3860230d860f1cbb43`。前一候选CI：[41829100528](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41829100528)。本地全量SQLite与真实PG17及备份恢复已完成；该候选Backend/PostgreSQL成功、Frontend因ISS039快照子进程两项失败；已补修有界输出缓冲和诊断，本地Chrome2/2及Node179/179。最终交付SHA以本报告对应Git提交和交付回执为准；最终三CI结束后，精确SHA回执保存在本机logs/FINAL-DELIVERY.json，并在交付消息给出GitHub同SHA运行链接。最后仅文档/证据提交须在交付时再次核实其精确SHA三项CI。

## 完整来源与集成

| 来源 | 固定完整SHA | 已核实来源CI |
|---|---|---|
| 起点 | 4388947d70d26bca66ca0bfc76b2383a2fc0d404 | 41782956426 |
| 打印封存 | b3d0d386de70d9efd77bf62cdbd87877fbccbfb8 | 41802910019 |
| 核心工作区 | e302199f7890c686a309f54aebe8cc31b6202f52 | 41808354916 |
| 财务 | 3a07e7ef1a9e63c98077d45492ba23b798c7fcdd | 41815451746 |
| 运维 | d289de36a3da3e4bd6531c812ec21a05f046d570 | 41814619508 |
| 历史承接 | a0729a0965850028fe52f5b6fcc3e825f23b1289 | 41822826770 |

各来源远端及同SHA三CI已重新核实；六个完整SHA均为本轮集成祖先，见[source-receipts.json](source-receipts.json)。没有只取末次补修或合并移动HEAD。来源CI不替代集成CI。文件冲突与完整处理见[MERGE-RECORD.md](MERGE-RECORD.md)：AGENTS保留取消数量上限的新约定，导航保留账户资金与历史入口，审计回退保留全部数据/迁移恢复断言；新增无数据操作的0103汇合迁移，不删除历史迁移。

## 本包确定缺陷与补修

- 附件：修前第二文件/上传审计/删除审计三项失败一致性已复现。ce74f8b、0914002、a866c29修复事务及存储补偿、改名恢复、提交结果探测、锁释放、私有恢复目录链接边界与原文件名下载；PG专项42/42。灾难性二次存储失败保留私有恢复副本与critical日志，不声称所有存储故障均可自动恢复。
- 浏览器：过期资金草稿断言曾早于Vue挂载，保留全部缓存与敏感字段断言，只等待现有控件就绪；专项8/8。多个脚本原把新输出写入历史目录，先保存当轮原始字节后恢复历史证据并隔离输出路径。
- 文案/布局：操作日志提示区分身份和环境，修复逐字换行；长姓名侧栏省略显示且title保留全名。真实Chrome桌面/窄屏及内置浏览器证据已保存，没有改权限或财务语义。
- 回退/备份：319941c增强0102反向守卫，避免非空银行来源因scope不一致被删除；补齐新FinanceVoucher路径/大小/SHA与媒体清单比对。修前迁移9项1失败，修后SQLite9/9、PG新专项13/13。
- 加密归档：1f189c3使密文完成解密复核后才以不覆盖硬链接发布正式名。修前4项1通过/3失败，修后6/6；真实GPG2/2验证往返和损坏拒绝，源归档不变且清理完成。

## 实际回归结果

完整逐轮通过/失败/跳过及错误原因见[TEST-RESULTS.md](TEST-RESULTS.md)，不会把早期失败抹去或把来源通过算作集成通过。

| 实际执行版本/范围 | 结果 | 证据 |
|---|---|---|
| c1937da财务合入全量后端 | 1249项：1189通过、60跳过、0失败 | logs/backend-full-c1937da.log |
| 673ae37全部来源Vitest | 77文件720通过、0失败/跳过 | logs/vitest-all-sources-673ae37.log |
| 673ae37字体规范/构建 | 1/1；构建成功2.28秒 | logs/typography-all-sources-673ae37.log、build-all-sources-673ae37.log |
| 财务/运维/侧栏Node | 177通过、0失败/取消/跳过 | logs/node-finance-ops-sidebar.log |
| 核心真实HTTP | 3/3，SQLite及PG专项通过 | CORE-HTTP.md、完整数据库及XLSX/CSV |
| 财务Chrome | 认证审批/过账/私有凭证2/2，开发资金页面2/2 | finance-browser-integrated/、finance-browser-anonymous/ |
| 历史—财务显式契约 | SQLite1/1；待PG全量 | REVIEW-HISTORY-FINANCE-CONTRACT.md |
| 财务PG17迁移/恢复 | 13/13；94表1027行4文件恢复一致，10新财务表有数据，序列/文件字节一致 | artifacts/postgres-backups/finance-restored-319941c05e46.json |
| 运维扩展单元 | 63项：59通过、4平台跳过、0失败 | logs/operations-source-targeted-post-fix.log |
| 真实GPG发布 | 2通过、0失败 | logs/real-gpg-publication-1f189c3.log |
| 冻结1f189c3全量SQLite | 1312项：1251通过、61跳过、0失败，816.678秒 | logs/backend-full-all-sources-1f189c3.log |
| 冻结1f189c3全量PG17+恢复HTTP | 1312项：1282通过、30跳过、0失败，1008.032秒；恢复HTTP4/4 | logs/postgres-full-all-sources-1f189c3.log |
| 候选1f189c3三项CI | Backend/PG成功，Frontend失败（270项中268通过/2失败） | 41829100528及失败归档 |

npm ci已在本包独占缓存完成；首次自有Vite占用binding导致EPERM及此前Node取消日志均保留。此后依赖锁文件与已验来源一致，没有audit fix或依赖替换。本机Python3.14.5、Node24.16.0；项目CI使用Python3.12与Node22，环境区别明确记录，不能互相冒充。

## 核心闭环、文件和视觉证据

真实HTTP合成流程覆盖报价→保存版本导出→销售确认→应收，以及采购→收货→发货→部分履约→反向/取消→应付追踪；重复请求及审计失败原子性、匿名/CSRF/受限角色拒绝分别核对。实际XLSX/CSV和三份完整SQLite文件在`artifacts/http-with-database-snapshots/`，完整性均ok。合成Django session不等于ERP业务登录或正式员工认证。

财务Chrome保存实际PDF/CSV、双人审批和核对重开截图。参考折算不冒称银行资金，待核实/模拟不经支持入口记账，批准不等于实际扣款，核实内部本金与独立手续费分开；内部ORM可构造非法事实的持久层边界仍见财务预审，不扩大正常入口测试结论。

历史Chrome第一次完成新申请审核/执行，但外部Google Fonts在沙箱ERR_NETWORK_ACCESS_DENIED使整轮FAIL；确切请求见history-network-diagnostic.json。沙箱外用原脚本重开同已执行申请通过，1440/390无溢出，未冒称第二次新审核。`artifacts/history-integrated-synthetic-database.zip`保存12条来源、3个not_connected、0正式财务/库存/履约写入，已应用0103；实际10工作表XLSX与截图保留。显式历史—财务测试通过官方服务验证账户、凭证、CNY实际金额/日期、唯一来源和幂等，不将历史执行器自动接通或猜汇率折算。

实际Chrome156的13页×桌面/390共26张截图在`screenshots/integrated-pages-manifest.json`，0 pageerror；空页只证明空状态/布局，不证明正向业务操作。原生打印完整成品/分页由用户明确延期，未追加催办。历史截图只保存在明确historical压缩包，未复用冒充本轮。

## Issue、复审与剩余门槛

124个唯一ID：FIXED_PENDING_REVIEW86、NEEDS_VERIFICATION14、BLOCKED14、CLOSED10、OPEN0；ISS105/108已校准为已有修复待独立复审，原行保留为引用历史。已关闭10个ID与起点相同，未自行关闭任何GitHub Issue。逐ID关闭缺项见[ISSUE-MATRIX.md](ISSUE-MATRIX.md)，集中复审入口见[REVIEW-PACK.md](REVIEW-PACK.md)。Codex和子代理的交叉审查均不称ChatGPT独立复审。

- **NEEDS VERIFICATION**：精确SHA三CI及独立复审；正式业务登录/全站鉴权、真实员工角色与审计、内部ORM真实性持久约束边界、目标DB运行角色及存储权限。
- **BLOCKED（目标环境/外部资料）**：Linux真实全写入者媒体栅栏、目标HTTPS代理与私有附件、异地副本/独立密钥/告警/RPO/RTO；真实启用日期、账户、余额及每笔凭证。没有连接目标/生产环境。
- **BLOCKED（未授权正式执行）**：真实历史导入、正式资金/库存/履约handoff与实际资料迁移；保留not_connected，不能仅改名宣称接通。
- **BLOCKED（用户明确延期）**：完整打印成品与分页；不扩大为ISS037主体快照延期。
- 警告：生产构建大chunk；npm4项moderate开发依赖（无high/critical）；既有Vue Transition警告及外部字体依赖继续记录。来源依赖审计只在锁文件字节一致的范围复用，不冒充目标镜像审计。

## 日志与原始记录

`raw-logs-phase-01.zip`及manifest保存闭合日志，失败运行保留；仍写入的日志明确排除。CI临时密钥字段仅发布标明脱敏的副本，并同时记录原始与发布摘要。源打印/核心/历史日志原始Git字节另存各source-raw压缩包，原路径是明确的去尾空白阅读副本。实际下载/PDF/数据库/截图使用字节保留属性。

早期工作报告完整字节保存在`stage-report-history.zip`。一次未等待Git合并进程完全结束便开始后续操作造成证据工作文件暂缺，已从保留index恢复385文件；没有丢弃工作或覆盖用户旧工作树。最终交付前继续核对清单和差异。

未合并master、未部署、未启用正式RBAC、未导入真实历史、未创建PR、未自行宣布上线就绪。

## 全来源恢复验收实绩

冻结1f189c3的PG17.11一次性集群实测99张表、1081行、128条迁移记录与4个媒体文件恢复一致；历史5表、财务10表均已通过官方流程填充合成记录。所有序列状态及私有凭证元数据/实际文件摘要一致，媒体引用4条核对一致。恢复后真实HTTP：匿名403、受限合成账号403、授权合成账号200且字节一致/private no-store、media直链404。源数据库/媒体未变，临时集群cleanup complete。归档1f189c3f74fd-0edd1427.zip的SHA256为6c0dc8077710edb1c47c853d39f62a5d5ce0b6d591607e3745ca45727c4d0688；核对文件见artifacts/postgres-backups/finance-restored-1f189c3f74fd.json及full-regression-results.json。这不是目标Linux维护窗口、真实运行角色或生产恢复演练。

## 最后前端测试补修与交付回执

ISS039全库快照默认输出缓冲的同型ENOBUFS已复现；新helper保留完整快照，以32MiB有界输出承载，并给出真实error/signal/字节数诊断。原业务和无副作用断言没有减少。受影响Chrome两尺寸2/2及默认Node179/179通过；新SHA全套Playwright与三CI以交付回执为准。前一CI失败日志和原始artifact子集完整保留，不能称旧CI成功。额外8项PG命令级备份正常/拒绝/失败清理已独立8/8通过；全量原跳过数不重写。后端与产品前端相对1f189c3无变化，本次后续只修浏览器测试基础设施并更新证据/文档。

测试修复精确来源：03b524db7392ab989c699e31586484fd33a95fcb（ISS039完整快照缓冲）及7a896d0f824a361287cf981c377b07731c45f879（财务测试输出跟随隔离证据根目录，避免改写旧来源、漏出CI归档）。后者新默认路径真实Chrome4/4；原FINANCE_CLOSEOUT_EVIDENCE显式覆盖及独立运行默认路径继续保留。最终后端和产品前端与全量已验1f189c3的Git tree完全一致，见code-tree-equivalence.json。原候选CI的124张实际Chrome PNG另存ci-1f189c3-ui-screenshots.zip；该运行整体失败2项的事实不变，截图本身不当作业务通过。
