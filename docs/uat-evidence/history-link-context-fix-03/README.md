# 历史商品关联上下文修复

基线为已审 A3 提交 `dd019e98f932668ae851dc0c4c7f602f888d51f9`。修复源码提交为 `7fa3799ca1d1785c2e99d8e6cb34583a05164220`。

## 复现与修复

在 A3 原版组件中，甲、乙申请均含同一工作表的第 2 行。甲选中正式 SKU B 并填写「甲来源中已核实」后，切换乙并保存，组件实际向乙申请、乙关联组发出包含甲目标和依据的 `resolve-master` POST。使用合成申请与模拟 API 验证了完整请求路径和载荷。

映射草稿绑定申请、关联组、原始工作表及行号、原始行内容和字段。切换申请或组时复用现有未保存确认。保存前校验归属。详情、搜索和保存回读会丢弃过时响应。失败时保留当前草稿供重试。仍可手动搜索并选择现有正式 SKU。

## 验证

- 定向 Vitest 通过 3 个文件、21 项测试，覆盖申请相同行号、同申请不同组、取消放弃草稿、迟到的搜索和详情、切换后重新选择、迟到的保存回读、失败重试及成功后保留组。生产构建通过，Vite 报告主包大于 500 kB。
- Chrome 使用两个独立 SQLite 库和媒体目录，使用经过认证的本机测试管理员。390 px 视口分别验证 100% 和通过 Chrome 网页缩放设置启用的 125%，后者有效宽度为 312 CSS px。
- 两次实跑均包含 H2 候选选用并保存、缺少规格的 409 冲突、补核规格后预览与保存、关联审计、CSV 文件内容、历史原文与 SKU 归集，以及报告读取失败恢复。截图、实际 CSV 和运行元数据按缩放比例归档。
- 125% 的首次尝试缺少持久 Chrome 会话的身份 Cookie，补齐后业务断言通过。Playwright 默认截图在滚动后的原生缩放页面发生偏移，最终改用 Chrome DevTools 截取实际视口并复跑。

从 `frontend/` 执行的命令

```text
npx --no-install vitest run tests/history-takeover.spec.js tests/history-preflight-page.spec.js tests/history-orders-analysis-race.spec.js --maxWorkers=2
npm run build
node scripts/run-isolated-browser-tests.mjs --business-test history-product-linking-h2-real.spec.js
```

浏览器运行设置 `ISOLATED_CODEX_TEST_SUPERADMIN=1`、`H2_VIEWPORT_WIDTH=390`，以 `H2_NATIVE_ZOOM=100` 或 `125` 分别执行。`H2_EVIDENCE_ROOT` 指向对应的缩放子目录。凭据由本机忽略配置注入。公共台账交由 CI-RESTORE-01 更新。
