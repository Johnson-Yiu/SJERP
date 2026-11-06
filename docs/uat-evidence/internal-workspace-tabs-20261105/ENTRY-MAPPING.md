# 入口映射与分类（固定基线）

基线 `10afcf16fbfc1d0c01a175094012b4b696483cfb`。全量原始事件与实际函数正文见 `baseline-handler-map.json`：64 个 Vue 文件、769 个可见事件绑定、832 个声明式函数。`action-inventory.json` 是初始事件索引，不能替代函数正文。下表的验收列是所需场景，实际通过/失败以 TEST-RESULTS.md 为准，不表示全部已执行。下表描述实际页面族及其动作处理链；短操作中的原确认、业务校验、API 和状态值保留。

|实际路由/入口 → 处理函数|原行为|新行为与分类依据|保留状态|验收|
|---|---|---|---|---|
|侧栏全部 `RouterLink`（App 的 nav）|替换唯一 RouterView|按业务模块复用独立列表标签；再次点侧栏恢复已打开工作区，列表筛选不清空|URL、筛选、分页、选中、DOM 滚动|模块往返、关闭与顺序、390px 横向标签|
|`/customers`、`/suppliers`、`/contacts`、`/follow-ups`、`/inventory-movements`、`/product-parameters`、`/product-certificates` → ResourcePage `openDetail`|本页 detailId 或 detail query 打开 EntityDetailModal|对象可独立办理：打开对象标签；同 path+对象 ID 去重，客户详情页签仍在对象内|原列表和每个对象的筛选/选择、详情子页签|两个客户、客户联系人双向、带 SKU 流水详情与返回|
|以上 ResourcePage → `openCreate`（界面由 newWorkspaceDraft 适配）|本列表弹出编辑器|独立新建工作区，每次 UUID；原编辑器仍承担输入与提交，不改变创建权限|两个同路由草稿、关联预填、附件选择|两份客户草稿不同名称、切换0额外请求、取消关闭|
|ResourcePage → `openEdit`、`editFromDetail`、`save`、`closeModal`|当前对象编辑、保存、取消|对象编辑属于当前任务；继续使用现有未保存 guard，保存不生成重复标签|form、联系人行、附件、editingId|保存失败保留、取消放弃、相关标签过期提示|
|`/quotes`、`/orders` → DocumentPage `activateQuoteTreeRow`、`openDetail`|详情 query 驱动工作台|对象标签；报价树展开 `toggleQuoteNode` 仍是列表局部行为，不生成标签|报价树展开集合、列表筛选、每个对象工作台子页|报价根/修订、两个订单、浏览器历史|
|DocumentPage → `create`、`edit`、`loadSourceQuote`、`save`、`handleQuoteSaved`|订单编辑或报价修订窗体|新建为独立任务；编辑/从报价载入为当前任务，保留原覆盖确认及修订语义|销售草稿、SKU 选项、来源报价、报价预览|两个新订单、载入确认取消、保存后 URL 和详情|
|DocumentPage → `remove`、报价导出 `exportQuote`|确认后删除；下载 XLSX|仍是确认/文件动作，不改成标签或绕过确认|业务写入锁、原下载生命周期|删除取消、原单据/导出回归|
|`/purchase-orders` → `togglePurchaseDetail`、`startCreate`、`editDraft`、`createPurchase`|采购列表详情/采购草稿|详情对象标签，新建独立草稿，编辑保留当前工作区|supplier/order 预填、供货档案、MOQ/付款快照、草稿内容|多个采购任务与来源订单往返|
|PurchaseOrderPage → `receive`/收货提交、`submitReceiptReversal`、`place`、`cancelPurchase`、`deleteDraft`、`pay`|收货/冲销/确认/取消/删除/付款子窗体|原短业务操作、确认与原因输入保留；不把写操作改成导航|收货数量、请求标识、原校验/锁|原采购、幂等、库存、费用与导出回归|
|EntityDetailModal → `drill`、`back`、`relationWorkbenchLocation`、`quickCreate`|关系栈、关系工作台或 RelatedCreateModal|已表达独立路由的关联对象进入标签；当前任务内部局部关系栈/短关联创建保留子窗体|详情 stack、当前 tab、局部选择|客户/联系人、产品/SKU、订单/采购关联与返回|
|OrderDetailModal/QuoteDetailModal/PurchaseDetailModal → `useDetailTab`、`load`、原编辑与履约 emits|工作台子页与动作|工作台页签仍是页内前进；入库、出库、成本、审批和附件不改变动作含义|工作台子页、未保存子表单|原工作台、合同金额、出入库、成本回归|
|`/products`、`/skus`、`/categories` → 原 load/create/edit/detail/规则编辑|列表、抽屉与编辑器|模块工作区；路由化独立对象为对象标签，嵌入 ProductWorkspace/SKU 选择及分类编辑仍为当前任务|参数、SKU、图片 object URL、分类路径、选择|产品/SKU 既有回归；失活暂停文档监听，关闭撤销对象 URL|
|`/sku-packaging`、`/sku-trade-units`、`/hs-codes` → 原 load/reset/save/query|维护与本地步骤|模块工作区；包装选择、单位换算和编码筛选不新增标签|表单、selected SKU、排序、URL 查询|既有参数/包装/交易单位回归|
|`/`、`/finance` → 概览下钻链接|导航到带筛选列表或对象|跨模块任务为标签，目标列表保留其 URL 业务筛选，原来源工作区不销毁|概览期间、返回上下文|原下钻和报表权限回归|
|`/reports` → 图表设置、共享报表、ReportDetailPanel 下钻、导出|局部图表与分页明细、CSV|图表及明细仍为当前任务/子窗体；图表布局偏好按账号隔离|图表定义、明细选择/分页、期间|报表、导出及权限原回归|
|`/receivables`、`/payables` → `openEdit`/`savePlan`、`openSettle`/`settle`、`contractLocation`|调整计划/收付款窗体，合同跳转|前两项短操作保留窗体，并注册独立未保存 guard；合同对象为标签|期间、筛选、原币输入、日期、备注|计划保护、原财务回归、关联合同|
|`/transactions` → `openForm`/`save`、冲销与分配|财务编辑、结果未知保护|当前工作区内短操作，保持唯一流水号与结果未知提示|完整输入只在内存，原请求身份不因标签切换重建|财务、冲销、重复点击与传输失败回归|
|`/rmb-cash-events` → `openCreate`/预检/确认/凭证|银行事实分步办理，曾写 localStorage 草稿|当前任务步骤，工作区只持久化请求标识，不保存完整财务表单；保留金额、凭证及审核规则|内存表单、凭证 File、分步预检|原银行事实回归；刷新只保护不承诺恢复|
|`/finance-ledger` → `run`/各登记表单/`submit`/`instructionAction`/`upload`/`downloadCsv`|账户、登记、复核、文件与期间|工作区内分步维护；各表单独立 guard，保存只清理相应表单 baseline；请求标识键隔离|内存财务表单、请求标识（不含完整正文）|账户资金原回归与未保存保护|
|`/historical-orders`、`/history-takeover` → 原筛选/申请/预检/明细/导出|历史资料任务步骤|独立模块工作区；预检、分组、执行确认仍在当前任务，不扩大历史导入授权|查询、当前申请/分组、临时输入|历史功能及失败原子性既有回归|
|`/import` → `loadTemplates`/预览/execute/下载|文件选择、预览、导入确认|当前模块工作区；不会把文件预览、执行变成新标签；写入忙状态阻止关闭|File、预览、重试批次 ID|原导入真实文件与导出回归|
|`/organization` → `selectRole`/`save`/`resetDraft`|组织与权限维护|原任务内角色选择与确认，不修改认证或权限策略|角色 draft、模块搜索、原 guard|原权限专项；开发身份保持原服务端入口|
|`/access-denied`、`/access-status-error`|权限拒绝/状态页|继续原路由与原判定；新工作区先鉴权后挂载，401 清理旧工作区|无旧身份业务缓存|身份边界专项|

资源/共享状态盘点：页面实例内 refs 保留在所属工作区，内存 router 隔离 useRoute 与 beforeEach；dialogs 队列仍是全局短确认，不存储业务草稿；accessState 仍由身份包拥有。源码未发现 setInterval 轮询。CategoryPathFilter 与 SKU 的 document 监听失活时解绑；全局 AppDialogHost 与 main 的站点监听保持单例。请求 retry 只用于只读请求；关闭中止绑定请求，身份 epoch 拒绝旧响应。文件下载及预览保持原清理流程，不进入延期打印和分页修复。

Git 观察：`worktree-observation.json` 枚举143个工作树，最终均完成只读状态检查；`branch-conflict-observation.json` 对相关近期分支固定 HEAD 比较基线，含共享导航/请求/权限差异。全局 safe.directory 未修改；只为每条只读 git 命令提供对应路径。未切换、清理、重置或写入其他工作树。此记录只证明所列固定时点，移动 HEAD 之后的差异另需集成时核对。
