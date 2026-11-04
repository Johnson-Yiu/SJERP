# Browser Label Audit

本审计只校正浏览器标签证据，不改原始 `visual-evidence.json`、PNG、日志、产品代码、runner、CI 或 Git 状态。逐项按 PNG 归档路径定位 producer，再核对相应源码 SHA 中的 runner 选择、isolated Playwright config 与 spec 级 `test.use`。文件名和测试标题中的 “Chrome” 不作为浏览器身份依据。

## 结论

| 原标签 | 项数 | 可证新标签 | 数量 |
|---|---:|---|---:|
| `actual-Chrome-CI-archive`（源码 1f189c3） | 124 | Chrome channel | 18 |
| 同上 |  | 默认 Playwright Chromium | 103 |
| 同上 |  | `UNKNOWN`（同名截图 producer 冲突） | 3 |
| `actual-Chrome-CI-success-artifact`（源码 8087f2） | 6 | Chrome channel | 6 |

Chrome 标签只表示源码选择 `channel: 'chrome'`；具体 Chrome 版本/可执行文件未由这两批图自身证明。默认 Chromium 表示 isolated config 的 `browserName: chromium` 且 `channel` 为 `undefined`。

## Runner 与源码依据

- 1f 源码：`1f189c3f74fda2908620dd3860230d860f1cbb43`；8087 源码：`8087f2c68b19a302a25e814ec8ce6113d91d4750`；当前检出 HEAD：`e768c69193d2d9241bdddc6cbce717f9d9701469`。三者的 runner 在 `frontend/scripts/run-isolated-browser-tests.mjs:534` 都只对单个 `iss028-035-category-schema.spec.js` 选择 `PLAYWRIGHT_CHANNEL=chrome`，其他选择传空字符串。
- Runner 的 `browserArgs()` 在 `run-isolated-browser-tests.mjs:470` 指向 `playwright.isolated.config.js`。该 config 在 `playwright.isolated.config.js:32-33` 使用 `browserName: chromium`，并将空 channel 转为 `undefined`。因此 CI 上“安装了 Chrome”或 screenshot 文件名带 `chrome` 都不等于通过 Chrome channel 启动。
- ISS-028 的 `1f189c3f74fda2908620dd3860230d860f1cbb43` spec 在 `frontend/browser-tests/iss028-035-category-schema.spec.js:114` 断言 channel 为 `chrome`；与 runner 特判及 isolated config 一致，14 张归为 Chrome channel。
- ISS-029 的 `1f189c3f74fda2908620dd3860230d860f1cbb43` spec 在 `frontend/browser-tests/iss029-recipient-snapshot.spec.js:6` 全文件声明 `test.use({ channel: 'chrome' })`；4 张 `chrome-version-*` 图归为 Chrome channel。
- Finance 成功归档 `8087f2c68b19a302a25e814ec8ce6113d91d4750` 的 `finance-closeout.spec.js:6` 与 `finance-closeout-approval.spec.js:7` 均全文件声明 `test.use({ channel: 'chrome' })`；6 张图保留 Chrome channel 标签。
- ISS-007 旧图来自 `1f189c3f74fda2908620dd3860230d860f1cbb43`，当时 spec 没有 `test.use`，因此归为默认 Chromium。较新的 `e768c69193d2d9241bdddc6cbce717f9d9701469` 在 `iss007-attachment-real.spec.js:12` 才声明 Chrome channel；该变更不追溯改变 1f 截图的生成环境。

## 逐 producer 分类

| 归档组 / producer | 项数 | 原标签 | 可证新标签 | 依据（源码 SHA） |
|---|---:|---|---|---|
| csv-upload-http-413.spec.js | 1 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| integration-020-051-evidence.spec.js | 3 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss029-recipient-snapshot.spec.js（chrome-version-*） | 4 | `actual-Chrome-CI-archive` | Chrome channel（build UNKNOWN） | `1f189c3`; producer mapping in JSON |
| historical-orders-fix-02.spec.js / historical-orders-fix-03.spec.js（playwright-*） | 3 | `actual-Chrome-CI-archive` | UNKNOWN | `1f189c3`; producer mapping in JSON |
| iss006-frontend-storage-chrome.spec.js | 16 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss007-attachment-real.spec.js | 8 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss007-image-snapshot-real.spec.js | 8 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss008-chinese-aliases.spec.js | 6 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss022-moq-real.spec.js | 9 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss028-035-category-schema.spec.js | 14 | `actual-Chrome-CI-archive` | Chrome channel（build UNKNOWN） | `1f189c3`; producer mapping in JSON |
| iss055-customer-404-real.spec.js | 6 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss075-payment-terms-real.spec.js | 4 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| quote-editor-mobile-actions.spec.js | 4 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| iss041b-evidence.spec.js（diagnostics helper 仅写 JSON） | 10 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| orders-390-layout.spec.js | 7 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| finance-summary-cards.spec.js | 9 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| fulfillment-receivables.spec.js | 1 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| supplier-ux.spec.js | 11 | `actual-Chrome-CI-archive` | 默认 Chromium（非 Chrome channel） | `1f189c3`; producer mapping in JSON |
| finance-closeout.spec.js | 2 | `actual-Chrome-CI-success-artifact` | Chrome channel（build UNKNOWN） | `8087f2c`; producer mapping in JSON |
| finance-closeout-approval.spec.js | 4 | `actual-Chrome-CI-success-artifact` | Chrome channel（build UNKNOWN） | `8087f2c`; producer mapping in JSON |

## 文件完整性与边界

- 1f 归档 `docs/uat-evidence/review-integration-batch-20261104/ci-1f189c3-ui-screenshots.zip`（SHA256 `169477d1aa4917dfdaff3f09767f42d6e157227aa11f32a55ec070b3e1cd5262`）：124/124 成员与原索引的字节数及 SHA256 一致。
- 8087 归档 `final-ci-41839476121-evidence.zip`（SHA256 `b0b4a1395d772e6dafe6246be78a3af41cc8507f8c27e1b053c0b6641240fbb8`）：6/6 Finance PNG 成员与原索引的字节数及 SHA256 一致。完整清单见 `browser-label-audit.json`。字节匹配证明图像归档一致，不证明浏览器身份。
- 3 张 `playwright-700px.png`、`playwright-desktop.png`、`playwright-700px-permission-limited.png` 在两个历史 spec 中同名写入共享目录，无法唯一定位最后写入者，按要求将 channel 留为 `UNKNOWN`。
- 按主审交接信息，78b/f92810 的默认 Chromium 修正及 e768 的独立真 Chrome 验收属于其他证据批次；本审计不改其标签或状态。其他显式 Chrome/IAB 的独立 `.mjs` 也未纳入推断。
- 原索引 SHA256（本审计读取时）：`f768954efa3082ef8e49b9b2c0d92b62de8a5a2e1641d8763db9e58f36ac05cd`。本审计未更改原索引、图像、日志、runner、CI、Git 状态。
