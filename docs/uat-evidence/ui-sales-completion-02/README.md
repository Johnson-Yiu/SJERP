# E1-R2 销售界面补修

- 分支 `codex/ui-sales-completion-02`
- 已审基线 `43067137d0fba04b0be055e449e55a06dba6d208`
- 被测产品源码 `f2b9e9a869bb003169057cf1550022326dc2eb04`。本报告及后续浏览器断言与截图仅改测试、证据。可用 `git diff --name-only f2b9e9a869bb003169057cf1550022326dc2eb04 HEAD -- backend frontend/src` 核验源码等价。
- Actions `NOT_RUN`。全部提交使用 `[skip ci]`。

## 复现与修复

| 问题 | H1 复现 | 修复后 |
| --- | --- | --- |
| 报价整页横向溢出 | 合成超长客户/单号。进入报价新建、选 SKU、创建修订或查看 PI。390px 原生两档下文档宽 853 CSS px，整页可移动 463／约 541 CSS px | 限制列表客户选择框固有宽度及编辑器网格，明细表保留独立滚动。六组截图的文档宽度均未超出视口，横移为 0；390px 已选明细容器可横向滚动 |
| 跟进附件失败遮挡 | 编辑带合成正文的跟进记录并新增附件。拦截附件 POST，正文走真实后端，触发重复悬浮与内联错误 | 在操作栏单独一行保留“跟进记录已保存，附件上传失败”，保留取消和同一条记录的保存重试。六组均检查按钮命中；取消拦截后 POST 201，重开只有一个附件，读取 200，24 字节内容一致 |
| 履约徽章被长名称挤压 | 打开合成长客户名/长订单号的订单草稿，390px 两档下徽章折为三行 | 标识允许换行，徽章保留独立空间；六组均断言一行，草稿编辑、确认和取消按钮可见 |
| PI 图片未解码 | H1 集成日志 `a2-h1-logs/image-preview-retry.txt` 第 255–279 行，已保存 PI iframe 图片等候超时。Vite 与 Django 端口不同，跨源的保护媒体响应即使 200 也受浏览器同源保护 | 已保存 PI HTML 使用同源保护媒体 URL，API JSON 继续返回原绝对 URL；六组均检查实际图片可见、解码宽 48、与 iframe 基准同源。完整打印和分页继续延期 |

[H1 窄屏失败索引](baseline/run.json) · [修复后六组截图及测量索引](fixed/run.json)

## 环境和文件

Chrome/156.0.8078.80，独立持久化 Chrome 资料目录、已认证合成 `codex`、独立 SQLite、媒体目录及 API/Vite 端口。使用 Chrome 设置改变原生页面缩放并断言 DPR，矩阵为 1366×768、1440×900、390×844，各 100%／125%。只有附件 POST 及补验中的库存故障使用受控拦截。浏览器运行器由项目复用，每次结束仅停止本次服务和清理本次数据库及媒体。截图尺寸、视口内 CSS 宽、横向移动、缩放和失败记录在对应 JSON。附件成功路径校验实际字节。运行器收集多条异常后仍会以非零退出。

产品文件为 `backend/crm/views.py`、`frontend/src/views/DocumentPage.vue`、`frontend/src/views/ResourcePage.vue`、`frontend/src/components/QuoteEditorModal.vue`、`frontend/src/components/OrderDetailModal.vue`。回归与种子文件为 `backend/crm/tests/test_quotes.py`、`frontend/browser-tests/ui-sales-completion-02.spec.js`、`frontend/browser-tests/iss007-image-snapshot-real.spec.js`、`frontend/browser-tests/iss029-recipient-snapshot.spec.js`、本目录 `seed.py`。未编辑共享样式、EntityDetailModal 或公共运行器。

## 定向结果

| 检查 | 结果 |
| --- | --- |
| H1 390px 基线 Chrome | FAIL，保留原始截图和逐状态断言 |
| 修复后六组原生缩放 Chrome | PASS，1/1，36 张 |
| 前端定向 Vitest | PASS，10 个文件、151 项 |
| SQLite Django `crm.tests.test_quotes.QuoteApiTests` | PASS，35 项 |
| 全量、PostgreSQL、通用浏览器 | NOT_RUN，A3 负责 |
| 完整打印成品与分页 | SKIPPED，已约定延期 |

## 既有证据与待验

