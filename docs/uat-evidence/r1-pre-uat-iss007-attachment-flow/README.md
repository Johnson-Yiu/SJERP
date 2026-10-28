# R1-PRE-UAT-ISS007 附件流程验收

日期：2026-10-29  
基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`  
分支：`codex/pre-uat-iss007-attachment-flow`

## 验收环境

- 独立 checkout：`D:/Codex项目/森爵照明管理系统/.worktrees/r1-pre-uat-iss007-attachment-flow`
- Django：一次性 SQLite，数据库位于 `.tmp/r1-pre-uat-iss007/db.sqlite3`
- 文件：独立 `MEDIA_ROOT`，位于 `.tmp/r1-pre-uat-iss007/media`
- 数据：`seed_isolated.py` 生成的合成客户、跟进、产品、SKU、报价和报价图片快照
- Chrome：真实 Chrome channel，Vite `55208`，Django API `55207`
- 开发身份仅用于本地授权业务流程；未连接生产数据库，未开启正式 RBAC

## 结果

### 业务流程

| 场景 | 结果 | 证据 |
| --- | --- | --- |
| 客户跟进附件上传、保存、再次打开 | PASS | [follow-up-pending-desktop.png](screenshots/follow-up-pending-desktop.png)、[follow-up-saved-desktop.png](screenshots/follow-up-saved-desktop.png)、[follow-up-saved-390.png](screenshots/follow-up-saved-390.png) |
| 跟进附件授权查看 | PASS，HTTP 200 | [http-results.json](http-results.json) |
| SKU 图片更换、预览 | PASS | [sku-image-preview-desktop.png](screenshots/sku-image-preview-desktop.png) |
| SKU 缩略图 | PASS，HTTP 200，`image/webp` | [http-results.json](http-results.json) |
| 报价历史图片快照不受 SKU 更换影响 | PASS，替换前后 SHA256 相同 | [quote-image-snapshot-desktop.png](screenshots/quote-image-snapshot-desktop.png)、[quote-image-snapshot-390.png](screenshots/quote-image-snapshot-390.png) |
| 上传失败提示与重试 | PASS，弹窗保留、待上传附件保留，重试只补传附件 | [follow-up-upload-failure.png](screenshots/follow-up-upload-failure.png)、[follow-up-upload-retry-success.png](screenshots/follow-up-upload-retry-success.png) |

初次基线运行复现：附件请求中断后，弹窗关闭且没有重试控制。最小修复后，真实 Chrome 结果为 `dialogCountAfterFailure=1`、`retryControlVisible=true`，第二次保存成功并可再次打开附件。未重新创建跟进记录。

### HTTP 与 SHA256

最终真实 Chrome 结果保存在 [http-results.json](http-results.json)：

- 跟进附件授权查看：`200`，38 bytes，SHA256 `59b310c7b5d102444d8e412ba33c40dee4b3b1bfbec3c04cec968c2cd121d755`
- SKU 替换图片：`200`，`image/gif`，43 bytes，SHA256 `ff95b99e6cd933dc1ce0dfc57ce7d4f78577e094ba87381f2edfba2a4690a7c6`
- SKU 缩略图：`200`，`image/webp`，72 bytes，SHA256 `460f90062e82b17cd8b97bb45454c729554bd90fbc06b75f26ab63d855348d9d`
- 报价历史图片：`200`，`image/png`，68 bytes，SHA256 `431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460`
- 本地 MEDIA_ROOT 中的同一报价快照与 SKU 初始图片 SHA256 均为 `431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460`，替换后的 SKU 图片为 `ff95b99e6cd933dc1ce0dfc57ce7d4f78577e094ba87381f2edfba2a4690a7c6`。

## 安全拒绝与权限

已有后端测试覆盖私有媒体 API：

- `test_media_url_requires_record_module_and_customer_scope`：匿名访问 `403`；有权用户 `200`；其他客户员工 `404`；模块权限撤销后 `404`；公共 `/media/`、目录穿越路径均 `404`。
- `test_sku_and_historical_quote_images_use_protected_media_permissions`：有权用户可查看 SKU 与历史报价图片；仅有 SKU 权限的用户不能查看报价快照；无关客户用户和撤销报价权限后均 `404`；公共媒体路径 `404`。

本地开发服务器按项目约定保留开发超级管理员身份，因此匿名/受限账号拒绝路径通过 Django RBAC 测试验证，不把开发身份的浏览器结果冒充生产权限验收。

## 自动化命令

后端：

```text
python manage.py test crm.tests.test_customer_h1 crm.tests.test_functional_rbac crm.tests.test_sku_images crm.tests.test_quotes --verbosity 1
Ran 127 tests ... OK
```

前端：

```text
npx --no-install vitest run tests/follow-up-safety.spec.js tests/follow-up-richtext-and-attachments.spec.js tests/crm-saving.spec.js tests/unsaved-changes.spec.js --environment jsdom --reporter=dot
4 files passed, 47 tests passed

npm run build -- --outDir .tmp/r1-pre-uat-iss007/frontend-dist
2018 modules transformed; build succeeded
```

真实 Chrome：

```text
npx --no-install playwright test browser-tests/iss007-attachment-real.spec.js --config=playwright.iss007.config.js
3 passed (23.0s)
```

迁移：一次性 SQLite 已从基线完整迁移至 0089；本任务未新增迁移，也未修改生产存储策略。

## 本轮改动

- `frontend/src/views/ResourcePage.vue`：跟进主记录保存成功但附件上传失败时，保留编辑弹窗和待上传文件，显示持久错误提示；重试时更新已保存跟进并只上传附件。
- `frontend/tests/follow-up-safety.spec.js`：覆盖附件失败、重试和避免重复创建。
- `backend/crm/tests/test_customer_h1.py`：覆盖 multipart 上传、中文文件名、文件字节与数据库引用一致性、空上传拒绝。
- `frontend/browser-tests/iss007-attachment-real.spec.js`、`frontend/playwright.iss007.config.js`：真实 Chrome 验收脚本。
- `seed_isolated.py`：一次性隔离测试数据。

## 遗留事项

- `DEPLOYMENT_VERIFICATION_PENDING`：ISS-017/047 所述生产 Nginx、持久卷、重启后的真实服务链路和容量告警未在本轮验证；本任务未连接或修改生产环境。
- 网络中断使用 Playwright route abort 模拟，真实代理/客户端超时链路仍需部署环境验收。
- 未修改共享 `PROJECT_ISSUES.md` / `PROJECT_PHASES.md`，符合本任务“不得修改共享 Issue 台账”的限制。

最终 GitHub 分支 HEAD 以本次交付报告及远端分支核验为准；本 README 不复制自引用 SHA。
