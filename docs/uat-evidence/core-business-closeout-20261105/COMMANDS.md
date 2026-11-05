# 实际命令与环境

工作树 D:/Codex项目/森爵照明管理系统/.worktrees/core-business-closeout-20261105。最终 CPython、16 项精确依赖、PG17、OpenSSL、Chrome 版本见 ENVIRONMENT.json。没有更改工作流或触发 CI。

本机已验证锁定 Python：C:/Users/Johnson/AppData/Local/Temp/sunjack-cpython312-verify-20261031-a37d/shared-venv/Scripts/python.exe（3.12.16）。以下 `$py` 指该完整路径。PG 可执行目录为 C:/Users/Johnson/AppData/Local/Temp/sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f/pgsql/bin；没有把临时演练集群当持久数据库。

```powershell
$env:APP_STAGE='development'
$env:PYTHONUTF8='1'
$env:DATABASE_URL='sqlite:///:memory:'
$env:OPS_TEST_OPENSSL='D:/Program Files/Git/usr/bin/openssl.exe'
# cwd=backend；不能在仓库根无标签发现后把0项算通过
& $py manage.py test --verbosity 2
# cwd=worktree；新建集群、随机数据库、专属媒体、身份核验和受控清理
& $py docs/uat-evidence/core-business-closeout-20261105/run_postgres.py --full --pg-bin <上述PG目录>
& $py docs/uat-evidence/core-business-closeout-20261105/run_postgres.py --pg-bin <上述PG目录>
# 仅生命周期诊断子集，不代表全量
& $py docs/uat-evidence/core-business-closeout-20261105/run_postgres.py --test-label crm.tests.test_iss006_idempotency.FulfillmentIdempotencyDatabaseTests.test_postgresql_concurrent_duplicate_requests_are_serialized --pg-bin <上述PG目录>
& $py backend/manage.py check
& $py backend/manage.py makemigrations --check --dry-run
& $py backend/manage.py showmigrations --plan
& $py -m pip check
npm ci --prefix frontend
npm --prefix frontend run test:unit
# cwd=frontend；完全沿用CI的文件选择，原生threads池4 worker；不改测试超时
npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --pool=threads --maxWorkers=4 --reporter=verbose
node --test tests/detail-drawer-typography.spec.js
npm run build
# cwd=worktree；路径为本工作树绝对路径，隔离运行器拒绝越界目录
$env:ISOLATED_TEST_PYTHON='<上述锁定Python完整路径>'
$env:ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT='<本工作树>/docs/uat-evidence/core-business-closeout-20261105/browser-runtime-payment'
npm --prefix frontend run test:browser:isolated -- --business-test core-business-closeout.spec.js
git diff --check
```

CORE_BUSINESS_EVIDENCE 分别指向本专属报告内 sqlite-closeout-api、pg-closeout-api、pg-final-accepted-api 等绝对目录，导出的是本次合成测试数据。SQLite 新库是独立内存库；默认开发媒体位于本工作树 backend/media，未使用其他工作树；PG 与 Chrome 另有专属临时媒体并清理。

实际日志保留原命令、结果和失败。最新数据库与专项命令有源 SHA 和 EXIT_CODE；Node/Vitest/Chrome shell 在进程结束后均回报 EXIT=0。1430项全量的生产源码冻结于7edbde7，后加的测试连接后置条件由4ffad5c的56项完整专项重新验证，见源码blob对应关系。最初探索失败、取消、0项发现均单列，不累计为通过。
