# 商品、采购与库存界面状态盘点

已审基线 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`。本表按入口与控件行为归组。浏览器实际覆盖以截图索引与 HTTP 记录为准，未出现在索引中的状态只完成源码盘点。入口定义见 [workspaceRoutes.js](../../../frontend/src/workspaceRoutes.js) 和 [resourceConfigs.js](../../../frontend/src/resourceConfigs.js)。

## 共用状态

- 列表区分首屏加载、首次加载失败及重试、刷新、无业务资料、已有资料但筛选无结果及清空筛选。采购还独立加载供应商、订单、SKU 和逐行供应来源，商品编辑独立加载分类和供应商，SKU 编辑独立加载五类参考资料。参考数据失败和主列表失败分别取证。
- 详情区分加载、读取失败及重试、无关联记录、单页关联与分页列表、跨资源导航及返回原筛选。无更新权限和已锁定记录的分支单独识别。隔离 codex 超级管理员不覆盖普通员工受限分支。
- 表单区分初始、脏表单、原生必填、服务端字段错误、通用请求失败、提交中禁用、成功通知及重读。关闭、返回、切换页签、切换编辑对象和嵌套弹窗的保护按各自实际 guard 核查。保存中与受控网络异常需要标明延迟／阻断方式。
- 选择器区分未选、加载、无选项、搜索无结果、已有选项、修改和清空。上传区分选择、替换、取消、格式／尺寸错误、服务器拒绝、保存后重开、打开／下载、适用时的移除确认。

## 页面与子界面

| 入口 | 可达状态与数据条件 | 源码 |
| --- | --- | --- |
| 产品 `/products` | 列表搜索、分类筛选、排序；新建、列表编辑、详情内编辑；主分类级联与附加分类增删、供应商搜索多选；自动产品编码及加载回退；销售型号前缀修改影响预览、确认、失败和返回；详情概览、SKU、供应商、供应能力规则、订单记录、销售统计、出入库流水、产品参数、证书档案、销售规则与操作日志；关联新增、返回。 | [ProductPage](../../../frontend/src/views/ProductPage.vue)、[EntityDetailModal](../../../frontend/src/components/EntityDetailModal.vue) |
| SKU `/skus`，产品详情内嵌及带产品上下文新建 | 搜索、产品／状态筛选；直接及带产品新建、分步编辑、动态主／附加分类属性、必填及缺选项、候选生成、重复／已存在、缩写建议与说明、组合规则预览及保存；单条／多条候选与批量筛选、批量包装及撤销、逐条规格和基础单位；已存 SKU 编辑、身份变更复核、版本历史、停用确认、图片选择预览替换和移除；详情的产品、库存、采购／订单、供应来源、包装与日志，以及交易单位跳转。 | [SKUPage](../../../frontend/src/views/SKUPage.vue)、[EntityDetailModal](../../../frontend/src/components/EntityDetailModal.vue) |
| 分类 `/categories` | 分类树、展开折叠、搜索、选中后属性；新建根／子分类、编辑、拖动排序／改父级；新增属性、编辑属性名、继承属性与覆盖，SKU／销售型号开关、必填及大小写、属性重排影响预览与确认；关闭草稿和请求失败。 | [CategoryPage](../../../frontend/src/views/CategoryPage.vue) |
| 参数 `/product-parameters` | 列表与按产品关联、参数详情；新增／编辑、所属产品搜索与缺选项、参数分组及值／单位、保存错误与关联回跳。 | [ResourcePage](../../../frontend/src/views/ResourcePage.vue)、[resourceConfigs](../../../frontend/src/resourceConfigs.js) |
| 供应商 `/suppliers` | 名称与分类筛选、供应商新建和编辑、状态及分类，付款规则作为资料字段展示；详情概览、采购关联与日志、关联采购入口；SKU 的供应来源列表加载、空、失败、新增／编辑，供应商查找、型号／编码、报价／币种、MOQ、交期、启停、首选及采购引用。 | [ResourcePage](../../../frontend/src/views/ResourcePage.vue)、[EntityDetailModal](../../../frontend/src/components/EntityDetailModal.vue)、[SKUPage](../../../frontend/src/views/SKUPage.vue) |
| 采购 `/purchase-orders` | 搜索、状态、待收货及 SKU 关联筛选；参考数据加载与逐项失败；新建草稿、编辑已有草稿、来源订单选择、供应商选择、SKU/供应来源选择、参考价／MOQ、交易单位及数量换算、添加与删除多行、金额与汇率、保存／离开保护；详情任务、明细、来源订单、到货及日志；草稿确认、删除确认、取消原因；不同来源订单／无来源、单／多 SKU、基础及交易单位。 | [PurchaseOrderPage](../../../frontend/src/views/PurchaseOrderPage.vue)、[PurchaseDetailModal](../../../frontend/src/components/PurchaseDetailModal.vue) |
| 采购成本分配 | 从采购详情打开；加载、可分摊来源、金额与目标行，多订单条件、已有分配回显、合计核对与校验、提交失败、关闭后回到原详情。 | [PurchaseOrderPage](../../../frontend/src/views/PurchaseOrderPage.vue)、[PurchaseCostAllocationModal](../../../frontend/src/components/PurchaseCostAllocationModal.vue) |
| 采购收货与冲销 | 待收、部分、已收、取消状态；分行收货，基础／交易单位、收货数量上限、库位及批次输入，提交中／重复／错误／成功；已有收货流水、冲销原因及可冲销条件，结果重读和导航。 | [PurchaseOrderPage](../../../frontend/src/views/PurchaseOrderPage.vue)、[PurchaseDetailModal](../../../frontend/src/components/PurchaseDetailModal.vue) |
| 库存 `/inventory` | 关键词、排序、需关注、正常／零库存／异常；实际、预留、可用、在途和待采购；详情抽屉及关联库存流水、订单、采购、出库、操作日志；每个 tab 的空、筛选、排序及目标链接，加载失败及重试。 | [InventoryPage](../../../frontend/src/views/InventoryPage.vue) |
| 库存流水 `/inventory-movements` | 日期、类型、SKU、来源等筛选与关联跳转；手工调整表单、仓库／库位／批次字段及为空／有值；自动流水及已冲销只读，手工流水冲销原因及确认、服务端拒绝、重试待核对、已保存回显。当前基线路由没有独立仓库、库位或批次维护页，应在收货、调整和流水详情验其可达控件。 | [ResourcePage](../../../frontend/src/views/ResourcePage.vue)、[resourceConfigs](../../../frontend/src/resourceConfigs.js) |
| 包装 `/sku-packaging` 及 SKU 内包装 | 名称、策略、启停筛选；新建、编辑、复制；纸箱尺寸、箱重、尾箱策略说明与不同条件；模板详情、关联 SKU 列表及跳回；SKU 内箱规查询、选用／清除、嵌套新建模板、单条或批量赋值。 | [PackagingPage](../../../frontend/src/views/PackagingPage.vue)、[SKUPage](../../../frontend/src/views/SKUPage.vue) |
| 交易单位 `/sku-trade-units` | 未选 SKU、选中无规格、有规格、切换 SKU 与未保存保护；通用与供应商专用、换算预览、仅整数／允许小数、重复提示、新增、编辑备注、不可改的换算定义、启停与默认切换、返回 SKU。 | [TradeUnitsPage](../../../frontend/src/views/TradeUnitsPage.vue) |
| 产品证书 `/product-certificates` | 全部、临期、过期等筛选，关联产品多选，证书详情与状态；新增、编辑、签发／到期日期、无文件／选择附件／替换／查看下载、校验失败保留、保存后重开。 | [ResourcePage](../../../frontend/src/views/ResourcePage.vue)、[EntityDetailModal](../../../frontend/src/components/EntityDetailModal.vue) |
| HS 编码 `/hs-codes` | 列表搜索、排序、状态筛选；新建／编辑、启停、重复校验；绑定产品抽屉、搜索、勾选、批量选择当前结果、已有绑定、加载失败／提交错误，保存后刷新数量。 | [HSCodePage](../../../frontend/src/views/HSCodePage.vue) |

采购付款、应付计划和资金恢复由 A2 覆盖。完整打印成品与分页继续延期。
