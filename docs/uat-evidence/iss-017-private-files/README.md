# ISS-017：ERP 附件私有化与业务权限验收

日期：2026-10-24

分支：`codex/iss-017-private-files`

基线：`71ec4a4c2d860b9944624a1434d9d7580e9a6d38`

本记录对应的实现提交：以交付消息中的最终 SHA 为准。

## 结论

应用代码层已将跟进附件、报价商品图片快照、SKU 图片、SKU 缩略图和产品证书文件收口到认证 API；未登录、无对应模块权限和越客户范围的文件请求不会得到文件内容。产品证书不再接受或返回外部 `http(s)` 文件链接，旧数据中的外部链接只保留为不可展示的遗留字段。

ISS-017 仍不能标记为生产安全通过：仓库没有目标环境的 Nginx、CDN、对象存储或反向代理 ACL 配置，未连接生产环境，因而不能证明部署后的 `/media/`、对象存储直链、CDN 缓存链接一定不会绕过应用权限。没有部署、没有公开 media 目录，也没有生成游客分享链接。

## 权限矩阵

| 文件/凭证类型 | 读取入口 | 必需权限 | 数据范围 | 缓存/直链结论 |
|---|---|---|---|---|
| 跟进附件 | `/api/media/<path>` | 登录 + `followups.view` | 跟进所属客户范围 | `private, no-store`；未授权返回 404 |
| 报价商品图片快照 | `/api/media/<path>` | 登录 + `quotes.view` + `skus.view` | 报价所属客户范围 | `private, no-store`；不走静态 `/media/` |
| SKU 原图 | `/api/media/<path>` | 登录 + `skus.view` | 共享产品/SKU 模块范围 | `private, no-store`；不暴露 FileField URL |
| SKU 缩略图 | `/api/skus/<id>/thumbnail/` | 登录 + `skus.view` | SKU 记录权限 | 响应 `private, no-store`；仍经过 ViewSet 权限 |
| 产品证书文件 | `/api/media/<path>` | 登录 + `certificates.view`；产品名称等关联字段仍按 `products.view` 脱敏 | 共享证书模块；不返回客户财务数据 | `private, no-store`；新建/更新只接受 ERP 私有上传 |
| 银行凭证 | `/api/rmb-cash-events/` 及详情 | 资金事件既有权限与可见范围 | 当前模型只有凭证引用、SHA256 和核实说明，没有可下载的文件字段或文件 URL | 不存在游客文件入口；文本/哈希随受控资金 API 返回 |

实现位置：`backend/crm/file_access.py`、`backend/crm/serializers.py`、`backend/crm/models.py`、`backend/crm/services/sku_images.py`、`backend/crm/migrations/0081_product_certificate_private_file.py`。前端证书上传和安全 URL 辅助见 `frontend/src/views/ResourcePage.vue`、`frontend/src/resourceConfigs.js`、`frontend/src/utils/certificateFile.js`。

## 原始 API/权限证据

测试方法是 Django `APIClient` + 临时 `MEDIA_ROOT`，文件内容为合成字节 `certificate bytes`，不连接生产数据库或生产文件存储。

来源：`backend/crm/tests/test_functional_rbac.py` 中 `test_product_certificate_files_use_private_media_and_reject_external_urls`。

| 场景 | 实际结果 |
|---|---|
| 未登录请求证书私有路径 `/api/media/product-certificates/...` | `403` |
| 未登录请求旧静态路径 `/media/product-certificates/...` | `404`，未发现 Django 静态绕过 |
| 有 `certificates.view` 的用户读取列表 | `200`；`file_url` 仅为 `/api/media/...`，响应中不含 `official.example` |
| 有 `certificates.view` 的用户读取文件 | `200`，正文为合成的 `certificate bytes` |
| 合法文件响应缓存头 | `Cache-Control: private, no-store`；同时设置 `X-Content-Type-Options: nosniff` |
| 只有 `products.view`、没有 `certificates.view` 的用户读取证书列表 | `403` |
| 同一无证书权限用户直接请求已知私有文件路径 | `404`，不泄露文件存在性 |
| 旧记录仅有外部 `file_url` | API 返回 `file_url: ""`，不把官网 URL 继续传播 |
| 新 API 提交 `file_url=https://official.example/new.pdf` | `400`，错误为“证书文件必须上传到 ERP 私有存储，不接受外部链接。” |

