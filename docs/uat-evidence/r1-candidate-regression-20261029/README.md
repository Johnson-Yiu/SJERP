# R1-CANDIDATE-REGRESSION-01 回归验收

日期：2026-10-29  
审查基线：`54e715bdc568b80ba624186fecd866550676cf38`  
分支：`codex/verify-candidate-regression-20261029`  
工作树：`.worktrees/candidate-regression-20261029`

本轮只做候选版本复测和证据归档，没有修改产品代码、依赖锁文件、共享台账、master，也没有触发 GitHub Actions 或连接现有业务数据库。测试使用本工作树专用 SQLite、MEDIA_ROOT 和本地开发身份。

## 环境与隔离

- C 盘测试前可用空间约 13.44 GB；D 盘约 103.93 GB。临时运行时、SQLite、媒体目录均放在本工作树的 D 盘目录；未清理用户数据。
- Python 3.14.5；锁定依赖安装到 `.candidate-runtime/venv`，测试完成后已移除。
- 前端使用 `npm ci --ignore-scripts --no-audit --no-fund`，未改写 `package.json` 或 `package-lock.json`。
- 后端数据库、媒体目录和 Playwright 隔离运行器均使用本轮专用路径；隔离运行器的标记临时目录由运行器自行清理。
- 本地开发身份按 [AGENTS.md] 的约定保持开发超级管理员，不伪造普通员工登录。

## 测试矩阵

| 层级 | 实际命令/范围 | 结果 |
| --- | --- | --- |
| Python 依赖 | `python -m pip install --requirement backend/requirements.lock` | 通过，锁定依赖安装成功 |
| Python 依赖 | `python -m pip check` | 通过：`No broken requirements found` |
| Django | `manage.py check` | 通过：0 issues |
| Django 迁移 | 全新 SQLite `manage.py migrate --noinput` | 通过，迁移到 `crm.0089` |
| Django 迁移 | `manage.py migrate --check`、`makemigrations --check --dry-run` | 均通过；`No changes detected` |
| Django 全量 | `manage.py test --verbosity 1`（清洁环境变量重跑） | 通过：1007 tests，18 skipped |
| 前端安装 | `npm ci --ignore-scripts --no-audit --no-fund` | 通过：227 packages |
| Node 单元 | `npm run test:unit` | 通过：169/169 |
| 贸易单位定向 | `npm run test:trade-units` | 通过：4/4 |
| Vitest 首次宽泛收集 | `npx vitest run --environment jsdom` | 失败：错误收集了 Node/Playwright/基础设施文件，44 files collection failures；不是产品断言失败 |
| Vitest 有效范围 | `npx vitest run tests --exclude "**/infrastructure-tests/**" --exclude "**/detail-drawer-typography.spec.js" --environment jsdom` | 通过：67 files，663/663 |
| 生产构建 | `npm run build` | 通过：2018 modules transformed；保留既有大 chunk warning |
| 隔离运行器验证 | `npm run test:browser:isolated:verify` | 通过：13/13 |
| 隔离基础设施冒烟 | `npm run test:browser:isolated` | 通过：1/1，含迁移、API/Vite 身份和代理路径检查 |
| 全量 Playwright | PowerShell：`$env:PLAYWRIGHT_CHANNEL='chrome'; $env:VITE_API_PROXY_PORT='55154'; npx.cmd playwright test --config=playwright.candidate-regression.config.js`（临时进程配置，运行后移除） | 199 scheduled；186 passed，13 initial failures；所有用例均已到达结果行，但 Vite webServer teardown 未退出，保留原始日志，未把它写成全量 PASS |

日志：

- [Python 安装](python-install.log)、[pip check](pip-check.log)
- [Django system check](backend-system-check-rerun.log)、[全新迁移](backend-fresh-migrate-rerun.log)、[迁移检查](backend-migrate-check-rerun.log)、[makemigrations 检查](backend-makemigrations-check-rerun.log)
- [后端首次失败原始日志](backend-full-test-first.log)、[后端清洁环境重跑](backend-full-test-clean-rerun.log)、[数据库设置定向重跑](backend-settings-rerun.log)
- [npm ci](frontend-npm-ci.log)、[Node 单元](frontend-node-unit.log)、[贸易单位](frontend-trade-units.log)、[首次宽泛 Vitest](vitest-first-broad.log)、[有效 Vitest](vitest-valid.log)、[生产构建](frontend-build.log)
- [全量 Playwright 首次端口失败](playwright-full-first.log)、[全量 Playwright 夹具重跑](playwright-full-fixture-rerun.log)

后端全量清洁重跑命令为 PowerShell：`$env:APP_STAGE='development'; $env:DJANGO_DEBUG='1'; $env:DEVELOPMENT_SUPERADMIN='1'; $env:RBAC_ENFORCEMENT='0'; $env:AUDIT_LOG_ENABLED='1'; $env:DATABASE_URL='sqlite:///.../evidence/backend-candidate.sqlite3'; $env:MEDIA_ROOT='.../evidence/media'; & $py manage.py test --verbosity 1`。路径中的 `...` 仅代表本工作树绝对路径，实际日志保留了 Windows 完整路径。

