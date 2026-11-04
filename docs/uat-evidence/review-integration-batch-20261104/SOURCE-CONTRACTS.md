# 稳定来源接收与跨包契约

更新检查点：集成分支 `codex/r1-prelaunch-consolidation-20261104` 当前 HEAD 为 `1f189c3f74fda2908620dd3860230d860f1cbb43`，其父提交为 `673ae3724b5db8d69018acbcea3e26c904c3fea3`；固定基线仍为 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`。`source-receipts.json` 对六个固定来源的祖先核验点是673ae37；673ae37是当前HEAD的直接父提交，因此这些来源仍在当前历史中。财务 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`、运维 `d289de36a3da3e4bd6531c812ec21a05f046d570`、历史 `a0729a0965850028fe52f5b6fcc3e825f23b1289` 均已完整进入该祖先。下表原始跨包契约观察仍保留；具体测试证据按各自实际执行 SHA 记录，不自动视为在当前HEAD重跑。

| 接通点 | 当前观察 | 稳定交付后必须证明 |
|---|---|---|
| 来源身份 | 历史 `HistoryTakeoverSourceRecord` 使用source_system/record_type/source_record_id唯一约束；财务事实使用source_system/source_key唯一约束 | 逐来源记录确定性映射，同源重试返回同一结果，不按备注或名称猜来源；组内失败不留下半组事实 |
| 来源长度 | 历史source_system最长160，财务服务限制80；财务source_key最长128 | 超长来源明确拒绝或使用有完整追溯的显式映射；不得截断导致不同来源合并 |
| 真实性 | 历史行使用真实/模拟/待核实，财务normalize接受verified/simulated/needs_verification | 明确映射并保留审批来源；字符串“真实”本身不能代替认证审批或银行凭证。模拟/待核实始终不进入正式资金及订单余额 |
| 账户 | 财务服务只接受已存在账户主键及账户核实条件；历史交接保留源数据 | 使用显式账户映射，不另建竞争性账户定义，不按同名银行/币种自动合并 |
| 凭证 | 历史源含voucher_reference，财务要求私有voucher对象及摘要核实 | 来源引用不能伪装成已上传文件或哈希；通过正式凭证服务保存真实合成文件后验证摘要，缺凭证明确未接通 |
| 操作人/审批 | 财务指令区分authenticated_user与开发身份，审批要求真实认证用户及两人分离；历史有申请/审核/执行轨迹 | 保留真实测试用户身份与职责分离；不把开发默认姓名写成实名审核者，不借集成绕过任何审批门禁 |
| 交接状态 | 历史执行结果明确finance/inventory/fulfillment not_connected，source records posted为0 | 未接通继续显示未接通；完成适配后用实际目标对象/幂等键/审计证明接通，不仅改标签。未核实暂存不增加正式资金、库存或履约 |
| 日期与余额 | 财务分 actual_date、启用基准、账户核对；历史保留源发生日期及承接剩余量 | 源日期不改为导入日，启用基准不计新收入；迟到事实使受影响账户/期间重新待核对，不凭合成日期配置真实启用 |
| 迁移图 | HEAD `1f189c3f74fda2908620dd3860230d860f1cbb43` 的 PostgreSQL 17.11 全量恢复记录含128条迁移；`0103_merge_finance_and_history` 已应用 | 此次合成PG17验收覆盖当前HEAD迁移升级；正式数据库升级和部署仍需目标环境审批及验证 |
| 新表/附件备份 | 当前HEAD `1f189c3f74fda2908620dd3860230d860f1cbb43` 的PG17.11全量完成：99表、1081行、128迁移、4个文件；history 5表及finance 10表seed后恢复，全部序列和voucher字节一致，源库未变、cleanup complete。恢复后私有凭证HTTP为4/4：匿名403、无权用户403、所属用户下载200且字节SHA一致、公开`/media/`直链404。清单 `artifacts/postgres-backups/finance-restored-1f189c3f74fd.json` 状态PASS；备份 `artifacts/postgres-backups/1f189c3f74fd-0edd1427.zip` SHA256 `6c0dc8077710edb1c47c853d39f62a5d5ce0b6d591607e3745ca45727c4d0688`。 | 这是owned synthetic PostgreSQL和文件环境的恢复验收，不证明正式handoff或真实部署环境；目标环境权限、存储、密钥及业务验收仍是外部门槛 |
| 附件补偿恢复副本 | 本包ISS-007修复在补偿再次失败时保留私有恢复副本/清单；现有services/private_media.py使用os.walk，未排除隐藏目录 | 恢复副本和摘要进入媒体备份并验证直链拒绝；critical恢复告警与人工处理纳入运维runbook。隐藏名称不代表ACL已验收，目标存储/NTFS权限仍须专项 |

