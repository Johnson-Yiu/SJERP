# 实际命令与退出语义

Windows本机解释器：`C:\Users\Johnson\AppData\Local\Temp\iss018-command-locked-venv\Scripts\python.exe`；其版本/全部pin见versions.log。以下在独立工作树执行；`APP_STAGE=development`、`PYTHONUTF8=1`。媒体由每个夹具TemporaryDirectory隔离。任何权限模拟仅在Django测试设置中生效。

```powershell
# backend目录；FINANCE_ADVERSARIAL_EVIDENCE为专属报告api子目录
& $python manage.py test crm.tests.test_finance_adversarial_review crm.tests.test_finance_adversarial_concurrency crm.tests.test_finance_adversarial_http crm.tests.test_finance_closeout crm.tests.test_bank_private_vouchers --verbosity 2
# 根目录；PG_BIN为既有独立PG17工具，脚本创建新随机集群，不使用其旧data
& $python docs/uat-evidence/finance-adversarial-review-20261104/run_postgres.py --pg-bin $PG_BIN
# 明确保留未修缺陷，下面两种命令实际exit 1，不计为通过
& $python docs/uat-evidence/finance-adversarial-review-20261104/run_postgres.py --pg-bin $PG_BIN --reproduce-defects
# backend目录，PYTHONPATH加入本包报告目录
& $python manage.py test defect_repros --verbosity 2
# 根目录
& $python backend/manage.py check
& $python backend/manage.py makemigrations --check --dry-run
& $python docs/uat-evidence/finance-adversarial-review-20261104/audit_reachability.py
git diff --check
```

`PG_BIN=C:\Users\Johnson\AppData\Local\Temp\sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f\pgsql\bin`。脚本校验工具版本17、自有随机data_directory、源/测试库及媒体身份，密码只在自有临时文件/子进程环境，不在命令/报告/归档。根目录新集群在系统temp中；测试完成后查无test数据库并受控清理。真实PG启动使用授权的沙箱外执行，未连接真实业务数据库。

原始`.log`完整保留，发布副本仅统一换行、隐藏一次性隔离凭据，原文件SHA256/字节数见manifest。初轮脚手架失败也保留；不要只读最后绿色日志而忽略显式产品反例exit 1。GitHub三项CI按最终精确SHA在交付正文核实，其原始日志可由运行链接下载，不把未完成运行写成成功。
