# R1-INTEGRATION-036-002-003-052-058 综合集成验收

日期：2026-10-27（Asia/Shanghai）

基线：`46353a5436637832f5adadb7bdef6b45cdeada23`

集成分支：`codex/integration-036-002-003-052-058`

## 来源核对与集成内容

集成前通过 GitHub 分支提交页核对了五个来源分支的实际 HEAD；均与任务指定值完全一致。集成工作树从固定基线创建，五个原分支和 master 均未修改。

| Issue | 来源分支 | 核实的来源 SHA | 集成内容 |
|---|---|---|---|
| ISS-036 | `codex/fix-iss036-snapshot-conflicts` | `b64c54b07908d4bb462c64f120c351d148e06f6f` | 历史交易单位快照语义冲突处理、装箱 API 回归和验收证据 |
| ISS-002 | `codex/audit-iss002-dependency-security` | `4e4ca504ee398da85fe23cc53d534c6008807e5c` | 依赖安全报告、Django/DRF 安全下限、精确前端依赖和锁文件 |
| ISS-003 | `codex/verify-iss003-employee-permissions` | `2111d193ef3a69db05c23e27813cfbf26d9034d7` | 员工权限与数据范围隔离验收报告；不启用正式 RBAC |
| ISS-052 | `codex/verify-iss052-csv-import` | `93736e0773ca2136d4070a604e62324cf832dc6f` | CSV 错误行中文映射、回归、四类导入报告及七张真实浏览器截图 |
| ISS-058 | `codex/measure-iss058-frontend-performance` | `742692a6e4887e4b8352736e69a52b1ebe8d066f` | 前端性能基线报告 |

`docs/PROJECT_ISSUES.md` 在 ISS-002 合并时发生内容冲突。已逐条合并 ISS-002 与 ISS-003 的不同核实记录和关闭条件，并保留两个任务的证据与状态；没有选择某一分支文件覆盖另一方。ISS-036、ISS-052、ISS-058 的最新核实项已补上来源 SHA、证据链接及后续动作。`docs/PROJECT_PHASES.md` 保留所有来源历史记录，并追加本轮记录。

ISS-052 的七个截图经文件签名确认以 `FF D8 FF` 开头，均为 JPEG 数据。集成工作树中仅通过 Git 重命名为 `.jpg` 并同步 README 链接，没有重新编码或制作图片。推送后通过 GitHub 内容 API 核对截图目录恰有七个 `.jpg` 文件，并逐个读取远端内容、验证 JPEG 签名；GitHub 当前浏览器会话打开私有仓库页面返回 `Page not found`，因此本轮无法在网页 UI 中目视确认图片预览。文件在 GitHub API 上存在且内容签名正确，但网页预览检查仍需有仓库访问权的浏览器会话复核。

## 本地环境与后端结果

Python 使用隔离虚拟环境 `Python 3.12.14`，从 `backend/requirements.txt` 干净安装；解析版本包括 Django `6.0.9`、Django REST Framework `3.18.3`、Pillow `11.3.0`。`DATABASE_URL` 指向临时目录中的 SQLite 文件；没有连接用户业务库。测试运行结束后 Django 已移除临时 test database。

| 命令 | 结果 |
|---|---|
| `python manage.py check` | 通过，无系统检查问题 |
| `python manage.py makemigrations --check --dry-run` | 通过，`No changes detected` |
| `python manage.py test` | 989 项运行，18 项跳过，0 项失败 |

全量套件覆盖实际装箱、CSV 导入、员工权限和销售/采购数据范围隔离。SQLite 全量测试通过不替代 PostgreSQL CI 验收。ISS-003 所需真实员工会话、真实组织树、生产 PostgreSQL、部署层会话/文件 URL 和真实员工 UI 仍未验收。

## 前端结果

| 命令 | 结果 |
|---|---|
| `npm ci` | 通过；安装 227 个包。安装日志有 `glob@10.5.0` 与 `lucide-vue-next@1.0.0` 弃用提示；本轮保留两项现状，不迁移图标包 |
| `npm audit` | 通过，0 vulnerabilities |
| `npm audit --omit=dev` | 通过，0 vulnerabilities |
| `npm run test:unit` | 通过，156 项 |
| `node --test tests/detail-drawer-typography.spec.js` | 失败，1 项：断言 `src/components/OrderDetailModal.vue` 出现未预期的 `font-size:11px`。这是当前集成源树中的既有失败，本轮未修改无关页面 |
| `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js` | 通过，67 个测试文件、661 项 |
| `npm run test:trade-units` | 通过，4 项 |
| `npx playwright test` | 失败，184 项中 164 项通过、20 项失败；详情见下方 |
| `npm run build` | 通过，2018 个模块转换；出现主 chunk 大于 500 kB 的 Vite 警告 |

Playwright 失败摘要（按失败断言归组；viewport 展开后共 20 项）：

