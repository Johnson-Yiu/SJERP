# BRANCH-COVERAGE-CLOSEOUT-01

以共同基线 `f3b7242e77752b6cc5b72425bcc3df2fa938de61` 审查。与已认证源码 `7e99a5d394ddc0d96a3af04b74686307f754ca08` 对比，`backend/`、`frontend/`、`.github/` 无树差异。后续 U4 的产品改动须用 U4 自身的最终提交复核。

[逐分支矩阵](classification-matrix.md) · [完整 SHA、路径和运行状态](classification-matrix.json) · [快照核对](snapshot-reconciliation.json) · [远端分支](remote-heads.tsv) · [Actions 快照](actions-snapshot.jsonl)

## 范围与结论

原快照与本次抓取各 244 个远端分支。原报告的 39 个未匹配分支中，`r1-sku-01-fix-02` 原 SHA 已有两次成功 CI，因此留在原单列项。其余 38 个全部保留，本次远端核对未发现这 38 个 HEAD 移动。原三份盘点输入留在 CI-RESTORE 目录，校验和写入快照核对记录。远端分支于 2026-11-11 10:32 UTC 抓取，Actions 分页共返回 548 条运行。缺少记录不改变原始状态。

- 6 项保留等效能力，20 项已有后继，9 项差异为证据或测试，1 项后继已实现原交付同时保留 Excel 打印延期，2 项留给 U4 复验。历史原 SHA 的失败、未运行和缺证据继续保留。
- 已确认的无需重复接收条目及业务入口逐行列出。尚无证据要求直接接收旧业务代码。两项前端范围保留明确的验收和接收条件。
- 本包不更新公共台账。原认证的主 CI 与 Linux 专项六项结果只属于 `7e99a5d3`，不改写任一旧分支的 CI。 [主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478188) · [Linux 专项](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478124)

## 给 U4 的接收建议

1. **finance-list-flex-01** 旧补丁给银行资金、财务流水、账户对账增加三套弹性布局。当前银行资金已用 `table-wrap`，流水已有局部滚动，账户对账已改用 `ledger-cards`。按现行结构检查 390 px／原生 125% 的表头、尾列、详情和操作按钮。若仍有失效，只改具体列表的滚动容器。冲突范围为 `CashEventPage.vue`、`TransactionPage.vue` 和 `FinanceLedgerPage.vue` 模板及 scoped CSS。依赖现行列表结构和交互回归。
2. **ui-copy-optimization-02** 当前工作簿代次保护和历史预检入口仍在，银行入口采用「银行资金记录」。请确认是否确需改成旧「银行结汇与凭证」。该入口也处理非结汇资金和凭证，改名会改变用户对入口范围的理解。若业务确认，最小改动限于导航和路由标题、对应文案断言，保留现有事实字段和权限。与 U4 的 App、路由及财务页变更可能冲突。
3. **ISS-040** 正式 Shipment XLSX 已保留。原生 Excel 打印成品及分页按原决定延期。只有恢复该首发范围时才需重新决定打印机、纸张与实际分页验收条件。
4. 独立视觉审查和旧测试夹具可按矩阵选场景复跑。只接收需要的场景与最小合成 fixture，沿用 U4 运行器。本轮未逐例确认旧部分视觉审查的每一条断言，矩阵保留这一证据缺口。

## 本轮实际补测

均在独立工作树的共同基线执行。SQLite 使用内存测试库，PG17 使用临时 loopback 集群与独立媒体目录。

- SQLite 182 项，176 通过、6 条件跳过。覆盖国家选择、MOQ、采购费用权限、库存参考、正式销售数量调整、主体快照、Packing List、SKU 成本、收款收敛、历史预检和权限。 [原始日志](candidate-sqlite.log)
- PostgreSQL 17 55 项，30 通过、25 条件跳过。覆盖 CSV 审计保护、正式销售数量调整和备份失败关闭。25 项为 SQLite 文件备份场景，不适用于该 PostgreSQL 集群。 [原始日志](candidate-pg17.log)

- Vitest 4 个文件、28 项通过，覆盖数字输入滚轮、所选工作簿请求竞态、供应商界面和国家选择。首轮漏传 `--environment jsdom`，数字滚轮用例 4 项失败，补传与 CI 一致的环境后全通过。 [最终日志](candidate-vitest.log) · [首轮日志](candidate-vitest-initial.log)
- 独立 SQLite、媒体和合成夹具上的真实 Chrome 账户对账，1440 px 和 390 px 共 2 项通过。核对窄屏余额卡片、入账事实、凭证直链和 CSV 中的两笔合成事实。原生 125% 及银行资金、财务流水两个入口未在本次独立补验中覆盖。 [运行日志](finance-chrome.log) · [390 px 截图](finance-chrome/account-facts-390.png) · [实际 CSV](finance-chrome/facts-390.csv)

前端从 `frontend/` 执行 `npx --no-install vitest run tests/numeric-wheel-guard.spec.js tests/history-preflight-page.spec.js tests/supplier-ux.spec.js tests/country-select.spec.js --environment jsdom --maxWorkers=2` 和 `node scripts/run-isolated-browser-tests.mjs --business-test finance-closeout.spec.js`。浏览器运行设置 `ISOLATED_PLAYWRIGHT_USE_CHROME=1` 和本机 Python 路径。后端执行 `python backend/manage.py test … --verbosity 2`，模块见 SQLite 日志。PG17 使用仓库的 `docs/uat-evidence/history-product-sku-linking-01/run-postgres.py` 与三个 `--test-label`，对应 CSV 审计、ISS-018 和数量调整。

本轮补测落在仍需交付的候选能力上。没有用真实凭证运行旧版本。旧版本各自的 CI 保留原状态。
