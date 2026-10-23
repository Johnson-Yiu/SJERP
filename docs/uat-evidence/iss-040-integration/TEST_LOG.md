# ISS-040 测试日志

运行目录：`C:\Users\Johnson\.codex\worktrees\iss-040-integration\森爵照明管理系统`

## 后端

| 命令 | 结果 |
|---|---|
| `python manage.py test crm.tests.test_packing_list_export --verbosity 1` | 28/28 通过 |
| `python manage.py test crm.tests.test_packing_list_export crm.tests.test_actual_packing --verbosity 1` | 54/54 通过 |
| `python manage.py test crm --verbosity 1` | 844 通过，13 skipped，0 failed；Django system check 0 issues |

后端测试覆盖：普通导出、原始模板结构、Logo/VML、长描述、混装箱物理字段只计一次、相同 SKU 相同箱规合并、相同 SKU 不同箱规分开、同 SO 分批 Shipment、60 箱多页、小计与打印区域、缺失物理值不虚构、逐 SKU 数量不一致拒绝、取消/冲销 Shipment 拒绝、权限和 HS Code 脱敏、失败事务不写回。

测试中出现的 `Bad Request`/`Internal Server Error` 是测试主动注入的业务拒绝、权限拒绝或事务回滚路径；最终测试结果均通过。

## 前端

| 命令 | 结果 |
|---|---|
| `npm exec -- vitest run tests/shipment-actual-packing.spec.js --environment jsdom` | 24/24 通过 |
| `npm run build` | 通过；仅有既有 bundle size warning |
| `npm exec -- vitest run tests --exclude tests/detail-drawer-typography.spec.js --exclude tests/phase2a-list-shell.spec.js --environment jsdom` | 63 files / 621 tests 通过 |

完整未排除运行记录为 63 files passed、1 test failed、1 file failed：`detail-drawer-typography.spec.js` 没有测试套件；`phase2a-list-shell.spec.js` 的静态预期未包含基线已有 `/historical-orders` 导航。这两项与 ISS-040 改动无关，排除后其余前端回归全部通过。

## XLSX 与视觉

- 7 个真实服务导出的 XLSX 已保存至 `samples/`，均已用 artifact-tool 导入和渲染。
- `xlsx-structure-validation.json`：16 列双语表头、公司信息、Logo、VML、公式、打印区域、重复表头、页脚和多页样本结构检查全部通过。
- `browser-chrome-packing-tab-1440.png`、`browser-chrome-packing-tab-700.png`：真实 Chrome 桌面/窄屏视觉证据已保存。
- 原生 Excel 打印预览：`PRINT PREVIEW PENDING`。本次未把 artifact-tool 图像当作原生打印预览；遗留项见同目录 `README.md`。
