# REVIEW-INTEGRATION-BATCH-01

本报告仍在编制，不能作为完成验收或上线授权。

当前阶段代码检查点：`7ca7a7a`（完整 SHA 以最终交付记录为准）。已接收打印封存、核心工作区、财务及运维完整来源；历史来源正在确认最终 SHA CI，未按移动 HEAD 合并。综合最终 CI 尚未执行，后续继续推进。

最新集成实测：财务合入阶段后端 1249 项中 1189 通过、60 跳过、0 失败（838.208 秒）；Vitest 717/717。运维合入及侧栏修复后 Node 177/177，生产构建成功（4.39 秒，大 chunk 警告保留）。隔离 Chrome 财务认证双人审批/过账/私有凭证 2/2，开发资金页面 2/2；正常服务拒绝待核实/模拟资金及统计不变测试 2/2。上述结果均有本包日志，不用来源结果代替集成实跑。

本阶段实际 Chrome 156 已保存 13 个页面的桌面/390 窄屏共 26 张截图，无 pageerror；来源、摘要、尺寸和范围见 `screenshots/integrated-pages-manifest.json`。空业务页面仅作为空状态/布局证据，正向业务闭环另见真实 HTTP、数据库、实际文件及财务浏览器证据。侧栏长姓名 2/2，完整姓名保留 title，另有内置浏览器截图。

阶段原始日志归档 `raw-logs-phase-01.zip` 已实际生成；manifest 明确排除正在写入的日志，并逐项列出原始/发布摘要及凭据脱敏次数。失败运行完整保留；含临时测试密钥的 CI 字段只发布明确脱敏副本，不能将其摘要称为原始字节摘要。最终验收后重新归档闭合日志。

## 已核对的起点

- 集成分支：`codex/r1-prelaunch-consolidation-20261104`
- 代码起点及远端 HEAD：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`
- 已核对的起点 CI：[41782956426](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41782956426)，该 SHA 的 CI 结论 SUCCESS。后续修改需绑定新的最终 SHA 验收。
- 保留现有历史预检、备份命令、0096/0097 汇合迁移及已有回归证据；工作树原有未跟踪截图、文件和日志未清理或覆盖。

## 并行来源接收条件

已完整接收财务 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`、运维 `d289de36a3da3e4bd6531c812ec21a05f046d570`、打印 `b3d0d386de70d9efd77bf62cdbd87877fbccbfb8` 和核心工作区 `e302199f7890c686a309f54aebe8cc31b6202f52`；远端和精确 SHA 三项 CI 已分别核实，完整谱系合入，见 MERGE-RECORD.md。历史尚未正式最终交付。早期开发检查点只作历史记录，不替代这些固定来源。

读取来源对话的最新用户指令后补充：打印完整验收与分页改进已由用户决定延期、后续自行处理（来源：`ISSUE FIX A02`，2026-11-04 用户指令“先收尾原任务，再直接进入新工作包”）。仅该子范围记 BLOCKED；ISS-037 其余主体快照要求不延期。用户另在该对话授权 `codex/core-workspace-ux-batch-20261104`，负责客户/跟进/产品SKU/销售/采购/库存前端体验，本包不同时修改这些页面，等待稳定来源统一复核。未向打印包追加催办消息。

## 复审边界

Codex 的代码核查、自动测试和并行预审均为开发侧自查。FIXED_PENDING_REVIEW 项保持待 ChatGPT 独立复审；本轮不自行关闭 Issue。历史通过证据按其数据库、身份、版本、页面和实际文件范围复用。

## 本地验收环境

本机默认 CPython 3.14、Django 6.0.6；本包创建专用虚拟环境按 requirements.lock 安装 Django 6.0.9 等精确依赖。安装和测试实际结果以 logs 中原始输出为准。PATH 中没有 PostgreSQL 工具，但已定位先前测试留下的 PostgreSQL 17.11 二进制并核实版本；本包仅复用二进制，在新建、带所有权标记的临时目录中创建一次性集群，不连接旧集群或业务数据库。第一次演练因未提交 backend 变更被既有安全检查拒绝并完成清理，后续结果仍待实际执行，不能用 SQLite 替代。

