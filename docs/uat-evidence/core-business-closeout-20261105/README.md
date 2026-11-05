# CORE-BUSINESS-CLOSEOUT-01 开发侧验收

基线：`bcdcb57545f121b8a4102f352c74008b47372035`。独立分支：`codex/core-business-closeout-20261105`。核心修复提交：`a52f85ef4196e296aa42062d872fdfca48662d6f`；Chrome 初版检查点：`6f51368f60de9114bac6a6b4190a2504e4478aca`；最终测试检查点见 tested-source.json。本报告是开发侧验证，等待集中独立复审，不关闭 Issue，不表示上线就绪。

## 先行核对与实际缺口

先读取 AGENTS、两份台账、REVIEW_PROTOCOL、integration-closeout-02 的 REVIEW-BACKLOG 及相关模块最新代码/证据。[MATRIX.md](MATRIX.md) 保留补修前六项矩阵；旧数量分摊、欠款被履约掩盖等历史描述不能单独证明当前仍有缺陷。

### C01 普通库存缺少仓库/批次强制扣减约束：已复现并补修，待独立复审

历史盘点基准存在时才启用 location_quantity 检查，导致无盘点基准的普通库存可能借用别仓/别批次余额。合成 A 仓 LOT-A 余额不足（2 件欲扣 3 件，或原批次已耗用）、B 仓 LOT-B 仍有库存时，原代码允许 A 仓发货、采购收货冲销、手工入库冲销、手工出库或将已耗用入库移往另一仓。

`before-repro.published.log` 原始六项失败中的五项证明这些路径；拒绝修复后仍须保持全部业务快照不变。服务现在始终检查实际位置余额。手工更新按“撤回原流水效果 + 应用新流水效果”核算两个位置，未耗用入库仍可合法调整，不一概禁止编辑。保留全局可用库存/预留、历史盘点专有约束、原仓库和批次、收发冲销审计及幂等事务。

### C02 成本保存使用取消前的旧订单对象：已复现并补修，待独立复审

CostInput 解析订单后到真正保存之间，订单可能被取消。原 save_costs 只锁 PO，prepare_costs 读取旧 Order.status，能把成本写到已取消订单。补修按“PO → 按主键排序的相关 SO → SKU”重新锁定并读取订单，涵盖新旧成本归属，按最新状态验证；目标已删除时返回明确校验错误。未增加逐销售订单授权，没有改金额分摊公式或采购修改权限。

### C03 采购付款与审计不在同一事务：已复现并补修，待独立复审

补验应付闭环时，发现 PurchaseOrderViewSet.pay 的 record_contract_payment 已结束内部事务，但两条 record_operation 随后才写入。注入第二条审计失败后，原代码留下付款 6、计划已核销 6 及首条成功审计。`before-payment-audit.published.log` 和 `payment-audit-results.json` 是失败及前后快照证据。

仅给该采购接口增加 transaction.atomic，将原付款服务及两条审计纳入同一事务；不改账户资金服务、付款分配、权限、模型或金额规则。新反例先失败后通过，且同次正常付款可重试成功。新增完整收货后仍欠应付 18、分次支付 6/12 后余额为 12/0 的 API 对照；补充界面供应商付款 6 后待付 12 的真实 Chrome 操作。

## 六项业务覆盖说明

| 范围 | 本轮新增/复用的验收 |
|---|---|
| 销售 | 独立 API 从报价版本创建 SO、确认、两次发货；未全发拒绝完成且无副作用；完成后仍欠 60，分次收齐为 0，退款后待收 10；Chrome 真正点击完成履约并重载验证待办 |
| 采购 | 实际 API 独立 PO，无 SupplierSKU 不自动建档；明确保存的合成协商付款条款生成应付，部分收货不可取消、冲销不抹应付、未付款且有效收货归零才取消；共享采购变更归属后两个 SO 的关联和流水来源仍保留 |
| MOQ/单位 | 当前 SupplierSKU 按 PO 合计基础单位，草稿可保存，低 MOQ 正式下单需例外原因；复用并实际运行 test_purchase_moq、test_trade_units、test_actual_packing 等全量范围，不另定阈值或快照优先级 |
| 库存/预留 | 新增普通多仓/批次反例和合法对照；公司存货放第三方仓的余额独立保留；历史盘点/第三方物权边界通过已有 history_operational_inventory 回归验证，不修改历史数量 |
| 成本 | 3000/2000/5000 商品金额 + 1000 运费得到 300/200/500；总额 11000；跨 SO 调整、旧版本拒绝、零基数费用拒绝、取消及删除目标拒绝；不改财务账户服务 |
| 异常/并发 | 收货响应丢失同键重试返回原结果，变更内容 409，不同键同内容允许独立操作；审计失败回滚；真实 PG17 独立连接验证位置超量、成本版本/取消竞争、SO 取消与发货及 PO 取消与收货竞争，并复跑既有收货/冲销/同键并发 |

