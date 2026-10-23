# ISS-067 报表旧 URL 与权限状态一致性核实

日期：2026-10-23  
分支：`codex/iss-067-report-permission`  
统一基线：`c356e57014d28295485d52df23612c2fe6c02444`

## 结论

在隔离权限场景和真实 Chrome 中未复现“无权来源仍作为有效已选择来源”或前端继续查询无权来源。保留现有报表生产代码、权限计算、金额计算、查询引擎和共享模板实现；本提交只增加复现/回归测试、测试日志和视觉证据。

ISS-067 仍保持 `P2 / NEEDS_VERIFICATION`，不自行关闭，等待独立审查。

## 核实场景

| 场景 | 实际证据 | 结果 |
|---|---|---|
| 管理员合法销售 URL | 旧 URL 含 `source=sales`、销售维度、日期和 `filter_country=China`，见 `iss067-report-permission.spec.js` | URL 合法 |
| 无订单查看权限员工打开旧 URL | UI fixture 只有 `reports.view`、`customers.view`；来源选择器只剩“客户增长”，当前值为 `customers` | 通过；无权 `sales` 未成为有效选择 |
| 用户提示 | 页面显示“地址中的报表来源当前不可查看，请重新选择查询。” | 通过 |
| 实际前端请求 | 无权旧 URL 首次加载和返回恢复均未发出 `/api/reports/data/?source=sales`；请求计数为 0 | 通过；没有数据泄露 |
| 后端强行请求旧 URL | `ReportingDimensionPermissionTests.test_old_sales_report_url_is_rejected_when_orders_view_is_revoked` 请求 `source=sales` 返回 HTTP 403，响应不含 `rows` | 通过；后端仍是最终边界 |
| 切换为有权来源并查询 | 查询后 URL 改为 `source=customers`，客户报表加载成功 | 通过；不扩大权限 |
| 刷新、返回、保存、重新载入 | 返回旧 URL 再次显示提示；切换后的合法来源可刷新、保存图表块、重新载入，合法筛选条件保留 | 通过 |
| ISS-042 共享模板 | 员工具备来源权限时，带 `shared_template` 的旧路径仍加载模板查询；既有管理者/员工跨会话回归通过 | 通过 |

## 自动化与浏览器证据

- Backend 报表 + 共享模板：**41/41 PASS**；系统检查通过。
- 后端新增旧销售 URL 拒绝测试：**1/1 PASS**。
- 报表相关 Vitest：**22/22 PASS**。
- 前端 Node 单元测试：**144/144 PASS**。
- 前端生产构建：**SUCCESS**；仅有既有大 chunk warning。
- ISS-067 真实 Chrome 场景：**2/2 PASS**。
- 既有报表中心 + ISS-042 共享模板真实 Chrome 回归：**16/16 PASS**，覆盖 1440/1280/1024/700、旧保存配置、URL/浏览器返回、下钻、保存和共享模板。

原始日志：

- `backend-reporting-shared.log`
- `frontend-vitest.log`
- `frontend-node.log`
- `frontend-build.log`
- `chrome-iss067.log`
- `chrome-existing-reports.log`

视觉证据：

- `employee-old-url-1440.png`：无权员工打开旧销售 URL，来源已切到合法客户来源并显示不可访问提示。
- `employee-old-url-700.png`：窄屏同场景，提示、选择器和保存区域无横向溢出。
- `employee-authorized-source-1440.png`：切换到有权来源后成功查询并保存图表块。

## 代码范围

- 未修改 `ReportsPage`、`ReportBlock`、报表注册表、后端报表查询/金额计算或共享模板服务。
- 新增一条后端权限拒绝回归，以及真实 Chrome 复现/回归用例。
- 不启用正式 RBAC，不改变开发超级管理员约定，不合并 `master`，不关闭 Issue。
