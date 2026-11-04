# 02140bf 前端闭合验收证据：FAIL

来源代码 SHA：`02140bf46df27ba1abf5b9018507c07aae825769`。本报告封存已结束的 9-profile 结果，没有重跑测试。

## 实际结果

- Node 单元测试：179 通过，0 失败。
- 字体排版测试：1 通过，0 失败。
- Vitest：78 个文件、725 项通过，耗时 159.10 秒。
- `npm ci`：exit 0；新增 227 个包并审计 228 个包；日志记录 4 项 moderate audit finding 和弃用包警告。
- 生产构建：exit 0，2.22 秒完成；保留单个压缩后超过 500 kB 的 chunk 警告。
- Playwright：9 profiles 合计 **262 通过、1 失败、0 跳过**；汇总 `allPassed=false`。
- 打印验收：7 项 deferred，未运行。

Profile 明细：

- business-suite: exit 0, 238 passed, 0 failed, 0 skipped
- shared-report-templates-isolated: exit 0, 1 passed, 0 failed, 0 skipped
- quote-editor-isolated: exit 1, 0 passed, 1 failed, 0 skipped
- iss006-storage-isolated: exit 0, 10 passed, 0 failed, 0 skipped
- iss007-attachment-isolated: exit 0, 3 passed, 0 failed, 0 skipped
- iss007-image-snapshot-isolated: exit 0, 1 passed, 0 failed, 0 skipped
- iss022-isolated: exit 0, 1 passed, 0 failed, 0 skipped
- iss028-035-isolated: exit 0, 2 passed, 0 failed, 0 skipped
- iss055-rbac: exit 0, 6 passed, 0 failed, 0 skipped

## 失败路径

唯一失败在 `quote-editor-isolated`：`download.saveAs: canceled`。失败测试 ID：`854db0be8c3252fde029-7f26666a6152537d1886`。保留该 profile stdout/stderr、`.last-run.json` 和 `playwright-suite-summary.json`。Playwright 引用的 `artifacts/6dad47d0-8210-4d79-a641-242a2d8e7282/quote-editor-mobile-action-261fe-reserve-preview-save-export/error-context.md` 在捕获时缺失；不以其他文件冒充该 context。

## 发布与完整性

- 完整闭合日志 ZIP：`logs/final-02140bf-frontend-closed-logs.zip`，24 个日志成员，ZIP CRC 已验证。
- 来源清单：`SOURCE-EVIDENCE-MANIFEST.json`。捕获到 308 个源文件；另有 17 个路径无法读取或在捕获期间发生变化，SHA 标记 UNKNOWN。
- 发布清单：`PUBLISHED-EVIDENCE-MANIFEST.json`；记录每个已发布文件的 SHA、原始/发布 SHA 对账和日志 ZIP CRC。
- 凭据审计：`PUBLISHED-REDACTION-AUDIT.json`。对发现的闭合隔离 token 仅脱敏发布副本；原始源文件未由本任务修改。源目录后续是否保留为 UNKNOWN。
- 扫描汇总：Cookie/session 值 0；日志中 22 个 seed/secret 凭据值及 HTTP JSON 中 11 个闭合隔离 token 字段已在发布副本中脱敏。共 14 个文件发生脱敏；审计记录各自原始/发布 SHA，不含凭据值。
- 所捕获的 PNG、PDF、XLSX、CSV 均逐字节保留。
- 独立 quote 下载根因诊断目录 `quote-download-sandbox-compare-20261105` 已从最终发布包剔除。首次暂存曾误将其复制到发布目录；纠正后已删除该发布副本，源目录未修改。

本包保留失败结果，不代表前端验收全通过。
