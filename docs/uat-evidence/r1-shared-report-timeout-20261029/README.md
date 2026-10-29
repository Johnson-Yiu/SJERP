# ISS-042 共享报表刷新超时专项验收记录

- 日期：2026-10-29
- 固定基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 分支：`codex/r1-fix-shared-report-timeout-20261029`
- 工作范围：仅目标浏览器 spec 和专属验收证据；未修改业务代码或共享台账。

> 本记录汇总实现者的独立隔离复现与验收证据，仍待另一位审查者复核，不代表独立代码审查或关闭 ISS-042。

## 结论

根因为浏览器导航等待 `load`，而不是共享模板业务同步断言：页面样式表 [`frontend/src/styles.css`](../../../frontend/src/styles.css) 通过 `@import` 引入 Google Fonts 的 DM Sans 与 Noto Sans SC。外网字体链无法完成时，刷新即使已到 `readyState=interactive` 仍迟迟不触发 `load`，原 `employee.reload()` 因此耗尽既有 30 秒默认超时。

诊断日志在模板更新后的 reload 捕获到 12 个未完成的 Noto Sans SC 字体分片请求，均为 `GET https://fonts.gstatic.com/s/notosanssc/v41/...woff2`（分片编号 `.117`、`.116`、`.115`、`.114`、`.107`、`.110`、`.113`、`.111`、`.112`、`.109`、`.108`、`.106`）；取消发布后的第二次捕获仍有 10 个 gstatic 分片 pending。两次快照均未显示未完成的 `fonts.googleapis.com` CSS 请求。也就是说，CSS `@import` 是字体资源链入口，但现有诊断证据指向其后的 gstatic 字体二进制请求卡住；没有证据表明 CSS 请求本身在刷新时仍 pending。

修复在 manager 与 employee 两个页面各自的 `page.goto` 前拦截 `https://fonts.googleapis.com/**` 和 `https://fonts.gstatic.com/**`，并让 Playwright 按原生 abort 处理。测试页面会使用现有字体栈中的 `sans-serif` fallback。字体仅影响可选字形/外观，既不参与模板数据，也不参与业务状态；拦截仅限定于该 spec 的页面，不修改产品 CSS、浏览器全局设置或服务端。该处理切断不稳定的公网字体依赖，使导航完成时间不再取决于外网字体下载。

原 spec 的模板创建、草稿、发布、跨会话可见性、员工权限入口、应用模板、保存图表块、更新同步、操作历史、版本冲突、取消发布和删除等业务断言均保留；所有三处 `employee.reload()` 及默认 30 秒时限未改。

## 复现与修复回归

使用项目既有 `test:browser:isolated` runner；修复验收命令为 `npm run test:browser:isolated -- --business-test shared-report-templates.spec.js`，并设置 `PLAYWRIGHT_CHANNEL=chrome`、`ISOLATED_TEST_PYTHON=C:\Python314\python.exe` 与 `ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT=docs/uat-evidence/r1-shared-report-timeout-20261029`。每轮均创建独立 SQLite 数据库及 `MEDIA_ROOT`，迁移和迁移后身份校验通过，API/Vite 及代理身份校验通过；runner 在结束时清理该轮临时数据库和媒体目录。固定原时限，没有添加延长 timeout 的参数。

| 轮次 | Playwright run ID | 结果 |
|---|---|---|
| 原始失败复现 | `350f2994-c492-411e-9c1a-0c116f947d84` | 隔离环境校验通过；原始 spec 在 `employee.reload()` 等待 `load` 30.0 秒后失败。日志保留完整 runner 输出和 Playwright error context。 |
| DOMContentLoaded 诊断 | `e82ecfc3-ce6e-4c91-978e-eaa2cb022b3c` | 临时诊断版本改为 `waitUntil=domcontentloaded` 仍在原 30 秒失败；记录 `readyState=interactive` 及上述 gstatic pending URL。该轮只用于诊断，不是修复后的验收。 |
| 修复后原断言回归 | `400e1f3b-ea51-46e8-885e-1986f6749c4c` | 原 spec、原断言、原时限在实际 Chrome 下 `1 passed (14.6s)`；隔离迁移、身份验证和代理验证均通过。 |

