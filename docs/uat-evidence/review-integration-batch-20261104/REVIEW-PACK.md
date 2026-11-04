# 集中独立复审入口

审查代码起点：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`。本轮新增测试/修复及最终 SHA 尚待集中交付。以下材料是 Codex 整理的审查输入，审查结论由 ChatGPT 或用户独立给出。历史有效证据按原范围保留；不要求仅为更新时间重做全部旧场景。

| 优先项 | 已有实现/来源与当前入口 | 正常、拒绝路径和实际证据 | 需独立复核或补齐 |
|---|---|---|---|
| ISS-001 / 004 / 005 | R1-A 来源 `d82643907f2886ecc412fdfa8839d2b8cc165751`；`backend/crm/services/finance.py`、`frontend/src/utils/orderOverview.js` | [R1-A](../../R1-A-核心业务历史Issue核实与修复.md)、[履约财务分离](../../R1-A-FUP-02-订单履约财务分离验收.md)；欠款完成履约、收齐、退款后待办恢复；独立采购部分收货/冲销/付款 | `test_fulfillment_receivables.py` 与 `fulfillment-receivables.spec.js` 的最终结果；跨刷新和提交后断连结果不明路径仍需具体证据；资金按本次集成前已有支持范围解读 |
| ISS-006 / 013–015 | 幂等来源 `dfa36058206fe7021ff6e6192fbbd247fb471947`；原子性来源 `7429c9630305bfad61f16475dd5617c13c07959e`；`views.py` 及履约服务 | [冲销原子性](../r1-iss006-reversal-audit-atomicity-20261030/README.md)、[Chrome闭环](../r1-iss006-inventory-chrome-uat-20261031/REPORT.md)；重复请求、冲销拒绝、库存/预留/审计回滚 | 最终 PG 并发实际数量、完整业务闭环及独立代码/截图复核。旧“从未执行 PG”须由精确 CI 和本轮专项替换 |
| ISS-007 / 078 / 092 | `FollowUpViewSet.upload_attachments/delete_attachment`、`ResourcePage.vue`；附件正常流程已在当前代码 | [文件UAT](../r1-iss007-followup-files-uat-20261031/README.md)；保存重开、私有下载、替换/删除、旧链接和权限拒绝 | 新发现服务端批量部分失败及删除审计失败一致性疑点；本轮故障注入后再定缺陷与修复。生产 ACL 单列 ISS-017 |
| ISS-019 | 来源 `cb2a90d36dbbecc062becbf13d879703b6856456`；报表 CSV 导出 | [CSV字节/权限](../iss-019-report-csv/README.md)；BOM、公式保护、正常金额及无权限拒绝 | 文件内容与当前查询口径、受限数据来源和导出权限独立复核 |
| ISS-020 / 029 | 收件人 `273d4a30689b4052e36f0d6338aeb409553aaf1f`；保存版本导出 `0eeaca68f6acf1f4029a1e955defaaafb765e046` | [报价导出](../iss-020-quote-export/README.md)、[收件人快照](../iss-029-quote-recipient-snapshot/README.md)；实际 XLSX/HTTP、缺字段422、权限403、范围404、历史图片及旧版不变 | 独立检查已保存版本/API/实际文件一致性；打印完整验收另列 ISS-037 子范围，不能用 XLSX 或网页截图代替打印成品 |
| ISS-021 | 来源 `3ec269246c39c77bb34d530d8817ba0cb136c9a6`；数量调整服务/0085迁移 | [调整闭环](../iss-021-integration/README.md)；已发货下限、付款保护、409、重放幂等及故障回滚 | 对当前代码、权限、迁移与实际HTTP数据库快照独立复核 |
| ISS-022 / 024 / 026 / 075 | MOQ、供应候选、供应商停用、付款快照；`test_purchase_moq.py`、`test_supplier_lifecycle.py`、`test_purchase_payment_terms.py` | 对应 [MOQ集成](../integration-r1-repairs-20261028/README.md)、[供应候选](../ISS-024/README.md)、[生命周期](../iss-026-supplier-lifecycle/README.md)、[账期集成](../integration-043-075-023/README.md) | MOQ边界/共享合计/越过留痕；停用排除且历史可看；新建与历史账期独立复核；真实SKU供应来源资料另由业务核实 |
| ISS-028 / 035 | 分类/SKU来源 `901b762fba20ed558f554cfba37175b303f83db9`；集成 `47fcab0f6f37f52475074e65ab7ab188352ae8ce` | [分类属性证据](../iss-028-035-category-schema/)、`iss028-035-category-schema.spec.js`；保存重开、根/子分类、属性继承和提示 | 旧“未形成修复”已不代表当前代码；需独立代码、HTTP/截图复核，不能重复派发同一实现 |
| ISS-039 | 金额分配修复 `b95852a4e4152d60976aa16d3f8e229b1e07a934`；`services/purchase_costs.py` | [金额分配](../r1-rule-gap-fix-batch-20261103/README.md)；909.09/90.91、quantity拒绝、取消、版本、权限、审计原子性 | 保留已有业务金额规则，独立核对守恒、无额外资金库存流水及PG预留竞争证据 |
| ISS-043 / 052 | CSV审计实现 `ab9ce886094a065766a24b35d9b82c7a7c0fd067`；TRUNCATE测试 `1aba37600cadbdf88aebe787d742310bac1a333f`；0091–0094及对应测试 | [审计加固](../r1-iss052-audit-hardening-20261031/README.md)；基线 PG17 CI 已有实际执行，本轮补真实PG专项 | 独立复核三表UPDATE/DELETE/TRUNCATE、历史回退保护、空表回退重建链、CSV关联/身份/原子性。实际部署数据库角色和维护绕过能力单列目标环境门槛 |

## 图像和环境边界

本轮内置浏览器访问 `127.0.0.1:55462`，后端为本包新建 SQLite 文件与专用媒体目录；它与真实 PostgreSQL 专项分别记录。首页 `screenshots/home-1440.jpg`、`home-390.jpg` 来自本集成工作树实际运行页面。窄屏截图首次捕获发生在视口切换尚未稳定时，已在读取实际390px视口与375px页面宽度后重新捕获；不以首次异常缩放图作视觉结论。

实际图像尺寸和SHA见 `screenshots/manifest.json`：桌面1440×950；请求390×844的窄屏原图实际375×812。保留工具原始字节，未缩放；该图证明所见窄屏内容，不能声称截图物理像素完全匹配请求尺寸。客户列表可正常加载并显示空态，点击新建后工具连接及恢复观察均超时，结果UNKNOWN；该步骤没有成功保存或重开证据。

旧报告引用但当前未找到的 BEFORE/AFTER 图片只登记证据定位缺项；不得补造历史图片，也不得据此认定已有修复失效。新UI工作包负责相关页面后续修改，集成包登记问题并在稳定来源纳入后统一复核。

## 已找回的历史原图

已核实 Git 对象，并原样导出以下归档；这是历史版本证据，不作为本轮集成截图。未重编码或改写原图。

- [历史第二轮原图](historical-second-review-e958.zip)：来源 `e958fe1518093d6179f8281f12bc5c722edd707e` 的 `ux-review/second-review-final/`；ZIP SHA256 `2cc2caf6c704bad9a295cc5ab3fe2db3adcc3ec18feda28288f2a0ee88b8aa15`。包含ISS-009/010及011–016对应 AFTER 图、原缺陷图、FINAL业务页面和快照图。Git blob清单见 `logs/historical-image-git-objects.log`。
- [历史精修原图](historical-polish-2c585.zip)：来源 `2c585901f9e3b7f245dc966940ef70fbd2bba237` 的 `ux-review/second-review-final/final-polish/`；ZIP SHA256 `1ff6d84af772b02cbd4fe9996ec2000fad2325a4b50adc2ebb2d3d496620b1a5`。含小数、库存成本、订单/采购确认入口、完成履约说明、商品间距及已保存PI标题共8张。

因此，上述图片的“当前主树路径缺失”已转为“原始历史归档可取得”；仍需核对对应产品版本及由独立审查接受其适用范围，不能从历史原图直接推断当前所有页面通过。