E1 既有证据来源 `9dd721723422b45b1fabf1d97d1ad492488b7437` 的 `docs/uat-evidence/ui-sales-state-evidence-01`。数量正式提交、双人主体审批、赠品超发、实际装箱和编辑、完成履约的原始真实后端证据保留。订单详情布局已变更，旧履约画面只证明原业务动作。本轮六组布局结果覆盖草稿，终态只读布局及其他状态组合仍须分开补验。

| 原状态范围 | 本轮仍缺的真实浏览器证据 |
| --- | --- |
| C01–C11 客户、联系人、跟进、新品提醒 | 其余关联选择器、创建嵌套子窗返回及跨工作区；新品需求并发、提交中；客户和联系人保存/服务端失败/未保存分支及缺失矩阵 |
| Q01–Q07 报价 | 交易单位、包装子窗保存后回读、主体拒绝/撤回/替换；报价提交中、服务端失败及其他缺失视口组合 |
| O01–O10 订单 | 采购草稿生成、交易单位发货、其他超发原因、装箱异常、取消和终态只读；订单加载、提交中、服务端失败及未保存的缺失组合 |
| 资金/历史相关入口 | 由对应工作包验收 |

## 窄屏补验

[补验截图和断言](supplemental/run.json)在 390×844 原生 100%／125% 覆盖了已选 SKU 后的缺客户校验、库存请求挂起、受控失败和真实后端 200 恢复、包装子窗打开和取消后回到同一 SKU、未保存时继续编辑和明确放弃。含核心场景复测共 22 张，未执行包装保存分支。

## H1 集成失败复跑

- ISS-007 原用例 1/1 PASS。单独运行首次因 SKU 保存还在进行时触发 5 秒断言，保留首次失败归因。之后等待保存收尾，并在导出时确认缺成本风险。原图和替换后历史图均已解码；缺失媒体 404，iframe 中图片节点存在且自然宽 0，无浏览器异常。原测试把缺失图也要求可见，改为断言节点、失败解码、业务行与 HTTP 404。见 [正常图](pi-regression/quote-pi-original-snapshot-desktop-1440.png) 和 [缺失图](pi-regression/missing-history-image-mobile-390.png)。
- ISS-029 原用例 1/1 PASS。H1 已到修订保存，等待下载超时是脚本漏确认成本风险。隔离真实会话首次在直接发出的非法邮箱请求收到 403，补带 CSRF 后验证业务校验 400，并保留 A/B 的收件人快照、保存、重开及下载断言。
- [实际 XLSX 核对](xlsx-verification.json)记录 Chrome 下载、单独的 HTTP 获取、文件哈希和收件人/金额核对。两版工作簿均为 USD 10.00，未保存邮箱未进入 B 版。含默认收款模板信息的二进制原件留于本地隔离运行产物；最终候选版本的 XLSX 与 CSV 由 A3 复验。

## 跨工作区补验

`workspace-integration-real.spec.js` 的 4 项均 PASS，使用真实 Chrome 和独立后端，产品源码与上方 SHA 等价。覆盖登出时保护未保存草稿及同名账号切换后的清理、会话过期后拒收迟到结果、并行客户草稿保存后返回原筛选列表、在两个客户入口之间保持各自的新品需求上下文和未提交内容。截图为各用例既有 1440 或 390 视口、原生默认 100%；其他视口/缩放及关联选择器的嵌套新建仍待验。见 [跨工作区截图](workspace-regression)。

## 重跑入口

从独立工作树运行 `node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-sales-completion-02.spec.js`。设置 `ISOLATED_CODEX_TEST_SUPERADMIN=1`，按项目约定从本地忽略配置加载测试账号，设置 `E1_R2_EVIDENCE_DIR` 为本次独立输出目录。默认检查全部六组；`E1_R2_EXTRA=1` 开启补充状态，`E1_R2_WIDTH=390` 复现已收录的窄屏补验。原用例以各自文件名作为 `--business-test` 运行。

## 报价主体生命周期补验

`party-lifecycle-real.spec.js` 及 `party-replacement-quote-real.spec.js` 各 1/1 PASS。两次首次运行的管理后台登录跳转来自测试浏览器继承默认 codex 登录。两个用例均明确使用空会话起点，再分别登录独立合成申请人与复核人。更正用例改由申请人通过界面标记已发送，仍断言 200。

真实后端保存拒绝和撤回，读回历史包含独立操作者及两种终态。另一个用例确认申请、独立批准、生成关联草稿并重读合成 PI。画面为用例原 1440×900 和 390×844 默认原生 100% 的相应状态。原生 125% 在这三个额外动作的缺项仍保留。见 [拒绝及撤回](party-regression/rejection-withdrawal) 与 [替换](party-regression/replacement)。
