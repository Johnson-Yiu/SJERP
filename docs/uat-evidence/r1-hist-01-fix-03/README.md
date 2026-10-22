# R1-HIST-01-FIX-03 验收证据

## 结论

本轮未发现历史分析业务代码缺陷，未修改后端报表逻辑、权限逻辑或数据模型。

根本原因是浏览器验收使用了旧的 8102 后端。旧服务的实际响应缺少 `by_country` 和 `by_category`，与当前分支代码不一致；截图中“销售汇总 17、可见 SKU 明细 1”的现象也来自前后端/数据快照不一致，而不是当前报表聚合结果。重新使用当前工作区启动的 8103 后端和当前分支前端后，国家/地区、SKU、产品分类明细均可见，数量与 API 响应一致。

验证基线：当前分支 `codex/r1-hist-01`，业务代码基线 `c4dcd79c5eeccf00d1cd08e496be99e1b924f7ef`（FIX-02）。本轮只增加验证用 Playwright 测试和验收证据，不改业务代码。

## 服务来源核对

- 当前后端从本工作区 `D:\Codex项目\森爵照明管理系统\.worktrees\r1-hist-01\backend` 启动：`python manage.py runserver 127.0.0.1:8103 --noreload`。
- 当前前端从本工作区启动 Vite：PowerShell `$env:VITE_API_PROXY_PORT='8103'; npm run dev -- --host 127.0.0.1 --port 5196`。
- Playwright 使用 `http://127.0.0.1:5196`，由 Vite 代理到 8103；配置文件为 `frontend/playwright.r1a.config.js`。
- 8102 仍有多个旧 Python 服务监听。Windows 对这些进程的命令行读取返回“拒绝访问”，因此不以进程名推测来源；实际接口响应已足以确认其版本过旧：`api-8102-response.json` 缺少 `by_country`、`by_category`。
- 当前 8103 响应见 `api-8103-current-response.json`，包含销售和采购两组国家/地区及产品分类维度。

## API 数据一致性

当前 8103 使用隔离开发数据库中的明确 FIX-03 测试数据，真实响应结果如下：

| 维度 | 汇总数量 | 明细数量 | 结果 |
| --- | ---: | ---: | --- |
| 历史销售 SKU | 21 | 4 + 17 = 21 | 通过 |
| 历史采购 SKU | 33 | 6 + 27 = 33 | 通过 |
| 历史销售国家/地区 | 加拿大、中国 | 400、1560 元 | 通过 |
| 历史采购国家/地区 | 日本、中国 | 180、845 元 | 通过 |
| 历史销售产品分类 | FIX03历史分类 | 400 元 / 4 件 | 通过 |
| 历史采购产品分类 | FIX03历史分类 | 180 元 / 6 件 | 通过 |

利润仍返回“不计算”，未用当前成本冒充历史成本。

## 自动化测试

### 后端

命令：

```text
cd backend
python manage.py test crm.tests.test_historical_orders --verbosity 1
```

退出码 `0`，`Ran 9 tests`，`OK`。测试输出见 `backend-historical-tests.txt`。

### 前端

命令：`npm run test:unit`

退出码 `0`，`142` 个测试通过，`0` 失败。

命令：`npm run build`

退出码 `0`，Vite 生产构建成功。仅有现有 chunk size warning，没有构建失败。详情见 `frontend-test-build.txt`。

### 当前分支 Playwright

命令：

```text
cd frontend
npx playwright test browser-tests/historical-orders-fix-03.spec.js --config=playwright.r1a.config.js --reporter=list
```

退出码 `0`，`2 passed`：

1. 700 CSS px 与 1440 CSS px 的分析明细、局部表格滚动和无横向溢出验证。
2. 权限受限时页面保持可用，隐藏无权明细，不显示采购入口。

截图：

- `playwright-700px.png`
- `playwright-desktop.png`
- `playwright-700px-permission-limited.png`

测试源文件：`frontend/browser-tests/historical-orders-fix-03.spec.js`。

## 环境及未完成事项

- 本轮没有重跑无关的 SQLite 全量测试，遵循 FIX-03 的范围限制。
- 未触发 GitHub Actions；CI 继续按项目约定保持 `PENDING`。
- 未使用 PostgreSQL；本轮目标是核实服务来源、历史分析一致性和当前前端响应式验收。
- 8102 旧服务未被本任务修改或停止，避免影响其他开发任务；后续浏览器验收应固定使用当前分支服务端口，或先清理旧服务。
