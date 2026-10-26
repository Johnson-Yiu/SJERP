# ISS-047｜单服务器私有文件存储验收记录

日期：2026-10-26
基线：`8b2b5c19e517addd9604b239211e199a789b739e`
分支：`codex/iss-047-private-storage`

## 结论

应用层已有的 ISS-017 私有媒体 API 保留并通过本轮定向回归；本轮补充了单服务器存储的 fail-fast 配置、持久目录与静态目录隔离、SHA256 媒体清单和 ISS-018 恢复校验接口。真实生产卷、Nginx/反向代理、容量告警和 PostgreSQL+媒体联合恢复未连接，全部保持 `DEPLOYMENT_VERIFICATION_PENDING`。

## 本地/隔离测试证据

测试使用 Django 测试数据库和临时可写媒体目录，不代表生产服务器安全验收。

| 场景 | 结果 | 证据 |
|---|---|---|
| 合法开发身份上传附件并读取受保护 URL | PASS | `BusinessFlowTests.test_follow_up_attachments_upload_and_context` + `test_functional_rbac.py` 私有附件回归 |
| 未登录/无模块权限/越客户范围读取 | PASS | ISS-017 定向 RBAC 测试 |
| 旧 `/media/` 静态路径 | PASS，404 | ISS-017 回归及本轮路径测试 |
| `../` 与编码路径穿越 | PASS，404 | `test_media_url_requires_record_module_and_customer_scope` |
| 开发/生产媒体目录隔离 | PASS，生产缺失或相对 `MEDIA_ROOT` 启动失败 | `test_database_settings.py` |
| 媒体目录与 `STATIC_ROOT` 重叠 | PASS，启动失败 | `test_media_root_cannot_overlap_static_root` |
| 模拟服务重启后读取文件 | PASS | `test_new_filesystem_storage_instance_reopens_file_after_restart_simulation` |
| 文件大小与 SHA256 完整性 | PASS | `test_manifest_is_relative_deterministic_and_sha256_verified` |
| 清单保存、恢复核对和篡改拒绝 | PASS | `test_management_command_can_write_and_verify_restore_manifest` |
| 符号链接越出媒体根目录 | PASS，清单拒绝 | `test_symlink_is_rejected_in_private_media_inventory`（不支持 symlink 的环境跳过） |

## 原始命令日志

```text
python manage.py test crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_media_url_requires_record_module_and_customer_scope crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_sku_and_historical_quote_images_use_protected_media_permissions crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_product_certificate_files_use_private_media_and_reject_external_urls crm.tests.test_functional_rbac.DevelopmentAccessCompatibilityTests.test_development_superadmin_can_read_protected_media_without_login crm.tests.test_sku_images --verbosity 1
Ran 7 tests ... OK

python manage.py test crm.tests.test_iss047_private_storage crm.tests.test_database_settings --verbosity 1
Ran 21 tests in 43.175s
OK (skipped=1)
（符号链接测试因当前 Windows 环境不支持创建 symlink 而跳过。）

python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations crm --check --dry-run
No changes detected in app 'crm'.

python manage.py test crm --verbosity 1
Ran 947 tests in 761.570s
OK (skipped=15)
System check identified no issues (0 silenced).

npm run test:unit
ℹ tests 154
ℹ pass 154
ℹ fail 0

npm run build -- --configLoader runner --outDir C:\\Users\\Johnson\\AppData\\Local\\Temp\\sunjack_iss047_dist
✓ built in 3.73s
（默认 dist 输出路径被托管 Worktree ACL 拒绝；改用临时可写输出目录，源码构建通过。）
```

全量测试期间使用临时可写 `MEDIA_ROOT`，未修改生产目录。测试输出中的 Bad Request/Internal Server Error 是既有测试主动覆盖的拒绝、回滚和异常路径，最终结果为 `OK`。这里不把未执行的生产卷、Nginx 或 PostgreSQL 结果写成 PASS。

## 截图边界

本任务没有修改前端页面。应用层附件页面的桌面/390px Chrome Use 截图沿用 [`ISS-017 私有附件验收`](../iss-017-private-files/README.md) 的真实证据：[`桌面截图`](../iss-017-private-files/certificate-desktop.png)、[`390px 窄屏截图`](../iss-017-private-files/certificate-narrow.png)。本轮尝试以 Chrome Use 打开本 Worktree 的 `http://127.0.0.1:5193/product-certificates`，但 Vite 依赖优化和 `dist` 输出均被托管 Worktree ACL 拒绝，页面未形成可用视觉证据，因此本轮浏览器状态记为 `BROWSER_PENDING`，不把白屏或其他分支页面当作通过。真实目标环境截图待运维部署验证后补充。

## 交付边界

未部署、未修改真实生产服务器、未合并 `master`、未关闭 ISS-047。最终提交 SHA 以本分支 Git HEAD 和交付消息为准。
