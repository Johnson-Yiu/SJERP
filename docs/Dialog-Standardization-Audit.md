# Dialog Standardization Audit

审计日期：2026-10-03。范围为 `frontend/src` 的业务源码；测试中对旧浏览器 API 的 mock 不计入业务残留。

## 原生 Dialog 审计与替换

| 位置 | 原调用 | 业务动作 / 风险 | 替代方案 |
| --- | --- | --- | --- |
| `views/CategoryPage.vue` | `confirm` ×2 | 删除分类、删除属性（高） | `confirmDialog`，危险确认 |
| `components/EntityDetailModal.vue` | `confirm` ×3 | 删除跟进、批量停用/启用 SKU（高/中） | `confirmDialog` |
| `views/DocumentPage.vue` | `confirm` ×1 | 删除订单草稿（高） | `confirmDialog`，危险确认 |
| `components/OrderDetailModal.vue` | `confirm` ×3 | 生命周期转换、超发、重生成装箱方案（高） | `confirmDialog`，危险确认 |
| `views/PackagingPage.vue` | `confirm` ×1 | 修改已关联包装模板（高） | `confirmDialog`，危险确认 |
| `components/ProductSkuManagement.vue` | `confirm` ×1 | 批量停用/启用 SKU（高/中） | `confirmDialog` |
| `views/ProductPage.vue` | `confirm` ×1 | 删除产品（高） | `confirmDialog`，危险确认 |
| `views/PurchaseOrderPage.vue` | `confirm` ×2、`prompt` ×1 | 下单、删除草稿、取消采购原因（高） | `confirmDialog`、必填 `inputDialog` |
| `components/PurchaseCostAllocationModal.vue` | `confirm` ×1 | 放弃未保存成本分配（中） | `confirmDialog` |
| `components/QuoteDetailModal.vue` | `confirm` ×1 | 停用重要备注（高） | `confirmDialog`，危险确认 |
| `views/ResourcePage.vue` | `confirm` ×1 | 删除通用资源（高） | `confirmDialog`，危险确认 |
| `views/SKUPage.vue` | `confirm` ×1 | 停用 SKU（高） | `confirmDialog`，危险确认 |
| `components/RichTextEditor.vue` | `prompt` ×1 | 输入链接（低） | `inputDialog`；格式错误使用 `alertDialog` |

合计：`confirm` 19 处、`prompt` 1 处、`alert` 0 处。实施后，这些业务调用均已移除。

## 新的统一能力

- `src/dialogs.js`：可 await 的 `confirmDialog`、`inputDialog`、`alertDialog` 与 `showToast`；请求串行排队，避免重叠 Dialog。
- `components/AppDialogHost.vue`：应用内 DOM Dialog/Toast Host，提供正常 `button`、明确文字及 `data-testid="dialog-confirm"` / `data-testid="dialog-cancel"`。
- 非危险 Dialog 可通过 Escape 或遮罩取消；危险确认不允许遮罩关闭。确认进入短暂 disabled/loading 状态，阻止双击重复解析。

## 特殊项

- `main.js` 的 `beforeunload` 仅保存当前页面滚动位置，未设置 `returnValue`、未显示离站确认，不属于业务原生 Dialog，保留。
- 现有表单广泛使用 `required`、`min`、`max`、`pattern` 与 `type=number`，可能产生浏览器 validation bubble。本轮没有重写表单校验体系；这些仍是后续可单独处理的 UX 改进项。
