# CORE-WORKSPACE-UX-BATCH-01：前端修复与隔离验收

固定基线 4388947d70d26bca66ca0bfc76b2383a2fc0d404，专属分支 codex/core-workspace-ux-batch-20261104。打印工作树独立封存，不迁入未封版打印测试。公共台账不修改。

| 页面/场景 | 已有成果复用 | 本轮检查 |
| --- | --- | --- |
| 客户、联系人 | ISS-008/025/080 身份/状态/重复规则 | 筛选分页、对象切换、保存/取消/错误、关系返回 |
| 跟进 | ISS-009/027 日期规则及客户同步 | 清空/重试、最新反馈、迟到响应 |
| 产品/SKU | ISS-028/035 分类/schema、历史单位与包装 | 长型号、分类筛选、表单、详情及图片入口 |
| 销售订单 | 既有履约、财务权限、关联导航 | 返回上下文、保存、状态及并发点击反馈 |
| 采购订单 | ISS-022/024/039/075 与既有回归 | 已复现收货成功残留旧错误、提交中可关闭对话 |
| 库存 | ISS-006/013/014/015 历史修复 | 列表与详情请求、错误/空态、来源和预留导航 |

所有实现限局部前端；不改业务模型/迁移/API/金额/库存规则/状态机/权限/依赖/CI。mock 组件回归与真实隔离后端/内置浏览器证据分开。使用现有隔离运行器、临时 SQLite/媒体和合成资料；开发身份不伪装真实认证审计人。受限权限使用已有组件测试，不启用正式 RBAC。

新发现问题（来源日期 2026-11-04）：采购收货失败重试成功后旧错误仍显示（建议 P2）；请求提交中取消/遮罩关闭易误导用户操作已取消（建议 P2）。独立复现测试两项失败保留 logs/purchase-before.log。最小修复清空最新反馈并限制提交中的取消/遮罩关闭；不改原请求及幂等键。

各业务子报告、原始日志、真实 HTTP 和桌面/390px截图将在本目录补齐；Codex 自查不等同 ChatGPT 独立复审，不关闭 Issue。

## 已实施 / 待独立复审

交叉动作补验：在阶段66869e0后进一步复现“旧收货错误进入新采购草稿”和“冲销提交期间取消仍可用”，独立四项测试中2失败/2通过（logs/purchase-cross-action-before.log）。最小追加仅清空新草稿旧错误、冲销提交时禁用取消/遮罩关闭；不改变冲销原因、请求、限制或幂等协议。补修后与既有收货编辑测试合跑24/24通过（purchase-cross-action-after.log），再次生产构建通过（build-closeout.log）。真实IAB既有收货/冲销成功、取消及新建入口证据保留；可控pending/拒绝交错以组件证据为准，不伪称人工限速或正式网络故障验收。下文711项全量与177项Node是追加前阶段结果，最终追加后的完整测试以最终CI同SHA为准，不混用SHA。

追加后最终本地结果：有效Vitest同命令重跑75文件/713项通过，162.49秒、退出0，无前次worker退出超时警告（logs/vitest-closeout-all.log）；Node全量177/177通过（node-closeout-all.log）；构建再次通过（build-closeout.log）。旧711项结果及全部失败/警告日志继续保留，不改写历史。完整文件清单见file-list.txt。最终CI结果继续以最终SHA运行链接核实。

