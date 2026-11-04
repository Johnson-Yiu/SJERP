# 稳定完整来源接收与冲突记录

## 最新集成检查点（2026-11-04；阶段结果，不是最终验收）

- 当前分支/HEAD：`codex/r1-prelaunch-consolidation-20261104` / `1f189c3f74fda2908620dd3860230d860f1cbb43`（父提交 `673ae3724b5db8d69018acbcea3e26c904c3fea3`）。`source-receipts.json` 对六个固定完整 SHA（基线、打印、核心工作区、财务、运维、历史）的祖先核验点为673ae37；该点是当前HEAD直接父提交，因此六来源均仍在当前历史中。来源 CI 只记来源证据，不是当前 HEAD 的最终集成 CI。
- 本轮3个并行来源：财务 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`（来源 CI 41815451746）由 merge `c1937da1c046496591d8404b72c42eec4d75bc88` 接入；运维 `d289de36a3da3e4bd6531c812ec21a05f046d570`（来源 CI 41814619508）由 merge `d6ebad3a6cd2358e0db14761c33ebbfaf34b0f50` 接入；历史 `a0729a0965850028fe52f5b6fcc3e825f23b1289`（来源 CI 41822826770）由当前 merge `673ae3724b5db8d69018acbcea3e26c904c3fea3` 接入。finance `319941c05e4682d80cd718f577514a39231fabfa` 及修复 `319941c` 已在当前 HEAD 祖先中。
- 迁移汇合：`backend/crm/migrations/0103_merge_finance_and_history.py` 保留两条依赖：`0102_bank_private_voucher_binding` 与 `0098_history_takeover_workflow`，无数据操作。当前 HEAD 1f189c3 的 PG17.11 全量恢复清单覆盖128条迁移并包含0103。
- 两处测试冲突的结果：
  - `backend/crm/tests/test_csv_import_audit_migration_rollback.py` 保留审计数据存在时拒绝回退及记录仍存在断言，并补充迁移保护仍 applied、历史承接表在拒绝后恢复的断言；`finally` 恢复最新迁移图。
  - `backend/crm/tests/test_history_import_preflight.py` 保留模板头部契约校验：当前库存表完整字段集合必须匹配；兼容旧模板时只接受明确列出的旧字段集合（不含 `warehouse_type`、`lot_reference`）；其他工作表仍逐列精确匹配。没有删除测试场景或跳过测试。
- 主台账当前为124个唯一 Issue ID：`FIXED_PENDING_REVIEW 86`、`NEEDS_VERIFICATION 14`、`BLOCKED 14`、`CLOSED 10`、`OPEN 0`。ISS-105、ISS-108 已校准为 `FIXED_PENDING_REVIEW`，旧状态另作历史引用；`ledger-verification.json` 已重算、`ISSUE-MATRIX.md` 已同步。未关闭 GitHub Issue；待独立复审项不由 Codex 自行关闭。
- 主审报告一次长 `git merge` 尚未结束时提前启动后续 Git 操作后，385个本包专属文件由保留 index 恢复，原始 bytes 已核对一致。此项是工作树恢复记录，不是测试通过证据；本目录未提供单独字节对比 manifest。
- PG finance seed/backup/restore：实际运行应用 SHA `319941c05e4682d80cd718f577514a39231fabfa`，13/13定向测试通过、0失败/跳过；10张新 finance 表有数据。13张finance/cash支持表行摘要、序列与 voucher 字节复核一致；archive `319941c05e46-b453a6b3.zip` SHA256 `c4e5277d68d38e8e16e3d8b1b2d18654c2384466004787c0a4842d037d038fa2`。恢复结果94表/1027行/126迁移/4文件，源媒体未变、cleanup complete。原始日志及manifest见 `logs/postgres-finance-seed-319941c-approved.log`、`artifacts/postgres-backups/319941c05e46-b453a6b3.json`、`artifacts/postgres-backups/finance-restored-319941c05e46.json`；受限 token 的首轮失败仍保留在 `logs/postgres-finance-seed-319941c.log`。该 PG 专项早于 ops/history 合并，不能冒充 HEAD 673 的全量验收。
- 当前 HEAD `1f189c3f74fda2908620dd3860230d860f1cbb43` 全量回归实际结果：SQLite 1312项，1251通过、61跳过、0失败，816.678秒；PostgreSQL 17.11 1312项，1282通过、30跳过、0失败，1008.032秒。PG seed/restore包含history 5表及finance 10表；恢复库99表、1081行、128迁移、4个文件，全部序列及voucher字节匹配，源库未变且cleanup complete。恢复后真实私有文件HTTP 4/4：匿名403、无权403、所属用户下载200且摘要匹配、公开media直链404。证据清单 `artifacts/postgres-backups/finance-restored-1f189c3f74fd.json`；备份 `artifacts/postgres-backups/1f189c3f74fd-0edd1427.zip` SHA256 `6c0dc8077710edb1c47c853d39f62a5d5ce0b6d591607e3745ca45727c4d0688`。这属于owned synthetic环境验证，不证明正式handoff或真实部署。
- HEAD 673阶段实测由主审报告：Vitest 77 files / 720项通过（170.27秒）、Node-only 1项、生产构建通过。Vitest/Node/build 的本轮原始日志路径未写入本目录索引，结果可记录但尚缺可点开的原始日志引用。
- 历史 Chrome 首轮审批/执行完成，但整次检查因 `fonts.googleapis.com` 在沙箱中 `ERR_NETWORK_ACCESS_DENIED` 记 FAIL；证据见 `history-network-diagnostic.json`、`history-browser-integrated/chrome-run.json`。沙箱外重开同一已批准/执行申请后退出码0、Chrome桌面及390px截图无 errors，见 `history-browser-reopened-approved/chrome-run.json`。重开不是重复的新审批/执行。该次实际数据库快照 `artifacts/history-integrated-synthetic-database.zip` / `.json` 记录12源记录、3个 `not_connected` handoff、正式财务/库存/履约事实均为0及迁移0103。
- CI run `41829100528`：主审最新状态回报为Backend与PostgreSQL成功、Frontend仍运行中。此次报告更新时GitHub API读取受到HTTP 429限流，未能独立刷新Frontend最终状态。该run尚不能记作三项全绿；本轮文档最终提交后的精确SHA仍须有对应Backend/PostgreSQL/Frontend结果。当前HEAD保持冻结，本次只更新三份报告，不提交。

以上测试记录区分各自执行SHA。1f189c3的SQLite、PG17及恢复HTTP实测已完成；CI前两项成功、Frontend运行中。正式handoff、真实历史承接和真实部署仍是外部门槛；不合并 master、不部署。

| 来源 | 已核对远端完整SHA | 精确SHA CI | 本包接收状态 |
|---|---|---|---|
| 打印封存 | b3d0d386de70d9efd77bf62cdbd87877fbccbfb8 | 41802910019三项成功 | 完整来源合入98bf4ea6108c913d0c6b31f77a25191df5e46e11；仅打印完整成品/分页按用户决定延期 |
| 核心工作区 | e302199f7890c686a309f54aebe8cc31b6202f52 | 41808354916三项成功 | 已审完整四提交范围，合并进行中 |

两个远端分支已经git ls-remote实际核对；源CI原始查询结果保存在本包logs/source-ci-*.json。源CI不替代集成最终CI。

## 文件处理

- AGENTS.md：唯一手工内容冲突。保留当前用户“按依赖/模块/冲突组织尽可能多任务、不设数量上限”，不恢复来源旧2–5限制；连续自查、集中交付、最终精确SHA CI、权限及部署授权边界保留。
- frontend/infrastructure-tests/runner-validation.test.mjs：Git自动合并后人工核对，保留本包自有子进程取消清理/诊断，保留打印来源xvfb/xauth可用性断言。只允许证据上传步骤使用always，业务检查仍禁止if或continue-on-error跳过/忽略失败。
- .github/workflows/ci.yml：接收打印来源已验证的虚拟显示及证据保留步骤，非通过修改workflow规避失败。Backend、真实PG17、Node、Node-only、Vitest、浏览器、构建步骤全部保留；没有减少任务或弱化断言。本包未另外改写workflow。
- QuotePreviewModal.vue：保留已保存PI图片/字体准备检查、失败提示及重试保护。不追加原生打印/分页新任务或宣称完整成品已独立接受。
- 核心Product/SKU/Resource/Document/Inventory/Purchase页面：审查来源完整差异，主要为晚响应失效、保存中导航保护、跨动作反馈及窄屏SKU字段布局。分类/SKU业务定义、收货请求幂等键、附件失败重试与待上传状态保留；最终行为仍需综合回归。

## 原始证据保留

来源原始CI/测试日志有尾随空白，导致整个集成差异的git diff --check报错。原始Git字节分别无损保存在print-source-raw-ci-logs.zip（2份）和core-source-raw-logs.zip（22份），仓库相对原路径、源SHA、原始及阅读副本摘要列在各manifest。历史路径的文本仅作为明确标头的阅读副本，去掉尾随空白；未删除失败、未改结果、未以阅读副本摘要冒充原始日志摘要。完整源提交作为合并祖先保留，原日志也可用git show精确源SHA取得。

本包首次浏览器回归还有两个测试把输出写到旧历史路径，已先保存本轮9个输出与双摘要，再恢复历史Git内容；仅修测试输出根目录，专项2/2及3/3通过，详见fixed-path-evidence-preservation.json。

上表仅保留早期打印/核心工作区的接收记录；财务、运维、历史来源的最新完整交付状态见本文件顶部检查点。此前“尚不接收”是早期阶段记录，已由顶部的固定 SHA/merge 记录取代，不再作为当前状态。

## 交付前CI更新

代码1f189c3的CI41829100528最终为Backend/PG成功、Frontend失败（ISS039快照子进程2项）。已保留原始失败证据并最小补修有界输出缓冲/诊断；大快照2/2、受影响Chrome2/2和Node179/179通过，原全库/业务/权限断言保留。最终完整前端与精确SHA三CI见统一交付回执，本文各早期运行中/待验句仅保留当时状态，不是当前通过声明。后端全量1312项SQLite/PG均无失败，PG额外8命令专项8/8；未关闭Issue或替代ChatGPT独立复审。
