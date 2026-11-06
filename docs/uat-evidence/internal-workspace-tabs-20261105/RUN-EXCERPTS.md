# 本地验证终端摘录

以下内容保留用例名和汇总。原始日志的哈希单独记录；运行令牌、临时路径和 HTTP 负载未收录。

## 后端全量

```text
Ran 1443 tests in 1077.724s
OK (skipped=85)
```

## Node 排版专项

```text
ℹ tests 1
ℹ pass 1
ℹ fail 0
ℹ skipped 0
```

## 生产构建

```text
✓ built in 5.84s
```

## Chrome 工作区专项

```text
Running 6 tests using 1 worker
ok 1 browser-tests\workspace-tabs-real.spec.js:6:1 › desktop and 390px isolated workspaces preserve draft inputs, route state and atomic close cancellation (5.4s)
ok 2 browser-tests\workspace-tabs-real.spec.js:62:1 › saved object tasks deduplicate, history and refresh retain links, and bulk closing respects dirty drafts (5.4s)
ok 3 browser-tests\workspace-tabs-real.spec.js:97:1 › saved customer drafts adopt the object and related dirty edits receive an explicit conflict prompt (3.0s)
ok 4 browser-tests\workspace-tabs-real.spec.js:127:1 › bounded synthetic workspaces measure requests, mounted panels, document listeners and timers through reclamation (4.9s)
ok 5 browser-tests\workspace-tabs-real.spec.js:182:1 › direct draft links, native refresh cancellation and synthetic account changes isolate all in-memory input (17.8s)
ok 6 browser-tests\workspace-tabs-real.spec.js:211:1 › list filters, page and both list and task scroll survive independent navigation (14.3s)
  6 passed (1.5m)
```

## 资金与财务重试

```text
Running 9 tests using 1 worker
ok 1 browser-tests\cash-events-p2b.spec.js:4:1 › cash event UI previews, registers, and confirms without changing receipt flows (2.9s)
ok 2 browser-tests\cash-events-p2b.spec.js:47:1 › source verification is explicit and any fact change invalidates the preview (1.5s)
ok 3 browser-tests\cash-events-p2b.spec.js:76:1 › refresh retains the stable request identity without persisting financial inputs (5.8s)
ok 4 browser-tests\cash-events-p2b.spec.js:97:1 › in-memory draft survives task switches and explicit abandon clears only after confirmation (2.7s)
ok 5 browser-tests\cash-events-p2b.spec.js:123:1 › changing a 30 allocation to 50 clears verification and requires a fresh preview (1.8s)
ok 6 browser-tests\cash-events-p2b.spec.js:157:1 › expired local draft is removed during page initialization and sensitive evidence is not persisted (1.8s)
ok 7 browser-tests\cash-events-p2b.spec.js:187:1 › legacy unscoped financial inputs are removed and never restored into a workspace (2.1s)
ok 8 browser-tests\cash-events-p2b.spec.js:217:1 › stale source responses cannot overwrite the current currency (2.1s)
ok 9 browser-tests\finance-retry-safety.spec.js:3:1 › finance pending submission and ambiguous retry preserve identity and guard departure (7.1s)
  9 passed (36.9s)
```

## 真实银行手续费

```text
Running 3 tests using 1 worker
ok 1 browser-tests\independent-bank-fee-real.spec.js:41:3 › independent fee without FX parent: real UI 1440px (17.1s)
ok 2 browser-tests\independent-bank-fee-real.spec.js:41:3 › independent fee without FX parent: real UI 390px (17.2s)
ok 3 browser-tests\independent-bank-fee-real.spec.js:127:1 › real API preserves optional-parent rejection, source quota and idempotency protections (1.7s)
  3 passed (1.3m)
```

## 真实采购付款计划

```text
ok 1 browser-tests\iss075-payment-terms-real.spec.js:22:3 › ISS-075 供应商固定付款规则退出常规前端真实浏览器回归 › 供应商 UI、空付款条件草稿/正式 PO、历史付款计划与窄屏 (11.6s)
  1 passed (18.1s)
```

## 库存完整浏览器组

```text
Running 9 tests using 1 worker
ok 1 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1440 (3.9s)
ok 2 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1440 (2.1s)
ok 3 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1280 (2.7s)
ok 4 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1280 (2.8s)
ok 5 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1024 (2.2s)
ok 6 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1024 (1.6s)
ok 7 browser-tests\inventory-ux.spec.js:54:1 › page restoration, detail navigation and browser Back preserve inventory context (3.1s)
ok 8 browser-tests\inventory-ux.spec.js:62:1 › empty and failed inventories distinguish errors, retry and no records (9.8s)
ok 9 browser-tests\inventory-ux.spec.js:67:1 › restricted UI hides adjustment, reversal and unauthorized cross-module entrances (2.9s)
  9 passed (36.1s)
```

## SKU/库存/产品返回

```text
Running 6 tests using 1 worker
ok 1 browser-tests\inventory-ux.spec.js:54:1 › page restoration, detail navigation and browser Back preserve inventory context (8.2s)
ok 2 browser-tests\product-master-ux.spec.js:54:1 › product detail URL survives reload and close preserves list filters (4.5s)
ok 3 browser-tests\product-master-ux.spec.js:61:1 › product parameter to product detail closes back to original filtered list (2.7s)
ok 4 browser-tests\sku-ux.spec.js:25:37 › SKU detail inventory link and Back 1440 (6.9s)
ok 5 browser-tests\sku-ux.spec.js:25:37 › SKU detail inventory link and Back 1280 (4.3s)
ok 6 browser-tests\sku-ux.spec.js:25:37 › SKU detail inventory link and Back 1024 (6.1s)
  6 passed (1.5m)
```

## 证书及 CRM 提交

