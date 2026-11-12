# CRM-STATE-CLOSEOUT-05

共同起点 `46738366350c5f494e3fa62b2b209385fb8f340b`。开始时从 SJERP fetch 的 U4 分支 HEAD 与该提交一致，C5 相关入口未见后续增量。工作树及浏览器、API、Vite、SQLite 和媒体目录独立。测试使用 runner 启动的认证 `codex` 账号与专属 C5 合成客户、联系人、跟进和需求。

U4 的 `remaining.md` 对照来源为 `c21a1060cb99bdf6bda33a07c7ba01b990f4878f`。核对至固定起点，`ResourcePage.vue`、`EntityDetailModal.vue`、`NewProductReminders.vue`、工作区管理器及 API 拦截器无差异。保留旧联系人重名、跟进附件和桌面保存生命周期记录作为补充。C5 新结果以本包逐组合日志为准，旧测试未抵充缺失的真实浏览器验收。

## 复现与修复

- CRM-02/04：390 px、125% 下，客户／联系人保存被明确拒绝时，旧浮动错误提示会占据表单底部操作区域。将这两类写入错误显示在各自表单的底部，并按表单重置和重试清除。输入、所属客户及稳定的真实保存路径保留。[旧联系人截图](baseline/CRM-04-rejected.png)
- NPD-01/02：需求保存被拒绝后，旧错误出现在页面上方，窄屏从提交按钮处看不到。真实过期编辑得到 409。现在错误在表单按钮附近，过期版本停止提交，用户可继续查看草稿，或确认放弃后读取最新版本并重新编辑。新建失败仍保留原请求键。 [旧过期版本截图](baseline/NPD-02-stale.png)
- CRM-03：联系人详情返回客户后，客户和联系人标签正确，焦点实际落到 `BODY`。问题在公共 `EntityDetailModal.vue` 的 `drill`／`backClean`。已交 U4。建议加载前记录来源关系按钮的稳定目标，返回加载完成及 DOM 更新后聚焦重建的触发控件，无法定位时聚焦详情内关闭按钮。回归须保留未保存保护和产品嵌套详情原路径。C5 保留必验失败断言。
- 初次脚本调试的挂起拦截清理、禁用的预填客户选择框、textarea 值读取、搜索模糊计数均属于采集器问题。最终以精确业务方法和路径拦截，等待拒绝响应再解除，成功后使用实际数据读回及精确归属和记录数核对。

## 执行入口及证据口径

- Chrome 启动独立 profile，使用真实 Chrome 设置变更页面缩放。截图以 CDP 截取实际视口，每份 JSON 记录 Chrome 版本、有效视口、DPR 和失败原因。受控 POST／PUT 挂起最终返回 HTTP 400。NPD-02 使用同一认证账号下两个独立浏览器工作区实例，PATCH 200／409 来自实际 SQLite 服务。另在隔离 PostgreSQL 实跑竞争写入、作废和幂等。
- CRM-01/03 的只读 **界面** 使用认证会话原响应，仅投影浏览器内已有的只读权限矩阵。详情、联系人与返回的数据均来自实际隔离后端。此方法未改动后端权限，不能作为独立的服务端授权验收。
- C5 运行器命令从 `frontend/` 执行 `node scripts/run-isolated-browser-tests.mjs --business-test crm-state-closeout-05.spec.js`。以 `ISOLATED_CODEX_TEST_SUPERADMIN=1` 及现有忽略凭据文件注入认证，`ISOLATED_TEST_PYTHON` 指向本机锁定依赖环境。无筛选变量时执行全部六组。
- Vitest 从 `frontend/` 执行 `npx --no-install vitest run tests/new-product-reminders.spec.js tests/customer-ux.spec.js tests/customer-followup-races.spec.js tests/crm-saving.spec.js tests/follow-up-safety.spec.js tests/follow-up-richtext-and-attachments.spec.js --environment jsdom --maxWorkers=2`，53 项通过。生产构建 `npm run build` 通过，Vite 报告现有主包大于 500 kB。
- PostgreSQL 使用仓库 `docs/uat-evidence/history-product-sku-linking-01/run-postgres.py --postgres-bin <本机 PG17 bin> --test-label crm.tests.test_new_product_reminders`，临时集群 9 项全部通过，包含 `test_postgres_competing_edit_void_and_duplicate`。 [日志](postgres.log)

## U4 接收清单

接收 C5 的两个业务源码文件、对应回归及 `crm-state-closeout-05.spec.js` 和 C5 种子。现有 runner 已实际通过独立文件入口执行，公共测试矩阵应加入专属 `codex: true` 配置，给该配置独立数据库、媒体、端口和用户目录。先处理 CRM-03 焦点并在最终 U4 候选复跑 C5，六组内所有必验断言均须通过。通用 CI 即使成功，也不替代这个独立配置。公共台账交 U4。

## 最终专项结果

[六组状态矩阵](matrix.md)对应源码 `0c463f6d739d07c14eca50ae4cce9135171b9cf1`。42 项通过，CRM-03 六次焦点断言失败。保留原基线截图及早期采集记录。最初完整运行包含 1366 px 两组较早采集版本，生产代码一致。两组已在最终源码复跑。

现行 CRM 保存兼容回归用同一独立入口选 `crm-saving.spec.js`，设 `ISOLATED_PLAYWRIGHT_USE_CHROME=1`，8 项通过。此前未指定 Chrome 的尝试退出非零。NPD-02 的 390 px、125% 调试曾等待后台页响应超时，前台激活后补跑及最终矩阵均通过。

[完整采集日志](chrome-run.log) · [1366 / 100% 复跑](chrome-1366-100-recheck.log) · [1366 / 125% 复跑](chrome-1366-125-recheck.log) · [NPD-02 补跑](npd-recheck.log) · [CRM 保存回归](crm-saving.log) · [Vitest](vitest.log) · [构建](build.log)
