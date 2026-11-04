# 447d 冻结检出的前端最终本地验收

验收对象：`447d7816ead2e971e249cb2e762b1a6f7009b9c0`  
检出目录：`.tmp/final-integrated-447d`（位于主审工作树内的 detached 检出）  
证据根：`docs/uat-evidence/integration-closeout-02/final-447d-frontend/`  
结论：**FIX REQUIRED**。Node、字体、Vitest 和构建通过；浏览器套件有 2 项失败，不能记为最终 PASS。

## 执行环境与命令

冻结检出中执行；没有切换 HEAD、修改产品代码、原 browser tests、原 runner、workflow、公共台账，未运行 Git 操作或触发 CI。

| CI 阶段 | 本次命令 | 实际结果 | 原始日志 |
|---|---|---:|---|
| 依赖安装 | `npm ci --cache D:\Codex项目\森爵照明管理系统\.worktrees\r1-prelaunch-consolidation-20261104\.tmp\review-npm-cache` | 退出码 0；安装 227 packages，审计 228 packages | `logs/npm-ci.log` |
| Node 全量 | `npm run test:unit` | 179 通过，0 失败，0 跳过；退出码 0 | `logs/frontend-node-unit.log` |
| 字体 Node 检查 | `node --test tests/detail-drawer-typography.spec.js` | 1 通过，0 失败，0 跳过；退出码 0 | `logs/frontend-font-node-test.log` |
| Vitest | `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js` | 78 files；725 通过，0 失败；退出码 0 | `logs/frontend-vitest.log` |
| 浏览器 | 见下方原 9-profile runner 结果 | 261 通过，2 失败，0 跳过；退出码 1 | `logs/playwright-profiles/` |
| 生产构建 | `npm run build` | 2024 modules transformed；退出码 0 | `logs/frontend-build.log` |

本机 Node 为 `v24.16.0`、npm `11.13.0`；CI workflow 配置 Node 22，本轮未安装/切换到 Node 22，版本差异是验收限制。隔离浏览器使用给定 Python 3.12.16 和 `OPS_TEST_OPENSSL=D:/Program Files/Git/usr/bin/openssl.exe`。

## Playwright：原 9 个 profile

专属协调 driver 复用了 `frontend/scripts/run-playwright-suite-stability.mjs` 的 9 个 profile 及原循环。业务大组原有 8 项隔离排除保持不变，只额外排除用户延期的 `iss037-print-output-acceptance.spec.js`；其他 ISS-037 规格仍在业务大组运行。原 runner 和测试文件未改。

每个 profile 均由原 isolated runner 建立临时 SQLite、合成媒体根和 fixture；没有连接实际业务数据库。

| Profile | 通过 | 失败 | 跳过 | 退出码 |
|---|---:|---:|---:|---:|
| business-suite | 237 | 1 | 0 | 1 |
| shared-report-templates-isolated | 1 | 0 | 0 | 0 |
| quote-editor-isolated | 0 | 1 | 0 | 1 |
| iss006-storage-isolated | 10 | 0 | 0 | 0 |
| iss007-attachment-isolated | 3 | 0 | 0 | 0 |
| iss007-image-snapshot-isolated | 1 | 0 | 0 | 0 |
| iss022-isolated | 1 | 0 | 0 | 0 |
| iss028-035-isolated | 2 | 0 | 0 | 0 |
| iss055-rbac | 6 | 0 | 0 | 0 |
| **总计** | **261** | **2** | **0** | **套件 1** |

合计为 263 次实际执行；这是逐 profile 日志汇总，不是预估值。所有 9 个 profile 的日志都记录了隔离 API/Vite 停止、端口释放和对应临时数据库/媒体目录清理。

本次 `iss007-attachment-isolated` 的 3/3 是原 runner 默认 Chromium 结果；主审另行准备的 `test.use({ channel: 'chrome' })`、CDP 路径/版本验收没有复制进冻结检出，也未由本报告代替。

### 浏览器实际通道

