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

起始源码 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`。首轮远端检查时 `codex/release-completion-acceptance-02` 仅存在本地引用。将当时本地 SHA `d4f90b9233c509f1fc6ad282376ce512fb1a2fbc` 作为预分析输入，固定候选以 A2 实际发布为准。

本轮再次执行 `git ls-remote --heads origin` 查询 release、acceptance 与本包分支。远端未返回 A2 分支，本地仍为上述 SHA。远端独立审查分支 `11c964897afb7558db8e3cd41c4539571aead5eb` 属于前端审查取证，不作为 A2 固定候选。本包浏览器索引对应已审基线。

- `PurchaseDetailModal.vue` 引入资金尝试状态，改动采购付款动作的可用性计算。即使付款流程由 A2 承担，采购抽屉的装载、概览、采购明细、收货和关联销售订单仍值得在固定候选核对。
- `styles.css` 有全局依赖差异，应检查改动选择器是否被各商品／库存页使用，并补拍匹配界面。初查的 `crm/views.py` hunks 涉及财务流水与经营概览，没有采购、SKU 或库存端点的直接改动。
- 使用 `git diff --name-only <baseline> <candidate>` 确认版本范围，再查对应组件的 import、Vue 模板选择器及 API 调用。运行时使用候选自身 worktree 或本包控制的独立候选 worktree。截图记录源代码 SHA，和本包归档提交 SHA 分开。
