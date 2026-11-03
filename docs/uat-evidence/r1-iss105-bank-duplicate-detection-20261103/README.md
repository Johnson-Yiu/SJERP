# ISS-105 银行事实疑似重复核实

基线：`a55469c1b07e4f13037c6644c69d8a35ef0496a0`。分支 `codex/r1-iss105-bank-duplicate-detection-20261103`；PostgreSQL 实测的代码提交为 `cc38433c6079c79ba0471543378e2f6ddfd8bc1a`。整体议题仍需集成验证和独立复审。

## 实现与边界

- 增量保存可选交易对手、银行摘要和银行交易标识；旧记录保持空值，不从客户主档补写。`bank_net_amount` 是人民币银行净额，币种固定 CNY；外币 `currency` 是来源币种，不是净额币种。
- 已确认事件中，同人民币账户、银行日期、方向及 CNY 净额相同，或同账户银行交易标识相同，即提示核对。交易对手、摘要和标识原样展示；缺项显示未提供。候选不等于重复，合法同额交易可经核实放行。
- PostgreSQL 确认事务取得核心特征事务级 advisory lock；有银行标识时另取得该标识的锁；随后在原来源和事件锁下重新查询。不同请求键、不同来源仍进入同一锁域。SQLite 不具备同等并发证明；不支持的数据库拒绝确认。
- 放行须有更新权限、当前候选令牌及非空说明；候选变化须重新核对，无权查看的候选阻止放行。`CashDuplicateReview` 与确认同事务保存候选 ID、说明、服务端身份及时间，应用层禁止修改或删除。已认证用户记录真实 user ID；开发身份仅标记开发超级管理员。记录不是现有 `OperationLog`；新增 PostgreSQL UPDATE/DELETE 和 TRUNCATE 触发器分别复用既有审计拒绝函数，历史记录存在时拒绝反向迁移。
- 隔离测试清理仅对已登记的随机测试库生效，并继续检查原三个 CSV 触发器；0096 已应用且新表存在时额外核查第四个触发器，迁移和表存在性不一致则拒绝清理。回退到 0095 时按原三张表执行。迁移名称若在集成时调整，须同步 `REVIEW_MIGRATION` 并回归。
- 按 [ISS-043 数据库权限方案](../../deployment/ISS-043-PostgreSQL审计防篡改.md)，部署前由 DBA 核对该表所有者和运行账号继承角色，运行账号只授予 SELECT/INSERT 及序列必要权限，撤销 UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER；运行账号不得为表所有者或超级用户。未修改任何实际数据库权限，权限和实际部署验证仍待完成。
- 未提供或为空的新增字段不改变旧请求哈希。保留来源额度、手续费父事件及银行净额统计口径；未处理内部转账、退款更正、启用余额或历史重分类。

## 验证

指定 CPython 3.12.16 / Django 6.0.9，`requirements.lock` 16 项逐项相符，`pip check` 无冲突；本工作树独立 `npm ci --no-audit --no-fund`。Django 使用内存 SQLite 与独立临时 MEDIA_ROOT；浏览器使用隔离启动器，迁移及 API、Vite、代理身份核对通过，使用系统 Chrome 与合成资料。

| 检查 | 实际结果 |
|---|---|
| Django 资金、实际报表及新增核实（首次护栏前） | 41 项，35 通过、6 项因需要 PostgreSQL 跳过；两个为跨来源并发用例，另一个为原始 SQL 审计保护测试 |
| 清理隔离、重复核实及 CSV 审计护栏补强后 | 49 项，37 通过、12 项真实 PostgreSQL 专属跳过；SQLite 覆盖迁移记录/表状态一致性、模拟清理路径和有历史时拒绝回退 |
| Django check / makemigrations --check --dry-run | 通过；新迁移 `0096_rmbcashevent_bank_counterparty_and_more` 待与 A 的迁移编号协调 |
| Node 单元全量 | 177 通过 |
| Vitest `tests/phase2a-list-shell.spec.js` | 22 通过 |
| Frontend build | 通过；主包保留大于 500 kB 警告 |
| Chrome + 真实隔离 API：重复候选 | 1440 和 390 两项通过；隔离数据库确认两条开发身份核实记录 |
| Chrome + 真实隔离 API：独立手续费 | 三项通过；两笔同额夹具改为不同银行日期以避免无意触发重复候选，原手续费断言保留 |
| 旧资金页面 mock 回归 | 8 项通过；不作为真实 API 证据 |
| PostgreSQL 17 | 本机无服务；改用 [隔离 PostgreSQL CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41615047577/job/125846286292)。全量 1131 项通过、21 项既有条件跳过；新增跨来源并发、跨日期同银行标识并发、原始 SQL UPDATE/DELETE/TRUNCATE 拒绝及反向迁移保护均实际执行。 |

新增测试覆盖不同键/来源、缺字段、合法放行、候选变化、无更新权限、认证用户与开发身份、审计插入和事件保存失败回滚。原同额测试增强为先拒绝再核实放行；未删除旧断言。两个 PostgreSQL `TransactionTestCase` 使用独立线程连接分别验证相同银行核心特征和相同银行标识跨日期，本机均跳过。

## 证据

- [1440px 真实 Chrome](screenshots/duplicate-review-1440.png)、[390px 真实 Chrome](screenshots/duplicate-review-390.png)：显示合成交易对手、摘要及交易标识，390px 截图已目视检查。
- [真实 API 响应](browser-http.json)、[隔离数据库记录](browser-database.json)、[数据库核对脚本](inspect_browser.py)。
- [原始日志包](execution-logs.zip) 包含 `backend-latest.txt`、`postgres-guard-local-final.txt` 原始输出及 `lock-versions.txt` 逐项版本核对。
- 首轮 Chrome 两视口失败，因测试未填写保留四位精度的旧来源分配金额，页面正确要求填写；失败快照在 `artifacts/6cffab08-5104-4efb-bc9f-dd59fba0cf21/`，补齐合成输入后重跑通过，没有增加超时。

复现：在 `frontend` 设置 `ISOLATED_TEST_PYTHON` 为用户指定解释器、`ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT` 为本报告目录后，执行 `node scripts/run-isolated-browser-tests.mjs --business-test cash-duplicate-real.spec.js`。数据库和服务由启动器创建、校验和清理。

审计插入失败时确认状态不变；审计插入后若事件保存失败，审计和事件状态整体回滚，两个路径均有隔离 SQLite 测试。整合后三项 CI、部署权限及独立复审仍待完成；不因此关闭 ISS-105。本机未连接业务数据库。
