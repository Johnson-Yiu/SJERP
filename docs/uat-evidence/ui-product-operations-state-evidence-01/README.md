# 商品、采购与库存界面取证

基线 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`，分支 `codex/ui-product-operations-state-evidence-01`。本包专门记录界面和复现，供独立复审。

- [源码状态清单](states.md)
- [既有证据、适用边界与 A2 差异](existing-evidence.md)
- [问题复现与复审](reproductions.md)
- [仍需补验的状态](gaps.md)
- [Chrome 截图与 HTTP 索引](browser-results.json)
- [Chrome 补验截图与 HTTP 索引](browser-followup.json)
- [定向复验截图与 HTTP 索引](browser-verification.json)
- [产品刷新失败与恢复](browser-product-refresh.json)
- [截图目录](screenshot-index.md)
- [合成数据脚本](seed.py)

## 隔离与重跑

在本包独立 worktree 安装前端锁定依赖。从 Git 忽略的本机配置加载 `ERP_TEST_USERNAME` 和 `ERP_TEST_PASSWORD` 到当前进程，设置 `ISOLATED_CODEX_TEST_SUPERADMIN=1` 和本机适用的 `ISOLATED_TEST_PYTHON`。不要输出凭据。

```powershell
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-state-evidence-01.spec.js
```

运行器为每次尝试单独分配 API／Vite 端口、SQLite、媒体目录及认证文件。本包打开独立 Chrome 配置目录，检查真实会话为 codex 且开发身份关闭，然后访问业务页。首轮长样本种子因同一供应商下空 SKU 编码重复而停止，样本已改用独立编码。该错误属于取证样本。

浏览器脚本通过 Google Chrome 通道开启浏览器，在设置页切换原生 100%／125%，以 DPR 和 CSS 视口宽度复核，使用 Chrome 截图保存实际视口。截图索引逐项记录原始尺寸、CSS 尺寸、文档宽度、API 类型及请求状态。截图是视口观察，不证明视口之外或内部滚动区域的所有控件均可操作。

## 定向自动检查

```powershell
# 在 frontend 下执行
node --test src/views/ProductPage.test.js src/views/SKUPage.test.js src/views/InventoryPage.test.js src/views/PurchaseOrderPage.test.js src/views/ResourcePage.test.js
```

Node 源码回归 35／35 通过。初次误以 Vitest 加载了使用 `node:test` 的文件，已按原生 Node 入口重跑。GitHub Actions 为 `NOT_RUN`，提交带 `[skip ci]`。

定向 Vitest 使用 `--pool threads --maxWorkers 1` 重跑，10 个文件的 108 项全部通过。此前 fork worker 启动超时的整组结果已由此次完整重跑覆盖。

设置 `PRODUCT_OPS_FOLLOWUP=1` 可运行补验组并独立写入索引。该组包含采购、库存、库存流水和包装的 125% 补图，包装新建、供应商详情、产品查询无结果、分类级联、未保存确认、证书校验和附件保存、部分收货及多订单采购成本。证书保存后用真实 HTTP 重新读取文件，逐字节核对上传内容。

`PRODUCT_OPS_FOLLOWUP=verify` 复验子流程。390px／125% 下，真实后端返回证书创建 201、部分收货 201、两张订单成本分配保存 200，并取得相应界面回显。各索引的 `gaps` 记录当次运行的断言缺口。部分早期截图保留了宽度切换过程。

`PRODUCT_OPS_FOLLOWUP=refresh` 单独复验产品列表刷新。在 Google Chrome 156.0.8078.80、390×844、原生 125% 下，拦截产品列表 GET 并持续返回 500。应用在五次自动重试后显示刷新失败和“重新加载”，保留上次加载的产品行。解除拦截后点击“重新加载”，真实隔离后端返回 200，刷新提示消失。[失败截图](screenshots/verification-product-load-failure-390-125.png) · [恢复截图](screenshots/verification-product-load-recovered-390-125.png)

取证运行记录。初轮完成真实 Chrome 空态后遇到合成数据唯一约束。下一轮完成部分 100% 图证，之后达到当时的六分钟用例时限，旧 Chrome 配置目录因锁文件由运行器留存，API 与 Vite 已释放。优化脚本在下一次启动时遇到 Django 身份探针超时，未进入浏览器阶段。各次均使用新隔离库与独立端口。
