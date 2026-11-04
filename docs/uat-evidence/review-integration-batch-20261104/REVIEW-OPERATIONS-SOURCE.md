# 运维来源只读预审

## 审查基线与范围

- 运维交付标识：`d289de36a3da3e4bd6531c812ec21a05f046d570`，父提交 `34f690655e11d5ba0eccf40021ea82662926ba35`。该提交本身只更新运维验收 README 和前端构建日志留档；运维实现来自其祖先并保留在当前集成历史中。
- 财务跨包实现初审提交：`319941c05e4682d80cd718f577514a39231fabfa`。本次综合 PG 验收固定源码 SHA：`1f189c3f74fda2908620dd3860230d860f1cbb43`。
- 本报告先前为只读开发侧预审。按后续明确授权，工作树包含未提交的最小补修：`backend/operations_backup.py` 与 `backend/crm/tests/test_operations_backup.py`；本轮补充只更新本报告，没有改源码或测试。综合 PG/GPG 实测结果见下文及对应原始日志。

## 结论

**PASS（代码路径）**：应用没有 `/media/` 直出路由；运维备份检查 PostgreSQL 身份、登录角色、活动会话和 prepared transactions，锁定公开表并复核数据状态。全表 PG dump 和私有媒体树摘要都覆盖完整数据，但它们本身不证明数据库附件引用指向真实文件。

**PASS（FinanceVoucher 真实 PG seed 备份恢复）**：`1f189c3f74fda2908620dd3860230d860f1cbb43` 的隔离 PostgreSQL 17 全量验收将财务/历史新表、序列及凭证文件纳入归档；恢复后 finance/history 清单与来源一致，媒体 4 个文件的 SHA/size 一致，源媒体未变化，清理完成。此前 Mock 引用单测仅为逻辑级证据；本次 PG 恢复结果覆盖真实数据库 SQL 与归档路径。

**PASS（真实 GPG 发布与损坏拒绝）**：使用保留的合成 PG 归档验证新正式名发布流程，真实 GPG 往返成功；实际损坏归档在发布前被拒绝，来源不变且清理完成。该 2/2 结果没有重新验证 Linux 只读维护门禁。

**NEEDS VERIFICATION（目标环境）**：Linux 只读媒体文件系统的全写入者门禁、实际 Nginx/代理、正式 DB/OS 账号与 ACL、密钥托管，以及保留凭据生成和防伪来源仍待目标环境验收。此次 PG/GPG 结果来自隔离合成环境，不等于真实维护主机/文件系统/凭据部署通过。

## 媒体访问与 FinanceVoucher 私有文件

`MEDIA_URL` 配为 `/media/`，但 Django 根路由只挂 admin 与 `/api/`，没有 MEDIA_URL 静态服务路由；设置注释也明确不为 MEDIA_URL 加服务路由（`backend/config/urls.py:1-8`；`backend/config/settings.py:194-218`）。部署 Nginx 示例对 `/media` 和 `/media/` 都返回 404，API 代理关闭缓存（`docs/deployment/operations-nginx.conf.example:17-30`）。

`/api/media/<path>` 只按记录授权提供跟进附件、SKU 图片、产品证书和报价图片快照；它不接受 FinanceVoucher（`backend/crm/urls.py:57`；`backend/crm/file_access.py:14-67`）。财务凭证通过专用下载 action，ViewSet 先做财务访问检查，`ledger.voucher()` 重算文件大小和 SHA256，响应为附件且带 `private, no-store` 与 `nosniff`（`backend/crm/finance_closeout_api.py:75-85,142-148`；`backend/crm/services/finance_closeout.py:101-119`）。这证明应用代码有私有访问边界；Nginx 文件是模板，实际代理配置尚未运行验收。

`FinanceVoucher.file` 存于 `finance-vouchers/%Y/%m/`，数据库同时保存 `size` 与 `sha256`（`backend/crm/models.py:1998-2016`）。

## 全表数据库备份与附件引用检查

运维备份对 `public` schema 的所有表计算行数和行摘要，并使用 `pg_dump --format=custom` 导出数据库（`backend/crm/services/operations_postgres.py:79-96,171-186`）。独立的私有媒体 manifest 遍历整个媒体树，为实际存在的每个文件登记相对路径、字节数和 SHA256（`backend/crm/services/private_media.py:66-83`）。这两项可以覆盖整个数据库和媒体目录的原始字节，但**单独不能发现某行数据库 FileField 指向缺失文件**。

旧的固定引用检查只校验四类字段的路径存在：`crm_followupattachment.file`、`crm_sku.image`、`crm_productcertificate.file`、`crm_quoteitem.image_snapshot`；这些字段没有与媒体 manifest 比较数据库侧 size/hash（`backend/crm/services/operations_postgres.py:58-65`）。

当前集成 HEAD `319941c05e4682d80cd718f577514a39231fabfa` 已把新财务 voucher 接通：`verify_media_references()` 再查询 `crm_financevoucher(file,size,sha256)`，要求路径存在，且数据库 size/hash 与实存媒体 manifest 完全一致；缺文件、大小或摘要不同会拒绝（`backend/crm/services/operations_postgres.py:54-76`）。备份在导出前调用该函数并将引用数写入 manifest（`:177-198`）；恢复 PostgreSQL 后再次调用并比对引用数（`:255-258`）。因此 FinanceVoucher 文件字节由完整媒体 manifest 覆盖，数据库关系由新增引用校验补齐。

