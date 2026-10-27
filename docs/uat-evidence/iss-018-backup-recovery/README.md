# ISS-018｜数据库与附件一致性备份恢复隔离演练

日期：2026-10-27

基线：`7951ecb8c6196f773128ad5978bfcd0a5b30c6b5`

原功能分支：`codex/iss-018-backup-recovery`

ISS-018-FIX-01 分支：`codex/fix-iss018-backup-safety`

ISS-018-FIX-01 基线：`ad64eed9e00810beb2734e23f4e58cb6b4533bb8`

## 结论

本轮补充了可执行的单归档一致性备份、恢复、SHA256 校验、保留计划和结构化状态记录。演练使用临时 SQLite、临时媒体目录和合成标记数据；没有连接生产 PostgreSQL、真实媒体卷、Nginx、systemd 或异地存储。因此 ISS-018 仍为 `BLOCKED`，生产部分明确为 `DEPLOYMENT_VERIFICATION_PENDING`。

实现不是把两份互不关联的文件打包：备份要求写入静默，数据库快照前后核对媒体清单，数据库、媒体、配置和清单进入同一个 ZIP；恢复先完整验证后在同一文件系统临时目录原子切换到新目录。

## ISS-018-FIX-01 安全恢复回归

FIX-01 修复了旧实现的副作用：非空目标拒绝后不再向目标目录写 `restore-result.json`。默认恢复结果改写到目标目录旁的隐藏报告，调用方可用 `--result-file` 明确指定位置。正式目标必须不存在；空目录也拒绝，以保持原子切换契约，不删除非空目录。

新增回归覆盖：

- 非空目标的普通文件和原有 `restore-result.json` 完全不变；失败报告写入目标外旁路路径。
- 调用方显式指定外部失败报告时，目标仍不变。
- 解包磁盘写入失败时没有正式目标或残留 staging 目录；可换新目标重试。
- 正常恢复保留结构化 PASS 报告，恢复目录、数据库和媒体文件在 POSIX 上分别为 `0700`/`0600`。
- POSIX 不安全备份目录默认拒绝，显式收紧后才可使用；Windows 开发环境仅记录 `WINDOWS_ACL_PENDING`，生产 NTFS ACL 未验证。

## 可复核自动测试

```text
python manage.py test crm.tests.test_iss018_backup_recovery --verbosity 1
Ran 15 tests in 1.183s
OK (skipped=1)
```

覆盖：未确认静默窗口拒绝、单归档恢复、订单金额/库存/附件路径关系、媒体复制过程中变化拒绝、篡改媒体恢复拒绝、路径穿越拒绝、目标冲突不变、原有报告不覆盖、外部失败报告、磁盘写入失败无半成品、POSIX/Windows 文件访问控制、PostgreSQL 未绑定快照 fail-closed、7/4/3 保留计划（层级取并集，不执行删除）。

管理命令的隔离实跑（临时目录名已脱敏）：

```text
create_consistent_backup ... --backup-id isolated-cli --quiesced
status=PASS
archive_sha256=8fc6b9b2291e3288936740569066e2863ba8e8118ea395f547e408f99b22d9c0
consistency_method=application-quiesced-sqlite-backup-and-media-archive

restore_consistent_backup ... --target-dir %TEMP%\iss018-cli-...\restored
status=PASS
verified_media_manifest_sha256=540ddee18000ba029f5a3b9625170ed7ba08b1fff5a20a5e50ad0bbfa337f542
RESTORED_ORDER_TOTAL=5000
RESTORED_INVENTORY_QTY=42
RESTORED_ATTACHMENT=followups/invoice.pdf

private_media_manifest --media-root <restored-media>
file_count=1
total_bytes=23
followups/invoice.pdf sha256=d2bfa734fdf085e40cb0f539bd62051de53ab3628d901daf89fb42c904443f58
manifest_sha256=540ddee18000ba029f5a3b9625170ed7ba08b1fff5a20a5e50ad0bbfa337f542
```

