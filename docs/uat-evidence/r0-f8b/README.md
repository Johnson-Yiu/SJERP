# R0-F8B 原始浏览器与CSV证据

2026-10-16；Codex内置浏览器连接Vite5203 / Django8116；仅用专用r0f8b-ux.sqlite3合成数据。中断后保留该库继续验收，没有删除/清空数据。

| 截图前缀 | 状态与操作 |
|---|---|
| initial（3尺寸） | 初始无文件，模板可用，预览禁用；1024规则说明下移 |
| file-selected（1440） | 真实chooser选择A-customers-new.csv，名称/大小/尚未校验 |
| validation-success（3尺寸） | 新增2条客户校验通过，尚未写入，数据库仍0 |
| confirmation（3尺寸） | 真实确认对话框，新增/更新数和覆盖提醒；先取消验证0写入 |
| completed（3尺寸） | 真实新增2成功，实际DB客户2；进入客户模块入口 |
| validation-errors（3尺寸） | 重复编号错误表格/行号/业务编号及下载入口；最终列宽调整后补拍 |
| empty-file（1024） | 实际空文件被后端拒绝，所选文件保留 |
| wrong-header（1440） | 实际错误表头缺code/name拒绝 |
| execution-conflict（3尺寸） | 预览后隔离资料变更，实际执行拒绝，文件保留并要求重新预览 |
| imported-customer-detail（1440） | 真实更新后从客户列表重开详情，多行引号备注原样显示 |

[SCREENSHOTS.md](SCREENSHOTS.md)和[manifest.json](manifest.json)保存22张原JPEG的尺寸/SHA-256。`generate_manifest.py`只读原图，不做图像编辑；`capture-records.json`记录请求视口/DOM/URL。图片是采集当时状态，不代表最终库字段一直相同。原始下载CSV在downloads，源合成CSV在files，均单独计算哈希。

`generate_csv_files.py`生成合成源文件；不修改数据库。`snapshot_database.py`只读核对指定隔离库；`verify_files_database.py`只读核验已保存文件/数据库记录；`inject_conflict.py`仅用于显式专用库制造并发状态冲突。不得将上述测试脚本指向业务库。SQLite数据库本体不提交。

[完整正常/异常矩阵](../../R0-F8B-数据导入验收.md)、[真实下载与DB核对](file-database-verification.json)、[自动化结果](TEST-RESULTS.md)。自动API模拟、隔离后端/浏览器、正式权限/审计、ChatGPT独立视觉分别记录；后两项未由本轮推定通过。截图未受阻，独立图片待审。