浏览器验证按用户本轮指示使用内置浏览器。最初外部下载页两次创建超时；随后本包隔离 ERP `http://127.0.0.1:55462/` 成功打开。首页桌面/390px实际截图已保存于 `screenshots/`，其他业务页面仍待验。数据库为新建 `.tmp/review-ui-20261104/db.sqlite3`，媒体为同目录下专用media；迁移至0097成功，日志为 `logs/ui-fresh-migrations.log`。

## 已完成的实际检查

| 检查 | 实际结果与证据 |
|---|---|
| 基线 CI 原始日志 | `logs/baseline-ci-direct.log`；首次经代理TLS握手超时，错误另存 `baseline-ci-41782956426.log`；仅命令进程清空代理后正常读取 |
| 基线 CI Backend | 1182项，1134通过、48跳过、0失败；CPython3.12/Linux |
| 基线 CI PostgreSQL17 | 1182项，1152通过、30跳过、0失败；0091–0094及原生SQL保护实际执行，不再描述为“从未做过PG验证” |
| 本地基线 Backend | 1182项，1131通过、51跳过、0失败；`logs/backend-corrected.log`。最初从仓库根目录发现0项的日志保留为 `backend-local.log`，不计通过 |
| 前端单元首次/锁定环境复跑 | 两轮均177项、176通过、0断言失败、1超时取消；日志 `frontend-unit.log`、`frontend-unit-locked.log`。并行运行器单项随后在原120秒限制内通过，完整套件仍待重型后端结束后复跑 |
| 前端单元后续核验 | 后端结束后默认命令第三次仍为176通过/1取消，`frontend-unit-after-backend.log`。基础设施诊断17/17通过，`frontend-infrastructure-diagnostic-regression.log`；`npm run test:unit -- --test-concurrency=2`完整177/177通过、0取消、0跳过，`frontend-unit-concurrency-2.log`，47.39秒。仅调度并行度，内部双运行器仍并行，120秒及全部断言保留；package脚本与workflow未改，不能把该结果冒充默认命令已通过 |
| 生产构建 | PASS；`logs/frontend-build.log`；主JS 1136.16kB、gzip396.79kB，保留大于500kB警告 |
| Vitest / 字体规范 | 69文件681项通过、0失败；`logs/vitest.log`；Node-only字体规范1/1通过，`logs/typography.log` |
| 新建SQLite全迁移 | PASS至0097；仅证明SQLite新库迁移，不能代替PG |
| 审计完整空表回退链 | SQLite3/3通过，0跳过；`logs/audit-full-rollback-sqlite.log`。新增回退至0089确认三表消失，再前向恢复所有叶节点并确认三表空；有历史时拒绝回退断言保留。PG结果待实际执行 |
| 本轮PG第一次尝试 | 安全拒绝：`Application SHA must match a clean backend and templates checkout`；新增未提交测试触发既有保护，`cleanup=complete`，`logs/postgres-focused.log`，未计为通过 |
| 本轮PG17全量ce74f8b | FAIL；发现1200、执行1199，1167方法通过、30跳过、2方法错误；另1类初始化错误导致1方法未执行，1147.795秒。两个HTTP夹具的Supplier.code超过两字，备份测试类缺完整隔离环境契约；`logs/postgres-full-ce74f8b.log`，cleanup=complete。空表完整回退、原生审计保护及两项附件并发实际通过，但整体及备份恢复不计通过 |
| PG17补修专项0914002 | PASS；29/29、0失败/跳过，222.604秒；`logs/postgres-focused-0914002.log`。含20附件故障/锁释放/并发、3真实HTTP正常/拒绝、2原生审计保护、3回退、1备份测试。随后实际备份恢复PASS：PG17.11/Django6.0.9、121迁移、84表/923行、两私有媒体文件，源媒体未变且cleanup=complete；不冒充全量或后续来源整合结果 |
| PG17最新附件与完整保护专项a866c29 | PASS；42/42、0失败/跳过，224.813秒；`logs/postgres-focused-a866c29.log`。增加实际junction边界拒绝、原始下载文件名及既有跟进安全。备份恢复再次PASS，121迁移/84表/923行/两私有文件；源媒体未变、cleanup=complete。这里是专项，不是后续财务/历史来源全量 |
| 本轮隔离浏览器全套 | FAIL；主套件226通过/1失败，其他8专项共25通过，合计251通过/1失败；`playwright-current/suite-run-summary.json`。资金过期草稿初始化立即读取断言失败，隔离同文件8/8通过另列，不抵消全套失败 |
| 测试证据路径补修 | 两文件Chrome专项2/2、3/3通过；`logs/evidence-path-*.log`。只改输出根目录，原夹具读取及所有业务断言保留；旧9个文件恢复历史Git字节，本轮输出与双摘要manifest另存 |
| npm ci | 首次因自有Vite占用原生binding报EPERM；停止仅本包UI服务后，使用本包缓存重试成功，安装227/审计228个包。`logs/npm-ci-current.log`与`npm-ci-owned-cache.log`均保留；4个moderate漏洞和glob/lucide弃用警告待明细核查，未自动升级依赖 |
| 默认前端单元最终本地复跑 | `npm run test:unit`默认命令177/177通过、0失败/取消/跳过，40.913秒；`logs/frontend-unit-after-npm-ci.log`。此前三次取消日志均保留，不删除失败记录；package/workflow/120秒限制未改 |
| npm审计 | 4 moderate、0 high/critical，`logs/npm-audit-current.json`；editorconfig/glob/js-beautify/minimatch，两个公告GHSA-3g3m-2fjr-6pw4、GHSA-g3hv-75wg-m249。只读取得依赖链，未运行audit fix，依赖处理须与运维包协调，不称安全审计全部通过 |
| 打印/核心合入后前端 | 默认Node177/177、0取消/失败/跳过，37.454秒；Node-only1/1；Vitest75文件714/714，114.45秒；build成功。日志`node-integrated-print-core.log`、`typography-integrated-print-core.log`、`vitest-integrated-print-core.log`、`build-integrated-print-core.log`。保留大chunk及插件计时警告 |
| 浏览器测试时序/证据隔离 | 资金8/8、正式合成PI文件1/1、字体失败保护1/1、核心真实API夹具1/1通过。资金断言现先等待页面操作入口可见，再执行原null及敏感字段断言；没有改财务产品逻辑。新增打印测试仅改输出根目录；完整原生打印仍按用户决定延期，本包不追加桌面打印操作 |
| 日志卡片视觉 | 内置浏览器及Chrome156.0.8078.80的1440/390两尺寸实际应用通过；Chrome两组DOM断言确认标题单行且无水平溢出，原PNG与组件SHA256在`screenshots/log-panel-chrome-metrics.json`，运行输出`logs/log-panel-chrome-visual.log`。内置390截图位图仍为375×812，未冒称精确像素 |

