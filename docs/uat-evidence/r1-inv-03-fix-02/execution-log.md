# 实际执行记录

执行日期：2026-10-20（Asia/Shanghai）

## 1. 历史采购来源快照测试

工作目录：`backend/`

实际命令：

```powershell
python manage.py test crm.tests.test_inventory_reference --verbosity 1; $code = $LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code
```

结果：`Ran 5 tests in 5.026s`，`OK`，`EXIT_CODE=0`。

覆盖内容：历史快照保留、当前供应来源档案标签、快照缺失不伪造历史信息，以及供应商查看权限下的来源脱敏。

## 2. INV + MOQ 临时集成后端

工作目录：临时集成 worktree 的 `backend/`。

实际命令：

```powershell
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from django.conf import settings; settings.DATABASES['default']['NAME']=':memory:'; settings.MEDIA_ROOT='C:/Users/Johnson/.codex/worktrees/r1-inv-03-fix-02-integration/backend/.integration-media'; from django.core.management import call_command; call_command('test','crm.tests.test_purchase_moq','crm.tests.test_inventory_reference','--verbosity','1')"; $code = $LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code
```

结果：`Found 12 test(s)`，`Ran 12 tests in 5.815s`，`OK`，`EXIT_CODE=0`。

## 3. INV + MOQ 临时集成前端单元测试

工作目录：临时集成 worktree 的 `frontend/`。

实际命令：

```powershell
npm run test:unit; $code = $LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code
```

结果：`tests 142`，`pass 142`，`fail 0`，`EXIT_CODE=0`。

## 4. INV + MOQ 临时集成前端构建

工作目录：临时集成 worktree 的 `frontend/`。

实际命令：

```powershell
npx vite build --configLoader runner; $code = $LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code
```

结果：Vite 完成 `2006 modules transformed`，构建成功，`EXIT_CODE=0`。仅有既有的大 chunk warning，没有构建错误。

## 5. 迁移图核对

工作目录：临时集成 worktree 的 `backend/`。

实际命令：

```powershell
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from django.conf import settings; settings.DATABASES['default']['NAME']=':memory:'; from django.core.management import call_command; call_command('showmigrations','crm')"; $code = $LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code
```

结果：迁移图成功加载并列出 `0076_customer_owner_profile`、`0077_rmb_cash_events`、`0078_purchase_moq_exceptions`，`EXIT_CODE=0`。该检查使用内存数据库且没有执行迁移，因此列表中的应用标记不代表正式数据库状态。

## 环境说明

- 临时集成前端通过一次性 `node_modules` junction 复用现有依赖，仅用于测试；未写入正式分支。
- 临时 Playwright 配置和测试脚本仅存在于一次性集成 worktree，未提交到库存分支。
- 本轮没有执行 PostgreSQL；本记录不将 SQLite/内存数据库结果冒充 PostgreSQL 结果。
