# R0-F9-VIS-01 全站视觉审查问题修复与补充截图

日期：2026-10-17。起点及实际运行代码：[9d05a70c07d1d8eb9d080dd1d75ea608209a799b](https://github.com/Johnson-Yiu/SUNJACK-ERP/commit/9d05a70c07d1d8eb9d080dd1d75ea608209a799b)。仅新增回归测试、采集校验及文档；没有修改 frontend/src、backend、业务数据定义、权限或页面样式。使用独立合成数据库 r0f9-vis01.sqlite3（从旧隔离样本复制），没有操作主工作区数据。

## 结论与验收边界

旧573张JPEG逐张复核原字节SHA-256和真实尺寸，全部仍与旧manifest一致，未覆盖历史原图。新目录归档368张原始JPEG及对应文本（其中初始诊断图的文本明确为说明而非DOM快照）。最终27路由×3视口=81张完成态基线，全部有稳定DOM、连续原始帧哈希观察；63张实际尺寸通过，18张仍为BLOCKED_EXACT_DIMENSIONS。**没有达到全站精确尺寸全部验收通过；不宣称ChatGPT独立视觉PASS。**

ISS-099两种实际入口均未复现空白取消误报，仍为NEEDS_VERIFICATION。ISS-100转为BLOCKED，记录可复现的截图接口尺寸限制。ISS-101/102修正证据采集流程后待独立复审；ISS-103为既有订单详情Vue过渡警告，待核实。未发现本轮新引入的P0/P1问题。此次没有为未证实的SKU原因修改统一dirty/busy保护。

## 原因与处置

### 加载中的最终图片（ISS-101，E类）

旧流程没有以业务请求、DOM和原图共同判定完成，部分截图仍为加载画面。新检查还复现：DOM已完成后，截图接口可能暂时返回旧的加载帧。因此不能以固定等待1秒、networkidle或单次DOM稳定独立判定成功。

本轮逐页等待请求完成/可见加载状态消失，比较连续DOM，轮询未经修改的JPEG原始字节，要求连续帧哈希稳定，再归档并复核原图。诊断过程均保留，但index默认只显示最终81张。产品详情、报价进入订单、库存、交易单位、组织页等待后均能完成，没有查到这些页面持续加载的程序缺陷。HTTP成功记录见real-api-http.log；不为证据采集过早而改写业务组件。

用户点名12张旧加载图片全部有逐项前后对照：[loading-comparison-12.json](uat-evidence/r0-f9-vis-01/loading-comparison-12.json)。其中交易单位/组织原图已显示完成数据，但精确像素仍BLOCKED，不混淆两种结论。

### 69张尺寸异常与跨视口重复（ISS-100/102，E类）

[dimension-exceptions-69.json](uat-evidence/r0-f9-vis-01/dimension-exceptions-69.json)逐项列出全部69张旧图、请求、实际尺寸、原SHA、新图对应及处置；历史操作状态不能仅凭当前等价页面重拍自动认定重验。旧最终81张中17张不符；新最终81张中18张不符，当前布局/记录状态变化可能改变滚动条，不能用减少异常数量作为成功标准。

确认两类采集问题：

1. 视口设置返回后DOM可已变更，但首次截图仍为上一视口；本轮产品详情诊断复现DOM1440而图为1024，随后重新观察得到1440原图。新流程按实际JPEG尺寸和哈希校验，避免旧帧直接归档为最终结果。
2. 浏览器级视口设置作用于当前标签；打开索引标签后，目标业务标签仍可能保留旧视口。新诊断保留错误请求与真实DOM，不冒充成功。最终81张均断言采集前后innerWidth等于请求宽度。

对于整页滚动的页面，稳定观察到innerWidth=1440、clientWidth=1425、DPR=1，接口原图为1425×990；1280对应1265×988，1024对应1009×985。返回宽度匹配clientWidth，高度近似按该宽度比例变化；这是对截图接口内容区域处理的推断，尚无内部实现证据。多次受支持原图采集仍不符，故保留技术BLOCKED。没有拉伸、补边、裁切、重编码，也没有为截图隐藏页面滚动条或修改UI。

旧chrome/skus-settled-1440.jpg与1024原图SHA相同已核实。新Chrome三视口原图实际为1440×1000、1280×1000、1024×1000，跨视口SHA不同；新1440重复观察的同视口SHA一致。旧样本缺少捕获内部轨迹，不能反推唯一历史成因；新复现支持视口/截图帧竞态，归档错误/复用不能仅凭旧文件排除。详见chrome目录和manifest。

### ISS-099空白新建SKU取消

实际Codex内置浏览器与真实Chrome分别测试SKU列表“新建SKU”、产品1详情→SKU管理→新增SKU组合，完全未输入后取消：编辑窗关闭、未保存确认数为0。再次打开后主动修改描述，取消显示“未保存修改”，输入仍在；无持久化写入。两种入口本轮未复现旧误报，因此保留NEEDS_VERIFICATION，不写成修复通过。

新增4项可控回归（独立入口/内嵌入口2项、异步默认值1项、参数缩写1项）：初始化请求未完成时表单尚未开放，完成后无修改可关闭；真实修改和参数自动缩写后的真实参数输入仍受到保护。原有保存中禁止关闭/路由离开、重复提交、失败输入保留均通过。没有调整共享守卫、清除真实dirty状态或削弱保存中保护。异步请求前后的细节以Vitest可控时序为证；不能冒称真实浏览器已观察到所有毫秒级竞争窗口。

## 27路由覆盖矩阵

表中的“尺寸通过”仅代表原图物理像素和请求一致，独立视觉仍待审。所有路由正常数据页面已重拍；代表表单/详情亦提供三种请求宽度，特殊页面以自身筛选、图表、文件输入或状态卡为代表。不是每个路由都具有列表、新建、详情三种业务能力。

|路由|1440×1000请求|1280×1000请求|1024×1000请求|代表状态|
|---|---|---|---|---|
| `/` | [1425×990 BLOCKED](uat-evidence/r0-f9-vis-01/overview/final-page-1440.jpg) | [1265×988 BLOCKED](uat-evidence/r0-f9-vis-01/overview/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/overview/final-page-1024.jpg) | 本页筛选/图表/状态控件；无独立新建弹窗 |
| `/reports` | [1425×990 BLOCKED](uat-evidence/r0-f9-vis-01/reports/final-page-1440.jpg) | [1265×988 BLOCKED](uat-evidence/r0-f9-vis-01/reports/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/reports/final-page-1024.jpg) | 本页筛选/图表/状态控件；无独立新建弹窗 |
| `/customers` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/customers/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/customers/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/customers/final-page-1024.jpg) | complete-detail |
| `/suppliers` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/suppliers/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/suppliers/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/suppliers/final-page-1024.jpg) | complete-detail |
| `/contacts` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/contacts/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/contacts/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/contacts/final-page-1024.jpg) | complete-detail |
| `/follow-ups` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/follow-ups/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/follow-ups/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/follow-ups/final-page-1024.jpg) | complete-form |
| `/products` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/products/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/products/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/products/final-page-1024.jpg) | complete-detail |
| `/categories` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/categories/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/categories/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/categories/final-page-1024.jpg) | complete-form |
| `/product-parameters` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/product-parameters/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/product-parameters/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/product-parameters/final-page-1024.jpg) | complete-form |
| `/skus` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/skus/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/skus/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/skus/final-page-1024.jpg) | blank-cancel-complete、complete-detail、complete-form |
| `/sku-packaging` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/sku-packaging/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/sku-packaging/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/sku-packaging/final-page-1024.jpg) | complete-form |
| `/sku-trade-units` | [1425×990 BLOCKED](uat-evidence/r0-f9-vis-01/sku-trade-units/final-ready-page-1440.jpg) | [1265×988 BLOCKED](uat-evidence/r0-f9-vis-01/sku-trade-units/final-ready-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/sku-trade-units/final-ready-page-1024.jpg) | complete-form |
| `/product-certificates` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/product-certificates/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/product-certificates/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/product-certificates/final-page-1024.jpg) | complete-detail |
| `/hs-codes` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/hs-codes/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/hs-codes/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/hs-codes/final-page-1024.jpg) | complete-form |
| `/inventory` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/inventory/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/inventory/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/inventory/final-page-1024.jpg) | complete-detail |
| `/inventory-movements` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/inventory-movements/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/inventory-movements/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/inventory-movements/final-page-1024.jpg) | complete-detail |
| `/quotes` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/quotes/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/quotes/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/quotes/final-page-1024.jpg) | complete-detail |
| `/orders` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/orders/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/orders/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/orders/final-page-1024.jpg) | complete-detail、from-quote-complete |
| `/purchase-orders` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/purchase-orders/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/purchase-orders/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/purchase-orders/final-page-1024.jpg) | complete-detail |
| `/finance` | [1425×990 BLOCKED](uat-evidence/r0-f9-vis-01/finance/final-page-1440.jpg) | [1265×988 BLOCKED](uat-evidence/r0-f9-vis-01/finance/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/finance/final-page-1024.jpg) | 本页筛选/图表/状态控件；无独立新建弹窗 |
| `/receivables` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/receivables/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/receivables/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/receivables/final-page-1024.jpg) | complete-form |
| `/payables` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/payables/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/payables/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/payables/final-page-1024.jpg) | complete-form |
| `/transactions` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/transactions/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/transactions/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/transactions/final-page-1024.jpg) | complete-form |
| `/import` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/import/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/import/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/import/final-page-1024.jpg) | 本页筛选/图表/状态控件；无独立新建弹窗 |
| `/organization` | [1425×990 BLOCKED](uat-evidence/r0-f9-vis-01/organization/final-page-1440.jpg) | [1265×988 BLOCKED](uat-evidence/r0-f9-vis-01/organization/final-page-1280.jpg) | [1009×985 BLOCKED](uat-evidence/r0-f9-vis-01/organization/final-page-1024.jpg) | role-detail |
| `/access-denied` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/access-denied/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/access-denied/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/access-denied/final-page-1024.jpg) | 本页筛选/图表/状态控件；无独立新建弹窗 |
| `/access-status-error` | [1440×1000 尺寸通过](uat-evidence/r0-f9-vis-01/access-status-error/final-page-1440.jpg) | [1280×1000 尺寸通过](uat-evidence/r0-f9-vis-01/access-status-error/final-page-1280.jpg) | [1024×1000 尺寸通过](uat-evidence/r0-f9-vis-01/access-status-error/final-page-1024.jpg) | actual-api-recovered、actual-api-unavailable |

