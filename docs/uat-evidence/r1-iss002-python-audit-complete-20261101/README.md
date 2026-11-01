# R1-ISS002-PYTHON-AUDIT-COMPLETE

## 结论：BLOCKED（PyPI 审计服务未能完成查询）

本轮使用项目真实锁文件完成了 OSV 数据源审计，但 `pip-audit` 的 PyPI 数据源在首个依赖请求时发生 TLS EOF，未产生审计 JSON。根据任务要求，整体 Python 漏洞审计标记为 **BLOCKED**；不能把 OSV 单一数据源的零命中扩大成全局零漏洞，也不能把 PyPI 未查询的依赖记录为零漏洞。本轮未重试 PyPI、未绕过 TLS。

## 基线与隔离

- 来源分支：`codex/r1-iss002-security-audit-final-20261101`
- 来源/审计基线 SHA：`427d2a2c38516a52d460f50e60e0fb635f23a4c2`
- 交付分支：`codex/r1-iss002-python-audit-complete-20261101`
- Python：CPython 3.14.5；审计器 `pip-audit 2.10.1`
- `pip-audit` 及其工具依赖只安装在系统临时目录的独立 venv；项目依赖未安装或升级。
- 审计对象：`backend/requirements.lock`，15 个精确版本 pin；其中 `backend/requirements.txt` 有 9 个直接 pin，其余为锁定的传递依赖。
- 锁文件 SHA256：`A106C2369FBB65E9592DF022D65F34F80FB432E9B7A5A3E2F9B20ECDC1D15E67`；直接依赖文件 SHA256：`D715164E45ED3FD8816EF6D42612515A7581BF074A920771897F5EDE700D25DC`。审计前后校验值一致。
- 没有修改 `requirements.txt` 或 `requirements.lock`，没有运行 `pip-audit --fix`，没有自动升级依赖。

## 执行结果

审计命令对锁文件使用 `--no-deps`，因为锁文件本身已经逐项列出所有 15 个精确锁定包；`--disable-pip` 排除的是临时审计 venv 中审计器自带的 pip，不会排除锁文件条目。

| 数据源 | 结果 | 可支持的结论 |
| --- | --- | --- |
| OSV | 命令退出码 0；JSON 含 15 个依赖，每项 `vulns: []`，包括 `pillow==13.0.0` | OSV 本次查询对这 15 个版本未返回公告 ID/严重度/受影响范围；仅代表该数据源的结果。 |
| PyPI（pip-audit provider） | 命令退出码 1；JSON 输出为空。对 `asgiref==3.13.0` 的请求因 `SSLEOFError: UNEXPECTED_EOF_WHILE_READING` 失败 | PyPI 数据源没有完成依赖审计；全部 15 项的 PyPI 结果未知，整体验收按要求 `BLOCKED`。 |

执行前的只读连通性探测中，PowerShell 对 PyPI 项目元数据返回 HTTP 200，OSV API 返回了响应；但实际审计器经 Python `requests` 请求 PyPI 漏洞接口时失败。故本报告保留具体审计路径失败，而不将一般端点可达性视为 PyPI 漏洞查询成功。

### Pillow 13.0.0 与实际使用路径

OSV 原始审计结果中 `pillow==13.0.0` 的 `vulns` 数组为空；本轮没有得到可报告的 Pillow 漏洞 ID、严重程度或受影响版本范围。PyPI 数据源未完成，因此不得据此断言 Pillow 13.0.0 全面无漏洞。没有尝试修复或升级。

上游 [Pillow 13.0.0 发布说明](https://github.com/python-pillow/Pillow/blob/main/docs/releasenotes/13.0.0.rst)包含安全修复记录；这说明该版本属于安全敏感范围，但不替代本轮未完成的 PyPI 数据源结果。

Pillow 是有真实输入面的运行依赖：

- SKU 图片上传入口：[`SKUViewSet.image`](../../../backend/crm/views.py#L1285)。
- 列表缩略图会对存储图像调用 `Image.open`、读取首帧、`thumbnail`、EXIF 方向处理和 WEBP 编码：[`sku_images.py`](../../../backend/crm/services/sku_images.py#L24)。
- 正式报价使用图片快照字段：[`QuoteItem.image_snapshot`](../../../backend/crm/models.py#L936)，保存/复制逻辑见 [`quote_snapshots.py`](../../../backend/crm/quote_snapshots.py#L16)；报价导出读取快照路径见 [`quotation_export_dto.py`](../../../backend/crm/quotation_export_dto.py#L96)。
- Packing List 导出把 SKU 图片交给 openpyxl 图片处理：[`packing_list.py`](../../../backend/crm/services/packing_list.py#L361)。

因此，未来若数据源报告图像解析公告，应结合用户上传、缩略图、报价快照和导出路径判断影响，不能当作未使用的开发依赖忽略。

### 锁文件制品完整性

锁文件包含 15 个精确版本 pin，但没有任何 `--hash` 条目。它限制版本解析，不校验下载到的 wheel/源分发制品字节；这留下制品来源/完整性与跨平台 wheel 重现风险。该风险与漏洞数据库命中不同，本轮没有添加哈希或改变锁文件。

## 原始证据

- [`audit-environment.txt`](logs/audit-environment.txt)：分支、基线、Python / pip-audit 版本及锁文件哈希。
- [`source-connectivity-preflight.txt`](logs/source-connectivity-preflight.txt)：PyPI/OSV 初始端点探测摘要，并明确区分实际审计服务结果。
- [`pip-audit-version.txt`](logs/pip-audit-version.txt)
- OSV 原始 JSON、stderr 和退出码：[`pip-audit-osv.json`](logs/pip-audit-osv.json)、[`pip-audit-osv.stderr.log`](logs/pip-audit-osv.stderr.log)、[`pip-audit-osv.exit-code.txt`](logs/pip-audit-osv.exit-code.txt)
- PyPI 原始输出、stderr 和退出码：[`pip-audit-pypi.json`](logs/pip-audit-pypi.json)、[`pip-audit-pypi.stderr.log`](logs/pip-audit-pypi.stderr.log)、[`pip-audit-pypi.exit-code.txt`](logs/pip-audit-pypi.exit-code.txt)
- 隔离审计器安装日志和 pip 安装报告：[`pip-audit-install.log`](logs/pip-audit-install.log)、[`pip-audit-install-report.json`](logs/pip-audit-install-report.json)
- 锁清单、版本计数、文件哈希及缺少 wheel hash 的核对：[`lock-inventory.log`](logs/lock-inventory.log)

复核/解除阻塞条件：在 PyPI 漏洞接口通过正常 TLS 连接可用的隔离环境中，对同一 SHA 和同一锁文件重跑 PyPI 审计；保留原始输出，核对 Pillow 及全部锁定包的 ID、严重程度、受影响/修复版本与实际代码路径。不得关闭证书校验或自动修复。

本轮没有合并 master、没有触发 CI、没有创建 PR，也没有连接数据库。
