# SJERP PRELAUNCH-REPAIR-BATCH-02 集成验收

分项业务及原 22 组 UI 已完成集成交互复验，32 个专用 Chrome 用例通过。本文件记录分项证据，不以阶段绿灯替代最终交付。完整候选认证在冻结提交后运行，最终结论须同时核对交付回复所附同 HEAD 本地认证文件与 Actions 的 headSha/job；不关闭 Issue。

## 来源与集成

独立分支 `codex/prelaunch-repair-integration-02`，工作树 `.worktrees/prelaunch-repair-integration-02`。正常 merge 完整来源，没有 reset/clean、整文件覆盖、合并 master、部署、正式导入或真实资金操作。

| 代号 | 完整提交 SHA | 作用 |
| --- | --- | --- |
| UI | `e5ce789459b2499189bc9b0b5e922e8722847da1` | 原 UI 完整来源 |
| 取消 | `c8a06892579bf586d1a674750902c27943fa69d4` | 原取消退款完整来源 |
| 基线 | `d7d155b994b652f6f4f777edde22a257a8ed7a2e` | 两来源正常 merge，无冲突，保留 SEC1 |
| A | `a4b2ff4c53e117b2efffeb5af54813121887ce5f` | 完整交付；业务最终 `9b739faec0d85c7c62b6a1e1f02ea4f102445cba`；后续测试/证据 |
| B | `79530615a24292d2a87198032d2a85420e630fd7` | 完整交付；成本业务 `3dfd2b813c209148aebdfe65d315fae632d179f5`；反馈业务 `1d96c5ca0d6e5b0011a50918c5f0a0907b15cd03` |
| C | `9d5dd253bf30e0785cb70b14246902811233a08f` | 完整交付；最终源码 `c83c56b194d4f6e029329a8eab551d316a814983` |
| D 字段/操作列 | `df8c6972e8431e030b2cb8b83f3493c7e1e4b6ce` | 成本标签、删除操作列、提醒测试环境 |
| D 公共层级 | `4c0845a013f382b8b299af639e1755b529184795` | 公共确认高于绑定抽屉，修复真实鼠标阻挡 |
| D guard 接口 | `e2d0f432e46b91447442b21cd47d0c22da2ec403` | 导出既有 confirmLeave 供 C 复用 |
| 集成应用源码 | `71592c9087198787baf03b22a4b5e0707b561505` | 业务已齐；之后仅测试、台账、证据。manifest 核对 backend、frontend/src 与该 SHA 无差异 |

A 持有财务/OrderDetailModal；B 在 models.py 只改 SKU/OrderItem，A 只改 Transaction；C 收拢产品工作区/公共详情丢稿；D 持有公共确认与全局样式。无新增迁移，147 个 CRM 迁移保持 0130 单叶及已有汇合依赖。

## R01–R07

| 编号 | 结果 | 实际验证 |
| --- | --- | --- |
| R01 | 已修复并验证 | A：直接计划收款 1000，空订单退款拒绝；选原订单退 100 后现金 900、待收 100。三类来源额度、日期/凭证、超退、幂等、审计回滚和 PG 并发见 A 报告。 |
| R02 | 已修复并验证 | A：收 50 取消后作废、收 999+抵减 1 取消后更正抵减，应收均保持 0；保留原流水、计划和审计。 |
| R03 | 已修复并验证 | B：人工金额/成本币种完整快照；派生继承对应来源，未知币种不改 CNY；普通 API 快照只读；表单保存重开及只读检查反例。 |
| R04 | 已修复并验证 | A：原 100 发 40，另有整行未发余项；先退款 600，再终止至 [40,0]，合同/净现金均 400、应收 0，发货事实保留。普通改量不放开 0，采购保留并提示核对。 |
| R05 | 已修复并验证 | C：规则/方案各自 dirty/busy；切工作区保留，关闭/卸载询问；继续/放弃、失败重试、保存回读、旧响应和后台刷新均实操。 |
| R06 | 已修复并验证 | A：取消错误留在本表单，原因/背景保留，忙碌不可重复或关闭；拒绝后返回、处理并重试成功。 |
| R07 | 已修复并定向验证；最终认证单列 | jsdom/SKU/作废旧提示断言已修复；850 Vitest、201 Node、排版1项、build通过。既有打印测试改真实点击和有限文件等待，原失败/修后单项保留。后端、完整浏览器和精确HEAD CI是交付门槛，必须以提交后认证为准。 |

分支原始失败和前后对照：[A](../cancel-refund-closeout-02/README.md)、[B](../cost-currency-integrity-02/README.md)、[C](../product-draft-protection-01/README.md)、[反馈](../prelaunch-p1-05-feedback-02/README.md)。本目录另有统一应用源码上的交叉复验，不只引用分支测试。

