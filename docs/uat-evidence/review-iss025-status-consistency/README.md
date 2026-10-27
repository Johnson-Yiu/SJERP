# ISS-025-FIX-01 客户状态标签全页面一致性核查

日期：2026-10-27  
统一核查基线：`1fac93f09e3b5c578a030df5c0736e5d0552e4cc`  
源分支：`codex/iss-025-customer-status-labels`  
核查分支：`codex/review-iss025-status-consistency`  
最小修补提交：`20981f9`  

## 结论

本轮不是重复开发。源分支已正确统一客户列表、详情、筛选、关联企业、客户 API 和跟进筛选的生命周期展示，但经营分析按客户状态分组仍直接使用 Django 模型文案：`contact` 会显示“联系人”，`company` 会显示“公司客户”。这是真实的全页面一致性缺口。

已在报表记录构造处仅对 `source=customers` 的 `status` 使用既有 `customer_status_display()` 映射，并补充回归测试。销售、采购和财务报表的业务状态展示未改动。

保留以下业务事实不变：数据库状态编码、模型状态选项、自动状态推进、联系人数量规则、历史客户/跟进/报价数据、筛选参数和权限范围。API 仍同时返回原始 `status`，展示名称通过 `status_display` 或报表 `label` 提供。

## 页面与接口核查

- 客户列表：`/customers?status=contact` 的筛选值和行徽章均为“已联系”。
- 客户详情：状态徽章为“已联系”；“联系人”仍只出现在 Contact 实体区域。
- 联系人详情：关联企业表格的客户状态为“已联系”。
- 跟进记录：`/follow-ups?customer=2` 的客户筛选保留 URL，刷新后仍显示对应客户及状态标签。
- 报表与经营分析：客户按生命周期分组显示“线索、已联系、商机、正式客户、返单客户”。
- API：客户列表保留 `status=contact`，`status_display=已联系`；报表原始 key 保留，label 使用统一映射。
- 刷新、分页和 URL 恢复：沿用原有状态恢复机制，未引入新的状态存储或重写。

隔离样本包含五个生命周期状态（`lead/contact/opportunity/customer/company`）及联系人；浏览器服务使用独立 SQLite，不连接生产数据库。

## 自动化验收

