# R0-F7B 本地验证输出摘要

CI的完整后端/PG结果以最终精确HEAD的GitHub run为准。本地命令及隔离范围见验收报告。

## Node

```text
✔ top bar has no fake search or notification controls and uses current operator initials (1.3609ms)
✔ core management lists and selectors use the tested all-pages loader (91.3795ms)
✔ trade-unit page preserves deactivate and default-source actions (68.028ms)
✔ transaction form distinguishes refunds from order expenses (11.578ms)
ℹ tests 121
ℹ suites 0
ℹ pass 121
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 7966.2976
```

## Node typography

```text
✔ all shared detail drawers use the system typography scale (17.8613ms)
ℹ tests 1
ℹ suites 0
ℹ pass 1
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 310.7022
```

## Vitest

```text

 RUN  v4.1.11 D:/Codex项目/森爵照明管理系统/.r0f1-review/frontend


 Test Files  57 passed (57)
      Tests  578 passed (578)
   Start at  22:21:56
   Duration  100.89s (transform 5.82s, setup 19.94s, import 19.65s, tests 37.47s, environment 101.41s)

```

## Playwright

```text
  ok 86 browser-tests\supplier-ux.spec.js:24:37 › supplier long names, notes, filters, editor and detail at 1280 (3.5s)
  ok 85 browser-tests\sku-ux.spec.js:26:1 › SKU history load failure remains distinct from empty history and retries (10.0s)
  ok 87 browser-tests\supplier-ux.spec.js:24:37 › supplier long names, notes, filters, editor and detail at 1024 (7.8s)
  ok 88 browser-tests\sku-ux.spec.js:28:1 › SKU logical loads keep separate history and ignore late responses in the rendered list (3.5s)
  ok 90 browser-tests\sku-ux.spec.js:57:1 › transaction-unit navigation returns to SKU editor with original list context (3.9s)
  ok 89 browser-tests\supplier-ux.spec.js:33:1 › supplier creates, cancels dirty edits, saves and reopens consistent detail and list (5.9s)
  ok 91 browser-tests\supplier-ux.spec.js:37:1 › duplicate code, invalid ratio and optional category failures keep entered data (3.2s)
  ok 92 browser-tests\supplier-ux.spec.js:40:1 › filters and page survive reload, detail close and procurement workbench return (6.1s)
  ok 93 browser-tests\supplier-ux.spec.js:43:1 › initial errors retry to empty and refresh errors retain supplier list (3.2s)
  ok 94 browser-tests\supplier-ux.spec.js:46:1 › restricted view hides supplier write actions and purchase shortcuts (4.1s)

  94 passed (4.6m)
```

## Related backend

```text
Bad Request: /api/skus/1/
Bad Request: /api/skus/1/
Bad Request: /api/skus/1/
....
----------------------------------------------------------------------
Ran 93 tests in 8.802s

OK
Destroying test database for alias 'default'...

Found 93 test(s).
System check identified no issues (0 silenced).
```

## Build

```text
transforming...✓ 1996 modules transformed.
✓ built in 7.86s
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```
