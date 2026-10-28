# R1-REPAIR-04 浏览器导航超时修复验收

## 范围与版本

- 基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
- 分支：`codex/repair-browser-navigation-timeouts`
- Worktree：`C:\Users\Johnson\.codex\worktrees\repair-browser-navigation-timeouts\森爵照明管理系统`
- 本报告对应最终提交：见本文件所在提交的 Git SHA
- 范围：`finance-reference-basis.spec.js`、`iss041b-evidence.spec.js`、`inventory-ux.spec.js`
- 未修改共享台账、master、全局 Playwright/Vite 配置或产品页面代码。

## 原始复现与结论

历史集成记录中的三个失败均为 `page.goto` 等待 `load` 超过 30 秒：

| 用例 | 历史失败视口 | 历史记录 |
| --- | ---: | --- |
| finance-reference-basis | 1024 | `/finance` 导航等待 `load` 超时 |
| iss041b-evidence | 700 | `/reports` 导航等待 `load` 超时 |
| inventory-ux | 1280 | `/inventory` 导航等待 `load` 超时 |

首次在全新 worktree 运行时，因 worktree 没有安装依赖，Playwright 报 `Cannot find package '@playwright/test'`；这属于环境前置缺失，不是产品或测试断言失败。执行 `npm ci --ignore-scripts --no-audit --no-fund` 后，未修改原有断言的原始测试分别通过：finance 2/2、ISS-041-B 2/2、inventory 9/9。

诊断显示页面业务 API、页面状态及资源加载均正常；唯一稳定失败的是外部 Google Fonts 请求。该 CSS 资源是可选字体，页面已有本地 fallback。为使本轮隔离回归不依赖外部字体可达性，新增仅供这三个测试使用的诊断 helper，在测试页面上下文拦截 `fonts.googleapis.com` 与 `fonts.gstatic.com`，同时记录请求、API 响应、控制台及页面错误。没有增加 timeout、降低断言或修改全局测试基础设施。

因此本轮未确认产品缺陷，也未确认测试契约过时；确认的是测试环境对外部可选字体资源的依赖会放大导航等待的不稳定性。若后续要求产品完全不访问外部字体，应另立页面/CSS 任务处理，不在本任务扩大范围。

## 本轮改动

- 新增 `frontend/browser-tests/r1-repair-04-diagnostics.js`：三个目标测试共用的、局部的网络/控制台/API 诊断与可选字体拦截 helper。
- 三个目标测试增加 `beforeEach/afterEach` 诊断输出和本轮实际截图；既有业务断言保持不变。
- 未修改 `playwright.config.js`、Vite 配置、生产页面、共享台账或其他模块。

## 验收结果

| 测试 | 结果 | 说明 |
| --- | --- | --- |
| `finance-reference-basis.spec.js` | PASS，2/2 | 1440、1024 |
| `iss041b-evidence.spec.js` | PASS，2/2 | 1440、700 |
| `inventory-ux.spec.js` | PASS，9/9 | 1440、1280、1024及错误/权限场景 |
| 有效 Vitest 定向集合 | PASS，71/71 | 5 个相关测试文件 |
| `npm run test:unit` | PASS，156/156 | 既有单元测试入口 |
| `npm run build` | PASS | 既有大 chunk warning，无构建失败 |

诊断 JSON 中，正常流程 `pageErrors=0`、API 无非 2xx 响应；inventory 的错误场景只包含测试明确模拟的 5xx 响应。字体拦截产生的 `ERR_FAILED` 已按预期记录，不作为产品 API 错误。

## 截图与诊断证据

本目录下的 PNG 均由本轮 Playwright 在真实 Chrome 通道生成：

- [finance 1024](finance-reference-basis-1024.png)、[finance 1440](finance-reference-basis-1440.png)
- [ISS-041-B 700](reports-detail-700.png)、[ISS-041-B 1440](reports-detail-1440.png)
- [inventory overview 1280](inventory-overview-1280.png)、[inventory overview 1024](inventory-overview-1024.png)、[inventory overview 1440](inventory-overview-1440.png)
- [inventory ledger 1280](inventory-ledger-1280.png)、[inventory ledger 1024](inventory-ledger-1024.png)、[inventory ledger 1440](inventory-ledger-1440.png)

同目录的 `*-diagnostics.json` 保存了每个测试的控制台、页面错误、失败请求及 API 响应。视觉检查确认报表窄屏、库存概览/台账及详情区域均可见，没有因本轮处理新增横向布局问题。

## 限制与后续风险

- 本轮按要求不触发 GitHub Actions、不部署、不执行 PostgreSQL/CI 验证。
- 外部 Google Fonts 在当前测试环境不可稳定访问；应用 fallback 字体可用，但生产网络策略未在本任务验证。
- 结果仅证明本基线与本地隔离 Chrome 回归通过，不替代 R1-REPAIR-06 对全局测试基础设施的工作。
