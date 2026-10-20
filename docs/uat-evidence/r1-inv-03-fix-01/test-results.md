# R1-INV-03-FIX-01 测试结果

## 通过

```text
python manage.py test crm.tests.test_inventory_reference --verbosity 1
Ran 3 tests
OK

PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/purchase-inventory-reference.spec.js --config=playwright.config.js --reporter=line
Running 4 tests using 1 worker
4 passed (20.2s)

npm run test:unit
tests 139 / pass 139 / fail 0

npm run build
vite build: success, 2005 modules transformed

python -c "...call_command('test', verbosity=1)"
Ran 771 tests in 287.751s
OK (skipped=13)
```

浏览器测试包含 1440/1024/700 三种视口、SKU A/B 选择、取消选择、数量保持、库存差异记录及延迟响应竞态。另在可见真实 Chrome 中实际完成库存 SKU 选择、无库存 SKU 切换、取消选择、数量 12 保持及库存记录展开。

前端既有回归和构建在本轮代码变更后需重新执行；上一基线已记录 `npm run test:unit` 137/137、`npm run build` 成功。本轮不会把未重新执行的结果冒充为 FIX-01 新执行结果。

## 待执行或环境阻断

- 本机 PostgreSQL 仍无可用服务（无 docker、psql、5432 listener），未伪造 PostgreSQL 通过结果。
- GitHub Actions 额度耗尽，继续 CI PENDING 策略；不创建无意义提交、不禁用工作流。
