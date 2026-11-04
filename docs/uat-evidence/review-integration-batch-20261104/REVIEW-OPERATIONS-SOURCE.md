# 运维来源只读预审

## 审查基线与范围

- 运维交付标识：`d289de36a3da3e4bd6531c812ec21a05f046d570`，父提交 `34f690655e11d5ba0eccf40021ea82662926ba35`。该提交本身只更新运维验收 README 和前端构建日志留档；运维实现来自其祖先并保留在当前集成历史中。
- 当前集成 HEAD：`319941c05e4682d80cd718f577514a39231fabfa`。该提交加入 `FinanceVoucher` 备份引用校验及两项测试；以下同时审查此跨包接通。
- 本文为只读开发侧预审。我未修改产品代码、运维代码、Issue 台账或来源提交。已执行既有运维 55 项及新增 voucher 引用 2 项测试；未连接 PostgreSQL、未执行真实 PG seed 备份/恢复、未验证生产代理或正式文件系统。

## 结论

**PASS（代码路径）**：应用没有 `/media/` 直出路由；运维备份检查 PostgreSQL 身份、登录角色、活动会话和 prepared transactions，锁定公开表并复核数据状态。全表 PG dump 和私有媒体树摘要都覆盖完整数据，但它们本身不证明数据库附件引用指向真实文件。

**PASS（新增引用逻辑的隔离测试） / NEEDS VERIFICATION（真实 PG seed）**：HEAD `319941c` 已把 `FinanceVoucher` 的 `file/size/sha256` 接入共享媒体引用检查；同一检查在备份和恢复路径都会执行。新增两项 SQLite 测试通过，但使用模拟连接，不证明真实 PostgreSQL 表/列查询和备份归档工作流。

**FIX REQUIRED（失败清理）**：PG 加密备份在最终 `.gpg` 路径写出密文后才解密验收；若后续解密或摘要验收失败，命令会返回失败，但没有清理本次创建的最终密文文件。

**BLOCKED / NEEDS VERIFICATION（部署环境）**：Linux 只读媒体文件系统全写入者验证、实际 Nginx/代理、正式 DB/OS 账号、密钥托管与保留凭据来源仍需目标环境验收。此前的 PG17 成功记录不覆盖本次新增 `FinanceVoucher` seed 路径。

## 媒体访问与 FinanceVoucher 私有文件

`MEDIA_URL` 配为 `/media/`，但 Django 根路由只挂 admin 与 `/api/`，没有 MEDIA_URL 静态服务路由；设置注释也明确不为 MEDIA_URL 加服务路由（`backend/config/urls.py:1-8`；`backend/config/settings.py:194-218`）。部署 Nginx 示例对 `/media` 和 `/media/` 都返回 404，API 代理关闭缓存（`docs/deployment/operations-nginx.conf.example:17-30`）。

`/api/media/<path>` 只按记录授权提供跟进附件、SKU 图片、产品证书和报价图片快照；它不接受 FinanceVoucher（`backend/crm/urls.py:57`；`backend/crm/file_access.py:14-67`）。财务凭证通过专用下载 action，ViewSet 先做财务访问检查，`ledger.voucher()` 重算文件大小和 SHA256，响应为附件且带 `private, no-store` 与 `nosniff`（`backend/crm/finance_closeout_api.py:75-85,142-148`；`backend/crm/services/finance_closeout.py:101-119`）。这证明应用代码有私有访问边界；Nginx 文件是模板，实际代理配置尚未运行验收。

`FinanceVoucher.file` 存于 `finance-vouchers/%Y/%m/`，数据库同时保存 `size` 与 `sha256`（`backend/crm/models.py:1998-2016`）。

## 全表数据库备份与附件引用检查

运维备份对 `public` schema 的所有表计算行数和行摘要，并使用 `pg_dump --format=custom` 导出数据库（`backend/crm/services/operations_postgres.py:79-96,171-186`）。独立的私有媒体 manifest 遍历整个媒体树，为实际存在的每个文件登记相对路径、字节数和 SHA256（`backend/crm/services/private_media.py:66-83`）。这两项可以覆盖整个数据库和媒体目录的原始字节，但**单独不能发现某行数据库 FileField 指向缺失文件**。

旧的固定引用检查只校验四类字段的路径存在：`crm_followupattachment.file`、`crm_sku.image`、`crm_productcertificate.file`、`crm_quoteitem.image_snapshot`；这些字段没有与媒体 manifest 比较数据库侧 size/hash（`backend/crm/services/operations_postgres.py:58-65`）。

当前集成 HEAD `319941c05e4682d80cd718f577514a39231fabfa` 已把新财务 voucher 接通：`verify_media_references()` 再查询 `crm_financevoucher(file,size,sha256)`，要求路径存在，且数据库 size/hash 与实存媒体 manifest 完全一致；缺文件、大小或摘要不同会拒绝（`backend/crm/services/operations_postgres.py:54-76`）。备份在导出前调用该函数并将引用数写入 manifest（`:177-198`）；恢复 PostgreSQL 后再次调用并比对引用数（`:255-258`）。因此 FinanceVoucher 文件字节由完整媒体 manifest 覆盖，数据库关系由新增引用校验补齐。

