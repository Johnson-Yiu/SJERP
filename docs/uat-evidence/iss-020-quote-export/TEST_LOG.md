# ISS-020 测试日志

日期：2026-10-26
分支：`codex/iss-020-quote-export`
基线：`28ba758388429f57c2e3516e12385a88ce6646a3`

## 缺陷先行复现

在修补前运行新增回归夹具 `python -B manage.py test crm.tests.test_iss020_quote_export --verbosity 1`：

- 不完整已保存报价的 `/api/quotes/<id>/export/` 返回 200/XLSX，而规则要求关键买方和币种缺失时提示且不生成错误文件。
- 两行 `1.005` 的逐行金额在 Excel 中为 `1.01 + 1.01 = 2.02`，但原预览小计按原始浮点和显示为 `2.01`，预览与正式文件不一致。

这两项是本轮确认的真实问题；没有因假设而修改图片快照、报价主体快照或核心查询引擎。

## 修补内容

- 后端导出 DTO 统一读取保存报价/QuoteItem 快照，并在正式导出与 `/pi-data` 预览共用校验和分币舍入结果。
- `quote_no`、买方公司、币种、商品明细及数量/单价缺失或无效时返回 422 和字段提示，不生成 XLSX；空邮箱仍保持为空。
- 逐行金额按分币舍入后再合计，运费/折扣/总额与英文大写均以同一导出 DTO 为准。
- 未保存编辑器预览使用相同的逐行分币规则；保存预览仍标识“已保存报价预览”，未保存预览保持独立。

## 自动化结果

| 检查 | 命令/结果 |
|---|---|
| ISS-020 后端专项 | `crm.tests.test_iss020_quote_export`：4/4 OK |
| 报价/修订专项 | `crm.tests.test_quotes.QuoteExportTests crm.tests.test_quotes.QuoteRevisionTests`：25/25 OK（与 ISS-020 合并运行） |
| 权限正向/无权 | `test_quote_export_and_import_actions_use_special_permissions`：1/1 OK，403 路径保留 |
| 跨客户数据范围 | `test_related_lists_details_and_context_inherit_customer_scope`：1/1 OK，详情/导出越权拒绝 |
| Django 全量 | 915 tests，13 skipped，OK；`full-django-test.log` |
| 前端 Node | `npm run test:unit`：151/151 pass |
| 有效 Vitest | `npx vitest run tests/pi-amount-words.spec.js tests/crm-list.vitest.js --environment node`：12/12 pass |
| 前端生产构建 | `npm run build`：pass；仅有既有大 chunk warning |

仓库直接运行未筛选的 `npx vitest run` 会把大量 `node:test` 文件误纳入 Vitest，并报告 `No test suite found`、`document/localStorage is not defined`；该入口不是项目有效 Vitest 口径，未将其失败计入 ISS-020 有效回归。

## API/XLSX 证据

`capture_api.py` 通过隔离服务 `http://127.0.0.1:28341` 保存真实响应：

- `version-a.xlsx`：11,605 bytes，SHA-256 `1ef0952b9013def37c9c544ac3ac9516d40abc552ff83a8f58ff8b6e93c9c626`；USD 250.00；收件人 Version A；金额大写 `SAY TOTAL US DOLLARS TWO HUNDRED FIFTY ONLY`；包含 `xl/media/image1.png`；打印区域 `'PI'!$A$1:$M$35`，portrait，公式单元格为空（金额以已核定静态值输出）。
- `version-b-empty-email.xlsx`：11,531 bytes，SHA-256 `c7c82dc1c81af569fc733093cec0cd95e28add1024812d3ec5486dd0550d867f`；EUR 247.50；收件人 Version B；邮箱为空；金额大写 `SAY TOTAL EUROS TWO HUNDRED FORTY SEVEN AND CENTS FIFTY ONLY`；包含 `xl/media/image1.png`；打印区域 `'PI'!$A$1:$M$34`，portrait，公式单元格为空（金额以已核定静态值输出）。
- 不完整报价：HTTP 422，字段 `buyer_company_name`、`currency`，无 XLSX 文件生成。
- 主档后续改名、改地址、改型号和替换蓝图后，两个版本 API/XLSX 仍使用 `ISS-020 Historical Buyer`、`ISS020-MODEL-HISTORICAL` 和红色历史图片路径。

## 权限和部署边界

开发环境按 `AGENTS.md` 的 `development_superadmin_enabled()` 统一为开发超级管理员，不能冒充生产员工账号。后端已有无导出权限 403 和跨客户范围拒绝回归；生产 PostgreSQL、反向代理、真实账户权限、Excel 桌面打印及 CI 未在本地冒充通过。

未合并 master，未关闭 Issue，状态保持 `FIXED_PENDING_REVIEW`。
