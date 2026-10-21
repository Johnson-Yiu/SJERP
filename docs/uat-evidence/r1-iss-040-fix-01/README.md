# R1-ISS-040-FIX-01 Packing List Excel 排版与图片保真补修证据

状态：`FIXED_PENDING_REVIEW`

分支：`codex/r1-iss-040-dev`

审查基线：`3fdddbe97c372f30b23b472188fe92c151915193`

本轮只补修正式 Packing List 文件质量，不合并 `master`，不修改 Shipment、实际装箱、采购、库存、付款或其他开发分支。

## 修复内容

1. 顶部字段改为明确的历史发货信息：`Packing List No.` 使用 Shipment 编号，`Date` 使用发货日期；无可靠 Invoice 来源时保持空白；SO 编号仅显示在 `Sales Order Ref.`。
2. Description、箱号和 Notes 使用实际列宽、英文/中英文混排和换行数计算行高，移除 90pt 固定上限，避免内容被边框截断或覆盖下一行。
3. 产品图片写入时保留模板 `xl/media/image1.png` 原始 LOGO；产品图片使用独立媒体文件和关系，保留 VML 公司页眉、Page X of Y 以及原模板关系。
4. 多页和混装样例验证 16 列、重复表头、汇总公式、打印区域和最后一页数据；导出仍为只读且不回写业务数据。

## 实际 XLSX 样例和预览

- [sample-normal-fixed.xlsx](samples/sample-normal-fixed.xlsx) / [预览](samples/sample-normal-fixed-preview.png)
- [sample-mixed-fixed.xlsx](samples/sample-mixed-fixed.xlsx) / [预览](samples/sample-mixed-fixed-preview.png)
- [sample-multipage-fixed.xlsx](samples/sample-multipage-fixed.xlsx) / [首页预览](samples/sample-multipage-fixed-preview.png) / [末页预览](samples/sample-multipage-fixed-last-page-preview.png)
- [sample-with-product-images.xlsx](samples/sample-with-product-images.xlsx) / [预览](samples/sample-with-product-images-preview.png)

样例由隔离 SQLite 数据库中的真实导出服务生成，包含普通箱、混装箱、超过 50 行多页数据，以及原模板 LOGO 加两个不同产品图片的文件。导出文件已重新读取并检查，不是手工拼接或截图替代品。

## OOXML 验证结果

实际验证命令的退出码为 `0`，结果为：

```json
{"samples":4,"multipage_rows":66,"multipage_print_area":"'Sheet1'!$A$1:$P$66","image_rows":[6,7],"image_colors":[[255,0,0],[0,0,255]],"logo_bytes_match_template":true}
```

- 四份样例均保持 16 列；多页样例为 66 行，打印区域为 `A1:P66`。
- 第 4、5 行保持重复表头；横向、A4、页脚 `Page &P of &N` 保留。
- 多页汇总公式覆盖数据行，净重、毛重和 CBM 不重复计算；混装箱数据没有丢行。
- `image1.png` 字节与原模板 LOGO 一致；产品图片行 6、7 分别为红、蓝图片；产品图片关系不再指向 `image1.png`；VML 仍指向模板 LOGO。

## 测试命令和结果

| 命令 | 结果 |
| --- | --- |
| `python manage.py test crm.tests.test_packing_list_export --verbosity 1` | 退出码 0；18 tests，OK |
| `python manage.py test crm.tests.test_packing_list_export crm.tests.test_actual_packing --verbosity 1` | 退出码 0；44 tests，OK |
| `python manage.py test crm --verbosity 1` | 退出码 0；786 tests，OK，skipped 13；system check 无问题 |
| `python -m compileall -q crm` | 退出码 0 |
| `npm run test:unit` | 退出码 0；136 passed，0 failed |
| `npm run build` | 退出码 0；Vite build 成功，既有大 chunk warning 未影响构建 |

后端全量测试中已有财务/迁移保护断言也保持通过；导出为只读操作，未修改数据库业务记录。

## 真实 Chrome 验收

使用真实 Chrome 操作订单 `SO-FIX-MIXED` 的 Packing List 导出入口，并实际点击“导出 Packing List”：

- [1440px 页面截图](browser-1440-packing-fixed.png)
- [1024px 页面截图](browser-1024-packing-fixed.png)
- [700px 页面截图](browser-700-packing-fixed.png)

三个宽度均能看到实际装箱、数量完成情况、纸箱卡片和导出入口；700px 无水平溢出。Chrome 生成下载动作已触发；由于浏览器下载目录由运行环境托管，实际 XLSX 文件证据使用同一后端导出服务生成并重新读取的四份样例保存。

## 环境限制

- 本机没有可用的 PostgreSQL 服务：PostgreSQL 回归为 `PENDING / environment unavailable`，未伪造通过结果。
- 本机没有 Excel、LibreOffice 或可用打印引擎：真实纸张分页、打印预览和 Excel 打开后的最终分页为 `PENDING`。当前证据是实际 XLSX 的 OOXML、工作表打印设置和预览渲染检查。
- GitHub Actions 继续按项目策略保持 `PENDING`，未制造无意义提交或重复触发。此前运行记录：[39597161426](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39597161426)；三个 job 均在测试步骤前失败且无 steps 日志。

ISS-040 保持 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立代码、模板、权限和视觉复审。
