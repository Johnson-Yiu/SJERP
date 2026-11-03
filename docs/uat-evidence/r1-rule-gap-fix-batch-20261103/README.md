# R1-RULE-GAP-FIX-BATCH-01 集成验收

日期：2026-11-03；统一基线 `8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`。
集成分支：`codex/r1-rule-gap-fix-integration-20261103`。本报告只覆盖本轮三个定向补修，不代表三个Issue整体关闭或生产就绪。

## 来源与完整性

以下远端HEAD经重新fetch及git ls-remote核实，原审查分支未修改；本集成分支保留全部报告、探针及原始日志：

| 审查 | 精确远端SHA | 报告 |
|---|---|---|
| ISS-105 | `1cad93d0cb0297c33f764f6cb68d5c610512d9e4` | [实际资金审查](../r1-iss105-actual-cash-audit-20261103/README.md) |
| ISS-037 | `c88a121298465fcb04e11f9b65ef9ad251eadf3f` | [历史快照审查](../r1-iss037-snapshot-audit-20261103/README.md) |
| ISS-039 | `2d5164287672d9a57a6496761c3ea0d026088072` | [共享采购成本审查](../r1-iss039-shared-cost-audit-20261103/README.md) |

三份审查仅移植指定证据提交；三个补修分支均从统一源码基线建立，不从审查提交或master派生。共享台账/阶段只由协调线程修改。补修来源的精确SHA、截图和定向回归见后续结果节和最终交付。

| 补修分支 | 已提交推送的精确来源SHA | 定向结果与证据 |
|---|---|---|
| `codex/r1-iss105-independent-bank-fee-fix-20261103` | `321cb77d0179888a4788408d32c77d789504fbdd` | [报告](../r1-iss105-independent-bank-fee-fix-20261103/README.md)：28通过/3 PG跳过、Node174、Vitest17、Chrome3及4张截图；另补3项入口选择自测和无外层账户变量的Chrome重跑 |
| `codex/r1-iss037-unknown-buyer-revision-fix-20261103` | `1a9666010c370dda08e2719e2c70caf6ee6c1b11` | [报告](../r1-iss037-unknown-buyer-revision-fix-20261103/README.md)：98通过/0跳过，含10项新增空/非空修订、PI/XLSX及回滚 |
| `codex/r1-iss039-amount-allocation-fix-20261103` | `aadd2ff3a7a15bc2a6601238ac6cea58d921c741` | [报告](../r1-iss039-amount-allocation-fix-20261103/README.md)：79通过/1 PG跳过、Node171、Vitest36、Chrome2及10张截图 |

集成逐条cherry-pick，无合并提交、无冲突。模型仅B修改；C仅改purchase_costs服务，A不修改资金业务后端。未出现共享序列化器/模型/测试覆盖式冲突；所有新增拒绝/历史保护断言保留。唯一测试入口补充是A隔离运行器为专项/全套提供固定合成账户，其他选择保留原配置；不是放开生产受控账户。

## 运行环境和隔离

- 实际解释器：`C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe`，真实CPython **3.12.16**，复用既有独立环境、未修改全局Python。
- 本基线 `backend/requirements.lock` 全部16个版本逐一与installed distribution比较一致：Django **6.0.9**、DRF **3.18.3**、Pillow **13.0.0** 等；pip check无冲突。不是上轮3.14/Django6.0.6，也不声称本轮全新安装了Python环境。
- 前端在本工作树执行 `npm ci --no-audit --no-fund`（227 packages），未更改package.json/package-lock，不运行自动升级。
- 所有Django本地回归显式内存SQLite/独立TEMP MEDIA_ROOT；真实浏览器使用现有隔离启动器，验证Django直连、Vite及/api代理runId/token/数据库/媒体身份，迁移完成后才进入测试。只使用合成数据，不操作默认业务库和未知服务。
- Chrome为系统真实Chrome channel；截图是实际浏览器渲染，不拼图、不模拟页面。权限/审计测试临时override仅作用于测试库；开发身份与正式RBAC配置不变，匿名开发操作不伪造正式操作人。
- 本机无可用PostgreSQL客户端/服务或Docker。本地SQLite不证明锁语义；PostgreSQL17完整测试由现有GitHub CI隔离服务执行，以精确集成SHA的结果为准，不连接真实数据库。