## P1/P2 逐项记录

“当前基线已有修复”表示没有重复修改实现，但在统一应用源码实际操作验证。新修复保持 FIXED_PENDING_REVIEW，不是 CLOSED。每项旧图见[编号映射](before-reference/items.json)：51 张原 PNG 仅作复现线索，不能当本轮通过证据。

证据代号：I=[综合交互](final-ui/)，L=[删除/银行](integrated/ui-prelaunch-polish-01.spec.js/)，T=[分类/工作区](integrated/prelaunch-ui-category-tabs-02.spec.js/)，O=[关联订单](related-final/)，H=[追溯更正](integrated/prelaunch-history-correction-02.spec.js/)，F=[反馈1366](integrated/prelaunch-p1-05-feedback-02.spec.js/)和[反馈1920](feedback-1920/)。A/B/C/P 为 integrated 下相应退款、成本、草稿、包装 spec 文件夹。用例/run ID、原图路径/像素/SHA256 见 [manifest](screenshot-manifest.json)。源码代号对应上表完整 SHA。

| 编号 | 结果 | 操作与回读 | 源码／证据 |
| --- | --- | --- | --- |
| P1-01 | 已修复并验证 | 库存浮层/产品预览基线已有；边缘鼠标、预览点击/Enter；补修确认被绑定抽屉阻挡。 | 基线、D 公共层级；I/C |
| P1-02 | 已修复并验证 | 初始焦点、正反 Tab 循环、父抽屉继续/放弃、关闭焦点恢复。 | D 公共层级、C；I/C |
| P1-03 | 当前基线已有修复并验证 | 库存输入切客户隐藏，返回保值和滚动；关工作区继续/放弃；保存 201、GET 数量 2。 | 基线；I |
| P1-04 | 当前基线已有修复并验证 | 数量/交期滚轮保护；交期 14 天实际保存；普通草稿数量 3→4 保存重开、正式确认。 | 基线；I/O |
| P1-05 | 已修复并验证 | 包装失败重试 PUT/GET；采购慢请求不可关闭、503 后重试且不能重复生成；导入丢响应后同批恢复、实际 CSV。两桌面独立操作。 | B 反馈；F |
| P1-06 | 已修复并验证 | 全失败/部分失败/成功数量、失败对象保留、重试、启停回读，父刷新不抹结果。 | C；C |
| P1-07 | 已修复并验证 | 修 1366 待处理裁切；两桌面慢 DELETE、鼠标重复只发一次、503 重试、204 后 GET 404。 | D 字段/操作列；L |
| P1-08 | 当前基线已有修复并验证 | 关联入口只读草稿；创建 201、编辑 PUT、重开 GET、正式确认 POST/GET。 | 基线、A；O |
| P2-01 | 当前基线已有修复并验证 | 初始底栏在视口；未核对不可提交；勾选后清数量触发原生校验聚焦，填 1 后入库 201/GET。 | 基线；I |
| P2-02 | 当前基线已有修复并验证 | 嵌套预览图片、鼠标滚动、实际关闭；下载 XLSX，核对单号和每行数量/单价/金额。不据此宣称完整打印通过。 | 基线；I |
| P2-03 | 当前基线已有修复并验证 | 真实非空银行事件详情，核对工作区顶部/底部按钮并实际关闭。 | 基线；L |
| P2-04 | 当前基线已有修复并验证 | 1280/1366/1920 短来源、超长继承来源滚入视口且无裁切，选分类保存产品回读。 | 基线；T |
| P2-05 | 当前基线已有修复并验证 | 长分类选择保存；包装长候选选择、空候选、新建和返回，两桌面实操。 | 基线；T/P |
| P2-06 | 当前基线已有修复并验证 | 12 条长列表/单条短列表，标题聚焦可见，返回保留筛选，保存 201/GET 内容一致。 | 基线；I |
| P2-07 | 当前基线已有修复并验证 | 两桌面加载、503 耗尽自动重试、可见手动重试恢复真实非空事件。 | 基线；L |
| P2-08 | 当前基线已有修复并验证 | 无筛选、有筛选、无结果、55 条客户分页，卡片等于接口全结果 count。 | 基线；I |
| P2-09 | 当前基线已有修复并验证 | 两桌面 6/12 个真实长客户标题，激活、左右移动；390 手动横滚和 Home，页面 scrollX=0。 | 基线；T |
| P2-10 | 当前基线已有修复并验证 | 键盘全选、鼠标拖选 MOUSE、取消保值、无选区插入、非法 javascript 拒绝；保存重开核对文字/href。 | 基线；I |
| P2-11 | 已修复并验证 | 公开日志标签统一，启用审计的空日志、切入、刷新和工作区切换不回总览。 | C；C/audit |
| P2-12 | 当前基线已有修复并验证 | 16 个受影响列表 ×1366/1920/1024/390；按容器宽度断言并实际命中四/二/单列。 | 基线；I |
| P2-13 | 当前基线已有修复并验证 | 历史分组/必填拒绝、真实 POST、刷新 GET；财务退款/更正由 A 真写入回读。 | 基线、A；H/A |
| P2-14 | 已修复并验证 | 销售 EUR/成本 CNY，数量3/售价12/成本3.5；鼠标进入成本框、位于底栏上方；两桌面/390 保存重开确认后金额/币种保留。 | D 字段/操作列；O |