没有对原 runner 注入全局 Chrome 覆盖。business-suite 使用 `playwright.isolated.config.js` 的默认 Chromium；源码中声明 `test.use({ channel: 'chrome' })` 且本轮纳入该大组的文件为 `cash-duplicate-real.spec.js`、`finance-closeout.spec.js`、`finance-closeout-approval.spec.js`、`independent-bank-fee-real.spec.js`、`iss037-print-font-failure.spec.js`、`iss037-seller-freeze-real.spec.js`、`iss039-amount-allocation-real.spec.js`、`iss029-recipient-snapshot.spec.js`。延期的 `iss037-print-output-acceptance.spec.js` 虽声明 Chrome，但整份未运行。ISS-028/035 profile 则由原 runner 显式设为 Chrome，测试输出确认 `Google Chrome 156.0.8078.80 (chrome)`。因此本轮是 Chromium 与个别 Chrome 用例混合，不是全套 263 次都在 Google Chrome 上运行。

业务大组中保留并实际通过了 `iss037-print-font-failure.spec.js`（1 项）和 `iss037-seller-freeze-real.spec.js`（3 项）。`iss037-print-output-acceptance.spec.js` 整份未执行，状态为 `NOT_RUN_USER_DEFERRED`。用户指示称该文件有 6 场景；对冻结文件静态计数为 2 个直接测试加 5 个参数化用例，共 7 项。为遵守整份延期，7 项均未运行；该计数差异已如实记录，不通过测试或删改文件消解。

### 两项失败：留待主审判断

1. **财务导出**：`frontend/browser-tests/finance-closeout.spec.js:11`，`real account ledger at 1440px` 失败于第 75 行 `download.saveAs(...)`，错误为 `download.saveAs: canceled`。测试文件声明 `test.use({ channel: 'chrome' })`；同文件 390px 场景通过。错误上下文：`artifacts/c8a5564c-acc2-4a98-af28-0c8084aeb4a0/finance-closeout-real-account-ledger-at-1440px/error-context.md`。最小归属建议是财务 closeout 导出路径与浏览器下载生命周期；现有证据不能确认是哪一侧取消，需主审判断。
2. **报价导出**：`frontend/browser-tests/quote-editor-mobile-actions.spec.js:10`，保存/预览/导出场景失败于第 116 行 `download.saveAs(...)`，同为 `download.saveAs: canceled`。隔离 Django 日志显示 `/api/quotes/2/export/` 返回 HTTP 200；此 profile 使用 runner 默认 Chromium。错误上下文：`artifacts/fad2da1c-a261-4d7c-8073-96190d7cd2e3/quote-editor-mobile-action-261fe-reserve-preview-save-export/error-context.md`。最小归属建议是报价导出 UI 与浏览器下载生命周期；根因未证实，需主审判断。

两个失败均保留原始 profile 日志和 Playwright 错误上下文，均未重跑；本轮未修改财务、报价代码或测试断言。

## 延期及无效尝试记录

在浏览器通道纠正前，曾启动过一次 Chrome 注入版 business-suite。收到用户纠正后已中止，不计入上表；其用例数为 `UNKNOWN`，隔离临时目录通过 runner 的匹配 runId/token 清理函数清理。中止日志与输出移入 `logs/aborted-channel-override-20261105/`，状态为 `ABORTED_NOT_COUNTED`。有效 9-profile 结果全部来自随后不覆盖原 runner 通道选择的完整运行。

## 构建与依赖警告

- `npm ci` 输出 `glob@10.5.0`、`lucide-vue-next@1.0.0` 弃用警告，并报告 4 个 moderate audit 项；本轮没有运行 `npm audit fix`。
- Build 成功，但 Vite 提示主 JS chunk `1,146.13 kB` 超过 500 kB 阈值；该警告未影响构建退出码。
- `npm ci` 和 build 在冻结检出产生的依赖/构建产物留在该 detached checkout；没有复制到主树。仅下述封存证据目录复制到主报告。

## 证据文件

- Playwright 9-profile 汇总：`playwright-suite-summary.json`
- 综合机器可读结果：`FINAL-FRONTEND-447D.json`
- 每个 profile 的 stdout/stderr：`logs/playwright-profiles/<profile>.stdout.log` 与 `.stderr.log`
- 安装、Node、字体、Vitest、构建日志：`logs/`
- Playwright 截图、trace 和 error context：`artifacts/`、`browser/`、`cash-duplicate/`
- 中止尝试：`logs/aborted-channel-override-20261105/`
- 复制校验清单：`SEALED-EVIDENCE-MANIFEST.json`

未创建截图冒充延期打印验收；本报告不把来源分支或其他 checkout 的证据计入 447d 结果。
