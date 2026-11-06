# 定向验证结果

浏览器运行器使用独立 SQLite、文件目录和本地端口。

## workspace-integration-real

`node scripts/run-isolated-browser-tests.mjs --business-test workspace-integration-real.spec.js`

```text
  ok 1 browser-tests\workspace-integration-real.spec.js:35:1 › real logout protects a dirty draft and clears it before a same-name account signs in (9.2s)
  ok 2 browser-tests\workspace-integration-real.spec.js:66:1 › real session expiry removes dirty workspaces and rejects a late authenticated response (4.9s)
  ok 3 browser-tests\workspace-integration-real.spec.js:104:1 › parallel customer drafts adopt the saved object and return to the original filtered list (3.4s)
  ok 4 browser-tests\workspace-integration-real.spec.js:130:1 › customer reminder entries keep separate context and preserve an in-progress need (5.8s)
  4 passed (25.0s)
```

## access-session-real

`node scripts/run-isolated-browser-tests.mjs --business-test access-session-real.spec.js`

```text
  ok 1 browser-tests\access-session-real.spec.js:6:3 › ERP login and logout use the isolated real session (desktop) (6.8s)
  ok 2 browser-tests\access-session-real.spec.js:6:3 › ERP login and logout use the isolated real session (narrow) (5.1s)
  ok 3 browser-tests\access-session-real.spec.js:43:1 › lost session shows expiry and preserves a same-origin return (2.2s)
  ok 4 browser-tests\access-session-real.spec.js:56:1 › external return target is never navigated (2.2s)
  4 passed (18.3s)
```

## workspace-tabs-real

`node scripts/run-isolated-browser-tests.mjs --business-test workspace-tabs-real.spec.js`

```text
  ok 1 browser-tests\workspace-tabs-real.spec.js:6:1 › desktop and 390px isolated workspaces preserve draft inputs, route state and atomic close cancellation (8.6s)
  ok 2 browser-tests\workspace-tabs-real.spec.js:62:1 › saved object tasks deduplicate, history and refresh retain links, and bulk closing respects dirty drafts (6.5s)
  ok 3 browser-tests\workspace-tabs-real.spec.js:97:1 › saved customer drafts adopt the object and related dirty edits receive an explicit conflict prompt (5.5s)
  ok 4 browser-tests\workspace-tabs-real.spec.js:127:1 › bounded synthetic workspaces measure requests, mounted panels, document listeners and timers through reclamation (4.3s)
  ok 5 browser-tests\workspace-tabs-real.spec.js:182:1 › direct draft links, native refresh cancellation and synthetic account changes isolate all in-memory input (11.5s)
  ok 6 browser-tests\workspace-tabs-real.spec.js:211:1 › list filters, page and both list and task scroll survive independent navigation (2.8s)
  6 passed (40.4s)
```

## import-ux

`node scripts/run-isolated-browser-tests.mjs --business-test import-ux.spec.js`

```text
  ok 1 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1440 (4.3s)
  ok 2 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1280 (1.1s)
  ok 3 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1024 (1.1s)
  ok 4 browser-tests\import-ux.spec.js:34:1 › downloads contain actual UTF8 BOM headers and correctly quoted failure rows (3.6s)
  ok 5 browser-tests\import-ux.spec.js:35:1 › pending preview and execute survive workspace switching and block duplicate changes; cancel never writes (2.1s)
  ok 6 browser-tests\import-ux.spec.js:36:1 › restricted import entry and template retry (19.6s)
  6 passed (33.9s)
```

## 后端和前端定向

- Django `manage.py test crm.tests.test_access_implementation crm.tests.test_workspace_identity crm.tests.test_new_product_reminders --noinput`。21 项，19 通过，2 跳过。
- Vitest `tests/workspace-manager.spec.js`。12 通过。
- Node `src/api.test.js src/utils/safeReturn.test.js`。9 通过。
- Vite 生产构建成功。
