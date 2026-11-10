# RELEASE-COMPLETION-ACCEPTANCE-02

日期为 2026-11-10（北京时间）。工作分支为 `codex/release-completion-acceptance-02`，由已审提交 `1e45e42cc4fa38afbf856143228dada7c8a2e86f` 建立独立工作树。业务候选为 `d4f90b9233c509f1fc6ad282376ce512fb1a2fbc`。

## 来源与保留范围

| 来源 | 远端固定 SHA | 集成提交 | 本轮范围 |
| --- | --- | --- | --- |
| A/B/C/D 已审基线 | `1e45e42cc4fa38afbf856143228dada7c8a2e86f` | 同一 SHA | 保留工作区、财务导出隔离、SKU 成本快照、采购库存参考、附件与恢复、销售导入、历史预检与承接。 |
| B2 财务补修 | `96ad680c7b0cd154914046bcbe63de23fb8e64e3` | `4bebdc03c54851c1c010c48243c754fafbddf8bf` | 作废和审计同事务，收款、付款、银行登记与确认的账号隔离，实际退款日期及原身份重放。 |
| D2 历史补修 | `3e925910d43647e58c1f0512c2ccc6371adeb874` | `62245cfc8d55714af2ce14c9cb1dab825e164b82` | 冻结分类键与报表、筛选、下钻和 CSV 一致，中文追溯更正与审核。 |
| 集成回归 | 当前分支 | `0049dd15`、`9027ea40`、`8bf288af`、`89dd09d0`、`eb316cfa`、`6460141d`、`d4f90b92` | 旧接口与 Windows 测试、独立历史数据库、资金确认状态、原生缩放与窄屏表单。 |

两个交付均为已审基线的直接后继。共享 `backend/crm/views.py` 按函数核对，保留 B2 的 `TransactionViewSet.void` 与 `refund_cash`，并接入 D2 的历史分类筛选。公共应用主壳和导航、数据库模型、迁移文件及 GitHub Actions 工作流未出现本轮变更。

## 失败归因与修复

- 无身份的旧收款测试进入兼容收款入口，返回 400。测试给每笔合成收款设置业务流水号，并继续核对精确金额、计划余额及无副作用。
- 相同收款内容重放返回原 201。旧断言更新为核对重放响应、结果和不重复写入；相同身份改金额时继续检查 409。
- 分配详情增加剩余应收，完整响应断言同步验证剩余金额和原订单、计划、已分配金额等字段。
- 核心业务链改用原收款流水和实际凭证退款，检查日期、金额、应收恢复、完结订单状态、实存与预留。
- 历史回退测试从最终库越过不可逆 0120 时，可能已撤去后续字段。本轮将历史起点在一次性 SQLite 文件或同一隔离 PostgreSQL 实例的独立随机数据库中前向建立，再验证对应历史保护和前向升级。应用迁移与生产保护代码保持原样。
- 旧前端测试补齐账号上下文，检查稳定的请求身份和原有提示、重试及权限边界。
- PostgreSQL 全量实际复现交易单位顺序反转。断言逐项匹配交易单位与基础数量，仍核对预留和出货。
- Windows 设置测试的子进程输出固定为 UTF-8，读取端使用相同编码。0114 主体替换用例使用历史模型建立资料，跨 0115 仍比较原指纹。签名回执、保留规则需要可执行的 OpenSSL，运行时显式指定已有 OpenSSL 3.5.6。
- 银行事件确认后保留已确认详情。财务流水筛选在 125% 缩放下提前换行，资金复核窄屏显示来源和带币种的金额，历史更正字段在用户修改后清除对应旧提示。

## 数据库升级证据

`git diff --exit-code 019367baa389c2a73ea2d8c58162313e4868fcca HEAD -- backend/crm/models.py backend/crm/migrations backend/config/settings.py .github` 用于关联 [三入口既有证据](../release-integration-repair-01/POSTGRES-019367-EVIDENCE.md)。既有结果覆盖空库至 0128、c978 至 0128、c90 至 0128，并核对合成的现金拆分、抹零更正、缺汇率、凭证与抵减、历史快照和迁移记录。以下本轮运行与该证据分开记录。[源码差异校验原文](source-diff-verification.txt)

## 执行记录

本轮使用 Windows zh-CN、Python 3.14.5、Django 6.0.9 和隔离 PostgreSQL 17.11（psycopg 3.3.6）。前端使用 Node 24.16.0 和 npm 11.13.0。浏览器使用本机 Chrome 156.0.8078.80、Django 6.0.8 和隔离 SQLite，真实登录 `codex`，开发身份关闭。所有应用数据为合成样本。

