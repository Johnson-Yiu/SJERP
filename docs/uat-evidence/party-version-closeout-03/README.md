# PARTY-VERSION-CLOSEOUT-03：验收记录

基础提交 `506b14f293fe8fcb989eeaf1c5d35866624553ad`。本轮继续既有独立工作树，未修改公共台账或已发布迁移。所有数据为合成资料、隔离数据库和独立媒体；两个认证账号不证明自然人独立。CI 因额度暂停，未运行，不计为通过。

## 业务口径和变更

用户授权助手选择冲突口径：报价当前版本经批准的扩展资料优先；明确留空保持空，未知明确拒绝并提示，不从原字段或当前主档补造。未保存扩展资料的旧报价使用原有快照，历史未知仍不能伪装为空。单一收件人位置明确使用 `recipient`，不以 `contact` 代替。

PI 和 XLSX 共享经审批／版本校验的报价 DTO。已映射买方名称、收件人、地址、税号、邮箱和电话；对主体资料篡改、未知值、卖方与保存模板不一致，以及非空但模板没有位置的资料明确拒绝。新行为对部分历史未知税号报价及含未映射资料的报价会从原先可导出变为 422，未改历史数据；这是需要业务运营处理的兼容影响。

SO/PO 原始快照卡片标注为原始，指向当前有效版本；主体审批差异区分历史未记录与拟议明确留空。采购／销售替换不再错误显示报价专属限制提示。

## 待定及未覆盖

现有模板未提供买方国家、联系人、账单地址、收货地址，以及卖方国家、税号、账单地址、收货地址和收件人的明确独立位置。需要确定各字段是否在正式文件显示、字段标签和具体模板位置；尤其联系人与收件人并存时不得混用。独立税务注册号是否需要区别税号及适用国家、卖方资料更正与银行账户归属如何核对，也需明确。不得改写历史保存模板或将当前主档冒充历史事实。含扩展资料的报价法律主体替换仍安全拒绝，待完整模板表达和对应快照验证后才能开放。

未发现独立 SO/PO 正式文件输出入口；现有报价 PI、XLSX 和发货装箱单不能冒充 SO/PO 正式文件。是否新增 SO/PO 正式文件及字段模板属于单独待定范围。本轮不声称 ISS-037 整体验收完成或关闭；系统打印框和分页按用户之前决定延期，不扩大为其他主体要求延期。

## 当前证据

两套合成正式报价在批准后改变客户主档，再生成 PI 和实际 XLSX：[无折扣](../party-version-closeout-20261105/pi-synthetic-evidence/no-discount.xlsx)、[有折扣](../party-version-closeout-20261105/pi-synthetic-evidence/with-discount.xlsx)、[数据与生成说明](../party-version-closeout-20261105/pi-synthetic-evidence/README.md)。模板为脱敏副本，只证明字段及快照，不代表原模板字节或打印样式。[历史兼容及未映射字段](../party-version-closeout-20261105/pi-export-compatibility-20261106.md)记录旧报价输出限制。

销售及采购主体替换的合成样本包含客户收款、供应商付款、采购入库及销售发货；原始单据、资金、付款计划、履约和库存流水的前后快照一致：[浏览器报告](../party-version-closeout-20261105/browser-recheck-after-copy-20261106/README.md)、[实际日志](../party-version-closeout-20261105/browser-recheck-after-copy-20261106/run.log)、[采购390截图](../party-version-closeout-20261105/browser-recheck-after-copy-20261106/extended/purchase-review-390.png)。覆盖两个认证账号、桌面和390×844，无法证明自然人独立。最终源码的报价基础替换双视口和 PI 读取通过：[日志](logs/chrome-quote-final.log)、[桌面截图](chrome-quote/replacement-quote/review-desktop.png)、[390px截图](chrome-quote/replacement-quote/review-390.png)；含扩展资料的报价替换未开放。

PostgreSQL 17.10 专项 204 项通过，完整升级、模型检查、回退拒绝和临时库清理通过，源码哈希前后一致：[日志](logs/pg17-final/party-tests.log)、[结果](logs/pg17-final/result.json)。锁定 Python 3.12 的 SQLite 定向 74 项通过：[日志](logs/backend-targeted-final.log)。生产构建通过：[日志](logs/build-final2.log)。有效 Vitest 81 文件 767 项通过：[日志](logs/vitest-final2.log)；首次 1 项文案断言失败，保留[失败](logs/vitest-final.log)。Node 全量 179 项通过：[日志](logs/node-final.log)。SQLite 后端全量在用户要求停止前已结束：1577 项运行、99 项条件跳过，其余通过：[日志](logs/backend-full-final2.log)；不将跳过记为通过。用户随后要求仅执行定向测试，本轮不再重复全量。此前为补回被误删的主档保护提示，中断的[全量日志](logs/backend-full.log)不计通过。

## 迁移和集成边界

本轮未新建迁移；继承 `crm.0113`→`0114`→`0115`→`0116`→`0117`，依赖上一版本的 `0112_party_quote_application`。集成时须核对其他分支的编号与依赖，保留既有保护并复验。共享改动为报价 DTO、PI 数据视图及主体详情组件；不修改资金／库存规则，不部署，不启用正式 RBAC，不关闭 Issue。
