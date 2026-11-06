# 报价 PI 主体资料消费与历史税号兼容核对

基线 `506b14f293fe8fcb989eeaf1c5d35866624553ad`；本记录针对工作树未提交修改，非独立复审结论。

源码核对：基线 PI API 从旧报价返回 `buyer_tax_id`，历史 `NULL` 可作为 JSON `null`；原 XLSX DTO 使用 `quote.buyer_tax_id or ""`，把未知变为空串。保存的打印模板可能把未知显示为空，旧模板也可能没有税号占位符。基线行为的结论来自源码核对，未在该精确基线单独运行 HTTP 实验。

当前行为：PI 和 XLSX 共用 DTO；模板需输出的买方字段为 `NULL` 时，两端返回 422，明示未知及模板不能区分未知和留空；空串可输出。无扩展记录时仍读取旧报价快照，历史税号为 `NULL` 的数据不写入、不补造。存在内容为 `NULL` 的扩展记录时拒绝，不回退旧字段。批准资料链不一致拒绝。已保存卖方及银行继续使用原模板；卖方已知资料与模板不符或无法映射时拒绝。

**兼容影响：**原本可预览或导出的合法旧报价，若税号为历史未知 `NULL`，现在不能通过 PI 或 XLSX 输出。这是无法安全区分未知和留空时的输出限制，不是判定报价无效；不能宣称对旧报价无影响。现有模板不能原地改写，且用户要求未知不能默默显示为空，因此在当前限制内未找到同时保持旧输出和明确表达未知的实现。历史未知不允许通过主档自动补值；恢复输出需要另行明确可安全表达未知的方案或业务处理规则。

验证：`python manage.py test crm.tests.test_quote_details_pi_export crm.tests.test_quote_template_snapshot crm.tests.test_quote_buyer_tax_id crm.tests.test_quote_unknown_buyer --noinput --verbosity 1`，本机 Python 3.14 / SQLite，51 项通过。包括无扩展历史 `NULL` 拒绝及值不变、空串与 `NULL`、真实申请批准应用后修改客户主档、分别选择零折扣及有折扣保存模板并对账 PI/打印 HTML/实际 XLSX 的买方单元格及卖方名称、首条银行值，以及篡改后两端拒绝。XLSX 在隔离测试中生成并读回，未留存文件。没有对全部银行行、真实历史库或生产环境做本轮核验。GitHub CI 按额度暂停，未运行；PostgreSQL 未运行。

## 买方未映射扩展字段补核

当前保存模板和渲染器没有 `buyer.country`、`buyer.contact`、`buyer.billing_address`、`buyer.shipping_address` 的独立位置。当前报价版本的扩展资料中，任何上述字段为非空字符串时，PI 和 XLSX 共用 DTO 返回 422，并列出所有非空未映射字段；不输出这些值，也不更改保存资料。`contact` 无论是否与 `recipient` 相同均不代替收件人。各字段为 `NULL` 或空串时，不因该未映射字段单独阻止输出；这不代表模板展示或证明了这些字段的状态，不能声称双方扩展资料已完整输出。

兼容影响：此前可能成功输出但静默遗漏上述已保存值的报价，现在会被阻止，包括原本有效的报价；现有模板不增加位置、不重写，恢复完整输出需另行明确模板映射或业务处理。无扩展记录的历史报价不因这四项新增拦截，仍受上文历史未知字段限制。

本次 Python 3.14 / SQLite 定向回归：`crm.tests.test_quote_details_pi_export crm.tests.test_quote_template_snapshot crm.tests.test_quote_buyer_tax_id` 43 项通过；随后额外单独运行真实审批后联系人变更及两模板未映射字段/多字段提示 2 项通过。两次测试有重叠，不相加为独立测试总数。未运行 PostgreSQL 或 GitHub CI。
