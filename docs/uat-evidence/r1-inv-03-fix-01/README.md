# R1-INV-03-FIX-01 真实浏览器验收证据

## 环境

- 分支：`codex/r1-inv-03`
- 基线：`1de08f81580a1b1781473e9b1f215ef1988eb36b`
- 隔离合成数据：沿用 `.r1-inv-03-ux.sqlite3` 与前端隔离 API
- 前端：`http://127.0.0.1:5195`
- 浏览器：Google Chrome channel，Playwright 实际操作和截图

## 已验证流程

- 1440px、1024px、700px 打开新建采购单。
- 搜索区域下方可见 SKU 列表；700px 列表滚动区为 160px，内容高度 696px，不再被预览区压缩为不可用区域。
- 实际勾选 SKU A、SKU B，切换当前 SKU，取消 SKU B；采购行数量仍保持原输入 `12`。
- 700px 下完成 SKU 选择并查看库存参考。
- 查看库存记录与差异，实际显示仓库、来源采购单、登记规格、供应来源特征和备注。
- 快速切换时人为延迟 SKU A 响应，SKU B 的当前资料没有被迟到响应覆盖。
- 页面宽度均未产生水平溢出。

## 截图

- [1440px SKU 选择与库存参考](purchase-sku-picker-1440.png)
- [1024px SKU 选择与库存参考](purchase-sku-picker-1024.png)
- [700px SKU 选择、列表可见](purchase-sku-picker-700.png)
- [1440px 库存记录与差异](purchase-sku-difference-1440.png)
- [1024px 库存记录与差异](purchase-sku-difference-1024.png)
- [700px 库存记录与差异](purchase-sku-difference-700.png)
- [Chrome 截图测量日志](browser-capture-log.json)

## 能力边界

本轮复用了 `/skus/:id/inventory-detail/`。页面只显示数据库实际记录的库存流水登记地点、来源单据、交易规格、备注、供应来源特征和相关采购/到货记录；“仓库”明确标为流水登记地点，不推断当前分仓余额。SKUVersion 仍只表示 SKU 主档变更，不被当作库存批次版本。没有可靠关联的数据明确显示“未记录”，不虚构客户、LOGO、包装或版本归属。

已有 SKU 资料图片仅在 SKU 权限可见且接口有图片引用时显示，并明确标注不代表每批库存均使用该图片。
