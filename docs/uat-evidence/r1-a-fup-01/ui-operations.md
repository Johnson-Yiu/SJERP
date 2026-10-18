# REAL_UI_ACTION 操作原始记录
2026-10-18，IAB http://127.0.0.1:5198/transactions，独立SQLite；Chrome同URL补充视觉。
A 新增空白→取消→直接关闭，无确认。
B 新增→金额12.34→取消→未保存修改→继续编辑，金额仍12.34；Chrome金额20→关闭→同样确认。
E 类型其他期间费用，USD12.34，汇率7.123456，备注FUP01-LOST-RESPONSE→保存；真实上游201后代理断开响应，页面结果不明确，FIN-75D1A0251671428F019397C0DBD9B26F仍显示。
F 点击保存，同号请求→真实400，页面明确编号重复不等于成功。
G 点击取消→记账结果尚未确认，含原编号及另建重复风险。
H 返回核对→编号/金额/币种/汇率/备注/错误保留；点击订单管理→相同风险确认→返回核对，仍在原表单。最后关闭→已记录编号，放弃表单→查询，仅一笔12.34。
I/J 连续新增两笔期间费用USD2.34，汇率7.123456，备注FUP01-REAL-PAYMENT-1/2→各自保存成功；不同FIN号，各一笔16.6689。
D 新增客户收款→搜索FUP01→选择FUP01-ORDER→金额20，EUR→保存；真实400合同币种不一致，保留编号FIN-476F73FE8F6AB2C7561FF4E883BDF5B3；取消→继续编辑→USD、金额21→保存成功，原编号及订单不变。
C 保存中所有入口与浏览器beforeunload分支由Vitest受控pending测试验证，属于MOCKED_TEST，不写成真实网络UI验收。Chrome reload未取得原生dialog可观测证据，原生弹窗视觉仍未覆盖；beforeunload事件拦截自动测试通过。
HTTP原始状态/请求/响应：transport-events.jsonl。数据库：database-after-lost-response.json / database-after-retry.json / database-final.json。