全站总览按三视口浏览，重点原尺寸复核产品/订单详情、库存、交易单位、组织及SKU关闭反馈。长名称和密集表格允许容器内水平滚动；滚动区/页尾内容不在单张1000px视口中完整出现，不代表原图被裁切编辑。窄屏控件布局与状态标签由现有三尺寸Playwright回归佐证。中文文案、正式字段和值保持不变。

## 实际交互、正常及异常反馈

|检查|结果与限制|
|---|---|
|SKU列表→空白新建→取消|内置浏览器/Chrome均关闭，无确认；重新打开/主动修改后确认保留输入|
|产品详情1→SKU管理→空白新增→取消|两浏览器均未误报；产品详情与SKU列表仍可用|
|报价R0F9-Q001→关联订单→查看订单|正确进入订单ID1/R0F9-O001，真实数据完成后重拍三视口；未转单或改变订单状态|
|产品/订单/采购/库存等详情|只读核对合成记录，代表详情原图和DOM一并归档|
|组织权限|切换查看业务员模板；没有编辑保存、启用RBAC、创建员工或调整真实账号权限|
|实际API不可用→恢复|停止仅供本轮使用的8118服务，等到错误完成态（按钮重新可用、错误可见），三视口截图；启动后点击“重新加载权限状态”回到可访问经营概览|
|失败/忙碌/旧请求/返回状态|完整607 Vitest及139 Playwright覆盖；fixture与真实API操作分开记录|

