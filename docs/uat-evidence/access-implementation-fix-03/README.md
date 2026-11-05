# ACCESS-IMPLEMENTATION-FIX-03

当前状态：修复已完成，冻结源码后的 Node 全量、Vitest、构建、受限登录 Chrome profile 和 PG17 安全专项通过；完整业务浏览器总入口本轮未实际运行，须在集成验收执行。首次 Node 全量超时保留。CI 因额度暂停，未运行。原报告及失败保留在 [ACCESS-IMPLEMENTATION-02](../access-implementation-20261105/README.md)。

基线 `642f3f1772cb8217a36b8c8b6a5e7f4d9e397f0a`。受限登录 profile 在全量入口作为独立第二次运行，普通 profile 排除它，完整入口不允许通过参数排除它；每次调用原有资源分配、身份校验和清理流程。首个 profile 失败后仍执行受限 profile，总退出失败。单文件入口仍独立运行。测试配置仅影响任务进程。

权限矩阵仅接受 JSON 布尔值；缺省字段仍为 false。完整请求在写入前验证，任何非法值返回 400；回归包含前行合法、后行非法，核对权限记录和审计未变化。

集成工作树只读核对时 HEAD `2536efe1a97dec0597ab7c5c28750eea25f47d68`：其运行器相对本包基线缺少上一轮登录 fixture、受限模式及 Chrome 的三处接线；本包以增量修改实现，集成时须核对两边改动，不整文件覆盖。未修改该工作树。公共台账中 ISS-003/051/097 涵盖权限矩阵和正式身份边界，未找到对字符串布尔值的单独登记；按要求交集成协调处理，不重复创建 Issue。

## 已知结果

- `npm run test:unit` 首次：181 项中 180 通过，1 项并行隔离测试在 120 秒取消，退出 1；[原始日志](logs/node-full.log)、[阶段分析](logs/node-timeout-analysis.log)、[进程计数](logs/process-count.log)。两个子运行器均报告停止并完成清理；存在其他进程，但根因尚未证实，没有终止其他工作树进程，也未增大超时。
- 冻结后 `npm run test:unit`：182/182，退出 0，[完整日志](logs/node-final.log)；包括全量入口分为两个 profile、身份配置、fixture、禁止排除以及第一 profile 失败后仍运行第二 profile 的回归。
- 冻结后 `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：78 文件 / 725 项通过，退出 0，[日志](logs/vitest-final.log)；`npm run build` 退出 0，[日志](logs/build-final.log)，保留大包警告。
- `run_postgres.py --implementation`：首次沙箱内启动因 `pg_ctl` 创建受限令牌失败退出 1，[日志](logs/postgres.log)；隔离环境外、任务自建 PG17 集群重跑 65/65 通过，退出 0，集群清理完成，[日志](logs/postgres-retry.log)。包含权限矩阵、最高角色、真实行锁并发、审计和相关权限测试。
- 冻结后 PG17 `--security-only`：16/16、退出 0，行锁并发及事务回滚通过并清理，[日志](logs/postgres-frozen.log)；`--suffix-scope-only`：2/2、退出 0，客户范围和财务导出通过并清理，[日志](logs/postgres-scope.log)。首次失败的沙箱运行因清理时未找到 PID 而留下任务临时目录 `sunjack-access-pg-cs_spd4a`，没有连接现有数据库；应在确认归属及无进程后清理。
- `node scripts/run-isolated-browser-tests.mjs --business-test access-session-real.spec.js`：独立合成账号及 SQLite、MEDIA_ROOT、端口；4/4 真实 Chrome 通过，退出 0，资源清理完成，[日志](logs/browser.log)。桌面与 390px 截图在 `browser/evidence_dir/`。全部业务总入口本轮未实际完整执行，不能以单 profile 通过声称全量浏览器通过。
- 上轮 SQLite 后端全量为 1416 项、81 项跳过，[原日志](../access-implementation-20261105/logs/backend-complete.log)；本轮改动后不将它冒充当前全量，最终集成全量由协调任务执行。

## 上线门槛

登录限速或锁定目前没有实施。目标环境的部署/安全负责人应在可信反向代理或独立认证防护层落实来源 IP 与账号维度的速率限制、失败审计与告警，明确多实例共享计数、可信代理头和锁定恢复策略；内测前由安全测试人员使用合成账号从多个来源验证连续错误被限制、正常账号仍可登录、不可伪造来源头绕过、告警生效及过期后恢复，并保留环境配置和结果。不能将本地测试或单一 IP 限制视为完成。正式 HTTPS、cookie、CSRF、真实员工生命周期和全站动作/数据范围仍需目标环境验收。

无迁移；未更改日常 RBAC、真实员工、共享台账或业务数据。提交使用 `[skip ci]`，不运行 GitHub Actions。

日志中的本次隔离随机令牌已脱敏，`*.raw.gz` 保留脱敏后的原始字节；文本副本清除行尾空白。截图和账号均为合成资料。
