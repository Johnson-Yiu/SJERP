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
2. 在操作系统临时目录下创建本轮唯一目录，写入随机 run ID/token 所有权标记，并创建 `db.sqlite3`、`media/`、Vite 优化缓存及 Playwright `outputDir`。Vite 使用 runner 配置加载器避免写入 `node_modules/.vite-temp`；Playwright 报告/状态文件不写共享工作树目录。
3. 只为子进程设置 `APP_STAGE=development`、`RBAC_ENFORCEMENT=0`、明确的 SQLite `DATABASE_URL`、`MEDIA_ROOT` 和 Django 本地 `FileSystemStorage`。测试专用 settings wrapper 提供随机 token 身份探针；未修改生产 URLConf 或业务路由。
4. 在 `manage.py check` 和任何迁移前，对标记、实际 SQLite 引擎/路径、MEDIA_ROOT、开发环境及 RBAC 关闭状态进行校验；拒绝预先存在的数据库文件、符号链接和额外数据库连接。确认后才迁移本轮数据库，运行 `migrate --check`，并要求迁移后的 SQLite 文件真实存在。
5. 使用 `runserver --noreload` 启动 Django，使用 `strictPort` 启动 Vite。Playwright 启动前，先直连 Django 校验 run ID、token、SQLite 路径及 `MEDIA_ROOT`，再通过 Vite 端口的 `/api/__test__/isolation/<token>/` 真实代理再次校验相同四项。代理目标或身份字段不符时，在 Playwright 启动前拒绝。
6. 结束或失败时，只停止该 runner 创建的子进程。清理前再次核对临时路径、专属前缀、marker、run ID 和 token；归属不明即拒绝删除。支持 SIGINT/SIGTERM 清理流程。

数据库校验器在迁移/写入前拒绝非 SQLite 或额外数据库连接、指向临时运行目录之外的数据库或媒体路径、符号链接、外部媒体存储后端、错误 marker，以及非开发/RBAC 已启用的设置。

## 使用方式

在 `frontend/` 安装锁文件依赖并运行基础设施冒烟：

```powershell
npm ci
npm run test:browser:isolated
```

运行基础设施自测（端口占用、错误 API 身份、真实 Vite 错误代理目标、受限测试选择、SQLite 路径、资源归属清理，以及两个独立工作区并行启动）：

```powershell
npm run test:browser:isolated:verify
```

默认配置仍执行 `frontend/infrastructure-tests/` 下的基础设施冒烟测试。业务测试只能通过启动器的文件选择参数指定，不能覆盖服务、配置或 Playwright 参数：

```powershell
npm run test:browser:isolated -- --business-test import-ux.spec.js
```

选择器只接受 `frontend/browser-tests/` 下存在的单个 `.spec.js` 文件名；默认冒烟和业务套件都先完成 API、Vite、代理和数据库隔离核验。本 runner 不提供任意 seed 命令入口；业务套件须自行通过 UI/API 创建合成 fixture，或另行审查与授权隔离种子流程。旧文档中的 `--test-dir` 不是 Playwright CLI 支持的参数，现已替换为受限选择器。

## 本地验证证据

环境：Windows、Node `v24.16.0`、Python `3.14`、Django `6.0.6`；前端依赖由现有 lockfile 的 `npm ci` 安装。Node 命令在 `frontend/` 执行，Python 单测在 `backend/` 执行。

| 命令 | 结果 |
|---|---|
| `node --check`（runner、隔离 Vite/Playwright config、验证测试、冒烟 spec） | 通过 |
| `npm run test:browser:isolated:verify` | 初次实现时 10 项通过；FIX-01 复测 12 项通过，详见下节 |
| `python -m unittest test_support.test_isolated_runtime -v` | 10 项通过：合法隔离目标、外部/错误/预先存在的 DB、非 SQLite、额外 DB、正式 RBAC、外部媒体路径/存储、错误 marker 拒绝 |
| `npm run test:unit` | 初次实现时 166 项通过；FIX-01 复测 168 项通过 |
| `npm run test:browser:isolated` | 单次标准启动通过：Django check、全部迁移至 `crm.0089`、`migrate --check`、API/Vite/代理身份与 DB/MEDIA_ROOT 匹配；Playwright smoke 1/1 通过 |
| `npm run build` | 构建通过；既有主 JS 1,126.03 kB，大于 500 kB 的 Vite chunk 警告仍存在 |
| `git diff --check` | 提交前通过 |

标准单次运行：run ID `a4029d66-873b-4671-8b0f-5d85a5b712fb`，API `9105`、Vite `9107`，临时 SQLite `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-mQhOKx\db.sqlite3`，`MEDIA_ROOT` 为同目录下 `media/`。迁移完整性、API/Vite/代理身份及路径核验通过；Playwright smoke 1/1，通过后删除本轮临时根目录。

