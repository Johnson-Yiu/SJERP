# Linux 稳定来源开发侧预审

## 结论

**代码可纳入集成分支；当前没有发现能绕过签名信任验证、把未验证恢复当成已验证回执，或漏备份 `FinanceVoucher` 文件内容的明确代码缺陷。** 但存在一项明确的运维接通缺口：签发账号创建的回执文件为 `0600`，分离的非 root 保留/监控账号无法读取；现有 Linux 演练通过标准输出把回执交给 runner，再由 runner 重写文件，未验证生产式跨账号文件交接。定时监控与回执保留因此应标为 **FIX REQUIRED / NEEDS VERIFICATION**，直至交接权限被补齐并实测。

这不妨碍把该固定 SHA 的代码并入集成分支；它阻止把整条签名回执—监控—保留链描述为已经部署接通，也不构成生产就绪结论。

## 审查边界与来源

- 固定基线：`8087f2c68b19a302a25e814ec8ce6113d91d4750`。
- 完整稳定来源：`4a4f338b09e9a464f1e66c24a905c35c970729bf`，为基线后 8 个提交的后代。
- 功能验收日志主要对应 `81d37ddb78748f61d58e24ace023fe7fc16a1379`。`81d37d..4a4f` 仅新增三份压缩日志和 README 记录，未改产品代码或验收 workflow。
- 主审提供的 [stable-source-ci-receipt.json](stable-source-ci-receipt.json) 记录：同 SHA `4a4f338` 的 CI run `41866028447`（Backend、Backend-Postgres、Frontend 三项成功）及 Linux run `41866028480`（Nginx、media-fence、PostgreSQL/receipt 三项成功）。这是**来源分支**证据；该回执注明集成后的 CI 仍须单独运行。
- 本文是 Codex 开发侧预审，不代替 ChatGPT 独立复审。本轮没有运行测试、修改产品代码或改 Git。

## 重点核查

### 签名信任根与保留账号

`backend/crm/services/operations_trust.py` 要求信任文件、公钥、OpenSSL 可执行文件及路径各级目录均为 root 所有、不可由 group/other 写入且不能是符号链接；信任文件只接受固定字段并校验公钥 DER SHA-256 pin。保留/监控入口拒绝以 root 运行。`operations_retention.py` 只从受信配置取 pin，不接受调用方自带的 pin。

Linux PG 演练把私钥放在 root 控制的 `/etc/sunjack-ci-trust-<uuid>`，文件模式 `0600`，并断言 runner/保留身份不能读取；调用方可写的信任文件被拒绝，root 管理的信任文件可用。由此可证同一非 root 保留 UID 不能替换 root 控制的 pin 或读取演练私钥。它**没有**验证生产 OS 账号创建、UID 回收/冒用、sudoers/systemd 配置不可替换；这些仍是主机部署条件。

另一个代码边界：`restore_and_sign` 检查私钥在 POSIX 上没有 group/other 权限，但不强制检查私钥 UID 必须为 root 或专用恢复 UID。Linux 演练由 root 生成并持有私钥；生产需明确专用签发身份、私钥所有者与可执行签发入口，不能仅凭函数的 mode 检查推定身份隔离完成。保留账号对备份目录具有文件系统写权限时，仍可绕过 CLI 直接删除文件；报告也明确要求由目标存储 ACL/不可变保留或独立副本承担此边界。

### 实际恢复回执、绑定与过期

`operations_receipt.restore_and_sign` 先解密并核验明文摘要，再调用真实 PG restore；恢复服务核验数据库表/序列状态、私有媒体摘要和审计拒绝路径，并在签名前检查密文未在过程中变化。回执签名覆盖密文/明文 SHA、应用 SHA、来源/目标系统标识、恢复数据库名、签发时间、归档观察到的 mtime(ns) 和审计验证结果。`verify_receipt` 校验可信 pin、签名、归档 SHA、时间戳不能在未来、最大年龄和格式字段。它绑定的是内容摘要、系统身份及观察时间；mtime 是文件系统观察值，不是历史业务日期。

