# FINANCE-CLOSEOUT-BATCH-01

统一基线：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`。专属分支 `codex/finance-closeout-batch-20261104`，独立工作树。实施成果待集中独立复审；不自行关闭 ISS-105/108/121，也不代表上线就绪。公共台账、AGENTS 和 CI workflow 未修改。

## 业务成果

| 子项 | 实施及验收边界 |
|---|---|
| 账户体系 | 明确银行/现金、自有/外部/待核实，名称不推断归属；依据留痕核实后才能记账。旧银行受控标识显式映射，银行不能映射成现金；已有历史不能直接改写账户归属。 |
| 性质与确认 | 性质待分类和凭证/真实性待确认分别表达；核实后的未知性质实际资金仍统计。利息、借款、注资、手续费、收入、支出、退款及超额性质保留。分类追加历史，既有分类不覆盖。 |
| 内部转账 | 明确指定不同自有账户的实际两端，允许跨日；本金同额才核实排除公司毛流量，账户变动保留，手续费单独记录。差额不当手续费，不补造另一端，不同日同额不自动配对。也支持明确映射后的原银行两端及新旧混合引用，文件逐端绑定，不复制旧事实。 |
| 启用余额 | 独立、经另一人复核的日期开始时点基准，不是新收入；零、正负余额可复算，银行/现金分开。只有合成日期、资料、余额用于验收，没有配置真实启用日或真实账户。 |
| 逐账户核对 | 期间、对账单文件、复算余额、差异、处理依据、人、时间和完成状态；有差异不能完成。迟到记录、日期/金额更正及期间内分类核实使指纹变化，保留原核对记录并返回需核对状态。 |
| 退回/商业退款 | 银行退回可部分、累计受限；原始事实保留，旧来源额度不释放。批准本身不产生流出；实际扣款关联有效批准并复核，累计及逐订单分配受限，未知归属待分配。超额退款独立金额字段，不以外币折算作实际扣款；扣款后退回保留两笔事实。 |
| 更正与审批 | 真实认证发起人不能自批；另一授权人复核。取消/失败及修订留痕重审，开发身份不伪装两个人。更正填核实后的完整金额/日期/方向，原版本保留，实际统计取有效版本，不制造差额银行流出。依赖已有退款或本金核实的危险改写继续拒绝，不自动解除来源。 |
| 凭证、审计与统计 | 实际私有文件由系统计算/重验 SHA256，限额流式保护；旧银行新确认也必须绑定真实文件，手填 SHA 不足以确认。银行文件按原批次来源鉴权，不混入公司账户文件列表。登记/确认/取消/失败/分类/匹配/核对与 OperationLog 同事务。概览、实际 API、报表、CSV 和带日期恢复的下钻共享有效事实口径。旧账面折算、原业务流水、订单、付款计划、库存不重算。 |

完整可调用跨包边界、字段及合成示例见 [CONTRACT-v1.md](CONTRACT-v1.md)。`CONTRACT-DRAFT.md` 与 `PROGRESS.md` 保留了早期尚未实施时的记录，不能作为当前完成状态。历史迁移包只能经资金服务承接，不能直接写资金表；本包没有实现或执行历史迁移器。

## 迁移和历史

新增 `0098_finance_accounts`、`0099_finance_closeout_workflows`、`0100_finance_legacy_fact_links`、`0101_finance_historical_transfer_links`、`0102_bank_private_voucher_binding`，全部在原0097叶节点上增量发展，没有修改已发布迁移。

新库 SQLite 迁移成功，空库可安全回退至0097再正向恢复。有账户、资金、私有凭证或历史绑定数据时相应回退保护拒绝删除；实测拒绝前后记录和文件一致。原0096银行重复审计回退保护保留，其测试同时验证原拒绝函数和新链上更早发生的私有凭证保护，未用新保护替代旧断言。PostgreSQL 的原重复审计 SQL UPDATE/DELETE/TRUNCATE 保护继续实际测试。

已确认旧银行记录保留原人工凭证引用，未自动补造文件、核实身份或历史日期；无文件的历史数据标记 `historical_manual_reference_only`。新增确认需实际文件；原待确认草稿可以留痕绑定文件，不能覆盖已确认历史。资金更正及银行退回不自动释放 `CashSourceAllocation`，也不修改旧 Transaction、应收应付或库存。

## 已执行验证

本机锁定环境：CPython 3.14.5、Django6.0.9，16项依赖pin全部匹配 `requirements.lock`，pip check通过；Node24.16.0、npm11.13.0，npm ci按锁文件安装。CI 使用 Python3.12/Node22，另行核实最终精确SHA。

| 检查 | 记录 |
|---|---|
| 早期完整 SQLite 回归 | 1207项，55条件跳过，无失败；`backend-full-first.log`。执行发生在后续文件绑定/有效更正补修之前，不当作最终源码的完整回归。 |
| 最终金融组合 SQLite | `sqlite-ci-migration-verified.log`：80项，6项PG条件跳过，无失败，包含CSV审计迁移回退与资金回归。PG条件跳过不计为并发通过。 |
| 稳定业务源码真实 PG17.11 | `postgres-ci-migration-verified.log`：88项全部实际执行，无跳过和失败；含CSV审计迁移回退、5项新并发、旧资金并发、银行重复核实SQL保护和迁移回退。随机测试库无遗留，集群停止并清理。此前85项定向记录保留。 |
| 新库和正反向迁移 | `migration-verification.log`：新库到0102、空回退至0097及再正向通过；有银行文件时拒绝回退，历史及实际文件不变。 |
| Django check / 模型迁移一致性 | 检查通过，makemigrations --check --dry-run无遗漏。 |
| 前端单元 | `vitest-acceptance.log`：70文件684项通过；`node-final-verified.log`：177项通过，0失败、0取消。刷新布局补修后本页3项再次通过。 |
| 构建 | `build-release.log`：通过，保留既有主包体积警告，不宣称性能验收完成。 |
| 真实 Chrome | 系统Chrome、独立SQLite/媒体、无mock。普通账户1440/390、认证双人闭环1440/390、旧独立手续费1440/390及真实API、旧重复候选1440/390均执行。成功及失败日志均保留；最终重跑文件为 `chrome-*-acceptance` / `chrome-*-final` 及银行专项日志。 |

截图和实际 CSV/PDF/HTTP 在 `browser/`、`bank-fee-release/`、`bank-duplicates-browser/`；`bank-fee-browser/`保留窄屏SHA换行补修前的历史截图。认证测试通过真实合成用户会话切换操作，两人ID不同；会话密钥只在临时运行目录中存在，未提交。核心业务表在实际HTTP前后比较哈希与记录数，见 `authenticated-http-*.json`，确认无订单、采购、库存、付款计划及旧业务流水写入。上传文件为清晰标注合成的有效PDF，不是真实银行凭证。

实际命令：

```text
python -m pip check
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python docs/uat-evidence/finance-closeout-batch-20261104/verify-migrations.py
python docs/uat-evidence/finance-closeout-batch-20261104/run-postgres-tests.py --pg-bin <本机PG17工具目录>
cd backend && python manage.py test --verbosity 1
cd frontend && npm ci --no-audit --no-fund
cd frontend && npm run test:unit
cd frontend && npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers=2
cd frontend && npm run build
cd frontend && node scripts/run-isolated-browser-tests.mjs --business-test finance-closeout.spec.js
cd frontend && node scripts/run-isolated-browser-tests.mjs --business-test finance-closeout-approval.spec.js
cd frontend && node scripts/run-isolated-browser-tests.mjs --business-test independent-bank-fee-real.spec.js
cd frontend && node scripts/run-isolated-browser-tests.mjs --business-test cash-duplicate-real.spec.js
git diff --check
```

本机使用上述锁定Python虚拟环境，设置development、隔离数据库和临时媒体。浏览器入口通过 `ISOLATED_TEST_PYTHON` 指向该解释器；认证测试只加入该运行自有Vite端口的精确CSRF可信来源，保持CSRF保护。需要合成夹具的入口校验运行标记、SQLite路径及媒体目录；PG脚本只初始化新的本地随机集群，不连接已有服务。

## 本轮失败分类与修正

- 前两次执行过早停止属于执行问题，未记录为外部BLOCKED；本轮继续实施全部工作包，没有只交付审查报告。
- Chrome初轮标题定位歧义，随后下拉框名称包含选项文字；限定页面区域并为产品选择器补明确无障碍名，没有删除业务断言或延长等待掩盖失败。
- 变更迁移过程中启动的一轮浏览器运行在迁移一致性检查处拒绝，未计为通过；迁移完成后重新运行。
- 认证真实UI的403明确为隔离Vite随机Origin不在可信来源；只配置本次自身Origin，未关闭CSRF。另一轮新测试写了JavaScript无效布尔值，修正脚本后重跑。
- 初轮Vitest导航契约遗漏新入口并有worker启动超时；保留原导航项、加新入口，并以受控并行度重跑全70文件，684项通过。Node并行隔离运行器的一轮超时保留为取消，不记通过，按最终重跑及CI结果交付。
- 新PG下载测试直接close流式响应导致测试事务连接被关闭，改为消费Django测试客户端流式迭代器并验证真实文件内容；新集群重跑通过，未更改生产数据库或清理机制。
- 人工更正的初版差额流出会歪曲毛流量，已改成不可覆盖历史及有效版本统计，并覆盖跨期更正、零更正和并发分叉拒绝。
- 390px实际截图发现银行文件SHA长串溢出，已加换行并增加真实Chrome宽度断言；截图不拼接、不重制。
- CI Run 41812921711及41813412575的PostgreSQL全量各有5项错误：CSV审计回退拒绝测试先撤销新财务空表，再触发旧保护；测试没有恢复最新schema，导致后续并发测试缺表。补充finally恢复全部叶节点并断言恢复，原审计拒绝及历史保留断言不变。锁定PG顺序组合88项全部通过，完整CI另行重跑；失败原始日志见ci-postgres-first。
- 全量浏览器的两项认证资金测试缺少夹具环境路径：单文件入口已准备，套件入口白名单遗漏。补入套件初始化及包含/排除回归断言，不删除测试。`chrome-suite-mode.log`使用真实all-business-tests入口，明确排除其他文件，仅四项资金场景，全部通过；这不是本地完整浏览器全量通过。Node再次177项通过。旧CI其余229项业务浏览器通过，完整CI仍以最终SHA重跑为准，失败原始日志见ci-frontend-first。
- 收尾环境复核发现共享根目录虚拟环境为Django6.0.8，不作为锁定环境验收；改用既有锁定解释器`iss018-command-locked-venv`（Django6.0.9），重跑check、迁移检查、SQLite、PG及普通/双人Chrome。对应chrome-locked-auth和chrome-locked-account各2项通过。启动PG时沙箱受限令牌失败，经授权在沙箱外只启动新随机集群后通过；未接触既有服务。

## CI 与交付边界

使用普通提交、正常推送现有工作流，核对同一最终精确SHA的 Backend、Backend PostgreSQL17、Frontend；最终Run ID、三个Job状态及实际执行数量随交付正文提供。CI未结束时不预写成功，不以跳过的PG专用场景冒充实际执行。

生产环境、真实账户/启用日/银行余额/凭证、正式RBAC、真实历史导入、生产代理及DB运行账号权限均未配置或操作。历史缺证不能由程序补齐；复杂已退款/已核实本金依赖的直接改写保持安全拒绝，需明确真实凭证和对应核实链，不能用猜测释放来源或冲销历史。完整工作包成果仍需独立业务、代码和视觉复审；不关闭原Issue、不合并master、不部署。

## 协调台账建议（本包不直接修改公共台账）

ISS-105/108：本包八项成果及增量迁移标记 FIXED_PENDING_REVIEW，依据本报告与 CONTRACT-v1，不整体关闭。ISS-121：资金承接服务契约已提供；正式迁移、真实凭证及启用余额仍须另行授权和核实。原未完成的生产权限、真实历史及部署验收门槛继续保留。

原始日志保留本地，提交的 *.redacted.log 仅隐藏一次性隔离身份并清理行尾空白，原文SHA256及发布文件SHA256见 evidence-manifest.json。不会把历史失败改写为通过。

视觉后续项：认证合成长用户名在390px全页截图左下方可见既有全局侧栏页脚文字溢出；资金表单、刷新按钮、文件摘要及页面宽度已核实。本包未修改全局侧栏，建议全局布局任务单独核查。刷新后的截图已回到页首等待两帧，避免滚动时粘性栏被截到页面中部。
