# ISS-040 正式 Packing List 导出验收

## 版本与范围

- 统一基线：`54925e0a10a48c16ba3b66bbab9e433f48a0e2d7`
- 旧成果分支：`codex/r1-iss-040-dev`
- 旧成果提交：`f308502362fc8bbee1a57d3905b5c12278719a05`
- 集成分支：`codex/next-iss-040-integration`
- Issue 状态：不修改 `docs/PROJECT_ISSUES.md`，不合并 master。

本次只迁移正式 Packing List 导出服务、Shipment 导出 API、实际箱单页面导出入口、原始 Excel 模板、测试与证据；实际装箱录入模型和接口沿用统一基线，没有重新开发。

## 规则来源

- `docs/Product-Optimization-Phase2G-PCR007.md`：实际 Shipment 装箱的数量、权限、数据范围及不回写约束。
- `docs/Product-Completion-Review-Phase1.md`：实际装箱与正式导出的职责边界。
- 旧成果证据：`docs/uat-evidence/r1-iss-040-dev/README.md`、`docs/uat-evidence/r1-iss-040-fix-01/README.md`、`docs/uat-evidence/r1-iss-040-fix-02/README.md`。

## 迁移内容

- `backend/crm/services/packing_list.py`：基于原始模板生成本次 Shipment 的可编辑 XLSX；导出前校验已确认、未冲销及逐 SKU 发货/装箱数量一致；保留模板 Logo、公司信息、16 列双语表头、打印区域、重复表头和 `Page &P of &N` 页脚。
- `backend/crm/views.py`：新增受现有数据范围和 `inventory/export`、`orders/view`、`skus/view`、`hs_codes/view` 权限控制的 Shipment 导出动作；不改变原有财务统计或 Shipment 数量。
- `frontend/src/api.js`、`frontend/src/components/ShipmentActualPacking.vue`：在实际箱单摘要中增加导出入口；未完成装箱时按钮禁用，导出失败显示逐 SKU 差异。
- `frontend/tests/shipment-actual-packing.spec.js`、`backend/crm/tests/test_packing_list_export.py`：补充导出入口、数量校验、混装箱、箱规区分、分批 Shipment、多页和写回保护回归。
- `backend/crm/templates/packing/Packing List装箱单.xlsx`：原成果保存的原始模板，未以新模板替换。

## 样本与检查

真实服务输出保存于 `samples/`：

- `sample-a-normal.xlsx`：普通纸箱。
- `sample-b-mixed.xlsx`：一个纸箱混装两个 SKU；箱数、净重、毛重和 CBM 只在箱首行计一次。
- `sample-c-different-carton-specs.xlsx`：同 SKU 不同箱规分开，相同箱规合并。
- `sample-d-split-shipment-01.xlsx`、`sample-d-split-shipment-02.xlsx`：同一 SO 的两个实际 Shipment 分别导出。
- `sample-e-multipage-60-rows.xlsx`：60 个箱明细，动态扩展至 66 行，含小计公式、打印区域和重复表头。
- `sample-f-long-description.xlsx`：长英文及中英文混合描述，动态行高显示完整文本。

`xlsx-structure-validation.json` 由 openpyxl/ZIP XML 只读检查生成，并核对原始模板的表头、Logo media、VML 关系、16 列、公式、打印区域、重复表头和页脚；7 个样本的验收检查均为 `true`。artifact-tool 已导入并渲染 7 个样本，渲染图保存在各样本旁的 `*-preview.png`。

## 浏览器证据

- `browser-chrome-packing-tab-1440.png`
- `browser-chrome-packing-tab-700.png`

两张图由真实 Windows Chrome headless channel 加载独立 worktree 服务的实际订单装箱页生成，分别检查桌面与窄屏布局、实际 Shipment、导出按钮和现有装箱信息。原生 Excel Print Preview 未在本环境实际打开，保留状态：`PRINT PREVIEW PENDING`；artifact-tool 渲染不冒充 Excel 原生打印预览。

## 遗留事项

- 需要在具备原生 Excel UI 的验收机上打开至少 `sample-e-multipage-60-rows.xlsx`，检查打印预览中的实际分页、每页重复表头、`Page X of Y`、混装箱 SKU 行不跨页，并将 `PRINT PREVIEW PENDING` 更新为实测结果。
- 本次不修改 ISS-048 财务概览，不修改 Issue 台账状态，不关闭 Issue。
