# R1-ISS-040-FIX-02 Description 行高与文字截断补修证据

状态：`FIXED_PENDING_REVIEW`

分支：`codex/r1-iss-040-dev`

本轮只调整 Packing List Description 列的换行估算和行高，不修改 Shipment、实际装箱、库存、采购、付款、模型或迁移。

## 修复结果

- `_wrapped_line_count()` 采用比模板默认数字字形更保守的列宽容量，覆盖中英文混排、长英文单词和显式换行。
- `_required_row_height()` 使用 `16pt` 文本行高和 `20pt` 总上下留白，无固定 90pt 上限。
- Description 单元格继续保留 SKU、产品描述、Carton No. 和 Notes 原文，并继续启用换行。
- 混装箱、汇总公式、16 列模板、重复表头、A4 横向、打印区域和公司页眉未改变。

## 实际 XLSX 与渲染预览

- [普通箱 XLSX](samples/sample-normal-fixed-02.xlsx) / [预览](samples/sample-normal-fixed-02-preview.png)
- [混装箱 XLSX](samples/sample-mixed-fixed-02.xlsx) / [预览](samples/sample-mixed-fixed-02-preview.png)
- [多页 XLSX](samples/sample-multipage-fixed-02.xlsx) / [首页预览](samples/sample-multipage-fixed-02-preview.png) / [末页预览](samples/sample-multipage-fixed-02-last-page-preview.png)

样例由隔离 SQLite 数据库通过实际 `render_packing_list_xlsx()` 服务生成并重新读取。多页样例包含 60 个装箱行，最后一行是第 60 个纸箱，之后保留小计行。

## 可重复的文字容纳量检查

重新读取三份 XLSX 后，逐个非空 Description 行计算：

`最低行高 = 估算换行数 × 16pt + 20pt`

结果全部满足最低行高，且 `wrap_text=True`：

| 文件 | 数据行 | 估算行数 | 实际行高 |
| --- | ---: | ---: | ---: |
| 普通箱 | 6–7 | 16 | 276pt |
| 混装箱 | 6 | 16 | 276pt |
| 混装箱 | 7–8 | 22 | 372pt |
| 多页 | 6–65 | 22 | 372pt |

渲染检查中，长描述最后一行、混装箱 Notes 最后一个字符、相邻行边框和小计行均可见；未删除或缩短业务文字。多页末段预览保留第 60 行和小计。

## 测试命令及结果

| 命令 | 结果 |
| --- | --- |
| `python manage.py test crm.tests.test_packing_list_export --verbosity 1` | 退出码 0；20 tests，OK |
| `python manage.py test crm.tests.test_packing_list_export crm.tests.test_actual_packing --verbosity 1` | 退出码 0；46 tests，OK |
| `python manage.py test crm --verbosity 1` | 退出码 0；788 tests，OK，skipped 13；system check 无问题 |
| `python -m compileall -q crm` | 退出码 0 |

测试输出中的拒绝和异常堆栈来自既有测试对错误路径、失败回滚和权限保护的验证，最终均为 OK。

## 打印环境限制

已完成 XLSX 重新读取和渲染预览检查；本机没有可用的 Excel、LibreOffice 或原生打印引擎，因此真实纸张分页和 Excel 原生 Print Preview 仍为 `PRINT PREVIEW PENDING`，未冒充通过。GitHub Actions 继续按项目策略保持 PENDING，不重跑无额度 CI。

ISS-040 继续保持 `FIXED_PENDING_REVIEW`，等待 ChatGPT 最终复审。
