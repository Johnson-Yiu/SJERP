# 集成测试日志

分支：`codex/integration-020-022-051`
基线：`28ba758388429f57c2e3516e12385a88ce6646a3`

## 后端

```text
python -B manage.py test crm.tests.test_iss020_quote_export
Ran 5 tests ... OK

python -B manage.py test crm.tests.test_quotes.QuoteApiTests crm.tests.test_quotes.QuoteExportTests crm.tests.test_quotes.QuoteRevisionTests crm.tests.test_trade_units
Ran 72 tests ... OK

python -B manage.py test crm.tests.test_database_settings crm.tests.test_environment_isolation
Ran 15 tests ... OK

python -B manage.py test crm
Ran 923 tests in 431.315s
OK (skipped=13)
System check identified no issues (0 silenced)
```

全量测试中的 Bad Request、Forbidden 和 Internal Server Error 输出均来自测试主动验证拒绝、权限、异常回滚和原子性路径；最终汇总为 OK。

## 金额对账

专项回归使用两行三位以上小数单价、EUR、多币种字段、运费和折扣，断言了：

- Quote `total_amount`：`2.04`
- Quote 详情 API：`2.04`
- PI preview API subtotal/total：`2.02` / `2.04`
- XLSX 行金额/运费/折扣/合计：`1.01`、`1.01`、`0.03`、`0.01`、`2.04`
- 从报价草稿创建的 Sales Order 模型和 API：`2.04`

## 迁移

```text
fresh SQLite: python -B manage.py migrate --noinput
all migrations through crm.0085 ... OK
python -B manage.py migrate --check                 passed
python -B manage.py makemigrations --check --dry-run
No changes detected
```

集成相对指定基线没有新增迁移；既有 `crm.0081` 并行叶节点及 `crm.0082_merge_iss026_iss107_iss017` 未被覆盖或重写。

## 前端

```text
npm run test:unit
151 passed, 0 failed

npx vitest run tests --exclude tests/detail-drawer-typography.spec.js --environment jsdom
67 files, 657 tests passed

npm run build
success; existing large-chunk warning only

PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/integration-020-051-evidence.spec.js --config=playwright.config.js
1 passed (real Chrome)
```

首次 Node 运行因独立 worktree 没有 `node_modules` 而无法解析 axios；按 `package-lock.json` 安装依赖后在同一集成工作树重跑为 151/151。Vitest 首次启动的 Vite 临时目录权限问题也已在提升权限的同一工作树重跑，最终为 657/657；均不是业务断言失败。

## CI / PostgreSQL

本地 SQLite、Django 全量和配置拒绝测试通过；本轮没有 PostgreSQL 服务。集成提交 `2297287fe148d2b9416083c744a08bd0226fd5e1` 的 run `40302716729`、随后证据提交 `1fdc392bb84234e3f7781f02f4dde4e4dc88b673` 的 run `40302837508` 均为 failure，`frontend`、`backend`、`backend-postgres` 三个 job 均在可见步骤前结束且 steps 为空；CI/PostgreSQL 状态为 **未验证，不得标记 PASS**。
