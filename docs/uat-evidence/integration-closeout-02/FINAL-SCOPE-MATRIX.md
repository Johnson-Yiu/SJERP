# 集成验收范围与证据边界

## 当前冻结候选：02140bf

本页当前状态对应源码候选 `02140bf46df27ba1abf5b9018507c07aae825769`。以下为实际JSON记录的验收结果；本页是开发侧证据汇总，不是ChatGPT独立复审或上线批准。

| 范围 | 当前结果 | 实际计数与证据边界 |
|---|---|---|
| Backend SQLite / Python 3.12 | PASS | 1410项：1338通过、72跳过、0失败。`backend-full-02140bf-python312-result.json`。 |
| PostgreSQL 17 | PASS | 1410项：1378通过、32跳过、0失败。真实PG结果及原始日志：`final-pg-02140bf/final-pg-02140bf-result.json`、`final-pg-02140bf/logs/postgres-final-02140bf-full.log`。 |
| 前端 Node / 字体 / Vitest / 构建 | PASS | Node 179/179；字体1/1；Vitest 725/725（78文件）；生产构建退出0。npm ci有2项弃用警告和4项moderate审计发现；构建有一个压缩后超过500 kB的chunk警告。见`final-02140bf-frontend/FAIL-RESULT.json`及`logs/`。 |
| 全量适用 Playwright | FAIL | 9个profile合计262通过、1失败、0跳过。唯一失败为`quote-editor-isolated`原断言`download.saveAs: canceled`；保留原失败结果。此套件按原runner使用混合浏览器配置，不把262项统称为Google Chrome。见`final-02140bf-frontend/playwright-suite-summary.json`及`FAIL-RESULT.json`。 |
| 打印完整输出与分页 | NOT_RUN_USER_DEFERRED | 用户延期的spec共7个场景，未运行；不计入Playwright跳过数。 |
| 历史接续真实Chrome验收 | PASS（独立专项） | 5/5个Chrome阶段通过；98个本地HTTP请求（90个200、8个201）；8张截图，工作簿实际文件存在。见`final-02140bf-history-chrome/result.json`。这组专项不计入1410后端测试。 |
| Source invariance | PASS（独立专项） | 6/6通过，0失败/跳过；独立源数据、序列及媒体复核，不计入1410后端测试。见`source-invariance-02140bf-result.json`。 |
| GitHub CI | NOT_RUN_USER_QUOTA_PAUSED | 按用户要求暂停；本轮没有新的CI结果。 |
| Issue状态汇总 | 记录状态，不代表关闭 | 124项：FIXED_PENDING_REVIEW 87、NEEDS_VERIFICATION 14、BLOCKED 13、OPEN 0、CLOSED 10。原86项复审队列保持未独立复审；ISS-121作为新增补充单独计入FPR，非CLOSED。 |

较早quote边界诊断在独立全新检出中分别为sandbox 1/1和native 1/1通过；两次是补充诊断，不覆盖上述全量Playwright的quote失败，也不能据此归因执行环境。详见`quote-boundary-controls-02140bf-result.json`。

## 历史基线记录：447d（以下原记录保留，不代表02140bf）

产品固定447d7816ead2e971e249cb2e762b1a6f7009b9c0；后续e768测试遥测与应用树无差异，证明见application-equivalence-447d.json。以下记录是Codex开发侧自查，不是ChatGPT独立接受。历史结果不替代上方02140bf结果。