新增 `backend/crm/tests/test_review_finance_backup_references.py:1-24` 覆盖匹配凭证通过，以及引用缺失、size 不同、SHA 不同三种拒绝情况。测试用 `Mock` 代替数据库连接，真实数据库覆盖由后续 PG 验收补足：在全量源/恢复快照中，99 张表、1081 行、128 项迁移和 4 个媒体文件恢复一致，包含 history/finance 新表、序列及凭证 SHA；来源未变化且 cleanup complete。证据：`logs/postgres-full-all-sources-1f189c3.log`、`artifacts/postgres-backups/1f189c3f74fd-0edd1427.json`、`artifacts/postgres-backups/finance-restored-1f189c3f74fd.json`。该实测未替代 Linux 只读媒体栅栏的部署验收。

## 数据库身份与写入者拒绝

`MaintenanceBackup` 要求明确 host/port/user/dbname，expected database 必须一致；应用身份需匹配完整 SHA 且 `backend/templates` 工作树干净。连接后再次核对数据库名、PostgreSQL system identifier 与 PG17 主版本；写入者门禁拒绝其他可登录角色、其他活动会话和未解决的 prepared transaction（`backend/crm/services/operations_postgres.py:99-140`）。备份锁定当时所有 public 表为 SHARE、固定导出快照，执行前后比对表/序列状态并重查写入者门禁（同文件 `:168-193`）。这是数据库写入者控制逻辑，不等于停止应用服务；依赖应用 DB 角色与维护账号分离，并在作业期间不开放维护凭据给其他写入者。

媒体栅栏要求 Linux、专用本地 ext4/xfs/btrfs、无子挂载，文件系统和挂载均只读（`backend/crm/services/operations_fence.py:13-39`）。本次 PG 全量验收通过了隔离数据库备份/恢复与 FinanceVoucher 引用；Linux 只读媒体文件系统全写入者门禁没有因本次 PG/GPG 实测而重新验收。Windows 环境默认拒绝该门禁。`pg_dump --no-owner --no-acl` 也不会还原目标角色/ACL，目标 DBA 需单独建角色并验证最小权限（`docs/uat-evidence/operations-readiness-batch-20261104/README.md` 及其 `maintenance-pg17-final.log`）。

## 加密、解密、保留与清理

`crypt_file()` 用显式 GnuPG 可执行文件、AES256、密钥 stdin、临时隔离 home/agent 和排他 `0600` 输出；解密后核对可信明文摘要，失败时仅删除本次创建且 inode 未变化的输出，并尝试终止隔离 agent（`backend/crm/services/operations_crypto.py:10-83`）。

修前故障已由新增测试复现：加密成功后令第二次解密失败或明文摘要不符，CLI 返回 FAILED，但旧逻辑仍将未通过往返验收的密文留在正式 `.gpg` 名下。旧目标已存在时，旧逻辑也先启动备份流程，再由加密工具拒绝覆盖。

当前未提交补修位于 `backend/operations_backup.py`：`_encrypted_backup()` 在正式目标目录生成 `.sunjack-encrypted-<uuid>.partial`，`crypt_file()` 以排他创建该密文；完成解密摘要复核且临时明文目录退出后，使用同目录 `os.link(..., follow_symlinks=False)` 以原子不覆盖方式创建正式名，再清除临时硬链接。目标已存在时在备份启动前拒绝；若另一个进程在校验期间创建目标，硬链接发布失败并保留既有目标。失败清理先比较设备号和 inode，只移除本次建立且身份未改变的暂存文件；若身份改变则拒绝删除。该文件系统方案依赖目标文件系统支持硬链接，能力不足时会失败关闭，不会退回覆盖式 rename。

故障注入位于 `backend/crm/tests/test_operations_backup.py`，覆盖解密失败、解密摘要不符、已有目标预检、正式发布瞬间出现竞争目标、临时名碰撞不删他人文件，以及成功复核后发布。修前日志显示 4 项中 3 项失败、1 项通过；两个主要失败都观察到正式目标残留。修后最终冻结测试文件为 6 项全通过（原审阅的 5 项后增加了正式目标竞争创建场景）。

权限和介质边界：临时密文与最终包位于同一配置备份目录，隐藏文件名不是 ACL；目录访问控制、Windows NTFS ACL/服务账号、目标卷硬链接能力、GPG 可执行文件和密钥隔离仍需部署验收。明文 zip 与 `verified.zip` 使用系统 `TemporaryDirectory` 并在退出时由运行时清理；这不等于安全擦除，也未证明临时目录 ACL 符合正式环境要求。若临时密文 unlink 失败，CLI 仍返回已验证归档并在结果中给出 `staging_ciphertext_cleanup_warning`；运维需处理留存的加密临时副本。

