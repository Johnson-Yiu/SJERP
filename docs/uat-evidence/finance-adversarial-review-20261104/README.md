# FINANCE-ADVERSARIAL-REVIEW-02

基线 **8087f2c68b19a302a25e814ec8ce6113d91d4750**；独立分支 `codex/finance-adversarial-review-20261104`。本轮是开发侧反例验证，**不是 ChatGPT 独立复审，不是财务验收全部通过**。确认缺陷保持未修，交统一集成协调。本包不改公共财务服务、契约、模型、迁移、前端、CI及共享台账，不启用运行环境正式RBAC，不处理真实资金。

## 阅读与来源

- `AGENTS.md`、`PROJECT_ISSUES.md`、`PROJECT_PHASES.md`、`REVIEW_PROTOCOL.md`；遵循最新开发超级管理员及独立工作树规则。公共台账由协调任务维护，本报告提供登记建议，不关闭或重建现有Issue。
- ISS-105/108当前记录为 FIXED_PENDING_REVIEW；旧 OPEN/BLOCKED 仅保留历史。此前开发侧通过和CI不等同本轮全部反例通过。
- 财务来源 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd` 的 `finance-closeout-batch-20261104/CONTRACT-v1.md`、验收报告及当前实现/测试。
- `review-integration-batch-20261104/README.md`、`DELIVERY-STATUS.md`、`MERGE-RECORD.md` 与现有0103汇合迁移；不合入历史包移动HEAD，不重复已通过的备份恢复/打印业务。
- 当前用户本包和 FINANCE-CLOSEOUT-BATCH-01 已明确的资金原则是验收依据，不重新把内部转账、待分类、来源不明真实扣款、双人更正等列为业务待决。
- 只读核对本机2026-10-24规则包的原ISS-108移交原文（`既有移交原件_2026-10-20/12_ISS-108_银行撤回、商业退款与资金更正.md`）：原事实保留、实际发生期、录入错误不是差额支出、核销关系精确追溯等既有结论不改写。该本机材料未复制或提交；历史已确认核销恢复、零净到账等不因本轮未覆盖而重新变成业务待决。

## 确认缺陷（均未修）

| 本包编号 | 预期与实际 | 影响与证据 |
|---|---|---|
| ADV-01 / P1 | 原本金事实先追加分类为 `expense` 后，详情已显示有效性质为 expense；再调用 `/transfers/` 应拒绝旧性质匹配，实际201成功。 | 同一有效分类的真实支出可从公司毛流量隐藏。`defect_repros.py::test_adv01_*`，SQLite与真实PG失败，`defect-api/`和`defect-pg-api/`保存匹配响应、实际API、CSV和事实明细。本金金额和账户余额不变并不能证明公司统计正确。 |
| ADV-02 / P2 | 账户期末余额53核对完成后，补充本金配对；余额仍53，但本轮要求内部配对变化重新核对，实际状态仍completed。 | `balance()`指纹包含事实/更正/分类，没有两种本金匹配。`test_adv02_*`，SQLite和真实PG失败；原review和余额均保留，不能宣称重核状态正确。 |
| ADV-03 / P1（正式权限启用前门槛） | 合成普通认证角色有finance/transactions的view/create/update及全局范围，应该进入preview并得到受控的隐藏候选提示；实际通用权限层403。 | `/finance-ledger/`无permission_module，PATH_MODULES亦无此路由；ModuleActionPermission对未知模块默认拒绝。开发超级管理员/真实superuser测试掩盖此缺口。`test_adv03_*`保留200期望与实际403，不启用真实服务RBAC。不是数据泄漏；是授权角色不可用。 |

完整最小建议见 [PATCH-SUGGESTIONS.md](PATCH-SUGGESTIONS.md)。编号只用于本包定位，建议挂接ISS-105/108及权限设计历史项，由协调任务核对是否已有登记；不擅自创建重复Issue或关闭原项。

**失败复现如何交付：** `defect_repros.py` 位于专属报告目录，显式命令执行仍应exit 1。没有expectedFailure、skip或把断言改成当前错误结果。常规CI不会自动发现该报告目录中的显式复现模块，因此三项CI绿色只表示常规回归通过，**不解除这三项缺陷**。原因是本包明确无权修改公共服务，不能把未修反例包装成通过。原始失败日志随分支保留。

## 六类范围及实际证据

| 范围 | 通过/未复现范围 | 明确保留 |
|---|---|---|
| 多期更正 | 113.27收入→跨月81.09支出→跨月零更正→72.08收入；原期、新期、累计余额、实际API、报表净额、CSV有效行及逐笔详情一致，原数据库全部字段不变；无差额付款。 | 只覆盖给定链，不代表所有历史坏数据已修。 |
| 内部转账 | 跨日47/79/52本金、新旧混合本金、独立1.23手续费、重复匹配不重复审计；匹配与更正竞争、单端争抢两个对端实际PG通过。 | 分类后匹配与匹配后重核为ADV-01/02。混合历史匹配中有效分类的反例未单独复现，建议修复时覆盖同一语义。 |
| 退款及退回 | 跨批准80+60相对93原收款累计超额47；逐订单批准50不能支付40后再分11；退款后21+39退回和多0.01拒绝；两笔70银行退回争抢100上限；批准取消/实际支付竞争保持真实扣款；未知结果不能假失败，原键重试不再记账。 | 原来源不明的refund_payment关联流程仍拒绝，但通过独立cash、commercial_refund性质实际记入29.91，不猜原收款、不自动核销；不能把关联拒绝误报为真实扣款必然丢失。暂无此丢失反例。 |
| 基准/核对 | 正20/负20/零基准、当日3.71变动、早于基准拒绝；跨期更正、迟到记录、分类变化重核；核对和迟到记账竞争、两次独立核对不改资金。 | 本金匹配变化漏重核ADV-02。未设置真实日期、余额、账户。 |
| 真实性/持久层 | 全7种kind对simulated/needs_verification的preview/save、批准和过账边界逐项检查；API拒绝过账，无FinanceFact。FinanceFact QuerySet.update拒绝；批准内容经可信ORM故障注入后，post凭摘要拒绝且无事实/审计副作用。 | bulk_create可由可信ORM插入模拟行（探针事务强制回滚），尚无当前受支持外部写路径；归为防御性约束缺口，不称API漏洞。详见REACHABILITY。 |
| 审批/权限/文件/审计 | 自批拒绝；API没有覆盖已批准内容/删除事实路径；替换同大小不同摘要、改大小、删除凭证时记账/下载拒绝；post/transfer/review审计故障全部回滚。无权列表/详情/下载/CSV 403，真实TCP HTTP会话+CSRF双人流程及文件字节/no-store通过。 | 授权普通角色正向HTTP为ADV-03。隐藏来源服务层只返回restricted、空ids/token并409拒绝，原订单和流水不变；因ADV-03不能声称其授权HTTP全链通过。 |

`api/`、`postgres-api/` 是逐项HTTP视图请求/响应、实际CSV文本、金额、账户及前后不变断言的合成证据。`transport=real_tcp_http` 为LiveServer+urllib真实环回网络，其他APIClient证据明确为Django HTTP视图测试，不冒充外部浏览器或生产流量。线程日志保存各请求不同pg_backend_pid；最终状态全部重新查库，无旧ORM对象假通过。两种测试都无网络mock。

本轮无可见UI改动，不新增Chrome成功路径截图；最终CI运行现有完整前端/浏览器套件，不能替代本包三个失败反例或生产验收。

## 测试命令、环境与日志

实际锁定解释器、16个pin匹配结果见 `versions.log`，Django6.0.9/psycopg3.3.6；PG17.11独立随机集群。原始日志均保留（包括首轮测试夹具错误），命令及退出语义见 [COMMANDS.md](COMMANDS.md)，最终数量从实际日志交付，不预写通过。

| 实际运行 | 结果 | 日志 |
|---|---|---|
| SQLite 新增+既有相关组合 | 55项，48通过，7个真实PG条件跳过，exit 0 | sqlite-release.log |
| 真实PG17.11新增专属验证 | 26项全部实际执行通过，0跳过，exit 0；含7组独立连接竞争、2项真实TCP HTTP | postgres-release.log |
| SQLite 三项未修反例 | 3项全部按原规则断言失败，exit 1 | defects-final-sqlite.log |
| 真实PG17.11三项未修反例 | 3项全部按原规则断言失败，exit 1；测试库销毁、cleanup complete | defects-release-postgres.log |
| Django检查/迁移一致性 | exit 0，无遗漏迁移；未新增或改动模型/迁移 | django-check.log / migration-check.log |

CI运行现有完整Backend/PostgreSQL/Frontend，最终精确SHA及三Job状态在交付正文列出；即使常规CI三绿，本报告结论仍为**存在三个确认缺陷，待统一集成补修**。

- 常规新增专属测试：`backend/crm/tests/test_finance_adversarial_review.py`、`test_finance_adversarial_concurrency.py`、`test_finance_adversarial_http.py`。
- 正常/反例PG入口：`run_postgres.py` / `--reproduce-defects`；只启动新随机集群，独立媒体，随机源/测试库，校验data_directory，确认测试库销毁，停止并清理自有集群。失败exit不伪装为0。
- 历次日志不覆盖：sqlite-first/corrected-harness/expanded记录测试夹具修正及授权角色真实失败；sqlite-release、postgres-release是冻结专属测试后的复验；defects-final-sqlite、defects-release-postgres为未修反例。
- 夹具问题明确与产品区分：长测试名文件超过Windows路径长度，改哈希短名（完整test id保留JSON）；Customer字段/Order日期按模型修正；ORM `_state`对象地址不能作历史字段比较，改`.values()`全字段；报表`amount`原合同为收入减支出的有符号净额（reporting.py 83/146），首轮误当毛额，毛额API/CSV逐方向断言完整保留。没有借此改动三项业务缺陷的期望。

## 可达性与后续协调

见 [REACHABILITY.md](REACHABILITY.md) 及可重跑的 `audit_reachability.py` / `reachability.json`。本轮未改历史包执行器；当前固定基线无历史资金接通路径。之后历史包接入必须重新核对实际调用SHA、仅调用资金服务、真实性、来源幂等、两人审批及同事务审计，不能把本包静态结论推广至未来代码。

交付状态：审查完成后提供精确SHA三项CI；三个产品缺陷仍由统一集成任务接收处理。正式账户、银行真伪、生产DB权限/媒体/代理/运维、真实资金和历史资料未核验；本包未遇真实外部资金依赖，不把未授权生产操作写成本地任务已完成。不得据此宣布上线就绪。

其他未覆盖：全类型原始历史坏数据、跨年度历史迁移后重新核实、精确核销恢复及零净到账完整组合、线上存储灾难恢复、对所有动态扩展/外部任务的可达性。上述不是新发现或业务待决；应沿用既有Issue和已确认规则继续验收，不能由本轮局部通过整体关闭ISS-105/108。退款/撤回后来源不明不自动释放，现有合成来源关联并不等于真实银行真实性。
