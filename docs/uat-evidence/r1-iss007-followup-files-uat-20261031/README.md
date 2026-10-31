# R1-ISS007-FOLLOWUP-ATTACHMENT-UAT

本报告记录固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 上的跟进附件隔离验收。分支为 `codex/r1-iss007-followup-files-uat-20261031`。

## 当前结论

真实 Chrome 已完成隔离数据下的上传、保存、刷新重开、预览、下载、授权/拒绝直链访问及文件/数据库/审计核对。此前发现并最小修复 UTF-8 纯文本预览缺少 charset 的问题。2026-11-01 在新的专属临时 SQLite/MEDIA_ROOT 中，用户明确授权后完成了合成目标附件删除、替代附件上传及删除后刷新/直链/审计检查；没有触碰真实历史附件或其他媒体目录。ISS-007 仍为 `NEEDS_VERIFICATION`，等待独立复审，不据本地 UAT 自行关闭。

## 隔离边界与身份

- 后端使用全新 SQLite 数据库和独立临时 `MEDIA_ROOT`；未连接或改动生产数据库、真实业务记录或生产媒体目录。
- 合成客户、跟进、历史样式附件和两个隔离认证测试账号均只存在于临时库。2026-10-31 操作人为 `iss007-uat-operator`；2026-11-01 删除操作人为 `iss007-uat-0c9dfbf4`，均为普通非超级用户。删除日志的 `operator` 外键指向该次已认证测试账号，非开发超级管理员，也不伪称真实员工账号。无权限账号仅用于直链拒绝测试。报告不保存临时密码。
- 仅测试服务器环境临时启用 `RBAC_ENFORCEMENT=1`、`AUDIT_LOG_ENABLED=1`、`DEVELOPMENT_SUPERADMIN=0`，并将本地 Vite 来源 `http://127.0.0.1:5279` 加入该隔离服务器的 `CSRF_TRUSTED_ORIGINS`。没有修改项目或生产权限配置。
- Chrome `156.0.8078.48`，实际安装路径 `C:\Program Files\Google\Chrome\Application\chrome.exe`；桌面视口 `1440×900`，窄屏 `390×844`。截图均为本轮真实运行生成，非旧图复制冒充。

## 业务流程结果

| 检查 | 结果与证据 |
|---|---|
| 选择 3 个合成附件并保存 | 跟进记录 `PUT /api/follow-ups/1/` → HTTP 200；附件上传 `POST /api/follow-ups/1/attachments/` → HTTP 201；真实操作人审计存在。 |
| 刷新、重开 | 页面刷新后重新打开编辑器，可见 1 个历史附件及本轮 3 个附件；数据库记录和磁盘文件均存在，名称/相对路径/字节数一致。 |
| 预览 | 受保护 URL HTTP 200，`Cache-Control: private, no-store`；修复后 `Content-Type: text/plain; charset=utf-8`，真实 Chrome 显示完整中文内容。 |
| 下载 | Chrome 下载 `ISS007-download.bin`，8 字节与上传字节逐一相同，SHA256 `5e62a906ba05040729ff6e2b3e3f7d744671a3c64f375cc2159b29483ed29bc1`。 |
| 授权/拒绝直链 | 授权用户读取有效历史附件 URL → HTTP 200；匿名请求 → HTTP 403；已认证但无跟进查看权限 → HTTP 404。旧 `/media/` 入口 → HTTP 404。有效历史路径的无权限访问 → HTTP 404。 |
| 数据库、路径与操作日志 | 4 条附件记录均指向存在的隔离媒体文件；DB 与磁盘字节数相同。上传日志记录 `attachment_ids=[2,3,4]` 和对应文件名，operator 为 `iss007-uat-operator`；跟进编辑日志也绑定该用户。逐文件 SHA256 见下方。 |
| 删除/替换、刷新与其他附件保护（2026-11-01） | 用户明确授权后，只对新建合成附件 `ISS007-delete-target.txt` 点击 UI 删除确认；取消确认先保留文件。DELETE → HTTP 204；目标 DB 行和磁盘文件均不存在；删除前后目标私有 URL 均为 HTTP 404。再通过 UI 上传 `ISS007-delete-target-replacement.txt` → HTTP 201，刷新后新附件显示、旧目标不再显示。删除前已有的合成历史样式文件、预览文件和下载文件，其 ID、路径、DB/磁盘大小及 SHA256 全部保持一致。审计为 `删除跟进附件`，操作人为隔离非超级用户 `iss007-uat-0c9dfbf4`，请求 `DELETE /api/follow-ups/1/attachments/4/`，元数据记录目标 ID `4` 和文件名。 |

