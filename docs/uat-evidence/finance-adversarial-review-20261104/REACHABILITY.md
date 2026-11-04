# 持久层与受支持入口审查

审查固定基线8087f2c；不是对任意插件、未来历史包或生产DB管理员的全称证明。

| 入口 | 当前观察 | 结论边界 |
|---|---|---|
| `/finance-ledger/preview/` | normalize，无FinanceFact创建 | 模拟/待核实可预览，非过账 |
| `/instructions/` | service.submit创建指令及审计；真实性不强制verified是为了保留待核实草稿 | 不能把保存指令视为实际资金 |
| `/approve/` | service.approve检查真实两人及verified | 模拟/待核实与自批拒绝 |
| `/post/` | service.post检查payload hash、verified、审批、文件、额度并同事务创建唯一事实/审计 | 已覆盖7种kind；同键重放不重复事实 |
| cancel/fail/classify/match/review | 改指令受控状态或追加专用历史，不直接插入任意FinanceFact | 新增分类/核对漏洞另列ADV01/02；不是任意字段写接口 |
| 旧银行register/confirm | 既有source verified/权限/文件机制；新账户表不通过旧API任意创建 | 原回归继续执行，隐藏候选服务层额外验证 |
| Django Admin | 仅显式模型注册，无FinanceFact/FinanceInstruction | 测试验证未注册，不存在此后台新增表单路径 |
| 管理命令、任务、历史执行器 | `reachability.json`列出实际文件/行/摘要；当前FinanceFact创建在finance_closeout.post，其他引用为报表读取/备份/测试合成种子 | 未发现当前受支持命令或任务bulk_create事实；不涵盖移动中的历史接通代码 |
| FinanceFact QuerySet.update/delete | OperationLogQuerySet保护，实际update回归拒绝 | ORM写保护，不声称所有原始SQL被禁 |
| bulk_create / DB管理直写 | 原save方法不会执行，数据库未约束truth verified；在回滚事务中可插入模拟行 | 可信代码/数据库管理员能力，**未确认普通API可达漏洞**；建议防御性约束和新调用方回归 |
| FinanceInstruction普通QuerySet.update | 可用于可信故障注入；post摘要检验发现payload异常 | 不是受支持ERP操作；状态字段DB层强化需与现有服务写权限设计协调 |

权限模拟只在隔离自动测试中override_settings，不改运行服务APP_STAGE/DEBUG/RBAC。开发超级管理员仍按原服务器入口获得完整权限；不能把开发模式全部可用当作正式员工授权路径成功。
