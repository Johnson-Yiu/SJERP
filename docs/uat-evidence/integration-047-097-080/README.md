# ISS-047 / ISS-097 / ISS-080 统一集成验收

日期：2026-10-27  
统一基线：`8b2b5c19e517addd9604b239211e199a789b739e`  
集成分支：`codex/integration-047-097-080`  
代码集成完成时的本地 HEAD：`512e739ac2beffe90e7153087509b2734c64e853`

## 集成范围

按 ISS-047 → ISS-097 → ISS-080 顺序，从指定提交逐项 cherry-pick：

| 任务 | 来源提交 | 本地集成提交 |
|---|---|---|
| ISS-047 私有文件存储 | `5ab3ed6dd740ba7331abb258118882d7c96e39b5` | `3cf5a81` |
| ISS-097 最高角色权限显示 | `9ee4bd4b1eb14f45e08a4b83f0b1cd1b294cde37` | `2f67e72` |
| ISS-080 联系人疑似重复提醒 | `efb2546b69ae4ace60715dcb97803145248d3a1b` | `d2d0a09` |
| ISS-080 证据及开发日志 | `9fe9f479bc47fd7470c80822c89fa59d7d71cbf5` | `512e739` |

ISS-080 没有直接合并旧分支，只移植了上述功能提交和证据/台账提交。未修改 master 或其他工作树。

## 冲突处理

实际冲突仅发生在 `docs/PROJECT_PHASES.md`：ISS-097 和 ISS-080 的文档提交分别与 ISS-047/ISS-097 的阶段记录相邻。均按段落保留三项任务记录，没有整文件覆盖；代码文件无冲突。`backend/crm/migrations/0088_operationlog_append_only.py` 和 `0089_operationlog_operator_protect.py` 均保留，未重写或新增重复迁移。

## 自动化验收

- `python manage.py check`：通过。
- `python manage.py makemigrations --check --dry-run`：通过，无模型差异。
- Django `crm` 全量：`950` 通过，`15` 跳过，`0` 失败。
- ISS-047 / ISS-097 / ISS-080 定向后端：`59` 通过，`1` 跳过；覆盖私有媒体、路径/权限、有效权限矩阵、联系人全量匹配和数据范围。
- 前端 Node：`npm run test:unit`，`154` 通过，`0` 失败。
- 有效 Vitest：`67` 个 suite、`659` 项通过；排除仓库中既有的 `tests/detail-drawer-typography.spec.js`（该文件是 `node:test` 文件，不包含 Vitest suite）。未将包含该既有配置问题的命令宣称为全量 Vitest PASS。
- 前端生产构建：`npm run build` 通过；保留既有大 chunk warning，未修改无关构建配置。
- Playwright CRM/RBAC 回归：`27` 通过；覆盖联系人重复提醒、跨筛选/分页、编辑自身、390px 页面，以及组织权限矩阵和错误状态。

## SQLite 迁移

- 全新 SQLite：从空库顺序迁移至最新版本，通过。
- 既有库升级：先迁移至 `0087_amount_calculation_compatibility`，再升级至最新版本，通过。
- 升级后确认 `0087`、`0088`、`0089` 均为 `[X]`。
- 迁移检查未发现重复或遗漏；真实 PostgreSQL 未在本机运行，本项不冒充 PostgreSQL 验收。

## 真实 Chrome 视觉证据

使用集成分支独立前后端服务（本地隔离 SQLite、开发超级管理员）在真实 Chrome 中检查桌面和 390px 窄屏。图片由同一集成服务的浏览器页面生成并提交，可独立查看：

- [ISS-080 桌面联系人重复提醒](screenshots/iss080-desktop-contact-duplicate.png)
- [ISS-080 390px 联系人重复提醒](screenshots/iss080-390-contact-duplicate.png)
- [ISS-097 桌面 24 模块权限矩阵](screenshots/iss097-desktop-permission-matrix.png)
- [ISS-097 390px 权限页面](screenshots/iss097-390-permission-matrix.png)

Chrome 实际观察确认：ISS-080 提示显示同客户重复原因、联系人入口和“非阻断提醒”；ISS-097 显示最高角色 `24 / 24`，所有复选框选中且不可编辑。390px 组织页保留现有侧栏和横向矩阵滚动行为；该页面在窄屏可操作但信息密度较高，后续可按独立 UI 复核决定是否继续收窄。

## 延期/待验事项

- ISS-047：真实生产 Nginx/反向代理、持久卷容量/inode 告警、服务重启、DB+媒体联合备份恢复及生产 PostgreSQL 仍为 `DEPLOYMENT_VERIFICATION_PENDING`。已在现有 ISS-047 台账记录更新，不创建重复 Issue。
- ISS-097：正式员工账号、生产会话和真实 RBAC 数据范围仍待独立环境验收；应用层权限不等于数据库、操作系统或服务器权限。已在现有 ISS-097 台账记录更新。
- ISS-080：当前浏览器使用开发身份和隔离合成数据；真实员工跨客户数据范围和生产业务数据抽查仍为 `BUSINESS_VERIFICATION_PENDING`，非功能失败。已在现有 ISS-080 台账记录更新。
- GitHub Actions：须以最终推送 HEAD 的 run/check 为准；如果测试步骤前失败，保留为 CI 环境待验，不能标记为 CI PASS。本地通过不替代 PostgreSQL 或部署验证。

## 边界

本轮未部署、未连接真实生产数据库、未改变银行资金事实、历史数据、权限执行策略或 ISS-043 审计防篡改规则；未关闭任何 Issue。