### 上传后数据库与文件核对

| ID | 文件 | DB 相对路径 | DB/磁盘字节 | SHA256 |
|---:|---|---|---:|---|
| 1 | `ISS007-legacy-history.txt` | `follow-up-attachments/2024/01/ISS007-legacy-history.txt` | 33 / 33 | `70390a1960a419faa0c75674f14d5d50ba9d96274cdf46e386208bf585af9af3` |
| 2 | `ISS007-preview.txt` | `follow-up-attachments/2026/10/ISS007-preview.txt` | 64 / 64 | `ee61d0bbe02c4a7b96f8b8a8057547583c98aab8089e643de00047ca3f976410` |
| 3 | `ISS007-download.bin` | `follow-up-attachments/2026/10/ISS007-download.bin` | 8 / 8 | `5e62a906ba05040729ff6e2b3e3f7d744671a3c64f375cc2159b29483ed29bc1` |
| 4 | `ISS007-delete-target.txt` | `follow-up-attachments/2026/10/ISS007-delete-target.txt` | 32 / 32 | `9e1d7b72cf92759290d760a4ebfc58980c819b24f9ea133b0df2d5678cf3e8fc` |

上传操作审计为 `POST /api/follow-ups/1/attachments/`，标签“上传跟进附件”，元数据包含 ID `[2,3,4]` 与上述 3 个名称。无文件正文或密码写入审计。2026-11-01 删除操作日志在目标 DB 行删除后仍保留隔离认证测试操作人的用户外键、HTTP method/path 及 `attachment_id` / `file_name` 元数据；详见本轮删除后核验记录。

### 2026-11-01 删除与替代 UAT 明细

旧隔离 DB/MEDIA_ROOT 未在参考分支证据中保留，旧测试服务也未运行；故没有把旧文件状态当作仍存在。本轮另建随机运行 ID `iss007-delete-uat-5997ec4cc688423a9d24b74f0c9dfbf4` 的一次性临时环境并重新创建合成客户、跟进、普通非超级用户操作人及一条“历史样式”合成附件。该附件不是任何真实历史业务附件。运行目录留在本机系统临时目录供复核；没有清理或遍历其他媒体目录。

删除目标上传后为 32 字节，SHA256 `9e1d7b72cf92759290d760a4ebfc58980c819b24f9ea133b0df2d5678cf3e8fc`。删除后 DB 记录不存在，先前相对路径上的磁盘文件不存在，认证操作人的旧 URL 返回 404；替代附件 `ISS007-delete-target-replacement.txt` 为 34 字节，SHA256 `7fd3572e955f74c4a46c0fd58c8e1469b8a78ac5df784ab0e7aea2df8e39f4f8`。替代附件为单独新文件，不覆盖旧对象；旧 URL 在替代上传后仍返回 404。

其他既有合成附件保持：`ISS007-legacy-history.txt` 57 字节 / `a9a3d887ca46e0a9ecd410a9bba89e6ee04a43916babb39849f6ad9bcc35314f`；`ISS007-preview.txt` 64 字节 / `ee61d0bbe02c4a7b96f8b8a8057547583c98aab8089e643de00047ca3f976410`；`ISS007-download.bin` 8 字节 / `5e62a906ba05040729ff6e2b3e3f7d744671a3c64f375cc2159b29483ed29bc1`。三者删除前后附件 ID、存储相对路径、数据库/磁盘大小及 SHA256 一致。完整快照见 [删除前数据](delete-20261101-0c9dfbf4/before-delete-snapshot.json) 和 [删除后核对](delete-20261101-0c9dfbf4/after-delete-verification.json)。

