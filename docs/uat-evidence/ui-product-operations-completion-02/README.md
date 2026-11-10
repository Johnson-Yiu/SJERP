# E2-R2 产品运营界面

## 产品详情修复

被测基线为 `43067137d0fba04b0be055e449e55a06dba6d208`。在产品列表打开合成长名称产品 EVID-P001，检查抽屉左缘、产品名称及左侧信息卡。桌面四组中，抽屉左缘均为 24 CSS px，可用工作区起点为 248 CSS px。窄屏 100% 进入关联证书后，关闭按钮没有获得焦点。原始 390×844、125% 的失败记录还捕获了过渡中位置，单凭该记录无法认定窄屏有稳态溢出。[原始失败记录和截图](chrome-baseline/failure.md)

产品抽屉和嵌套证书抽屉按所属工作区的实际宽度布局。产品长名称换行。进入嵌套证书时，焦点移至关闭按钮，父产品工作区仍显示产品名称。按 Esc 返回触发按钮，再按 Esc 关闭父抽屉并返回列表。修复集中在 `frontend/src/components/EntityDetailModal.vue` 和 `frontend/src/views/ProductPage.vue` 的产品抽屉分支。原有共享样式表未编辑。

最终被测产品源码为 `df1a32e0a2631fb14ce5e370ef4c9b14444a0de8`。通过六组 Chrome 矩阵，覆盖 1366×768、1440×900、390×844 和原生 100%／125%。桌面左缘为 272 CSS px，可用区起点为 248 CSS px。390×844、125% 下嵌套证书顶边与父抽屉顶边均为 130 CSS px。验证名称完整可见、信息卡和标签可达、内容区可滚动、关闭按钮可达、返回和键盘焦点恢复。浏览器为 Google Chrome 156.0.8078.80，使用独立持久上下文修改 Chrome 外观设置的原生缩放，并在页面读回 DPR。数据来自真实隔离 Django、独立 SQLite 和媒体目录，以测试库 codex 账号登录。截图绑定各次产品源码 SHA。[中间修复记录](chrome-product-detail/run.json) · [最终记录和截图](chrome-final/run.json)

## 自动化检查

| 检查 | 结果 |
| --- | --- |
| 产品、SKU、采购、库存、销售与采购文案定向 Vitest | 首次修复源码 14 文件 145 条通过 |
| 最终产品源码定向 Vitest | 4 文件 13 条通过，覆盖产品工作区、产品主档、库存导航及关联报价入口 |
| 最终产品源码定向 Node | 16 条通过，覆盖 ResourcePage、HistoryOrdersPage 和详情抽屉排版 |
| 隔离 SQLite 定向 Django | 69 条通过，覆盖产品与分类、SKU 身份及动态组合、SKU 图片、供应绑定、交易单位、采购关联和库存冲销 |
| GitHub Actions | NOT_RUN |
| 最终候选全量 SQLite、PostgreSQL 17、Node/Vitest、构建与通用浏览器 | A3 负责 |

详见[剩余状态与既有证据](gaps.md)。

## 隔离重跑

设置本机 `ISOLATED_TEST_PYTHON`、`ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT` 以及 Git 忽略的 codex 测试凭据。安装锁定的前端依赖后，在仓库根目录运行。记录目录应指向本包内独立的运行目录，防止覆盖原始截图。脚本会保留已采集的证据，并在必验断言失败时以失败退出。

```powershell
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-completion-02.spec.js
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-prefix-02.spec.js
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-parameter-02.spec.js
```

本包源码的 Vite 生产构建通过。Vite 报告原有大包体积警告。
