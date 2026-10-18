# R1-A-FUP-02 订单履约与财务结清分离验收

日期：2026-10-18。基线：`4099c8b081e96899aa927f632c0056bc576c503b`（最新origin/master），隔离工作区`.worktrees/r1-a-fup-02`，主工作区未提交修改保留。用户本轮明确确认“FUP-01已通过ChatGPT独立复审”，其提交f779ed858da3bc4dd468645f5405b0fed2556a8d已推送且三项CI成功；满足开工门槛。业务方案A已由负责人确认。

## 1. 判定与修复前分析

ISS-001更新为FIXED_PENDING_REVIEW，等待ChatGPT独立审查，未关闭。原问题包含“欠款仍可完成”及“完成后待办消失”：方案A明确前者合法，实际修复后者及语义/权限显示。

- `order_lifecycle.complete_order`已有transaction.atomic、Order行锁、shipped状态及全部商品发货数量检查；只更新履约状态和更新时间，不读取或清除应收。不改既有完成条件。
- Order.paid_amount为有效客户收款+有效预收分配-退款；outstanding_amount按有效open应收计划余额派生。PaymentPlan按原币核销；完成后计划、退款和逾期均可继续，不应要求收款清零。
- `orderTasks`对completed提前返回[]，是欠款待办消失的根因。原nullish回退也可能在财务摘要被隐藏时回退到订单金额；修复显式权限及缺失值处理。
- 应收列表逾期open+due_date<today、财务概览排除draft/cancelled，不排除completed；数据范围和模块权限仍由原服务端入口控制。历史completed计划可直接读取，不需迁移。

## 2. 最小代码修改及规则

| 文件 | 修改 | 未改变的边界 |
|---|---|---|
| services/finance.py | 新增只读order_receivable_state：由有效receivable计划推导待收/部分收款/款项已结清、逾期余额；草稿/取消、零金额无计划、非零无计划、异常计划待核对分别显示 | Decimal计算；无save、默认计划创建、核销或模型字段新增 |
| views.py workbench | 在payment_summary追加settlement派生信息，finance及transactions均可查看时才返回，否则None | 原paid/balance计算、原数据范围及生命周期API保持 |
| orderOverview.js | completed只允许收款待办，不重现采购/发货；取消空、草稿确认保留；显式canViewPayments；不从被屏蔽payment余额回退 | 非completed原采购/发货任务保留 |
| OrderDetailModal.vue | 履约状态与回款状态分开，逾期提示，完成履约按钮与成功反馈；受权卡片/待办/入口；完成后重新load | 不新增冗余卡片；订单状态持久值不改；API读取失败不显示旧结论 |
| DocumentPage.vue / context.py | 订单列表、客户关联订单列称“履约状态”；列表回款金额列要求财务及流水查看权限 | 合同额/实收口径不变；客户关联仍进入原订单详情/概览 |

结清从计划派生，不能由订单completed判断。后续付款/退款/合法调整通过既有服务改变计划后，下一次GET自然恢复正确状态。零金额订单现有服务不建有效零计划；数据库也禁止非取消零金额计划，本轮未放宽校验。无有效计划不冒称已结清。无需自动更新任何历史completed记录。

完成履约不代表财务结清，也不代表银行结汇。R1-FIN-AUDIT-01及ISS-105提出的人民币实际到账/精度方案未实施；本轮保留原币、汇率、本位币及已有统计口径。

## 3. 实际业务矩阵

环境：全新隔离SQLite，127.0.0.1:5202→只读观察代理8131→真实Django8132，开发超级管理员。无正式RBAC、员工账号或生产连接。详细点击和真实/模拟分类见[原始操作](uat-evidence/r1-a-fup-02/ui-operations.md)。

| 场景 | 结果及分类 | 原始证据 |
|---|---|---|
| A USD500全部发货，收340、待160，完成履约 | REAL_UI_ACTION：10pcs×USD50，真实发货POST201、收款201、完成200；completed欠款160且逾期，采购/发货待办不再出现 | 01–04原图；http-events.jsonl；before/after_complete |
| B 完成后应收链接 | REAL_UI_ACTION：订单专属receivables?order=1，尾款160可查 | 05原图；操作记录 |
| C 尾款逾期 | REAL_UI_ACTION：勾仅看逾期，合同尾款350/已核销190/待结160；fixture日期预设为过去，未改余额 | 05原图及GET状态200 |
| D 再收160 | REAL_UI_ACTION：应收登记201，重新打开订单显示已收500/余额0/款项已结清，履约仍completed，待办消失 | 06原图；database_settled.json |
| E 退款恢复 | REAL_UI_ACTION：客户退款40→201，GET显示460/40、部分收款、逾期40，completed不变 | 07原图；database_refunded.json |
| F 已收齐未发齐 | REAL_UI_ACTION读取已收齐fixture：confirmed，未发货，不显示完成；REAL_API_OBSERVATION完成400且DB不变 | 08原图；api-rejections.json |
| G 四类状态 | REAL_UI_ACTION读草稿/取消/已发货未完成/已完成；未执行额外正式业务动作 | 02、03、10、11原图 |
| H 多计划及分批收款 | REAL_UI_ACTION：340拆150+190，尾款160；最后退款40回退尾款，余额准确。日期来自原分期 | HTTP201及计划/流水快照；自动补充小数金额 |
| I 历史completed欠款 | FIXTURE_SETUP准备已有completed+收100/欠200；REAL_UI_ACTION只读正确显示，无迁移，前后历史单据/计划/流水逐行一致 | 09原图；fixture/final快照与DB断言 |
| J 重复完成 | REAL_API_OBSERVATION再次complete400、全库业务行不变；MOCKED_TEST受控pending反复点击第二入口，两个入口禁用且一个POST | api-rejections.json；database_after_rejections.json；Playwright |
| 权限 | MOCKED_TEST后端屏蔽finance或transactions均返回paid/balance/settlement=None；前端恶意未屏蔽fixture也不显示金额卡/待办/链接，列表金额列隐藏 | 后端7项、Vitest6项、Node状态矩阵、Playwright受限用例 |
| 失败/重开/返回 | REAL_UI_ACTION服务停止→真实读取失败→重试恢复；付款/退款后重新GET、reload和订单/应收/客户入口往返正确 | 13–17原图、browser-api-failure.json；mock另测500及返回 |