本包不基于开发中移动 HEAD 实现临时兼容分叉。稳定完整来源现已接入；1f189c3的SQLite/PG17综合回归及隔离备份恢复已经完成，证据按实际SHA记录。正式handoff、真实业务资料承接和真实部署仍须业务负责人及目标环境完成外部验收；本报告不代表已获上线授权。

## 合并后历史交接证据（证据生成于集成 SHA 673ae37）

- 实际 Chrome 集成数据库快照：`artifacts/history-integrated-synthetic-database.zip` 与 `artifacts/history-integrated-synthetic-database.json`。清单记录源 SHA 为 `673ae3724b5db8d69018acbcea3e26c904c3fea3`、数据库完整性检查 `ok`、12 条历史来源记录、3 条 handoff 均为 `not_connected`；正式财务事实/指令、旧 Transaction、付款计划、库存移动/预留、Shipment、GoodsReceipt 及采购成本分配均为0。该数据库使用合成资料，不是实际历史导入。
- 清单记录该隔离 Chrome 数据库已应用 `0103_merge_finance_and_history`。这证明该合成数据库的迁移状态，不代替 PostgreSQL 17 对最终迁移分支的验证。
- 历史来源第一次 Chrome 审批/执行路径已完成；整次视觉验收因 console 抓到外部字体请求失败而记 `FAIL`。确切 URL 与 `net::ERR_NETWORK_ACCESS_DENIED` 见 `history-network-diagnostic.json` 和 `history-browser-integrated/chrome-run.json`。随后在沙箱外重开同一个已执行申请，Chrome 1440/390 截图及 `history-browser-reopened-approved/chrome-run.json` 无 errors；这是既有申请重开验收，不是第二次全新审批/执行。
- ISS-105、ISS-108 在当前主台账均为 `FIXED_PENDING_REVIEW`，原 OPEN/BLOCKED 行仅由历史引用保留，不表示当前仍为该状态；二者尚待 ChatGPT 独立复审，不据此关闭 GitHub Issue。

## 早期财务版本化契约检查点（历史记录）

已只读取得财务检查点 `9c2c226dd3682e6c8640d049456f30b0b021b716` 的 `docs/uat-evidence/finance-closeout-batch-20261104/CONTRACT-v1.md`。该段为当时尚未完整接收的只读记录；现已完整接收3a07e7e，不能将本段旧时状态当作当前阻塞。

- 实际入口是submit→独立approve→post，只有post建立FinanceFact；待核实/模拟指令不能批准或计入实际资金。
- 受控账户、私有文件ID及系统摘要、实际日期、稳定请求键/源键均须显式提供，不能从旧历史备注或voucher_reference猜补。
- 旧银行确认入口另有来源集合绑定凭证；历史人工哈希声明保留原属性，不升级成已核验文件。
- opening为独立基准，correction为原事实的有效完整版本而非新差额付款，真实银行退回仍是独立实际事实；核实转账本金才从公司毛流量排除。
- 契约明确尚未授权正式历史迁移执行器或真实历史导入。集成时须区分隔离合成服务契约验证、历史暂存交接状态和真实导入授权，不仅修改not_connected标签，也不借集成擅自导入真实历史。

## 当前跨包显式契约验收

REVIEW-HISTORY-FINANCE-CONTRACT.md的合成测试经真实历史申请/审核/执行建立handoff，再以明确账户、真实合成文件、显式实际CNY金额/日期和唯一源键调用财务官方服务。请求/来源幂等、不同认证操作人、待核实/模拟拒绝及原始来源不变已在SQLite1/1验证；全量PG正在执行同一用例。finance_closeout.text()对超长source_system(80)/source_key(128)拒绝而非截断，历史160长度不被静默兼容。正式历史执行器仍未自动接通，不因合成服务调用而将not_connected改名。

## 交付前CI更新

代码1f189c3的CI41829100528最终为Backend/PG成功、Frontend失败（ISS039快照子进程2项）。已保留原始失败证据并最小补修有界输出缓冲/诊断；大快照2/2、受影响Chrome2/2和Node179/179通过，原全库/业务/权限断言保留。最终完整前端与精确SHA三CI见统一交付回执，本文各早期运行中/待验句仅保留当时状态，不是当前通过声明。后端全量1312项SQLite/PG均无失败，PG额外8命令专项8/8；未关闭Issue或替代ChatGPT独立复审。
