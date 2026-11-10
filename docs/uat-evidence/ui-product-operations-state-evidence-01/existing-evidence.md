# 既有证据与候选差异

| 既有证据 | 可沿用范围 | 保留边界 |
| --- | --- | --- |
| [RELEASE-INTEGRATION-REPAIR-01 补验](../release-integration-repair-01-followup/README.md) | 同一标签页内库存调整响应丢失后回到工作区重放原提交，真实后端防重复；产品证书 400 指明证书名称并保留原输入。 | 库存场景为真实写入并主动丢弃响应；关闭整个浏览器标签页不在恢复范围。该报告的六种原生缩放组合是财务和历史页。 |
| [ISS-028／035 分类和 SKU 模板](../iss-028-035-category-schema/README.md) | 真 Chrome、隔离 API 及 SQLite，根分类选择与持久化、分类筛选、属性继承、模板变更、已发布 SKU 普通编辑重开。 | 报告保存了 1440／390 的视觉图及当时侧栏覆盖；未标原生 125%。旧截图不能证明当前布局问题仍存在。 |
| [供应商及采购定向复测](../supplier-purchase-ux-regression-054bd825/README.md) | ISS-022／075 的真实隔离采购与供应商条款流程；另有供应商界面布局图。 | `supplier-ui` 的浏览器截图来自模拟 API；ISS-022／075 另有真实后端证据，分别归属原源码。 |
| [ISS-039 采购成本分配](../iss-039-integration/README.md) | 成本候选、跨订单保存、刷新恢复、只读与无权的交互证据；后端定向检查金额守恒与权限。 | Chrome 图证使用 mock API。真实后端专项与浏览器流程是分开的，不能作为本包真实端到端成本分配通过。 |
| [库存 UI 模拟诊断](../review-integration-batch-20261104/playwright-current/browser/r1_repair_04_evidence_dir) | 1440／1280／1024 库存与流水布局，空态、故障重试、过滤、详情导航、只读入口。 | 由 [inventory-ux.spec.js](../../../frontend/browser-tests/inventory-ux.spec.js) 屏蔽真实 API，桌面宽度。 |
| [库存仓库与货位历史截图](../history-operational-closeout-20261104/screenshots/inventory-location-chrome.json) | Chrome 156.0.8078.80，1440／390，手工库存调整表单中填写位置字段。 | 该脚本没有提交库存，不能作为仓库与批次数据落库或回显证据。 |
| [ISS-022 MOQ](../iss-022-procurement-moq/README.md) | 合成资料经真实隔离后端，低 MOQ 返回 400 后补填原因并成功，同等于 MOQ 时直接下单。 | 原问题证据，不能替代新候选的同状态复测。 |

## A2 对照

已在 GitHub 核对 `codex/release-completion-acceptance-02` 发布 SHA `d836ba21a657a3a61b770a1d124a5b1fb62a9f46`。在该 SHA 的独立检出中使用 Chrome 156.0.8078.80、独立 SQLite 和媒体目录完成真实 API 复验。运行取证脚本时设置 `PRODUCT_OPS_FOLLOWUP=candidate` 和 `PRODUCT_OPS_CANDIDATE_SHA`，脚本断言检出与指定 SHA 一致。

采购、产品、库存列表和共用页头与标签栏、采购与产品新建、产品详情，以及采购草稿详情的概览、采购明细、收货和关联销售订单均覆盖 1366×768、1440×900、390×844 各自的原生 100% 和 125%，共 60 张截图。采购明细显示四行合成采购数据，收货与关联销售订单按草稿样本取证。各组合中页头与标签栏间距均在 1 CSS px 内。 [A2 浏览器证据](browser-a2-candidate.json)

A2 的相关差异在 `PurchaseDetailModal.vue`、`useFinanceAttempts.js` 和 `styles.css`。采购付款和资金恢复属于 A2 的验收范围。桌面产品详情左侧裁切在候选上仍可复现。[候选截图](screenshots/a2-product-detail-1440-100.png)

前期取证的业务源码为 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`。基线与候选的前端差异用 `git diff --name-only 1e45e42c d836ba21 -- frontend/src` 核对。各 HTTP 索引分别保留执行时的检出 SHA。
