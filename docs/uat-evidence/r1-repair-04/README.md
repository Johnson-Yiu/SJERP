# R1-REPAIR-04-FIX-01 浏览器导航超时修复验收

## 范围与版本

- 目标分支：`codex/repair-browser-navigation-timeouts`
- 远端 HEAD 核实：`ce6bbf5a05d47000a06962b0bf2f444d84e7e5ca`，与用户给定当前 HEAD 一致
- 独立 worktree：`C:\Users\Johnson\.codex\worktrees\repair-browser-navigation-timeouts\森爵照明管理系统`
- 目标测试：`finance-reference-basis.spec.js`、`iss041b-evidence.spec.js`、`inventory-ux.spec.js`
- 本轮未修改产品业务代码、共享 `PROJECT_ISSUES.md` / `PROJECT_PHASES.md`、master 或全局 Playwright/Vite 配置。

## 修复内容

独立审查确认 `r1-repair-04-diagnostics.js` 中两个字体拦截的 `page.route()` 原先没有等待，三个目标测试的 `beforeEach` 也没有等待诊断安装完成，存在 `page.goto` 与路由注册竞态。

本轮改动：

1. `installRepair04Diagnostics` 改为 async，并对 `fonts.googleapis.com`、`fonts.gstatic.com` 两次路由注册显式 `await`。
2. finance、ISS-041-B、inventory 三个目标测试的 `beforeEach` 均 `await installRepair04Diagnostics(...)`。
3. 保留原有业务断言、诊断事件、截图与诊断 JSON 输出；仅增加 `fontInterceptions` 记录，便于验证实际拦截。
4. 新增 `r1-repair-04-routing.spec.js`：在调用 `page.goto` 前断言路由已注册，再加载包含 Google Fonts CSS 的 data URL，并断言字体请求实际被拦截。

没有增加 timeout，也没有修改产品代码或降低业务断言。

## 定向注册验证

```text
PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/r1-repair-04-routing.spec.js --config=playwright.config.js --workers=1 --reporter=line
PASS — 1 passed — 3.0s
```

该用例在导航前断言 `fontRoutesRegistered === true`、拦截计数为 0；`page.goto` 后拦截计数大于 0，证明注册已在导航开始前完成且路由实际生效。

## 三组目标测试

以下均使用真实 Chrome 通道、单 worker，未增加测试 timeout：

| 测试组 | 结果 |
| --- | --- |
| `finance-reference-basis.spec.js` | PASS，2/2 |
| `iss041b-evidence.spec.js` | PASS，2/2 |
| `inventory-ux.spec.js` | PASS，9/9 |

对应截图及 `*-diagnostics.json` 均保留在本目录。最新诊断 JSON 的 `fontInterceptions` 字段记录了实际被拦截的 Google Fonts 请求；正常流程 API 响应为 2xx，inventory 错误场景中的 500 仅来自测试明确模拟的失败。

## 历史失败结论

历史记录中的导航超时发生在 `/finance`、`/reports`、`/inventory` 的 `page.goto` 等待 `load` 阶段。当前三组在不修改业务断言、不增加 timeout 的前提下稳定通过，说明本修复消除了测试侧字体路由注册竞态；本轮没有证据表明存在产品导航性能缺陷。

## 证据与限制

- [测试日志](test-results.md)
- [finance 1024 截图](finance-reference-basis-1024.png)、[finance 1440 截图](finance-reference-basis-1440.png)
- [ISS-041-B 700 截图](reports-detail-700.png)、[ISS-041-B 1440 截图](reports-detail-1440.png)
- inventory 概览与台账截图见本目录对应 PNG 文件；诊断 JSON 保存控制台、页面错误、失败请求和 API 响应。
- 外部 Google Fonts 被测试 helper 按设计拦截，页面使用本地 fallback；这不代表生产环境已验证外部字体网络策略。
- 未运行 GitHub Actions、CI、部署或生产数据库验证。
