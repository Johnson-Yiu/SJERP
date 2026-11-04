# 集成版实测结果（持续更新）

本表只列本包实际执行，来源独立分支 CI 另列 MERGE-RECORD.md。日志路径相对本目录；logs 内闭合日志发布在 raw-logs-phase-01.zip 中，manifest 列明任何凭据字段脱敏。未写最终版本的行均为阶段证据，不能当最终完整验收。

| 版本/环境 | 项目 | 通过 | 失败/错误 | 跳过/取消 | 原始记录与边界 |
|---|---|---:|---:|---:|---|
| 起点 Windows SQLite | 全量后端1182 | 1131 | 0 | 51跳过 | logs/backend-corrected.log；初次错误工作目录发现0项，不能作为通过 |
| ce74 PG17 | 首轮全量 | 1167 | 2方法错误+1类设置错误 | 30跳过，另1方法因类设置未运行 | logs/postgres-full-ce74f8b.log；实际执行1199，不记通过。Supplier.code超长及备份测试缺完整隔离凭据环境已修正 |
| 0914002 PG17 | 真实HTTP/附件/审计/备份专项 | 29 | 0 | 0 | logs/postgres-focused-0914002.log |
| a866c29 PG17 | 扩展附件边界/原名/HTTP/审计/备份 | 42 | 0 | 0 | logs/postgres-focused-a866c29.log；实际源/恢复一致，清理完成 |
| f266433 PG17 | 可保留归档备份专项 | 1 | 0 | 0 | logs/postgres-retained-backup-f266433.log；归档含实际合成dump与媒体，不含后续财务seed |
| 附件修前 SQLite | 三个失败注入 | 0 | 3 | 0 | logs/attachment-atomicity-20261104-transactiontest.log；失败一致性复现 |
| a866附件 SQLite | 附件原子性 | 17 | 0 | 4 PG专用跳过 | logs/attachment-atomicity-final-recovery-boundary-0914002.log |
| Windows junction | 恢复目录链接边界 | 1 | 0 | 0 | logs/attachment-recovery-junction-platform-test.log |
| HTTP证据命名修前 SQLite | 核心真实HTTP | 2 | 1 | 0 | logs/core-http-final-20261104.log；两个场景manifest同名导致拒绝覆盖，保留失败 |
| 命名修后 SQLite | 核心真实HTTP | 3 | 0 | 0 | logs/core-http-prefix-unique.log，107.906秒 |
| f266快照 SQLite | HTTP及实际XLSX/CSV/完整数据库 | 3 | 0 | 0 | logs/core-http-with-database-snapshots.log，103.842秒；artifacts/http-with-database-snapshots |
| 早期隔离Chrome全套 | 浏览器252 | 251 | 1 | 0 | playwright-current/suite-run-summary.json；过期草稿断言早于挂载，不能将分套相加冒充全绿 |
| 页面就绪补修后Chrome | 资金过期草稿与字段安全 | 8 | 0 | 0 | logs/cash-ready-fix.log；原缓存和敏感字段断言保留 |
| npm ci 后默认Node | 单元测试177 | 177 | 0 | 0 | logs/frontend-unit-after-npm-ci.log；此前3轮各176通过/1取消的原始日志保留 |
| 打印/核心工作区阶段 | Node / Vitest | 177 / 714 | 0 | 0 | logs/node-integrated-print-core.log、vitest-integrated-print-core.log |
| c1937da SQLite | 财务合入全量后端1249 | 1189 | 0 | 60跳过 | logs/backend-full-c1937da.log，838.208秒 |
| c1937da Vitest | 76文件 | 717 | 0 | 0 | logs/vitest-with-finance-c1937da.log，153.15秒；后续侧栏单独验证 |
| 财务/运维+侧栏Node | 默认单元测试 | 177 | 0 | 0 | logs/node-finance-ops-sidebar.log，45.753秒 |
| 财务/运维+侧栏 | 生产构建 | PASS | 0 | 0 | logs/build-finance-ops-sidebar.log，4.39秒；>500kB chunk警告仍在 |
| 财务集成 Chrome | 合成认证双人审批/过账/凭证/核对 | 2 | 0 | 0 | logs/finance-browser-approval-integrated.log，25.5秒；finance-browser-integrated/actual-files |
| 财务集成 Chrome | 开发资金页面 | 2 | 0 | 0 | logs/finance-browser-closeout-integrated.log，21.9秒 |
| 新资金语义 SQLite | 待核实/模拟拒绝及更正/本金/费用 | 2 | 0 | 0 | finance-source-negative-paths-sqlite.txt；不是内部ORM权限保证 |
| 财务迁移修前 SQLite | 0098–0102回退矩阵 | 8 | 1 | 0 | logs/finance-migration-rollback-sqlite.log；非空bank_sources/account scope回退没有拒绝 |
| 319941c SQLite | 回退保护补修矩阵 | 9 | 0 | 0 | logs/finance-migration-rollback-fixed.log，11.443秒；保留迁移操作和依赖，增加反向守卫 |
| 319941c 无需数据库 | 财务凭证备份正/拒绝路径 | 2 | 0 | 0 | logs/finance-backup-references.log；真实PG后续另记 |
| 运维集成专项 Windows | 运维既有测试+新引用 | 53 | 0 | 4平台跳过 | operations-source-targeted-sqlite.txt，57项；跳过不记为平台通过 |
| Chrome156 | 长姓名侧栏桌面/窄屏 | 2 | 0 | 0 | logs/sidebar-long-name-chrome-stable.log；等待动画结束后核实视口内 |
| Chrome156 | 13页×2尺寸截图 | 26张 | 0 pageerror | 不适用 | screenshots/integrated-pages-manifest.json；空页面不是正向业务闭环 |