原始环境及运行证据：[published-logs.zip](published-logs.zip)，内部按原始归档名分目录。综合检查采集器：[verify.py](verify.py)，各子命令保存未裁剪stdout/stderr、argv/cwd/exit和版本元数据；仅由[publish_logs.py](publish_logs.py)脱敏已销毁运行的48位临时隔离nonce，不改变失败、断言、状态、空白和测试结果。原始日志压缩归档以保留空白，不把日志格式化当结果修复。

## 补修与未变边界

### A 独立银行手续费

只修前端强制fee_for的问题，无关联发送null；选择关联继续原后端校验。保留独立CNY bank_fee来源、受控账户、凭证/人工核实、来源额度、精度、稳定请求键和一次确认统计。不扩大可接受来源、不修改报表计算。

### B 历史未知买方

只在首次根报价且未提供买方字段时进行模型默认预填；显式空值、历史实例保存和所有修订继承均不回读当前主档。普通修订和OrderSerializer触发修订共用修复。保留买方快照只读和正式PI/XLSX关键字段422拒绝，不改0012、不回填旧记录。

来源分支 `codex/r1-iss037-unknown-buyer-revision-fix-20261103`，定向提交 `1a9666010c370dda08e2719e2c70caf6ee6c1b11`；[定向报告及98项回归](../r1-iss037-unknown-buyer-revision-fix-20261103/README.md)。本子任务无UI改动，不伪造Chrome截图。

### C 金额法公共费用

新增/修改费用必须显式amount，quantity/非法请求拒绝不写；历史quantity继续原法只读解释，不自动转换。用户主动编辑历史时明确确认并预览金额重算后才可保存，取消保留原数据。零商品金额有正费用拒绝，零金额无费用允许。跨销售采购修改权限、尾差守恒、版本冲突、取消目标、审计失败回滚及预留重算不变；不恢复逐SO授权、不新增资金库存流水。

## 综合回归与CI

本地最终代码为三项补修完整集成（集成代码提交 `b95852a`，随后仅协调文档/证据提交）；以下全部是同一业务代码树的真实结果，不以旧报告PASS替代。最终精确SHA、CI运行及三项结果通过GitHub运行记录及最终交付核实。最终集成提交不含skip标记，独立补修分支提交含 `[skip ci]`。

| 集成检查 | 结果 | published-logs.zip内目录 |
|---|---|---|
| Django check | 无问题，exit0 | backend-raw/1-raw.log |
| makemigrations --check --dry-run | No changes detected，exit0；无新增迁移 | backend-raw/2-raw.log |
| 全量Backend SQLite | **1114项：1081通过，33跳过，0失败/错误**，694.159秒；skip逐项保留，含真实PG锁/触发器及Windows平台边界，不宣称PG通过 | backend-raw/3-raw.log |
| Node全量最终复跑 | **177通过，0跳过/失败**，51.419秒；含17项隔离设施测试（原14+3合成账户选择） | node-raw/1-raw.log |
| 单独typography Node | **1通过** | frontend-raw/2-raw.log |
| Vitest全量 | **69文件、681通过**，0失败，262.16秒 | frontend-raw/3-raw.log |
| 前端生产构建 | 成功；主JS 1133.71kB/gzip396.01kB，保留原>500kB警告，不宣称性能改善 | frontend-raw/4-raw.log |
| 集成真实Chrome：手续费 | **3通过**，无父费用桌面/390px、合法及非法关联、刷新/重试/幂等/一次流出 | chrome-raw/1-raw.log |
| 集成真实Chrome：成本 | **2通过**，桌面/390px、历史只读/确认/预览/取消/金额法保存/新费用跨SO/非法及零基数拒绝 | chrome-raw/2-raw.log |
| 锁定环境/pip check | 全16 pin一致、无冲突 | environment-raw/ |
| diff/锁文件/workflow/迁移 | diff --check通过；requirements、package-lock、workflow和迁移相对基线无差异 | 最终git核对 |