已有文件类型的同一组 RBAC 回归还覆盖了跟进附件、报价图片、SKU 图片和客户范围；本轮定向命令结果为 **68 tests OK**。

## 浏览器与自动回归

### Chrome Use 实测

Chrome Use 实际打开独立 worktree 的 `http://127.0.0.1:5192/product-certificates`，页面和表单均可见：

- 列表辅助文案：证书文件上传后仅通过 ERP 权限访问，不生成公开链接。
- 新建表单提示：证书文件必须上传到 ERP 私有存储；查看和下载均需当前证书权限。
- 文件控件为“选择文件”，没有可填写的外部 URL 输入框。

该页面使用开发环境身份，这是仓库 `AGENTS.md` 约定的服务端开发超级管理员，不代表正式员工账号或生产 RBAC 验收。

### Chrome 通道 Playwright

回归命令（固定指向 ISS-017 独立 worktree 的 5192 端口，避免复用其他 worktree）：

```text
$env:PLAYWRIGHT_CHANNEL='chrome'; npx playwright test browser-tests/certificates-hs-ux.spec.js --config=playwright.iss017.config.js
13 passed (49.2s)
```

覆盖 1440、1280、1024 和 390px；还覆盖证书旧链接不生成 `javascript:` 链接、只读权限、加载失败重试、保存中阻止重复提交/关闭/导航、后端拒绝后保留输入和刷新 URL 恢复。`frontend/playwright.iss017.config.js` 固定指向 5192，正式 `frontend/playwright.config.js` 未改。

截图使用合成 fixture 并由 Chrome 通道生成：

- [桌面证书私有上传表单](certificate-desktop.png)
- [390px 窄屏证书私有上传表单](certificate-narrow.png)

截图只证明当前前端布局和文案，不证明生产对象存储或代理 ACL。

## 验证命令日志

```text
python manage.py test crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_product_certificate_files_use_private_media_and_reject_external_urls crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_media_url_requires_record_module_and_customer_scope crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_sku_and_historical_quote_images_use_protected_media_permissions crm.tests.test_sku_images crm.tests.test_quotes --keepdb
Ran 68 tests ... OK

python manage.py makemigrations crm --check --dry-run
No changes detected in app 'crm'

npx vitest run tests/certificates-hs-ux.spec.js --environment jsdom
Test Files 1 passed; Tests 8 passed

npm run build
Vite build succeeded; 2009 modules transformed

PLAYWRIGHT_CHANNEL=chrome ... --config=playwright.iss017.config.js
13 passed (49.2s)
```

构建有既有的 chunk 大小提示；不影响本次私有附件回归。`npm run test` 在仓库当前 package script 中不存在，已改用实际存在的 `test:unit`/Vitest 入口；`test:unit` 的 Node 直接加载 `.vue` 限制不是本次修复引入，定向 Vitest 和 Chrome 回归均通过。

## 部署边界与待验证项

仓库扫描只找到 Django `MEDIA_URL=/media/`、`MEDIA_ROOT=BASE_DIR / "media"` 和 `/api/media/<path>` 受保护入口；没有目标环境 Nginx、Caddy、Traefik、CDN 或对象存储配置。当前本地 API 测试不能冒充生产安全验收，因此以下项目仍待运维/安全负责人在隔离部署环境完成：

1. 禁止 Web 服务器直接公开本地 `media` 目录，并检查历史缓存和 CDN 回源规则。
2. 对对象存储 bucket、CDN、反向代理和应用部署分别用未登录、跨客户无权、过期/旧缓存 URL 做实测。
3. 确认不会生成游客公开分享链接，也不会把 ERP 文件直接同步到官网公开目录。
4. 清理或迁移历史 `ProductCertificate.file_url` 外部值，并由业务负责人确认官网链接策略。

本分支未部署、未修改 Nginx/代理、未合并 master、未关闭 Issue。
