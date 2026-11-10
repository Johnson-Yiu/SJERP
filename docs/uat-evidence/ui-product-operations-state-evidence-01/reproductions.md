# 问题复现与复审

## OPS-UI-01 窄屏工作区标签与页头之间留空

- 源码 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`。在 Chrome 156.0.8078.80 将视口设为 390×844、原生 100%，打开库存、产品管理、SKU 管理或采购管理。页头下沿至标签栏背景起点间可见一条空带。[库存截图](repro-screenshots/ops-ui-01-inventory-390-100.png)
- 影响。所有共用工作区的窄屏页面多占 12 CSS px，进一步减少表单和表格可见空间。当前截图未证明点击被遮挡。
- 代码定位。窄屏 `.topbar` 高 70px，`.workspace-bar` 固定使用 `top:82px`。[styles.css](../../../frontend/src/styles.css#L154)
- 在 A2 固定候选 `d836ba21a657a3a61b770a1d124a5b1fb62a9f46` 上，采购、产品、库存列表的页头与标签栏间距均在 1 CSS px 内，覆盖三档视口和两档缩放。原问题状态交独立复审。[窄屏候选图](screenshots/a2-purchases-list-390-125.png)

## OPS-UI-02 桌面产品详情左侧内容被截掉

- 在已审基线的隔离库加载 [合成样本](seed.py)，使用 codex 登录。Chrome 156.0.8078.80、1440×900、原生 100% 打开 `/products?detail=1`。等待产品概览出现。名称在左侧被截掉，左起部分标签、指标和预览内容不可见。[实际截图](repro-screenshots/ops-ui-02-product-detail-1440-100.png)
- 影响。桌面用户可能无法识别完整产品名或切换左侧标签。截图中侧栏正常，详情正文从侧栏右边缘被裁切。当前只按已执行的直接详情 URL 复现。
- 代码位置。工作区将详情遮罩左边界限制在 248px，但产品详情仍按整视口宽度计算并右对齐。遮罩的 `overflow:hidden` 裁掉超出左边界的内容。独立复审可核对详情宽度是否受实际遮罩宽度约束。[EntityDetailModal.vue](../../../frontend/src/components/EntityDetailModal.vue#L507) · [styles.css](../../../frontend/src/styles.css#L164)
- A2 固定候选 `d836ba21a657a3a61b770a1d124a5b1fb62a9f46` 在 1440×900、原生 100% 仍可复现。[候选截图](screenshots/a2-product-detail-1440-100.png)
