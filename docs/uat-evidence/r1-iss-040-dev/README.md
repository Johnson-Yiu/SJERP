# R1-ISS-040-DEV 正式 Packing List Excel 导出验收证据

## 状态与范围

- 分支：`codex/r1-iss-040-dev`
- 基线：`origin/master` `25405e1b25ff8a218b67883acf489ada8a53e146`
- 最终提交：待提交后补录
- 建议状态：`FIXED_PENDING_REVIEW`
- 本轮范围：对已确认且数量完整的实际发货单导出正式 Packing List Excel。导出只读，不创建、修改或冲销发货、装箱、库存、采购、付款、应收或订单记录。
- 不新增数据库模型或迁移；不修改历史业务金额、库存流水和履约事实。

## 实现与模板映射

后端入口为 `GET /api/shipments/{id}/export-packing-list/`，复用实际装箱数据和项目既有权限。前端只在已确认且装箱数量与发货数量一致时启用“导出 Packing List”；数量不完整时按钮保持禁用，后端再次校验并返回每个 SKU 的差异。

原始模板 `Packing List装箱单.xlsx` 已保存为 `backend/crm/templates/packing/Packing List装箱单.xlsx`。实现保留模板的表头、双语列、公司抬头、Logo、原有页眉/页脚、A4 横向打印设置和模板格式，并补充 `Page &P of &N` 页码。

| 模板区域 | 实际来源/处理 |
|---|---|
| Packing List No. | `Shipment.shipment_no` |
| Date | `Shipment.shipment_date` |
| Invoice Ref No. | 关联销售订单号；模板字段名沿用，不虚构发票号 |
| Product Name / Description | 优先使用入库/出库快照，回退到订单行快照，再回退到当前 SKU 资料；描述中标记 SKU code、箱号和已记录的箱备注 |
| Image | 当前 SKU 有可读产品图片时嵌入；没有时留空 |
| Quantity / pcs/carton / Cartons | 实际装箱明细，数量按基础单位 pcs 输出 |
| HS Code | 仅具备 `hs_codes.view` 时输出；无权限时留空，不泄露编码 |
| Carton L/W/H、N.W.、G.W.、CBM | 实际箱记录；模板默认零值在业务上视为“未测量”，因此留空而不是伪造零物理数据 |

模板没有独立 SKU Code 列，因此 SKU code 写入 Description 的 `SKU:` 行，避免丢失 SKU 识别信息。

### 原始模板结构核对

实际读取用户附件副本后，工作表为 `Sheet1`，原始有效区域为 `A1:P15`，列顺序为：`A No.`、`B Product Name`、`C Image`、`D Description`、`E Quantity(pcs)`、`F HS Code`、`G pcs/carton`、`H Cartons`、`I Carton L(CM)`、`J Carton W(CM)`、`K Carton H(CM)`、`L N.W.`、`M Total N.W.`、`N G.W.`、`O Total G.W.`、`P CBM`。第 4 行为英文表头，第 5 行为中文表头；`A15:G15` 为小计标签合并区域；原始页眉包含 `PACKING LIST`，Logo 和页眉绘图位于模板的 VML/媒体部件，页面为 A4 横向并以第 4–5 行为打印标题。

导出结果在保留上述结构的基础上，将打印区域扩展到实际最后一行，自动插入超出模板 9 行明细的行，重复第 4–5 行表头，并设置 `Page &P of &N`。原始模板没有单独的打印区域值和页脚页码，因此这两项属于按任务要求补充，不是用另一套模板替代。

同一 SKU 在相邻箱中具有相同装箱数量、尺寸、重量、CBM 和备注时合并为连续箱号范围；混装箱不被错误合并，物理信息只在该箱第一行展示，其余 SKU 行保留数量和来源。不同箱的备注写入描述，未记录时明确为空，不推断包装、客户定制或版本信息。

## 自动化测试（实际执行）

以下命令均在本 worktree 执行，退出码为 `0`：

