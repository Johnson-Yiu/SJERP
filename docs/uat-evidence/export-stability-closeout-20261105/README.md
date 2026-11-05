# EXPORT-STABILITY-CLOSEOUT-03 验收记录

固定基线 `bcdcb57545f121b8a4102f352c74008b47372035`，源码检查点 `56ce3588f544fcfeb98d431fb71d7e2d937f67db`。本工作树独立于统一集成工作树。CI 根据用户要求暂停，所有新提交带 `[skip ci]`，未触发或等待 Actions。

## 当前结果与边界

- 报价：原始时序的默认Chromium场景1/1、真实Chrome场景1/1通过。原动作和断言保留，增加HTTP 200、文件非空检查和实际XLSX保存。`quote-chrome/browser/quote-editor-mobile-actions.spec/xlsx-verification.json`记录文件SHA、ZIP CRC、PI表、合成报价编号、型号与12.5金额；1440与390截图为实际Chrome页面，已人工查看。Chrome定向运行发生在源码检查点提交前，报价页面/API和专属测试内容与检查点相同，财务页面当时有并行编辑，不能称该定向运行是冻结整棵56ce源码的全量测试。既有完整套件262通过/1次`download.saveAs: canceled`原始失败仍在基线证据中；单次成功不能证明根因或覆盖旧失败。此前诊断显示失败发生在Blob撤销前，页面未在点击后导航；本轮完整套件使用与原失败证据根目录相同的161字符长度，不将路径长度预设为原因。
- 报价的独立字节诊断从详情页调用同一导出helper：同一次真实HTTP响应和Chrome下载均为10,117字节、SHA相同，ZIP及合成型号、数量、单价和金额通过检查；内部临时路径100字符、保存目标164字符。详情见 `quote-http-byte-control/README.md`。该诊断的页面入口与原失败的保存并导出不同，读取响应和记录时间线可能影响时序，不代替原场景或完整套件。
- 保存并导出的独立有界诊断另外运行三次、各1/1通过；保留原动作和断言并添加页面/上下文关闭及下载监听。三次均未复现取消，未进入失败采集分支，Chrome `interruptReason` 仍为UNKNOWN，未采集中断码；监听可能改变时序。见 `quote-save-export-interrupt-diagnostic/README.md`。不把这三次结果合并为原完整套件的通过数量或宣称报价问题已修复。
- 财务：导出失败不再占用页面加载错误状态，允许重试；导出期间捕获请求期间并用于文件名，实际资金导出增加进行中保护。没有改动财务计算、业务服务或后端。基线bcd的相同Chrome模拟API测试3/3失败：桌面及390导出失败后按钮不可重试，实际资金缺少进行中禁用；修复后3/3通过。独立模拟API期间竞争对照显示：bcd账面及实际资金导出内容仍为10月而文件名错误显示9月，56ce两项的文件名与请求期间一致；原始CSV和结果见 `finance/period-race-control/`。真实Django和Chrome的16个CSV下载覆盖1440/390、两个月份、账面/实际资金与连续导出；合成数据由API校验及状态机创建，检查金额、UTF-8 BOM和`= + - @`公式前缀转义。下载与另一笔同URL、未改变数据库的原始HTTP响应逐字节一致；Playwright `response.body()` 与下载相差BOM，首次直接比较失败已保留，不称同一响应字节一致。详情见 `finance/baseline-control/`、`finance/README.md` 和 `finance/real-django-chrome/README.md`。
- 上轮已修下载行为的账户资金页另有 `finance/ledger-chrome/` 真实Django/Chrome专项：1440及390、9月及10月各连续导出两次，8份CSV均检查BOM、金额、四种公式前缀和期间过滤；每个视口首次请求模拟400，确认报错后可重试，其他下载走真实服务；离页重入发生在下载完成之后。合成账户和8条事实经API及状态机创建。首轮种子因开发身份未开启而403、首次Chrome因诊断脚本标题定位不唯一而失败，日志与截图均保留；修正隔离设置和诊断定位后成功，未改产品断言。
- 版本与重跑：上述首次财务Django 33项及两组真实服务Chrome测试使用系统Python3.14/Django6.0.6，是独立旧结果。随后在新目录使用Python3.12/Django6.0.9、独立SQLite及合法API种子重跑：Django 33通过/0失败/0跳过；Chrome概览和实际资金16次、账户资金8次下载通过，金额/BOM/四种前缀和独立HTTP字节对照分别通过。账户资金另外补拍等待期间刷新完成后的四张截图；原截图和原始结果保留。证据和退出码见 `finance/django609-rerun/README.md`，不把两轮数量相加。
- Packing List：真实Chrome桌面连续两轮各10次、390px一次，保存的XLSX经ZIP CRC、openpyxl、混装数据和响应字节检查；专项后端28/28、组件26/26。测试样本使用现有合成测试fixture，不代表正式业务数据创建流程。未复现取消，不修改原有零延时撤销实现；有限成功不排除其他时序。见 `packing/README.md` 和 `packing/README-390.md`。
- 上述早期报价和Packing服务诊断使用系统Django6.0.6，版本不足以代表锁定环境；后以Python3.12.16/Django6.0.9的合成数据库副本重跑，报价同次响应与下载均为10,143字节且SHA相同，Packing桌面连续10次逐次一致并通过工作簿校验，另补390px截图与实际文件，见 `python312-http-recheck-20261105/README.md` 及 `packing-390/README.md`。重跑带响应读取诊断钩子，旧结果及限制保留。
- 完整前端：首次Node单元179/179，但其中隔离运行器子进程使用系统Python及Django 6.0.6；随后指定锁定Python3.12/Django6.0.9重跑179通过、0失败、0跳过，日志见 `logs/unit-locked.log`。字体1/1、Vitest 725/725（78文件），生产构建退出0。首次`npm ci`新增227包，审计5项moderate，两个依赖弃用提示；构建有大于500kB chunk提示。Node24与历史CI Node22存在环境差异。首次安装输出未另存文件，其退出0及审计计数为直接观察；回归后同一锁文件另做一次`npm ci`并保留完整 `logs/npm-ci-repeat.log`，退出0、添加227包，不能把复装日志冒充首次日志。
- 视觉证据：`visual-index.json` 列报价、财务概览、账户资金及Packing List桌面/窄屏八张真实Chrome截图的实际像素、场景、源码和SHA。长页面为全页截图，不能称为单屏高度；截图不单独证明金额或业务闭环。
- Playwright完整适用套件：源码56ce的九个配置全部退出0，266通过、0失败、0跳过，其中业务配置241通过、报价原操作配置1通过。完整打印及分页spec的七项按用户此前决定延期，单独标为未运行，不计为跳过。逐配置计数、退出码和日志见 `full-suite/test-counts.json`。本次完整套件通过是本次事实，不能覆盖旧版262通过/1失败，也不能证明历史取消根因已消除。

