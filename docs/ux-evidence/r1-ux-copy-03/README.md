# R1-UX-COPY-03 验收证据

## 来源

- 分支：`codex/ux-copy-finance-inventory`
- 当前提交：`fa6b50242c89720513f79214400ddf481c5041af`
- 固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`
- 范围：库存、财务、报表页面的可见文案澄清；金额计算、数据来源、权限、日期范围、状态值及业务 API 未改动。

详细文案映射见 [R1-UX-COPY-03-文案对照表](../../ux-copy/R1-UX-COPY-03-文案对照表.md)。

## 已有视觉证据

本提交包含以下页面截图，作为该成果的视觉基线：

- `finance.png`
- `inventory.png`
- `inventory-detail.png`
- `receivables.png`
- `reports.png`
- `rmb-cash-events.png`
- `transactions.png`

截图目录：`docs/ux-evidence/r1-ux-copy-03/`。

## 本地验证

| 验证项 | 结果 |
| --- | --- |
| Node 单元测试 `npm run test:unit` | 169/169 通过 |
| 前端生产构建 `npm run build` | 通过；仅保留既有大 chunk 提示 |
| 隔离 Chrome `inventory-ux.spec.js` | 9/9 通过 |
| 隔离 Chrome `overview-reports.spec.js` | 15/16 通过 |

`overview-reports.spec.js` 唯一失败是受限保存图表场景仍断言旧文案“没有此图表的数据来源”；当前页面按本提交的文案显示“当前账号没有此报表的数据权限，未加载该报表。”。这是共享浏览器测试断言待同步项，不是通过修改断言绕过的测试结果。

上述浏览器测试使用隔离 SQLite、隔离 Django API 和隔离 Vite，未连接实际业务数据库；因此不替代真实后端部署环境验收。

## 变更边界

- 未修改共享 Issue 台账。
- 未修改数据库迁移。
- 未修改金额口径、权限判定、报表查询或财务数据。
- 未合并 master、未部署、未触发 GitHub Actions。

