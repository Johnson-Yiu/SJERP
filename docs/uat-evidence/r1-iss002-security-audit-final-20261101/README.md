# R1-ISS002-SECURITY-AUDIT-FINAL

## 结论

**部分完成；整体复验仍未完成（Python 项标记 BLOCKED）。** 本报告只审计固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c`，没有修改业务代码、依赖清单或锁文件，也没有运行修复命令或 GitHub CI。

- npm 漏洞数据库在本轮可访问。全量依赖审计发现 5 个中危、0 个高危/严重；仅生产依赖审计发现 0 项。
- Python 的 `pip-audit` 不在环境中，`python -m pip_audit` 也因模块不存在而无法启动。没有为安装工具进行第二次网络访问。因此本轮**没有**对 Python 包/Pillow 查询漏洞数据库，不能声称 Pillow 13.0.0 当前无漏洞，也不能给出 Python 高危漏洞数量。此为工具缺失导致的 BLOCKED，不是已观察到 Python 漏洞数据库拒绝连接。

## 范围与复现命令

- 分支：`codex/r1-iss002-security-audit-final-20261101`
- Python：本机仅发现 CPython 3.14.5；`pip-audit` 命令和模块均不可用。
- 前端：Node `v24.16.0`，npm `11.13.0`。
- 漏洞库检查只进行本轮这一轮；无重试、无 `npm audit fix`、无联网安装审计工具。

```powershell
cd frontend
npm audit --json
npm audit --omit=dev --json
```

全量 `npm audit` 的退出码为 1 是因为发现漏洞；生产依赖命令退出码为 0。完整 stdout、stderr 和退出码记录见 [`logs/`](logs/)。

## 依赖审计结果

### JavaScript

| 审计范围 | 结果 | 证据 |
| --- | --- | --- |
| 全部依赖（生产 + 开发） | 5 中危；0 高危；0 严重 | [`npm-audit-all.json`](logs/npm-audit-all.json)、[`npm-audit-all.stderr.log`](logs/npm-audit-all.stderr.log)、[`npm-audit-all.exit-code.txt`](logs/npm-audit-all.exit-code.txt) |
| 生产依赖（`--omit=dev`） | 0 项 | [`npm-audit-production.json`](logs/npm-audit-production.json)、[`npm-audit-production.stderr.log`](logs/npm-audit-production.stderr.log)、[`npm-audit-production.exit-code.txt`](logs/npm-audit-production.exit-code.txt) |

全量结果中受影响包均在 lock 中标记为 `dev: true`，不属于生产依赖树：

| 包及锁定版本 | 审计关联 | 影响与实际边界 |
| --- | --- | --- |
| `glob` 10.5.0 | GHSA-3g3m-2fjr-6pw4：AbortSignal 取消绕过，可在超时后继续文件系统遍历 | 对依赖它的开发工具输入恶意 glob/遍历任务时可能造成额外文件系统工作；本次锁中为开发依赖。 |
| `minimatch` 9.0.9 | GHSA-g3hv-75wg-m249：globparts 放大导致潜在拒绝服务 | 恶意模式字符串可能放大匹配计算；本次仅处于开发工具依赖链。 |
| `editorconfig` 1.0.7 | 通过 `minimatch` 关联 | 属于受影响依赖链；npm 显示存在可用修复，但本任务不更新依赖。 |
| `js-beautify` 1.15.4 | 汇总 `editorconfig`、`glob` 依赖问题 | 它使 `@vue/test-utils` 的开发依赖子树受到审计标记；未发现其属于生产依赖。 |
| `@vue/test-utils` 2.4.11 | 直接开发依赖，审计通过 `js-beautify` 指向上述问题 | 仅影响测试/开发工具链；不是浏览器生产包依赖。 |

上述 5 个包是 npm 报告中的受影响包计数，直接漏洞描述是两项中危问题（`glob` 和 `minimatch`）。当前数据未报告高危/严重 npm 项。审计记录中的 advisory URL 及 npm 原始细节均保存在 JSON 日志中。

### Python 与 Pillow

固定基线在 `backend/requirements.txt` 和 `backend/requirements.lock` 均固定 `Pillow==13.0.0`。Pillow 并非闲置依赖：

- SKU 图片上传由 `backend/crm/views.py` 的 `SKUViewSet.image` 处理；模型字段为 `backend/crm/models.py` 的 SKU `ImageField`，DRF 图片字段负责上传校验。
- 实际解码/缩略图路径见 `backend/crm/services/sku_images.py`：`Image.open`、首帧读取、`thumbnail`、`ImageOps.exif_transpose` 和 WEBP 编码。
- 报价图片快照字段位于 `backend/crm/models.py` 的 `QuoteItem.image_snapshot`；Packing List 导出在 `backend/crm/services/packing_list.py` 读取 SKU 图片并嵌入 Excel。

因此，Pillow 处理用户可上传的图像内容，解析器安全问题具有真实应用路径；但本轮没有运行 `pip-audit`，**无法核实 13.0.0 是否对应当前漏洞库中的任何公告、受影响范围或严重度**。仓库历史报告 [`iss-002-python-security/README.md`](../iss-002-python-security/README.md) 记录了早先 Pillow 11.3.0 升级到 13.0.0 的背景和当时的审计结果；该结果是历史证据，不替代本次查询。Python 高危项及 Pillow 当前公告适用性均待后续在具备 `pip-audit` 的环境完成单次联网复验。

## 锁文件完整性

- **Python：** `requirements.txt` 的 9 个直接 pin 均与 `requirements.lock` 版本匹配；lock 共 15 个精确 pin（包括传递依赖及 `psycopg-binary`）。离线比较见 [`python-lock-integrity.log`](logs/python-lock-integrity.log)。两份文件都没有制品哈希；lock 注释注明它由 Python 3.14 环境生成，目标为 CPython 3.12+。因此版本解析被固定，但尚未达到按平台 wheel 哈希校验的完整可复现锁定。
- **npm：** `package.json` 的生产及开发依赖声明与 lockfile v3 根声明一致；锁文件共 253 个条目（含根节点），252 个 registry 条目全部带 `integrity`。离线结构核对见 [`frontend-lock-integrity.log`](logs/frontend-lock-integrity.log)。这核实了清单一致性和完整性字段存在，不等于本轮重新安装或验证每个制品哈希。

## 日志索引

- [`audit-environment.txt`](logs/audit-environment.txt)：审计基线、分支和工具版本。
- [`python-runtime-and-pip-audit-availability.log`](logs/python-runtime-and-pip-audit-availability.log)：Python launcher 实际发现的解释器。
- [`pip-audit-unavailable.log`](logs/pip-audit-unavailable.log)：模块启动失败原始信息与退出码。
- [`pip-audit-cache-check.log`](logs/pip-audit-cache-check.log)：本地 pip 缓存中未找到 pip-audit 包的检查结果。
- [`npm-audit-all.json`](logs/npm-audit-all.json)、[`npm-audit-all.stderr.log`](logs/npm-audit-all.stderr.log)、[`npm-audit-all.exit-code.txt`](logs/npm-audit-all.exit-code.txt)：全量依赖原始审计结果。
- [`npm-audit-production.json`](logs/npm-audit-production.json)、[`npm-audit-production.stderr.log`](logs/npm-audit-production.stderr.log)、[`npm-audit-production.exit-code.txt`](logs/npm-audit-production.exit-code.txt)：生产依赖原始审计结果。
- [`python-lock-integrity.log`](logs/python-lock-integrity.log)、[`frontend-lock-integrity.log`](logs/frontend-lock-integrity.log)：离线清单/锁文件结构比较。

## 建议的最小后续动作

在已安装 `pip-audit`、使用真实项目锁文件的受控环境中，对 `backend/requirements.lock` 执行一次 `pip-audit -r backend/requirements.lock --no-deps --disable-pip`，保存原始输出并专门核对 Pillow 13.0.0。当前报告不建议或实施任何依赖升级；npm 中的开发依赖问题也应先由维护者审阅后再另行决定是否更新。

## 限制

未修改业务代码、依赖文件、锁文件或共享台账；未运行 `npm audit fix`；未连接业务数据库；未触发 GitHub Actions、未创建 PR、未合并 master、未部署。
