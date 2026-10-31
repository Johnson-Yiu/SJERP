# ISS-052 CSV 上传流式大小限制

## 范围与实现

基于 `a6c5b56a00326234681399a3405efa2117198f76`，为 CSV 预览、正式执行及兼容预览入口增加 Django 流式上传保护：

- `CSV_IMPORT_MAX_BYTES` 配置及默认 10 MiB 保持不变。
- `CsvImportSizeLimitUploadHandler` 在 Django 内存/临时文件上传处理器之前运行，仅对 `/api/import/csv/`、`/api/import/csv/preview/` 和 `/api/import/csv/execute/` 生效。
- 处理器累计文件流字节数；一旦超过上限即停止 multipart 解析。导致超限的块不会传给后续内存或临时文件处理器，剩余请求体不再由 Django 上传处理器读取。
- `_read_import_csv()` 的已有大小检查和有界读取继续保留，作为解析阶段的第二道保护。
- 三个入口超限均返回 HTTP 413 和明确的中文大小提示。预览及兼容入口不创建导入审计批次；正式执行先经过既有认证和审计门禁，实体可识别时仅创建失败批次，SHA-256 留空、总行数/失败行数为 0、不创建行审计，也不写业务数据。
- 未修改数据库结构、权限规则、预览签名或导入业务逻辑。

## 流式拦截证据

新增的 `test_upload_stream_limit_stops_all_csv_import_routes_before_file_completion` 通过 Django multipart 上传处理器实际发送 1 MiB 合成文件，将限制设为 64 字节，并把内存上传阈值降至 128 字节，确保正常情况下会使用临时文件处理器。三个入口均在 `_read_import_csv()` 前返回 413；测试断言已观察到的文件流字节数小于完整文件、传递给后续处理器的字节数不超过上限、内存处理器未激活且 `request.FILES` 没有完成文件，客户记录不变。正式执行另验证失败批次存在、摘要为空且无行审计。未登录请求和审计关闭请求仍先由原门禁拒绝，上传处理器未开始读取。

## 验证

使用 Python 3.14.5、Django 6.0.6、DRF 3.17.2；隔离 SQLite 测试数据库及临时 `MEDIA_ROOT` 均位于本轮专属 `%TEMP%` 目录。未连接仓库业务数据库。

- `python manage.py check`：通过。
- `python manage.py makemigrations --check --dry-run`：通过，无迁移变化。
- CSV 相关测试集合：43 项通过，1 项因仅支持 PostgreSQL 而在 SQLite 环境跳过。
- 覆盖 `test_safe_csv_import`、`test_dashboard_import`、CSV 文档编号兼容门禁、CSV 导入权限门禁、销售数据范围 CSV 用例及 `BusinessFlowTests.test_customer_csv_import_updates_by_code`。
- `git diff --check`：通过。

当前全局 Python 包版本低于仓库锁文件所列的 Django/DRF 版本；本轮测试结果应视为当前环境验证，仍可在锁定依赖环境中补验。没有触发 GitHub Actions。