使用保留的合成 PG 归档执行真实 GPG 加密发布验收 **2/2 通过**：真实往返成功；实际损坏归档被拒绝且未发布正式名；源归档未变化，临时资源清理完成。该日志明确标注输入是保留的合成 PG 归档，并非重新运行维护门禁或新建备份快照。证据：[real-gpg-publication-1f189c3.log](logs/real-gpg-publication-1f189c3.log)。

恢复后私有凭证 HTTP 验收依次得到未授权拒绝 **403**、无权访问拒绝 **403**、有权下载 **200** 且返回实际 67 bytes 并带 `private, no-store`；`/media/finance-vouchers/...` 直读返回 **404**。证据：[restored-private-http-1f189c3f74fd.log](logs/restored-private-http-1f189c3f74fd.log)。这是隔离恢复环境的应用层行为，不替代目标反向代理配置验收。

单独的 `operations_archive.py decrypt` 是显式输出命令：解密成功会保留调用者指定的 plaintext destination；失败由 `crypt_file()` 清理本次输出（`backend/operations_archive.py:24-47`；`operations_crypto.py:65-82`）。这是有意交付明文文件的接口，不会自动擦除成功输出；运行手册需确保目标是受控私有暂存路径，并在恢复后执行明确清理。

保留工具默认 dry-run，只接受显式归档名称；要求 owner marker、每个待保留包摘要与独立副本摘要匹配、`restore_verified_sha256` 等于该包 SHA、保留数至少为 1，并在逐项删除前再次计算摘要；不触碰副本或未知文件（`backend/crm/services/operations_retention.py:9-55`）。它返回 `independent_failure_domain_verified=false`，不会把同机副本冒充异地容灾。凭据由 JSON 配置提供，代码只比较摘要字段，不验证凭据签名或自行证明成功恢复；RUNBOOK 将其交给受控恢复流程保管。部署验收应证明该恢复凭据确由真实解密/恢复成功流程生成且配置不可被普通运行账号伪造（`backend/operations_archive.py:17-46`；`docs/uat-evidence/operations-readiness-batch-20261104/RUNBOOK.md:55-59`）。

## 定向 SQLite 回归

此前 Windows 隔离运维定向集：**63 项，59 通过、0 失败、4 跳过**，Django system check 通过，退出码 0。Python **3.14.5**（本机 `.tmp/review-integration-python`），`APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:`；Django 输出 `Skipping setup of unused databases: default`，该组没有打开 SQLite 测试数据库。4 项跳过为 Windows 环境不支持的 POSIX 权限或符号链接场景。该单元集结果与以下真实 PG17 全量回归分开记录。

**真实 PostgreSQL 17 全量回归 PASS**：`1f189c3f74fda2908620dd3860230d860f1cbb43`，1312 项中 **1282 通过、0 失败、30 跳过**，1008.032 秒；恢复核对 99 张表、1081 行、128 项迁移及 4 个媒体文件，history/finance 新表、序列和 FinanceVoucher SHA 与来源一致，源未变，cleanup complete。Django/PG 工具版本为日志所示 PostgreSQL 17.11。原始日志：[postgres-full-all-sources-1f189c3.log](logs/postgres-full-all-sources-1f189c3.log)；归档与校验记录：[1f189c3f74fd-0edd1427.json](artifacts/postgres-backups/1f189c3f74fd-0edd1427.json)、[finance-restored-1f189c3f74fd.json](artifacts/postgres-backups/finance-restored-1f189c3f74fd.json)。

加密发布专测修前 **4 项：1 通过、3 失败**，原始日志：[operations-backup-publication-pre-fix.log](logs/operations-backup-publication-pre-fix.log)。修后冻结版本 **6 项：6 通过、0 失败、0 跳过**：[operations-backup-publication-post-fix.log](logs/operations-backup-publication-post-fix.log)。运维相关合并定向集 **63 项：59 通过、0 失败、4 跳过**：[operations-source-targeted-post-fix.log](logs/operations-source-targeted-post-fix.log)。此外真实 GPG 发布/损坏拒绝 2/2 通过，见上文独立日志。PG/GPG 结果均为隔离合成验收；本报告没有记录新的最终 CI 结果。

原始旧运维/Voucher 测试输出：[operations-source-targeted-sqlite.txt](operations-source-targeted-sqlite.txt)。

## 冻结与提交状态

产品文件及测试已冻结。PG17 全量与真实 GPG 合成验收已按上述 SHA 完成；Linux 维护文件系统门禁、目标代理/ACL/身份/密钥与保留凭据部署条件仍需单独验收。本报告只更新实际证据，不推断未提供的最终 CI 结果。

## 交付前CI更新

代码1f189c3的CI41829100528最终为Backend/PG成功、Frontend失败（ISS039快照子进程2项）。已保留原始失败证据并最小补修有界输出缓冲/诊断；大快照2/2、受影响Chrome2/2和Node179/179通过，原全库/业务/权限断言保留。最终完整前端与精确SHA三CI见统一交付回执，本文各早期运行中/待验句仅保留当时状态，不是当前通过声明。后端全量1312项SQLite/PG均无失败，PG额外8命令专项8/8；未关闭Issue或替代ChatGPT独立复审。