```text
Running 9 tests using 1 worker
ok 1 browser-tests\certificates-hs-ux.spec.js:13:57 › hs-codes pending POST blocks backdrop/back/navigation; failure retains input and retries once (4.0s)
ok 2 browser-tests\certificates-hs-ux.spec.js:13:57 › product-certificates pending POST blocks backdrop/back/navigation; failure retains input and retries once (8.0s)
ok 3 browser-tests\certificates-hs-ux.spec.js:16:1 › assignment pending PUT blocks close and survives workspace switches, retains selection on rejection and retries (3.3s)
ok 4 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1440px (4.1s)
ok 5 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1280px (6.0s)
ok 6 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1024px (8.7s)
ok 7 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1440px (4.3s)
ok 8 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1280px (5.2s)
ok 9 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1024px (6.9s)
  9 passed (57.7s)
```

## 报表 Chrome

```text
Running 16 tests using 1 worker
ok  1 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 1440 (4.5s)
ok  2 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 1440 (4.4s)
ok  3 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 1280 (4.7s)
ok  4 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 1280 (4.4s)
ok  5 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 1024 (4.2s)
ok  6 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 1024 (1.6s)
ok  7 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 700 (1.4s)
ok  8 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 700 (1.5s)
ok  9 browser-tests\overview-reports.spec.js:36:1 › saved local chart configurations survive reload, reorder, remove and undo (2.3s)
ok 10 browser-tests\overview-reports.spec.js:44:1 › CSV export keeps the last submitted filters while the form has an unsaved draft (1.8s)
ok 11 browser-tests\overview-reports.spec.js:70:1 › drill and previous-analysis return preserve actual period and browser navigation restores URL (2.5s)
ok 12 browser-tests\overview-reports.spec.js:76:1 › empty dashboard and charts have useful neutral states (2.0s)
ok 13 browser-tests\overview-reports.spec.js:79:1 › initial failures recover, refresh failure keeps stale data, and catalog has retry (2.2s)
ok 14 browser-tests\overview-reports.spec.js:85:1 › restricted UI hides sources, export and navigation, retaining unavailable local configuration (1.6s)
ok 15 browser-tests\overview-reports.spec.js:91:1 › two-level groups show separate columns, drill either dimension and return the original query (2.2s)
ok 16 browser-tests\overview-reports.spec.js:95:1 › cross-group result opens paginated raw detail and links to the original order (1.3s)
  16 passed (44.1s)
```

## CRM Chrome

```text
Running 8 tests using 1 worker
ok 1 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1440px (4.9s)
ok 2 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1280px (4.8s)
ok 3 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1024px (4.4s)
ok 4 browser-tests\crm-saving.spec.js:90:3 › contacts pending PUT failure preserves fields and quick retry sends one request (4.2s)
ok 5 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1440px (3.5s)
ok 6 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1280px (2.7s)
ok 7 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1024px (2.8s)
ok 8 browser-tests\crm-saving.spec.js:90:3 › follow-ups pending PUT failure preserves fields and quick retry sends one request (5.6s)
  8 passed (38.0s)
```

## 权限 Chrome

```text
Running 16 tests using 1 worker
ok  1 browser-tests\organization-access-ux.spec.js:12:37 › organization long matrix computed bounds and sticky headers 1440 (5.2s)
ok  2 browser-tests\organization-access-ux.spec.js:12:37 › organization long matrix computed bounds and sticky headers 1280 (4.6s)
ok  3 browser-tests\organization-access-ux.spec.js:12:37 › organization long matrix computed bounds and sticky headers 1024 (4.8s)
ok  4 browser-tests\organization-access-ux.spec.js:13:1 › dirty switching, cancel and delayed save/readback navigation are protected (5.9s)
ok  5 browser-tests\organization-access-ux.spec.js:14:1 › save refusal and readback refusal retain input; readback retry never posts twice (4.0s)
ok  6 browser-tests\organization-access-ux.spec.js:15:1 › read-only and overview retry do not expose a write action (1.4s)
ok  7 browser-tests\organization-access-ux.spec.js:16:95 › access-denied layout and permitted return 1440 (1.3s)
ok  8 browser-tests\organization-access-ux.spec.js:16:95 › access-status-error layout and permitted return 1440 (1.2s)
ok  9 browser-tests\organization-access-ux.spec.js:16:95 › access-denied layout and permitted return 1280 (1.3s)
ok 10 browser-tests\organization-access-ux.spec.js:16:95 › access-status-error layout and permitted return 1280 (1.5s)
ok 11 browser-tests\organization-access-ux.spec.js:16:95 › access-denied layout and permitted return 1024 (1.3s)
ok 12 browser-tests\organization-access-ux.spec.js:16:95 › access-status-error layout and permitted return 1024 (1.2s)
ok 13 browser-tests\organization-access-ux.spec.js:17:45 › permission service 401 failure and recovery avoid redirects (1.4s)
ok 14 browser-tests\organization-access-ux.spec.js:17:45 › permission service 403 failure and recovery avoid redirects (1.3s)
ok 15 browser-tests\organization-access-ux.spec.js:17:45 › permission service 500 failure and recovery avoid redirects (15.4s)
ok 16 browser-tests\organization-access-ux.spec.js:17:45 › permission service network failure and recovery avoid redirects (15.4s)
  16 passed (1.2m)
```

## 中屏布局阶段性复测

```text
Running 12 tests using 1 worker
ok  1 browser-tests\certificates-hs-ux.spec.js:11:1 › certificate list and grouped form actual bounds 1024 (5.4s)
ok  2 browser-tests\certificates-hs-ux.spec.js:12:1 › HS assignment searchable selection and actual bounds 1024 (3.5s)
ok  3 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1024 (1.9s)
ok  4 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1024 (2.9s)
x   5 browser-tests\inventory-ux.spec.js:54:1 › page restoration, detail navigation and browser Back preserve inventory context (30.1s)
ok  6 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1024 (9.7s)
ok  7 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1024 (8.2s)
ok  8 browser-tests\packaging-ux.spec.js:31:1 › trade pending and failed save keep SKU/factor; switching warns, and retry succeeds once (6.5s)
ok  9 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1024 (7.1s)
ok 10 browser-tests\product-master-ux.spec.js:84:37 › category search depth and retry 1024 (6.0s)
ok 11 browser-tests\product-master-ux.spec.js:114:37 › parameter long layout and empty reset 1024 (4.9s)
ok 12 browser-tests\product-master-ux.spec.js:136:41 › R0-F9 products status labels stay on one line 1024 (4.3s)
  1 failed
  11 passed (2.1m)
```