FIXTURE_SETUP独立记录：采购/库存准备、未发齐已付、历史订单及特殊状态都在fixture_setup.py，不冒充UI创建验收。主订单发货、340收款、完成、尾款160与退款40均为真实UI操作；API代理只观察转发，不伪造业务结果。无权限测试不等同正式员工UAT，未在真实运行库切换开发身份。

## 4. 数据库一致性与金额

[数据库验证结果](uat-evidence/r1-a-fup-02/database-verification.json)、[原始断言输出](uat-evidence/r1-a-fup-02/database-verification.log)。所有金额用Decimal及逐行对比；没有直接改余额、删历史单据或覆盖流水。

1. before_complete→after_complete：PaymentPlan、Transaction、Shipment、InventoryMovement、InventoryReservation逐行相等；主订单仅履约状态及更新时间更新。应收160保持。
2. settled：计划原币总额500、累计核销500、余额0；主订单completed不变。
3. refunded：计划余额40，原币净收460；流水人民币参考净额3266（500×7.1−40×7.1），原汇率及计算精度保持。未把其宣称为实际银行到账。
4. 两次拒绝完成（主订单已completed、另单未发货）前后全部快照逐行相等；没有重复状态变更/财务写入。
5. 历史订单5及其计划/流水与fixture快照逐行一致；只读新派生字段不会重写旧订单。
6. 财务概览当前应收2笔：主订单40+历史200=USD240，按原合同汇率折人民币1704。合同总额与收付统计未改变；完成状态不作为收清统计依据。

## 5. 自动化与全量

新增后端7项：完成有债务/重放无写入、付款退款状态、已付未发拒绝、历史无计划只读、特殊状态/零金额、字段权限、分期小数及逾期；另验证客户关联列。Node新增8项状态/缺失/权限矩阵；Vitest新增6项动态刷新/权限/导航/历史/失败；Playwright新增3项返回导航/结清退款刷新/受限数据/保存中重复及失败恢复。旧断言关于completed无待办及“完成订单”按已批准规则更新。

| 检查 | 本地结果 / 原始日志 |
|---|---|
| Backend SQLite | 736项，10项按SQLite环境跳过；backend-sqlite.log。最后客户列纯文案补充后，targeted-final 7项通过；最终精确HEAD CI再跑全量 |
| Backend PostgreSQL | 最终精确HEAD GitHub CI，作业日志/URL随交付汇总提供；不以SQLite替代 |
| Node / 额外Node | 129 / typography1项通过；node.log / typography.log |
| Vitest | 626项、62文件通过；vitest.log |
| Playwright | 143项通过；playwright.log；新增重复点击加强断言再跑targeted-final 3项 |
| Frontend Build / migration check | 通过，build.log；无迁移，migrations-check.log |

保留初次测试失败原日志：零计划fixture触发现有数据库约束后改用合法取消零计划；旧completed/列名断言更新；Playwright首次500等待不足既有GET重试退避时间，改为等待最终失败。没有为测试放宽业务约束或改变重试策略。

## 6. 权限、兼容与未覆盖边界

原服务端development_superadmin_enabled、模块权限、订单/客户数据范围保持有效，无DB迁移。新摘要仅在finance与transactions查看权限同时具备时提供；前端同样保护，null不会变成已结清，也不会fallback泄漏余额。既有财务视图/应收API权限继续由原框架控制。

本轮真实UI为开发身份，权限拒绝分支为隔离自动测试，不宣称正式RBAC或员工UAT。付款或退款后需重新获取工作台；本轮验证返回/重开/reload及refreshKey，不新增跨标签实时推送。合同调整恢复欠款共用计划派生，退款已真实验证；所有调整组合、异常历史坏账、所有币种和历史4位尾数的全面迁移不在本轮验收范围。ISS-105、FUP-01既有边界均保留，不借此更改会计政策或其他Issue状态。

## 7. 交付及独立审查

仅ISS-001从BLOCKED转FIXED_PENDING_REVIEW；业务负责人方案A决定及FUP-01独立复审已由本轮用户明确确认，其他Issue状态不变。原图清单和哈希见screenshot-manifest.json；HTTP、步骤、前后数据库、测试原始日志均在docs/uat-evidence/r1-a-fup-02/。浏览器图像为原始JPEG，17张含Chrome真实目视检查。

修复提交为本报告所在Git提交；最终完整SHA、精确HEAD的Backend/Backend PostgreSQL/Frontend三项CI完整URL与结果、原始CI日志在交付汇总及审查ZIP中提供（不自引用提交SHA）。push master后停止，等待ChatGPT独立代码/业务/图片复审决定是否关闭ISS-001；不进入R1-B、正式RBAC、员工UAT或生产部署。
