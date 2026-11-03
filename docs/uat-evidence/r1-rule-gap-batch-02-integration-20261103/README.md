# R1-RULE-GAP-BATCH-02 集成核验

基线 `a55469c1b07e4f13037c6644c69d8a35ef0496a0`，集成分支 `codex/r1-rule-gap-batch-02-integration-20261103`。三个专项均在独立工作树处理，未使用业务数据库。

| 项目 | 专项来源 HEAD | 证据 |
|---|---|---|
| ISS-037 | `b00981200eb01af4bfa8351c4bd636ab1a678b71` | [卖方与模板](../r1-iss037-seller-template-freeze-20261103/README.md) |
| ISS-105 | `8e99dc1abcf1f4f9fbd9d6cac57258990c12d3e8` | [银行疑似重复](../r1-iss105-bank-duplicate-detection-20261103/README.md) |
| ISS-039 | `087f6098c27050a1d7180fe9c85eef6417063c0b` | [采购预留并发](../r1-iss039-reservation-concurrency-20261103/README.md) |

## 集成和迁移

逐提交移植，两个 0096 保留独立名称和各自内容，通过 `0097_merge_quote_and_cash_review` 汇合。迁移测试恢复全部叶节点，保留审计历史存在时拒绝回退断言。首次集成测试错误地以另一分支的叶节点作为反向目标，导致预期拒绝没有发生；改为共同祖先并在 finally 恢复完整叶节点后重跑通过。没有覆盖原有迁移或业务记录。

## 本地结果

CPython 3.12.16、Django 6.0.9，全部 16 个 Python 锁定版本相符，`pip check` 通过；前端 `npm ci` 使用锁文件。隔离 SQLite / 合成数据：Django check、`makemigrations --check --dry-run` 通过；专项 79 项通过（30 项 PostgreSQL 条件跳过），全量 1148 项通过（42 项按条件跳过）；Node 177 项、前端构建通过，构建仍有超过 500 kB 的现有警告。真实 PostgreSQL 不可用时，专项 CI 而非 SQLite 用于验证：ISS-039 [PostgreSQL 17](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41609103366/job/125826214644) 1119 项通过、21 跳过；ISS-105 [PostgreSQL 17](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41615047577/job/125846286292) 1131 项通过、21 跳过，具体并发和审计保护用例实际执行。专项截图、HTTP 响应、错误与修正见各报告。

## 尚需完成

完整集成版本的 PostgreSQL、前端全量及 Chrome 回归、三项 GitHub CI 同一精确 SHA 验收尚待核实。历史报价原件归档、打印最终 PDF/物理输出、完整双方主体与审批流程、ISS-105 内部转账/退款更正/启用余额/账户核对、生产审计表权限等仍为遗留事项。三项专项通过不代表 ISS-037 或 ISS-105 整体关闭，也不替代独立复审。不得推测启用日、真实余额或历史资料。