本轮未重新执行旧F9的所有业务写入链、每个路由全部异常类型/全部表单组合，未重建所有历史特定状态截图。页面级错误反馈在自动回归中覆盖，实际停服截图只证明权限状态服务失败与恢复；不能扩展为27个模块所有失败恢复已真人式UAT。其余跨模块链保留F9已覆盖范围和历史Issue，不以本轮只读补证重复宣称业务写入通过。

## 完整自动化

|检查|结果|日志|
|---|---|---|
|Backend|720项通过，跳过10项，退出0|backend-test.log|
|Backend check / migrations|无问题 / No changes detected|命令核对|
|Backend PostgreSQL|必须以交付最终精确HEAD三项CI核验|见交付CI记录|
|Node|121通过|node-test.log|
|抽屉字体专项|1通过|drawer-typography.log|
|Vitest最终完整|607通过，60文件；SKU专项23通过|vitest-final.log / sku-targeted.log|
|Playwright最终完整|139通过，退出0|playwright-unsandboxed.log|
|Frontend Build|成功|build.log|

首轮沙箱Playwright运行到139项后清理不退出，未当作最终成功；在正常本机进程权限下完整重跑取得139 passed和退出0。首次完整Vitest606项后新增参数缩写用例，已完整重跑607项。没有修改共用UI组件；完整回归仍检查已封版模块。