| 命令 | 结果 |
| --- | --- |
| `python manage.py test crm.tests.test_finance_receipt_convergence crm.tests.test_finance_closeout.FinanceBankReturnConcurrencyTests crm.tests.test_receipt_refund_attribution crm.tests.test_cash_events crm.tests.test_reporting crm.tests.test_history_takeover --noinput -v 2` | 集成接口提交 `62245cfc` 上 123 项通过，0 跳过。覆盖作废与审计回滚、原币退款日期与跨日重放、重复提交、来源占用及历史承接锁。其后后端业务源码差异为空。[原始输出](logs/postgres-targeted.txt) |
| `python manage.py test crm.tests.test_database_settings crm.tests.test_party_replacement_migration --noinput -v 2` | 17 通过，0 跳过。Windows 环境启动配置与主体更正指纹。[原始输出](logs/postgres-encoding-party.txt) |
| `python manage.py test crm.tests.test_operations_receipt crm.tests.test_operations_retention crm.tests.test_trade_units --noinput -v 2` | 31 通过，0 跳过。使用实际 OpenSSL。[原始输出](logs/postgres-crypto-trade.txt) |
| `python manage.py test --noinput -v 2` | 业务后端 `eb316cfa` 上使用全新隔离 PostgreSQL、`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、显式 `OPS_TEST_OPENSSL`。后续候选到 `d4f90b92` 的 `git diff --exit-code eb316cfa d4f90b92 -- backend` 无差异。 |
| `npm run test:unit` 与 `node --test tests/detail-drawer-typography.spec.js` | 分别 197 和 1 通过，0 失败。后续候选新增资金复核 CSS 与 Playwright 视觉断言。[Node 输出](logs/node-qualified.txt) [排版用例](logs/node-detail-qualified.txt) |
| `npm exec --no -- vitest run tests src --environment jsdom --exclude '**/*.test.js' --exclude '**/browser-tests/**' --exclude '**/infrastructure-tests/**' --exclude '**/detail-drawer-typography.spec.js' --maxWorkers=2` | 业务候选 `d4f90b92` 上 89 文件、829 项通过，0 失败。Node 原生用例和 Playwright 用例由各自运行器独立执行。[原始输出](logs/vitest-delivery.txt) |
| `npm run build` | 业务候选 `d4f90b92` 上通过。Vite 报告主包体积警告。[原始输出](logs/build-delivery.txt) |
| `node scripts/run-isolated-browser-tests.mjs --business-test sales-order-import-real.spec.js` | 业务候选 `d4f90b92` 上 11 通过。使用真实账号，保留 Chrome 页面截图及浏览器实际下载。[原始输出](logs/chrome-delivery.txt) |

原始输出中只遮蔽临时运行时校验令牌，保留成功、失败和跳过结果。旧 SQLite 全量为 1746 项，6 失败、57 错误、119 跳过。[旧 SQLite 输出](logs/sqlite-baseline.txt) 旧 PostgreSQL 诊断为 1749 项，6 失败、15 错误、38 跳过。[旧 PostgreSQL 输出](logs/postgres-full-first.txt)旧环境包含 Windows 编码、依赖与数据库污染等独立问题，见本报告归因；这些记录不作为最终通过结果。

## 浏览器文件

- [真实下载清单](download-manifest.json)记录实际 XLSX 和 CSV 的字节数及 SHA256，样本均由隔离页面触发下载。
- [原生缩放测量](browser/sales-order-import-real.spec/native-zoom-results.json)覆盖 1366×768、1440×900、390×844，按 100% 和 125% 分别记录收款编辑和历史更正。收款扣减、订单计划、历史字段校验和提交按钮为实际页面状态。
- [收款编辑 125%](browser/sales-order-import-real.spec/receipt-edit-390-zoom-125.png)、[中文更正 125%](browser/sales-order-import-real.spec/history-correction-390-zoom-125.png)、[实际退款日期](browser/sales-order-import-real.spec/refund-actual-date-390.png)、[待确认收款恢复](browser/sales-order-import-real.spec/receipt-pending-recovered-390.png)、[银行资金已确认](browser/sales-order-import-real.spec/funds-reviewed-390.png)。

退款、待确认恢复、资金搜索、待复核与已确认状态另有 1366、1440、390px 的 100% 截图。窄屏复核断言包含金额表格可见、侧栏收起及主要操作可达。

## 恢复与正式环境边界

本轮在 `6460141d` 执行 `python backend/operations_pg_acceptance.py --postgres-bin <PG17-bin> --gpg <gpg.exe> --openssl <openssl.exe> --msys-paths`，实际 PostgreSQL、GnuPG 2.4.9 和 OpenSSL 3.5.6。合成恢复、附件和凭证校验、审计保护、并发锁、加密备份及签名保留均通过，脚本清理完成。[原始输出](logs/postgres-encrypted-restore-final.txt) 前一次隔离尝试因 Windows 受限令牌未能启动 pg_ctl。隔离限制外的一次性集群复验通过。既有 [C 包演练](../attachments-recovery-hardening-01/final-candidate-pg17-crypto-20261110.md) 仍保留。

本轮恢复演练的媒体栅栏为模拟，本地副本位于同一故障域。正式媒体 ACL、异地副本、正式调度和真实历史资料继续待验。

CI 为 `NOT_RUN`，生产部署及正式资料导入未执行。目标媒体权限、异地副本、实际调度和真实历史资料继续待验。完整打印及分页视觉验收保留既有延期范围。

## 最终业务候选

业务提交 `d836ba21a657a3a61b770a1d124a5b1fb62a9f46`。本节补充前述候选证据。最终证据提交仅修改 `docs/`。

- 财务恢复记录按业务目标索引，响应只清理自己提交的快照。采购付款、计划收付、收款、分配、退款、作废、资金登记和确认统一检查操作快照。两个真实工作区分别收到迟到成功或迟到失败时，后续操作仍可关闭重开并恢复。
- 权限刷新期间保留已知账号边界，初次挂载时尚无账号的组件延迟绑定。真实权限加载复验同账号恢复后提交、权限刷新失败时不发送写入，以及换账号时拒绝使用原账号的操作。提示区分账号验证与存储失败。
- 旧历史更正的额外资料可在审核轨迹展开，包含嵌套明细与零值。新申请维持中文业务表单。
- PostgreSQL 锁测试轮询前清除 PostgreSQL 统计快照，解决全量中事务内重复读取旧锁等待视图导致的假超时。仍等待实际阻塞方 PID。此项仅调整测试探测。
- 对比既有升级证据提交 `019367baa389c2a73ea2d8c58162313e4868fcca`，模型、迁移、数据库配置和 GitHub Actions 无差异。空库、c978、c90 的旧证据按源码差异关联。

| 验证 | 最终候选结果 |
| --- | --- |
| Windows，PostgreSQL 17.11，Python 3.14.5，Django 6.0.9，psycopg 3.3.6。隔离连接，指定 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、`OPS_TEST_OPENSSL`，运行 `python manage.py test --noinput -v 2` | 1771 项，1733 通过，38 跳过，0 失败，0 错误。[原始输出](logs/a2-recovery-full.txt) |
| 相同 PostgreSQL 环境，`python manage.py test crm.tests.test_finance_integration_lock_order crm.tests.test_finance_receipt_convergence crm.tests.test_cash_events --noinput -v 2` | 67 项通过，0 失败、0 跳过。实际执行锁顺序、竞争占用、重放、作废及审计回滚。[原始输出](logs/a2-recovery-pg.txt) |
| Vitest，`node node_modules/vitest/vitest.mjs run src/components/PurchasePaymentModal.spec.js src/composables/useFinanceAttempts.spec.js --environment jsdom --pool=threads --maxWorkers=1` | 12 通过。使用真实工作区 API 封装、存储组合函数与权限加载，网络响应可控。随后改动只涉及历史更正界面及测试。[原始输出](logs/a2-recovery-confirmed.txt) |
| `npm run build` | 通过，Vite 主包体积警告仍在。[原始输出](logs/a2-final-build.txt) |

[38 个跳过项逐条记录](logs/a2-postgres-skips.txt)。SQLite 专属文件恢复用例在独立 SQLite 运行中补验；涉及真实 PostgreSQL 命令和备份演练的场景另有专用隔离集群、加密恢复证据。Windows 符号链接和 POSIX 权限项仍保留相应平台边界。

Node 24.16.0 下 `npm run test:unit` 197 项通过，`node --test tests/detail-drawer-typography.spec.js` 1 项通过。Node 测试自动启动独立的无界面 Chromium 进行隔离基础设施自检，页面验收使用内置浏览器。[Node 输出](logs/a2-final-node.txt) [排版输出](logs/a2-final-node-detail.txt)

Vitest 全量 89 文件、834 项通过，0 失败、0 跳过。复跑的 worker 池设置不同，结果一致。

- `node node_modules/vitest/vitest.mjs run tests src --environment jsdom --exclude '**/*.test.js' --exclude '**/detail-drawer-typography.spec.js' --pool=threads --maxWorkers=1`。[原始输出](logs/a2-final-vitest.txt)
- `node node_modules/vitest/vitest.mjs run tests src --environment jsdom --exclude '**/*.test.js' --exclude '**/browser-tests/**' --exclude '**/infrastructure-tests/**' --exclude '**/detail-drawer-typography.spec.js' --maxWorkers=2 --reporter=verbose`。[逐项输出](logs/a2-final-vitest-verbose.txt)

### 内置浏览器复验

按用户最新要求使用 ChatGPT 内置浏览器，真实登录 `codex`。沿用隔离运行器建立新 SQLite 和独立媒体目录，使用合成业务资料，保留所有隔离校验和测试种子。临时副本只将浏览器自动化阶段替换为等待手动验收，以避免启动桌面 Chrome。首次连接超时，随后一轮遗漏账号种子开关。第三和第四轮业务种子拒绝非允许输出路径。最后一次指定 `ISOLATED_CODEX_TEST_SUPERADMIN=1` 和 `ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT` 后，使用 `node scripts/a2-iab-verified.local.mjs --business-test sales-order-import-real.spec.js` 成功启动。临时副本已清理。[隔离及 API 原始输出](logs/a2-iab-verified.txt)

| 最终业务候选实测 | 结果 |
| --- | --- |
| 多扣减、多订单、多计划收款编辑 | 1366×768、1440×900、390×844。长客户名、长单号、两个扣减及两个核销金额均进入实际表单。窄屏可局部滚动至保存，保存尝试正确提示扣减缺依据凭证。 |
| 历史中文更正 | 三个视口实测主要按钮位置。窄屏实测缺失明细提示、填写、提交和审核，隔离 API 两次写入均返回 200。提交状态画面页头与工作区间无正文露出。旧补充资料由最终组件测试验证。 |
| 银行资金记录 | 实际登记表单打开，业务来源搜索可输入。当前隔离样本没有可选来源，复核与待确认恢复未在最终候选完成。 |
| 下载 | 点击历史承接模板后，内置浏览器等待下载事件超时。最终候选缺实际文件复验；此前 Chrome 的实际 XLSX/CSV 文件证据和 SHA256 仍归属 `d4f90b92`。 |
| 剩余浏览器覆盖 | 内置浏览器视口 API 只支持宽高，本轮未验证最终候选 125% 原生缩放。采购付款和计划收付恢复、退款日期、作废恢复、结汇待确认恢复、跨账号／会话失效仍缺最终候选同版本浏览器覆盖。 |

内置浏览器截图记录在当前验收对话中，未生成可提交的本地截图文件。仓库所附实际 Chrome 截图和下载清单归属 `d4f90b92`，与最终候选的差异单列。[早期截图与测量](browser/sales-order-import-real.spec/native-zoom-results.json) [源码差异](source-diff-verification.txt)

状态为待独立复审。GitHub Actions 为 `NOT_RUN`。正式媒体权限、异地副本、正式调度、真实历史资料、完整打印与分页验收保留既有状态。生产部署、正式导入均未执行。

### 网络超时后的内置浏览器复验

同一业务候选 `d836ba21a657a3a61b770a1d124a5b1fb62a9f46`，通过隔离运行器临时副本执行 `node scripts/a2-iab-recheck.local.mjs --business-test sales-order-import-real.spec.js`，以等待内置浏览器操作替代 Playwright 阶段。使用独立 SQLite、媒体目录与合成资料，`codex` 登录返回 200。

- 从历史承接点击下载模板，隔离服务返回 HTTP 200、14337 字节。从财务概览点击导出 CSV，隔离服务返回 HTTP 200、592 字节。两次请求均来自实际页面操作，最终候选的浏览器落盘文件仍未取得。现有早期候选实际文件和哈希继续有效。
- 财务流水成功保存 USD 100 合成客户收款，返回 201，界面显示已核销。打开原流水退款表单，实测日期 2026-10-30、关联订单和 USD 10 金额。截图在验收对话。凭证上传未观察到成功反馈，退款提交与回读仍待验。
- 隔离运行器清理服务、数据库与媒体目录。此记录仅追加本次已观测结果，原有待复审项仍可在本报告中核对。

[脱敏隔离运行及 HTTP 日志](logs/a2-iab-download-recheck.txt)

### 导出文件内容补验

业务提交 `d836ba21a657a3a61b770a1d124a5b1fb62a9f46`。Windows 上沿用隔离运行器与合成业务种子，使用独立 SQLite、媒体目录和真实 `codex` 登录。临时运行器将 Playwright 阶段替换为等待内置浏览器。使用 Python 标准库 `urllib.request` 和 CookieJar，经 Vite 本机代理登录并将两个 HTTP 附件响应写入文件。XLSX 用 `zipfile.ZipFile.testzip()` 检验完整性并确认工作簿结构，CSV 以 UTF-8 BOM 兼容解码后由 `csv.reader` 解析。

- 历史承接 XLSX 返回 200，14338 字节。财务概览 CSV 返回 200，592 字节，SHA256 与此前 Chrome 实际下载样本一致。[文件与校验清单](http-downloads/manifest.json)
- 内置浏览器导航仍超时，运行器随后因 Vite 代理身份校验超时退出并清理环境。本轮文件来自认证 HTTP 请求。最终候选的浏览器落盘、退款凭证上传后的登记与回读，以及此前列明的浏览器场景继续待验。[脱敏运行日志](logs/a2-gap-http.txt)
