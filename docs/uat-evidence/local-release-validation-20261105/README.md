# LOCAL-RELEASE-VALIDATION-03（执行中）

固定起点 `bcdcb57545f121b8a4102f352c74008b47372035`，统一分支 `codex/r1-prelaunch-consolidation-20261104`。本包不修改或重试延期的完整打印及分页；报价 XLSX、财务 CSV 和 Packing List 等实际文件不在该延期范围。GitHub Actions 按用户决定 `NOT_RUN`，不视作通过。

## 已复现与修复：ISS-121 来源长度

上轮候选预审已指出来源编号长度及跨组作用域缺少边界证据。本轮以合成工作簿复现：超长来源系统名和组编号在 SQLite 被接受并创建申请，而模型分别限制 160 和 120 字符；首次反例见 `logs/history-source-boundaries-before.log`，2 项失败。SQLite 不证明 PostgreSQL 的运行结果。

预检现在对超长组号、系统名和实际存储的来源编号（包含复合明细编号）标记阻断；申请提交前拒绝超长内容，旧申请执行前再次验证，不截断历史来源。SQLite 边界测试验证 120/160 上限、超限拒绝且无申请、跨组同系统同类型同编号冲突、其他系统独立、哈希请求键长度、预检错误与旧申请防护。`logs/history-preflight-boundaries-final.log` 共 45 项、1 个 PostgreSQL 专项跳过、其余通过；检查点 `b27b9a0fddfe20b706bf4762e9e38168ac0333d1` 使用新建 PostgreSQL 17.11 专项：55 项通过、无跳过，含边界、历史并发及原三财务反例；102 表、1218 行、133 迁移及 5 个媒体文件的历史/财务/运营备份恢复核对通过，见 `logs/postgres-b27-targeted.log` 与 `pg-baseline-targeted/`。此结果不能代替最终集成候选全量。首次模块名拼写错误造成的 62 项/1 error 及修正后 64 项/8 skip 记录分别见 `logs/baseline-history-finance.log`、`logs/baseline-history-finance-corrected.log`。以上为本包源码修改前后各自的局部证据，不代表最终集成全量。

## 可复现本地入口

`run-local-validation.py --sha <完整HEAD> --python <锁定Python绝对路径> --postgres-bin <PG17 bin绝对路径> --openssl <OpenSSL绝对路径> --run-name <新目录名>`；运行前先 `python -m pip install -r backend/requirements.lock`。入口拒绝与 HEAD 不同的 SHA 或有未提交应用源码，逐阶段检查源码状态并保存命令、退出码、日志 SHA 及摘要。SQLite 全量使用内存库，升级检查使用新建专属 SQLite 文件；PostgreSQL/备份复用原专属临时集群保护，历史 Chrome 复用原隔离脚本。真实浏览器沿用九组配置，唯一额外排除 `iss037-print-output-acceptance.spec.js`；原始打印测试未删除或修改。入口不连接现有数据库，测试合成数据与临时媒体，GitHub CI 为 NOT_RUN。

错误 SHA 和应用源码有未提交变化均在创建测试目录前拒绝，分别见 `logs/runner-wrong-sha.log`、`logs/runner-dirty-source.log`。该入口预检模式在 b27b 及运维接收后的 `c3e68b9633dbdde5589dbc4d9f8acfcc8925184f` 分别执行；锁定依赖、Django 检查、迁移图、含合成旧客户的 SQLite 0103→最新升级通过。其后发现 Windows 可执行文件查找差异，两次预检在 Node 路径校验阶段失败，证据 `preflight-locked-path/result.json` 和 `preflight-locked-path-fixed/result.json` 保留；改为真实 Node 子进程校验后 `preflight-node-python/result.json` 的预检全部通过。入口的完整运行仍需在稳定来源集成后验证；不可将语法检查说成全量通过。运行期间以周期检查监测源码，不能替代操作系统不可变挂载；应使用专用冻结工作树并禁止其他进程修改。

[87 项代码、断言和证据索引](REVIEW-INDEX.md) 是由原复审映射和 ISS-121 补充生成的待审入口；87 个条目均有测试断言或视觉采集校验入口。已检查 829 个代码/断言/资料链接及行号可定位，但链接存在不证明业务正确；断言候选须由独立审查者核对是否覆盖具体问题，不等同独立接受。

