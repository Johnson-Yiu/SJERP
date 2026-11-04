# 财务反例候选来源只读审查

## 范围与状态

- 固定基线：`8087f2c68b19a302a25e814ec8ce6113d91d4750`。
- 待审候选完整 SHA：`2e20bfdccb711bdd5f9028cb60e287ee742c77c5`，提交链为本报告下表的三笔提交。
- 审查时当前 worktree HEAD：`9af2a32fa81df3aa975424b70a887057e40b6b22`；审查前后相同。本次只读访问 Git 对象，没有 checkout、合并、移动 HEAD 或运行候选测试。
- 结果是开发侧来源/测试证据审查，不是 ChatGPT 独立复审。该候选尚未正式接收，等待明确稳定交付。

## 固定提交链

| 顺序 | 完整提交 SHA | 父提交 | 提交说明 |
|---|---|---|---|
| 1 | `648a0720ccadcfff04a3225783e0473fa83efa7a` | `8087f2c68b19a302a25e814ec8ce6113d91d4750` | Add adversarial finance API and PostgreSQL evidence with three unresolved counterexamples |
| 2 | `3c34d9e121e751af39267fc28338bf2233178fc3` | `648a0720ccadcfff04a3225783e0473fa83efa7a` | Verify deployed and plain session HTTP challenge contracts without changing finance rules |
| 3 | `2e20bfdccb711bdd5f9028cb60e287ee742c77c5` | `3c34d9e121e751af39267fc28338bf2233178fc3` | Preserve unrelated native print CI timeout evidence without changing its assertions |

`git diff 8087f2c..2e20bfd`共92个路径：3个`backend/crm/tests/`新增文件，以及89个全部位于`docs/uat-evidence/finance-adversarial-review-20261104/`的报告/日志/API证据文件。没有backend业务实现、模型、迁移、前端、打印测试源码或`.github`工作流变更。第二笔提交调整一个HTTP测试和其证据；第三笔仅更新报告manifest并添加打印超时发布日志。

## 三个未修反例

原文件 [`finance-adversarial-review-20261104/defect_repros.py`](../finance-adversarial-review-20261104/defect_repros.py) 含ADV-01/02/03三个普通断言测试，没有`skip`、`xfail`、`expectedFailure`或把实际错误状态改成期望的改写。该文件在三笔提交中的Git blob SHA均为`25d81b7efba0b45e4d8055c48496a26b51cdecb5`，因此原复现代码未被后续提交改写。

| 反例 | 保留的断言/复现意图 | 日志结果 |
|---|---|---|
| ADV-01 | 追加分类后详情性质必须为`expense`；再把它匹配为内部转账应精确拒绝（400），收入和支出统计表面仍各保留47。 | SQLite与PG复现均失败，实际转账请求被接受，与断言相反。 |
| ADV-02 | 余额53的已完成核对之后补做本金配对，余额仍53，但核对状态应变为`needs_review`。 | SQLite与PG复现均失败，实际状态未转为`needs_review`。 |
| ADV-03 | 已授予finance/transactions操作权限及全局数据范围的普通角色，应可进入受限来源preview（报告记载期望200）。 | SQLite与PG复现均失败，实际为403。 |

证据入口：

- [`defect_repros.py`](../finance-adversarial-review-20261104/defect_repros.py)：三个逐项复现与断言。
- [`defects-final-sqlite.published.log`](../finance-adversarial-review-20261104/defects-final-sqlite.published.log)：`Ran 3 tests`、`FAILED (failures=3)`，文件SHA256 `444c7548e077a0afafa5e2fda74dca0621001c1efc172eb9d301a459ab91f75e`。
- [`defects-release-postgres.published.log`](../finance-adversarial-review-20261104/defects-release-postgres.published.log)：PG复验`Ran 3 tests`、`FAILED (failures=3)`；测试库无残留、cleanup complete，文件SHA256 `b111172138e16cf49bfe30c3d7542597433e2f60d074d0cc185042043c9ecfb8`。
- [`README.md`](../finance-adversarial-review-20261104/README.md)说明`defect_repros.py`需显式命令执行，常规CI不会发现报告目录中的复现模块。因此普通CI变绿不代表三个反例消失。

**后续集成门槛：**按用户要求，将这三个原始反例不改断言地纳入默认CI发现/执行路径，而不只留作手动命令。它们在缺陷修复前会按真实缺陷失败；修复合入后应由原断言转绿，不能用xfail、skip或放宽状态断言掩盖。

## 新增正常路径测试及PG日志核对

三项新增后端测试源码：

- [`test_finance_adversarial_review.py`](../../../backend/crm/tests/test_finance_adversarial_review.py)：17个测试方法。
- [`test_finance_adversarial_concurrency.py`](../../../backend/crm/tests/test_finance_adversarial_concurrency.py)：7个PostgreSQL并发方法；类级`skipUnless(connection.vendor == "postgresql")`只在非PG环境跳过真实锁语义，属于环境门槛，不是迎合实现。
- [`test_finance_adversarial_http.py`](../../../backend/crm/tests/test_finance_adversarial_http.py)：3个`LiveServerTestCase`方法，统一经`urllib.request.urlopen`连接本机真实TCP HTTP服务。