## 执行与失败记录

专用 Chrome 32 项：A1、B1、C1、包装1、反馈两尺寸各2、关联3、分类/工作区5、删除/银行4、历史1、综合11。后者及反馈1920、关联最终轮为独立锁定 Python（Django6.0.9）；早期诊断环境 Python3.14/Django6.0.6。最终认证使用 requirements.lock，不能将旧版本全量归为锁定环境结果。

实际命令：

```text
npm run test:unit
node --test tests/detail-drawer-typography.spec.js
npx --no-install vitest run tests src/components/CashEventEntryForm.spec.js src/components/PurchasePaymentModal.spec.js src/components/HistoryProductLinking.spec.js --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers=2
npm run build
npm run test:browser
npm run test:browser:isolated -- --business-test <对应spec>
npm run test:browser:isolated -- --audit-product-draft-test
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput --verbosity 2
python docs/uat-evidence/history-product-sku-linking-01/run-postgres.py --postgres-bin <独立PG17路径> --full
python -m unittest discover -s scripts -p test_check_public_delivery.py
python scripts/check_public_delivery.py --range 00f7753dfc40b417983335be05135cb76a945ee0..HEAD
```

- 原 UI CI：841 项中 835/6；本轮环境/断言修后 848/848。接入 A 最终提示后 850 项先 849/1，再 850/850；未删行为断言。
- Node201/201、排版1/1、Vitest850/850、build通过；既有大 chunk/jsdom scrollTo 提示不当作业务失败或跳过。
- 浏览器早期等待、种子联系人、共享fixture、精确label、漏风险确认、Windows长路径读取失败保留；最终正常指针、实际下载字节和接口回读通过。失败轮不计入32。
- 视觉自查发现来源badge/390成本框未入截图，已滚入视口、真实点击、重新取图；不以DOM存在替代可操作。
- 通用浏览器原生打印先出现20秒文件等待失败，部分PDF迟到；扩大等待的诊断仍6/7，随后真实locator点击的多页单项生成197234字节PDF并通过。只修既有测试工具，没有实施打印业务专项；完整矩阵仍须在冻结候选执行，不把单次成功覆盖原失败。SQLite PG专用跳过/PG平台跳过按最终报告分别列出，不算pass。

阶段 CI：[9a8c78dc](https://github.com/Johnson-Yiu/SJERP/actions/runs/43476264092)、[79ad7888](https://github.com/Johnson-Yiu/SJERP/actions/runs/43483066741)仅为阶段记录，不是最终交付绿灯。冻结后再次执行本地全量并核对远端每个job；运行结果独立归档以避免将证据提交前的SHA冒充最终HEAD。

已完成的分项原始日志见 [logs](logs/)。只替换了已销毁测试实例的临时隔离标识，未改变状态码、请求和测试结果；未归档账号密码。最终认证产生的日志和结果单独以完整HEAD命名，交付回复提供可点击路径和CI链接。

## 原图、数据和范围

集成原图281张；manifest直接读PNG头/原字节，无裁切、缩放或重编码。默认原生100%；A实际Chrome设置100%/125%，保留物理尺寸、CSS视口和弹窗边界。人工检查分类来源、确认覆盖、收货底栏、PI滚动、银行详情、1024两列、390关联成本等；保留正式业务术语。

全程隔离SQLite/PG17、媒体和浏览器profile，codex凭据未进Git/日志。B只读差异检查仅对合成数据：原申请与不可变关联冲突为confirmed_mismatch，可能后续人工修改/来源不足为needs_review。没有正式库扫描结论，不批量重标CNY或推算汇率；真实更正须另核原件并留痕。

P3-01～04继续仅记[长期台账](../ui-prelaunch-polish-01/postlaunch-backlog.md)，不计22项分母；P4保留。ISS-129～134及105/108待独立复审，关闭0项。不扩展全站移动端、所有缺图、完整打印专项、正式员工权限、部署或正式历史导入。
