# R1-UX-COPY-03 验收证据

## 本次测试修复定位

- 基线分支：`codex/ux-copy-finance-inventory`
- 基线 SHA：`9f957e1744e790b2cc784176ea9999b9c949c98f`
- 原始文案代码提交：`fa6b50242c89720513f79214400ddf481c5041af`
- 测试修复分支：`codex/ux-copy-finance-inventory-test-fix`
- 本次测试修复代码提交（最终代码 SHA）：`724becda275ee14130131f906f02c879b10b7817`
- 本次只修改 `frontend/browser-tests/overview-reports.spec.js` 的一处文案断言，以及本验收报告；未修改页面、业务逻辑、数据库、API、权限或财务计算。

## 文案断言修复

| 位置 | 旧断言 | 新断言 |
| --- | --- | --- |
| `frontend/browser-tests/overview-reports.spec.js` 受限报表场景 | `没有此图表的数据来源` | `当前账号没有此报表的数据权限，未加载该报表。` |

受限报表场景原有安全断言全部保留：

- 受限来源不会被前端请求绕过，仍断言每个报表请求的 `source` 都是允许的 `customers`，不会请求被限制的 `sales` 来源。
- 无权访问的报表不显示可用操作按钮，仍断言 `导出 CSV` 不存在；经营概览中的财务入口也不显示。
- 本次没有删除测试场景或降低断言强度。

## 定向验收结果

| 验证项 | 实际结果 |
| --- | --- |
| `npm run test:browser:isolated -- --business-test overview-reports.spec.js` | **16/16 通过**，独立 SQLite、独立 Django API、独立 Vite，Playwright 1 worker，38.2 秒 |
| `npm run test:unit` | **169/169 通过**，0 failed、0 skipped |
| `npm run build` | **通过**；2018 modules transformed，生产构建完成 |
| `git diff --check` | **通过** |

隔离浏览器测试实际执行了迁移、API/Vite 身份校验和全部 16 个 `overview-reports.spec.js` 场景；运行使用合成 fixture，不连接实际业务数据库。

## 警告与限制

- 构建保留既有 Vite 警告：`index-nTI1cWka.js` 为 1,128.55 kB，超过 500 kB chunk 建议；本次没有修改构建配置。
- 隔离测试只证明隔离 SQLite 与合成接口场景下的浏览器行为，不替代真实后端部署环境验收。
- 本次未新增页面截图：本分支只修复测试断言和更新报告，原始文案代码提交中的页面截图仍作为视觉基线。
- 尝试执行额外的 headed Google Chrome 受限场景时，当前桌面已有 Chrome 会话未建立独立测试窗口，因此该次没有形成可采纳结果，也未计入 16/16；正式浏览器结果以隔离 Chromium 测试为准。

## 变更边界

- 未修改共享 Issue 台账、数据库迁移、业务 API、权限逻辑或财务计算。
- 未合并 master、未部署；提交均包含 `[skip ci]`，不触发 GitHub Actions。

详细文案映射见 [R1-UX-COPY-03-文案对照表](../../ux-copy/R1-UX-COPY-03-文案对照表.md)。原始视觉证据仍位于本目录：`finance.png`、`inventory.png`、`inventory-detail.png`、`receivables.png`、`reports.png`、`rmb-cash-events.png`、`transactions.png`。
