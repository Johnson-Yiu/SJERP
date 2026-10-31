# R1-ISS-002 CPython 3.12 验收复核

日期：2026-10-31

来源分支：`codex/r1-iss002-python-security-bd324-20261031`

来源 HEAD：`fe4245f20ec19ca22db0adeaacf5e8e6d7920061`

复核分支：`codex/r1-iss002-python312-verify-20261031`

## 结论

在真实 **CPython 3.12.16 x64** 下完成依赖、漏洞、Django、迁移及 104 项图片/Excel 相关回归，均通过。依赖使用独立临时 venv；数据库和媒体写入目标位于系统临时目录，不触碰工作树或共享业务数据库。本报告不代表生产镜像、PostgreSQL 或部署制品验收。

## Python 3.12 与锁文件

- 解释器：`CPython 3.12.16`，Windows x64，MSC v.1944；由独立临时目录中的 uv-managed standalone CPython 提供。验证使用明确的解释器绝对路径，不经过系统 Python 3.14，也没有更改全局 PATH。
- 锁文件环境由来源成果提供；其头注释注明最初在 Python 3.14 生成。本轮实际安装发现 `psycopg` 在 Python <3.13 时会解析条件依赖 `typing-extensions>=4.6`，原锁文件未固定该依赖，虽当次解析到 4.16.0。为满足 3.12 的可复现锁定，本分支仅在 `backend/requirements.lock` 加入 `typing-extensions==4.16.0`；`requirements.txt` 的直接依赖未改，现有直接版本与锁定版本一致。
- 在全新 CPython 3.12 venv 执行 `pip install --requirement backend/requirements.lock`：成功安装锁文件中的全部 16 个发行包，包括 `typing-extensions==4.16.0`。
- 干净 venv 的 `pip check`：`No broken requirements found.`；导入核对为 Django 6.0.9、Pillow 13.0.0、typing-extensions 4.16.0。
- 锁文件及已安装 Python 3.12 项目环境均执行 `pip-audit`：`No known vulnerabilities found`。锁文件无 wheel hashes，pip-audit 对此给出完整性提示；漏洞审计不等于制品哈希/来源验证。

## Django 和图片/Excel 回归

所有命令均由上述 CPython 3.12 环境执行。`DATABASE_URL` 和 `MEDIA_ROOT` 指向本轮临时隔离目录；迁移先在该 SQLite 文件完成，Django 测试框架随后使用独立内存测试库。

| 检查 | 结果 |
|---|---|
| `python manage.py check` | PASS，无系统检查问题 |
| `python manage.py makemigrations --check --dry-run` | PASS，`No changes detected` |
| 全量迁移 `python manage.py migrate --noinput` | PASS，迁移至最新状态 |
| `python manage.py test crm.tests.test_sku_images crm.tests.test_quotes crm.tests.test_iss020_quote_export crm.tests.test_packing_list_export --verbosity 2` | PASS，104/104，0 失败、0 跳过 |

104 项覆盖 SKU 图片缩略图、替换及无效图保护；报价图片快照、报价/PI/XLSX 导出一致性；Packing List 图片嵌入、模板关系、包装数据及权限等。

## 风险与范围边界

- 锁文件目前是精确版本锁定但未含制品 hashes；生产供应链完整性仍应在可信 CI/构建流程中验证。
- 本轮为 Windows CPython 3.12 wheel 验证，不替代 Linux 生产构建或 PostgreSQL 回归。
- 不修改 Pillow 版本、图片业务逻辑、数据库结构、共享 Issue 台账；未触发 CI、未合并 master、未部署。

## 2026-10-31 原始日志补充复验

本次复验使用真实 **CPython 3.12.16 x64**，解释器及共享临时 venv 路径见 logs/01-python-runtime.log。工作区 Python 3.14 未参与本次命令。Django 的数据库和媒体目标均经 logs/06-isolated-target-verification.log 验证，位于本次临时目录 C:\Users\Johnson\AppData\Local\Temp\sunjack-py312-evidence-20261031-iss002\django；迁移写入仅发生在该 SQLite 文件中，测试使用 Django 的独立内存测试库。

锁文件安装命令在这个既有、独立的 CPython 3.12.16 venv 中重新执行，16 个精确锁定包均已满足；pip check 通过。另试建全新 venv：离线缓存缺少 asgiref==3.13.0，在线 PyPI 获取未完成，相关尝试日志一并保留。故本次记录是既有锁定环境核验，不把未完成的全新下载说成成功安装。

本轮 check、迁移检查、全量迁移均通过；图片及 Excel 定向回归 **104/104 通过，0 跳过**。本轮 pip-audit **BLOCKED**：受控尝试 20 秒未完成且没有产生审计输出；连通性诊断显示 api.osv.dev:443 与 pypi.org:443 均不可达。此前 README 所记的 pip-audit 通过结果属于历史运行，不代表本次重新复验通过；网络恢复后仍需重跑。

### 日志索引

- [Python 版本与解释器路径](logs/01-python-runtime.log)
- [requirements.lock 安装/版本满足情况](logs/02-requirements-lock-install.log)
- [全新 venv 离线缓存失败](logs/03-fresh-venv-offline-cache-failure.log)
- [全新 venv 在线下载未完成记录](logs/03-fresh-venv-pypi-fetch-interrupted.log)
- [pip check](logs/03-pip-check.log)
- [pip-audit 工具运行时](logs/04-pip-audit-tool-runtime.log)及[工具版本](logs/04-pip-audit-tool-version.log)
- [pip-audit 锁文件 stdout](logs/04-pip-audit-lock.stdout.log)、[stderr](logs/04-pip-audit-lock.stderr.log)与[受控尝试状态](logs/04-pip-audit-lock-status.log)
- [pip-audit 网络诊断](logs/04-pip-audit-network-diagnostic.log)
- [隔离数据库与媒体路径核验](logs/06-isolated-target-verification.log)
- [Django check](logs/07-django-check.log)、[makemigrations 检查](logs/08-makemigrations-check.log)、[全量迁移](logs/09-full-migrate.log)
- [104 项图片及 Excel 定向测试](logs/10-image-excel-104-tests.log)
