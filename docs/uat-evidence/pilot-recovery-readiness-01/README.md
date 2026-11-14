# B 包恢复演练交接（2026-11-14）

构建基线 `96276dffa07c11fb60720a439269df8c36031f7a`。配置入口和待填写事项见 [局域网内测备份与恢复](../../deployment/PILOT-RECOVERY.md)。

## 既有依据与本轮范围

- [既有 PostgreSQL 命令恢复证据](../integration-closeout-02/final-backup-command-447d-result.json)记录了隔离集群恢复和拒绝场景。[ISS-018](../../deployment/ISS-018-数据库与附件一致性备份恢复.md)保留 Linux 维护、加密、签名、回执、独立副本和监控说明。本轮只运行合成业务恢复。
- 本轮复用 `backend/isolated_postgres_drill.py`，由工具创建随机回环端口、临时 PostgreSQL 17 集群、不同的源/恢复库、独立媒体目录。工具在备份时使用数据库锁和进程内媒体写入门闩，合成实例无其他写入者。恢复时仅启动本包短时回环 HTTP 服务，退出时随演练关闭，现有开发服务和业务数据未接触。
- 首次稀疏检出遗漏报价模板，演练在造数时失败并清理临时集群。补入仓库已有 `templates` 后重跑。
- 首次接入真实 HTTP 时，恢复后新建登录会话改动了恢复库，原逐行比对准确拒绝该次结果。最终把合成会话建在备份前，恢复后使用随归档恢复的会话只读检查。

## 本轮结果

Windows / Django 6.0.9 / PostgreSQL 17.11，退出 0。临时回环源库 `iss018_src_4dc905d18e314530` 与新恢复库 `iss018_dst_3d857a961ad64c2d` 共用本包独占临时集群，源与目标媒体分目录。逐行比对 124 张表、1,171 行，含 165 项迁移。源媒体未变，归档清单中 3 个文件共 103 字节。临时集群、归档和媒体已清理。

| 核对项 | 源库与恢复库一致 |
| --- | --- |
| 客户，销售订单 | 2 个客户，1 张订单，原币 USD 20.00 |
| 收款，付款 | 收款 USD 5.0000，付款 USD 3.0000 |
| 库存 | 1 笔采购入库，库存数量 2.00 |
| 恢复实例订单 | 认证会话访问订单详情 HTTP 200 |
| 客户跟进附件下载 SHA256 | `64e20fdf0f55d33193d299a7109e6e6b45ad1b31622bea93341c60330b2a0200` |
| 报价图片下载 SHA256 | `ff95b99e6cd933dc1ce0dfc57ce7d4f78577e094ba87381f2edfba2a4690a7c6` |

两份附件经回环 HTTP 读取，摘要均与源字节相同。联合归档 SHA256 为 `b88b653dcda947652619de4f44149c1a33776dba398f0e257be4dcee6c807499`。

## 定向复跑入口

使用干净的 `backend`、`templates` 和 `backend/requirements.lock` 环境。执行前确认是合成验收机。

```powershell
$env:APP_STAGE = 'development'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
python docs/uat-evidence/pilot-recovery-readiness-01/run.py --postgres-bin '<PostgreSQL 17 bin directory>'
```

归档与测试数据库由工具保存在独占临时目录，工具关闭临时集群后清理。通过条件是命令退出 0 并报告 `PASS`、源数据与恢复数据一致、源媒体不变、业务原币、库存和两个 HTTP 下载字节复核成功，以及 `cleanup=complete`。

## 目标端待验

目标机、独立恢复集群及独立备份位置尚未获准连接。目标端实机待核对 Linux 媒体卷的内核只读状态、维护角色与静默窗口、加密归档及签名回执、跨主机副本校验以及登录下载。本地 Windows 合成演练使用已有 ISS-018 演练适配器，Linux `operations_backup.py` 真实文件系统栅栏与目标配置仍待验。上线前由运维按交接填入负责人与频率、保留期。
