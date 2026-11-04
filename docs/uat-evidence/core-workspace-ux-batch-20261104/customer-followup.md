# 客户 / 联系人 / 跟进局部竞态修复

2026-11-04；基线 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`；分支 `codex/core-workspace-ux-batch-20261104`。仅修改 `ResourcePage.vue` 中这三个实体的前端路径及独立测试；未提交。已读 AGENTS、批次范围 README、PROJECT_ISSUES / PROJECT_PHASES / REVIEW_PROTOCOL，及 r0-f5-final、r0-f9、integration-021-029-027、iss-055-customer-404 历史证据。既有保存防重复、关闭拦截、失败保留输入、日期规则及 404 语义继续复用。

| 新发现（均待独立复审） | 修复前可控 Promise 证据 | 最小修复 |
| --- | --- | --- |
| 客户列表旧请求覆盖当前查询，或提前结束加载 / 展示过期错误 | 旧成功及旧失败在新查询未完成时将 `loading` 改成 false | 客户列表复用现有 `crmRequest` 版本号；成功、失败、finally 均只处理最新请求 |
| 三个实体的空态探测迟到，改写当前查询的空态 | 新查询确认空库后，旧探测把 `allRecordsExist` 改成 true | 探测成功和失败均检查请求版本 |
| 新建初始化迟到，污染随后打开的编辑表单 | 旧 next-code 覆盖 `CURRENT` 为 `OBSOLETE`；旧 operator 覆盖历史跟进人；旧选项加载可清空历史附件展示 | `loadOptions` 后提前检查当前路由动作；编号、默认跟进人先局部接收，再核对动作版本后写入 |

测试使用 Vue 真实组件、内存路由及模拟 API；不写真实业务数据，不代表真实后端或权限验收。客户 `owner_profile`、跟进人及附件语义均保持原样；没有新增权限绕过、API、依赖、公共组件或业务规则。可见文案未改。

## 独立修复前证据

临时驱动从固定 SHA 读取原始视图，在同目录生成独立临时 SFC 和测试副本，运行相同用例后 finally 删除；不替换当前视图、不回滚其他人的修改。当时运行命令（frontend 下，驱动现已按协调者要求删除）：

```powershell
node tests/customer-followup-before.mjs
```

实际退出码 1；最终 **8/8 失败**，明确对应上述问题，完整断言见 [before-unit.txt](customer-followup/before-unit.txt)。临时 `CustomerFollowupBefore.vue`、`customer-followup-before.spec.js`、`customer-followup-before.mjs` 均已清理；完整套件不会发现故意失败的 before 副本。

## 修复后定向回归

```powershell
npx vitest run tests/customer-followup-races.spec.js tests/crm-saving.spec.js tests/customer-ux.spec.js tests/crm-list.vitest.js --environment jsdom --maxWorkers=1
```

最终 **4 文件、35/35 通过**（8 项新竞态 + 27 项既有回归），退出码 0，完整输出见 [after-unit.txt](customer-followup/after-unit.txt)。首次测试夹具把客户展示 `owner` 当成表单字段，已纠正为实际 `owner_profile`，不涉及产品改动。`git diff --check -- frontend/src/views/ResourcePage.vue` 通过。全量 Node / Vitest 由协调者统一执行。

## 验收边界 / 交接

按协调者最新要求，不再启动本地 Chrome，真实隔离后端 fixture 和所有页面 IAB / 视觉验证由协调者统一执行。此前启动的独立 Chrome 回归与专用 Vite 已停止，未作为最终验收证据。请重点验证：客户搜索/刷新与快速切换筛选；空态清除筛选提示；新建未完成时切换编辑，编号、负责人、跟进人与历史附件保持当前对象。建议本子范围标记 `FIXED_PENDING_REVIEW`；公共台账、统计、最终集成与全页验收由协调者维护，不自行关闭历史 Issue。


## ResourcePage 全消费者范围复核（协调者追加要求）

通过文件读取静态检查 `frontend/src/router.js`、`resourceConfigs.js`、`utils/routePageState.js` 及当前 `ResourcePage.vue`。未启动 shell、浏览器、Node/Vitest 子进程，不干扰协调者正在执行的全量测试。无需进一步改代码。

| 使用方 | 本次新增分支的可达性 | 兼容性结论 / 验证边界 |
| --- | --- | --- |
| customers | 客户列表专属分支；新建编号与默认负责人版本检查 | 本轮目标范围，8 项新增竞态测试覆盖 |
| contacts / follow-ups | `isCrmPage` 仅由这两个 endpoint 构成；空态探测版本检查；初始化完成后检查 | 本轮目标范围；跟进默认操作人检查另受原有 customers / follow-ups 条件限制 |
| suppliers | `isCustomerPage=false`、`isCrmPage=false` | 新列表分支与新增初始化返回不可达；仍使用原 supplier / ledgerRequest 路径，原保存/付款/生命周期逻辑未改 |
| product-certificates | 两个新增入口条件均 false | 原证书列表、文件与表单路径未改 |
| product-parameters | 两个新增入口条件均 false | 原通用列表及参数表单路径未改 |
| inventory-movements | 两个新增入口条件均 false | 原库存流水 ledgerRequest 列表与独立创建入口未改 |
| products / skus / categories / transactions 配置 | 两个新增入口条件均 false；router 明确排除这四项的 ResourcePage 路由 | 当前使用各自专属页面；即便单独挂载配置也不会进入新增分支 |

关键静态依据：客户列表新增逻辑整体位于 `if (isCustomerPage.value)` 内；空态探测变更位于原 `if (isCrmPage.value)` 内；`loadOptions` 后的新增返回为 `(isCustomerPage.value || isCrmPage.value) && !isCurrent()`，排除模块短路，不调用新增版本检查；其余新增检查分别位于原 customers 分支、原 `[customers, follow-ups]` 分支内。未更改共享加载选项、watch、关闭/保存、模板、组件导入或模块级状态；`crmRequest` 是原有组件实例内变量。源码扫描未发现 router 以外的产品代码 ResourcePage 使用方。

测试记录仍为修复前 8/8 失败、修复后定向 4 文件 35/35 通过；本次只完成静态范围复核，未新增执行组件测试，也不将静态结论宣称为排除模块的完整 UI 验收。尝试进程内提取函数验证时，工具运行时拒绝动态代码生成，未执行、未计通过；未尝试绕过。供应商/证书/库存流水等全量组件兼容性，以协调者正在运行的最终 Node/Vitest 及 IAB 验收为准。
