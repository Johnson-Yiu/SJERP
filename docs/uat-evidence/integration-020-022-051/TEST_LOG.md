# 集成测试日志

分支：`codex/integration-020-022-051`
基线：`28ba758388429f57c2e3516e12385a88ce6646a3`

## 后端

```text
python -B manage.py test crm.tests.test_iss020_quote_export
Ran 7 tests ... OK

python -B manage.py test crm.tests.test_purchase_moq crm.tests.test_procurement crm.tests.test_supplier_sku crm.tests.test_purchase_payment_terms crm.tests.test_iss020_quote_export crm.tests.test_order_quantity_adjustments
Ran 82 tests ... OK

python -B manage.py test crm
Ran 932 tests in 405.200s
OK (skipped=13)
System check identified no issues (0 silenced)
```

全量测试中的 Bad Request、Forbidden 和 Internal Server Error 输出来自测试主动验证拒绝、权限、异常回滚和原子性路径；最终汇总为 OK。

## ISS-020 历史金额对账

隔离 SQLite 的修复前复现：

```text
legacy quote raw total: 2.010
unprotected current derived total: 2.02
legacy order raw total: 2.010
legacy payment plan total: 2.0100
```

修复后保留旧正式记录的版本 1，新的单据使用版本 2：

```text
legacy formal quote: model=2.010, API/PI=2.01
legacy confirmed order: base/total=2.010, payment plan=2.0100
new draft order: version=2, total=2.02
new EUR sample: lines=1.01+1.01, freight=0.03, discount=0.01, total=2.04
```

覆盖了多行三位及以上小数单价、已确认正式报价、历史报价/版本、已确认销售订单及付款计划、合同数量变更预览、EUR 与运费/折扣。合同数量变更回归只对比变更前后预览，不更新历史付款计划。没有写入真实生产数据，也没有批量重算历史财务或应收。

## ISS-022 MOQ 与成本交叉验收

定向 82 项和全量 932 项覆盖采购 MOQ、SupplierSKU、交易单位换算、共享 PO/跨 SO 合计、无 MOQ、例外原因/操作员/时间/采购单审计、采购状态筛选、采购付款和成本相关回归。真实 Chrome 日志 `iss022-browser-final/browser-log.json` 记录：

```text
equal MOQ create/place: 201
below MOQ first place: 400 purchase_moq_exception_required
below MOQ with reason: 200
ordered status filter: 200
window width: 700px; horizontal overflow: false
```

隔离数据库从 seed 运行了等于 MOQ、低于 MOQ（交易单位换算）、取消保留草稿、填写原因后正式下单、详情审计和 `status=ordered` 筛选。没有自动补量、虚假数量或内部参考成本改写。

## 迁移

```text
python -B manage.py makemigrations --check --dry-run
No changes detected

fresh SQLite: python -B manage.py migrate --noinput
all migrations through crm.0087 ... OK
python -B manage.py migrate --check
passed

isolated existing database: crm.0085 -> crm.0087
legacy_version=1, legacy_total=2.01000000000000
current_version=2, current_total=2.02
```

`0086_purchase_moq_exception` 接续 `0085_order_quantity_adjustment`；`0087_amount_calculation_compatibility` 接续 `0086`。没有删除、覆盖或重写迁移历史，也没有把旧并行迁移重新编号。

## 前端

```text
npm run test:unit
153 passed, 0 failed

npx vitest run tests --exclude tests/detail-drawer-typography.spec.js --environment jsdom
67 files, 657 tests passed

npm run build
success; existing large-chunk warning only

PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/iss022-moq-real.spec.js --config=playwright.iss022.config.js
1 passed (real Chrome, 12.2s)

PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/integration-020-051-evidence.spec.js
1 passed (real Chrome; deterministic API fixture; current run used an equivalent temporary runner config only to avoid a Windows Vite temp-file lock)
```

报价测试的本次新截图写入本机受控证据目录；仓库内已有报价截图没有被 Windows 文件句柄覆盖。采购截图、日志、fixture 和 Playwright 报告已保存在本目录并随集成提交。

## CI / PostgreSQL / 部署

源分支 ISS-051 run `40264628939`、ISS-020 run `40286651906` 以及此前集成 run `40302716729`、`40302837508`、`40302954124` 均为 failure，`frontend`、`backend`、`backend-postgres` 在可见 steps 前结束或无 steps；不能标记 PASS。最终集成 SHA 的 CI 状态需在最终 push 后再次查询。当前没有本地 PostgreSQL 服务，PostgreSQL 和真实生产代理安全验收仍未验证。

ISS-051 保留 `DEPLOYMENT_VERIFICATION_PENDING`。本地 SQLite、Django、Node、Vitest、生产构建和真实 Chrome 结果不能替代 GitHub CI、PostgreSQL 或生产环境验收。
