# P6 验收记录

共同起点为 `3048697fdba660390fe9361fa12ac8517a170fb1`，包含取回的 SJERP 远端 U4 `1dff4f7219f5e440ea9bc086a9a7af36a49379fa`。从 U4 固定提交 `310035884dd9b785b4ff2df37618fd4056257d2a` 接收原测试及运行产物。SJERP 远端 U4 已核对更新到该提交。P6 修复源码为 `6575b350e5dec312dbf9fc5211b6d8ac3bf00a94`。

| 编号 | 已有证据 | 待核销 |
| --- | --- | --- |
| SKU-01 | U4 在六组用原生 Chrome 触发列表错误，移除拦截后重试得到真实成功响应。Enter 打开新建，选择产品，继续编辑后选值保留，放弃后编辑器关闭。 | Tab 到达行和行内按钮、现有记录编辑和保存回读、放弃后 API 无写入、原筛选与工作区隔离。 |
| PKG-01 | U4 在六组用原生 Chrome 触发列表错误并重试成功。Enter 打开新建，继续编辑后保留模板名称，放弃后编辑器关闭。 | Tab 到达关键操作、数量和单位与箱规读回、放弃后 API 无写入及重新打开。 |
| INV-01 | U4 在六组检查采购入库来源、四个可见标签、滚动、关闭回筛选列表及重新打开核对批次。 | 关联子详情返回、其他来源组合、逐路数量与方向、只读与原有冲销入口。 |

[SKU 和包装原始运行记录](chrome-u4-editor-guards/run.json)覆盖 1366×768、1440×900、390×844 各原生 100% 和 125%。[采购入库记录](../ui-delivery-closeout-04/inventory-matrix/chrome-purchase-receipt-combinations/run.json)的源码为 `46738366350c5f494e3fa62b2b209385fb8f340b`，证据提交为 `29cfaf7b8c54da900178a007af9aec5139a2e34b`。

## SKU 局部修复

源码检查发现，聚焦 SKU 行内按钮按 Enter 时，按键会冒泡到整行的详情处理。SKU 页面使用 `@keydown.enter.self`，仅在行自身收到 Enter 时执行整行详情操作。新增独立模板回归，浏览器交互仍需验收。

## 测试与公共矩阵接线

- 在仓库根目录运行 `node --test frontend/src/views/SKUPage.test.js frontend/src/views/ProductStateCloseout06.test.js`。9 个既有用例与 1 个新增断言通过。
- 在 frontend 使用已有隔离 runner 执行 `node scripts/run-isolated-browser-tests.mjs --business-test ui-u4-editor-guards.spec.js`。从本机忽略文件加载验收凭据并启用 `ISOLATED_CODEX_TEST_SUPERADMIN=1`。将 `ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT` 指向 `docs/uat-evidence` 内本次运行的绝对路径。首次本地调用未设置该变量，隔离环境和登录均通过，测试在写证据前退出。该专项目标使用独立数据库、媒体和 Chrome 配置，普通矩阵调用会跳过此文件。
- U4 接线时保留上述隔离入口，将运行 JSON 和截图归档到 P6。库存关联详情另需隔离专项，逐路径保留打开前后的流水 ID、标签、筛选、滚动位置和焦点。待实际复现后再给 U4 定位公共组件和最小修复要求。

库存联查从 `EntityDetailModal.vue` 的 `inventory-movements` 入口定位。当前直接关联映射包含 SKU、产品和订单，实际展示取决于流水数据。复现时分别断言关闭子详情回到原流水及选中标签，再关闭根详情回到原筛选和滚动位置。若出现复位，U4 在公共弹窗的关系返回栈和列表触发点之间定位，并在有该关联的真实合成记录上复测。当前没有浏览器结果可据以认定公共缺陷。

P6 重跑退出码为 0，Playwright 1 项通过，包含 SKU 和包装各 6 组。Chrome 156.0.8078.80。隔离运行结束后已释放本次端口和临时库。重跑范围为继承的编辑器路径，未操作 SKU 行内按钮。[P6 重跑记录](rerun/chrome-u4-editor-guards/run.json)