真实 Chrome 截图：取消确认时目标仍存在；删除后即时状态及刷新后的列表不再含目标；替代附件刷新后在桌面和 390px 窄屏均显示。窄屏检查 `documentScrollWidth=375`，未出现水平溢出。截图：

- [桌面：取消确认，目标保留](delete-20261101-0c9dfbf4/screenshots/desktop-delete-cancelled-1440x900.png)
- [桌面：确认删除后的即时状态](delete-20261101-0c9dfbf4/screenshots/desktop-delete-immediate-state-1440x900.png)
- [桌面：删除后刷新，其他附件保留](delete-20261101-0c9dfbf4/screenshots/desktop-delete-refresh-1440x900.png)
- [桌面：替代附件刷新后显示](delete-20261101-0c9dfbf4/screenshots/desktop-replacement-refresh-1440x900.png)
- [390px：替代附件刷新后可见](delete-20261101-0c9dfbf4/screenshots/mobile-replacement-visible-390x844.png)

## 发现与修复

初次 Chrome 预览响应为 `text/plain`（无 charset）；合成 UTF-8 文本的原始 API 字节正确，但 Chrome 将中文显示为乱码。`backend/crm/file_access.py` 现仅在响应类型精确为 `text/plain` 时增加 `charset=utf-8`，不改存储字节、附件数据、授权、缓存或二进制响应。`backend/crm/tests/test_functional_rbac.py` 增加中文内容、响应头及原始字节回归。Django 相关测试通过，真实 Chrome 复验内容正确。

初次浏览器尝试中的其他失败分类：

- Playwright 默认 Chrome 路径与机器实际安装路径不同；发现并使用已安装的 Chrome，没有安装软件或改变其他 Chrome 窗口。
- Vite 的默认端口已占用，改用 5279；首次 PUT 被隔离 Django 测试服务器以 CSRF Origin 403 拒绝。响应为 `CSRF Failed: Origin checking failed - http://127.0.0.1:5279 does not match any trusted origins.`。只在隔离服务器环境增加该本地来源后重跑，非产品授权缺陷。
- 首次复用已认证 Chrome context 时，Django admin 将 `/admin/login/` 重定向到管理页，测试脚本仍等待登录表单。测试助手已改为识别已有会话；没有更改产品代码或放宽产品断言。
- `node --test tests/unsaved-changes.spec.js` 曾因该项目 Vitest 文件的扩展名省略式 ESM 导入而在加载阶段失败；不计作产品测试通过。对应附件回归由项目 Vitest 正式 runner 执行并通过。

## 测试日志

运行均为本地隔离测试，不触发 GitHub Actions。

```text
Fresh SQLite migrate --noinput: OK; all migrations through crm.0092_merge_fulfillment_and_csv_audit applied.
python manage.py check: System check identified no issues (0 silenced).
python manage.py makemigrations --check --dry-run: No changes detected.
python manage.py test crm.tests.test_customer_h1.FollowUpOwnershipAndAttachmentTests crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_media_url_requires_record_module_and_customer_scope --verbosity 2
Ran 6 tests in 2.716s — OK.
npx vitest run tests/follow-up-richtext-and-attachments.spec.js --environment jsdom
Test Files 1 passed (1); Tests 12 passed (12).
npm run build
vite build — success; 2019 modules transformed. Existing large-chunk warning remains (main JS ~1,128 kB).
npm ci --ignore-scripts --no-audit --no-fund
success; 227 packages installed.
```

