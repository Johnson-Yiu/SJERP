# R1-ISS105-INDEPENDENT-BANK-FEE-FIX-01

日期：2026-11-03。分支：`codex/r1-iss105-independent-bank-fee-fix-20261103`。

实现/测试基线：`8d3ca5faa16fb74de95dbc716f5556a5d51bbe79` 加本补丁。协调线程复核后以 `[skip ci]` 提交推送独立分支，最终集成按同一精确 SHA 触发三项 CI。原审查报告远端 SHA：`1cad93d0cb0297c33f764f6cb68d5c610512d9e4`，对应 [CASH-04](https://github.com/Johnson-Yiu/SUNJACK-ERP/blob/1cad93d0cb0297c33f764f6cb68d5c610512d9e4/docs/uat-evidence/r1-iss105-actual-cash-audit-20261103/README.md)。已读 AGENTS、REVIEW_PROTOCOL、共享台账/阶段相关条目和原报告；不改共享文件。

## 范围与结论

**定向缺陷已修复，等待独立复审，不代表 ISS-105 整体关闭。**

- `frontend/src/views/CashEventPage.vue`：删除无父结汇的额外客户端拒绝及 HTML required；标签为“关联结汇事件（可选）”，空项为“不关联结汇”。帮助文字明确独立扣费仍需独立人民币手续费来源。
- `frontend/src/utils/cashEventPayload.js`：空选项及无效数字不序列化成 0/NaN；有效正整数保留身份，异常恢复值显示客户端错误而不发送请求。
- 后端资金服务、模型、权限、统计、数据库迁移和历史数据均未修改。父事件存在性、已确认结汇、同人民币账户、无含扣费校验继续由现有后端执行。独立 CNY bank_fee 来源、额度、精度、凭证、人工确认与稳定请求幂等均保留。
- 新增后端 `crm/tests/test_independent_bank_fee.py`、Node 序列化及页面契约回归、真实 API Chrome 用例 `frontend/browser-tests/independent-bank-fee-real.spec.js`。
- 交付前补齐测试入口：隔离运行器增加纯函数 `isolatedCashAccountEnvironment(selection)`，只对本专项或 `businessSuite` 注入固定合成账户；其他专项、基础设施冒烟和未配置值均保持原状。新增3项选择分支回归，不修改生产 settings / workflow。

## 锁定环境与隔离

实际解释器（只复用，未修改）：

```text
C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe
```

CPython **3.12.16**；`verify_environment.py` 将本树 `backend/requirements.lock` 的16个 pin 逐一与实际安装比对，全部一致，包括 Django **6.0.9**、DRF **3.18.3**、Pillow **13.0.0**；`pip check` 通过。不是原审查的 Django 6.0.6 环境。Node **24.16.0**、npm **11.13.0**，本树 `npm ci --no-audit --no-fund` 完成，package-lock 未修改。

Django 单测使用 `DATABASE_URL=sqlite:///:memory:`、独立临时 MEDIA_ROOT。Chrome 用既有隔离启动器，每次临时 SQLite / MEDIA_ROOT，明确独立 API/Vite 端口；先通过迁移、直接 Django、Vite 及真正 `/api` 代理身份校验，再运行写入型测试。`seed_browser.py` 在 beforeAll 内验证运行标记、实际 settings、数据库路径和迁移后才写合成 fixture；随机编号，不假设全套测试库为空，不触碰已有记录。结束核对本次源流水完整字段未变，由启动器仅清理本次已标记资源及其服务。

真实 API 进程需要合成白名单 `SYNTH_FX,SYNTH_CNY`，现由隔离启动器在选择本专项或全 business suite 时自动注入，**不再要求外层环境或 workflow 传入**。其他 suite 原有账户配置（包括未设置）保持不变。这只是隔离合成 fixture，不是真实银行账户/启用日/余额，不放宽业务服务保护；测试仍不 skip。外层删除 `RMB_CASH_ACCOUNT_IDS` 后已重新执行本专项真实 Chrome，证明标准入口自足。

## 实际结果

| 检查 | 结果及证据 |
|---|---|
| 锁定环境比对、pip check | 16/16一致；无依赖冲突，见日志 ZIP environment.txt / pip-check.txt |
| Django 三组专项 | 31项：28通过，3跳过，0失败；现金事件、实际报表及新增独立费用3项测试，backend-final.txt |
| 3项跳过原因 | 全为 `Real PostgreSQL locks required`；未以 SQLite 代替 PostgreSQL 锁验证，待主集成 PG/CI |
| Node 定向 | 11项通过，含空值/非法数字序列化、页面和报表口径，node-final.txt |
| Node 全量 | 入口补齐前174项通过、0跳过；含基础设施并行隔离测试；原执行及显式锁定解释器重跑分别保留日志。入口补齐后新增3项定向通过，未冒称重新执行177项全量 |
| CI入口选择回归 | 3项通过：本专项、全business suite固定合成账户；其他专项/基础设施冒烟保留既有或未设置账户，见补充ZIP runner-account-selection.txt |
| Vitest 相关 | 3文件17项通过：trade-finance、finance-reference-basis、finance-contract-navigation，vitest-final.txt |
| 真实 Chrome | 3项通过：1440px、390px无父费用真实UI，以及真实API父关联/拒绝/重放；原日志 browser-release.txt。入口补齐后清除外层账户变量重跑3项通过，最终证据对应补充ZIP browser-self-contained.txt |
| 生产构建 | 通过；主JS 1132.53 kB，gzip 395.65 kB；仍有原有 >500 kB chunk 警告，未作性能验收声明 |
| Django check / 迁移检查 | system check无问题；makemigrations --check --dry-run无变更；隔离库全量迁移成功 |
| diff检查 | 交付前 git diff --check；无共享台账、业务后端/迁移、锁文件变更 |

首轮新增后端测试曾因把既有 API 零流入字符串预期写成 `0.00` 而失败；实际契约为 `0`，对齐正确精确响应后重跑通过。未改产品序列化，初次失败日志 backend-raw.txt 保留，不隐瞒。

## 真实业务与 HTTP / 数据核对

原始请求/响应：[independent-bank-fee/http.json](independent-bank-fee/http.json)。运行前合成数据及实际隔离路径：[isolation-database.json](independent-bank-fee/isolation-database.json)；结束逐字段源流水和银行事件/分配记录：[database-after.json](independent-bank-fee/database-after.json)。所有可见业务资料均为合成，默认 AUDIT_LOG_ENABLED=0，不冒充正式登录操作员审计。

| 场景 | 观察 |
|---|---|
| 无结汇父事件，桌面及390px | 空选择请求 `fee_for:null`；预览200、登记201、勾选人工核实后确认200，刷新后仍已确认 |
| 草稿刷新恢复 | 稳定请求键、空关联和输入恢复；凭证字段不存 localStorage，重新填写后才允许继续 |
| 未核实来源 | 客户端拒绝，修正后可继续；未绕过逐条核实 |
| 真实失败后重试 | 银行净额6但来源5，真实预览400；保留输入，改回5后200/201/200成功 |
| 重复确认/统计 | 每个独立费用再次确认200；报表 count仅增1，outflow仅增5，inflow不变；不是重复记账 |
| 合法关联 | 已确认、无含扣费、同账户父结汇，费用预览200、登记201、确认200 |
| 待确认父 / 非结汇父 / 父含扣费 / 账户不符 | 400；不存在父ID 404；不新建资金事实 |
| 非独立 CNY bank_fee 来源 | 400；拒绝前后事件数不变 |
| 稳定键登记重试 / 来源再分配 | 同请求200且同ID；换键超额409；再次确认仍同事实 |
| 凭证/精度/来源门禁 | 后端专项验证缺摘要确认400、无来源/错误币种/高精度/未人工核实400，pending保留；既有含扣费用拒绝测试继续通过 |
| 历史保护 | 后端 legacy_hash 前后相同；Chrome结束比较本次5条源流水完整字段与创建后基准完全相同。只新增合法银行事件/分配，不写订单、库存或第二笔客户收款 |

## 真实截图与文案检查

均为系统 Chrome 实际操作截图，没有 mock API、拼图或重制作；Chrome版本和关联控件边界记录在 [layout.json](independent-bank-fee/layout.json)。本次只改可选关联及手续费帮助文案，桌面和窄屏可读；未缩字体/隐藏操作。

| 文件 | 场景及结果 |
|---|---|
| [optional-fee-1440.png](independent-bank-fee/screenshots/optional-fee-1440.png) | 桌面空关联、可选标签和真实预览后的表单 |
| [optional-fee-390.png](independent-bank-fee/screenshots/optional-fee-390.png) | 390px可选关联及帮助自然换行，控件未超视口 |
| [confirmed-fee-1440.png](independent-bank-fee/screenshots/confirmed-fee-1440.png) | 桌面独立银行扣费5元，已确认，来源分配可见 |
| [confirmed-fee-390.png](independent-bank-fee/screenshots/confirmed-fee-390.png) | 390px已确认资金事件；可滚动查看详情 |

**既有文案遗留（本轮不扩大）：** 确认后详情顶部仍写“资金事件待确认”，而状态 badge 已为“已确认”。协调线程已目视指出；本次不修标题，仅保留待独立文案修复。

## 可复核命令

在本树 frontend（PowerShell；Linux CI 使用其绝对 Python3.12 路径替换）：

```powershell
$env:ISOLATED_TEST_PYTHON='C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe'
Remove-Item Env:RMB_CASH_ACCOUNT_IDS -ErrorAction SilentlyContinue
$env:PYTHONUTF8='1'
$env:ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT=(Resolve-Path '../docs/uat-evidence/r1-iss105-independent-bank-fee-fix-20261103').Path
npm ci --no-audit --no-fund
node scripts/run-isolated-browser-tests.mjs --business-test independent-bank-fee-real.spec.js
npm run test:unit
npx --no-install vitest run tests/trade-finance.spec.js tests/finance-reference-basis.spec.js tests/finance-contract-navigation.spec.js --environment jsdom
npm run build
```

在本树 backend：

```powershell
$feePython='C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe'
$env:APP_STAGE='development'
$env:DATABASE_URL='sqlite:///:memory:'
$env:MEDIA_ROOT=Join-Path $env:TEMP ('iss105-fee-tests-'+[guid]::NewGuid())
$env:PYTHONUTF8='1'
& $feePython manage.py test crm.tests.test_independent_bank_fee crm.tests.test_cash_events crm.tests.test_actual_cash_reporting --verbosity 2
& $feePython manage.py check
& $feePython manage.py makemigrations --check --dry-run
```

原始日志统一见 [raw-logs.zip](raw-logs.zip)。仅将临时隔离身份 nonce/其探测 URL 脱敏，不改失败、断言、响应或结果；脱敏脚本 [redact_logs.mjs](redact_logs.mjs) 可检查。不保留多余 traces/artifacts 或散落临时日志。日志包摘要见 [SHA256.md](SHA256.md)。

入口补齐后的定向选择单测及外层无账户配置 Chrome 原始输出见 [ci-entry-supplement.zip](ci-entry-supplement.zip)；这次最终执行对应本目录的 HTTP/SQLite/截图。补充单测命令：

```powershell
node --test --test-name-pattern 'bank-fee selection|full business suite receives|other business selections' infrastructure-tests/runner-validation.test.mjs
```

## 仍未覆盖及移交

- PostgreSQL并发、集成全量Backend/Frontend/Chrome及同SHA三项GitHub CI由主集成验收；本树没有触发CI。
- 正式操作人审计/受控凭证内容绑定仍有原缺口，不把开发身份或合成SHA声明为真实凭证验真。
- ISS-105内部转账排除、多字段银行重复识别、待分类、现金/银行分离、启用基准余额及账户核对等原审查遗留不在本次补修范围；不设置真实启用日期/余额，不改变ISS-108/121既有原则。
- 未改主分支、其他worktree、共享台账/阶段、正式RBAC、workflow或真实业务数据库；测试启动器仅按本节受控选择注入合成 fixture 账户。未提交、推送、创建PR、部署或关闭Issue。主代理统一提交、更新台账及集成后独立复审。