| 命令 | 结果 |
|---|---|
| `python manage.py test crm.tests.test_packing_list_export --verbosity 1` | 14 tests passed |
| `python manage.py test crm.tests.test_packing_list_export crm.tests.test_actual_packing --verbosity 1` | 40 tests passed |
| `python manage.py test crm --verbosity 1` | 782 tests passed，13 skipped，`OK` |
| `python -m compileall -q crm` | 通过 |
| `npm run test:unit` | 136 tests passed |
| `node_modules\\.bin\\vitest.cmd run tests/shipment-actual-packing.spec.js --environment jsdom` | 24 tests passed |
| `node_modules\\.bin\\vitest.cmd run tests --exclude tests/detail-drawer-typography.spec.js --environment jsdom` | 63 files / 637 tests passed |
| `npm run build` | 通过；Vite 8.3.1，保留既有大 chunk warning |

项目同时存在 Node 原生测试文件和 Vitest 文件。直接运行未排除的完整 Vitest 扫描会把 `tests/detail-drawer-typography.spec.js` 当作 Vitest 文件，产生 runner mismatch；该命令中已执行的 637 个 Vitest 测试全部通过，未将 runner mismatch 当作业务通过或失败隐藏。

另执行了生成证据样本的隔离数据库命令：

```text
python manage.py migrate --noinput --verbosity 0             # exit 0
python generate_packing_list_evidence.py                    # exit 0
```

样本包括正常单 SKU、混装箱和 60 箱多页单据。使用 artifact-tool 导入并渲染三份实际生成的 XLSX，均成功生成对应 PNG 预览；混装描述的行高已按换行内容增加，未出现文字覆盖下一行。

## 真实 Chrome 验收

使用真实 Chrome、隔离 SQLite 和开发阶段超级管理员身份操作：

1. 打开 `http://127.0.0.1:5192/orders?uat=1`。
2. 进入实际发货单 `SH-MIXED` 的“装箱”页，页面显示 2 箱，SKU A `6/6 pcs`、SKU B `4/4 pcs`。
3. 在 1440px 窗口中确认“导出 Packing List”按钮可见并实际点击。
4. 将窗口调整为 700px，确认装箱卡片、数量、重量和导出按钮仍可滚动查看，页面无水平溢出。
5. 导出请求由同一真实页面触发；CUA 会话未提供下载文件的本地等待路径，因此文件内容以同一后端服务生成的三份真实 XLSX 样本和结构检查作为文件证据，不把浏览器按钮点击冒充为已取得下载文件。

截图：

- [1440px 实际装箱与导出按钮](./browser-1440-packing.png)
- [1024px 实际装箱与导出按钮](./browser-1024-packing.png)
- [700px 实际装箱窄屏布局](./browser-700-packing.png)

样本文件及预览：

- [正常单 SKU](./samples/sample-normal.xlsx) / [预览](./samples/sample-normal-preview.png)
- [混装箱](./samples/sample-mixed.xlsx) / [预览](./samples/sample-mixed-preview.png)
- [多页样本](./samples/sample-multipage.xlsx) / [预览](./samples/sample-multipage-preview.png)
- [隔离样本种子记录](./samples/seed.json)

## 权限、历史和兼容边界

- 导出接口要求库存导出、订单查看和 SKU 查看权限；HS code 单独按 `hs_codes.view` 脱敏。
- 当前开发环境使用 `development_superadmin_enabled()`，没有伪造正式员工或正式审计人。本轮没有宣称正式 RBAC 员工 UAT 通过。
- 导出从实际装箱/发货数据读取，不回写任何历史单据；未完成装箱、取消或冲销发货会被拒绝。
- 缺少物理称重/尺寸的记录留空；当前模型无法区分“真实测得 0”与默认零值，本轮不把默认零解释为真实物理数据。
- 模板没有独立 SKU 列，因此使用 Description 的 SKU 行；如物流方要求独立 SKU 列、原产地、包装材质或正式 Invoice No.，需另行确认模板规则。

## 环境限制与未完成项

- 本机 PostgreSQL：`127.0.0.1:5432` 未监听，未伪造 PostgreSQL 通过；仅执行 SQLite 全量回归。
- 本机未发现 Excel、LibreOffice 或 soffice，因此没有执行原生打印预览；artifact-tool 预览用于结构与布局检查。
- GitHub Actions 本轮保持 `CI PENDING`，没有为制造 CI 记录创建无意义提交；推送后由独立审查决定是否在额度恢复后补跑。
- 正式员工 RBAC、真实下载目录捕获和最终纸张打印效果仍需独立审查/具备相应环境后补验。
