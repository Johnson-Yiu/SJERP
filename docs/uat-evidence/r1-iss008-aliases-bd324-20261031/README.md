# R1-ISS-008-FUP-01 国家中文名称与别名补齐验收

日期：2026-10-31
分支：`codex/r1-iss008-aliases-bd324-20261031`
指定基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
历史成果：`80dc73ae4ae47f9e04969f39b441af206d34306b`
本轮浏览器测试提交：`dba4a81c10a464012aa004a539a16378f7517b0e`

## 结论与差异核查

指定基线已经包含历史成果中的国家目录、中文名称/搜索别名、249 项覆盖测试、选择器单测及原有客户新建/报价选择器浏览器测试。逐文件比较历史成果与指定基线的 `backend/crm/country_registry.py`、`backend/crm/tests/test_issue_008_country_select.py`、`frontend/tests/country-select.spec.js` 和既有浏览器测试后，国家目录及业务实现没有缺失或冲突；因此没有重复移植或修改生产业务代码。

本轮唯一代码变更是扩展 `frontend/browser-tests/iss008-chinese-aliases.spec.js`：增加客户编辑既有国家的真实 Chrome 流程，保存后刷新并重新打开，确认 API 保存与重新加载仍显示 `Hong Kong / HK`。没有改动客户历史国家数据、报价编号逻辑、数据库模型/迁移或 alpha-2/alpha-3 对照表。

## 覆盖及规则

- 后端注册表含 249 条记录，标准中文名与英文名称、alpha-2、alpha-3 搜索值逐条对照；测试对 249 个条目逐项执行中文名解析和字段断言。完整名单与中文来源记录见[历史覆盖清单](../iss008-fup-01/country-coverage.md)。
- CLDR 简体中文 territory 名称作为显示名；别名仍由版本化本地表维护，不依赖页面打开时访问外部服务。
- `America` 仍只出现在候选搜索字段中；直接解析为国家代码会抛出歧义错误。用户必须明确选择 `United States / US`，不会自动保存猜测值。
- 未知输入不会作为新选择保存；历史导入中无法解析的国家文本仍原样保留，等待人工确认。
- 既有报价编号和修订号不随客户国家后续变化；同日同国家报价流水唯一性测试保留并通过。

## 本轮测试

| 范围 | 结果 | 数据/环境 |
|---|---:|---|
| `crm.tests.test_issue_008_country_select` | 11/11 通过，0 跳过 | 项目锁定 Python 环境；隔离内存 SQLite；包含 249 项逐条子测试、别名/歧义、未知旧值、报价历史编号与流水唯一性 |
| `vitest run tests/country-select.spec.js --environment jsdom` | 4/4 通过 | 锁文件安装的前端依赖 |
| `playwright test browser-tests/iss008-chinese-aliases.spec.js --workers=1` | 2/2 通过 | 本机真实 Chrome；1440×844、390×844；每种视口覆盖客户编辑/保存/刷新重开、客户新建国家选择、报价客户选择器 |
| `git diff --check` | 通过 | 提交前执行 |

复现命令（PowerShell；分别在 `backend`、`frontend` 目录运行）：

```powershell
$env:APP_STAGE='development'
$env:DATABASE_URL='sqlite:///:memory:'
$env:MEDIA_ROOT=Join-Path $env:TEMP 'sunjack-r1-iss008-aliases-20261031-media'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B manage.py test crm.tests.test_issue_008_country_select --verbosity 2

npm ci
npm exec -- vitest run tests/country-select.spec.js --environment jsdom
$env:CI='1'
$env:PLAYWRIGHT_CHANNEL='chrome'
$env:ISS008_FUP_01_EVIDENCE_DIR='C:\Users\Johnson\.codex\worktrees\r1-iss008-aliases-bd324-20261031\森爵照明管理系统\docs\uat-evidence\r1-iss008-aliases-bd324-20261031\screenshots'
npm exec -- playwright test browser-tests/iss008-chinese-aliases.spec.js --workers=1 --reporter=line
```

Chrome 中客户编辑从 `Germany / DE` 搜索并明确选择中文“中国香港”，保存 PUT 为 `HK`，刷新并重新打开仍显示 `Hong Kong / HK`；国家新建候选及报价客户选择器均可操作。自动化页面使用隔离合成 API fixture，不连接业务数据库；后端 API/注册表验证由单独隔离 SQLite 测试覆盖。未运行全量前端套件、生产构建、PostgreSQL 或 GitHub CI（本轮无生产源代码变更）。

## 真实 Chrome 截图

视口均为 844px 高；以下均为本轮新运行生成的截图，并已逐张视觉检查：

| 交互 | 桌面 1440×844 | 窄屏 390×844 |
|---|---|---|
| 编辑客户：中文搜索并选择 Hong Kong / HK | [customer-edit-country-1440.png](screenshots/customer-edit-country-1440.png) | [customer-edit-country-390.png](screenshots/customer-edit-country-390.png) |
| 新建客户：搜索并选择德国 | [customer-country-1440.png](screenshots/customer-country-1440.png) | [customer-country-390.png](screenshots/customer-country-390.png) |
| 新建报价：选择客户 | [quote-customer-1440.png](screenshots/quote-customer-1440.png) | [quote-customer-390.png](screenshots/quote-customer-390.png) |

窄屏客户编辑表单纵向可滚动，国家候选和底部保存操作可见，无横向溢出；报价表单在 390px 下保持可用。截图展示合成客户与合成商品，不含真实客户数据。

## 日志与最终状态

- 后端：[`backend-iss008.log`](backend-iss008.log)
- 前端 Vitest：[`frontend-vitest.log`](frontend-vitest.log)
- Chrome：[`playwright-chrome.log`](playwright-chrome.log)
- 当前实现提交：`dba4a81c10a464012aa004a539a16378f7517b0e`（只新增浏览器验收步骤）
- 最终报告/台账提交 SHA：以本分支最终 HEAD 为准，并在交付消息中报告。
- 不触发 CI、不连接生产数据库、不修改历史客户国家/报价编号，不关闭 Issue；等待独立审查。
