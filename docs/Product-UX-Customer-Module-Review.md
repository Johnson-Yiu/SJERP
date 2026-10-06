# Product UX Review — Module 1：Customer / CRM

## 范围与状态

接受基线：`bd205c1af0b1ba334fbb437af60ae3190f5cb362`，CI #152 三项 SUCCESS。
这是模块逐项 UX 评审的第一项，只调整 Customer / CRM 信息层级与关系视图导航。
实现、自动化测试及真实 UI UAT 已完成；CI 待推送核验，独立 ChatGPT 评审待完成。
**不得提前标记 UX-FROZEN；仅当最终 HEAD 三项 CI 全部 SUCCESS 且独立 ChatGPT 评审通过后，本轮 Customer / CRM 层才可冻结。全 ERP 不在冻结范围内。**

无新模型、迁移、全局样式或权限变化。Customer/FollowUp 自动生命周期、销售人民币金额与正式订单统计、报价/订单状态、库存和财务计算均未调整。
QuoteDetailModal、OrderDetailModal 的完整工作台没有修改；PCR-020、PCR-007、PCR-019 保留并进行全套回归。

## 原问题与信息层级决策

原客户列表以编号优先；详情默认联系人；下次跟进埋在基础信息；关联报价/订单先展示客户；管理链接只打开列表且关闭原详情，丢失精确单据及返回上下文。
新的日常路径是：客户 → 跟进 → 报价 → 订单 → 成交商品 / 财务。

- 客户列顺序：name、code、status、country、region、owner、next_follow_up、order_count、sales_amount。名称是第一主列，原数据均保留。
- 顶部四项：累计销售额、订单、报价、下次跟进；无安排显示未安排。联系人数量保留于页签。
- 基础信息：负责人、业务区域、来源、网站、地址、备注；下次跟进不重复，国家继续位于副标题。
- 客户业务记录页签：跟进记录、报价记录、订单、联系人、成交商品记录、财务流水；默认跟进记录。
- 订单商品记录仅改名成交商品记录，数据仍来自正式 OrderItem，行仍指向对应 Order。
- ROOT Customer 新增跟进、新建报价、编辑客户、关闭复用既有按钮与 RelatedCreateModal；跟进与报价均预填当前 customer ID，不增加新建订单。
- 通用 Quote sections：报价明细、关联订单、客户。
- 通用 Order sections：订单明细、收付款流水、出入库流水、来源报价、客户。

## 精确工作台与返回路径

嵌套报价链接：打开报价工作台 → `/quotes?detail=<current quote ID>`。
嵌套订单链接：打开订单工作台 → `/orders?detail=<current order ID>`。
使用 RouterLink 普通 push，不触发原关闭详情的 query 清除；其他实体仍使用打开管理页的既有行为。
客户列表打开详情时通过普通 router.push 写入 `/customers?detail=<id>`，包括行点击、Enter 和查看详情按钮，以保留可恢复的客户地址。
嵌套返回按钮沿用现有详情栈；进入专业工作台后的浏览器 Back 沿用浏览器历史，返回原客户路由。没有引入新的历史系统。

## 真实 UI UAT

日期 2026-10-07。使用内置 Browser 技能，不使用 Computer Use、API / DB / shell 数据捷径。
现有客户：ID 1 `UAT-R1 客户 Alpha GmbH`；未创建、编辑、保存或删除任何业务数据。

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| UAT-CUST-001 | PASS | 列表首列客户名称，随后客户编号、状态；全部九列顺序正确 |
| UAT-CUST-002 | PASS | 直接打开客户 ID 1，跟进记录默认激活，已有两条跟进即时可见 |
| UAT-CUST-003 | PASS | 累计销售额 ¥24,714.72、正式订单 6、报价 13、下次跟进 2026-09-30 |
| UAT-CUST-004 | PASS | 新增跟进打开既有编辑器，客户 Alpha 预选并锁定；取消未保存 |
| UAT-CUST-005 | PASS | 新建报价打开既有报价编辑器，客户 Alpha 预选并锁定；取消未保存 |
| UAT-CUST-006 | PASS | 报价 SJ20261002DE003（ID 40），报价明细默认激活，两条真实商品立即可见 |
| UAT-CUST-007 | PASS | 打开报价工作台进入 `/quotes?detail=40`，准确报价；浏览器 Back 回 `/customers?detail=1` 同一客户 |
| UAT-CUST-008 | PASS | 订单 SO-2026-00026（ID 26），订单明细默认激活，两条商品立即可见 |
| UAT-CUST-009 | PASS | 打开订单工作台进入 `/orders?detail=26`，准确订单；浏览器 Back 回 `/customers?detail=1` 同一客户 |
| UAT-CUST-010 | PASS | 联系人 1、成交商品记录 7、财务流水 9 均展示；分别下钻 UAT 联系人 Alpha、SO-2026-00034、FIN-D2E3CF9C90C54883，返回客户正常 |

额外回归：编辑客户打开原编辑表单，姓名、区域等数据正确；取消未保存。
结束时客户仍为 12 个，累计列表销售额 ¥65,612.88；未新增业务记录，无临时数据需要清理。
截图：本任务 visualizations 目录的 `customer-ux-uat.png`。

## 自动化测试

新增后端 `crm.tests.test_customer_ux` 5 项：客户 sections/metrics/info 精确顺序、正式人民币销售金额/订单数、未安排、报价明细优先、订单明细优先、成交商品原订单目标及正式范围。
现有 BusinessFlowTests 的旧名称断言按指定文案改为成交商品记录；首次全量运行仅此断言失败，修正后重跑通过。
新增前端 `tests/customer-ux.spec.js` 8 项：九列、默认跟进、摘要与客户业务记录、编辑事件、共享跟进预填取消、报价预填、报价/订单下钻与默认明细、精确 href、嵌套返回、普通 router push/browser back、其他实体管理链接、成交商品原订单目标。
既有报价预填、路由生命周期、客户编辑与 RelatedCreateModal 回归测试继续通过。

| 验证 | 结果 |
| --- | --- |
| Backend full suite | 562 项，OK（本地跳过 10 项 PostgreSQL 专用测试） |
| makemigrations --check --dry-run | No changes detected |
| Frontend Node | 111 项 PASS |
| Node-only detail typography | 1 项 PASS |
| Frontend Vitest | 24 文件 / 183 项 PASS |
| Frontend build | PASS，既有大块体积提示 |
| git diff --check | PASS |

## CI 与独立评审门槛

待记录实现提交的 GitHub CI。最终文档提交也须核对对应 HEAD 的 backend、backend-postgres、frontend 三个结论。
最终 SHA、最终运行号和作业结论在交付报告列出；文档不会提前声称未运行的提交通过。
独立 ChatGPT 评审结果尚未收到，因此当前不宣布 Customer / CRM 为 UX-FROZEN。
正常 commit/push；不 force push、reset、远程历史 rebase。遇非快进停止。
不开始下一模块。
