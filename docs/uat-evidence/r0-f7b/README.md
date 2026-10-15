# R0-F7B 原始浏览器证据

日期：2026-10-15。隔离合成数据，Django8114 / Vite5201 / r0f7b-ux.sqlite3。

[45张截图清单](SCREENSHOTS.md)；[机器清单](manifest.json)；[原始采集记录](capture-records.json)。`generate_manifest.py`只读取原图并验证文件名、请求、DOM和像素，计算SHA-256，不修改图片。采集记录保留列表重复拍摄的历史条目，manifest取同名最后一条。

| 文件前缀（均三尺寸） | 操作说明 |
|---|---|
| packaging-list | 初始列表、长名称、状态、操作列 |
| packaging-create | 新建60×40×30模板表单及尾货说明 |
| packaging-error | 实际超长名称被API拒绝，保留输入 |
| packaging-linked-verified | 共享模板修改前，2个SKU已验证，数量/重量不同 |
| packaging-edit | 共享模板长50改55的未保存编辑及风险提示 |
| packaging-detail | 保存后的55×40×30详情 |
| packaging-linked-updated | 修改后两项待验证，原数量/净重未变 |
| trade-units | SKU1的5/10/50米卷和两个供应商规格 |
| trade-unit-edit | 5米卷不可变定义及备注编辑 |
| trade-unit-error | 超限系数实际拒绝，输入保留 |
| trade-unit-pcs | 切换PCS样本，1箱=100pcs |
| sku-packaging | REPACK保存后重开，SKU主表单上下文 |
| sku-packaging-fields | 重开后包装字段，25基础单位/0.25kg |
| sku-inline-packaging-error | 内联超长名称失败，父表单原关联保留 |
| sku-packaging-batch | 两组合只筛512项填30；之后撤销两项恢复0，未保存SKU |

完整操作与自动/真实证据边界见[验收报告](../../R0-F7B-包装模板与交易单位验收.md)。自动回归、Codex目视、ChatGPT独立图片审查分别记录，后者待审。

种子：`seed_isolated.py`仅允许目标隔离库且拒绝已有Product/SKU/Supplier。执行：在backend目录设置DATABASE_URL=sqlite:///r0f7b-ux.sqlite3，先migrate，再通过manage.py shell -c执行脚本。勿对正式库执行。本轮UI保存改变了种子后的隔离状态，种子不等同最终快照。
