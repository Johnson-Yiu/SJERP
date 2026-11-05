# LOCAL-RELEASE-VALIDATION-03（执行中）

固定起点 `bcdcb57545f121b8a4102f352c74008b47372035`，统一分支 `codex/r1-prelaunch-consolidation-20261104`。本包不修改或重试延期的完整打印及分页；报价 XLSX、财务 CSV 和 Packing List 等实际文件不在该延期范围。GitHub Actions 按用户决定 `NOT_RUN`，不视作通过。

## 已复现与修复：ISS-121 来源长度

上轮候选预审已指出来源编号长度及跨组作用域缺少边界证据。本轮以合成工作簿复现：超长来源系统名和组编号在 SQLite 被接受并创建申请，而模型分别限制 160 和 120 字符；首次反例见 `logs/history-source-boundaries-before.log`，2 项失败。SQLite 不证明 PostgreSQL 的运行结果。

预检现在对超长组号、系统名和实际存储的来源编号（包含复合明细编号）标记阻断；申请提交前拒绝超长内容，旧申请执行前再次验证，不截断历史来源。SQLite 边界测试验证 120/160 上限、超限拒绝且无申请、跨组同系统同类型同编号冲突、其他系统独立、哈希请求键长度、预检错误与旧申请防护。`logs/history-preflight-boundaries-final.log` 共 45 项、1 个 PostgreSQL 专项跳过、其余通过；检查点 `b27b9a0fddfe20b706bf4762e9e38168ac0333d1` 使用新建 PostgreSQL 17.11 专项：55 项通过、无跳过，含边界、历史并发及原三财务反例；102 表、1218 行、133 迁移及 5 个媒体文件的历史/财务/运营备份恢复核对通过，见 `logs/postgres-b27-targeted.log` 与 `pg-baseline-targeted/`。此结果不能代替最终集成候选全量。首次模块名拼写错误造成的 62 项/1 error 及修正后 64 项/8 skip 记录分别见 `logs/baseline-history-finance.log`、`logs/baseline-history-finance-corrected.log`。以上为本包源码修改前后各自的局部证据，不代表最终集成全量。

## 可复现本地入口

`run-local-validation.py --sha <完整HEAD> --python <锁定Python绝对路径> --postgres-bin <PG17 bin绝对路径> --openssl <OpenSSL绝对路径> --run-name <新目录名>`；运行前先 `python -m pip install -r backend/requirements.lock`。入口拒绝与 HEAD 不同的 SHA 或有未提交应用源码，逐阶段检查源码状态并保存命令、退出码、日志 SHA 及摘要。SQLite 全量使用内存库，升级检查使用新建专属 SQLite 文件；PostgreSQL/备份复用原专属临时集群保护，历史 Chrome 复用原隔离脚本。真实浏览器沿用九组配置，唯一额外排除 `iss037-print-output-acceptance.spec.js`；原始打印测试未删除或修改。入口不连接现有数据库，测试合成数据与临时媒体，GitHub CI 为 NOT_RUN。

错误 SHA 和应用源码有未提交变化均在创建测试目录前拒绝，分别见 `logs/runner-wrong-sha.log`、`logs/runner-dirty-source.log`。该入口预检模式在 b27b 及运维接收后的 `c3e68b9633dbdde5589dbc4d9f8acfcc8925184f` 分别执行；锁定依赖、Django 检查、迁移图、含合成旧客户的 SQLite 0103→最新升级通过。其后发现 Windows 可执行文件查找差异，两次预检在 Node 路径校验阶段失败，证据 `preflight-locked-path/result.json` 和 `preflight-locked-path-fixed/result.json` 保留；改为真实 Node 子进程校验后 `preflight-node-python/result.json` 的预检全部通过。入口的完整运行仍需在稳定来源集成后验证；不可将语法检查说成全量通过。运行期间以周期检查监测源码，不能替代操作系统不可变挂载；应使用专用冻结工作树并禁止其他进程修改。

[87 项代码、断言和证据索引](REVIEW-INDEX.md) 是由原复审映射和 ISS-121 补充生成的待审入口；87 个条目均有测试断言或视觉采集校验入口。已检查 829 个代码/断言/资料链接及行号可定位，但链接存在不证明业务正确；断言候选须由独立审查者核对是否覆盖具体问题，不等同独立接受。

## 待完成

运维工作包完整稳定 SHA `250c3b7f55585acccb73b2efc1b0993605be0b0b` 已核对远端并合入；其本机 Linux 不可用及跨 UID 等未验限制保留。等待导出包完整稳定 SHA；接收后检查冲突和原始证据，并对同一最终候选重跑所有适用全量。真实 Linux 跨 UID 和目标生产环境未执行时维持各自待验；不以 Windows 模拟替代。不得关闭待独立复审 Issue、合并 master、部署或导入真实数据。

`c3e68b9633dbdde5589dbc4d9f8acfcc8925184f` 的 Node 全量 179 通过、0 失败/跳过，使用锁定 Python；发布日志中 10 处一次性隔离 token 已脱敏，原始日志保留本地且记录原始/发布 SHA，见 `logs/node-c3-locked-redacted.log` 和 `logs/node-c3-redaction.json`。不以该运行替代最终整合源码的 Node 全量。历史 Chrome 脚本现支持 `ISOLATED_TEST_PYTHON`，原默认路径和断言不变。

预检结果 `preflight-node-python/result.json` 中 Node 启动的 Python 为锁定环境，Django 6.0.9。入口自检失败记录 `preflight-locked-path/result.json` 与 `preflight-locked-path-fixed/result.json` 不删除；失败时后续步骤为 NOT_RUN，不能记为通过。

同一检查点 `c3e68b9633dbdde5589dbc4d9f8acfcc8925184f` 有效 Vitest 全套 78 文件、725 项通过，见 `logs/vitest-c3.log`；源导出包尚未接收，本结果不替代最终集成全量。

已记账历史资金补充合成测试：审计更正的申请细节记录来源 ID 与资金事实 ID，审核事件关联申请，原资金及映射保持不变、不能把已记账指令作为失败/取消重提；`logs/history-posted-correction.log` 1/1 通过。当前更正 `details` 仍为自由内容，系统未自动验证填写的来源/事实 ID 或凭证与对应原件一致；真实业务更正/退款映射及凭证对应仍需业务规则与独立复核，不得把该测试扩大为所有更正类型已支持。