压缩原始 Linux PG 日志的 JSON 结果显示：PG17、99 张表/975 行、三次实际 GPG 解密和数据库恢复签名、伪造/错包/过期拒绝、保留删除两份已核验旧归档；源数据库与合成凭证未变。早期 PG 运行因测试代理把 `pg_restore --list -` 当文件名而失败；固定来源的记录保留了原失败和复现，后续修正 stdin 调用后运行通过，未把早期失败算作通过。

**确认的交接缺口：** `operations_backup.py restore-encrypted-verify` 通过 `publish_archive` 发布回执；`backend/crm/services/operations_postgres.py` 的 `publish_archive` 以 `os.open(..., 0o600)` 创建文件。`backend/operations_monitor.py` 则要求以非 root 身份读取单独的 `receipt_file`。在签发身份与保留/监控身份分离的预期下，默认生成的文件不可由后者读取，代码中没有 group/ACL 授权或交接步骤。现有 PG 验收调用 `linux_receipt_signer.py`（sudo）取得 stdout JSON，再由 runner 自己写 `receipt_file`，所以证明了真实签名和恢复，不证明 CLI 正式回执文件能被调度账号消费。整合后应提供受控的只读交接方案，并用不同 UID 实测 monitor 与 prune 都能读回执、篡改仍拒绝。

### 过期、保留及备份覆盖

保留入口要求显式回执、固定 UUID 文件名、所有权 marker、最少保留数和最小年龄；先验证回执、归档 SHA/mtime 及独立副本，再按执行开关删除，并在删除前重新核验。默认是 dry-run。监控会将缺失、篡改或超龄回执/备份返回非零。Linux 日志包含过期回执、错包、伪造签名、可写 pin、组可写保留目录和错误密钥拒绝，以及错过调度后的非零退出。

`MaintenanceBackup.backup` 对数据库执行 PostgreSQL custom-format `pg_dump`，核验公开 schema 表状态和序列、已应用迁移及备份前后状态；媒体清单覆盖实际文件。`verify_media_references` 明确检查 `crm_financevoucher.file/size/sha256` 与媒体字节匹配，恢复后再次核验引用。Linux PG17 合成数据实际包含并恢复私有凭证，日志记录恢复凭证 SHA。结论是新凭证表与文件被此路径覆盖；这不是生产数据恢复验收，也不等于检查了所有数据库对象权限或外部存储。

### PostgreSQL 角色与写入者栅栏

PG17 演练验证维护角色和应用示例角色均非 superuser；维护角色拥有数据库并有 `CREATEDB`，服务拒绝其他登录角色、活动连接和未决 prepared transaction。示例 runtime 角色为 `NOSUPERUSER NOCREATEDB NOINHERIT`，获准对 `crm_operationlog` SELECT/INSERT，UPDATE/DELETE/TRUNCATE 被拒绝。媒体真实只读挂载、独立写入、备份期间 remount 与文件更改也有实测拒绝证据。

范围限制：该 runtime 夹具仅演示审计表最小权限，没有生成或核验完整 ERP 生产运行角色在所有业务表、序列、函数及新表上的授权矩阵；维护账号仍有 `CREATEDB`。目标 PostgreSQL 主机需另验实际角色、默认权限、连接池/运维账号和凭据隔离，不能把 CI 的两个合成角色当作生产 RBAC 完成。

### Nginx 授权与 workflow 范围

`docs/deployment/operations-nginx.conf.example` 将 `/media` 直链固定返回 404，静态资源单独 alias，API 反代并附 `private, no-store` 与安全头。真实 Nginx、测试证书和隔离 SQLite 测试记录：SKU/凭证授权请求 200，匿名请求 403，受限用户 404 或 403，公开媒体直链 404；Nginx 与应用重启后合成私有文件仍可读。它不验证正式证书链、真实主机 ACL、正式代理拓扑或完整生产角色矩阵；Django 只应信任受控反代转发头。

`.github/workflows/linux-operations-acceptance.yml` 权限为 `contents: read`，PG service 使用一次性 `postgres:17` 和 runner 内信任认证，不取生产 secret/数据库；push 仅匹配 `codex/linux-operations-acceptance-20261104`，另有 `workflow_dispatch`。README 记录工作流不在 default branch 时 dispatch 曾返回 404。因此合并到其他集成分支不会自动触发这套 Linux 验收；同 SHA 的本次成功运行已由主审回执记录，但之后仍需对**最终集成 SHA**单独验收。日志另有 GitHub Actions Node 20 弃用/强制 Node 24、`punycode` 弃用、pip 更新提示及一次性 PG trust-auth 提示；未见这些警告导致本轮 job 失败。workflow 使用 `@v4/@v5` 标签及 `ubuntu-latest`，目标环境应评估动作版本固定和 runner 漂移。

