# 失败对照

基线 SHA：`54e715bdc568b80ba624186fecd866550676cf38`  
最终计划：199 个 Playwright 用例；最终 199/199 通过，编排器退出码 0。

| 执行记录 | 计划/实际 | 通过 | 失败 | 结论与证据 |
|---|---:|---:|---:|---|
| 用户提供的初始回归摘要 | 199 | 186 | 13 | 失败类别为夹具、隔离环境变量、ISS-055 身份契约和 Vite teardown。首轮原始机器日志未随任务提供，`logs/initial-run-reported.md` 仅保存用户摘要，不能逐项映射 13 个失败堆栈。 |
| 初次未充分隔离的诊断运行 | 193 | 191 | 2，另 ISS-055 seed 启动失败 | ISS-022 列表数量受共享 DB 的其他采购单影响；ISS-035 重开后列表数据被前置测试交叉污染。两场景独立隔离后通过。ISS-055 seed 缺 `django.setup()`，之后补齐，并由真实员工会话组通过。日志见 `logs/first-split-attempt/`。 |
| ISS-055 setup 修复后的全量中间尝试 | 199 | 198 | 1 | `fulfillment-receivables.spec.js` 模拟请求在 `button.click()` 返回后才进入 route handler，测试立即读取 `writes` 时偶发仍为 0。夹具现在显式发出“请求开始”信号，测试等待后保留原有 pending、禁用按钮、重复点击仅一次写入及履约状态断言。失败上下文见 `logs/fulfillment-receivables-flaky-error-context.md`，该次完整阶段日志见 `logs/second-full-attempt/`。 |
| 首次按数据边界拆组的完整运行 | 199 | 198 | 1 | 普通组 189/190；其余 ISS-022 1/1、ISS-028/035 2/2、ISS-055 6/6。唯一失败是 `shared-report-templates.spec.js:61` 的 `employee.reload()` 收到 `net::ERR_ABORTED; maybe frame was detached`，30 秒测试超时。原始阶段日志和 JSON 汇总见 `logs/suite-attempt-189-of-190-shared-report-timeout/`。 |
| 共享报表模板单独复现 | 1 | 1 | 0 | 同一断言、同一默认 timeout，在全新隔离 DB/服务和浏览器进程中 22.7 秒通过；原始日志为归档目录中的 `shared-report-targeted-repro.combined.log`。这支持长套件浏览器生命周期/页面导航累积的运行稳定性判断，但不足以证明一个更底层的 Chromium 根因。 |
| 最终完整套件 | 199 | 199 | 0 | 189 + 1 + 1 + 2 + 6 分组全部退出码 0。共享报表模板独立进程 24.8 秒通过；汇总见 `suite-run-summary.json`，完整日志见各阶段 stdout/stderr。 |

## 首轮 13 项原始日志限制

仓库及当前工作区中均未找到用户所指首轮执行的原始 Playwright 日志。因此本报告不声称知道 13 项各自的名称或精确堆栈，也不把后续复现日志伪装成首轮原件。已知摘要和独立 Vite teardown 复现分别保存在 `logs/initial-run-reported.md` 与 `logs/pre-fix-webserver-reproduction.md`。

## 修复与验收映射

- 共享 DB 下 ISS-022/ISS-035 的列表污染：改为单独隔离 SQLite/媒体目录；最终两项类别均通过。
- ISS-055 身份契约：隔离 seed 创建专用员工、员工档案和受控角色；浏览器通过真实 Django admin 登录建立 session，并断言 RBAC 开启、开发超级管理员关闭。禁止伪造 current-operator 响应。最终 6/6 通过。
- 字体/页面请求和 API/Vite 地址：环境变量从隔离运行器单一注入，运行前后校验 API 身份、数据库路径、MEDIA_ROOT 和 Vite `/api` 代理。
- Windows Vite teardown：不由本地 Playwright `webServer` shell 管理服务；运行器仅停止自己启动的进程树，检查端口释放后清理自己持有标记的临时资源。现有 CI CLI 配置仅在 `CI=true/1` 时保留 `webServer`，工作流未改。
- 收货模拟提交竞态：测试夹具给出请求开始信号，测试先等待请求进入再验证 pending 状态及重复写入防护；不改变预期写入次数、不增加 timeout。
- 长组导航中断：共享报表用例移至单独浏览器生命周期。全量 189 项组与独立 1 项组均通过，原用例和断言完整保留。

没有删除或 skip 用例，没有放宽断言或测试 timeout。首次失败记录和最终通过记录都保留，便于按文件对照。
