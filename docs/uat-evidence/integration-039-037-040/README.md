# ISS-039 / ISS-037 / ISS-040 统一集成验收

## 集成范围

- 统一基线：`54925e0a10a48c16ba3b66bbab9e433f48a0e2d7`
- 集成顺序：ISS-037 `6d3496d0cc45213f4aab26950cd5ab8629996de8` → ISS-039 `1d976d8dd1d1b827d9ab9122c4d07be8c816a14d` → ISS-040 `a4fc6d4f01f8c32a4a89f0d46557500a34566e98`
- 集成分支：`codex/integration-039-037-040`
- 未合并 master，未修改 Issue 状态，未修改其它 worktree。

## 冲突处理

三项代码提交均已保留。唯一冲突为 `docs/PROJECT_PHASES.md` 的并行历史记录追加；保留 ISS-037 原记录，并在其后追加 ISS-039 记录。`PurchaseOrderPage.vue`、前端测试、`backend/crm/views.py` 自动合并，未覆盖任一功能。

## 交叉验收

新增 `backend/crm/tests/test_integration_039_037_040.py`，验证：

- 正式销售订单客户主体快照、正式采购单供应商快照在主档修改后保持不变；
- 使用正式采购单历史供应商快照进行采购成本分配，公共运费按订单分摊，金额守恒；
- 成本分配不新增银行交易或付款计划；
- 采购归属订单执行实际 Shipment，生成实际箱单；
- Packing List 保留 16 列、Shipment/SO 引用、Subtotal 公式和 `Page &P of &N` 页脚。

## 证据索引

- ISS-039 权限、脱敏、审计、回滚与金额守恒：`../iss-039-integration/`
- ISS-037 快照与历史主体：`../r1-iss-037-p1/`
- ISS-040 真实 XLSX 样本、模板结构、Logo、公式、多页与长描述：`../iss-040-integration/`
- 当前统一分支真实 Chrome：`chrome-integrated-desktop-1440.png`、`chrome-integrated-narrow-700.png`

ISS-040 原生 Excel 打印预览仍为 **PRINT PREVIEW PENDING**。已有 PNG/artifact-tool 结构预览不作为原生 Excel 打印预览结论。