## 原始日志与实际文件

阶段原始输出原样保存在`raw-logs-phase-01.zip`，ZIP内路径对应本目录下原logs位置（含套件各stdout/stderr）；每份字节摘要见`raw-logs-phase-01-manifest.json`。ZIP不进行换行或尾随空白转换。历史来源日志另有两份无损ZIP及manifest，详见MERGE-RECORD.md。`.gitattributes`只保护下载/生成证据的原始字节，代码和报告仍按文本审查；实际CSV和70字节上传/下载TXT不能被Windows换行转换破坏摘要。

新增核心 HTTP 最终 SQLite 回归为2/2通过（98.105秒，`logs/core-http-rbac-20261104.log`），开发身份关闭且RBAC/审计开启，使用合成superuser session；具体范围及实际文件见 `CORE-HTTP.md`。附件故障回归当前15项、13通过/2项PG专属跳过/0失败，现有兼容6/6通过；不能把跳过的PG并发用例记为通过。ISS-007 原始 transaction test 日志仍保留3 run、0 pass、3 fail、0 error，明确是修复前失败证据。

本地修复提交 `ce74f8b7cf6cd1e1e4e8f50141d9fc38e86c3903` 已形成，尚未推送。本轮PG及浏览器全量均未通过，实际数量和原因见上表。后续交叉自查发现恢复文件被存储改名时引用更新可能回滚，以及提交结果不确定/锁释放的补测缺口，正在追加修复，不能把ce74f8b记作最终已通过版本。

后续补修提交0914002已完成上述29项PG专项；另发现恢复目录链接边界的最小防护补修进行中。HTTP新增拒绝用例一度使两个manifest重名，失败原始日志为`logs/core-http-final-20261104.log`；未归档的终端132.142秒3/3不作为可复核证据。主审修复命名前缀后，`logs/core-http-prefix-unique.log`实际3/3、0失败/跳过、107.906秒，新文件和三份独立manifest在`artifacts/http-final-prefix-unique/`。

