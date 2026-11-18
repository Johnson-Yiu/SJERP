# SJERP 非财务 UI 交付审查与最小补修

审查目标：`3bb0970148ff98025d44d6c5ee42e17bfe180002`。本轮在该提交逐文件、逐 Git blob 校验得到的源码上工作，没有把旧本地工作树当作目标版本。最终 26 个修改/新增文件及 Git blob 在 `final-changed-files.json`；每个既有文件的修改前 blob 均与目标提交树一致。

## 结论

确认两类问题：

1. **原中文优化中的实际展示改动遗漏。** `a5869a50`、`01b6fe73` 的部分源补丁没有进入当前页面：历史预检仍显示内部字段键、旧空态和旧操作措辞；多处日常 helper 仍是源补丁删除的旧句。已经按当前结构最小补回。没有重放旧页面、旧状态映射、旧样式或旧财务导航名。
2. **本轮新发现的现存缺陷：报价保存中可以关闭编辑器。** 已用真实 Vue 组件和挂起的创建 POST 复现；关闭并确认放弃后组件会先发出 `close`，原请求完成仍发出 `saved`。尚无证据证明它由某次历史回退造成。已按协调任务授权补充主/子编辑器 busy 保护，正式回归通过。

以下功能已在目标源码内存在，不应再次合并旧分支来重做：全局数字滚轮保护、业务弹窗遮罩不关闭、工作区多标签及独立草稿、客户新品提醒及作废留痕、跟进附件重开读取最新详情、销售草稿暂停背景订单详情、报价保存/导出与正式快照路径。完整原生打印矩阵及真实环境视觉验收不能从代码存在推定通过。

## 1. 中文遗漏的来源及处理

主要来源：