## 历史用例适配阶段性复测

```text
Running 60 tests using 1 worker
ok  1 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1440 (8.6s)
ok  2 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1280 (4.6s)
ok  3 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1024 (7.1s)
ok  4 browser-tests\import-ux.spec.js:34:1 › downloads contain actual UTF8 BOM headers and correctly quoted failure rows (5.3s)
ok  5 browser-tests\import-ux.spec.js:35:1 › pending preview and execute survive workspace switching and block duplicate changes; cancel never writes (5.9s)
ok  6 browser-tests\import-ux.spec.js:36:1 › restricted import entry and template retry (3.1s)
ok  7 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1440 (2.0s)
ok  8 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1440 (2.3s)
ok  9 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1280 (1.9s)
ok 10 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1280 (2.4s)
ok 11 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1024 (1.8s)
ok 12 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1024 (1.9s)
x  13 browser-tests\inventory-ux.spec.js:54:1 › page restoration, detail navigation and browser Back preserve inventory context (30.3s)
ok 14 browser-tests\inventory-ux.spec.js:62:1 › empty and failed inventories distinguish errors, retry and no records (10.9s)
ok 15 browser-tests\inventory-ux.spec.js:67:1 › restricted UI hides adjustment, reversal and unauthorized cross-module entrances (4.0s)
ok 16 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1440 (9.9s)
ok 17 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1280 (17.2s)
ok 18 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1024 (11.5s)
ok 19 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1440 (5.2s)
ok 20 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1280 (11.4s)
ok 21 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1024 (8.5s)
ok 22 browser-tests\packaging-ux.spec.js:28:1 › packaging pending save blocks close/back/navigation; rejected data stays for retry (6.9s)
x  23 browser-tests\packaging-ux.spec.js:31:1 › trade pending and failed save keep SKU/factor; switching warns, and retry succeeds once (9.2s)
ok 24 browser-tests\packaging-ux.spec.js:34:1 › initial template failure retries and view-only permissions hide all writing entries (4.1s)
ok 25 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1440 (3.8s)
ok 26 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1280 (5.3s)
x  27 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1024 (30.1s)
ok 28 browser-tests\product-master-ux.spec.js:54:1 › product detail URL survives reload and close preserves list filters (4.9s)
ok 29 browser-tests\product-master-ux.spec.js:61:1 › product parameter to product detail closes back to original filtered list (3.4s)
ok 30 browser-tests\product-master-ux.spec.js:66:1 › view-only fixtures cannot create/edit/delete through these page entries (11.1s)
ok 31 browser-tests\product-master-ux.spec.js:70:1 › product failure preserves input and retry; unsaved cancel requires confirmation (9.3s)
ok 32 browser-tests\product-master-ux.spec.js:84:37 › category search depth and retry 1440 (3.4s)
ok 33 browser-tests\product-master-ux.spec.js:84:37 › category search depth and retry 1280 (2.8s)
ok 34 browser-tests\product-master-ux.spec.js:84:37 › category search depth and retry 1024 (3.8s)
ok 35 browser-tests\product-master-ux.spec.js:95:1 › category saving blocks backdrop, retains failure and permits retry (9.7s)
ok 36 browser-tests\product-master-ux.spec.js:103:1 › product parameter context and pending save failure remain recoverable (5.6s)
ok 37 browser-tests\product-master-ux.spec.js:114:37 › parameter long layout and empty reset 1440 (5.5s)
ok 38 browser-tests\product-master-ux.spec.js:114:37 › parameter long layout and empty reset 1280 (2.8s)
ok 39 browser-tests\product-master-ux.spec.js:114:37 › parameter long layout and empty reset 1024 (2.5s)
ok 40 browser-tests\product-master-ux.spec.js:123:1 › category drag preserves selected node and collapsed state after reorder (5.3s)
ok 41 browser-tests\product-master-ux.spec.js:136:41 › R0-F9 products status labels stay on one line 1440 (10.3s)
ok 42 browser-tests\product-master-ux.spec.js:136:41 › R0-F9 products status labels stay on one line 1280 (4.2s)
ok 43 browser-tests\product-master-ux.spec.js:136:41 › R0-F9 products status labels stay on one line 1024 (3.7s)
ok 44 browser-tests\sku-ux.spec.js:20:37 › SKU list filters and pending batch 1440 (14.1s)
ok 45 browser-tests\sku-ux.spec.js:20:37 › SKU list filters and pending batch 1280 (17.7s)
ok 46 browser-tests\sku-ux.spec.js:20:37 › SKU list filters and pending batch 1024 (11.5s)
ok 47 browser-tests\sku-ux.spec.js:21:1 › batch failure retains selections and retry succeeds once (9.4s)
ok 48 browser-tests\sku-ux.spec.js:22:37 › SKU supplier source error and retry 1440 (8.2s)
ok 49 browser-tests\sku-ux.spec.js:22:37 › SKU supplier source error and retry 1280 (10.6s)
ok 50 browser-tests\sku-ux.spec.js:22:37 › SKU supplier source error and retry 1024 (9.1s)
ok 51 browser-tests\sku-ux.spec.js:23:1 › SKU read-only detail remains accessible with no write controls (4.8s)
x  52 browser-tests\sku-ux.spec.js:25:37 › SKU detail inventory link and Back 1440 (4.2s)
x  53 browser-tests\sku-ux.spec.js:25:37 › SKU detail inventory link and Back 1280 (5.0s)
x  54 browser-tests\sku-ux.spec.js:25:37 › SKU detail inventory link and Back 1024 (3.3s)
ok 55 browser-tests\sku-ux.spec.js:26:1 › SKU history load failure remains distinct from empty history and retries (11.7s)
ok 56 browser-tests\sku-ux.spec.js:28:1 › SKU logical loads keep separate history and ignore late responses in the rendered list (4.3s)
ok 57 browser-tests\sku-ux.spec.js:57:1 › transaction-unit navigation returns to SKU editor with original list context (5.1s)
ok 58 browser-tests\sku-ux.spec.js:59:41 › R0-F9 skus status labels stay on one line 1440 (4.5s)
ok 59 browser-tests\sku-ux.spec.js:59:41 › R0-F9 skus status labels stay on one line 1280 (3.7s)
ok 60 browser-tests\sku-ux.spec.js:59:41 › R0-F9 skus status labels stay on one line 1024 (2.8s)
  6 failed
  54 passed (8.0m)
```

