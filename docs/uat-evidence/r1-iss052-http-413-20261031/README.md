# R1-ISS-052-HTTP-413 真实浏览器上传验收

日期：2026-10-31

基线：`d08ca625ac6beeec51ecc14eb92c97da0ea6f63b`

分支：`codex/r1-iss052-http-413-20261031`

## 结论

在隔离 SQLite、隔离媒体/临时目录和真实本地 HTTP 服务中，真实浏览器分别向 CSV 正式预览、兼容预览和正式导入入口上传超限 CSV。6 次浏览器请求均实际收到 JSON `413`，`network_error` 均为 `null`；Django HTTP 服务日志也记录三路由返回 `413`。正常大小文件完成真实 UI 预览和正式导入。结果不是连接重置，也没有把超限请求记作业务导入成功。

确认了原实现的资源缺口并作最小后端修复：旧实现只拦截越限的那一个数据块，但此前 65,319 字节已送入后续上传处理器；测试观察到 Django 临时文件处理器也已打开文件。新实现让 CSV 专用处理器接管文件流、在达到上限前最多保留上限大小的有界前缀；越限即关闭并丢弃该缓冲区，再停止 multipart 解析。`StopFutureHandlers` 阻止 Django 内建内存/临时文件处理器初始化；超限请求不会创建 Django UploadedFile 或临时上传文件。完整且不超限的文件仍作为 `InMemoryUploadedFile` 交给既有解析和导入逻辑。解析阶段既有大小校验保持不变。

正式导入超限请求遵循现有认证/审计门禁。门禁通过且实体可识别时，只留下失败导入批次（空 SHA、零行），不写入客户、SKU、交易等业务记录；两个预览路径不创建导入批次。未改导入业务规则、权限、数据库模型或迁移。

## 复现与根因

修复前以 64 KiB 上限、128 字节 Django 内存阈值及约 128 KiB multipart 文件隔离复现：响应为 `413`，但解析器已观察到 130,855 字节，已有 65,319 字节转发到后续处理器；测试还观察到临时文件处理器打开文件。旧保护只保证跨过阈值的块不再转发，不能证明整个超限文件前缀没有进入 Django 内存/临时存储。

修复后定向测试对三个 URL 都断言：`bytes_forwarded == 0`、内建内存处理器未激活、`request.FILES` 为空、临时处理器没有文件、隔离临时目录为空、CSV 解析器未调用、Customer 未写入。正式执行只记录空 SHA/零行的失败批次。另以 128 字节内存阈值测试 25 行正常 CSV（文件大于阈值），预览成功且没有临时文件或预览业务写入。

## 浏览器及 HTTP 证据

由于 Chrome 扩展浏览器会话正被另一任务占用并出现标签页被接管，按用户此前给出的选择使用 Codex 内置 Chromium 浏览器（IAB）。这是本地真实浏览器，不是 Playwright mock；浏览器页面以应用实际 Axios 客户端发起 multipart HTTP 请求，经本地 Vite 代理到隔离 Django HTTP 服务。超限场景用本地合成文件，认证用户仅为隔离数据库中的合成 QA 用户；未连接真实业务数据库或生产服务。

测试页面：`http://127.0.0.1:5201/browser-tests/iss052-http-413-probe.html`。页面直接显示每个浏览器响应的 endpoint、状态码、Content-Type、错误字段、响应 JSON 和耗时。浏览器截图在执行时通过 UI 工具实际观察；没有保存为仓库图片文件。下表的 `network_error: null` 来自浏览器页面捕获的 Axios 响应，非服务器日志推断。

| 文件 | 预览 `/api/import/csv/preview/` | 兼容 `/api/import/csv/` | 正式导入 `/api/import/csv/execute/` |
|---|---|---|---|
| 10 MiB + 35 B（10,485,795 B） | 413 / `application/json` / 无网络错误 | 413 / `application/json` / 无网络错误 | 413 / `application/json` / 无网络错误 |
| 20 MiB + 1 B（20,971,521 B） | 413 / `application/json` / 无网络错误 | 413 / `application/json` / 无网络错误 | 413 / `application/json` / 无网络错误 |

浏览器页面实测 20 MiB 文件的三个结果均包含“CSV 文件超过大小限制（最大 10 MiB（10,485,760 字节））。”；正式导入返回失败批次 ID。该请求是 HTTP `413` JSON 响应，不是浏览器 `ERR_CONNECTION_RESET` 或连接错误。对应 Django 服务端访问日志记录：

