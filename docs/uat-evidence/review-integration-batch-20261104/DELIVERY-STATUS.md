# 综合验收状态（2026-11-04 阶段检查点）

**总体状态：NEEDS VERIFICATION。** 当前冻结并已普通推送的集成 HEAD 为 `1f189c3f74fda2908620dd3860230d860f1cbb43`，父提交为 `673ae3724b5db8d69018acbcea3e26c904c3fea3`。该HEAD全量SQLite、PG17及恢复后HTTP已结束；CI run 41829100528的Backend/PG成功，Frontend仍运行。本记录区分各证据的实际执行SHA，也不代表正式handoff、真实部署或上线授权。

| 范围 | 状态 | 当前可证实结果 | 尚缺的验收 |
|---|---|---|---|
| 稳定来源接收 | PASS | `source-receipts.json` 对6个固定完整 SHA的核验点为 HEAD 673；673是当前 HEAD 1f189c3 的直接父提交，因此六来源均在当前历史中。三项新来源及集成锚点：finance `3a07e7e…`→`c1937da…`，operations `d289de3…`→`d6ebad3…`，history `a0729a0…`→`673ae37…`。来源 CI run 41815451746、41814619508、41822826770 是来源证据。 | 正式handoff与真实部署仍须外部验收。 |
| Issue 台账 | PASS（计数核对） | 124个唯一 ID：`FIXED_PENDING_REVIEW 86`、`NEEDS_VERIFICATION 14`、`BLOCKED 14`、`CLOSED 10`、`OPEN 0`。ISS-105、ISS-108 已从旧 OPEN/BLOCKED 校准为 `FIXED_PENDING_REVIEW`，原状态仅作历史引用；没有关闭 GitHub Issue。 | 86项仍需 ChatGPT 独立复审；FIXED_PENDING_REVIEW 不等于已接受。 |
| 两处测试冲突 | PASS（合并内容审查） | CSV审计迁移拒绝回退测试仍核查原审计行保留，并增加 migration recorder/历史承接表恢复断言；历史预检模板测试继续精确核对当前完整表头，另列明确旧模板字段集，其它工作表仍逐列精确匹配。没有删除测试场景或跳过测试。 | 最终 HEAD 全量执行仍待完成。 |
| 0103迁移图 | PASS（HEAD 1f189c3 PG17.11） | PostgreSQL全量恢复清单包含128条迁移并已应用 `0103_merge_finance_and_history`。 | 真实部署库升级仍须在目标环境执行并由运维/业务负责人验收。 |
| 全量SQLite / PostgreSQL | PASS（HEAD 1f189c3） | SQLite：1312项，1251通过、61跳过、0失败，816.678秒。PostgreSQL 17.11：1312项，1282通过、30跳过、0失败，1008.032秒。 | 跳过项按原状态保留，不计入通过；目标部署环境仍需外部验收。 |
| Seed、备份恢复与恢复后HTTP | PASS（owned synthetic环境，HEAD 1f189c3） | History 5表、finance 10表seed后恢复；99表、1081行、128迁移、4文件。全部序列和voucher字节一致，源未变、cleanup complete。恢复HTTP 4/4：匿名403、无权用户403、所属用户下载200且SHA匹配、公开media直链404。清单 `artifacts/postgres-backups/finance-restored-1f189c3f74fd.json`；归档 `artifacts/postgres-backups/1f189c3f74fd-0edd1427.zip` SHA256 `6c0dc8077710edb1c47c853d39f62a5d5ce0b6d591607e3745ca45727c4d0688`。 | 仅证明隔离合成源/恢复环境及私有文件路径；不证明正式handoff或真实部署。 |
| 历史 Chrome 审批/执行 | NEEDS VERIFICATION（浏览器运行有限制） | 首次 Chrome 完成审批/执行；整次浏览器验收因外部字体 GET `https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap` 返回 `net::ERR_NETWORK_ACCESS_DENIED` 记 FAIL，见 `history-network-diagnostic.json`、`history-browser-integrated/chrome-run.json`。沙箱外重开同一个已执行申请，Chrome 1440/390 截图无 errors，见 `history-browser-reopened-approved/chrome-run.json`；这是重开既有申请，不是第二次全新审批。 | 若要证明无该网络错误的全新审批/执行，再跑新申请且保留原断言。 |
| 历史集成数据库快照 | PASS（隔离合成范围） | `artifacts/history-integrated-synthetic-database.zip` / `.json` 的 source SHA 为 HEAD 673，完整性 `ok`；12条来源记录、3个 handoff 全为 `not_connected`；FinanceFact、FinanceInstruction、Transaction、PaymentPlan、InventoryMovement/Reservation、Shipment、GoodsReceipt、采购成本分摊均为0；最新迁移0103。 | 这不是实际历史导入或 finance/inventory/fulfillment 已接通的证明；未授权真实历史导入。 |
| Vitest / Node-only / 构建 | PASS（主审当轮实测） | HEAD 673：Vitest 77 files、720/720通过、170.27秒；Node-only 1项通过；生产构建通过。 | 本轮 Vitest/Node/build 原始日志路径尚未写入本包索引；构建警告需以最终日志核实。 |
| CI run 41829100528 | NEEDS VERIFICATION（部分完成） | 按主审最新状态回报，Backend与PostgreSQL成功，Frontend仍运行中。此次报告更新时GitHub API读取遇HTTP 429，未能独立刷新Frontend最终状态。 | 前端结束后核实三项状态；本轮文档最终提交会产生新SHA，须以该精确SHA核实三项CI。 |

## 保留事项

- 一次长 `git merge` 未结束时提前执行后续 Git 操作后，385个本包专属文件已从保留 index 恢复，原始 bytes 已核对一致。该工作树恢复结果不作为测试或业务验收证据；单独对比 manifest 路径未记入本报告包。
- 原受限 token 启动失败保留在 `logs/postgres-finance-seed-319941c.log`，不能覆盖为成功；后续 approved log 是单独的成功运行。
- 正式handoff、真实历史承接、目标环境配置/存储与真实部署验收仍是外部门槛。没有合并 master、部署、启用正式 RBAC、导入真实历史或关闭 GitHub Issue；本状态不宣布上线就绪。

## 交付前CI更新

代码1f189c3的CI41829100528最终为Backend/PG成功、Frontend失败（ISS039快照子进程2项）。已保留原始失败证据并最小补修有界输出缓冲/诊断；大快照2/2、受影响Chrome2/2和Node179/179通过，原全库/业务/权限断言保留。最终完整前端与精确SHA三CI见统一交付回执，本文各早期运行中/待验句仅保留当时状态，不是当前通过声明。后端全量1312项SQLite/PG均无失败，PG额外8命令专项8/8；未关闭Issue或替代ChatGPT独立复审。
