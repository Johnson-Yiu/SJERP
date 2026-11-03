# 启用前整合：第一部分

起点 `d5abc64750d00c89d685bf12c0f8f67d4ba10a97`；分支 `codex/r1-prelaunch-consolidation-20261104`。在 2026-11-04 查询远端，两项后续验收任务没有可确认的已交付分支或最终 SHA；本轮只完成第一部分并等待，不推测完成。

## 来源完整性

- 预检共同基线 `a55469c1b07e4f13037c6644c69d8a35ef0496a0`，按顺序移植初版 `0ccbf6c4a776fef5be74ad71ca4b6df0ba12e813`、FIX-01 `951adda34b5c60b303725702514cdacac17cc58d`。相对来源逐文件核对实现、测试、路由、上传 handler、模板及证据无差异；`/api/import/history-preflight/` 复用流式限额，并限制解压大小及行数。
- 备份同一共同基线，按顺序移植 `fd8623a`、`458b48b`、`a9f80b6`、`8f6f099`、`98d5dfe`、最终证据 `9250b066cbd28fd09bd2b1cc1f057604de1f76d9`；与指定来源的适配器、夹具、测试及报告无差异。真实 PG 演练范围和局限见[来源报告](../r1-iss018-backup-restore-drill-20261103/POSTGRES-02.md)。
- 与起点比较，`0096_quote_pi_template_snapshots`、`0096_rmbcashevent_bank_counterparty_and_more`、`0097_merge_quote_and_cash_review` 无差异。没有覆盖其他工作树。

## 本地检查

CPython 3.12.16，`pip check` 通过；显式使用 `DATABASE_URL=sqlite:///:memory:`、独立临时 MEDIA_ROOT 和合成数据。`manage.py check`、`makemigrations --check --dry-run` 通过；新建内存数据库完整 `migrate --noinput` 至两条 0096 和 0097 成功。`showmigrations crm --plan` 的最后叶节点为 0097。

`python manage.py test crm.tests.test_history_import_preflight crm.tests.test_csv_upload_http_413 crm.tests.test_safe_csv_import crm.tests.test_historical_orders crm.tests.test_iss018_backup_recovery crm.tests.test_postgres_drill_backup --verbosity 1`：90 项，86 通过、4 跳过，0 失败。跳过不计通过；此结果不代表真实 PostgreSQL 备份命令验收。本次没有连接真实业务数据库、运行备份恢复命令、重跑 PostgreSQL 演练或触发最终 CI。

完整 `git diff <起点> --check` 对预检源提交保留的原始失败日志 `fix01-before-regression.log:128` 报告一个行尾空格；来源报告已记录该问题。为保留真实原始日志没有重写，后续集成应显式处理或说明，不能声称全量 diff check 通过。

按问题表中每个唯一 ID 的最后一条状态核对，共 124 项：OPEN 1、BLOCKED 16、NEEDS_VERIFICATION 17、FIXED_PENDING_REVIEW 80、CLOSED 10；本部分新增 0、关闭 0。历史时点统计保留。

## 下一步

等待 `R1-ISS018-RESTORE-COMMAND-ACCEPTANCE-03`、`R1-ISS037-PRINT-OUTPUT-ACCEPTANCE-01` 两项明确交付及远端稳定 SHA，之后逐项核对并执行第二部分。剩余门槛见 [READINESS-GATES.md](READINESS-GATES.md)。本部分不部署、不合并 master、不启用正式 RBAC、不导入真实历史数据、不关闭 ISS-018/037/105/121。
