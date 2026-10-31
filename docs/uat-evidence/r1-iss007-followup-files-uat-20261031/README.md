# R1-ISS007-FOLLOWUP-ATTACHMENT-UAT

本报告记录固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 上的跟进附件隔离验收。分支为 `codex/r1-iss007-followup-files-uat-20261031`。

## 当前结论

真实 Chrome 已完成隔离数据下的上传、保存、刷新重开、预览、下载、授权/拒绝直链访问及文件/数据库/审计核对。验收发现 UTF-8 纯文本预览未声明字符集，中文乱码；已最小修复并在 Chrome 中复验正常。删除/替换步骤尚未执行：它会删除本轮上传的 `ISS007-delete-target.txt` 合成附件，正等待用户在执行时确认。因此本轮当前仍为 `NEEDS_VERIFICATION`，不得据此宣称删除流程已通过或关闭 ISS-007。

## 隔离边界与身份

- 后端使用全新 SQLite 数据库和独立临时 `MEDIA_ROOT`；未连接或改动生产数据库、真实业务记录或生产媒体目录。
- 合成客户、跟进、历史附件和两名真实认证测试用户均只存在于临时库。获授权操作人是 `iss007-uat-operator`（普通非超级用户）；拒绝用账号是 `iss007-uat-no-permission`。所有上传操作日志均关联前者，不使用开发超级管理员身份。报告不保存临时密码。
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
| 取消删除 | 尚未执行。只会在获用户当次确认后，删除一次性合成附件 `ISS007-delete-target.txt`，再核对数据库、文件、日志及刷新后的页面。 |

### 上传后数据库与文件核对

| ID | 文件 | DB 相对路径 | DB/磁盘字节 | SHA256 |
|---:|---|---|---:|---|
| 1 | `ISS007-legacy-history.txt` | `follow-up-attachments/2024/01/ISS007-legacy-history.txt` | 33 / 33 | `70390a1960a419faa0c75674f14d5d50ba9d96274cdf46e386208bf585af9af3` |
| 2 | `ISS007-preview.txt` | `follow-up-attachments/2026/10/ISS007-preview.txt` | 64 / 64 | `ee61d0bbe02c4a7b96f8b8a8057547583c98aab8089e643de00047ca3f976410` |
| 3 | `ISS007-download.bin` | `follow-up-attachments/2026/10/ISS007-download.bin` | 8 / 8 | `5e62a906ba05040729ff6e2b3e3f7d744671a3c64f375cc2159b29483ed29bc1` |
| 4 | `ISS007-delete-target.txt` | `follow-up-attachments/2026/10/ISS007-delete-target.txt` | 32 / 32 | `9e1d7b72cf92759290d760a4ebfc58980c819b24f9ea133b0df2d5678cf3e8fc` |

上传操作审计为 `POST /api/follow-ups/1/attachments/`，标签“上传跟进附件”，元数据包含 ID `[2,3,4]` 与上述 3 个名称。无文件正文或密码写入审计。删除审计及删除后文件一致性将在确认并执行后补记。

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

相关 Playwright 行为与每次 HTTP 状态输出见上文及浏览器日志：上传 201、历史/新附件读取 200、匿名 403、无权限 404、旧静态路径 404。后续删除阶段未运行。

## 截图

- [桌面：选择待上传附件，1440×900](screenshots/desktop-pending-attachments-1440x900.png)
- [桌面：保存后刷新并重开，1440×900](screenshots/desktop-saved-reopened-1440x900.png)
- [桌面：UTF-8 修复前的真实乱码，1440×900](screenshots/desktop-preview-utf8-before-fix-1440x900.png)
- [桌面：UTF-8 修复后的真实预览，1440×900](screenshots/desktop-preview-text-1440x900.png)
- [桌面：另一轮修复后预览，1440×900](screenshots/desktop-preview-utf8-after-fix-1440x900.png)
- [窄屏：保存刷新后附件列表，390×844](screenshots/mobile-saved-refresh-390x844.png)

## 未覆盖与安全边界

- 删除/替换和删除后的刷新状态等待用户对隔离合成文件 `ISS007-delete-target.txt` 的当次确认；未确认前未触发 DELETE，也未删除文件或数据库行。
- 本地应用层认证和权限已核实；生产 Nginx/CDN/对象存储/反向代理的直链和缓存 ACL 未测试，不能以本轮本地结果替代 ISS-017 部署安全验收。
- 未启用正式员工权限、未使用生产账号/数据库/媒体、未运行 PostgreSQL、未运行 GitHub CI、未合并 master、未部署、未关闭 Issue。

ISS-007 暂保留 `NEEDS_VERIFICATION`。后续先完成经确认的合成附件删除/刷新/数据库/文件/审计核对，再等待独立审查。
