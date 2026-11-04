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

补充失败限制：finance-browser-integrated.log 是一次错误传入两个 --business-test 参数、runner在启动前拒绝；后续分为两条合法命令各2/2。postgres-finance-seed-319941c.log 是沙箱 pg_ctl restricted token 错误、临时资源清理完成；沙箱外重跑另用新文件，不能覆盖旧失败。原生完整打印/分页按用户决定延期，不将本地未跑的7个场景称为通过，CI仍保留原场景。

最终同SHA三项CI、全来源PG全量及新财务seed恢复尚待结果，不提前登记PASS。历史版本、开发超级管理员和合成session都不代替正式业务认证或目标部署验收。