## 既有业务浏览器汇总

```text
Running 242 tests using 1 worker
[business-suite] ok   1 browser-tests\cash-duplicate-real.spec.js:35:3 › 核对同账户同额候选并有说明放行 1440px (12.3s)
[business-suite] ok   2 browser-tests\cash-duplicate-real.spec.js:35:3 › 核对同账户同额候选并有说明放行 390px (2.9s)
[business-suite] ok   3 browser-tests\core-business-closeout.spec.js:6:33 › real core closure 1440px (19.2s)
[business-suite] ok   4 browser-tests\core-business-closeout.spec.js:6:33 › real core closure 390px (15.7s)
[business-suite] ok   5 browser-tests\finance-closeout-approval.spec.js:12:34 › authenticated finance closure and reconciliation 1440px (20.0s)
[business-suite] ok   6 browser-tests\finance-closeout-approval.spec.js:12:34 › authenticated finance closure and reconciliation 390px (16.9s)
[business-suite] ok   7 browser-tests\finance-closeout.spec.js:11:34 › real account ledger at 1440px (13.5s)
[business-suite] ok   8 browser-tests\finance-closeout.spec.js:11:34 › real account ledger at 390px (13.3s)
[business-suite] x    9 browser-tests\independent-bank-fee-real.spec.js:41:3 › independent fee without FX parent: real UI 1440px (11.8s)
[business-suite] x   10 browser-tests\independent-bank-fee-real.spec.js:41:3 › independent fee without FX parent: real UI 390px (14.4s)
[business-suite] ok  11 browser-tests\independent-bank-fee-real.spec.js:122:1 › real API preserves optional-parent rejection, source quota and idempotency protections (1.8s)
[business-suite] ok  12 browser-tests\iss029-recipient-snapshot.spec.js:12:1 › real Django: recipient A/B, empty/invalid email, master changes, saved PI and XLSX (17.7s)
[business-suite] ok  13 browser-tests\iss037-seller-freeze-real.spec.js:25:3 › saved PI and Chrome print entry 1440px (8.2s)
[business-suite] ok  14 browser-tests\iss037-seller-freeze-real.spec.js:25:3 › saved PI and Chrome print entry 390px (6.8s)
[business-suite] ok  15 browser-tests\iss037-seller-freeze-real.spec.js:48:1 › unsaved revision preview uses the parent seller and retains print action (5.3s)
[business-suite] ok  16 browser-tests\iss039-amount-allocation-real.spec.js:25:3 › amount-only and deliberate legacy conversion, real Chrome 1440px (30.9s)
[business-suite] ok  17 browser-tests\iss039-amount-allocation-real.spec.js:25:3 › amount-only and deliberate legacy conversion, real Chrome 390px (48.5s)
[business-suite] x   18 browser-tests\cash-events-p2b.spec.js:4:1 › cash event UI previews, registers, and confirms without changing receipt flows (30.1s)
[business-suite] ok  19 browser-tests\cash-events-p2b.spec.js:47:1 › source verification is explicit and any fact change invalidates the preview (1.8s)
[business-suite] ok  20 browser-tests\cash-events-p2b.spec.js:76:1 › refresh retains the stable request identity without persisting financial inputs (3.1s)
[business-suite] ok  21 browser-tests\cash-events-p2b.spec.js:97:1 › in-memory draft survives task switches and explicit abandon clears only after confirmation (2.9s)
[business-suite] ok  22 browser-tests\cash-events-p2b.spec.js:123:1 › changing a 30 allocation to 50 clears verification and requires a fresh preview (2.7s)
[business-suite] ok  23 browser-tests\cash-events-p2b.spec.js:157:1 › expired local draft is removed during page initialization and sensitive evidence is not persisted (2.7s)
[business-suite] ok  24 browser-tests\cash-events-p2b.spec.js:187:1 › legacy unscoped financial inputs are removed and never restored into a workspace (2.0s)
[business-suite] ok  25 browser-tests\cash-events-p2b.spec.js:217:1 › stale source responses cannot overwrite the current currency (3.7s)
[business-suite] ok  26 browser-tests\certificates-hs-ux.spec.js:11:1 › certificate list and grouped form actual bounds 1440 (7.7s)
[business-suite] ok  27 browser-tests\certificates-hs-ux.spec.js:12:1 › HS assignment searchable selection and actual bounds 1440 (6.5s)
[business-suite] ok  28 browser-tests\certificates-hs-ux.spec.js:11:1 › certificate list and grouped form actual bounds 1280 (7.4s)
[business-suite] ok  29 browser-tests\certificates-hs-ux.spec.js:12:1 › HS assignment searchable selection and actual bounds 1280 (4.4s)
[business-suite] x   30 browser-tests\certificates-hs-ux.spec.js:11:1 › certificate list and grouped form actual bounds 1024 (3.5s)
[business-suite] x   31 browser-tests\certificates-hs-ux.spec.js:12:1 › HS assignment searchable selection and actual bounds 1024 (30.3s)
[business-suite] ok  32 browser-tests\certificates-hs-ux.spec.js:11:1 › certificate list and grouped form actual bounds 390 (7.6s)
[business-suite] ok  33 browser-tests\certificates-hs-ux.spec.js:12:1 › HS assignment searchable selection and actual bounds 390 (6.4s)
[business-suite] ok  34 browser-tests\certificates-hs-ux.spec.js:13:57 › hs-codes pending POST blocks backdrop/back/navigation; failure retains input and retries once (5.2s)
[business-suite] ok  35 browser-tests\certificates-hs-ux.spec.js:13:57 › product-certificates pending POST blocks backdrop/back/navigation; failure retains input and retries once (11.1s)
[business-suite] ok  36 browser-tests\certificates-hs-ux.spec.js:14:1 › HS read-only hides maintenance and both pages reload errors recover (16.2s)
[business-suite] x   37 browser-tests\certificates-hs-ux.spec.js:16:1 › assignment pending PUT blocks close and navigation, retains selection on rejection and retries (11.6s)
[business-suite] ok  38 browser-tests\certificates-hs-ux.spec.js:17:1 › certificate first load failure retries to empty, and expiry URL survives reload (14.3s)
[business-suite] ok  39 browser-tests\core-workspace-fixture.spec.js:6:1 › isolated core workspace fixture and real API contracts (3.1s)
[business-suite] ok  40 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1440px (4.0s)
[business-suite] ok  41 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1280px (5.1s)
[business-suite] ok  42 browser-tests\crm-saving.spec.js:73:43 › contacts pending POST resists close and navigation at 1024px (6.1s)
[business-suite] ok  43 browser-tests\crm-saving.spec.js:90:3 › contacts pending PUT failure preserves fields and quick retry sends one request (8.4s)
[business-suite] ok  44 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1440px (3.8s)
[business-suite] ok  45 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1280px (4.5s)
[business-suite] ok  46 browser-tests\crm-saving.spec.js:73:43 › follow-ups pending POST resists close and navigation at 1024px (5.7s)
[business-suite] ok  47 browser-tests\crm-saving.spec.js:90:3 › follow-ups pending PUT failure preserves fields and quick retry sends one request (8.5s)
[business-suite] ok  48 browser-tests\crm-ux.spec.js:148:3 › contacts filters, grouped columns, and form fit 1440px (7.6s)
[business-suite] ok  49 browser-tests\crm-ux.spec.js:148:3 › contacts filters, grouped columns, and form fit 1280px (3.2s)
[business-suite] ok  50 browser-tests\crm-ux.spec.js:148:3 › contacts filters, grouped columns, and form fit 1024px (2.5s)
[business-suite] ok  51 browser-tests\crm-ux.spec.js:167:1 › contact create, duplicate advisory, primary edit and return query stay consistent (10.2s)
[business-suite] ok  52 browser-tests\crm-ux.spec.js:192:1 › contact duplicate check uses hidden customer contacts, links to the record, and fits 390px (3.0s)
[business-suite] ok  53 browser-tests\crm-ux.spec.js:212:1 › editing a contact does not flag itself as a duplicate (2.7s)
[business-suite] ok  54 browser-tests\crm-ux.spec.js:225:3 › follow-up filters, detailed groups, and long content fit 1440px (5.3s)
[business-suite] ok  55 browser-tests\crm-ux.spec.js:225:3 › follow-up filters, detailed groups, and long content fit 1280px (5.3s)
[business-suite] ok  56 browser-tests\crm-ux.spec.js:225:3 › follow-up filters, detailed groups, and long content fit 1024px (3.9s)
[business-suite] ok  57 browser-tests\crm-ux.spec.js:252:1 › follow-up search and due filters remain in URL and saved text updates list (3.4s)
[business-suite] ok  58 browser-tests\crm-ux.spec.js:279:1 › saved attachment delete can be cancelled, confirmed, and remains removed after reopening (7.5s)
[business-suite] ok  59 browser-tests\csv-upload-http-413.spec.js:10:1 › real Chrome upload receives HTTP 413 for an oversized CSV without connection reset (5.5s)
[business-suite] ok  60 browser-tests\final-cross-module-ux.spec.js:3:3 › R0-F9 quotes customer column and filters 1440 (6.5s)
[business-suite] ok  61 browser-tests\final-cross-module-ux.spec.js:3:3 › R0-F9 orders customer column and filters 1440 (4.9s)
[business-suite] ok  62 browser-tests\final-cross-module-ux.spec.js:3:3 › R0-F9 quotes customer column and filters 1280 (3.6s)
[business-suite] ok  63 browser-tests\final-cross-module-ux.spec.js:3:3 › R0-F9 orders customer column and filters 1280 (4.8s)
[business-suite] ok  64 browser-tests\final-cross-module-ux.spec.js:3:3 › R0-F9 quotes customer column and filters 1024 (4.7s)
[business-suite] ok  65 browser-tests\final-cross-module-ux.spec.js:3:3 › R0-F9 orders customer column and filters 1024 (5.2s)
[business-suite] ok  66 browser-tests\finance-actual-cash-resilience.spec.js:32:1 › actual cash failure leaves the legacy dashboard available and retry is independent (4.5s)
[business-suite] ok  67 browser-tests\finance-actual-cash-resilience.spec.js:50:1 › rapid date changes discard stale actual cash responses (3.5s)
[business-suite] ok  68 browser-tests\finance-csv-stability.spec.js:8:32 › CSV retry and changing period 1440 (12.9s)
[business-suite] ok  69 browser-tests\finance-csv-stability.spec.js:8:32 › CSV retry and changing period 390 (11.2s)
[business-suite] ok  70 browser-tests\finance-csv-stability.spec.js:23:1 › actual cash export failure can retry and blocks duplicate pending requests (12.3s)
[business-suite] ok  71 browser-tests\finance-drill.spec.js:42:3 › finance dashboard composition drill desktop and narrow 1440px (10.3s)
[business-suite] ok  72 browser-tests\finance-drill.spec.js:42:3 › finance dashboard composition drill desktop and narrow 700px (12.2s)
[business-suite] ok  73 browser-tests\finance-layout.spec.js:4:5 › receivables: computed filter layout at 1440px (7.9s)
[business-suite] ok  74 browser-tests\finance-layout.spec.js:4:5 › receivables: computed filter layout at 1280px (8.7s)
[business-suite] ok  75 browser-tests\finance-layout.spec.js:4:5 › receivables: computed filter layout at 1024px (6.3s)
[business-suite] ok  76 browser-tests\finance-layout.spec.js:4:5 › receivables: computed filter layout at 640px (6.7s)
[business-suite] ok  77 browser-tests\finance-layout.spec.js:4:5 › receivables: computed filter layout at 390px (7.8s)
[business-suite] ok  78 browser-tests\finance-layout.spec.js:4:5 › payables: computed filter layout at 1440px (4.8s)
[business-suite] ok  79 browser-tests\finance-layout.spec.js:4:5 › payables: computed filter layout at 1280px (4.9s)
[business-suite] ok  80 browser-tests\finance-layout.spec.js:4:5 › payables: computed filter layout at 1024px (6.9s)
[business-suite] ok  81 browser-tests\finance-layout.spec.js:4:5 › payables: computed filter layout at 640px (3.1s)
[business-suite] ok  82 browser-tests\finance-layout.spec.js:4:5 › payables: computed filter layout at 390px (3.4s)
[business-suite] ok  83 browser-tests\finance-reference-basis.spec.js:15:33 › reference basis across finance, transactions and saved cash config 1440 (3.6s)
[business-suite] ok  84 browser-tests\finance-reference-basis.spec.js:15:33 › reference basis across finance, transactions and saved cash config 1024 (2.6s)
[business-suite] x   85 browser-tests\finance-retry-safety.spec.js:3:1 › finance pending submission and ambiguous retry preserve identity and guard departure (7.1s)
[business-suite] ok  86 browser-tests\finance-summary-cards.spec.js:111:5 › 财务流水在1440px完整显示汇总金额 (7.0s)
[business-suite] ok  87 browser-tests\finance-summary-cards.spec.js:111:5 › 应收计划在1440px完整显示汇总金额 (5.7s)
[business-suite] ok  88 browser-tests\finance-summary-cards.spec.js:111:5 › 应付计划在1440px完整显示汇总金额 (7.0s)
[business-suite] ok  89 browser-tests\finance-summary-cards.spec.js:111:5 › 财务流水在1024px完整显示汇总金额 (5.3s)
[business-suite] ok  90 browser-tests\finance-summary-cards.spec.js:111:5 › 应收计划在1024px完整显示汇总金额 (5.6s)
[business-suite] ok  91 browser-tests\finance-summary-cards.spec.js:111:5 › 应付计划在1024px完整显示汇总金额 (6.0s)
[business-suite] ok  92 browser-tests\finance-summary-cards.spec.js:111:5 › 财务流水在390px完整显示汇总金额 (3.6s)
[business-suite] ok  93 browser-tests\finance-summary-cards.spec.js:111:5 › 应收计划在390px完整显示汇总金额 (3.8s)
[business-suite] ok  94 browser-tests\finance-summary-cards.spec.js:111:5 › 应付计划在390px完整显示汇总金额 (3.2s)
[business-suite] ok  95 browser-tests\finance-summary-cards.spec.js:124:3 › 其他汇总卡片页面保持可用：/customers (4.0s)
[business-suite] ok  96 browser-tests\finance-summary-cards.spec.js:124:3 › 其他汇总卡片页面保持可用：/suppliers (6.7s)
[business-suite] ok  97 browser-tests\finance-summary-cards.spec.js:124:3 › 其他汇总卡片页面保持可用：/purchase-orders (6.8s)
[business-suite] ok  98 browser-tests\fulfillment-receivables.spec.js:21:1 › completed receivable navigation, Back, settlement and refund reloads retain fulfillment (7.5s)
[business-suite] ok  99 browser-tests\fulfillment-receivables.spec.js:32:1 › restricted user cannot read protected debt from malicious unmasked order payload (5.4s)
[business-suite] ok 100 browser-tests\fulfillment-receivables.spec.js:39:1 › completion pending prevents duplicate UI action and failed reload retries without false financial success (16.2s)
[business-suite] ok 101 browser-tests\fulfillment-receivables.spec.js:49:48 › unknown no_plans has a review task and no confirmed zero (12.0s)
[business-suite] ok 102 browser-tests\fulfillment-receivables.spec.js:49:48 › unknown review has a review task and no confirmed zero (4.2s)
[business-suite] ok 103 browser-tests\historical-orders-fix-02.spec.js:20:1 › history analysis detail tables work at desktop and 700px CSS viewport (4.8s)
[business-suite] ok 104 browser-tests\historical-orders-fix-02.spec.js:45:1 › history analysis hides unauthorized detail dimensions without blanking the page (6.1s)
[business-suite] ok 105 browser-tests\historical-orders-fix-03.spec.js:51:1 › current historical analysis detail tables match the API at desktop and 700px CSS viewport (5.5s)
[business-suite] ok 106 browser-tests\historical-orders-fix-03.spec.js:84:1 › current historical analysis hides unauthorized detail dimensions without blanking the page (9.7s)
[business-suite] x  107 browser-tests\import-ux.spec.js:35:1 › pending preview and execute block back/navigation, duplicates and changes; cancel never writes (0ms)
[business-suite] ok 108 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1440 (3.6s)
[business-suite] ok 109 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1280 (12.0s)
[business-suite] ok 110 browser-tests\import-ux.spec.js:7:37 › import real computed bounds and long error table 1024 (6.6s)
[business-suite] ok 111 browser-tests\import-ux.spec.js:34:1 › downloads contain actual UTF8 BOM headers and correctly quoted failure rows (7.5s)
[business-suite] ok 112 browser-tests\import-ux.spec.js:36:1 › restricted import entry and template retry (2.7s)
[business-suite] ok 113 browser-tests\integration-020-051-evidence.spec.js:49:1 › Chrome quote workbench and saved PI show the reconciled 1.005 total (6.4s)
[business-suite] ok 114 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1440 (4.3s)
[business-suite] ok 115 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1440 (3.7s)
[business-suite] ok 116 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1280 (5.1s)
[business-suite] ok 117 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1280 (4.4s)
[business-suite] ok 118 browser-tests\inventory-ux.spec.js:30:2 › inventory overview, reserved quantities and SKU drawer at 1024 (3.5s)
[business-suite] ok 119 browser-tests\inventory-ux.spec.js:42:2 › ledger filters, sticky actions and adjustment dialog at 1024 (3.3s)
[business-suite] ok 120 browser-tests\inventory-ux.spec.js:54:1 › page restoration, detail navigation and browser Back preserve inventory context (3.5s)
[business-suite] ok 121 browser-tests\inventory-ux.spec.js:62:1 › empty and failed inventories distinguish errors, retry and no records (10.0s)
[business-suite] ok 122 browser-tests\inventory-ux.spec.js:67:1 › restricted UI hides adjustment, reversal and unauthorized cross-module entrances (4.7s)
[business-suite] ok 123 browser-tests\iss008-chinese-aliases.spec.js:57:3 › customer edit, country aliases and quote customer picker remain usable at 1440px (20.2s)
[business-suite] ok 124 browser-tests\iss008-chinese-aliases.spec.js:57:3 › customer edit, country aliases and quote customer picker remain usable at 390px (29.7s)
[business-suite] ok 125 browser-tests\iss037-formal-fixtures.spec.js:6:1 › formal synthetic PI matrix creates saved API and XLSX evidence (16.0s)
[business-suite] ok 126 browser-tests\iss039-shared-purchase-costs.spec.js:94:1 › ISS-039 authorized procurement can restore and edit a cross-order allocation without sales data (11.1s)
[business-suite] ok 127 browser-tests\iss039-shared-purchase-costs.spec.js:127:1 › ISS-039 read-only procurement is refused by the candidate API and has no edit action (7.8s)
[business-suite] ok 128 browser-tests\iss039-shared-purchase-costs.spec.js:142:1 › ISS-039 no-permission role cannot restore the purchase URL (9.0s)
[business-suite] ok 129 browser-tests\iss041b-evidence.spec.js:18:3 › ISS-041-B raw detail evidence at 1440px (1.7s)
[business-suite] ok 130 browser-tests\iss041b-evidence.spec.js:18:3 › ISS-041-B raw detail evidence at 700px (1.6s)
[business-suite] ok 131 browser-tests\iss067-report-permission.spec.js:6:1 › employee opening an old unauthorized report URL gets a valid source and keeps the warning (10.6s)
[business-suite] ok 132 browser-tests\iss067-report-permission.spec.js:45:1 › shared template path remains available to an employee with the source permission (9.5s)
[business-suite] x  133 browser-tests\iss075-payment-terms-real.spec.js:22:3 › ISS-075 供应商固定付款规则退出常规前端真实浏览器回归 › 供应商 UI、空付款条件草稿/正式 PO、历史付款计划与窄屏 (2.0m)
[business-suite] ok 134 browser-tests\orders-390-layout.spec.js:54:3 › R1-REPAIR-07 orders layout after 390px (5.0s)
[business-suite] ok 135 browser-tests\orders-390-layout.spec.js:54:3 › R1-REPAIR-07 orders layout after 700px (6.3s)
[business-suite] ok 136 browser-tests\orders-390-layout.spec.js:54:3 › R1-REPAIR-07 orders layout after 1024px (5.5s)
[business-suite] ok 137 browser-tests\orders-390-layout.spec.js:54:3 › R1-REPAIR-07 orders layout after 1440px (5.5s)
[business-suite] ok 138 browser-tests\organization-access-ux.spec.js:12:37 › organization long matrix computed bounds and sticky headers 1440 (7.1s)
[business-suite] ok 139 browser-tests\organization-access-ux.spec.js:12:37 › organization long matrix computed bounds and sticky headers 1280 (7.2s)
[business-suite] ok 140 browser-tests\organization-access-ux.spec.js:12:37 › organization long matrix computed bounds and sticky headers 1024 (5.2s)
[business-suite] ok 141 browser-tests\organization-access-ux.spec.js:13:1 › dirty switching, cancel and delayed save/readback navigation are protected (7.0s)
[business-suite] ok 142 browser-tests\organization-access-ux.spec.js:14:1 › save refusal and readback refusal retain input; readback retry never posts twice (6.4s)
[business-suite] ok 143 browser-tests\organization-access-ux.spec.js:15:1 › read-only and overview retry do not expose a write action (2.4s)
[business-suite] ok 144 browser-tests\organization-access-ux.spec.js:16:95 › access-denied layout and permitted return 1440 (3.6s)
[business-suite] ok 145 browser-tests\organization-access-ux.spec.js:16:95 › access-status-error layout and permitted return 1440 (7.5s)
[business-suite] ok 146 browser-tests\organization-access-ux.spec.js:16:95 › access-denied layout and permitted return 1280 (9.5s)
[business-suite] ok 147 browser-tests\organization-access-ux.spec.js:16:95 › access-status-error layout and permitted return 1280 (6.4s)
[business-suite] ok 148 browser-tests\organization-access-ux.spec.js:16:95 › access-denied layout and permitted return 1024 (6.2s)
[business-suite] ok 149 browser-tests\organization-access-ux.spec.js:16:95 › access-status-error layout and permitted return 1024 (4.5s)
[business-suite] ok 150 browser-tests\organization-access-ux.spec.js:17:45 › permission service 401 failure and recovery avoid redirects (6.0s)
[business-suite] ok 151 browser-tests\organization-access-ux.spec.js:17:45 › permission service 403 failure and recovery avoid redirects (5.0s)
[business-suite] ok 152 browser-tests\organization-access-ux.spec.js:17:45 › permission service 500 failure and recovery avoid redirects (15.4s)
[business-suite] ok 153 browser-tests\organization-access-ux.spec.js:17:45 › permission service network failure and recovery avoid redirects (15.5s)
[business-suite] ok 154 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 1440 (11.2s)
[business-suite] ok 155 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 1440 (8.9s)
[business-suite] ok 156 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 1280 (3.2s)
[business-suite] ok 157 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 1280 (2.6s)
[business-suite] ok 158 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 1024 (2.5s)
[business-suite] ok 159 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 1024 (4.5s)
[business-suite] ok 160 browser-tests\overview-reports.spec.js:10:2 › dashboard long names, large amounts and 12-month layout at 700 (3.6s)
[business-suite] ok 161 browser-tests\overview-reports.spec.js:24:2 › reports complex filters, multi charts and computed layout at 700 (3.3s)
[business-suite] ok 162 browser-tests\overview-reports.spec.js:36:1 › saved local chart configurations survive reload, reorder, remove and undo (5.9s)
[business-suite] ok 163 browser-tests\overview-reports.spec.js:44:1 › CSV export keeps the last submitted filters while the form has an unsaved draft (12.2s)
[business-suite] ok 164 browser-tests\overview-reports.spec.js:70:1 › drill and previous-analysis return preserve actual period and browser navigation restores URL (4.0s)
[business-suite] ok 165 browser-tests\overview-reports.spec.js:76:1 › empty dashboard and charts have useful neutral states (8.6s)
[business-suite] ok 166 browser-tests\overview-reports.spec.js:79:1 › initial failures recover, refresh failure keeps stale data, and catalog has retry (4.4s)
[business-suite] ok 167 browser-tests\overview-reports.spec.js:85:1 › restricted UI hides sources, export and navigation, retaining unavailable local configuration (2.9s)
[business-suite] ok 168 browser-tests\overview-reports.spec.js:91:1 › two-level groups show separate columns, drill either dimension and return the original query (8.2s)
[business-suite] ok 169 browser-tests\overview-reports.spec.js:95:1 › cross-group result opens paginated raw detail and links to the original order (3.7s)
[business-suite] ok 170 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1440 (3.5s)
[business-suite] ok 171 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1280 (3.6s)
[business-suite] ok 172 browser-tests\packaging-ux.spec.js:16:37 › packaging actual layout and linked navigation 1024 (11.0s)
[business-suite] ok 173 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1440 (3.4s)
[business-suite] ok 174 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1280 (9.9s)
[business-suite] ok 175 browser-tests\packaging-ux.spec.js:23:37 › trade units conversion and form fit 1024 (5.4s)
[business-suite] ok 176 browser-tests\packaging-ux.spec.js:28:1 › packaging pending save blocks close/back/navigation; rejected data stays for retry (5.6s)
[business-suite] ok 177 browser-tests\packaging-ux.spec.js:31:1 › trade pending and failed save keep SKU/factor; switching warns, and retry succeeds once (6.4s)
[business-suite] ok 178 browser-tests\packaging-ux.spec.js:34:1 › initial template failure retries and view-only permissions hide all writing entries (5.0s)
[business-suite] ok 179 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1440 (8.4s)
[business-suite] ok 180 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1280 (3.9s)
[business-suite] ok 181 browser-tests\product-master-ux.spec.js:30:38 › product filters, long content and pending save 1024 (2.7s)
[business-suite] ok 182 browser-tests\product-master-ux.spec.js:52:1 › product detail URL survives reload and close preserves list filters (11.7s)
[business-suite] ok 183 browser-tests\product-master-ux.spec.js:59:1 › product parameter to product detail closes back to original filtered list (5.9s)
[business-suite] ok 184 browser-tests\product-master-ux.spec.js:64:1 › view-only fixtures cannot create/edit/delete through these page entries (12.1s)
[business-suite] ok 185 browser-tests\product-master-ux.spec.js:68:1 › product failure preserves input and retry; unsaved cancel requires confirmation (8.1s)
[business-suite] ok 186 browser-tests\product-master-ux.spec.js:82:37 › category search depth and retry 1440 (15.6s)
[business-suite] ok 187 browser-tests\product-master-ux.spec.js:82:37 › category search depth and retry 1280 (5.3s)
[business-suite] ok 188 browser-tests\product-master-ux.spec.js:82:37 › category search depth and retry 1024 (4.3s)
[business-suite] ok 189 browser-tests\product-master-ux.spec.js:93:1 › category saving blocks backdrop, retains failure and permits retry (5.6s)
[business-suite] ok 190 browser-tests\product-master-ux.spec.js:101:1 › product parameter context and pending save failure remain recoverable (7.2s)
[business-suite] ok 191 browser-tests\product-master-ux.spec.js:112:37 › parameter long layout and empty reset 1440 (3.7s)
[business-suite] ok 192 browser-tests\product-master-ux.spec.js:112:37 › parameter long layout and empty reset 1280 (11.9s)
[business-suite] ok 193 browser-tests\product-master-ux.spec.js:112:37 › parameter long layout and empty reset 1024 (2.8s)
[business-suite] ok 194 browser-tests\product-master-ux.spec.js:121:1 › category drag preserves selected node and collapsed state after reorder (6.0s)
[business-suite] ok 195 browser-tests\product-master-ux.spec.js:134:41 › R0-F9 products status labels stay on one line 1440 (6.2s)
[business-suite] ok 196 browser-tests\product-master-ux.spec.js:134:41 › R0-F9 products status labels stay on one line 1280 (5.3s)
[business-suite] ok 197 browser-tests\product-master-ux.spec.js:134:41 › R0-F9 products status labels stay on one line 1024 (6.3s)
[business-suite] ok 198 browser-tests\r1-repair-04-routing.spec.js:4:1 › R1-REPAIR-04 font interception is registered before navigation (441ms)
[business-suite] ok 199 browser-tests\report-query-request-order.spec.js:4:1 › submitted labels can precede the data response; capture the actual filtered request (4.4s)
```
