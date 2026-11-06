# 合成正式报价 PI / XLSX 验收样本

本目录包含零折扣和有折扣各一组 `.xlsx`、`.pi.json` 与 `.reconciliation.json`。两组均由隔离内存 SQLite、合成客户/SKU/卖方/银行、三个合成账号生成；报价更正经申请、不同账号审批和应用，修订转为 `sent` 后修改合成客户主档，再调用实际 PI 和导出 API。合成账号只能证明账号不同，不证明真实人员独立。税号明确留空，Excel 的 B6 读回为 `null`；与历史未知 `NULL` 不等同。

为避免泄露真实资料，生成脚本仅在系统临时目录中复制两份既有模板的布局结构，清空所有单元格内容、图片、图表、注释、超链接、页眉页脚、外部链接、定义名称和文档属性，写入合成卖方/银行数据；临时副本用于捕获模板快照。样本不是原模板字节，且原模板标签等内容已清除，不能作为真实资料、原模板内容或最终打印样式验收。脚本核对原模板卖方和银行非短文本未出现在生成文件的 XML 或 PI JSON；另检查 XLSX 包不含图片、绘图、外链、注释或自定义 XML 等附加部件。未连接实际业务数据库或写入现有业务模板。

样本的 PI、XLSX 均为 HTTP 200；对账 JSON 包含模板及文件 SHA-256、买方 B3–B8、卖方 I3、首项银行值、报价状态和主档变更标记。样本及快照摘要每次生成可能因元数据而变化。

运行环境：CPython 3.12.16，`backend/requirements.lock` 的 16 个精确版本与环境一致，`pip check` 通过。使用同环境运行 `crm.tests.test_quote_details_pi_export crm.tests.test_quote_template_snapshot crm.tests.test_quote_buyer_tax_id crm.tests.test_quote_unknown_buyer`，SQLite 54 项通过；这只是本轮定向回归，不替代用户统一执行的最终回归。GitHub CI 暂停，PostgreSQL 本轮未运行。先前 Python 3.14 结果不是最终验证。

生成过程两次初次尝试均未写出样本：第一次隔离客户端 `testserver` 不在允许主机，第二次两组合成 SKU 使用同一销售型号触发唯一约束。仅修正本目录生成脚本的测试主机和合成型号后重跑成功，未修改产品代码。失败为运行时输出，未保留独立日志。

本轮完成时产品文件 SHA-256：

- `backend/crm/quotation_export_dto.py`: `e8325c89f0f01e96f9bdefd99d02808cc0a55d8419312862c9431cc9c253e95f`
- `backend/crm/views.py`: `12788b31007e26177b57ebc4f0cbd615bde5a7e098ad1fca5b09514bcff62a8a`
- `backend/crm/tests/test_quote_details_pi_export.py`: `e01d149a6762789b376a2a100b114bbf33aa8b5cad63eeb3718561eb7375c743`

历史未知税号和未映射扩展字段的兼容限制见上级目录 `pi-export-compatibility-20261106.md`；本样本不覆盖这些拒绝场景。
