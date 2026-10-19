# R1-SKU-01-FIX-01 执行日志摘要

执行时间：2026-10-20（Asia/Shanghai）

## 前端

```text
$ npm run test:unit
ℹ tests 141
ℹ pass 141
ℹ fail 0

$ PLAYWRIGHT_CHANNEL=chrome CI=true npx playwright test browser-tests/r1-sku-01-fix-01.spec.js --reporter=line
Running 6 tests using 1 worker
6 passed (约 1.1m)

$ PLAYWRIGHT_CHANNEL=chrome CI=true npx playwright test --reporter=line
Running 163 tests using 2 workers
163 passed (6.7m)

$ npm run build
✓ 2005 modules transformed.
✓ built in 1.50s
```

专项浏览器测试使用独立端口 `127.0.0.1:8102` 的后端测试服务和 `127.0.0.1:5195` 的当前 worktree Vite 服务。过程中发现并停止了另一任务遗留的旧 5195 Vite 进程，之后所有结果均由当前 `codex/r1-sku-01-fix-01` worktree 产生。

## 后端

```text
$ python backend/manage.py check
System check identified no issues (0 silenced).

$ python backend/manage.py makemigrations crm --check --dry-run
No changes detected in app 'crm'

$ python backend/manage.py test crm.tests.test_sku_cost_verification crm.tests.test_sales_data_scope crm.tests.test_quote_availability crm.tests.test_quotes crm.tests.test_purchase_costs crm.tests.test_purchase_safety crm.tests.test_procurement crm.tests.test_fulfillment crm.tests.test_inventory_movement_reversal crm.tests.test_finance --verbosity 1
Found 216 test(s).
Ran 216 tests in 198.771s
OK
```

负面校验用例会在开发服务器输出 `Bad Request`，这是预期的 400 响应；测试数据库最终以 `OK` 完成并销毁。

## 视觉检查

所有截图均由真实 Chrome 页面使用 `page.screenshot()` 生成，并在提交前通过本地图片预览人工检查。中文文案检查重点为“导出前风险提示”“暂不导出”“了解风险，继续导出”“请先保存当前 SKU 成本价格和成本币种，再进行核实”等办公场景短文案。
