# 最小补丁建议（未应用）

固定依据8087f2c。仅为统一集成任务提供可复核方向；本包没有修改以下文件或契约。

## ADV-01：有效分类与匹配一致

位置：`crm/services/finance_closeout.py::match_transfer` 和 `match_historical_transfer`。

1. 提取受控的有效性质读取：最后一条FinanceClassification存在则取该性质，否则取原FinanceFact.nature；与fact_data/reporting_events同口径。
2. 在既有账户及事实锁范围内重新检查有效性质，保持已更正事实拒绝、不同账户/同本金、两端唯一和既有权限校验；不改历史nature。
3. 按新事实/历史混合两条路径验证分类为对外支出后不能隐藏金额；补分类与匹配竞争，任一顺序都不能出现“有效expense已匹配”状态。
4. 当前classify禁止直接设置internal_principal。不建议本轮为修复此缺陷擅自开放新分类入口；保留已有合法两端核实规则及契约。

## ADV-02：核对指纹包含本金核实

位置：`balance()`核对指纹，`reconcile()` / API list展示现有指纹比较。

将影响该账户/期间事实的FinanceTransferMatch、FinanceHistoricalTransfer记录标识及必要关联加入稳定有序指纹；新增匹配须使旧review返回needs_review，余额计算不变，旧review不覆盖。覆盖跨日、跨期、新旧混合、重复匹配不重复改变、匹配与核对竞争。不要以重算公司汇总代替逐账户核对。

## ADV-03：授权角色路由

位置：`FinanceCloseoutViewSet`与既有ModuleActionPermission。

最小模块声明建议 `permission_module = "finance"`，另核对各动作的create/update/view/export映射与视图已有ledger.access一致；不要用allow-any或切回development绕过。保留transactions查看、global数据范围、关联订单及来源可见性。尤其preview为只读而通用POST动作默认为update，需补只读财务角色正向预览及不能写入的测试，不能只加superuser成功路径。真实运行环境RBAC开关不变。

## 持久层建议（不是已证实API漏洞）

后续集成可评估FinanceFact增加与当前服务一致的`truth=verified`数据库约束，先只读审查旧数据；不得批量改历史真实性来通过迁移。继续禁止受支持调用方直接bulk_create资金事实。FinanceInstruction普通QuerySet.update可用于可信代码/DB故障注入；API没有此入口。应收敛运行账号权限和内部写入契约、补实际接通历史执行器回归；不要把拥有应用源码/DB写能力等同普通ERP用户能力。
