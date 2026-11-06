# HISTORY-PREFLIGHT-WEB-01 验收记录

## 范围

- 起点：`b7ce265833320cc62a7b9aa57e08880f6013203f`
- 分支：`codex/history-preflight-web-01`
- 工作树：`.worktrees/history-preflight-web-01`
- 新页面：ERP「历史资料预检」，复用 `POST /api/import/history-preflight/` 和 `POST /api/import/history-preflight/?report=csv`。
- 「历史资料预检」只做文件检查、结果浏览和报告下载；正式提交仍在单独的「历史资料承接」页面。没有新增或改变写入 API、迁移、RBAC 或正式业务数据。

## 操作步骤

1. 打开 ERP 侧栏中的「历史资料预检」。
2. 选择 `.xlsx` 文件并开始预检；查看文件级摘要和成功、警告、阻断数量。
3. 在行级问题表查看问题、来源行号、记录编号和建议操作；需要核对通过行时启用“显示全部行”。
4. 点击“下载 CSV 清单”保存当前预检报告。
5. 如确认需要正式承接，再单独进入「历史资料承接」并按其流程操作。预检页本身不会提交资料。

## 自动回归与页面检查

- Backend：`crm.tests.test_history_import_preflight`，23 项通过。覆盖正常工作簿只读预检、重复来源/订单阻断、错误及不支持文件、未授权用户 403、CSV 输出安全性和数据范围。测试期间的业务/媒体快照断言通过。
- Frontend：`HistoryPreflightPage.test.js` 与既有 `tests/history-takeover.spec.js`，两文件共 8 项通过。
- Frontend：`npm run build` 通过。
- 真实 Chrome：打开 `/history-preflight`，人工查看标题、说明、汇总和行级问题；分别选择有效、重复来源和损坏工作簿。有效文件显示 3 行、2 项通过、1 项警告；重复文件显示 4 项阻断并定位重复来源及订单编号；损坏文件显示无效 XLSX 错误。页面上的“历史资料承接”入口可导航到独立承接页，承接页提供“只预检文件”返回链接。
- CSV：Chrome 页面按钮触发真实 `?report=csv` 请求并观察到 HTTP 200。自动化桥接未暴露浏览器保存下载事件；因此将同一 HTTP 端点的真实附件响应保存为 `synthetic-history-preflight.csv`，核对其 `Content-Type`、`Content-Disposition`、UTF-8 BOM、列头及 3 行数据。原始响应头见 `synthetic-history-preflight.headers.txt`。这证明 CSV 响应实际生成并可保存，不把浏览器桥接事件描述成已确认。
- 权限：既有后端匿名/未授权回归请求收到 403；沿用 `HistoryPreflightPermission`，未引入前端角色名绕过。
- 不运行全量测试或 GitHub Actions：遵守“只跑定向测试”和 `[skip ci]` 项目约定，CI 为 `NOT_RUN`。

## 合成文件

| 文件 | 内容/用途 |
| --- | --- |
| `synthetic-history-valid.xlsx` | 3 行正常预检数据，得到 2 条通过、1 条未结状态警告 |
| `synthetic-history-duplicate.xlsx` | 4 行包含重复 `source_record_id`、重复 `order_no` 和关联阻断 |
| `synthetic-history-malformed.xlsx` | 损坏的 XLSX 容器，用于错误文件路径 |
| `synthetic-history-unsupported.csv` | 不支持扩展名路径 |
| `synthetic-history-preflight.csv` | 从 CSV 报告 API 保存并检查的真实响应 |

所有工作簿只含合成数据。

## 不变性核对

`snapshot_preflight_state.py` 在合成主数据准备完成后、预检上传前及所有页面/API操作结束后读取完整记录。`state-before.json` 与 `state-after.json` 字节级一致（3,349 字节）。两个快照各包含 19 张模型表；目标数据表的业务计数为：

- InventoryMovement：0；应收计划：0；应付计划：0。
- 销售订单：0；采购订单：0。
- 私有媒体文件：0。

基线包含合成夹具的 1 个 Customer、1 个 Product 和 1 个 SKU；这些合成主数据在预检操作前已准备完成，比较前后均保留。其余模型记录、导入审计表及媒体目录也纳入完整 JSON 比较。

## 文件索引

- `prepare_synthetic_preflight.py`：生成上述工作簿及用于预检的合成主数据。
- `snapshot_preflight_state.py`：输出模型记录、库存、应收/应付、订单、审计表和私有媒体哈希快照。
- `state-before.json`、`state-after.json`：预检前后完整快照。
- `synthetic-history-preflight.csv`、`synthetic-history-preflight.headers.txt`：实际 CSV API 响应及 HTTP 头。

独立复审待完成；本记录不改变 ISS 状态，也不代表正式历史资料可直接承接。