- [`a5869a50ed3a853b9a481a728af02f6c14de6bdb`](https://github.com/Johnson-Yiu/SJERP/commit/a5869a50ed3a853b9a481a728af02f6c14de6bdb)：历史预检和承接的初步文案。
- [`01b6fe73f77c2294a17d1b4e001d8e3afe83e27a`](https://github.com/Johnson-Yiu/SJERP/commit/01b6fe73f77c2294a17d1b4e001d8e3afe83e27a)：历史、财务及日常流程文案。
- [目标版本中的接入记录](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/docs/uat-evidence/first-release-independent-review-02/README.md) 明确区分了 `6cb20a84` 的导航改名与全站中文工作：前者只接入 5 个文件、9 行替换，不能代表后者完整接收。该记录与本轮逐文件看到的实际差异一致。

逐条旧句、新句、来源及语义解释完整记录于 `copy_changes.json`。本代理完成 50 处精确替换、24 个文件，其中 12 个是运行代码，12 个是已有测试/验收脚本。财务 3 个文件及采购页面文案由另外两个模块负责人接收，不计入上述数量。

| 运行文件 | 实际补回内容 | 保留的行为与边界 |
| --- | --- | --- |
| `backend/crm/history_import_preflight.py` | 重复编号用已有 schema 中文标签显示；例如 `source_record_id` 改显示“原系统记录编号”；改清楚单位快照、换算和审核说明 | 同一来源组的重复判定、阻断状态、关联行、数量检查及只读行为均保持。没有改变 key、代码或持久化值 |
| `frontend/src/views/HistoryPreflightPage.vue` | XLSX 操作、空态、预检明细、建议处理方式和后续审核说明 | 保留文件切换竞态修复、当前编号说明、工作区请求、CSV 与来源文件绑定 |
| `frontend/src/views/HistoryTakeoverPage.vue` | 申请空态、剩余数量、加载入口、库存/余额说明；“逐组执行”改“承接本组” | 保留“批准本组/拒绝本组”、现行标题及风险说明、更新后的中文 coverage 映射、逐组执行条件和双人核实流程 |
| `frontend/src/utils/apiErrors.js` | 将特定 DRF 未登录消息显示为“请登录后再继续” | 不改变 HTTP 状态、鉴权或路由；其他错误仍按原规则格式化 |
| `frontend/src/components/ProductSkuManagement.vue` | 明确 SKU 清单、候选供应商和实际采购供应商 | SKU 并发保存与批量保护不变；原脚本逐字节相同 |
| `frontend/src/components/SupplierAllocationModal.vue` | 候选空态与补充供应能力入口 | 候选匹配、实际分配、保存条件不变 |
| `frontend/src/components/WorkspaceTabs.vue` | 简化“数据已更新”提示 | 继续要求保存/取消当前编辑再重载；失效确认对话框和保护不变 |
| `frontend/src/components/reports/ReportDetailPanel.vue` | 所选分组无原始记录的空态 | 查询范围、权限、明细和导出不变 |
| `frontend/src/components/OrderDetailModal.vue` | 历史主体未知说明、包装快照 helper | 主体版本的新说明不回退；取消、退款、终止剩余履约及并发保护不变；原脚本逐字节相同 |
| `frontend/src/components/PurchaseDetailModal.vue` | 历史主体未知说明 | 不用现行主档填充历史主体；不改变当前版本、采购或付款功能 |
| `frontend/src/views/Dashboard.vue` | 零分母时“无法计算变化率” | 统计日期和计算不变 |
| `frontend/src/views/HistoryOrdersPage.vue` | 历史成本不完整时不计算利润的说明 | 保留后续新增筛选、分析、竞态和未知成本规则 |

没有机械恢复的来源改动：

- `0580cd5c` 的旧承接整块 CSS 已由当前布局替代。没有证据支持覆盖现行 CSS。
- `01b6fe73` 的 coverageLabels 已有现行中文 `coverageLabel()` 等价实现，不再加入第二套映射。
- 原来只写“批准/拒绝”的按钮保留当前更明确的“批准本组/拒绝本组”；“承接本组”接收原“承接”的业务表达并保留组作用域。
- `945c2ae4` 的旧财务导航名称已有后继命名，不恢复旧名称。
- CashEventPage 的旧内联资金表单已提取为 CashEventEntryForm，模块负责人已核对现代组件的等价自然文案，不回放旧表单。

### 业务规则不变的证据

`changed-file-verification.json` 证明上述 10 个 Vue 文件的全部 `<script>` 与 `<style>` 块逐字节相同；仅模板可见文本变化。所有既有 CRLF 数量保持，没有整文件换行或格式化。后端预检原有 24 项实际测试均通过，包含业务快照不变、重复拒绝、来源分组、数量、上传/解析限制等；源提交中“中文字段标签且不泄露 source_record_id”的断言已加入原真实重复场景。

## 2. 新确认的报价保存关闭缺口

目标源码 `QuoteEditorModal.vue` 的主 guard 和包装 guard 都未传 `busy`。`requestClose` 直接调用 `editorScope.requestClose`；主窗关闭和取消按钮保存时仍可点击。工作区请求封装的 `workspace.busy` 仅在工作区关闭时提供保护，无法替代编辑弹窗自身关闭。

`quote-busy-repro-local.log` 记录了修改前反例：真实组件发出 `/quotes/` 请求并处于挂起状态，点击关闭、确认放弃后，`close` 已触发，保护断言失败；释放原 POST 后还会执行正常保存完成逻辑。最初在工作区外运行的诊断因 Vitest 外部 setup 路径解析失败而未运行测试，日志另存 `quote-busy-repro.log`，不拿它作为缺陷证据。

最小补修：

- 主 guard 在报价保存或包装保存中拒绝关闭/导航/刷新。
- 包装 guard 在包装请求中也保持 busy。
- 主编辑器的关闭、取消按钮在任一保存中禁用。
- 先声明 busy refs，再创建 guard，避免 guard 的立即 watch 访问尚未初始化的变量。

没有修改报价校验、载荷、接口、修订、保存与导出顺序、包装数值或默认包装写入规则。`quote-function-verification.json` 证明全部 **31 个具名函数体**及所有样式与基线完全相同；变化只在响应式 busy 接线、声明顺序和关闭按钮 disabled 属性。

正式新增测试文件：`frontend/tests/quote-editor-save-protection.spec.js`，**3 个用例**：

1. 创建报价 POST 挂起时关闭、取消、导航和刷新均受保护；重复提交不多发请求；失败保留全部输入；重试成功后只保存/关闭一次。
2. 报价修订执行同样场景，仍走原 `/quotes/44/revise/`，不改变修订语义。
3. 子包装 PUT 挂起时父、子编辑器均不可关闭；失败保留模板、装箱数、净重；重试仍提交原 SKU，成功后可正常关闭。

临时 `release-audit-quote-busy.spec.js` 已移出候选目录，只保留上述正式回归。

## 3. 已核对仍在的交付成果

| 范围 | 当前实现证据 | 结论限制 |
| --- | --- | --- |
| 数字滚轮保护 | `numericWheelGuard.js` 与来源 `568105bd220185ae95e9f0d7b8b1c32081d445c3` 新增内容逐字节相同；main.js 全局安装、HMR 清理，捕获阶段保护 number/spinbutton 并向滚动容器转发 | 原分支 diverged 不代表功能缺失 |
| 弹窗遮罩 | Vue 模板 AST 扫描到 56 个 overlay/backdrop/mask 元素，没有点击、mousedown、pointerdown 关闭事件；仅 3 个保留 Escape 键操作 | `backdrop-scan.json` 是源码证据，不冒充真实鼠标验收 |
| 内部标签与草稿 | App 挂载 WorkspaceTabs/WorkspacePane；manager 每页独立 memory router、对象去重、草稿隔离、关闭守卫、写入 busy、失效刷新、会话清理和取消请求 | 本轮相关 manager 自动化通过；不扩大为所有真实员工会话的验收 |
| 新品提醒 | 前后端、路由与客户/跟进入口均在；默认有效、搜索关联、版本冲突、作废理由/审计、浅灰作废状态；后端 `http_method_names` 不含 DELETE | 未发现缺失，不重复开发 |
| 跟进附件 | ResourcePage.openEdit 对 follow-ups 无条件先 GET 当前详情，再读 attachments；不是从上传前列表行恢复 | 与 ISS-135 后续修复记录一致；本轮不声称重新完成实际附件下载 |
| 销售草稿 | DocumentPage 保存时 busy；编辑已有订单草稿给背景详情传 `suspended`，保留原详情/焦点处理 | 与 UI-DELIVERY-CLOSEOUT-04 已交付修复一致。独立新发现报价缺口另列，不混淆为订单草稿旧问题复活 |
| 报价导出/打印 | 下载路径复用保存版本输出；Blob URL 延迟回收；保存与导出分离；保存的 PI 用保存的 print_html iframe，等待资源后调用原生打印 | 完整原生打印/分页有独立授权和后续记录，不能以旧 FAIL 宣称仍失败，也不能以源码存在宣称全验通过 |

### 排除 300 文件 compare 截断误判

对 `ui-sales-state-evidence-01` (`9dd72172`) 与 `ui-product-operations-state-evidence-01` (`67410d72`) 直接读取 Git tree，绕开大 compare 文件列表的 300 项上限：两个分支与共同基线 `1e45e42c` 的 frontend/src 树都为 `6d80b1fd18043e1a127c01208eeced5519efe3c4`；backend 树都为 `c918cd9285fd816c2ce07a01c39701f9196b7af7`。它们的新内容是浏览器测试和证据，没有新运行功能代码。证据为 `evidence_branch_trees.json`。

`ui-final-state-closeout-03`、销售 completion-02、产品 completion-02 的未纳入差异主要为测试/验收证据；对应最终行为必须依后继源码和 `ui-delivery-closeout-04` 等记录核对，不能单凭旧分支 HEAD 不在祖先就把整条分支合进候选。

## 4. 本轮实际验证

环境：Node **24.22.3**（目标 CI 为 Node 22，最终仍需该环境）；Python **3.12.14**，使用协调任务已核对锁定依赖的隔离环境。后端 `DATABASE_URL=sqlite:///:memory:`，没有访问正式数据库。

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| 历史、SKU、工作区、报表、订单明细 9 文件 Vitest | **82/82 PASS** | `vitest-tests.log` |
| API 定向 Node | **8/8 PASS** | `api-tests.log` |
| 历史预检 Django | **24/24 PASS**（补齐未物化的原始模板后） | `backend-tests-retest.log` |
| 报价保护、原未保存保护、报价可用性、主体修订 4 文件 Vitest | **76/76 PASS**，包含新增 3 例 | `quote-protection-tests.log` |
| 报价编辑器/详情 Node | **11/11 PASS** | `quote-node-tests.log` |
| Vue 文案文件/行尾审查 | 10 个 Vue 的脚本与样式相同；原行尾保持 | `changed-file-verification.json` |
| 报价最小修复审查 | 31 函数体及样式相同 | `quote-function-verification.json` |
| 实际浏览器/视觉 | **BLOCKED，未生成截图、未进入页面** | `visual-tests.log` |

预检首轮 24 项中的 1 项失败，原因是本地只物化运行/测试源码，漏放原仓库已有 `ISS-121-history-import-template.xlsx`。从缓存取出后，其 Git blob 与精确目标提交目录中的 `71346c5bc4f97f10e8b57bca5c83b7e5aff07399` 一致（58,347 字节），补回后原 24 项全部通过。初跑日志保留 `backend-tests.log`，证明见 `template-verification.json`；模板不是本轮产品修改。

本机没有 Google Chrome，尝试已安装 Chromium 156.0.8078.79 在创建页面前被系统拒绝：`process_singleton_posix.cc:297 socket() failed: Operation not permitted (1)`。没有改参数或换工具绕过。`visual-review.mjs` 已准备历史预检/承接、财务概览/账户核对的桌面 1440 与窄屏 390 合成夹具，但由于浏览器未能启动，不能声称脚本场景或人工视觉通过。

## 5. 给最终候选的交接

1. 本代理拥有的最终源码/验证修改清单以 `final-changed-files.json` 为准：**26 文件，13 个运行代码、13 个测试/验收文件**。
2. ProductSkuManagement、OrderDetailModal 和模块负责人的 FinanceLedger 等被发布清单精确锁定的文件，须由协调任务审核新 blob 后明确更新清单；不能为了清单通过而还原新旧成果。
3. 最终统一构建、精确提交 CI、真实 Chrome UI/下载及目标部署由协调任务与 Codex 执行。本轮未跑全量、未部署、未操作正式数据。
4. 台账应区分“部分中文成果未接收”与“新发现的报价保存关闭缺口”；不能把二者都描述为已证明的 Git 回退。真实 Chrome 阻塞及未验边界继续保留，不能仅凭自动化通过关闭。
