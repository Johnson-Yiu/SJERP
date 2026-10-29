# R1-PLAYWRIGHT-SUITE-STABILITY-01

基线：`54e715bdc568b80ba624186fecd866550676cf38`  
分支：`codex/fix-playwright-suite-stability-20261029`

本报告记录隔离 Playwright 套件修复、全量计划用例结果、基础设施验证、失败对照及可复核日志。最终 199 项均执行并通过，编排器退出码为 0。测试按隔离边界分为五组：普通业务套件 189 项、共享报表模板 1 项、ISS-022 1 项、ISS-028/035 2 项、ISS-055 6 项；每组均由 `frontend/scripts/run-isolated-browser-tests.mjs` 管理独立 SQLite、媒体目录、Django API 和 Vite。

## 初始回归记录

用户提供的首轮记录为：计划 199 项、通过 186 项、初始失败 13 项。失败类别包括测试夹具缺失、隔离环境变量缺失、ISS-055 测试身份契约不匹配，以及测试完成后 Vite webServer 未退出。

基线仓库及当前工作区未找到该首轮执行的原始机器日志文件，因此没有补写或伪造那 13 项的堆栈输出。`logs/initial-run-reported.md` 保存了用户提供的原始摘要；`logs/pre-fix-webserver-reproduction.md` 保存了本任务中针对 Vite teardown 的独立复现记录。后续完整尝试的 stdout、stderr、阶段退出码见 `logs/` 和 `suite-run-summary.json`；首次 189/190 失败的日志单独归档在 `logs/suite-attempt-189-of-190-shared-report-timeout/`。

## 修复内容

- 扩展隔离运行器，允许在限定的业务测试文件集合中运行全量测试，并只为 allowlist 中的场景运行合成数据 seed；历史订单、ISS-022、ISS-075、ISS-028/035 和 ISS-055 的证据目录及环境变量均由运行器显式设置。
- 修复子进程环境契约：向 seed/API 统一传入 `ISOLATED_TEST_PYTHON`、`PYTHONPATH`、UTF-8 编码、隔离 SQLite `DATABASE_URL`、独立 `MEDIA_ROOT`、Vite/API 地址及运行身份；运行开始前后均校验 DB、媒体目录和 Vite 代理实际指向本轮隔离资源。
- 将 ISS-022、ISS-028/035 和 ISS-055 分别放入新建的隔离运行，避免共享套件中前置测试的数据影响这三组对列表数量或目录状态敏感的场景。ISS-035 单独运行时 2/2 通过，支持“共享运行数据交叉影响”的判定。
- ISS-055 使用每次随机生成的专用员工账号和密码、专用员工档案/角色/客户夹具，通过 Django 登录建立真实 session；受控配置仅启用该隔离运行的 RBAC，明确关闭开发超级管理员。浏览器直接验证 session、身份、数据范围和只读权限，不伪造 current-operator 响应。
- `test:browser` 改为调用隔离套件编排器；本地隔离配置不使用 Playwright `webServer`，而由运行器直接启动并跟踪本轮 Django/Vite 进程树，Windows 下仅按本轮 PID 清理。结束时验证两个端口已释放，再删除带有本轮 ownership marker 的临时 DB/media 根目录。标准 `playwright.config.js` 只在 `CI=true/1` 时保留原 CLI `webServer` 行为，以兼容现有工作流的 `npx playwright test`；没有修改工作流文件。
- 为隔离运行长期浏览器进程中的导航偶发失败，将共享报表模板测试单独放入新浏览器进程。它在首次 189/190 组运行末段遇到一次 `employee.reload()` 的 `net::ERR_ABORTED`，同一测试在全新隔离进程中单独通过，最终也在专属阶段通过；未调整断言、重试次数或 timeout。完整诊断目录现在写入本任务报告，不随临时根目录删除。
- 收货完成的模拟 API 夹具增加“请求已开始”信号；测试等待该信号后仍验证按钮禁用、重复点击只写一次及后续履约状态，消除事件循环时序竞态而不削弱断言。
- 未修改产品业务代码、正式权限配置或 CI 配置；没有删除或 skip 测试，也没有放宽断言或增加 timeout。

## 全量 Playwright 结果

| 阶段 | 用例 | 通过 | 失败 | 进程退出码 |
|---|---:|---:|---:|---:|
| 普通业务套件 | 189 | 189 | 0 | 0 |
| 共享报表模板隔离组 | 1 | 1 | 0 | 0 |
| ISS-022 | 1 | 1 | 0 | 0 |
| ISS-028/035 | 2 | 2 | 0 | 0 |
| ISS-055 真实员工会话/RBAC | 6 | 6 | 0 | 0 |
| **合计** | **199** | **199** | **0** | **0** |

汇总 JSON 为 `suite-run-summary.json`；各阶段完整日志为 `logs/<阶段名>.stdout.log`、`logs/<阶段名>.stderr.log`。失败尝试和首轮用户摘要对照见 [`failure-comparison.md`](failure-comparison.md)。浏览器截图附件（合成数据）位于 `browser-artifacts/iss067-report-permission/`。

## 隔离运行器验证

最终运行 `npm run test:browser:isolated:verify`：14/14 通过（包含端口冲突拒绝、身份和代理校验、受控夹具映射、并行运行隔离、进程树 teardown、临时 DB/media 清理验证；输出见 `logs/runner-validation-final-rerun.log`）。后端 `python manage.py test test_support.test_isolated_runtime`：13/13 通过，覆盖 ISS-055 受控 RBAC allowlist 和开发超级管理员关闭约束（`logs/backend-isolated-runtime-final-rerun.log`）。

## 运行环境与清理

当前工作站环境：Python 3.14.5、Django 6.0.8、Node.js 24.16.0、npm 11.13.0、Vite 8.3.5、`@playwright/test` 1.64.0、Chromium 156.0.8078.4。测试只访问本机回环地址及每轮临时 SQLite/MEDIA_ROOT。

最终阶段和单测复现涉及的 6 个带 ownership marker 的临时 DB/media 根目录均已不存在；对应 12 个 API/Vite 端口均无监听。每个阶段日志均确认本轮 API/Vite 进程树已停止。未连接生产服务、未触发 GitHub Actions，也未修改 `.github/workflows`、共享 Issue 台账或产品业务代码。