## 待完成

运维工作包完整稳定 SHA `250c3b7f55585acccb73b2efc1b0993605be0b0b`、导出包完整稳定 SHA `dc57b06e856f4640c804e5d14659e40b4093c4e4` 均已核对远端并完整合入，两个来源均为集成候选 `a46c26f796fe6cc4c4a6a07dc70fe92cfda34114` 的祖先，未发生合并冲突。导出来源适用浏览器套件 266/266 通过，但此前报价下载取消根因仍 UNKNOWN；原失败不得覆盖。该候选的全量已经结束但浏览器和历史 Chrome 未通过；修复测试证据输出后，新的冻结候选 `d5a6a23394397775d3aab0f237163d4000bce224` 已在独立工作树完成重跑，但浏览器全套仍有一项失败。运维真实 Linux 跨 UID 等未验限制保留。真实 Linux 跨 UID 和目标生产环境未执行时维持各自待验；不以 Windows 模拟替代。不得关闭待独立复审 Issue、合并 master、部署或导入真实数据。

`c3e68b9633dbdde5589dbc4d9f8acfcc8925184f` 的 Node 全量 179 通过、0 失败/跳过，使用锁定 Python；发布日志中 10 处一次性隔离 token 已脱敏，原始日志保留本地且记录原始/发布 SHA，见 `logs/node-c3-locked-redacted.log` 和 `logs/node-c3-redaction.json`。不以该运行替代最终整合源码的 Node 全量。历史 Chrome 脚本现支持 `ISOLATED_TEST_PYTHON`，原默认路径和断言不变。

预检结果 `preflight-node-python/result.json` 中 Node 启动的 Python 为锁定环境，Django 6.0.9。入口自检失败记录 `preflight-locked-path/result.json` 与 `preflight-locked-path-fixed/result.json` 不删除；失败时后续步骤为 NOT_RUN，不能记为通过。

同一检查点 `c3e68b9633dbdde5589dbc4d9f8acfcc8925184f` 有效 Vitest 全套 78 文件、725 项通过，见 `logs/vitest-c3.log`；源导出包尚未接收，本结果不替代最终集成全量。

已记账历史资金补充合成测试：审计更正的申请细节记录来源 ID 与资金事实 ID，审核事件关联申请，原资金及映射保持不变、不能把已记账指令作为失败/取消重提；`logs/history-posted-correction.log` 1/1 通过。当前更正 `details` 仍为自由内容，系统未自动验证填写的来源/事实 ID 或凭证与对应原件一致；真实业务更正/退款映射及凭证对应仍需业务规则与独立复核，不得把该测试扩大为所有更正类型已支持。

`b27b9a0f` 专项的实际合成 PostgreSQL 备份 ZIP SHA256 为 `a45c53a0b6714f8071b5e4ad3a3d8635fb07b012d47c3ad5945a2e4ab7563637`，原包仅保存在本地专属证据目录（包含一次性测试会话，不推送原包）；仓库保留备份清单、恢复核对与原始测试日志。此前集成公开样本及脱敏副本仍位于 `integration-closeout-02/`。

最终验收工作树为 `.tmp/lrv-final-a46c26f`，应用源码冻结 `a46c26f796fe6cc4c4a6a07dc70fe92cfda34114`。浏览器套件可能把截图写入冻结副本的历史证据路径，不会改动统一分支既有文件；只发布带来源和哈希的新证据。结果收齐后才更新本报告，不将仍运行中的步骤记作通过。

冻结应用候选 `a46c26f796fe6cc4c4a6a07dc70fe92cfda34114` 的最终本地后端：SQLite 1419 项、1339 通过、80 跳过、0 失败；PostgreSQL 17.11 1419 项、1387 通过、32 跳过、0 失败。PG 合成备份恢复核对 102 表、1218 行、133 迁移、5 文件，历史/财务/历史运营恢复均通过，源媒体未变且清理完成。原始详细日志在冻结工作树的 `final-a46/logs/`；独立备份故障注入及前端套件仍在运行，不能将全包标记完成。