补充失败限制：finance-browser-integrated.log 是一次错误传入两个 --business-test 参数、runner在启动前拒绝；后续分为两条合法命令各2/2。postgres-finance-seed-319941c.log 是沙箱 pg_ctl restricted token 错误、临时资源清理完成；沙箱外重跑另用新文件，不能覆盖旧失败。原生完整打印/分页按用户决定延期，不将本机未重跑的iss037-print-output-acceptance七项称为本地通过，CI仍保留原场景。

以上为早期阶段记录；全来源本地最终结果见下节，最终同SHA三CI单独核实，不以阶段结果抵消失败。历史版本、开发超级管理员和合成session都不代替正式业务认证或目标部署验收。

## 全来源冻结代码1f189c3完整结果

| 项目 | 通过 | 失败/错误 | 跳过 | 原始日志 |
|---|---:|---:|---:|---|
| SQLite全量1312 | 1251 | 0 | 61 | logs/backend-full-all-sources-1f189c3.log，816.678秒 |
| PostgreSQL17.11全量1312 | 1282 | 0 | 30 | logs/postgres-full-all-sources-1f189c3.log，1008.032秒 |
| 历史/财务seed备份恢复 | PASS | 0 | 0 | 99表1081行128迁移4文件；源不变cleanup complete |
| 恢复后真实私有HTTP | 4 | 0 | 0 | logs/restored-private-http-1f189c3f74fd.log；403/403/200/404 |
| 真实GPG新发布/损坏拒绝 | 2 | 0 | 0 | logs/real-gpg-publication-1f189c3.log；临时文件清理完成 |
| 加密发布修后故障回归 | 6 | 0 | 0 | logs/operations-backup-publication-post-fix.log |
| 全来源Vitest | 720 | 0 | 0 | logs/vitest-all-sources-673ae37.log，77文件 |
| 既有合成UI库升级0103 | PASS | 0 | 0 | artifacts/upgrade-existing-synthetic-0103.json；84个原CRM表400行与媒体摘要不变 |

综合CI41829100528的Backend和PG已SUCCESS，Frontend继续等待；以上本地结果不预写为完整CI通过。详细跳过原因与数量见full-regression-results.json。

## 候选CI失败及前端最小补修

CI41829100528（代码1f189c3）实际：Backend1312项，1254通过/58跳过；PostgreSQL1312项，1282通过/30跳过。Frontend的Node177与Vitest720通过，但Playwright主套件243通过/2失败，其余25通过：合计268通过、2失败、0跳过。两个失败均在ISS039的Python全库快照spawnSync调用，退出status为null，原日志未打印error.code，不能把推断冒充原始错误消息。

默认Node缓冲复现同型故障：stdout1114113字节、ENOBUFS、SIGTERM、status null；完整CRM快照没有丢行。补修使用32MiB有界缓冲并输出实际字节计数/启动错误诊断；原退出码0断言、全表全字段比较、金额分配/取消/权限等断言及120秒上限均保留。新大于1MiB Unicode/启动错误回归2/2，ISS039实际Chrome2/2（39.7秒）；默认Node179/179、0失败/取消/跳过（33.150秒）。完整集成套件仍须新SHA CI验证，不能以定向结果替代。

失败CI原始artifact下载摘要与官方43e94fb972987300f282690b6d2472f26b704a0fbbdcc1035576f682d6bf70fb一致。23份原始失败上下文/套件日志/summary无损保存在ci-41829100528-failure-evidence.zip，完整57MB归档留在本包.tmp文件，未将Chrome profile发布进Git。连接器返回的完整job解码日志保存在logs/ci-*-plugin-41829100528.log（去UTF-8 BOM，不是原始传输ZIP字节）；命令行网络重置/TLS与ANSI输出拒绝不作为测试通过或产品失败。

全量中因ISS018_COMMAND_PG_BIN未设置跳过的8项已另行按原命令专项启用：8通过、0失败/跳过，320.691秒，正常恢复、摘要/版本/介质损坏、恢复工具故障、错误数据库和production-stage拒绝均保留断言，临时资源全部按预期清理。日志logs/backup-command-all-sources-1f189c3.log。全量原30跳过数字不改写，也不把重跑数量相加成1312+8个不同测试。

财务证据路径补修7a896d0：默认隔离根目录下，普通资金页面2/2（16.9秒）、认证审批2/2（19.9秒）；PNG、实际PDF/CSV/HTTP记录随本次目录保留。候选CI1f的打印输出spec实际7/7，其中5个为真实Chrome打印对话PDF输出，另外2个为资源保护；不把这个合成子集当用户已接受完整成品/分页。最终CI仍需重跑同一完整套件。
