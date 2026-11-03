# R1-ISS121-PREFLIGHT-FIX-01

状态：`FIXED_PENDING_REVIEW`；等待独立复审。基线为 `0ccbf6c4a776fef5be74ad71ca4b6df0ba12e813`，继续使用 `codex/r1-iss121-history-import-preflight-20261103`。ISS-121 整体仍为 `BLOCKED`；本次没有执行正式导入。

## ChatGPT 复审意见与修复

复审指出整单 `partial` 不要求每个订单行都部分履约：某一行完成而另一行未开始，仍可能构成整单部分履约。修复前先运行新增回归；销售和采购两种情形均在旧实现上失败，原始输出保存在 `fix01-before-regression.log`，该次命令退出码为 1。

现在仅在来源覆盖完整、关联行及履约记录足以核实时，逐行比较各行自己的已核实净履约量与该行数量，再综合判断整单。不同 SKU 或单位之间不相加数量。整单标记 `partial` 而全部行均未履约或全部行均已履约时，对订单提示人工核对；一行完成、另一行未开始或各行均部分履约均不产生该矛盾提示。原有订单 `partial` 的一般性人工核实提示仍保留。

来源覆盖不完整、真实性/履约状态未知、证据缺失或行数据存在歧义时，不推断缺失履约事实，订单继续提示人工核实。原有单行负数、超发/超收与超额冲销检查及关联组汇总保留。履约状态与收付款计划结清状态分别检查；不根据计划状态推断订单履约完成。

## 验证与证据

- `fix01-before-regression.log`：修复前单项回归，销售与采购两个 subtest 均重现误报；退出码 1。
- `fix01-focused.log`：修复后的销售/采购状态矩阵定向测试；2 tests，退出码 0。
- `fix01-environment.log`：隔离环境变量、Python 3.14.5、`pip check`、安装版本、Django system check 与迁移检查的完整命令输出及各自退出码。依赖版本与 `backend/requirements.lock` 对应；`pip check` 通过、迁移检查 `No changes detected`。
- `fix01-regression.log`：预检、CSV 上传 413、安全 CSV 和历史订单回归的完整输出与退出码；67 tests，退出码 0。PowerShell 汇集 stderr 时对空输出行显示 `System.Management.Automation.RemoteException`，Django 汇总为 `OK`；负向路径的 400/403/413/503 日志属于测试请求。
- `run-fix01-tests.ps1`：上述环境/回归日志的复现命令。其测试数据库为内存 SQLite，媒体目录由测试创建临时目录。
- 既有模板一致性测试读取实际交付的 XLSX，核对全部 10 张工作表及每张数据表的表头与服务端 schema；空模板拒绝，填入合成记录的模板副本可预检。
- 代码、测试、报告和脚本的 `git diff --cached --check` 通过。包含原始日志的全量检查对 `fix01-before-regression.log:128` 的 unittest 输出行尾空格给出提示；为保留原始输出未改写该行。

新增用例在销售和采购分别覆盖：一行完成另一行未开始、每行部分完成、全部完成、全部未开始、部分冲销、不同 SKU 和单位、未核实履约、覆盖不完整、单行超额履约、净履约为负和冲销超过原事件，以及 `open`/`completed`/`cancelled`/`partial` 与收付款计划结清状态的独立性。测试比较预检前后业务及审计记录快照和媒体目录，并检查请求期间没有 INSERT、UPDATE、DELETE 等写入 SQL。

## 范围与后续

本次未修改公共 `PROJECT_ISSUES.md` 或 `PROJECT_PHASES.md`。建议后续统一集成时追加该 ChatGPT 复审意见、修复及本记录，不删除既有验收结论；ISS-121 继续 `BLOCKED`，待实际启用日期、银行基准、真实凭证与受控导入方案另行验收。已确认的期初余额、资金确认和库存盘点原则不重新列为待决。

本地 PostgreSQL、真实历史资料及生产环境未验证；SQLite 证据不代表 PostgreSQL 或生产验收。未合并 BATCH-02、master，未部署、启用正式 RBAC 或关闭 Issue。GitHub Actions 应以本分支推送后实际运行和最终 SHA 为准，在交付消息中单独报告。
