# Products / SKUs：2026-11-04

基线 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`，工作树 `core-workspace-ux-batch-20261104`。仅修改 ProductPage.vue、SKUPage.vue 和新增独立测试；未提交。已读 AGENTS、PROJECT_ISSUES、PROJECT_PHASES、REVIEW_PROTOCOL、产品/SKU 最近提交（含 f825546 文案优化、47fcab0 分类修复）及 R0-F7A 历史验收。旧 PASS 不作为本次视觉结论。

## 已证实且已修复，待独立复审

| 问题 | 复现 / 影响 | 最小修复 |
|---|---|---|
| 产品空结果补充请求越过版本保护 | 搜索 A 无结果，等待无筛选产品存在性查询；开始 B 查询；A 补充查询完成后仍写入存在性、参考资料并结束 B 的 loading。成功及失败均可复现。 | 补充查询先保存局部结果，再次核对 loadVersion 后才发布存在性并继续更新页面。 |
| SKU 编辑器供应来源跨记录回填 | 编辑 A，来源请求未完成；取消后编辑 B；A 成功覆盖 B 来源，A 失败设置 B 错误，并提前结束 B 的 loading。可能把错误来源动作暴露在当前编辑器中。 | 供应来源请求独立序号；创建/编辑/关闭/卸载失效旧请求；成功、错误和 finally 均只允许最新请求更新。 |

页面没有新增可见文案；既有 SKU、交易单位、采购等术语及状态值未改。未改后端、模型、API 契约、权限、业务、依赖、CI、全局组件或公共台账。公共台账编号、阶段统计及统一集成由协调任务处理；本文件不关闭旧 Issue。

## 组件回归

新增 `frontend/tests/product-workspace-batch-races.spec.js`（2 项）、`frontend/tests/sku-workspace-batch-races.spec.js`（3 项）。覆盖旧请求成功/失败、当前加载状态及当前来源失败后重试。

修复前：**4 failed / 1 passed**，独立临时基线副本执行，见 [完整失败证据](products-skus-before.md)。修复后首次执行：**4 files / 33 passed**，含新增 5 项、原 product-master-ux 和 sku-ux 保存保护、失败保留、重试、重复提交、异步列表等回归。最终带日志复跑：**4 files / 33 passed，exit 0**，见[完整通过证据](products-skus-after.md)。`git diff --check`（两处视图）通过。

```powershell
cd frontend
npx vitest run tests/product-workspace-batch-races.spec.js tests/sku-workspace-batch-races.spec.js tests/product-master-ux.spec.js tests/sku-ux.spec.js --maxWorkers=2
```

`node --test src/views/ProductPage.test.js src/views/SKUPage.test.js`：**11/11 passed**（既有源码/工具契约回归）。

## 浏览器交接（由协调任务负责 IAB + 隔离真实后端）

用户补充“No local Chrome”后，已取消两个本地 Chrome 会话，不再运行。此前 mock Chrome 部分执行和三张 1440px 截图只是中止前产物，**未做完整目视验收，不计本轮通过**。未启动或写入真实业务后端。新增独立 `browser-tests/sku-workspace-batch-races.spec.js` 可供参考，模拟 API 仅证明前端，不能代替真实后端。最终 IAB / 视觉状态：**NEEDS_VERIFICATION**，不声明 UI/UX 全部完成。

真实浏览器核验步骤：

1. 隔离 fixture 中至少准备 A/B 两个 SKU、不同供应商来源，长产品名、长供应商名和长型号。1440/1024/390px 检查产品列表、SKU 列表和编辑器；长文本应可识别、可横向查看表格，页面与按钮不越界或互相遮挡。未证实新长名称布局缺陷，未作猜测性 CSS 修改。
2. 对 A 的供应来源请求限速；打开 A 编辑器后取消，立即打开 B。A 完成或失败后，B 应保持自身来源加载/结果，不出现 A 来源、旧错误或旧动作；B 当前请求失败后“重新加载”成功并清除错误。
3. 产品搜索 A（无结果）并限速补充的无筛选 `/products/` 请求；立即搜索 B。A 完成/失败不得提前启用 B 的刷新按钮、覆盖空态或参考资料。B 最新请求完成后显示正确结果。无法人工稳定排序时采用新增组件测试的 deferred gate 证据，不把普通点击冒充竞态验证。
4. 打开带筛选/详情 URL 的产品/SKU，改描述并保存；保存中重复点击/关闭/导航不重复写入，失败保留字段，重试成功后仍能识别当前记录和筛选。API 业务语义与数据快照验收沿用协调任务范围。

保存状态/上下文已有定向回归覆盖，本轮未证实额外缺陷。异步缩写建议、参考选项并发加载等其他路径未扩展修复；不把审查范围外项目当作已通过。

## 追加静态复核（用户要求不再启动本地 Chrome 后）

- 启动事实澄清：此前确实以 `PLAYWRIGHT_CHANNEL=chrome` 启动过两组本地 Playwright；原套件已执行部分测试，新增 race spec 1440px 用例完成并输出三张截图（sku-list、sku-editor、products）。收到“No local Chrome”后均以 Ctrl+C 取消，进程调用 exit 1。不是“从未启动”；未把该中止运行当作完整 Chrome / 目视验收。
- 本次追加仅静态审查与 `--list` 收集，不启动浏览器。新浏览器 spec 精简为只读 fixture，非 GET 返回 405；按 1440/390px × 旧来源成功/失败共 4 项，明确等待旧网络响应完成并经浏览器帧处理后再检查 B 的加载状态。截图改用 `testInfo.outputPath()`，不再向仓库固定证据目录写入。
- 现有 CI `.github/workflows/ci.yml` 调用 `npm run test:browser` → `scripts/run-playwright-suite-stability.mjs` → `run-isolated-browser-tests.mjs --all-business-tests`；`playwright.isolated.config.js` 在此模式收集 `browser-tests/**/*.spec.js`。新文件不在排除清单内，runner 清空默认 PLAYWRIGHT_CHANNEL，因此本 spec 使用 CI 安装的 Chromium，不需要本地 Chrome。未改 CI、runner 或依赖。
- 已用隔离配置 `--list sku-workspace-batch-races.spec.js` 成功收集 **4 tests / 1 file**；最终版本运行结果仍待 CI / 协调验收，不将收集成功当作浏览器通过。
- ProductPage.vue 相对 HEAD 仅 4 增 / 1 删：局部 exists 和 await 后版本检查。SKUPage.vue 仅 14 增 / 2 删：来源请求序号、编辑器生命周期失效和三处发布保护。两处都未改模板/CSS/保存请求/身份确认/字段值/API/权限规则，无其他人的视图改动混入。
- 产品/SKU 临时基线 `.batch-before.vue` 与 `*-workspace-batch-before.spec.js` 在工作树中均不存在，`git ls-files --stage` 也无记录；未暂存或提交。其他工作包自己的 before 文件不在本任务范围，未触碰。

## IAB 390px 编辑表单补修

真实 `screenshots/sku-editor-390.jpg` 证实字段约 120px：末尾 <=1200px 双列覆盖早期 <=520px 单列，同时全局 <=980px `.field {grid-column:1!important}` 把输入全部压在第一列。已在 SKUPage scoped CSS 末尾增加 <=520px、仅非 sku-create-layout 编辑器的单列规则；桌面/新建规则不变。浏览器 race spec 增加 390px 单列、每个主要字段/控件宽度占满卡片内容区断言，1440px 保持六列断言。仅 `node --check` 和 diff check 通过；依用户要求没有启动新测试或浏览器，新增布局回归待协调 IAB/CI 验证。skus-1440.jpg 待协调任务固定真实视口、等布局稳定后重拍，不能仅据文件名认定桌面截图。