内置浏览器已补充实际合成客户保存、重开详情、中文“德国”映射及邮件跟进保存证据；三张原图为1280×720。该UI后端是此前启动的no-reload进程，不作为新附件服务运行证明；详细范围见 `BROWSER-COPY.md` 与截图manifest。

## 逐 ID 矩阵与新增证据校准（2026-11-04）

- 全量矩阵：ISSUE-MATRIX.md。与当前主表逐 ID 对齐，共 124 个唯一 ID，包含 ISS-008-FUP-01。
- 当前状态数：OPEN 1、BLOCKED 15、NEEDS_VERIFICATION 14、FIXED_PENDING_REVIEW 84、CLOSED 10。历史记录保留，不以旧时点统计替代当前主表。
- ISS-062：当前状态 FIXED_PENDING_REVIEW。来源提交 9edbb6488a66a0801ecc1e5bc842df7866c6c7dc 是当前集成 HEAD 的祖先；test_dashboard_import.py 第 99–180 行覆盖截至冻结今日、排除未来/历史订单、补齐 12 个月及自定义报表保留未来范围。acceptance-report.md、两个 API JSON 和 1440px/700px 截图均存在。原专项记录 14/14、报表 20/20、前端 142/142、Dashboard Vitest 25/25、Chrome 13/13 通过。旧“业务日期未明确”仅作为历史记录保留；ISS-062 等待独立复审，不再提出日期定义待决。
- ISS-007：原始故障注入日志 logs/attachment-atomicity-20261104-transactiontest.log 实际为 3 run、0 pass、3 fail、0 error。第二文件存储失败留下 1 row/1 file/0 audit；上传审计失败留下 2/2/0；删除审计失败导致预期保留的 row/file 变成 0/0/0。该子范围归为确定缺陷，最小修复进行中；Issue ID 不变，台账状态仍 NEEDS_VERIFICATION。修复 SHA 尚 UNKNOWN；该日志明确不计作通过。
- ISS-028/035/045：当前状态均 FIXED_PENDING_REVIEW，历史状态记录保留。分类/SKU 来源 47fcab0f6f37f52475074e65ab7ab188352ae8ce、旧 QA 命令退役来源 72a6b27f3f855424f16cd9657996055c68b5ca95 与 seed 隔离补修 6ec1a50ee14fd17a64de4f68cd63e2b2c426b47b 均已核实为当前 HEAD 祖先。
- ISS-037：只有完整打印验收及分页改进子范围明确延期、后续由用户处理；ISS-037 其他主体要求不延期。具体原始用户授权见矩阵所列 ISSUE FIX A02 userMessage ID。
- core-workspace-ux 包已获授权负责核心前端；本轮未核实其稳定来源 SHA。移动来源尚未接收，不据此推定已集成。
- 矩阵整理阶段没有改变业务代码；其后本包主审已同步共享台账的上述状态校准，并开展附件缺陷最小修复和真实 HTTP 新测试。当前 HEAD 的既有 CI 证据为 run 41782956426；本次仍未形成新的最终 SHA CI。

## 来源复核补记

运维来源已推进至 `09006189d642928fef3aec7cdc2c229d96bc939f`，但来源明确“尚未完成整包验收”，联合备份恢复、全写入者竞争、保留与加密机制未完成；该 SHA 仅列阶段记录，不作为完整来源合入。财务仍在补旧人民币资金确认入口的实际凭证核验，历史包仍在独立依赖与浏览器回归，核心前端包仍在采购交叉动作补修，均未接收移动 HEAD。

最新明确交付的打印封存b3d0d386de70d9efd77bf62cdbd87877fbccbfb8、核心工作区e302199f7890c686a309f54aebe8cc31b6202f52已重新核对远端及各自精确CI三项成功，并完整合入本分支。合并提交分别98bf4ea6108c913d0c6b31f77a25191df5e46e11、06d6cf1083afbdf98277dec3b6694834a868bf2f。冲突、历史原日志无损归档和workflow来源详见MERGE-RECORD.md；此前“核心未交付”的文字仅为历史过程，不代表当前状态。
## 待补齐

集中复审包、核心闭环数据库/HTTP/浏览器证据、缺陷归属、来源冲突处理、最终测试数量、最终台账统计及同一最终 SHA 三项 CI。逐 ID 矩阵已建立，随新证据继续维护。