## 运行环境和证据边界

最终验证使用 CPython 3.12.16、Django 6.0.9、psycopg 3.3.6；16 项依赖与 requirements.lock 全部逐一一致，pip check 实际执行。早期 3.14 探索日志保留，不替代最终锁定环境验收。Node v24.16.0、npm 11.13.0。

SQLite/PG 数据均为合成数据。PG 工具每次初始化全新 PostgreSQL 17.11 集群，随机用户、源库/测试库、非 5432 端口和专属媒体，核验 data_directory；只清理本次所有权标记匹配的资源。没有连接业务数据库。它是本包隔离验收脚本，不修改项目公共运行器。

Django APIClient 证据表示调用真实 Django 路由/序列化器/服务但不经过网络；真正 HTTP 与 Chrome 证据另列于 chrome/*-http.json 和 chrome-fifth 日志。浏览器沿用开发超级管理员身份，不冒称真实登录/审计操作人；审计事务和操作者验证由隔离测试中的合成认证账号完成。

Chrome 加强验收两视口通过，最终截图 12 张（另保留 initial-* 原图），已人工查看最终桌面收货数量/记录/完成状态和窄屏退款待办。实际浏览器版本见 chrome/*-http.json；最终运行日志为 chrome-payment.published.log。页面无 pageerror；现有 Vue Transition 警告、无装箱计划的 404 和 ContractChangeRequest 未排序分页警告保留于原日志，未改成通过业务功能或新建重复 Issue。未修改可见 UI。

## 测试结果与命令

| 项目 | 实际结果 | 退出码 | 发布日志 |
|---|---|---|---|
| Django SQLite 全量 | 1430 项：1345 通过、85 跳过，0 失败/错误 | 0 | sqlite-closeout.published.log |
| Django PG17 全量 | 1430 项：1397 通过、33 跳过，0 失败/错误；测试库无残留、集群清理完成 | 0 | pg-closeout.published.log |
| 最终 PG17 专项 | 56 全通过、0 跳过，含新增 20 项、既有幂等/并发/审计及线程连接后置条件；测试库无残留 | 0 | pg-final-accepted.published.log |
| Node 全量 | 179 通过，0 失败/取消/跳过 | 0 | node-unit-low-load.published.log |
| 有效 Vitest 全量 | 78 文件、725 项全通过 | 0 | vitest-full-verbose.published.log |
| Node 专用字体回归 | 1 项通过，未混入 Vitest | 0 | node-typography.published.log |
| 前端生产构建 | 通过；保留既有大 chunk 提醒 | 0 | build.published.log |
| Chrome | 1440/390 两项真实流程通过，含收货、供应商付款、完成履约、收齐款及退款待办恢复 | 0 | chrome-payment.published.log |
| OpenSSL 环境补验 | 显式使用已安装 OpenSSL 3.5.6，两组 15 项通过 | 0 | openssl-verified.published.log |
| Django check / 迁移一致性 / diff check | 通过；没有新增迁移 | 0 | final-system-check / final-migration-check / final-diff-check 对应发布日志 |

两种数据库全量冻结于生产代码提交 `7edbde7c37674a7f73ba22335e5d9b90119722d3`。随后仅修改旧并发测试的连接清理及专属诊断参数，56 项已在测试提交 `4ffad5cf1b84639788ccf4c67a58cb10eacba59c` 重新完整执行。没有把较早全量称为包含了后加的连接断言：四个生产修改文件与最终版本逐个 Git blob 相同，见 source-integrity.json；全部前端产品、单测、基础设施、运行脚本及锁文件与统一基线的源树相同，前端复验没有产品代码差异。Chrome 脚本最终验证点为 `3afaacae1ac1bc0ff387793326fc2bf704c818f7`。

精确计数和源码绑定见 TEST-RESULTS.json、tested-source.json、source-integrity.json；SKIPS.json 列全 85/33 项实际跳过名称及原因。56 项是全量的相关子集，不与全量/新增 20 项重复累加。Node/Vitest/Chrome 的退出码均在原进程结束后由 shell 确认为 0。可重放命令见 COMMANDS.md。

### 失败历史及处理

- C01/C02：before-repro 六项均失败，修复后通过。C03：before-payment-audit 的快照证明付款/核销/首条审计残留，补事务后整组快照一致并正常重试。两类原始失败不改写。
- 早期新增测试的辅助函数、出库枚举、409 契约和付款条款前提误配已按现行接口校正，保留 flows-first、pg-first、pg-full 等日志；没有修改产品满足错误预期，也没有删除断言。
- 初次从仓库根启动无标签 Django 发现 0 项（sqlite-full），这是无效执行，**不计通过**；后续在 backend 目录真实执行完整 1430 项。
- 两组签名运维测试因 OpenSSL 未在 PATH 初始化失败；找到 D:/Program Files/Git/usr/bin/openssl.exe 后先补验 15 项，再以该显式工具路径重跑两种数据库全量。未修改运维实现。
- Node 的并行工作树冷启动两次超过原 120 秒上限，未加长超时或改运行器；相同命令在负载下降后 179 全通过。旧超时取消记录保留，不能当新业务缺陷重复登记。
- Vitest 的错误集合选择或未完成中止均不计通过；最终按仓库 CI 的有效文件集合执行 78 文件/725 项，Node 专用字体另跑。没有把单文件探针当全量。
- 人工看首次收货截图发现成功提示早于数据刷新，保留 initial-*，追加已到数量、入库记录和完成状态断言。一次窄屏重载失败的 DOM 为“正在加载”，补真实 workbench HTTP 响应同步后执行原 5 秒断言，两视口通过；没有改 UI 或延长断言时限。

### 旧并发用例连接清理（测试缺口，非新增业务 Issue）

pg-payment-accepted 的 56 项业务断言虽 OK，但仍有 2 条连接，Django 删除测试库失败，**驱动退出 1，不计整轮通过**。旧发货幂等用例的 worker finally 只有 close_old_connections；当前 CONN_MAX_AGE=60，它不保证关闭新鲜连接。普通单例复跑一度无故障，故未据此断言消失；新增 worker 连接关闭后置断言后，before-worker-connection-postcondition.published.log 直接得到 [False,False]，并再次出现两连接占用。

仅把该 worker 的清理改为 connections.close_all，保留新后置断言和所有原业务断言，未修改公共运行器、连接设置、TRUNCATE 保护、权限或业务。单例及最终 56 项均返回 0、测试库无残留。旧错误仍保留；专属 run_postgres.py 的 --test-label 只用于诊断子集，不替代全量。

## 边界与后续协调建议

- C01/C02/C03 作为本包修复待独立复审项交协调任务；不直接修改 PROJECT_ISSUES.md 或 PROJECT_PHASES.md。
- 保留旧冲突单位快照业务待核实边界，不推断历史优先级；不改主体快照、审批、权限框架、导出 helper、账户资金服务、运维或公共测试运行器。
- 本轮不覆盖真实客户、真实资金、正式历史导入、正式 RBAC、生产代理/部署环境；未重跑全站 Playwright，真实浏览器范围为本包关键流程，既有打印延期范围原样保留；不自行宣布上线就绪。
- CI 因额度不足暂停，全部本包提交含 [skip ci]，未触发、等待或重跑 GitHub Actions，不计为通过。
- npm ci 报告现有 5 项 moderate 告警，构建有 >500kB chunk 提醒；没有擅自升级依赖或改锁文件。


## 实际证据及建议同步项

- chrome/：12 张最终真实 Chrome PNG、两个视口的完整 HTTP/JSON；initial-* 保留第一次瞬时截图，不充作最终到货完成证据。
- pg-final-accepted-api/、sqlite-closeout-api/、pg-closeout-api/：合成数据的逐请求结果、16 类核心表前后快照；pg-race-results.json 汇总 5 项竞争的不同 PID 与实际响应。
- payment-audit-results.json：C03 补修前后付款/计划/审计差异；exploratory-dom/ 保留重载未就绪的实际 DOM。
- 48 条既有真实 HTTP 回归响应来自本轮实际执行的 ReviewCoreHttpTests，提取于 existing-real-http-regression.json，来源日志明确标注；不冒称新增功能或 APIClient 网络证据。
- manifest.json 对发布材料逐文件计算 SHA256；仅脱敏临时隔离 token/凭证并归一行尾；补证 DOM 的生成源码空行移除尾空白，原文摘要见 exploratory-dom/PROVENANCE.json；保留原日志字节摘要与本地原文件。GitHub 中日志使用 *.published.log，本地原始 *.log 不推送。没有上传集群、密码文件、签名私钥或数据库归档。

建议协调台账将 C01/C02/C03 关联到已有库存、共享采购成本及付款审计条目，记 FIXED_PENDING_REVIEW；线程清理是已修测试生命周期缺口，不重复登记新业务 Issue。已有历史审查结论与单位冲突待核实边界全部保留。工作包已完成开发侧验证，等待 ChatGPT 集中独立复审。
