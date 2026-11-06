# 验证记录

产品提交 `aa8ba801f02e051f694a4c4d9df5b8fb82ca4678`，前端源码树 `8c9d1405e909ffbc66f0670df5c38637bc8295b9`。

## 自动回归

|检查|结果|环境|
|---|---|---|
|Django 全量|发现 1,443 项，执行 1,358 项通过，85 项跳过|SQLite 内存库，Python 3.14、Django 6.0.6，本机 Git OpenSSL|
|Vitest 组件回归|79 个文件，737 项通过|jsdom，单 worker，列表返回与接续修复另有专项覆盖|
|详情抽屉排版专项|1 项通过|使用 Node 原生运行器单独执行既有 typography 用例|
|Node 全量|180 项通过|包括工作树隔离、基础运行器和导航静态回归|
|生产构建|通过|Vite 仍提示个别产物大于 500 kB|

后端验证命令为 `DATABASE_URL=sqlite:///:memory: python manage.py test --noinput`，通过 `OPS_TEST_OPENSSL` 指定已安装的 OpenSSL。后端树为 `90db6a881d3627c90ece8262d0f7458a18be648b`。首次未指定 OpenSSL 的运行有两项测试类初始化错误；配置后重跑通过。未做 PostgreSQL 或锁定 Python/Django 组合的额外运行。

Vitest 命令为 `node node_modules/vitest/vitest.mjs run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --pool=threads --maxWorkers=1`。既有单 RouterView 路由测试以独立页面挂载验证原流程；真实 App 的内部标签由工作区专项验证。Node 命令为 `node --test --test-concurrency=1`。截图由真实 Chrome 运行生成，并逐项目视检查桌面与 390px。

## Chrome 与真实 API

使用运行器新建带标记的临时 SQLite 和 MEDIA_ROOT，检查 API、Vite 及代理的运行标记，导入合成数据。验收后回收本次的进程、端口和数据目录。重跑共享手工库时出现合成客户名称冲突，正式数据采用全新库记录。

|场景|结果与证据|
|---|---|
|客户与订单、采购单并行|同一窗口内多个模块/对象，客户复点去重。[桌面对象](chrome/desktop-parallel-objects.png) · [390px 直接链接](chrome/mobile-order-link.png)|
|两份同 URL 新建草稿|输入独立，切换和浏览器前进/后退恢复对应草稿。验证关闭取消、关闭其他、关闭右侧及移动标签。[桌面](chrome/desktop-drafts.png) · [390px](chrome/mobile-drafts.png)|
|保存与编辑冲突|真实客户创建返回 HTTP 201，草稿标签接续为客户。另一标签提示数据更新，取消继续保存时 0 次 PUT，输入保留。[冲突界面](chrome/desktop-conflict-preserved.png)|
|列表与任务上下文|真实 API 合成 55 个客户后翻到第二页，搜索、页码、列表和任务滚动保留。[列表](chrome/desktop-list-page-scroll-restored.png)|
|会话与刷新|Chrome 原生刷新确认可取消并保留草稿。模拟同名、不同 ID 的账号切换后旧工作区销毁；权限 401 和旧响应隔离另有测试。[边界记录](chrome/identity-boundary.json)|
|负载与回收|共 12 个标签，切换 10 次增加 0 个 API 请求，合计 0 次写入。批关 11 个后回到 1 个标签、128 个 Vue 实例和 12 个 window/document 注册。[资源原始记录](chrome/resources.json)|
|资金与业务原回归|真实银行手续费 3 项通过，含 1440px、390px 和真实 API 的原有来源限制/幂等断言。资金 UI 模拟 API 8 项通过。|
|报表与 CRM 原回归|报表模拟 API 16 项、CRM 模拟 API 8 项、组织权限模拟 API 16 项分别通过。保留原 CSV、报价/订单以及一次写入、失败保留和读回断言。|
|采购、库存与证书原回归|真实采购草稿、下单与历史付款计划 1 项通过，库存模拟 API 9 项通过，SKU/库存/产品返回专项 6 项通过，证书与 CRM 提交保护 9 项通过。|

真实 Chrome 使用 Playwright。桌面截图人工检查了工作区与工作台两层标签、草稿标识及保存/取消的可达性，390px 检查了窄屏横向标签、订单操作和页面宽度。另行尝试通过 Codex 连接 Chrome 手动操作时连接超时。证据来自真实 Chrome 脚本和截图检查。

权限/身份方面，真实 Django 的身份接口测试覆盖稳定服务端 ID 与匿名开发身份。浏览器账号变更用合成身份触发；实际员工登录、退出、凭证更新应随身份包联合验收。当前界面未提供可操作的正式退出按钮，集成入口为 `confirmExit()`。浏览器崩溃恢复不在验收范围；退出或刷新前的拦截依赖浏览器支持和此前页面交互。

## 既有业务浏览器回归

运行 `node docs/uat-evidence/internal-workspace-tabs-20261105/run-browser-regression.mjs`。延期打印输出与字体故障两个用例按工作包范围排除，既有报价与文件导出用例仍运行。未运行 GitHub Actions。

下列运行记录按阶段更新。既有业务全组测试与修补后的定向复测分别统计。