新增 `backend/crm/tests/test_review_finance_backup_references.py:1-24` 覆盖匹配凭证通过，以及引用缺失、size 不同、SHA 不同三种拒绝情况。测试用 `Mock` 代替数据库连接，没有真正执行 psycopg 查询，也没有跑完整 `MaintenanceBackup.backup/restore`。**最小剩余接通点**：在一次性 PG17 seed 中建立真实 FinanceVoucher 行及对应私有文件，验证同一 voucher 在真实备份与新库恢复两处计入 manifest；分别移除文件、改动实际字节或 DB size/SHA，确认备份拒绝且不发布最终归档，并确认恢复失败清理本次新库和媒体目录。此 PG seed 验收尚未执行。

## 数据库身份与写入者拒绝

`MaintenanceBackup` 要求明确 host/port/user/dbname，expected database 必须一致；应用身份需匹配完整 SHA 且 `backend/templates` 工作树干净。连接后再次核对数据库名、PostgreSQL system identifier 与 PG17 主版本；写入者门禁拒绝其他可登录角色、其他活动会话和未解决的 prepared transaction（`backend/crm/services/operations_postgres.py:99-140`）。备份锁定当时所有 public 表为 SHARE、固定导出快照，执行前后比对表/序列状态并重查写入者门禁（同文件 `:168-193`）。这是数据库写入者控制逻辑，不等于停止应用服务；依赖应用 DB 角色与维护账号分离，并在作业期间不开放维护凭据给其他写入者。

媒体栅栏要求 Linux、专用本地 ext4/xfs/btrfs、无子挂载，文件系统和挂载均只读（`backend/crm/services/operations_fence.py:13-39`）。运维验收 README 记录真实 PG17 表锁竞争、活动连接和其他登录角色拒绝已测；但媒体全写入者 Linux 专项明确 BLOCKED，Windows 环境默认拒绝。`pg_dump --no-owner --no-acl` 也不会还原目标角色/ACL，目标 DBA 需单独建角色并验证最小权限。此前 84 表/923 行的 PG17 结果属于原运维代码；不能代替新 FinanceVoucher PG seed 验收（`docs/uat-evidence/operations-readiness-batch-20261104/README.md` 及其 `maintenance-pg17-final.log`）。

## 加密、解密、保留与清理

`crypt_file()` 用显式 GnuPG 可执行文件、AES256、密钥 stdin、临时隔离 home/agent 和排他 `0600` 输出；解密后核对可信明文摘要，失败时仅删除本次创建且 inode 未变化的输出，并尝试终止隔离 agent（`backend/crm/services/operations_crypto.py:10-83`）。

PG 加密备份先在 `TemporaryDirectory` 创建明文 zip，再加密到最终 destination，最后从密文解密到临时 `verified.zip` 做摘要往返校验（`backend/operations_backup.py:42-62`）。临时明文和验收文件在上下文退出时清理；但如果第 60 行解密/摘要校验失败，最终 destination 已由第 59 行成功创建，外层只打印 FAILED，不清理该文件。可复现路径是加密成功后令第二次 GPG 解密失败或输出摘要不符；最终 `.gpg` 仍留在正式目标名下，后续目录运维可能误把失败物当成归档。**最小修复方向**：先把密文写入本次独占的临时名，完成解密验收后再用不覆盖的原子发布；失败只清理本次持有的临时输出。

单独的 `operations_archive.py decrypt` 是显式输出命令：解密成功会保留调用者指定的 plaintext destination；失败由 `crypt_file()` 清理本次输出（`backend/operations_archive.py:24-47`；`operations_crypto.py:65-82`）。这是有意交付明文文件的接口，不会自动擦除成功输出；运行手册需确保目标是受控私有暂存路径，并在恢复后执行明确清理。

保留工具默认 dry-run，只接受显式归档名称；要求 owner marker、每个待保留包摘要与独立副本摘要匹配、`restore_verified_sha256` 等于该包 SHA、保留数至少为 1，并在逐项删除前再次计算摘要；不触碰副本或未知文件（`backend/crm/services/operations_retention.py:9-55`）。它返回 `independent_failure_domain_verified=false`，不会把同机副本冒充异地容灾。凭据由 JSON 配置提供，代码只比较摘要字段，不验证凭据签名或自行证明成功恢复；RUNBOOK 将其交给受控恢复流程保管。部署验收应证明该恢复凭据确由真实解密/恢复成功流程生成且配置不可被普通运行账号伪造（`backend/operations_archive.py:17-46`；`docs/uat-evidence/operations-readiness-batch-20261104/RUNBOOK.md:55-59`）。

## 定向 SQLite 回归

执行既有运维 55 项测试，并加入新 FinanceVoucher 引用 2 项测试，共 **57 项：53 通过、0 失败、4 跳过**，Django system check 通过，退出码 0。环境为 Python **3.14.5**（本机 `.tmp/review-integration-python`）、`APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:`；没有连接 PostgreSQL。Django 输出 `Skipping setup of unused databases: default`，所以该组测试没有实际打开 SQLite 测试数据库，属于隔离单元测试结果，不构成数据库回归。该解释器也不是运维 README 所列锁定的 CPython 3.12.16。四项跳过均为当前 Windows 环境不支持的 POSIX 权限或符号链接测试。新增两项只用模拟连接验证 `verify_media_references()`，真实 PG SQL/备份/恢复留待上述 seed 验收。

原始测试输出：[operations-source-targeted-sqlite.txt](operations-source-targeted-sqlite.txt)。