## 浏览器失败逐项复跑

首次全量运行的 13 项失败及结论如下。测试脚本和产品代码均未为“变绿”而修改。

| 用例 | 首次观察 | 单独重跑 | 分类 |
| --- | --- | --- | --- |
| `historical-orders-fix-02.spec.js` | 页面无历史订单夹具，`.analysis-detail-grid` 不存在 | 隔离运行器预置历史订单后 2/2 通过 | 环境/夹具缺失 |
| `historical-orders-fix-03.spec.js` | 无夹具导致 API 比对值为 `undefined` | 隔离运行器预置历史订单后 2/2 通过 | 环境/夹具缺失 |
| `iss022-moq-real.spec.js` | 120 秒超时；采购页没有 ISS-022 合成 SKU | 隔离运行器预置 MOQ/SupplierSKU 后 1/1 通过 | 环境/夹具缺失；非 MOQ 产品缺陷 |
| `iss075-payment-terms-real.spec.js` | 120 秒超时；页面没有 ISS-075 合成采购资料 | 隔离运行器预置历史付款计划后 1/1 通过 | 环境/夹具缺失；非付款规则产品缺陷 |
| `iss028-035-category-schema.spec.js`（2 项） | `ISOLATED_PLAYWRIGHT_BASE_URL` 未提供，`new URL()` 抛 `Invalid URL` | 设置真实隔离 URL、SQLite、Python 后 2/2 通过 | 测试启动契约/环境问题 |
| `iss029-recipient-snapshot.spec.js` | 未加载 ISS-029 fixture，买方邮箱收到空值 | 隔离运行器预置客户联系人后 1/1 通过；PI/XLSX 请求均完成 | 环境/夹具缺失；非快照产品缺陷 |
| `iss055-customer-404-real.spec.js`（6 项） | `/api/session/current-operator/` 返回 `development_superadmin=true`, `data_scope=all`；脚本硬编码要求 `false/self` | 使用全新 SQLite 和同一开发开关重跑，6/6 稳定复现同一差异 | 测试身份契约与 AGENTS 开发规则冲突；不是候选版本回归 |

ISS-028/035 的真实浏览器重跑证据保存在 [iss028-rerun](iss028-rerun/)；包含桌面/窄屏截图、HTTP 结果和 API/数据库快照。ISS-055 的六份原始失败上下文保存在 [playwright-failure-contexts](playwright-failure-contexts/)。

隔离业务运行日志：

- [ISS-022](isolated-iss022.log)、[ISS-075](isolated-iss075.log)
- [历史订单 FIX-02](isolated-historical-orders-fix-02.log)、[FIX-03](isolated-historical-orders-fix-03.log)
- [ISS-029](isolated-iss029.log)
- [隔离运行器验证](isolated-runner-verify.log)、[隔离冒烟](isolated-runner-smoke.log)
- [ISS-028/035 独立迁移](iss028-rerun-migrate.log)、[干净浏览器重跑](iss028-rerun-playwright-clean.log)
- [ISS-055 独立迁移](iss055-rerun-migrate.log)、[夹具 seed](iss055-rerun-seed.log)、[六项身份契约重跑](iss055-rerun-playwright.log)

## 首次失败保留与边界

1. 后端第一次全量测试的 11 项失败来自测试子进程继承了本轮错误设置的 `AUDIT_LOG_ENABLED=0`；失败集中在 `test_database_settings`，随后取消该变量并以 `AUDIT_LOG_ENABLED=1` 重跑，1007/1007 通过。首次日志未删除。
2. 首次宽泛 Vitest 命令收集了不属于 Vitest 的 Node/Playwright 文件；有效测试范围重跑后 663/663 通过。没有删除测试或放宽断言。
3. 默认 Playwright 端口 5195 首次启动收到 Windows `EACCES`；改用本轮专用端口只用于诊断，未修改全局 Playwright/Vite 配置。
4. 全量 Playwright 的最终进程在所有 199 个测试结果输出后卡在 webServer teardown，因而报告为“186 通过、13 初始失败、命令退出未收敛”，不是“全量通过”。
5. 本轮没有 PostgreSQL、GitHub CI、生产部署或正式非开发 RBAC 身份验收；ISS-055 的真实员工数据范围仍需进入对应权限验收任务。

## 结论

在固定 SHA 上未确认新的产品缺陷，没有实施产品代码或依赖修复。后端、锁定依赖、前端有效测试/构建和隔离业务浏览器场景均通过；候选版本仍不能标记为“全量浏览器 PASS”，原因是全量运行器 teardown 环境问题，以及 ISS-055 需要正式非开发身份而当前开发规则明确使用开发超级管理员。最终提交仅包含本报告和本轮真实浏览器/原始日志证据。
