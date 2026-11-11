# 历史导入交付：核查工作记录（未完成）

被测共同基线：`c21a1060cb99bdf6bda33a07c7ba01b990f4878f`。本目录中的两个空 XLSX 由该基线的服务端模板生成函数直接生成，并非手工维护的字段副本；最终使用前应从目标系统重新下载，以目标版本为准。

## 已核对的入口和边界

- 客户主档：数据导入的客户 CSV；字段为 `code,name,country,source,website,address,notes`，其中 `code,name` 必填。按客户编号可能更新现有资料，预览时应检查新增/更新数及覆盖范围。
- 已发生历史业务：历史资料承接模板 v2，包含分组、销售订单、销售明细、采购订单、采购明细、收付款计划、收付款流水、履约记录及库存盘点。原系统编号与同组关联编号须保留；真实性、覆盖范围及凭证须按实际证据填写。历史商品可在缺少正式 SKU 时归档，之后经人工核实关联。
- 历史资金：来源流水先归档并核实；正式资金事实须走独立的受控资金承接步骤及审核，不能凭合同汇率猜测实际人民币到账金额。实际到账和来源对应必须有凭证。
- 未结应收应付、启用库存及剩余履约：分别核实来源、余额、盘点和实际履约，并走既有受控承接流程。归档或关联 SKU 本身不等于产生正式资金、库存或履约事实。
- 新销售草稿：`sales-order-import-template.xlsx`；来源订单编号、客户编号、订单日期、币种、SKU、交易单位、数量、单价必填，对人民币汇率列可按模板说明填写。客户与 SKU 必须已存在，交易单位须有效。此入口仅创建草稿，不适用于已收款或已发货历史订单。

历史模板的必填字段以工作簿和服务端预检为准；部分业务规则还要求凭证、准确关联、审批和完整性，不应以表头必填清单代替预检。未知事实保持待核实，不补造。真实文件尚未取得，未进行真实文件适配。

## 尚未完成

本记录不是交付验收：贯通的单批次隔离试导、合成示例、金额及来源行核对报告、正式资金和履约前后差异核对、精确提交 CI 均未完成。既有 CSV 审核报告汇总预检结果，尚未证明满足本任务全部对账维度。不得据此申请正式导入。独立工作树不应连接正式业务库；真实文件和报告应保存在仓库外。

## 本次定向自动测试

在独立工作树的 Django 测试数据库和独立媒体目录运行 `test_history_import_preflight`、`test_history_takeover`、`test_history_products`、`test_history_operational_finance`、`test_history_operational_inventory`、`test_sales_order_import`、`test_safe_csv_import`：115 项，OK，跳过 9 项。SQLite 跳过项不能视为 PostgreSQL 并发验收。测试数据库已由测试运行器销毁；测试不是单批次贯通试导，也不替代正式对账。

模板 SHA-256（生成时）：历史承接 v2 `d80efcc4150b8772b61cff8d28e41f6e1960e2b80225fc5d8b9104e6fc39e025`；销售草稿 `875cac82fedfda1e563b3c09a6c6c1c8b3e31e125f95df735e6a79192205c271`。XLSX 内部元数据可能使重新生成的字节哈希不同，应按实际文件核对。

## 2026-11-12 补充核对

GitHub 将 `Johnson-Yiu/SUNJACK-ERP` 解析至 `Johnson-Yiu/SJERP`；目标分支在远端查询时不存在。本地原分支仍在共同基线，原成果未被清理。`synthetic-customers-example.csv` 和 `synthetic-history-example.xlsx` 均由 `generate_synthetic_examples.py` 调用现行字段和既有测试夹具生成。历史样例标为“模拟”，用于阅读字段和预检，不可作为真实凭证申请执行；其来源编号仅具合成意义。客户样例有对应历史客户编号，但历史示例另含合成供应商、商品和履约、财务资料，不能直接当作完整执行批次。

本次独立 SQLite 测试库另运行以下四项，4 项通过：`test_group_balance_stock_receipt_shipment_and_later_settlement`、`test_archive_with_empty_master_then_link_single_and_batch`、`test_failure_in_later_business_write_rolls_back_the_whole_group`、`test_explicit_amount_review_post_and_idempotent_replay`。测试使用不同夹具和事务，不能合并表述成同一批次的贯通对账。当前 Python 环境缺 PostgreSQL 驱动，旧 PostgreSQL 专用虚拟环境指向已不存在的 Python；本次 PostgreSQL 验证未运行。参考其他任务的历史演练记录不能替代本基线试导。

仍须补齐：客户 CSV 到历史订单的同批次试导、重复来源及组内错误与安全重试、各币种及运费折扣核对、来源行映射和不应发生的库存履约变化、可复用只读核对程序、合成资金实际到账对应凭证、最终 CI。未取得真实文件，不代表真实文件已适配或通过验收。

## 2026-11-12 同批次回归进展（仍未完成）

新增 `crm.tests.test_history_delivery_same_batch`：客户 CSV 预览/执行后，以同一组来源申请归档；原正式 SKU 为空；注入归档中途异常并确认事务回滚，原组重试、重复执行幂等；创建 B 并关联两条历史商品；归档和关联阶段正式资金、库存及履约计数均为零；随后用合成凭证和分离的审核人将源收款对应实际人民币 287.43 受控入账并验证重复入账幂等。样例源流水原币 USD 40。工作簿文件字节保持相同验证重复提交复用。SQLite 与项目隔离 PostgreSQL 17.11 运行器各 1 项通过，PostgreSQL 测试库及临时集群清理完成。此测试中的“真实”标记是隔离测试对审核条件的模拟，不是实际业务真实性声明。

未覆盖：完成订单、重复来源但文件内容不同、组内错误、完整来源映射及只读报告、实际完整对账输出。未取得真实文件。本地使用锁定依赖的专用虚拟环境；本次仍非最终交付。

先前 `dde7ef452363e9398cce86303fe69608393e5230` 的 CI：backend 与 backend-postgres 成功；frontend 在安装 Chromium 系统依赖阶段因 Ubuntu 软件源 DNS 解析失败，未运行前端测试（run 43060984382）。