[`postgres-auth-verified.published.log`](../finance-adversarial-review-20261104/postgres-auth-verified.published.log)逐项列出17+7+3=27个测试名，末尾记录`Ran 27 tests in 60.408s`、`OK`、`test_exit: 0`、测试库无残留及`cleanup: complete`。其中7个并发测试和3个TCP HTTP测试都实际出现于该PG日志；PG运行中没有跳过。日志SHA256为`f9df6be2816863889aeb33e2e62f51a00abb1d361897aec9589aa872a5681ac4`，与本包manifest登记相符。README同样记为27/27通过、0跳过。

三项真实HTTP场景为：双人Session/CSRF审批、过账重试和CSV；私有文件字节与匿名/无角色拒绝；现有认证器challenge下匿名拒绝状态与文件字节保护。均是隔离合成数据，非外部生产流量或真实员工身份。

## 403 / 部署401认证契约

该调整局限在HTTP测试，不改认证器或部署配置。基线已有[`backend/crm/authentication.py`](../../../backend/crm/authentication.py)中的`SessionAuthenticationWithChallenge`，它继承DRF `SessionAuthentication`，`authenticate_header()`返回`Session`；部署stage的[`backend/config/settings.py`](../../../backend/config/settings.py)配置该现有类。

[`test_finance_adversarial_http.py`](../../../backend/crm/tests/test_finance_adversarial_http.py)保留两条精确契约：

1. 对普通`SessionAuthentication`显式测试仍断言匿名请求403；已认证但无业务角色的用户访问列表、凭证下载、CSV也断言403。
2. 部署challenge测试从`FinanceCloseoutViewSet().get_authenticators()[0].authenticate_header(None)`读取实际challenge，断言状态必须精确等于“有challenge时401、无challenge时403”，响应`WWW-Authenticate`必须与该challenge完全相等，并断言响应体不含凭证字节。

所以测试没有接受任意401/403，也没有撤掉拒绝路径或凭证字节保护。代码用现存Session认证契约解释部署401，不改变认证或授权产品行为。

## 打印超时证据与变更范围

[`ci-frontend-print-timeout.published.log`](../finance-adversarial-review-20261104/ci-frontend-print-timeout.published.log)保留CI 41857369306中的既有ISS-037原生打印失败：`iss037-print-output-acceptance.spec.js:74`，1440px、`headers=false`，30秒测试超时。日志也记录同文件其他打印场景通过；该失败根因在原证据中未确定，不应写成已修复。

此失败日志的manifest同时保留原日志名和发布副本关系，发布日志SHA256为`4e7e2000916152a606c3faefa62436526f9471d0f5188a26d419947f473cd9f5`。候选diff没有改打印spec、前端代码或CI workflow；不延长超时、不删断言、不把先前成功运行当成本次超时修复。该项仍交打印/集成工作包后续处理。

## 尚未覆盖及交付状态

- 候选本身仍记录ADV-01/02/03未修；两种数据库的三项反例日志均按原断言失败。之后主审告知的906修复ADV-01/02、9af的ADV-03路由/动作修复及PG在独立干净检出运行，属于候选之后的协调状态；本报告没有复审这些后续代码或结果。
- 候选的反例文件不在默认CI自动发现路径；集成时需按上文保留原测试并让默认CI执行。
- 打印超时没有在本候选中修复；生产认证/权限及真实业务数据也不在这组隔离合成证据范围。
- 等待明确稳定交付SHA后再核对完整来源、修复后反例结果及默认CI接线。本候选当前**未正式接收**。

本报告是对固定候选Git对象、测试源码与随附日志的开发侧只读核验，不是ChatGPT独立复审或上线就绪声明。

## 主审登记与延期边界

上述历史打印超时已登记公共ISS-037，不创建重复ID；本包没有给打印聊天追加任务或催办，也不重试用户延期的完整成品/分页。既有全量CI中的打印断言仍保留。候选文档/失败日志保持原样，正式接收与最终集成CI分开，不将当前记录当作源码已独立通过。
# 当前接收记录（2026-11-05）

来源已明确交付完整稳定SHA `e301a86044ffe56b72172a94dc3b00ae09401b05`，已完整合入统一分支（合并提交`087fe34d54e1f34b5e55a59795bf5cfcad9a0d89`）。不是只摘取末尾日志脱敏提交。重新读取GitHub确认来源CI [41862778457](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41862778457)同SHA三项SUCCESS；来源交付时的排队描述属于历史，不是当前结果。来源成功不代表集成通过。

`defect_repros.py`保持原样；新增默认发现模块`backend/crm/tests/test_finance_adversarial_regressions.py`加载原来的两个TestCase、三条原断言，不复制/弱化/跳过。协调补修后实际SQLite **3通过、0失败、0跳过（0.524秒）**。PostgreSQL与最终统一SHA全量/CI仍须单独核实。来源失败日志完整保留，不追改历史失败为成功。

以下为对先前固定候选2e20的历史审查，所述“未正式接收/等待交付”仅适用于当时，打印延期边界继续有效。