并行端到端成功运行（两个临时工作区分别启动，均完成迁移、身份/代理核对、Playwright smoke 1/1 并清理各自 marker 目录）：

| 工作区 | run ID | API / Vite | 临时 SQLite / MEDIA_ROOT |
|---|---|---|---|
| A | `c3fa2710-5413-443a-afe8-1ed8768d0f4e` | `9531 / 9532` | `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-duNseb\db.sqlite3` / `...\media` |
| B | `d039b0a0-d0b2-4fbd-9269-dd1f422b9064` | `9529 / 9530` | `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-Lsy2Bo\db.sqlite3` / `...\media` |

两个运行的身份、端口、SQLite 和媒体目录均不相同；迁移输出到 `crm.0089` 后 `migrate --check` 通过。runner 仅停止本次启动的 Django/Vite 子进程并清理各自临时目录，没有触及其他服务或数据库。首次并行试验使用共享 `node_modules` 链接，观察到 Vite 写共享 `.vite-temp` 的 `EPERM`；最终测试改为每工作区独立 node_modules 命名空间，并将优化缓存放入 run 临时目录后通过。

实现过程中，第一次预检因 Windows SQLite URL 解析路径不一致而在迁移前拒绝；随后一次因测试 URLConf 没有被生产 settings 环境变量覆盖而在 Playwright 前以 404 拒绝。修正后上述最终运行通过；失败探针仅清理各自 marker 匹配的临时目录。`npm ci` 显示既有 `glob@10.5.0` 弃用警告；本轮未改依赖版本或 lockfile。

## 范围与遗留限制

- 未创建或修改任何采购单及业务资料。
- 未编辑其他工作树中的测试；`codex/repair-browser-navigation-timeouts` 保持未触碰。
- 未触发 GitHub Actions；仅推送本任务分支；未合并、部署或关闭 Issue。
- 本报告不修改 `PROJECT_ISSUES.md`、`PROJECT_PHASES.md`。默认空库 smoke 不依赖业务数据，也不植入业务数据；所选业务套件必须在本轮隔离库内自行创建/验证所需的合成 fixture，不能假设存在历史业务数据。冒烟不等价于各业务浏览器套件的业务验收。

## R1-REPAIR-06-FIX-01 复核记录

独立审查发现：旧实现把 Vite-proxied API 检查 URL 指向了 Django API 直连端口，因此早期记录中的“代理验证”并未实际经过 Vite。本次修复保留直连检查，另向 Vite 的 `/api/__test__/isolation/<token>/` 发请求，并比较直连响应、代理响应与本轮预期中的 run ID、token、SQLite 文件路径和 `MEDIA_ROOT`。任一不符在启动 Playwright 子进程前拒绝。

| 验证命令 | 结果 |
|---|---|
| `npm run test:browser:isolated:verify` | 12/12 通过：含错误身份、错误配置/参数拒绝、四字段比较、真实 Vite `/api` 代理指向错误 SQLite/MEDIA_ROOT 时拒绝、端口冲突、仅清理本轮资源、双工作树并行启动 |
| `python -m unittest test_support.test_isolated_runtime -v` | 10/10 通过 |
| `npm run test:browser:isolated` | 通过；Django check、迁移和 migrate --check、直连身份及真实 Vite 代理四字段校验通过；基础设施 Playwright smoke 1/1 |
| `npm run test:browser:isolated -- --business-test import-ux.spec.js` | 通过；先完成同一套隔离验证，再执行 CSV 导入业务浏览器测试 6/6；测试 fixture 为合成数据 |
| `npm run test:unit` | 168/168 通过 |
| `npm run build` | 通过；主 JS 1,126.03 kB（gzip 393.55 kB）；保留既有大于 500 kB 的 chunk 警告。沙箱内首次运行因 `.vite-temp` 写入权限失败，获准仅对该构建命令提升权限后成功 |
| `node --check`（runner、Playwright config、验证测试）与 `git diff --check` | 通过 |

业务测试实跑 run ID：`131cc53e-3a32-4fe2-8551-d750a5c6756a`；API/Vite 端口 `13888/13889`；数据库及媒体路径均位于本次 `sunjack-r1-repair-06-RlhulM` 临时根目录，运行后已由启动器清理。默认 smoke run ID：`11aa539d-f91e-415b-8cf4-86bc0da9cb5a`；端口 `13832/13833`；其独立临时根目录 `sunjack-r1-repair-06-mAMVD0` 也已清理。负向代理测试另行启动本地 Vite 和错误上游，仅创建并删除自身临时目录，没有连接或改动其他工作树服务/数据库。

业务测试命令现只接受 `--business-test <name.spec.js>`，解析时验证文件位于 `frontend/browser-tests/` 且为常规文件；所有其他 CLI 参数（包括 `--test-dir`、`--config`、grep 和服务覆盖参数）均拒绝。Playwright 配置由启动器固定，默认基础设施 smoke 行为保持不变。
