# R1-HIST-01-FIX-01 验收证据

## 范围

本轮在 `codex/r1-hist-01` 上集中修复历史订单的资金隔离、历史分析权限、历史成本自动填入和历史订单页面的部分权限加载问题。未修改 master、ISS-121、既有历史业务数据或迁移文件。

历史订单仍使用现有 `historical_only` 隔离标记；没有新增数据库模型或迁移。历史录入生成的 SO/PO 编号是 ERP 新生成的内部标识，不是原始历史合同编号。

## 代码与环境

- 工作分支：`codex/r1-hist-01`
- 基线：`42bfb6e34656d1ba5786a0dc471219792c4f1092`
- 后端：SQLite 开发数据库，`http://127.0.0.1:8102`
- 前端：Vite 开发服务器，`http://127.0.0.1:5193`
- PostgreSQL：未配置（`DATABASE_URL` 未设置），未声称 PostgreSQL 通过。
- GitHub Actions：按项目当前额度策略保持 `CI PENDING`，本轮未反复触发。

## 实际执行结果

| 命令 | 结果 |
|---|---|
| `cd backend; python manage.py check` | exit 0；无系统检查问题 |
| `cd backend; python manage.py makemigrations --check --dry-run` | exit 0；`No changes detected` |
| `cd backend; python manage.py test crm.tests.test_historical_orders --verbosity 1` | exit 0；9 tests，全部通过 |
| `cd backend; python manage.py test --verbosity 1` | exit 0；777 tests，全部通过，13 skipped |
| `cd frontend; npm run test:unit` | exit 0；140 tests，全部通过 |
| `cd frontend; npm run build` | exit 0；Vite production build 成功；仅有既存 chunk size warning |

全量 SQLite 输出同时确认数据库校验前后摘要一致，历史金额字段保持不变；迁移验证显示既有 legacy rows 相等。

## 定向安全验证

- `other`、`other_income` 以及计划关联的资金流水均不能关联历史销售订单或历史采购订单。
- serializer 和 `record_transaction()` 服务边界均执行拒绝；完全独立、没有历史单据关联的普通资金登记仍可成功。
- 历史分析入口不再要求通用 `reports.view`；有 `orders.view` 或 `purchases.view` 即可进入对应聚合范围。
- 客户、供应商、SKU 和产品分类维度按各自主档权限分开返回。缺少 `skus.view` 时不返回 SKU ID、编码、名称或产品信息；缺少客户/供应商权限时不返回对应身份维度。
- 历史订单创建不再从当前 SKU 成本填入订单行；历史分析利润保持“不计算”。正式订单成本逻辑未改。
- 历史订单页面按权限请求可用接口，单个 403/加载失败只形成提示，不清空其他已授权资料；无主档选择权限时不显示不可用的录入表单。

## 真实 Chrome 验收

在普通开发身份（服务端开发超级管理员）下，通过真实 Chrome 完成了：

1. 打开历史订单分析页，确认“历史订单 · 仅用于经营分析”及“不生成应收、应付、采购或库存记录”提示。
2. 实际录入并保存一笔历史销售订单：真实日期 `2020-02-20`、SKU、数量和单价；页面显示保存成功、历史订单列表和历史销售分析金额。
3. 切换采购页签，实际录入并保存一笔历史采购订单：真实日期 `2020-05-21`、SKU、数量和单价；页面显示保存成功、历史采购列表和历史采购分析金额。
4. 检查桌面宽度下表单、页签、分析卡片、历史列表和滚动行为，没有布局溢出。

截图：

- [桌面初始页面](./chrome-desktop.png)
- [销售保存成功](./chrome-sales-saved-desktop.png)
- [采购保存成功](./chrome-purchase-saved-desktop.png)
- [最终桌面页面](./chrome-desktop-final.png)
- [窄屏检查记录图](./chrome-narrow-zoom.png)

当前 CUA Chrome 接口没有提供可验证的 viewport 设置；`chrome-narrow-zoom.png` 是同一真实 Chrome 会话的辅助检查图，不能作为精确 700px viewport 的证明。700px CSS 分支已由组件测试和构建覆盖，但精确 700px 的 Chrome 视觉复核仍需在可设置 viewport 的浏览器环境补做。

## 未完成与边界

- 未执行 PostgreSQL：本机没有可用连接配置。
- 未声称真实打印或 PDF 打印预览；本任务不要求新增打印流程。
- 历史订单内部编号仍由 ERP 当前编号规则生成；如需保存原始历史合同编号，需要后续业务决定和独立字段设计。
