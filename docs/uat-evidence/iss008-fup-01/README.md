# ISS-008 FUP-01 验收报告：国家/地区中文别名补齐

## 结论

本轮仅补齐既有 ISS-008 国家选择器的中文显示与搜索数据，没有重新开发选择器。固定基线为 `bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`，工作分支为 `codex/fix-iss008-chinese-aliases`，独立 worktree 为 `C:\Users\Johnson\.codex\worktrees\fix-iss008-chinese-aliases\森爵照明管理系统`。

已完成 249/249 个既有 ISO 3166-1 条目的中文覆盖。原英文名、alpha-2、alpha-3 维持不变；中文名和别名只进入本地注册表的显示/搜索路径。数据库状态、历史客户国家资料和报价编号没有迁移或重写。

## 来源与处理原则

- 标准中文名采用 Unicode CLDR 中文 territory 数据快照：[CLDR 原始 territories.json](https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-localenames-full/main/zh/territories.json)；可用 [CLDR 中文摘要表](https://unicode.org/cldr/charts/49/summary/zh.html) 复核。
- [联合国 UNTERM country names](https://conferences.unite.un.org/unterm/download/country) 作为术语交叉核对来源。
- 每个已有 alpha-2 均保留原英文名和 alpha-3。标准中文名加入搜索索引并作为新增的 `nameZh` 字段返回；既有 `label`（英文名 / alpha-2）和既有字段保持兼容。
- 现有中文别名与历史英文别名全部保留，并补充必要的地区/旧称变体。模糊词 `America` 继续要求用户明确选择，不自动保存；历史未知文本继续原样展示，不被最新主档覆盖。

完整覆盖表见 [country-coverage.md](./country-coverage.md)。

## 代码与验证范围

- `backend/crm/country_registry.py`：新增 249 项中文覆盖；扩展兼容别名；不改变 alpha-2 解析、历史文本保留和歧义拒绝规则。
- `backend/crm/tests/test_issue_008_country_select.py`：逐项验证 249 条记录、中文解析、英文/中文/alpha-2/alpha-3 搜索文本及兼容别名。
- `frontend/tests/country-select.spec.js`：验证新增 `nameZh` 契约、中文名和代码筛选；保留原有 America 明确选择行为。
- `frontend/browser-tests/iss008-chinese-aliases.spec.js`：真实 Chrome 的客户国家选择和报价客户选择回归，未修改 Playwright/Vite 全局配置。
- 新截图：见本目录下的 `customer-country-1440.png`、`customer-country-390.png`、`quote-customer-1440.png`、`quote-customer-390.png`。这些截图由本轮隔离浏览器测试实际生成，未复制旧证据。

## 测试记录

| 检查 | 结果 |
|---|---|
| Django ISS-008 定向测试（含 249 条逐项 subTest） | PASS：11 tests |
| Django ISS-008 + quotes 关联回归 | PASS：77 tests |
| Vitest country-select 定向测试 | PASS：4 tests |
| Vitest country/customer/编辑器关联回归 | PASS：18 tests |
| Node 前端单元测试（`npm run test:unit`） | PASS：169 tests |
| Vite 生产构建 | PASS：2018 modules transformed；仅有既有 chunk size warning |
| Playwright 真实 Chrome，1440×844 | PASS：1 test |
| Playwright 真实 Chrome，390×844 | PASS：1 test |
| 截图视觉复核 | PASS：4 张本轮截图；客户和报价选择框可见，窄屏无页面横向溢出 |
| 数据库迁移/历史资料 | 未新增迁移；仅注册表与测试，未写入历史客户或报价数据 |
| GitHub Actions / PostgreSQL | 本轮未触发/未验证，按任务要求保留为外部验收项 |

执行命令：

```text
$env:PYTHONDONTWRITEBYTECODE='1'; python -B manage.py test crm.tests.test_issue_008_country_select --verbosity 1
npm exec -- vitest run tests/country-select.spec.js --environment jsdom
$env:PLAYWRIGHT_CHANNEL='chrome'; npm exec -- playwright test browser-tests/iss008-chinese-aliases.spec.js --config=playwright.config.js --workers=1 --reporter=line
```

真实 Chrome 本轮结果为 `2 passed (26.8s)`；桌面和窄屏各执行一次。测试使用隔离 API fixture 验证 UI 契约，后端完整 249 项覆盖由 Django 定向测试验证。

## 不变更项与剩余风险

- 未修改共享 `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md`，未合并 master，未触发 CI。
- 未修改国家选择器结构、客户历史国家字段、报价编号生成或既有历史值。
- 未把有歧义的名称自动猜测为国家；`America` 仍需明确选择。
- CLDR 名称随上游标准更新的版本化审查仍是后续维护事项；本提交将当前快照固化在本地注册表，避免运行时依赖外部 API。
- 最终提交 SHA 以本分支提交后的 `git rev-parse HEAD` 为准。
