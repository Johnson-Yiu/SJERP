# ISS-049 / ISS-053 / ISS-067 统一集成验收

日期：2026-10-23

统一基线：`c356e57014d28295485d52df23612c2fe6c02444`

集成分支：`codex/integration-049-053-067`
最终分支 SHA：以交付时 `git rev-parse HEAD` 为准；本报告所在提交之后无业务代码改动。

## 分支与合并

| 任务 | 源分支最终 SHA | 集成合并提交 | 结果 |
|---|---|---|---|
| ISS-049 | `9d08009f62920c62399ec48defe7f4d1c2e21411` | `73faf80` | 已合并 |
| ISS-053 | `caf0aadf5f7305d5c0d69020a07d2aeab71e4f34` | `c50767e` | 已合并；已先推送并用 `git ls-remote` 确认远端分支可见 |
| ISS-067 | `dd538183523c9b3670763da9d43551a9454fb0b3` | `40a9483` | 已合并 |

三次合并均无 Git 文件冲突。文档台账存在历史状态滞后：ISS-049 原记录仍为延期/未复测，ISS-053 阶段阻塞描述仍把状态文案列为待修复；本轮只更新这些记录的当前证据和措辞，没有覆盖三项任务的实现、测试或截图证据。

## 验收结论

- ISS-049：确认客户国家筛选、跟进记录客户/方式/日期/排序复合筛选、财务流水状态/方向/日期筛选可由 URL 恢复；真实 Chrome 页面正确回显筛选条件。未发现需要追加的真实缺陷，保留 `FIXED_PENDING_REVIEW`，不关闭问题。
- ISS-053：未复现历史英文显示缺陷。数据库/API 仍使用 `ordered`；API 返回 `status_display: 已下单`，列表、详情、编辑界面、状态筛选、销售订单采购关联卡片均显示中文。其他实际状态 `draft`、`partial`、`completed`、`cancelled` 分别显示“草稿”“部分到货”“已完成”“已取消”。本轮没有修改采购业务代码，保留 `NEEDS_VERIFICATION` 等待独立审查。
- ISS-067：报表页面在开发超级管理员身份下正常加载；权限边界由后端完整测试及浏览器回归确认：无权来源查询返回 403 且不含业务 `rows`，前端不发起无权来源请求并显示中文提示。保留 `NEEDS_VERIFICATION`，等待独立审查。

## API 响应证据

在隔离集成服务 `http://127.0.0.1:8323` 上读取：

```text
GET /api/purchase-orders/?status=ordered -> 200
results[0].status_display = "已下单"
results[0].status = "ordered"

GET /api/purchase-orders/2/ -> 200
status_display = "已下单"
status = "ordered"

GET /api/reports/catalog/ -> 200
sources.sales / sources.purchase / sources.profit / sources.cash 可见

GET /api/reports/data/?source=sales&group_by=time&date_from=2026-10-01&date_to=2026-10-31 -> 200
返回 source、period、totals、rows；未越权请求不暴露无权来源数据。
```

完整采购状态截图、API/浏览器日志和原任务证据仍在：

- [ISS-049 测试日志](../iss-049-quick-filters/TEST_LOG.md)及六张客户/跟进/流水截图
- [ISS-053 核实报告](../iss-053-purchase-status/README.md)及五张采购页面截图
- [ISS-067 核实报告](../iss-067-report-permission/acceptance-report.md)、测试日志及三张权限截图

## 自动化验证

| 检查 | 结果 |
|---|---|
| `backend/manage.py check` | PASS；无 system check 错误 |
| `backend/manage.py makemigrations --check --dry-run` | PASS；No changes detected |
| 迁移 | PASS；隔离 SQLite 已应用至 `crm.0079_shared_report_template` |
| `backend/manage.py test crm --verbosity 1` | PASS；816 tests，skipped=13，`OK` |
| `PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/crm-ux.spec.js browser-tests/iss067-report-permission.spec.js --workers=1` | PASS；11 passed |
| `npm run test:unit` | PASS；145 tests passed |
| 有效 Vitest 批次（排除 Node 测试混入和既有 phase2a 路由断言） | PASS；63 files / 619 tests passed |
| `npm run build` | PASS；2009 modules；仅有既存大 chunk warning |
| 真实 Chrome | PASS；ISS-049 客户/跟进/流水筛选、ISS-053 采购入口矩阵、ISS-067 报表中心均已观察 |

后端完整测试还覆盖迁移等价性、财务金额/汇率计算、采购成本与订单毛利、权限 403 边界及报表详情权限。P2A 验证日志中的 `bank_net: 705.00`、`all_legacy_rows_equal: true` 保持通过。

## 保存、筛选与业务规则

- 未改动采购生命周期和状态转换规则；数据库保存值仍是英文枚举。
- ISS-049 只验证筛选状态、URL 传参、回显和重置，不改变业务数据或列表统计口径。
- ISS-067 只验证来源权限和报表查询边界，不放宽权限，也不修改共享模板权限路径。
- 未发现迁移漂移；未新增迁移；财务业务规则由后端完整测试覆盖。

## 剩余风险与合并判断

- 当前真实服务使用开发超级管理员身份；ISS-067 的受限角色边界证据来自后端权限测试和既有 Chrome/Playwright 权限回归，正式员工账号/生产配置仍需独立复审。
- 默认 `npx vitest run` 会混入 Node `node:test` 文件，且一个既有 phase2a 路由清单断言仍落后于当前导航；本轮使用项目可识别的有效 Vitest 批次并记录该测试债务，没有借机修改无关模块。
- 构建保留既有大 chunk warning；本地没有替代 CI PostgreSQL/部署环境验收。
- 三个问题均保留待独立审查状态；本轮未合并 `master`、未关闭 Issue。

因此：集成分支代码、测试和证据已经具备提交统一独立审查的条件；在独立审查完成、正式权限/部署环境风险接受前，不宣称具备直接合并 `master` 的最终条件。
