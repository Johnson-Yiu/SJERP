# HISTORY-PREFLIGHT-WEB-FIX-01 验收记录

## 范围

- 基线：`4c29837f42697596c8c67e8c2d34379a5939eebd`
- 分支：`codex/history-preflight-web-fix-01`
- 工作树：`.worktrees/history-preflight-web-fix-01`
- 修复：预检结果及 CSV 必须绑定到同一份当前选定的 XLSX；旧请求返回不得覆盖当前文件的汇总或行级结果。

## 实现行为

- 每次文件选择递增版本号，清空旧预检、错误和下载状态，并立即解除旧预检的 loading 状态，让新选的 B 能开始预检。
- 每次预检捕获所选 `File` 和版本；响应、错误和 `finally` 只在请求仍属于当前文件时更新页面。
- 成功结果单独保存对应的 `previewFile`。汇总显示该文件名；下载时以这份文件构造请求体。
- 下载响应返回前再次检查文件和版本。用户已改选文件时，旧 CSV 响应不会触发下载，也不会覆盖新下载状态。

## 三个定向场景

前端自动回归使用可控的延迟 Promise：

1. **A 预检中改选 B**：A 请求未完成时重新选择 B；旧汇总清空，开始预检按钮立即可用，B 请求带的是 B 文件。
2. **A 旧响应晚到**：B 的预检先完成后再返回 A；页面汇总、文件名、行级记录继续对应 B，A 响应不覆盖。
3. **改选后下载**：A 先得到结果，再选择 B；旧汇总和下载入口被清除。B 预检完成后，CSV multipart 中的文件对象就是 B，不是 A。

## 自动验证

- 命令：`node node_modules/vitest/vitest.mjs run src/views/HistoryPreflightPage.test.js tests/history-takeover.spec.js --environment jsdom`
- 结果：2 个测试文件通过，共 **10/10**。
- 命令：`npm run build`
- 结果：生产构建成功。Vite 保留项目现有主 bundle 大于 500 kB 的提示；本包没有改动分包配置。
- 未运行前后端全量测试、未运行 GitHub Actions，符合本轮“只跑定向测试”约束；CI 状态为 `NOT_RUN`。

## 内置浏览器实际文件验收

本轮用隔离 SQLite 服务（API `127.0.0.1:8118`、Vite `127.0.0.1:5200`）打开内置浏览器页面 `/history-preflight`。真实选择 `workbook-B-duplicate.xlsx` 并运行预检，页面显示文件名为 B、数据行 4、阻断 4，行级表显示 `FIXB-SO-1`。点击页面“下载 CSV 清单”，内置浏览器报告实际下载路径为 `C:\Users\Johnson\Downloads\history-preflight.csv`。该文件复制到本目录并按 UTF-8 BOM/CSV 解析器读取。

`verify_download.py` 将已下载 CSV 中 `销售订单` 行的 `原系统记录编号` 与 B 工作簿的同一列比较：两边多重集均为 `FIXB-SO-1` 两条；下载文件没有 `FIXA-` 编号。实际 CSV 共 4 条数据行、1,912 字节。该核对使用浏览器保存的文件，不是从 API 另行重取的副本。

## 数据不变性与证据文件

浏览器上传和 CSV 下载全部针对隔离 SQLite、合成 XLSX。`state-before.json` 在合成客户/商品/SKU准备后、浏览器预检前生成；`state-after.json` 在预检及下载后生成。两份快照 SHA-256 均为 `B0D22C2A8AC9EEBF857F2FEFF76093F603A1883AD0D176509045E918A2F848EC`，包含 19 张业务/审计模型表、库存流水、应收应付、订单及私有媒体目录。

- `prepare_race_workbooks.py`：生成具有不同 A/B 来源编号的两个合成工作簿并准备合成主数据。
- `workbook-A-valid.xlsx`：A 的来源编号为 `FIXA-SO-1`。
- `workbook-B-duplicate.xlsx`：B 含两条重复来源编号 `FIXB-SO-1`。
- `history-preflight.csv`：从内置浏览器点击页面按钮下载的实际文件。
- `verify_download.py`、`download-verification.json`：下载 CSV 和 B 工作簿逐项对比结果。
- `state-before.json`、`state-after.json`：业务/审计表与媒体目录快照。

该修复待独立复审；没有更改正式历史资料、提交 API、权限设计或 Issue 状态。