| 范围 | 状态 | 已执行证据 | 未覆盖 / 关闭缺项 |
|---|---|---|---|
| 完整稳定来源及自动合并 | PASS（代码预审） | e301/4a4/ba完整祖先；finance_closeout.py保留有效分类锁内重验、核对指纹及历史双人批准门槛 | 待独立代码复审；不以无冲突等于业务正确 |
| 后端Python3.12全量 | PASS（本地隔离） | SQLite1410：1330通过80跳过；PG17.11 1410：1378通过32跳过，均0失败 | Windows环境，不替代Linux权限或目标服务器 |
| 迁移汇合 / 新库 | PASS（本地隔离） | check、makemigrations --check、唯一叶0108；全量新测试库实际应用至0108 | 来源旧数据升级/危险回退原证据仅在五个迁移blob相同范围复用，不称本轮重新执行全部来源命令 |
| 审计 / 历史新表不可变 | PASS范围以原断言和最终PG工件为准 | 0108及原保护测试进入PG全量；填充历史盘点2/冲销1/接续合同2行后完整恢复 | PG超级用户/对象owner可改DDL，生产应用角色与迁移角色分离仍需目标验收 |
| 备份 / 私有文件 / 恢复 | PASS（一次性合成PG） | 102表1218行133迁移，5文件254字节SHA一致；归档/财务/实际接续三个恢复PASS，源未变、cleanup complete | 不证明生产计划任务、独立故障域、密钥保管、正式RPO/RTO |
| 财务反例 / 权限动作 | 已修复待独立复审 | 原三反例默认发现，25有序锁专项、30完整财务来源PG、最终PG全量；preview/create/update及导出契约有拒绝路径 | 未扫描或自动纠正目标存量错误配对，未启用正式RBAC |
| 附件保存后重开 | 已修复待独立复审 | 修前确定性失败，修后Vue27/Node9；e768实际GoogleChrome3/3、10图和HTTP文件摘要 | 与447d应用代码一致；不证明目标私有存储/真实员工身份 |
| 历史实际接续 / 财务及库存契约 | 已实施，集成正向视觉验收中 | 完整ba合入，正式服务和幂等/原子性断言进入1410 PG；新表非空恢复 | 集成Chrome结果另收敛；源编号边界、凭证人工对应、更正范围仍逐项审查 |
| 前端单元及构建 | PASS（本地） | Node179、字体1、Vitest725/78文件；npm ci和构建退出0 | Node24/npm11与CI22不同；4 moderate、弃用、大chunk警告保留 |
| 适用浏览器全量 | FIX REQUIRED / 调查中 | 9 profiles，261通过2失败0跳过；完整失败原日志保留 | 两项download.saveAs canceled根因/定向回归待收敛，不改弱断言 |
| 打印完整成品与分页 | NOT_RUN_USER_DEFERRED | 原完整输出spec及断言保留，静态7项均未执行；字体失败1/1及卖方冻结3/3执行通过 | 用户已决定延期，不再催办或重试完整输出 |
| Linux跨UID正式回执交接 | NEEDS VERIFICATION | 0037正式CLI只读属组补修；本机27通过2 POSIX跳过 | 源4a4原Linux成功不等于补修后Linux通过；无已验证Linux执行环境，CI额度暂停 |
| GitHub CI | NOT_RUN_USER_QUOTA_PAUSED | 历史906/41855319673三成功；0037零步骤账单失败另存 | 用户要求后续[skip ci]；不新触发、等待或重跑，不改workflow规避 |
| 正式身份 / 目标资料 / 真实迁移 | BLOCKED（外部条件或另行授权） | 开发超级管理员约定不变，合成双人Session只用于隔离验证 | 正式员工认证、生产配置、实际余额/凭证、真实迁移执行、目标HTTPS/角色/私有媒体/异地副本另验 |

原86项FIXED_PENDING_REVIEW及10项CLOSED集合保持，不将全量PASS或内部agent审查当成ChatGPT独立复审。所有缺陷按公共台账原ID承接；未合master、未部署、未导入真实资料、未宣布上线就绪。

恢复后不可变性实证：三张实际非空历史表各UPDATE/DELETE/TRUNCATE，共9/9次被原历史guard拒绝，SQLSTATE均55000；逐次SAVEPOINT回滚，完整数据库状态/序列比较未变。证据为final-pg-447d中的history-operational-restored-447d7816ead2.json，不并入1410单元测试数量，不声称已验证生产受限角色。

最终447d备份命令补充专项：8/8通过、0失败/错误/跳过，326.359秒，Python3.12/真实PG17.11。原始校验和、损坏归档、缺媒体、版本、工具失败、错误环境、production-stage拒绝及正常恢复断言均保留；各任务目录清理完成。原全量32跳过不改写，这8项单独列出。首轮沙箱1通过7失败（pg_ctl restricted token87，尚未seed，source_unchanged=null），获工具审批在沙箱外按原断言复跑通过；两个原始日志及逐case结果封存于final-backup-command-447d-result.json和ZIP。