## 问题与历史边界

- ISS-099：P3 / NEEDS_VERIFICATION，本次未复现，等待最小复现证据。
- ISS-100：P2 / BLOCKED，18张最终基线尺寸不满足请求，需截图接口修正或用户明确接受技术限制。
- ISS-101：P2 / FIXED_PENDING_REVIEW，加载完成证据采集流程修正，独立原图复核待审。
- ISS-102：P2 / FIXED_PENDING_REVIEW，跨视口陈旧/重复图防护及新Chrome证据待独立复核。
- ISS-103：P3 / NEEDS_VERIFICATION，既有OrderDetailModal在Transition中多根节点警告。browser-console.json可见；本次订单详情加载完成，未证实数据影响，未擅自扩大修复。

全部103个ID保留：OPEN6、BLOCKED21、NEEDS_VERIFICATION28、FIXED_PENDING_REVIEW40、CLOSED8；优先级P0=0、P1=19、P2=74、P3=7、Enhancement=3。ISS-095/096保留此前已接受代码/覆盖操作范围，ISS-097不变。没有批量关闭历史Issue。A类新UI缺陷未确认；B类ISS-099待核实；C类警告ISS-103待核实；D类财务、文件、正式权限事项按原台账保持；E类本轮101/102处理及100技术BLOCKED。

## 文件、提交与停止条件

- 新原图/DOM、manifest、capture-records、尺寸/加载对照、HTTP/控制台与自动化日志：[r0-f9-vis-01](uat-evidence/r0-f9-vis-01/)。
- 离线人工审查：[index.html](uat-evidence/r0-f9-vis-01/index.html)，默认最终81张，可按模块、视口、页面状态和证据角色筛选；点击原图。
- 完整尺寸/哈希：[SCREENSHOTS.md](uat-evidence/r0-f9-vis-01/SCREENSHOTS.md)、[manifest.json](uat-evidence/r0-f9-vis-01/manifest.json)。
- 运行代码SHA明确为9d05a70c07d1d8eb9d080dd1d75ea608209a799b；交付增加测试与证据，不伪造截图来自尚未存在的提交。最终交付Commit与同SHA的三项CI URL在交付回复及本地final-verification.json中核对，不能用基线CI代替。

完成push master及最终精确HEAD的Backend / Backend PostgreSQL / Frontend三项SUCCESS后停止，等待ChatGPT再次独立代码及证据审查。进入集中修复的条件仍为独立接受、未通过项修复或明确接受限制、用户授权下一阶段。当前18张尺寸BLOCKED、099/103待核实且独立视觉尚待审，不得自行进入历史Issue集中修复、正式RBAC、员工UAT或生产部署。