集成重跑截图/HTTP/数据库：[手续费目录](independent-bank-fee/)、[成本目录](browser/iss039-amount-allocation/)。每项原补修报告另保留14张明确索引截图；本集成目录再次生成同场景实拍，不拿原分支截图冒充集成运行。截图只包含合成资料。协调线程目视检查了桌面/390px的可选关联与金额转换结果；窄屏表格沿用内部横向滚动。

取证过程失败记录全部保留：初始采集器在GBK控制台打印Unicode失败，Django/Playwright原始子命令状态已先写入ZIP；修正的是本目录采集器输出编码。最初Node因采集器向临时影子工作树泄露主树证据根目录而 **176通过/1失败**，隔离设施正确fail-closed；随后将该环境变量仅用于Chrome模式，Node177项原样复跑通过。失败见frontend-initial-raw/与frontend-raw/1-raw.log，成功见node-raw/；没有改产品、禁用检查、跳过用例或调大超时。Vitest、build和Chrome最终均exit0。原审查探针是历史缺口证据，不作为修复后验收测试重复调用。

CI在提交此报告时尚未启动，不能预写SUCCESS；最终推送后协调线程核实同一精确SHA的backend/backend-postgres/frontend，并在最终交付提供运行/job链接及导出日志。现有workflow执行完整Python3.12/PostgreSQL17及前端隔离浏览器套件，不修改workflow或跳过标记。本机没有PG环境，最终PostgreSQL结论只来自实际CI，不由本地SQLite替代。

本地基础设施自测：14/14通过（99.289秒），包括错误代理拒绝、占用端口拒绝、两个并行独立工作树真实启动和清理；后续Node全量再次包含此套件并保存原始日志。无需修改任何workflow、跳过标记或降低断言。

## 台账对账与剩余缺口

读取AGENTS、REVIEW_PROTOCOL和两份台账，按最新代码与规则改正旧ISS-037/039阻断描述，保留历史阶段。按每个ID最后一条表格状态解析得到 **124项**：OPEN **1**、BLOCKED **16**、NEEDS_VERIFICATION **17**、FIXED_PENDING_REVIEW **80**、CLOSED **10**。本轮新增0、关闭0；ISS-037从旧BLOCKED校准NEEDS_VERIFICATION，ISS-039从旧BLOCKED更新定向修复待审，其他状态不变。独立复审前不整体关闭。

- ISS-105保持OPEN：内部转账排除、银行多维重复识别、待分类、现金银行分类、启用基准/余额核算、账户核对、凭证文件绑定及完整审计仍待实施。
- ISS-037保持NEEDS_VERIFICATION：卖方/模板冻结、完整双方字段、多地址税务注册、历史来源可信度、主体版本和发起审批分离仍未覆盖。
- ISS-039本轮定向FIXED_PENDING_REVIEW：历史quantity保持原解释，正式身份/生产审计/真实库存竞争和部署验收不能从开发Chrome或SQLite推导通过。
- ISS-108/121保留BLOCKED的未实施/外部验收边界，**不再把已确认原则写成业务待决**。原D01–D08已规定保留银行原事实/凭证、明确银行日期、未知来源不得自动释放；本轮规则确认基准余额独立不算流入、现金银行分离、差异保留原始记录及凭证更正。具体启用日、真实余额和单笔更正凭证需要财务提供，不代选；本轮不实现这些后续模块、不解除fail-closed。

完成后不创建PR、不合并master、不部署、不启用正式RBAC、不进入标签页开发，停止等待独立复审。