最终候选 `a46c26f` 的浏览器全套出现新失败：`quote-editor-mobile-actions.spec.js` 在第二视口截图 `page.screenshot` 阶段达到整个测试 30 秒时限，未执行保存并导出，因此没有本次下载、下载路径或 `saveAs` 结果；日志记录该隔离 API/Vite 进程树停止且端口释放。失败上下文和原始日志保存在冻结工作树 `final-a46/browser/artifacts/` 与 `browser/logs/playwright-profiles/quote-editor-isolated.*.log`。这是截图/工作流整体时间预算问题的实测现象，不是旧下载取消已复现，也不能确定浏览器取消根因。现保留全部断言，在测试中为每张截图设置独立 15 秒上限、为包含四个视口与两个完整打开流程的整项设置有界 90 秒，并增加下载、页面/上下文关闭、路径和进程的生命周期记录；需在新源码重新跑全量，不能用局部通过抹去本次失败。

失败当次隔离运行 ID `0e59d5f2-c4fd-422e-86cd-d96bb1bfbab8`，API/Vite 分别监听本机 6905/6907；页面错误快照停在报价编辑界面，测试在构造下载事件及目标文件路径之前超时，因此不存在可记录的本次下载路径或中断码。原测试没有页面/上下文关闭事件监听，无法事后推断这些事件；仅能确认运行器日志明确记录服务进程树停止、端口释放和任务专属临时资源清理。新增生命周期记录供新候选发生失败时直接取证，不追造原次缺失数据。

## 候选 a46 全量中的浏览器失败（保留原始失败）

`a46c26f796fe6cc4c4a6a07dc70fe92cfda34114` 的适用浏览器套件有实际失败，不能计为全套通过。报价编辑器场景在下载开始之前的截图步骤耗尽 30 秒总预算；本次不是已知的 `saveAs canceled`，旧取消根因仍为 UNKNOWN。后续测试仅补充分阶段超时和页面、上下文、下载生命周期诊断，不改变产品导出和断言；两个定向启动分别遇到端口占用、隔离 Django 身份检查超时，均未进入测试，不能算通过。

ISS-007 图片快照场景在整项 60 秒用尽时等待最后一次打开报价预览；错误快照中报价工作台及“预览 PI”按钮均已出现。该场景包含多次图片上传、真实导出及 8 张截图；后续测试保留所有断言并增加阶段耗时、为完整多阶段场景设置总预算，尚待重新运行验证。失败后隔离 API/Vite 进程退出且端口释放，但测试私有 SQLite 文件清理遇到 EBUSY，原临时目录保留，不能称清理完全成功。以上现象尚不能证明产品缺陷或并发负载是根因。

首轮 `a46c26f796fe6cc4c4a6a07dc70fe92cfda34114` 共 9 个浏览器配置中 7 个退出成功、2 个失败；生产构建通过。历史 Chrome 未开始测试：ISS-067 测试将 3 张截图写入 `frontend/docs/`，干净源码检查正确拒绝执行。原截图及 SHA 复制至 [证据目录](candidate-a46-iss067-screenshots/manifest.json)，保留失败日志；首轮其他日志及失败现场经脱敏后见 [原始记录索引](candidate-a46-evidence/publication-manifest.json)，保留原始和发布文件哈希。此前启动的 `732d756cec38c139187e7d9c49de771d97df93d4` 全量因确认会遇到同一证据路径问题而主动中断，绝不能记为全量通过。现将 ISS-067 截图写到 Playwright 专属输出目录，不修改权限断言；固定新的 `d5a6a23394397775d3aab0f237163d4000bce224` 重跑全量，最终结果以该次实际日志为准。

`d5a6a233` 截图路径修复后，在另一个隔离环境运行 ISS-067 定向测试：第一张截图成功写入 Playwright 输出目录，但两项中一项点击“经营概览”时耗尽 30 秒测试总预算，另一项通过；隔离 API/Vite 已退出、端口释放，专属临时数据库和媒体已清理。这个定向运行是 FAIL，不证明完整场景通过；点击已定位但在等待可见、可用和稳定时超时，产品或环境原因尚未确定。脱敏日志及原始/发布哈希见 `logs/iss067-path-target-redacted.log`、`logs/iss067-path-target-hashes.json`；本次失败不能由后续定向成功覆盖。

首轮发布清单的 322 个文件重新计算 SHA256，均与发布哈希一致；原始文件保留于本地隔离工作树，发布文本已脱敏。