- `python manage.py test crm --keepdb`：953 passed，15 skipped，OK（413.161s）。
- ISS-025 定向后端测试：包含客户 API、关联企业和报表映射断言，全部通过。
- `python manage.py makemigrations --check --dry-run`：`No changes detected`。
- `npm run test:unit`：156 passed，0 failed。
- `npx vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：659 passed，0 failed。
- `npm run build`：通过；仅保留既有 chunk size warning。
- `git diff --check`：通过。

## Chrome Use 真实视觉核查

使用真实 Chrome Use 完成桌面和 `390×844` 窄屏检查，未使用 computer use。核查结果：

- 桌面客户列表显示筛选“已联系”和客户行状态徽章“已联系”。
- 桌面详情、联系人关联企业、跟进筛选和报表结果均显示统一状态名称。
- 390px 窄屏下筛选区、客户卡片及状态标签可见可操作；表格保持原有横向滚动方式，没有遮挡状态值。
- 报表结果实际显示五个 canonical label，且每个样本数量为 1。

独立 API 复核结果：

```json
{
  "customer_status": "contact",
  "customer_status_display": "已联系",
  "report_labels": "company=返单客户, contact=已联系, customer=正式客户, lead=线索, opportunity=商机"
}
```

既有客户状态视觉截图仍保存在 [`ISS-025 原验收证据`](../iss-025-customer-status-labels/README.md)；本轮新增核查重点为经营分析缺口、报表结果和窄屏/刷新复核，未把旧截图冒充为新的浏览器结果。

## 台账与延期事项

- `docs/PROJECT_ISSUES.md` 中 ISS-025 原记录已更新，没有创建重复 Issue。
- 其他状态名称“商机”“正式客户”“返单客户”的简化符合当前实现，但用户尚未逐一确认措辞，登记为 `BUSINESS_VERIFICATION_PENDING`；本轮不扩大文案重构范围。
- 真实生产数据库、真实员工账号和全量业务数据抽查仍为 `BUSINESS_VERIFICATION_PENDING` / `DEPLOYMENT_VERIFICATION_PENDING`。
- 本轮未新增迁移、未修改 master、未关闭 Issue、未部署生产。

## ISS-025-FIX-02 本轮真实 Chrome 视觉证据补齐（2026-10-27）

本轮只补充真实浏览器视觉证据，没有修改报表逻辑、状态编码、销售/采购/财务报表文案或权限代码。使用同一已审查提交 `d5d0d15c03d55a718f11a298e08f29a9b9d0c4b0` 的独立 Worktree、全新 SQLite 数据库和本地 Vite/Django 服务；未连接生产数据库，未触发 GitHub CI。

### 本轮隔离测试数据

创建 5 条唯一客户记录，日期口径为 `created_at`，查询范围为 `2026-10-01` 至 `2026-10-31`，每种状态 1 条：

| 客户编号 | 数据库状态编码 | 报表显示 |
|---|---|---|
| `ISS025F02-01` | `lead` | 线索 |
| `ISS025F02-02` | `contact` | 已联系 |
| `ISS025F02-03` | `opportunity` | 商机 |
| `ISS025F02-04` | `customer` | 正式客户 |
| `ISS025F02-05` | `company` | 返单客户 |

独立 API `GET /api/reports/data/?source=customers&group_by=status&date_field=created_at&date_from=2026-10-01&date_to=2026-10-31&metric=count&view=bar&comparison=previous&grain=month` 返回 5 行、总数 5，每行 `count=1`；`key` 保持上述英文编码，`label` 与页面中文一致。报表区域文本实际检查到五个规范标签，未检查到旧生命周期文案“联系人”或“公司客户”。

### 本轮新截图

以下两张是本轮 Chrome 会话直接保存的新文件；旧截图仍保留在原目录/原验收证据中，未复制或改名冒充本轮证据：

- [桌面视口：客户状态报表](screenshots/iss025-fix02-customer-status-report-desktop.png)：默认 Chrome 视口，PNG 捕获面 `1905×912`，结果表和条形图均显示五种规范状态。
- [窄屏视口：390×844 客户状态报表](screenshots/iss025-fix02-customer-status-report-mobile-390x844.png)：CSS viewport `390×844`；PNG 捕获面 `375×812`（浏览器滚动条/外层区域不计入截图），菜单收起、查询结果和五个状态标签可见，按钮/筛选区按窄屏换行。

窄屏 DOM 实测：`innerWidth=390`、可用内容宽度 `375`；页面 `scrollWidth=375`，没有页面级横向溢出；报表表格 `clientWidth=313`、`scrollWidth=313`，本次两列结果不需要横向滚动，状态值没有被遮挡。报表内不出现“联系人”“公司客户”；左侧导航中的“联系人”仍是联系人实体入口，不属于客户生命周期标签。

### 本轮执行记录

- `python manage.py migrate --noinput`（隔离 SQLite）：全新数据库迁移完成，包含当前仓库全部迁移。
- 本地 Django API：`127.0.0.1:8176`，返回状态报表 HTTP 200；数据和页面结果一致。
- 本地 Vite：`127.0.0.1:5376`，真实 Chrome 桌面及 `390×844` 窄屏回归完成。
- `python manage.py test crm.tests.test_issue_025_status_labels crm.tests.test_reporting --keepdb`（隔离 SQLite）：36 passed，0 failed，OK。
- `npm run test:unit`：156 passed，0 failed。
- `npm run build`：通过；保留既有 chunk size warning，无构建错误。
- `git diff --check`：通过；本轮无应用代码修改。
- 未触发 GitHub CI，未运行生产数据库或真实员工账号验收；上述部署/真实业务数据风险继续保留原台账状态。

本轮证据提交为 `f9e2c7493ba86007fb6969d826d336dc4077edb7`；后续若仅为远端交付记录产生提交，以最终交付 SHA 为准。提交只包含截图、证据 README 和台账记录；不合并 `master`、不关闭 Issue、不部署生产，等待独立视觉复审。