1. `final-cross-module-ux.spec.js`：报价和订单页在 1440/1280/1024 三种宽度下都未找到“照明工程采购长名称客户有限公司”表格单元格，共 6 项。
2. `finance-reference-basis.spec.js` 1024 宽度：打开报表 URL 时等待页面 `load` 超时 30 秒。
3. `historical-orders-fix-02.spec.js`：未找到 `.analysis-detail-grid`。
4. `historical-orders-fix-03.spec.js`：历史报表请求收到 HTML，测试按 JSON 解析时遇到 `Unexpected token '<'`。
5. `inventory-ux.spec.js` 1280 宽度：打开 `/inventory` 等待页面 `load` 超时 30 秒。
6. `iss022-moq-real.spec.js`：真实采购 MOQ 场景超时 120 秒。
7. `iss029-recipient-snapshot.spec.js`：预期买方邮箱 `primary@example.com`，实际为 `uat-alpha@example.test`。
8. `iss041b-evidence.spec.js` 700 宽度：打开 `/reports` 等待页面 `load` 超时 30 秒。
9. `iss075-payment-terms-real.spec.js`：供应商付款规则真实浏览器场景超时 120 秒。
10. `supplier-ux.spec.js`：1440/1280/1024 三种宽度均未找到预期的 `.terms-description` 文案，共 3 项。
11. `supplier-ux.spec.js` 新建供应商：测试读取 `state.posts[0].payment_terms_config.map` 时该字段为 undefined。
12. `supplier-ux.spec.js` 比例失败场景：没有找到名为“比例 % 1”的 spinbutton。
13. `supplier-ux.spec.js` 筛选分页场景：URL `termsMode=custom&page=2` 下预期 1 行，实际 25 行。

Playwright 期间 Vite 还输出 `OrderDetailModal` 在 `<Transition>` 中返回非元素根节点的 Vue 警告。本轮记录测试与运行输出，不据失败本身推断新的产品缺陷，也未扩展为范围外修复。

## ISS-058 构建体积复测

集成依赖 `vite 8.3.5` 下重新执行 `npm run build`。主 JS 为 `frontend/dist/assets/index-CSX7Z4_9.js`，原始大小 `1,126,035` bytes，gzip `393,552` bytes。原报告基线为 `1,126,218` / `393,477` bytes：原始包减少 `183` bytes，gzip 增加 `75` bytes，约 `-0.016%` / `+0.019%`，包体基本持平。

构建仍报告某些压缩后 chunk 超过 500 kB。真实公网、TLS/CDN、低端设备 CPU 与受限网络下的可重复加载及交互性能均未测量；不能据此次构建或单次包体数据声称用户体验改善。按任务边界，本轮没有做性能重构。

## 安全与验收状态

- ISS-002 保持 `NEEDS_VERIFICATION`。Pillow `11.3.0` 仍在 `<12` 约束内，并可从图片上传、缩略图及 Excel 图片路径触达；本轮没有跨大版本升级。Python 依赖没有完整 lock 方案，仍须验收解析冻结和生产环境风险。前端两项 npm audit 为 0 不等于 ISS-002 全部安全结论通过。
- ISS-003 保持 `BLOCKED`。真实员工身份、正式组织与生产环境权限验收缺口未改变；未启用正式 RBAC。
- ISS-036 保持 `FIXED_PENDING_REVIEW`。等待独立代码、业务和视觉复审；冲突历史快照业务归属仍待明确。
- ISS-052 保持 `NEEDS_VERIFICATION`。开发身份 `authenticated=false`、`AUDIT_LOG_ENABLED=false`、`OperationLog=0`；持久化导入批次和行级 before/after 审计未通过，仍是验收缺口。
- ISS-058 保持 `P3 / NEEDS_VERIFICATION`。包体基本持平，Vite chunk 警告仍在，没有代表性真实用户性能数据。

## GitHub Actions 与收尾状态

首次集成提交 `4a83ec1455cbe4e927ae39252477fa095cf329ca` 推送后，GitHub Actions 运行 [CI #40535678568](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40535678568)，事件为 `push`，head SHA 与该提交一致。`backend`（job `122300149745`）、`backend-postgres`（`122300149687`）和 `frontend`（`122300149370`）均在约 3 秒内 `failure`；三个 GitHub job 对象均为 `runner_id=0`、`steps=[]`，没有可读取的运行日志。三项 check-run 均有同一条 GitHub 原始 failure annotation：`The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings`。这确认是账户近期付款失败或消费限额不足导致启动被拒；原始消息未区分具体是哪一种。三项 CI 均标记 `BLOCKED`，不能以本地测试替代。仓库所有者需手动检查 GitHub `Billing & plans` 后再对精确提交重跑；本轮未修改账单、仓库策略或工作流。

文档更新提交 `7ff7fdb51fba99796a6823817774d1ddfdb2eeaa` 的 [CI #40536898954](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40536898954) 再次精确匹配 head SHA；`backend`、`backend-postgres`、`frontend` 三个 job 均 `failure`，各在 2–3 秒内结束且 `runner_id=0`、`steps=[]`。三个 check-run 都返回上述同一条账单/消费限额 failure annotation。最终交付提交还会单独核验；CI 仍为账户账单/额度导致 `BLOCKED`。

集成过程中没有新增迁移；两个共享文档历史记录均保留。Playwright 生成并覆盖的其他历史截图已恢复到基线；最终差异仅保留五项任务所需代码、测试、报告、依赖及本轮集成记录。未合并 master、未关闭 Issue、未部署、未连接业务数据库，等待独立审查。