最终候选 `d5a6a23394397775d3aab0f237163d4000bce224` 的本地全量进行中：SQLite 1419 项、1339 通过、80 跳过、0 失败；真实 PostgreSQL 17 全量 1419 项、1387 通过、32 跳过、0 失败，合成历史、财务和历史接续备份恢复通过。PostgreSQL 32 个跳过包括 21 个 SQLite 文件备份用例、8 个另行运行的独立 PostgreSQL 备份命令用例，以及 3 个 Windows 不支持的符号链接/POSIX 场景。独立 PostgreSQL 备份命令故障测试 8/8 通过；锁定前端依赖安装通过，Node 179/179、字体 1/1、Vitest 78 文件 725/725 通过。适用浏览器全套 265 通过、1 失败，延期打印 7 项未运行；生产构建通过，历史 Chrome 合成业务流程通过。因报价下载取消，全套总体为 FAIL。

最终候选已结束的 19 个环境、迁移、数据库、备份和前端日志已脱敏并保留原始/发布 SHA：[日志清单](candidate-d5-backend-logs/publication-manifest.json)。尚在运行的浏览器日志不包含在该快照中。

最终候选 `npm ci` 成功但报告 4 项 moderate 漏洞；此为安装工具汇总，未逐项核实公告和实际可达性，不代表完整安全审计；未运行 `npm audit fix`，沿用 ISS-002 原待验记录。


## 最终候选浏览器与交叉验证

精确测试提交 `d5a6a23394397775d3aab0f237163d4000bce224`：9 个浏览器配置共 265 通过、1 失败、0 跳过；其中主业务 241/241，ISS-007 图片快照 1/1，报价编辑器 0/1。生产构建及真实 Chrome 历史闭环通过。统一结果为 FAIL，不能作为完整通过或上线就绪依据。全部阶段日志、实际导出及截图见 [候选证据](candidate-d5-full-evidence/publication-manifest.json)；历史 Chrome 另见 [历史证据](candidate-d5-history-chrome/publication-manifest.json)。用户延期的原生打印 7 项 NOT_RUN。

报价失败现场：导出 GET 返回 200、响应 10219 字节，浏览器产生下载事件，约 149 毫秒后 `download.saveAs: canceled`；此时页面和上下文仍开放，页面 URL 为报价详情，同次测试的临时下载根目录及 Playwright 输出目录已记录。随后浏览器页面与上下文关闭、隔离 API/Vite 进程退出、端口释放，独占临时目录清理成功。当前代码在点击后 1000 毫秒才撤销 Blob URL，单凭本次时序无法归咎该定时器。日志中 `test-finish.status` 在异常尚未交还给 Playwright 时可能显示 passed，最终 Playwright 结果和 failureMessage 均明确 FAIL；后续诊断提交修正为失败/执行中状态。API 正常不证明实际下载正确，也不能确定取消属于产品还是运行器；根因 UNKNOWN，ISS-020 保持原状态。

为定位增加主框架导航、Blob 撤销和下载链接事件记录（诊断代码 `1b548b67e74dc7bb1ba144f98eec97f5d5dbfda0`，只改测试，不改业务实现）。独立真实 Chrome 156 与默认 HeadlessChrome 156 各运行一次均成功保存实际 XLSX，分别 10218、10219 字节；两次均无法复现失败，不能覆盖上述全套失败或排除偶发问题。[对照证据](quote-download-diagnostics/publication-manifest.json) 保留真实文件、截图与脱敏日志。下一步须在捕获导航、链接、Blob 和请求失败事件的条件下复现完整失败，区分浏览器运行器与业务触发后再最小修复，并对最终稳定源码重新执行集成全量。

独立真实 Chrome 机制对照采用零填充合成 Blob（不是 Excel 文件）：基线、点击后同页路由、点击后整页导航各成功保存 10219 字节。该实验未复现取消，只说明这些单独动作不足以稳定重现；不能证明真实故障与导航无关。复现入口 `probe-download-navigation.cjs` 从 `frontend` 执行，输出见 `logs/quote-navigation-probe.log`；两次实验各自的专用临时目录保留。