2026-11-01 补充：锁定 Python 环境（CPython 3.14；`backend/requirements.lock`）安装成功，`pip check` 无冲突；`crm.tests.test_customer_h1.FollowUpOwnershipAndAttachmentTests` 5 项通过；浏览器脚本/runner/capture 脚本 `node --check` 通过。真实 Chrome 156.0.8078.48：上传 201、取消确认保留、删除 204、旧 URL 删除前后 404、替代附件上传 201；删除后 DB 行与磁盘文件均不存在，审计人/方法/路径/元数据正确，三项原有合成附件 ID/路径/大小/SHA 不变。

本轮 HTTP 与数据库证据见 [Chrome/DB 回归日志](delete-20261101-0c9dfbf4/logs/browser-delete-uat-retry.log)、[后端附件测试](delete-20261101-0c9dfbf4/logs/backend-attachment-tests.log)、[迁移日志](delete-20261101-0c9dfbf4/logs/migrate.log)、[Django check](delete-20261101-0c9dfbf4/logs/django-check.log)、[迁移一致性检查](delete-20261101-0c9dfbf4/logs/makemigrations-check.log)、[锁定 Python 环境与 pip check](delete-20261101-0c9dfbf4/logs/pip-lock-verification.log) 和 [窄屏替代附件截图诊断](delete-20261101-0c9dfbf4/logs/mobile-capture.log)。首次本轮流程尝试因 Vite 默认代理指向 8100、而隔离 Django 服务监听 8177，导致 UI 未加载合成跟进；该次在附件上传/删除前失败。将本轮 Vite 进程设为 `VITE_API_PROXY_PORT=8177` 后重跑通过；此为测试服务器配置错误，非产品/API 缺陷，原始日志见 [首次尝试](delete-20261101-0c9dfbf4/logs/browser-delete-uat.log)。本地运行未触发 GitHub Actions。

## 截图

- [桌面：选择待上传附件，1440×900](screenshots/desktop-pending-attachments-1440x900.png)
- [桌面：保存后刷新并重开，1440×900](screenshots/desktop-saved-reopened-1440x900.png)
- [桌面：UTF-8 修复前的真实乱码，1440×900](screenshots/desktop-preview-utf8-before-fix-1440x900.png)
- [桌面：UTF-8 修复后的真实预览，1440×900](screenshots/desktop-preview-text-1440x900.png)
- [桌面：另一轮修复后预览，1440×900](screenshots/desktop-preview-utf8-after-fix-1440x900.png)
- [窄屏：保存刷新后附件列表，390×844](screenshots/mobile-saved-refresh-390x844.png)
- [桌面：删除取消，目标仍保留，1440×900](delete-20261101-0c9dfbf4/screenshots/desktop-delete-cancelled-1440x900.png)
- [桌面：确认删除后的即时状态，1440×900](delete-20261101-0c9dfbf4/screenshots/desktop-delete-immediate-state-1440x900.png)
- [桌面：删除后刷新列表，1440×900](delete-20261101-0c9dfbf4/screenshots/desktop-delete-refresh-1440x900.png)
- [桌面：替代附件刷新后显示，1440×900](delete-20261101-0c9dfbf4/screenshots/desktop-replacement-refresh-1440x900.png)
- [窄屏：替代附件刷新后可见，390×844](delete-20261101-0c9dfbf4/screenshots/mobile-replacement-visible-390x844.png)

## 未覆盖与安全边界

- 本地隔离删除/替换流程已完成；本报告和分支仍等待 ChatGPT 独立审查，不能据此关闭 ISS-007。
- 本地应用层认证和权限已核实；生产 Nginx/CDN/对象存储/反向代理的直链和缓存 ACL 未测试，不能以本轮本地结果替代 ISS-017 部署安全验收。
- 未启用正式员工权限、未使用生产账号/数据库/媒体、未运行 PostgreSQL、未运行 GitHub CI、未合并 master、未部署、未关闭 Issue。

ISS-007 暂保留 `NEEDS_VERIFICATION`。本地删除/替换证据已补齐，下一步为独立审查；部署代理/对象存储 ACL 仍由 ISS-017 单独验收。