修复回归使用的临时隔离路径为 `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-PhvDw9\db.sqlite3` 和同目录下的 `media`。原始复现使用 `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-NpUjBg\db.sqlite3` 和同目录下的 `media`。均由 runner 在各轮结束后移除。测试通过 `ISOLATED_TEST_PYTHON=C:\Python314\python.exe` 执行；该环境 Django 版本为 6.0.6，低于项目 requirements 所列版本，见风险说明。

## 代码与视觉验收

代码变更仅为 `frontend/browser-tests/shared-report-templates.spec.js`：新增 `blockOptionalGoogleFonts(page)`，分别在 manager、employee 的初始导航前安装两条路由。未更改任何业务断言、reload 语句、断言顺序或 timeout。

检查了修复后实际 Chrome 截图：员工 700px、管理员 1440px 与 1024px；报表及共享模板完整显示，桌面和窄视口页面均有内容。窄屏 full-page 截图可见固定顶栏覆盖纵向捕获中的页面内容，这是既有 fixed-header 与 full-page screenshot 的组合，不是本次测试代码修改引起的 UI 变化。本任务只改浏览器测试，不涉及页面或可见文案修改。

## 证据索引

- 原始失败日志：[baseline-reproduction.log](baseline-reproduction.log)
- 原始失败 Playwright context：[baseline error-context.md](artifacts/350f2994-c492-411e-9c1a-0c116f947d84/shared-report-templates-se-bc410--published-query-definition/error-context.md)
- 原始失败过程截图：[baseline-employee-700px.png](baseline-employee-700px.png)
- DOMContentLoaded 网络诊断日志：[domcontentloaded-diagnostic.log](domcontentloaded-diagnostic.log)
- DOMContentLoaded 诊断 Playwright context：[diagnostic error-context.md](artifacts/e82ecfc3-ce6e-4c91-978e-eaa2cb022b3c/shared-report-templates-se-bc410--published-query-definition/error-context.md)
- 修复后真实 Chrome 测试日志：[fixed-browser-test.log](fixed-browser-test.log)
- 修复后员工 700px 截图：[fixed-employee-700px.png](fixed-employee-700px.png)
- 修复后管理员 1440px 截图：[fixed-manager-1440px.png](fixed-manager-1440px.png)
- 修复后管理员 1024px 截图：[fixed-manager-1024px.png](fixed-manager-1024px.png)
- 删除模板后的员工状态：[fixed-employee-700px-after-delete.png](fixed-employee-700px-after-delete.png)
- 诊断过程中的员工/管理员页面截图：`diagnostic-employee-700px.png`、`diagnostic-manager-1440px.png`、`diagnostic-manager-1024px.png`

## 范围与风险

- 未运行单元测试或生产构建：改动仅为 Playwright 测试路由；已用目标 spec 原有完整业务断言在隔离环境回归。
- 运行时 Python 为全局 Python 3.14 / Django 6.0.6（本机目标 worktree 无项目虚拟环境），与 requirements 的 Django 6.0.9 有版本差异；系统检查、全量迁移和隔离身份验证均通过，但这不是在项目指定 Python/Django 环境下的后端兼容性证明。
- 此修复稳定的是该 spec 的导航，不会修复产品在公网不可达时无法取得 Google Fonts 的情况；应用应继续依靠 CSS fallback 显示。其他测试若依赖外部字体，也需各自在自己的页面上隔离网络依赖。
- 未触发 GitHub Actions，未创建 PR，未推送，未合并 `master`，未部署。ISS-042 仍为 `FIXED_PENDING_REVIEW`，等待独立复审。