## 证据与报告一致性

| 证据 | 原始内容可证 | 边界 |
|---|---|---|
| `81d37dd-postgres-role-receipts.raw.log.gz` | PASS；source SHA `81d37d…`；PG17；99 表/975 行；三次签名恢复；删除两份旧归档；key/trust/过期拒绝 | 合成 runner 和本机副本，不是生产容灾 |
| `81d37dd-nginx-private-media.raw.log.gz` | PASS；SKU 与凭证授权/拒绝状态、no-store、公开直链拒绝、重启持久性 | 一日自签测试证书与 SQLite |
| `81d37dd-media-fence.raw.log.gz` | 可写挂载拒绝、只读挂载接受、独立写入拒绝、移除只读保护后再次拒绝 | 仅 runner 临时 ext4 |
| `local-unit.log` / `local-unit-after-cleanup.log` | Django 单测分别 47/47、49/49 OK | Windows 本地，不替代 Linux/PG |
| `linux-pg-failure.raw.log.gz` + `pg-restore-stdin-repro.log` | 首轮失败原因是测试传输器 stdin 参数错误；后续 b48e920、bcac0ec、81d37d 的运行通过 | 原失败须保留为历史，不计入最终通过数 |
| `stable-source-ci-receipt.json` | 主审记录同 SHA 4a4f 的三项 CI 与六个 Linux job 成功 | 该 JSON 标注来源 CI，不能代替最终集成分支 CI |

README 所述“同轮本地 27 项”在固定来源提交的原始证据中没有对应的 27 项日志：归档单测显示 47 和 49 项；81d37d Linux workflow 中的回执拒绝单测显示 15 项。该 27 项说法应补其原始日志或从量化结论中移除，不能用其他数量代替它。

## 整合门槛与剩余风险

1. 可以合入固定代码 SHA；将上述 0600 回执跨账号读取问题作为明确的运维接通项。确定受控权限交接，并用真实分离 UID 对 CLI 产生的回执文件完成 monitor/prune 读写拒绝回归。
2. 最终集成 SHA 单独执行三项 CI 和 Linux 三项专项（合计六个 job）；不要把来源 SHA 通过记作集成 SHA 通过。
3. 目标环境提供独立 root/恢复签发身份、root 管理的 pin/公钥/OpenSSL 路径、受限保留身份及不可由该身份直接改写/删除的存储保护；核验 UID/sudoers/systemd 权限。
4. 在隔离预生产 PG17 上以实际角色演练备份、恢复、签名回执、过期监控、保留与故障告警；验证真实 Nginx 证书/代理、外部通知接收、异地或独立故障域副本及恢复抽查。
5. 当前 Linux 定时器/OnFailure 证据只证明任务临时 unit 到同机 loopback receiver 的传递；不能视为外部值班通知或生产调度通过。同 runner 副本不能视为异地灾备。

审查只写入本报告；未修改产品文件、workflow、公共台账或 Git 状态。


## 2026-11-05 ISS-018 回执跨账号交接补修（已提交0037b8c）

上一节记录的 0600 回执交接缺口已在当前工作树作最小补修，已提交0037b8c5899554819943944a9cf9e4ea952d2bae，真实 Linux 专项仍待验：

