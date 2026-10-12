# R0-D4B2-B UI 验收证据

代码：7e5e565e44e5abafd292c65c166f366cf6f2ba11。
CI：https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38232779023
Backend、Backend PostgreSQL、Frontend 全部 SUCCESS。Backend 690（SQLite 跳过 10），PostgreSQL 690；Frontend Vitest 492、Node 121、独立排版测试 1，构建成功。

使用 Codex 内置浏览器、隔离 SQLite 数据库和虚构验收身份。原开发环境权限未修改。

- 01：self 范围的混合订单成本只读；可见自己的订单，遮蔽跨部门订单。
- 02：共享采购正常入库，仅显示可见销售关联。
- 03：采购入库正常冲销，状态和库存回退，保留历史入库记录。
- 04 / 05：共享供应商 Context 采购信息可见，受限来源销售订单隐藏。
- 06：all 且具备模块权限，两个跨部门销售订单的成本分摊成功保存 V1。
- 07：缺少 orders、finance、transactions 权限，独立采购库存成本成功保存。
- 08：缺少 orders.view 时所有销售归属身份隐藏，整单修改禁用。

BLOCKED：现有成本接口整单替换、重算全部费用，尚无跨范围订单委托授权；含无权修改订单的整单调整需由具备全部关联订单权限的人员处理。部门 / 部门树 / all 的授权协作仍正常。

已有 P2：供应商 Context 状态显示 ordered；冲销后仍保留先前到货成功提示。两项不影响 API 权限和库存状态，本轮记录，不扩张重构。

完成后等待独立复审，不进入 B2-C。
