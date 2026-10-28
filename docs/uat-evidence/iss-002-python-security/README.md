# R1-ISS-002-SEC-01 Python 依赖与 Pillow 安全升级验收

## 基本信息

- 固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`
- 分支：`codex/repair-iss002-python-security`
- 任务：`R1-ISS-002-SEC-01`
- 验收日期：2026-10-28
- worktree：独立 worktree；未从本地脏 master 复制文件

本轮没有修改业务规则、模型、API、权限、财务数据或共享问题台账，也没有运行 `npm audit fix`、连接正式数据库或触发 CI。

## 结论

已确认 Pillow 11.3.0 位于实际运行路径，不能继续按“仅测试依赖”处理。最小安全升级到 Pillow 13.0.0 后，图片上传、缩略图、报价图片快照、Packing List 图片及 Excel 导出回归通过；Django、DRF、openpyxl、psycopg 依赖无解析冲突。

依赖现在分为：

- `backend/requirements.txt`：直接运行依赖精确 pin。
- `backend/requirements.lock`：完整运行时传递依赖精确 pin，可在干净环境用 `pip install -r backend/requirements.lock` 重复安装。

本轮将 ISS-002 的 Pillow 版本风险和 Python 版本漂移风险处理为 `FIXED_PENDING_REVIEW` 候选，但不修改共享台账；仍需独立复审后再改变台账状态。

## 实际路径核对

| 路径 | 当前调用 | 结果 |
| --- | --- | --- |
| SKU 图片上传 | `crm/views.py` 的 `/api/skus/<id>/image/`，允许 GIF/JPEG/PNG/WebP | 通过 |
| SKU 缩略图 | `crm/services/sku_images.py`：`Image.open`、`thumbnail`、`ImageOps.exif_transpose`、RGBA/WEBP 输出 | 通过 |
| 报价图片 | `test_iss020_quote_export.py`：上传 PNG 后生成正式报价图片快照并导出 | 通过 |
| Packing List 图片 | `crm/services/packing_list.py`：openpyxl drawing image，保留模板/关系并写入 XLSX | 通过 |
| Excel 图片读取 | Packing List、报价和相关测试用 `PIL.Image.open` 复核实际嵌入图片 | 通过 |

基线开发环境实际检查：Python 3.14.5、Pillow 11.3.0、Django 6.0.8、DRF 3.18.0。项目源码中没有 Pillow 12/13 已删除 API 的使用；实际路径使用的 `Image.open`、`thumbnail`、`ImageOps.exif_transpose` 与 openpyxl 图片包装在升级环境正常工作。

## 安全公告与版本判断

官方 Pillow 12.3.0 发布说明仍列出多项图像解析、解压炸弹、OOB 和资源耗尽修复；官方 13.0.0 发布说明进一步列出关键 JPEG 解码、OpenJPEG、TIFF、Exif、GIF、PDF 等安全修复。当前 11.3.0 不满足这些修复版本要求，因此没有选择只升级到 12.3.0。[Pillow 12.3.0 安全发布说明](https://github.com/python-pillow/Pillow/blob/main/docs/releasenotes/12.3.0.rst) · [Pillow 13.0.0 安全发布说明](https://github.com/python-pillow/Pillow/blob/main/docs/releasenotes/13.0.0.rst) · [Pillow 官方安全公告](https://github.com/python-pillow/Pillow/security/advisories)

重点判断：

- 11.3.0 仍处于既有安全审计记录的受影响区间。
- 12.3.0 不是本轮的安全终点；官方公告显示若干关键问题的修复版本为 13.0.0。
- PyPI 为 Pillow 13.0.0 提供 CPython 3.12 的 Windows、manylinux、musllinux 和 macOS wheels，并声明 Python `>=3.11`；因此依赖元数据满足 Python 3.12 目标。[PyPI Pillow 13.0.0 文件与元数据](https://pypi.org/project/pillow/)
- 额外执行 `pip download --python-version 3.12 --implementation cp --abi cp312 --platform win_amd64 Pillow==13.0.0`，成功取得 `pillow-13.0.0-cp312-cp312-win_amd64.whl`；这证明目标 wheel 可解析，但不替代真实 Python 3.12 运行时测试。
- 本机没有 Python 3.12 解释器，实际运行回归使用 Python 3.14.5；不能把本机回归表述为真实 Python 3.12 运行时验收。

## 测试证据

### Pillow 13.0.0 临时升级环境

独立临时环境安装：Pillow 13.0.0、Django 6.0.9、DRF 3.18.3、django-cors-headers 4.9.0、dj-database-url 3.1.2、openpyxl 3.1.5、psycopg 3.3.6、bleach 6.4.0、pycountry 26.2.16。

- `pip check`：`No broken requirements found`
- `manage.py check`：无问题
- `manage.py makemigrations --check --dry-run`：`No changes detected`
- 全新 SQLite 迁移：通过，迁移至 `crm.0089`
- `crm.tests.test_sku_images crm.tests.test_packing_list_export crm.tests.test_iss020_quote_export`：38 passed
- Django 全量：1000 passed，18 skipped
- `pip-audit -r backend/requirements.lock --no-deps --disable-pip`：`No known vulnerabilities found`；`--disable-pip` 排除审计工具自身 pip 版本，不把工具漏洞混入项目运行时结论。

全量测试第一次在中文 worktree 默认 `MEDIA_ROOT` 创建目录时遇到 Windows `PermissionError`；切换到独立 ASCII 临时媒体目录后，以同一代码和同一依赖重跑通过。该环境问题不作为产品失败隐藏。

### Python 依赖锁复验

在第二个全新临时 Python 3.14 环境执行 `pip install -r backend/requirements.lock`，安装成功；随后 `pip check`、system check、全新 SQLite 迁移、`makemigrations --check` 和 38 项图片/Excel/Packing List 定向测试均通过。

## 已修复与未解决事项

### 已修复/已验证

- Pillow 从 11.3.0 固定到 13.0.0，覆盖本轮核对的 Pillow 11.x 风险窗口。
- 直接运行依赖由范围约束改为精确 pin，新增完整运行时 `requirements.lock`。
- 图片上传、缩略图、报价快照、Packing List 图片及 Excel 文件结构相关回归通过。
- Django、DRF、openpyxl、psycopg 解析版本一致，`pip check` 无冲突。

### 仍需独立/环境验收

- 本机缺少 Python 3.12，真实 CPython 3.12 启动和全量测试为 `DEPLOYMENT_VERIFICATION_PENDING`；已用官方 3.12 wheel 元数据和 Python 3.14 兼容回归作支持证据。
- 直接对完整环境运行的 `pip-audit` 曾因 PyPI SSL/连接中断报告审计环境自身 pip 的公告；最终改用精确 `requirements.lock`、`--no-deps --disable-pip` 复核并得到 `No known vulnerabilities found`。生产镜像仍应在可联网 CI 中重做带 hash/制品签名的最终快照。
- lock 当前是精确版本锁，不含每个平台 wheel 的 hash；正式生产仍应在受控镜像构建中增加 hash/制品签名校验，并核对 Linux/Windows 目标平台。
- 未验证真实生产镜像、PostgreSQL、外部上传暴露、反向代理、操作系统库和资源限制；这些不由本地测试替代。

## 未做事项

- 未修改 `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md`。
- 未运行 `npm audit fix`。
- 未触发 GitHub Actions、未合并 master、未部署、未关闭 ISS-002。
