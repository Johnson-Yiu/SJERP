# R0-D2 — Unified Unsaved Changes Guard

基线：`7a5e44525be8d17bbbec6e850c7756808a669fe0`。

## 公共机制

`frontend/src/composables/useUnsavedChangesGuard.js` 提供 `setBaseline()`、`dirty`、`markClean()` 和 `requestClose()`。稳定快照比较全部可编辑数据，覆盖嵌套商品行、联系人、SKU 参数和包装、组合选择及待上传文件；初始化完成前不判断 dirty。

主动关闭和路由导航统一调用现有 custom confirmDialog，标题“未保存修改”，内容“当前修改尚未保存，离开后将丢失。是否继续？”，按钮“继续编辑 / 放弃修改”。取消保持数据与路由；路由真正成功后才清除 dirty，后续导航被其他 guard 拒绝时仍保留保护。dirty 时注册标准 beforeunload，clean 或卸载后移除；没有使用 window.confirm。

嵌套编辑器通过公共 scope 注册，父详情关闭或切换标签也检查子编辑器。没有编辑器的只读详情 scope 不弹确认。

## 覆盖与基线

- QuoteEditorModal：新建、修订、商品行；客户及联系人预填完成后建立基线。
- DocumentPage Direct Order：新建、编辑、来源报价载入；预填后的日期、币种、汇率属于 clean。
- OrderDraftModal：从报价生成的订单草稿，初始化行及交易单位转换后建立基线。
- PurchaseOrderPage：创建、编辑及订单/供应商 route prefill；全部供货档案载入后建立编辑基线。
- ProcurementDraftModal：订单履约生成采购草稿，分组、数量、价格与汇率初始化属于 clean。
- SKUPage：参数、型号缩写、包装、组合及图片；异步缩写与派生明细完成后建立基线。
- RelatedCreateModal：现有通用对象及订单；报价复用报价编辑器。
- ResourcePage：Customer、Supplier、Contact、FollowUp 及现有通用主数据，包含客户联系人。

主记录 API 保存成功后先 markClean，再关闭或导航。失败保持 dirty。SKU 主体与包装已成功但图片失败时，在刷新与派生数据稳定后重新 markClean，保留原图片重试入口。FollowUp 主记录成功后不将附件失败误判为主记录未保存。

## 自动验证

- 新增 focused tests：13 PASS，覆盖 clean/dirty 关闭、商品行、保存失败与成功、路由取消/放弃、Back、采购价格、SKU 包装、联系人、RelatedCreate、报价/订单采购预填、beforeunload、嵌套父层关闭及附件部分成功。
- Frontend Vitest 全量：47 文件、465 测试；Node unit：115；独立排版：1。
- Backend 全量：614，OK（10 skipped）；migration check：No changes detected。
- 生产构建通过；保留现有 chunk size 提示。

## 页面验收与证据

Chrome 连接两次重试仍失败；遵循用户既有授权，使用内置浏览器完成真实页面验收。未保存输入仅用于界面测试，均放弃，没有改写业务记录。

1. 新建报价默认 clean，关闭无确认；填写备注后关闭出现统一确认，继续编辑保留备注。
2. 采购新增商品并填写 12.50 单价后关闭出现确认，继续编辑保留价格。
3. SKU 编辑载入后直接关闭无确认；包装整件数量 10 改为 11 后关闭提示，继续编辑保留 11。
4. 新建订单填写备注后浏览器 Back 提示；继续编辑保留 URL 和备注，再次 Back 放弃修改返回原 SKU 列表。

截图只存于 `ux-review-evidence`，目录 `ux-review/r0-d2-unsaved-guard/`：

- `R0D2_01_quote_unsaved_confirm.png`
- `R0D2_02_purchase_unsaved_confirm.png`
- `R0D2_03_sku_unsaved_confirm.png`
- `R0D2_04_navigation_unsaved_confirm.png`

最终 production SHA、exact-head CI 与 evidence SHA 见交付报告。完成后停止，等待独立审查。