本机工具核对：`age=NO`、`psql=NO`、`pg_dump=NO`、`docker=NO`；因此没有执行真实 PostgreSQL 或加密异地副本恢复，也没有把模拟结果写成生产 PASS。

## 回归日志

```text
python manage.py test crm --verbosity 1
Ran 957 tests in 464.009s
OK (skipped=15)

python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations crm --check --dry-run
No changes detected in app 'crm'

npm run test:unit
tests 154 / pass 154 / fail 0

npm run build -- --configLoader runner --outDir %TEMP%\sunjack_iss018_dist
2013 modules transformed; built successfully in 1.84s
```

FIX-01 在独立 Worktree 以受控测试权限重跑全量 Django：`python manage.py test crm --verbosity 1`，`Ran 965 tests in 421.922s`，`OK (skipped=16)`。首次非提升沙箱运行因 Worktree 位于受限 C: 路径而无法创建既有 `backend/media`，未作为代码失败；提升后的同一测试通过，未放宽媒体目录权限。

前端构建保留既有大 chunk warning；`npm install` 报告依赖审计 `2 moderate、9 high`，未执行自动修复或无授权升级，沿用项目既有依赖风险台账，不将其误报为本任务生产漏洞。

现有 ISS-047 清单定向测试仍保留，未修改其权限和媒体 API；ISS-043 的 PostgreSQL 触发器/运行账号生产验证仍按原台账保持待验。

## 演练数据核对

测试夹具在 SQLite 中写入：

```text
order_no       SO-ISS018-001
total_amount   5000.00
sku            SKU-ISS018-001
inventory      42.00
attachment     followups/invoice.pdf
media SHA256   由 ISS-047 build_private_media_manifest 逐文件生成
```

恢复后通过 SQLite 查询重新读取订单金额 `5000`、库存数量 `42` 和附件路径 `followups/invoice.pdf`，确认恢复媒体中该路径存在，并用 `compare_private_media_manifest` 得到空差异。恢复结果 JSON 的 `status` 为 `PASS`，同时记录 `started_at`、`finished_at` 和 `duration_seconds`。

## 失败和拒绝证据

| 场景 | 结果 |
|---|---|
| 不传 `--quiesced` | 失败；拒绝把未证明的操作窗口称为一致性备份 |
| 媒体在数据库快照后变化 | 失败；不生成最终 ZIP |
| 篡改归档内媒体 | 恢复拒绝；SHA256/manifest 不匹配 |
| 非空目标/已有 `restore-result.json` | FIX-01：拒绝，普通文件和原报告均不变，失败结果写目标外旁路文件 |
| 解包磁盘写入失败 | FIX-01：拒绝，正式目标和 staging 均不留下，可用新目标重试 |
| POSIX/Windows 访问控制 | FIX-01：POSIX 目录/文件 `0700`/`0600`；开发 Windows 为 `WINDOWS_ACL_PENDING`，生产 NTFS ACL 待核验 |
| 当前设置改为 PostgreSQL 但未提供绑定快照 | fail-closed；不连接数据库、不冒充通过 |
| 保留计划 | 只读 PASS；默认不删除，`--apply` 需运维显式授权 |

## 未执行项

以下项目不由本机演练替代：真实 PostgreSQL `pg_dump`/快照、生产私有媒体卷、独立故障域加密副本、age 私钥恢复、Nginx 静态绕过、systemd 定时器、失败告警通道、磁盘/inode 告警以及目标环境 RPO/RTO。它们均保持 `DEPLOYMENT_VERIFICATION_PENDING`，解除条件是隔离 staging/生产环境和可核实的原始命令、状态 JSON、恢复结果、数据库关系/金额/库存及媒体 SHA256 证据。

不提供真实备份文件、不上传密钥或敏感资料；本 README 只记录非敏感合成数据和命令结果。
