# R1-REPAIR-06 — Playwright worktree 隔离

日期：2026-10-28

分支：`codex/repair-playwright-isolation`

基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`

## 结果

新增可复用的本地 Django API + Playwright 隔离启动器。只新增测试基础设施，不改业务代码、既有业务测试、共享项目台账、采购单或普通开发服务器配置。默认从空隔离库启动，不导入业务数据。

原 Playwright 配置使用固定 Vite 端口且可能复用已运行服务；Vite API 代理默认目标端口为 `8100`。新流程为显式选择的独立配置，不会复用这些服务。

## 隔离与拒绝策略

运行 `npm run test:browser:isolated` 时依次执行：

1. 检查本地 Vite/Playwright 依赖；给 API 和 Vite 分配不同的 loopback 端口，并在创建测试数据前实际 bind-probe。可用 `ISOLATED_API_PORT`、`ISOLATED_VITE_PORT` 指定端口；端口占用会立即退出，不创建数据库，也不尝试连接已有服务。
2. 在操作系统临时目录下创建本轮唯一目录，写入随机 run ID/token 所有权标记，并创建 `db.sqlite3` 与 `media/`。
3. 只为子进程设置 `APP_STAGE=development`、`RBAC_ENFORCEMENT=0`、明确的 SQLite `DATABASE_URL`、`MEDIA_ROOT` 和 Django 本地 `FileSystemStorage`。测试专用 settings wrapper 提供随机 token 身份探针；未修改生产 URLConf 或业务路由。
4. 在 `manage.py check` 和任何迁移前，对标记、实际 SQLite 引擎/路径、MEDIA_ROOT、开发环境及 RBAC 关闭状态进行校验。确认后才迁移本轮数据库，运行 `migrate --check`，并要求迁移后的 SQLite 文件真实存在。
5. 使用 `runserver --noreload` 启动 Django，使用 `strictPort` 启动 Vite。Playwright 启动前，分别核验 API、Vite 的随机身份，并经 Vite `/api` 代理再次核验 API 返回的数据库及媒体路径。任一端口冲突或身份不符均拒绝执行 Playwright。
6. 结束或失败时，只停止该 runner 创建的子进程。清理前再次核对临时路径、专属前缀、marker、run ID 和 token；归属不明即拒绝删除。支持 SIGINT/SIGTERM 清理流程。

数据库校验器在迁移/写入前拒绝非 SQLite 或额外数据库连接、指向临时运行目录之外的数据库或媒体路径、符号链接、外部媒体存储后端、错误 marker，以及非开发/RBAC 已启用的设置。

## 使用方式

在 `frontend/` 安装锁文件依赖并运行基础设施冒烟：

```powershell
npm ci
npm run test:browser:isolated
```

默认 Playwright config 只执行 `frontend/infrastructure-tests/isolated-runtime.spec.js`。选择已有真实 API 浏览器测试时，可将测试目录交给 Playwright，例如：

```powershell
npm run test:browser:isolated -- --test-dir=./browser-tests --grep "测试名称"
```

所选业务套件须自行通过 UI/API 创建合成 fixture，或另行审查与授权隔离种子流程。本 runner 不提供任意 seed 命令入口；现有测试配置中固定端口或复用服务的启动设置不会被加载，服务生命周期由隔离配置统一管理。

## 本地验证证据

环境：Windows、Node `v24.16.0`、Python `3.14`、Django `6.0.6`；前端依赖由现有 lockfile 的 `npm ci` 安装。Node 命令在 `frontend/` 执行，Python 单测在 `backend/` 执行。

| 命令 | 结果 |
|---|---|
| `node --check`（runner、隔离 Vite/Playwright config、冒烟 spec） | 通过 |
| `node --test infrastructure-tests/runner-validation.test.mjs` | 6 项通过：空闲端口、端口冲突/重复拒绝、SQLite URL、仅清理本轮目录、错误 marker 拒绝清理 |
| `python -m unittest test_support.test_isolated_runtime -v` | 9 项通过：合法隔离目标、外部/错误 DB、非 SQLite、额外 DB、正式 RBAC、外部媒体路径/存储、错误 marker 拒绝 |
| `npm run test:unit` | 162 项通过 |
| `npm run test:browser:isolated` | 通过：Django check、全部迁移至 `crm.0089`、`migrate --check`、API/Vite/代理身份与 DB/MEDIA_ROOT 匹配；Playwright smoke 1/1 通过 |
| `npm run build` | 构建通过；既有主 JS 1,126.03 kB，大于 500 kB 的 Vite chunk 警告仍存在 |
| `git diff --check` | 提交前通过 |

最终成功端到端运行：API `1542`、Vite `1543`，run ID `49e43f1f-8ede-4cae-8b68-d6fbe6eb2200`，临时根目录 `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-9uILeY`。API 探针返回的 `db.sqlite3`、`media/` 均位于该目录。runner 停止自身 Django/Vite 子进程并清理该 marker 目录，未触及其他服务或数据库。

实现过程中，第一次预检因 Windows SQLite URL 解析路径不一致而在迁移前拒绝；随后一次因测试 URLConf 没有被生产 settings 环境变量覆盖而在 Playwright 前以 404 拒绝。修正后上述最终运行通过；失败探针仅清理各自 marker 匹配的临时目录。`npm ci` 显示既有 `glob@10.5.0` 弃用警告；本轮未改依赖版本或 lockfile。

## 范围与遗留限制

- 未创建或修改任何采购单及业务资料。
- 未编辑其他工作树中的测试；`codex/repair-browser-navigation-timeouts` 保持未触碰。
- 未触发 GitHub Actions；未推送、合并、部署或关闭 Issue。
- 本报告不修改 `PROJECT_ISSUES.md`、`PROJECT_PHASES.md`。冒烟仅证明隔离服务、迁移、身份与代理链路，不等价于各业务浏览器套件的业务验收；所选套件仍须提供合成数据并独立验证。