| 子任务 | 结果与最小修复 | 可复核依据 |
| --- | --- | --- |
| 客户、联系人 | 客户旧列表响应和空结果辅助查询不再覆盖当前筛选；取消新建后迟到编号/选项不污染编辑对象 | [客户/跟进](customer-followup.md)，修复前8项失败、修复后35项定向通过；真实客户备注保存重开，联系人修改及窄屏创建 |
| 跟进、待办 | 迟到新建跟进人/附件初始化不覆盖当前编辑资料；日期算法不改 | 同上；真实设置2026-11-10、保存、清除后列表及客户当前日期均同步 |
| 产品、SKU | 产品空结果探测请求的版本保护；SKU供货来源晚到结果/错误失效 | [产品/SKU](products-skus.md)，修复前4失败/1通过；修复后33项定向通过 |
| 销售订单 | 订单列表成功/失败/finally只发布当前请求；保存中禁止取消/离开；关闭后忽略迟到来源报价错误 | [销售订单](sales-orders.md)，修复前5项失败、修复后60项定向和17项Node通过；实际订单→采购→返回原fulfillment页签 |
| 采购订单 | 收货开始/重试清除旧反馈；提交中取消及遮罩关闭禁止；既有重复提交防护及原幂等键保持 | logs/purchase-before.log 两项失败；purchase-rerun.log 30项通过；真实窄屏部分收货→冲销→重开及HTTP400/数据库不变 |
| 库存、履约 | 刷新/切换SKU/离页使旧详情失效；阻止防抖及排队路由跳回旧页；保留服务端权限拒绝原因 | [库存](inventory.md)，29项组件和2项Node通过；真实0库存/0预留/10在途及来源导航 |
| 布局、文案 | 确认SKU手机编辑框被晚出现的平板双列规则压窄，追加仅≤520px、仅编辑表单的scoped单列覆盖 | 修复前 screenshots/sku-editor-390.jpg；修复后 screenshots/final-IAB/sku-editor-fixed-390.jpg、sku-editor-actions-390.jpg；不改桌面/新建布局 |
| 历史待复审证据 | 保留原ISS-006/009/013/014/015/025/027/028/035等已有证据，本轮局部补证，不代替独立审查 | 未改公共台账、Issue状态或46项规则 |

以上发现来源均为2026-11-04固定基线代码核对、独立复现或本轮IAB，建议优先级P2。公共Issue ID由集成对话统一分配。未发现的业务规则缺陷不作猜测性改造。

## 真实环境、HTTP与视觉证据

复用现有 `npm run test:browser:isolated -- --business-test core-workspace-fixture.spec.js`。新spec只用Playwright request/合成夹具，不启动本地浏览器；`CORE_WORKSPACE_IAB=1`明确进入有时限人工IAB协作窗口，默认CI不等待。运行器验证独立DB/媒体、迁移、直连与Vite代理身份，结束仅清理自身资源。未修改隔离基础设施。

首轮有效数据CEF48C3E、端口14335的 `real-api-fixture.json`/`real-api-after.json` 保存真实响应及业务表前后核对：客户备注、联系人电话、唯一新增联系人、跟进日期清除均落库；采购2件收货后冲销，收货历史保留、库存流水两条、采购恢复ordered。非法零数量POST收货返回400，查询的八张业务表前后逐字段相同。开发身份沿用现有机制，`AUDIT_LOG_ENABLED=0`，不宣称真实认证审计或正式RBAC验收。订单夹具含明确“历史主体未记录”兼容样本，不将当前主档伪充历史。

初次IAB使用本机既有Python3.14/Django6.0.6；核对后发现与基线锁文件有差异，故建立本工作树独立.venv按全部16项精确锁安装、pip check通过，后续锁定环境补验单独保存，不将不同环境混称。前端从package-lock执行npm ci，227包，无依赖或锁文件变更。CI使用工作流既有Python3.12和锁文件。

锁定补验B51443F5：本包.venv Python3.14.5 / Django6.0.9、全部16项实际版本与requirements.lock逐项相同（locked-python-versions.json），隔离端口7101。IAB实际客户保存、390px联系人唯一创建/取消、2件收货/冲销、库存及SKU手机表单已补做，截图screenshots/locked-IAB/；真实HTTP400拒绝及数据库前后完全一致再次通过，结果real-api-after-B51443F5.json和logs/locked-api-readback.log。日期设置/清除的完整人工操作仍以首轮CEF48C3E证据为准，不把新夹具初始空日期冒充重新清除操作。锁定运行完成后运行器自行清理专属数据库/媒体与端口。

归档自查补充：浏览器截图辅助函数保留早先目录闭包，因此锁定补验原件实际先写入final-IAB；其viewports.json按URL7101清楚标出该批来源。现将这六张原始字节副本及筛选出的实际视口清单另存locked-IAB，未重拍或修改像素。客户保存图实际为恢复默认视口后的1304×892，副本据实命名customer-saved-1304.jpg，不把原误名1440作为尺寸证据；1440桌面客户证据仍使用首轮实际1440×1000原图。