```text
POST /api/import/csv/preview/ HTTP/1.1 413 86
POST /api/import/csv/ HTTP/1.1 413 86
POST /api/import/csv/execute/ HTTP/1.1 413 143
```

同样的三条状态码也在 20 MiB 浏览器请求中由服务端日志记录。

### 正常文件正向路径

浏览器通过正式 ImportPage 上传 64 字节的合成客户 CSV：预览 HTTP `200`，界面显示“校验通过，尚未写入”、新增 1 行/错误 0；确认后正式执行 HTTP `200`，界面显示“导入完成，已写入数据库”、新增 1 行。服务日志：

```text
POST /api/import/csv/preview/ HTTP/1.1 200 333
POST /api/import/csv/execute/ HTTP/1.1 200 92
```

### 隔离数据库与文件系统快照

浏览器测试完成后的独立 SQLite 计数：`Customer=1`（仅正常文件中的 `ISS052-QA-NORMAL`）、`Product=0`、`SKU=0`、`Transaction=0`。导入批次为 3 个超限失败批次（`total_rows=0`、`failed_rows=0`、`file_sha256=""`）和 1 个正常成功批次（1 行、0 错误）；行级审计共 1 条，来自正常客户导入，超限批次均无行审计；操作日志共 5 条（3 个超限批次、1 个正常批次及 1 个客户创建）。`MEDIA_ROOT` 与业务数据库均为本任务专用临时目录。Django `FILE_UPLOAD_TEMP_DIR` 在请求后为空；越限分支自动化断言还在解析时检查了内建临时处理器未创建文件。

## 代码和验证

- `backend/crm/upload_handlers.py`：对本地三个 CSV 路由启用首位专用处理器；有界接收、超限即关闭缓冲并停止解析；通过 `StopFutureHandlers` 不让内建内存/临时处理器初始化；正常文件保持原有解析入口。
- `backend/crm/tests/test_safe_csv_import.py`：新增三个入口的内存/磁盘/数据库副作用回归，以及高于 Django 默认内存阈值的正常 CSV 预览回归。
- `frontend/browser-tests/iss052-http-413-probe.html`：仅测试用浏览器证据页，调用实际 Axios API 客户端并显示真实响应，不被生产 UI 引用。

本地验证：

| 命令 | 结果 |
|---|---|
| `python manage.py test crm.tests.test_safe_csv_import crm.tests.test_dashboard_import crm.tests.test_document_numbers crm.tests.test_functional_rbac --verbosity 1` | 86 项通过；Django test DB 自动销毁 |
| `python manage.py check` | 通过，无系统问题 |
| `python manage.py makemigrations --check --dry-run` | 通过，无迁移变化 |
| `npm run test:trade-units` | 1 文件、4 项通过 |
| `npm run build` | 通过；Vite 有既有大 chunk 警告（主 JS gzip 约 394 KiB） |
| `npm run test:unit` | 171 项中 169 项通过、2 项失败：两项浏览器隔离运行器基础设施测试要求 worktree 内 `frontend/node_modules/@playwright/test/cli.js`，本工作区为避免修改共享依赖使用只读 junction，目标依赖不存在。失败不是 CSV 导入断言；未将其冒充为通过。 |

原始命令输出：[Django 跨模块测试](backend-cross-module-tests.log)、[Django 系统检查](django-check.log)、[迁移检查](django-migrations-check.log)、[Node 单测](frontend-node-tests.log)、[Vitest](frontend-vitest.log)、[生产构建](frontend-build.log)。

Django 测试环境版本：Python 3.14.5、Django 6.0.6、DRF 3.17.2。前端所用共享依赖树的实际 Vite 为 8.2.0，而锁文件要求 8.3.5；`npm ls vite --depth=0` 因版本不匹配返回 `ELSPROBLEMS`。构建在实际安装的 8.2.0 上通过；完整锁定依赖安装未执行。

没有新增数据库迁移；没有运行 GitHub Actions、连接 PostgreSQL、连接生产、部署或关闭 Issue。ISS-052 继续保持 `FIXED_PENDING_REVIEW`；真实员工操作人及正式行级审计验收仍为原有待办，本轮隔离合成账号测试不替代该验收。
