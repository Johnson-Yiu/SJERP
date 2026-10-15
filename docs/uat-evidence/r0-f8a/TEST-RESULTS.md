# R0-F8A 本地测试输出摘要

命令与隔离范围见验收报告。完整Vitest后对分配集合恢复原样的dirty判断进行了8项针对性复验。精确最终HEAD的完整Backend、PostgreSQL和Frontend结果以GitHub CI交付链接为准。

## Node 121

```text
✔ trade-unit page preserves deactivate and default-source actions (22.6196ms)
✔ transaction form distinguishes refunds from order expenses (38.5438ms)
ℹ tests 121
ℹ suites 0
ℹ pass 121
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 9843.7106
```

## Node-only typography 1

```text
✔ all shared detail drawers use the system typography scale (27.6995ms)
ℹ tests 1
ℹ suites 0
ℹ pass 1
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 374.9746
```

## Full Vitest 586

```text

 RUN  v4.1.11 D:/Codex项目/森爵照明管理系统/.r0f1-review/frontend


 Test Files  58 passed (58)
      Tests  586 passed (586)
   Start at  23:16:47
   Duration  128.33s (transform 6.34s, setup 21.54s, import 24.63s, tests 53.85s, environment 120.60s)

```

## Final focused Vitest 8

```text

 RUN  v4.1.11 D:/Codex项目/森爵照明管理系统/.r0f1-review/frontend


 Test Files  1 passed (1)
      Tests  8 passed (8)
   Start at  23:30:39
   Duration  27.71s (transform 1.99s, setup 2.41s, import 2.60s, tests 272ms, environment 21.64s)

```

## Full Playwright 105

```text
  ok  99 browser-tests\product-master-ux.spec.js:121:1 › category drag preserves selected node and collapsed state after reorder (2.2s)
  ok  98 browser-tests\supplier-ux.spec.js:24:37 › supplier long names, notes, filters, editor and detail at 1280 (4.5s)
  ok 100 browser-tests\supplier-ux.spec.js:24:37 › supplier long names, notes, filters, editor and detail at 1024 (2.2s)
  ok 101 browser-tests\supplier-ux.spec.js:33:1 › supplier creates, cancels dirty edits, saves and reopens consistent detail and list (7.7s)
  ok 102 browser-tests\supplier-ux.spec.js:37:1 › duplicate code, invalid ratio and optional category failures keep entered data (3.0s)
  ok 103 browser-tests\supplier-ux.spec.js:40:1 › filters and page survive reload, detail close and procurement workbench return (4.8s)
  ok 104 browser-tests\supplier-ux.spec.js:43:1 › initial errors retry to empty and refresh errors retain supplier list (2.9s)
  ok 105 browser-tests\supplier-ux.spec.js:46:1 › restricted view hides supplier write actions and purchase shortcuts (1.7s)

  105 passed (4.2m)
```

## Final focused browser 11 (action bounds)

```text
  ok  4 browser-tests\certificates-hs-ux.spec.js:11:1 › HS assignment searchable selection and actual bounds 1280 (6.4s)
  ok  5 browser-tests\certificates-hs-ux.spec.js:10:1 › certificate list and grouped form actual bounds 1024 (7.6s)
  ok  6 browser-tests\certificates-hs-ux.spec.js:11:1 › HS assignment searchable selection and actual bounds 1024 (7.1s)
  ok  7 browser-tests\certificates-hs-ux.spec.js:12:57 › hs-codes pending POST blocks backdrop/back/navigation; failure retains input and retries once (8.0s)
  ok  8 browser-tests\certificates-hs-ux.spec.js:12:57 › product-certificates pending POST blocks backdrop/back/navigation; failure retains input and retries once (3.9s)
  ok  9 browser-tests\certificates-hs-ux.spec.js:13:1 › HS read-only hides maintenance and both pages reload errors recover (8.3s)
  ok 10 browser-tests\certificates-hs-ux.spec.js:15:1 › assignment pending PUT blocks close and navigation, retains selection on rejection and retries (3.6s)
  ok 11 browser-tests\certificates-hs-ux.spec.js:16:1 › certificate first load failure retries to empty, and expiry URL survives reload (15.8s)

  11 passed (1.4m)
```

## Related backend 18

```text
......Bad Request: /api/product-certificates/6/
.......
----------------------------------------------------------------------
Ran 18 tests in 12.807s

OK
Destroying test database for alias 'default'...

Found 18 test(s).
System check identified no issues (0 silenced).
```

## Build

```text
transforming...✓ 2000 modules transformed.
✓ built in 7.75s
(!) Some chunks are larger than 500 kB after minification. Consider:
```