## 已执行命令

在 `frontend` 目录分别执行 `npm ci`、`npm run test:unit`、`node --test tests/detail-drawer-typography.spec.js`、`npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js` 和 `npm run build`，首次各自退出码均为0；首次Node单元的Python子进程版本限制见上。报价使用 `node scripts/run-isolated-browser-tests.mjs --business-test quote-editor-mobile-actions.spec.js`；两次指定隔离Python和各自证据根目录，Chrome次额外设置 `EXPORT_STABILITY_CHROME=1`，退出码均为0。锁定Python为3.12.16，来自此前隔离环境的只读解释器；16个锁定包版本全部匹配且pip check通过。应用代码与测试均来自本工作树。`logs/quote-logs-manifest.json` 和 `logs/frontend-logs-manifest.json` 记录公开日志与本机私有原日志SHA；只对已关闭隔离环境的随机token作公开副本脱敏。

完整适用Playwright执行本报告内的 `full-suite/run-applicable-suite.mjs`，它按原九配置调用未修改的 `frontend/scripts/run-isolated-browser-tests.mjs`；只额外排除用户延期的完整打印spec，原七场景未删。证据根使用 `full-suite/0123456789012345678901234567890`，实际长度161字符，与原失败时的证据根长度相同；长度匹配不是根因结论。

项目原套件的部分旧测试仍向历史证据路径写截图：运行前新工作树干净，完成后已将30份本轮生成图另存 `full-suite/history-path-overwrites/`，再按HEAD原始Git字节逐项恢复原历史图；另3份写到未跟踪 `frontend/docs/` 的图已复制，原件留在本机。每项新旧SHA和恢复结果见该目录 `manifest.json`。全套日志公开副本对隔离随机令牌及相关凭证字段进行脱敏，22个原始文件在本机私有目录保留，映射和SHA见 `full-suite/publication-redaction-audit.json`；测试结果与失败记录未改。

为保留实际文件和已记录的脚本副本SHA，本证据目录的自动生成PDF、日志及明确列出的冻结脚本副本按二进制归档；产品源码和活动测试仍执行正常的 `git diff --check`。早期直接写入合成数据的试验SQLite没有用于财务验收，原件仅留在本机，公开清单记录其哈希及排除原因。

## 失败证据与限制

财务专项首次模拟500时触发既有GET重试，测试等待立即报错超时；该次原始日志未单独保存，记为UNKNOWN。最终用400测试不可自动重试的失败，3/3通过。真实端到端首次直接比较浏览器响应与文件因BOM差异失败，失败日志保留；后续独立HTTP字节比较通过。首次fixture API因`testserver` host限制失败，Django debug HTML可能含环境信息，公开日志脱敏该HTML，原始日志仅保存在本机私有临时目录，SHA见 `finance/real-django-chrome/seed-api-redaction.json`。首次截图被重试覆盖，不冒称保存。

随后补做独立Chrome模拟500测试：首次点击的原始请求及5次自动重试均返回500，重试耗尽后错误可见且导出按钮恢复可用；手动再次点击的第7次请求返回200，CSV的BOM和内容通过，退出码0。`finance/retry-500-control/`保留逐次时间戳、失败/成功截图、下载及日志；该补充不是重建此前遗失的首次500日志。

账户资金下载进行中离页、所有CSV字段及所有运行环境未在上述专项中穷尽。完整打印继续延期，正式认证、真实资料与部署均不在本包。未改公共台账或自行关闭Issue。
