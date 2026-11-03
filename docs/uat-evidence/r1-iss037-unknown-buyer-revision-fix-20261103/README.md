# R1-ISS037-UNKNOWN-BUYER-REVISION-FIX-01

日期：2026-11-03。代码基线：`8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`；补修精确提交由协调线程交付时核对远端HEAD。
分支：`codex/r1-iss037-unknown-buyer-revision-fix-20261103`。
工作树：`D:\Codex项目\森爵照明管理系统\.worktrees\r1-iss037-unknown-buyer-revision-fix-20261103`。

状态：定向修复完成，经协调线程复核后以 `[skip ci]` 提交推送独立分支，再纳入集成验证；不能把基线 SHA 称为包含本修复的最终 SHA。独立分支不触发CI，集成分支按本轮要求触发三项CI。

## 已读依据与边界

完整读取 AGENTS.md、REVIEW_PROTOCOL.md、原审查报告，以及 PROJECT_ISSUES/PROJECT_PHASES 的 ISS-020/029/037 相关历史；读取现有 `r1-iss-037-p1/INTEGRATION-README.md` 和 `r1-iss-037-p1-fix-01/README.md`。
原审查：[独立审查 c88a121298465fcb04e11f9b65ef9ad251eadf3f](https://github.com/Johnson-Yiu/SUNJACK-ERP/blob/c88a121298465fcb04e11f9b65ef9ad251eadf3f/docs/uat-evidence/r1-iss037-snapshot-audit-20261103/README.md)，仅补修其 D1，不混入 D2 卖方/模板冻结。

共享台账仍有旧 BLOCKED 描述，但后续六项客户/五项供应商快照及展示修复已经实现；没有重复开发已有快照。按本任务明确分工，共享台账及阶段记录由协调线程维护，本工作树不修改它们。

## 原因与最小改动

`backend/crm/models.py` 的 `Quote.save()` 原来对所有空买方执行当前 Customer 名称兜底，普通修订和订单确认修订虽然复制了旧空值，仍被该兜底改写。

现在在实例初始化时区分买方字段“未提供”和“明确提供（含空字符串）”，并将模型默认预填严格限定为：首次保存、非父/根关联修订、未提供买方、字段为空且有客户。ORM 位置参数加载同样视为提供字段；已存实例不会回读主档填空。没有新增字段或迁移。

核对所有生产创建路径：

| 路径 | 当前结果/改动 |
|---|---|
| `QuoteSerializer.create()` → `Quote.objects.create()` | 新报价省略买方时继续从客户明确预填。现有四个收件人字段的 `setdefault` 与显式空值契约不变。 |
| `QuoteViewSet.revise()` | 已复制 `buyer_company_name`；模型不再覆盖空值，不需要复制一套修订补丁。 |
| `OrderSerializer._create_quote_revision_if_needed()`，由 `confirm_order()` 调用 | 已复制 `buyer_company_name`；同样继承原空值；草稿编辑仍延迟至确认才建立修订。 |
| 已存 Quote 普通/部分/延迟字段保存 | 未知仍未知，非空原值保留。 |
| 模型显式 `buyer_company_name=""` | 保存空值，不补当前主档；缺省模型创建仍预填。 |

`buyer_company_name` 在公共 Quote API 中仍为只读：客户端提交买方字段继续按既有契约被忽略，不能藉此更换主体；“显式空值”在内部模型创建/快照继承层保留，不是开放 API 修改买方名称。API 收件人四项显式空值仍保留。

未改 views、serializers、导出 DTO、卖方模板、0012/0080 或其他迁移；未放开已保存报价的 PUT/PATCH；没有回填任何历史业务记录。

## 风险与验收矩阵

新增 `backend/crm/tests/test_quote_unknown_buyer.py`，10 项测试；多组空/非空输入以 subTest 核对。

| 场景 | 本轮证据 |
|---|---|
| 新报价缺省预填、外部买方仍只读 | API POST 201，保存客户名称而非客户端名称。 |
| 模型省略、显式空、显式非空 | 分别保存主档默认、空值、指定快照。 |
| 历史未知买方、客户已改名、全量/部分/延迟字段保存 | DB 和 GET 仍为空，四个收件人字段仍为空。 |
| 普通修订和二代修订 | HTTP 201；空/非空原值分别继承，原版本完整 `values()` 前后相等。 |
| 直接构造修订且省略买方字段 | 不允许当作新根报价回读主档。 |
| 订单触发修订 | order-draft GET 200、创建订单 201、confirm 200；空/非空旧买方继承，父根链接正确，原版本完整字段不变。 |
| 非空历史快照 PI/XLSX | PI 200、XLSX 200；实际 openpyxl 读取内容含历史买方、不含当前改名；空邮箱保持。 |
| 空买方原版与修订版 PI/XLSX | 均为 422，`fields` 包含 buyer_company_name，不返回 XLSX 文件，不回落主档。 |
| 普通修订生成行失败及重试 | 注入服务异常，报价、修订计数器及原版回滚；重试 201、修订号 1、买方仍为空。 |
| 订单确认生成修订行失败及重试 | 原订单完整字段、报价及计数器回滚；重试确认 200，关联修订仍为空。 |
| 已存快照直接修改 | PATCH 400，空快照不变。 |

以上为 Django APIClient 穿过实际视图、序列化器、生命周期和数据库的测试，不是 mock HTTP 成功响应。mock 仅用于两个明确的故障注入点以验证事务回滚；不将其冒充浏览器真实 HTTP 证据。

## 锁定运行环境与命令

显式解释器（复用，不安装或修改）：

```text
C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe
```

实际 CPython **3.12.16**、Django **6.0.9**、DRF **3.18.3**、Pillow **13.0.0**；本工作树 `backend/requirements.lock` 的 **16 个 pin 逐项相符**。`pip check`：No broken requirements found。不是上轮 Python 3.14.5/Django 6.0.6 环境。

每次运行均显式设置 `APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:`、`PYTHONUTF8=1`，并用 `New-Item` 创建新 GUID TEMP MEDIA_ROOT。实际测试库输出 `file:memorydb_default?mode=memory&cache=shared`；没有连接默认磁盘库、业务库或其他工作树服务。

真实命令形式（工作树根目录设置环境后进入 backend；`$py` 为上述绝对路径）：

```powershell
$env:APP_STAGE='development'
$env:DATABASE_URL='sqlite:///:memory:'
$env:PYTHONUTF8='1'
$env:MEDIA_ROOT=Join-Path ([System.IO.Path]::GetTempPath()) ('iss037-final-media-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $env:MEDIA_ROOT
Set-Location backend
& $py manage.py test crm.tests.test_quote_unknown_buyer --verbosity 2 --noinput
& $py manage.py test crm.tests.test_quote_unknown_buyer crm.tests.test_formal_party_snapshots crm.tests.test_contract_lifecycle crm.tests.test_quotes crm.tests.test_quote_revision_tree crm.tests.test_iss020_quote_export --verbosity 2 --noinput
& $py manage.py check
& $py manage.py makemigrations --check --dry-run
& $py -m pip check
```

原始 stdout/stderr 由 PowerShell Tee-Object 保存，没有裁掉异常堆栈或预期 400/422。初次只运行当时的 8 项新增测试；补充订单回滚和直接模型修订两项后跑完整 98 项。最后再增强非空 PI/XLSX 断言并重跑相同 98 项，最终结果以下方日志为准。

| 检查 | 结果 | `raw-logs.zip` 内文件 |
|---|---|---|
| Python/依赖/隔离环境 | 3.12.16 / 6.0.9 / 内存 SQLite / 独立 TEMP 媒体 | environment.log |
| 16 个锁定依赖逐项比较 | 全部 matches=True | lock-consistency.log |
| pip check | exit 0 | pip-check.log |
| 新增测试首轮 | 8 通过，0 skip，exit 0，0.941s | targeted.log |
| 相关回归首轮（10 新增 + 88 既有） | 98 通过，0 skip，exit 0，36.168s | regression.log |
| 最终增强断言回归（同一 98 项） | 98 通过，0 skip，exit 0，39.240s | final-regression.log |
| Django check | exit 0，无问题 | django-check.log |
| makemigrations --check --dry-run | exit 0，No changes detected | migrations-check.log |

故障注入导致日志出现 Synthetic item failure / Synthetic order revision failure 及 Internal Server Error，属于断言要求的回滚场景，不是隐藏失败；以最终 unittest 汇总为准。已有 PI、XLSX 图片/金额/币种、收件人空值、修订树及正式主体快照测试原断言未删除、未放宽。

原始日志归档：[raw-logs.zip](raw-logs.zip)，SHA-256 `CC90116C644F9E0022942365312D048279582652A3F5CB950E1F99C789876EA0`。归档仅包含本轮生成的 `.log`；未包含凭据或业务库。`git diff --check` exit 0；新增测试和 README 的 `git diff --no-index --check -- NUL <file>` 无空白错误（exit 1 表示与空文件不同，只有 LF→CRLF 提示）。

## 改动与剩余事项

仅变更 `backend/crm/models.py`，新增 `backend/crm/tests/test_quote_unknown_buyer.py` 和本专属报告/日志 ZIP。共享台账、阶段、配置、工作流、迁移和前端无改动；无 UI 改动，因此本任务没有 Chrome 视觉或文案改动验收，不虚构截图。

尚未执行：PostgreSQL、全量后端、CI、真实 Chrome、Excel 桌面打印、正式员工身份/审批、业务库历史抽样。由协调线程集成后补全跨任务回归与最终精确 SHA CI；本任务不自行提交/推送。

ISS-037 仍不整体关闭。卖方/模板冻结、完整双方资料、历史来源可信度、主体新版本流程和审批分离均不在此补丁内；旧 0012 来源风险未被更改或掩盖。ISS-020 的关键字段正式导出拒绝、ISS-029 的收件人空值、ISS-021 的订单生命周期和失败原子性继续保留。
