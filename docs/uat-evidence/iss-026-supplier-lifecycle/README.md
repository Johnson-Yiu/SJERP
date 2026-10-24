# ISS-026 供应商生命周期验收

日期：2026-10-24
基线：`71ec4a4c2d860b9944624a1434d9d7580e9a6d38`
分支：`codex/iss-026-supplier-lifecycle`
状态：`FIXED_PENDING_REVIEW`

## 实施范围

- `Supplier.is_active` 与迁移 `0081_supplier_lifecycle`。
- `SupplierViewSet` 的 `activate` / `deactivate` 事务动作、审计和 `DELETE` 405 防护。
- 采购候选、Supplier SKU 候选、历史采购候选和人工来源候选过滤停用供应商。
- 新采购序列化与确认路径拒绝停用供应商。
- 供应商列表状态列、停用/启用按钮和删除入口移除。
- 未修改 ISS-039 成本分配、ISS-037 历史主体快照或 ISS-048 财务概览。

## 自动化结果

| 验收项 | 结果 |
|---|---|
| `python manage.py test crm.tests.test_supplier_lifecycle -v 2` | 4/4 通过；覆盖有/无采购历史 DELETE、停用/恢复、候选过滤、新采购拦截、历史采购/付款/来源、权限和审计 |
| 供应商来源、采购生命周期、批量绑定、ISS-039/037/040 相关回归 | 33/33 通过 |
| `python -m compileall -q backend/crm` | 通过 |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `npm run test:unit` | 150/150 通过 |
| `npm run build` | 通过；保留既有大 chunk warning，非本次功能错误 |
| Django 全新测试数据库迁移 | 0001 至 0081 顺序通过 |
| 供应商 Playwright 套件 | 未启动：隔离环境缺少 `@playwright/test`；尝试 `npm install --no-save --ignore-scripts @playwright/test` 时被 Windows 文件锁阻断，未将其计为通过 |

## API/数据验收

- 有历史采购和无历史采购的供应商直接 `DELETE` 均返回 405，记录仍存在。
- 仅有查看权限的角色可读取但不能停用/启用或删除；更新权限角色的直接 `PATCH is_active` 返回 400，必须使用生命周期动作。
- 停用后从规则、Supplier SKU、历史采购和人工来源候选中排除；重新启用后恢复候选资格。
- 停用供应商不能创建或确认新采购。
- 现有采购单、付款流水、联系人和供应来源仍可读取，采购单继续使用既有供应商快照。
- 停用与启用分别生成“停用供应商”“启用供应商”审计，记录前后 `is_active` 值。

## 真实 Chrome 验收

使用独立 worktree 后端 `127.0.0.1:8112`、前端 `127.0.0.1:5193`，开发超级管理员身份仅用于隔离验收数据：

- 桌面默认视口：列表同时显示启用和停用状态；启用供应商显示“停用供应商”，停用供应商显示“启用供应商”；页面无删除按钮。
- 桌面操作：点击“停用供应商”出现确认提示，确认后状态变为“停用”、按钮变为“启用供应商”，并显示“供应商已停用”；再次启用后状态和按钮恢复，并显示“供应商已启用”。
- 窄屏 `390×844`：汉堡菜单可收起导航，页面标题、统计卡片、新建入口、搜索/筛选区和列表内容保持可见；已恢复默认桌面视口。
- 桌面与窄屏截图已通过本次任务的真实 Chrome 截图输出展示；未把图片渲染结果冒充原生打印或其他验收证据。

## 遗留事项

- 仓库内未找到用户所述独立“2026-10-24 规则包”文件；本轮以用户消息中的 ISS-026 规则为准。
- Playwright 供应商套件仍待依赖可用后补跑；真实 Chrome 操作已完成。
- PostgreSQL/CI 未在本机执行；不影响本轮 SQLite、API、Node、构建和真实 Chrome 范围的结论。
- 等待 ChatGPT 独立审查；不关闭 Issue、不合并 master。