- `backend/operations_backup.py` 的 `restore-encrypted-verify` 增加可选 `receipt_read_group` 配置。省略时回执保持 `0600`；配置时先在恢复前解析必须已存在的 POSIX 组名，非 POSIX/不存在/无效组失败关闭。该配置不适用于其他操作。
- `backend/crm/services/operations_receipt.py` 新增回执专用独占发布 helper。内容先写入同目录、默认 `0600` 的暂存文件并 fsync；按配置对打开的暂存 FD 执行 `fchown(fd, -1, gid)`，再 `fchmod(fd, 0640)`，再次 fsync、核对 inode/模式/属组后用不覆盖的 hard link 发布。权限或 link 发布失败时清除本次暂存/本次链接，不产生正式回执；保留目标数据库并由 CLI 错误附注要求人工检查。未设置时仍以 `0600` 发布。没有 world-read；备份归档和私钥权限路径未改变。
- `test_operations_receipt_cli.py` 新增默认私有模式、存在组的 `0640`、无效/不支持组在恢复前拒绝、权限设置失败不发布、link 失败清除暂存且不发布等测试。POSIX 的真实 `fchown/fchmod` 单元在 Windows 上标为 skip，由 Linux 专项执行。
- `linux_receipt_signer.py` 现在以 root 调用正式 `backend/operations_backup.py restore-encrypted-verify` CLI；加密密钥仅经 stdin 传给受限 wrapper，再写入 root 私有临时目录，stdout 只返回 CLI 结果和回执路径，不输出或重写回执 JSON。
- `linux_operations_pg_acceptance.py` 继续以普通 runner 身份运行。它通过正式 CLI 实际生成默认 root-owned `0600` 回执并断言普通账号读被拒；再以该账号主组生成 root-owned `0640` 回执，断言普通账号能读原文件、不能写，monitor 直接读取同一原文件，prune 使用从该文件读取的签名数据；仍断言普通账号不能读 root 私钥。该真实 Linux 代码路径尚未执行。用户现因额度暂停CI；本机只读核实未找到docker命令，沙箱外wsl --list --verbose退出1，仅返回安装/帮助，未确认可用发行版（local-linux-availability.json及原始日志ZIP）。未安装/启动WSL或改系统功能，不能将Windows用例等同真实Linux。

### 本地回归结果

运行环境：主审提供的 `.tmp/closeout-python312/Scripts/python.exe`，确认 CPython `3.12.16`；`DATABASE_URL=sqlite:///:memory:`。

- 命令：`python manage.py test crm.tests.test_operations_receipt_cli crm.tests.test_operations_backup --verbosity 2`
- 结果：12 项运行，10 通过、2 跳过、0 失败；跳过项是 POSIX 专属属组发布及权限故障注入测试。本机为 Windows，未以模拟结果替代 Linux 权限证据。Django system check 无问题。
- `linux_operations_pg_acceptance.py`、`linux_receipt_signer.py`、`operations_backup.py`、`operations_receipt.py` 和 `test_operations_receipt_cli.py` 的 Python 3.12 AST 解析均通过。
- 另一次尝试同时运行 `test_operations_receipt` 时，相关 CLI/备份用例通过，但 `ReceiptIssuanceTests.setUpClass` 因当前 Windows 环境找不到 `openssl` 可执行文件而报环境错误；该次命令不能记为全通过。聚焦命令不含该依赖套件并通过。密码签名、正式 PG17 与权限交接仍由真实 Linux 专项验证。
- 主审已核实的历史付款/限额阻断 run `41874838749` 三个 job 均未进入 step；这是外部 CI 条件。本轮没有复用或伪造该结果，也未触发新的 workflow。

本补修仅涉及 `operations_backup.py`、`operations_receipt.py`、`test_operations_receipt_cli.py`、`linux_operations_pg_acceptance.py` 和 `linux_receipt_signer.py`，以及本报告。未修改公共 Issue 台账、workflow 或 Git 历史；Issue 状态由主审统一登记。真实 Linux 结果与最终集成 SHA CI 仍为待验。

## 主审扩展回归补充（2026-11-05）

本机已有Git OpenSSL位于`D:/Program Files/Git/usr/bin/openssl.exe`。通过原测试支持的`OPS_TEST_OPENSSL`显式指定，不修改测试或系统PATH后，Python3.12.16实际执行receipt_cli、operations_backup、receipt、retention、trust共29项：**27通过、2个POSIX专属skip、0失败，7.123秒**。首次未定位可执行文件的环境错误仍保留，不以此成功追改原失败。该扩展实际执行签名、篡改/错包/过期拒绝及保留测试，但不能代替真实Linux的跨UID权限验收。

封闭日志与实际数量：[receipt-handoff-python312-result.json](receipt-handoff-python312-result.json)、[日志ZIP](receipt-handoff-python312-logs.zip)。早期12项聚焦/环境错误原始文件未落盘，仅有子代理工具输出；此证据限制明确保留，未重新制造失败日志。