候选 `d5a6a233` 的 PostgreSQL 合成恢复核对覆盖 102 张表、1218 行、133 条迁移记录和 5 个私有文件，源媒体未变化；加密合成备份包保留本地，SHA256 `a7822f46b6db60b219683053c1bf6f3bf0a08657fd255c545c9385626189a2df`，不将隔离数据库或凭据推送。为在完整运行中捕捉取消发生时的导航、Blob 与请求事件，随后固定新测试候选 `d7d927658e26727b6ebef135708d77278b9ee258` 重跑全量；它尚无最终结果，不影响 `d5a6a233` 的 FAIL 事实。

诊断候选 `d7d927658e26727b6ebef135708d77278b9ee258` 已完成 SQLite 1419 项（1339 通过、80 跳过）、真实 PostgreSQL 1419 项（1387 通过、32 跳过），二者均 0 失败；独立 PostgreSQL 备份故障 8/8、Node 179/179、字体 1/1、Vitest 725/725 通过。新候选浏览器、构建和历史 Chrome 尚未结束。已结束的 19 份日志经脱敏并记录原始/发布 SHA：[日志清单](candidate-d7-backend-logs/publication-manifest.json)。此前 `d5a6a233` 的浏览器 265/1 仍为 FAIL。

`d7d927658e26727b6ebef135708d77278b9ee258` 进行中的浏览器主套件出现历史经营分析导航 `load` 等待 30 秒超时；快照显示标题及多张明细表已经出现，阻塞 `load` 的具体资源未知。测试提交 `d7d37de82f492f0e128f85ee28577f8e3e3a058d` 使用 DOM 就绪并保留原标题、表格、布局和权限断言；隔离 Playwright Chromium 定向 2/2 通过，进程/端口/专属临时数据清理成功，不能覆盖全套失败。[定向证据](history-navigation-target-evidence/publication-manifest.json) 含截图、脱敏日志和哈希；完整失败现场待本次运行结束后归档。

`d7d9276` 主套件还出现应付布局刷新和资金重复核查导航等待 `load` 超时；应付失败快照已有筛选框及原值。资金套件要求两条审核，第一场景超时后最终仅有一条，因此另一个 afterAll 断言也失败；这不能单独证明业务缺陷。改为 DOM 就绪并保留筛选值、布局、候选及审核断言后，隔离财务布局 10/10、真实 Chrome 合成资金重复核查 2/2 通过，进程、端口及专属临时数据清理成功。[定向日志及截图](finance-readiness-target-evidence/publication-manifest.json)。同次主套件还观察到导入 CSV 的 `download.path: canceled` 及报价历史 XLSX 的 `download.saveAs: canceled`，具体原因未定，完整失败日志待全套结束归档。

新增来源：CORE-BUSINESS `78bcedb217d3d6ca0a05c9348e72d37c35801312` 的完整 8 提交已合入 `eab047ddc8055bc3ff3ff13442f242bf8b389d5f`，无合并冲突；源包 SQLite/PostgreSQL 各 1430 项仅为来源证据，不能替代集成全量。主体 `792edff6b696c4ad1f5bc65f9e91f623b5b964c0` 尚未接入、仅部分交付；权限审查 `81cb56c18e6183b357af5b9845a4d56d6e6dd96b` 只接收[报告和测试原件](../access-readiness-20261105/INTEGRATION-NOTE.md)，不接入会失败或要求错误行为的默认测试，待权限包修复。

核心合入冻结候选 `76c98873f8ba4e521941f497fbd170c9b2bdb689` 的 SQLite 跨库存、历史盘点、采购成本及审计测试 71 项中 64 通过、7 项 PostgreSQL 专属跳过、0 失败；真实 PostgreSQL 17 交叉已完成 76/76、0 跳过，包含库存/取消/成本竞争及第二条采购付款审计失败后重试，历史、财务及运营合成恢复均通过；[脱敏日志](core-pg-cross-log/publication-manifest.json)、[恢复证据](core-pg-cross-artifacts/publication-manifest.json)。合成备份包留本地，SHA256 `9b25dbd40139a272b290e84125c370027e56561088452602eb89d3755356b57c`。已有正式主体快照与数量调整兼容专项仍在运行，部分主体新模型尚未集成。SKU 只读场景在旧候选全页 load 超时；测试提交 `4463ef8ca85871fa39c73941b608b66c57597f97` 改为 DOM 就绪且保留权限断言，独立 Chromium 文件回归 17/17 通过。两次原始日志及哈希见[定向证据](core-sku-target-evidence/publication-manifest.json)，不覆盖完整套件失败。