截图本地视觉结论以真实IAB的JPG为准。1440×1000及390×844入口已操作客户、联系人、跟进、产品/SKU、订单、采购和库存，表格/页签按现有横向滚动浏览。初次视口切换瞬间截图的误名/尺寸不作为通过证据，原文件保留；桌面库存、桌面SKU、窄屏产品及SKU修复后另存 `screenshots/final-IAB/`，每张抓取时的innerWidth/height、clientWidth和pageWidth见viewports.json。390视口存在15px滚动条时clientWidth375，不误称375为390。另有代理早先中止的mock Chrome PNG，明确不用于本轮真实后端IAB结论，启动事实和限制见products-skus.md。

图片/SKU历史版本、第三方仓批次的全部业务组合、真实员工鉴权及真实业务数据均未在本轮穷尽；组件权限测试只证明界面边界，不扩大为服务端正式RBAC验收。快速切对象/迟到响应/网络失败/重复提交由可控Promise组件回归覆盖，与真实后端操作分开。

## 本地测试命令与结果

命令在frontend执行，全部原始日志保留logs/及各子报告目录。

| 检查 | 命令 | 实际结果 |
| --- | --- | --- |
| 锁定前端安装 | npm ci --ignore-scripts --no-audit --no-fund | 成功，227包；不升级依赖 |
| 全量Node最终重跑 | npm run test:unit | 177/177通过，无跳过（node-final.log） |
| 隔离运行器独立复跑 | node --test infrastructure-tests/runner-validation.test.mjs | 17/17通过，两个工作树真正并发且DB/端口/媒体分离（runner-alone.log） |
| 有效Vitest全量 | node node_modules/vitest/vitest.mjs run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers=2 | 75文件/711项通过，退出0；保留follow-up-safety worker退出超时警告（vitest-direct-all.log） |
| 上述Node专属测试 | node --test src/views/TaskK1Pagination.test.js tests/detail-drawer-typography.spec.js | 2/2通过；排除项已以其正确Node运行器执行，并非删除或跳过 |
| 最终六组补修组件 | vitest run tests/core-workspace-purchase-feedback.spec.js tests/customer-followup-races.spec.js tests/inventory-async-ux.spec.js tests/product-workspace-batch-races.spec.js tests/sku-workspace-batch-races.spec.js tests/sales-orders-async.spec.js --environment jsdom --maxWorkers=1 | 6文件/30项通过（all-fixes-targeted.log） |
| 最终生产构建 | npm run build | 通过；保留既有大包警告（build-final.log） |
| 真实隔离API及IAB协作 | npm run test:browser:isolated -- --business-test core-workspace-fixture.spec.js | 首次有效及补录运行各1项通过，协作时长不当作自动化执行速度（real-isolated-third.log、visual-final-run.log） |

失败历史不删除：首轮fixture付款阶段误用name键，被现有规则拒绝并回滚，纠正为label/due_basis/offset_days；一次并发启动API身份超时；Node早期运行器120秒超时，后续单独17/17和全量177/177通过；TaskK1源码直接赋值字符串断言改为验证“all-pages读取→当前请求检查→赋值”，保留分页覆盖，不回退安全实现。错误Vitest命令（缺jsdom/未限定tests目录）未计入有效全量；终止无效运行的记录保留，不修改全局测试配置或放宽断言。

## 集成与剩余范围

只修改六个页面、分页源码契约测试及独立回归；无业务后端/模型/迁移/API/金额/状态机/权限/依赖/CI变化。ResourcePage改动限customer/contact/followup分支；DocumentPage订单保护只作用于订单，报价保存/打印不改；SKU CSS仅手机编辑表单。合入须按局部diff处理，不能整文件覆盖其他包的共享ResourcePage/DocumentPage/SKUPage新修改。

最终交付精确SHA及同一SHA的Backend、Backend PostgreSQL、Frontend实际结果以本分支GitHub记录和交付回复为准；未完成CI不记PASS。打印封存来源b3d0d386de70d9efd77bf62cdbd87877fbccbfb8在另一个工作树，完整打印与分页用户延期，不纳入本包。不合并master、不部署、不关闭Issue。完成后等待ChatGPT集中独立复审。
