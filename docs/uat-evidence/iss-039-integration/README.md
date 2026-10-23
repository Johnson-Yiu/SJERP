# ISS-039 共享采购成本分摊与跨订单权限

日期：2026-10-24
统一基线：`54925e0a10a48c16ba3b66bbab9e433f48a0e2d7`
分支：`codex/next-iss-039-integration`
旧开发分支/成果：`codex/r1-iss-039` / `372221c0b4a1ea23e9a022b3bbec9eb2ec9775c0`
独立 worktree：`C:\Users\Johnson\.codex\worktrees\next-iss-039-integration\森爵照明管理系统`

## 结论

问题在统一基线已复现，未做假设性修改。采购人员只有 `purchases.update`、没有 `orders.view/update` 时，原成本分配保存返回 `403`，错误为“没有权限修改采购关联的销售订单”。这使后端拒绝查询与前端应有的采购成本归属能力不一致。

本轮对旧提交逐文件比较后只迁移仍需要的 ISS-039 逻辑，没有整体覆盖旧分支，也没有修改 `master`、ISS-041/ISS-042 或其他任务分支。旧提交中的权限调整、候选来源 API、前端来源选择器、审计和回归测试按当前基线逐项重放；保留当前基线已有的新代码和测试契约。修补后：

- 授权采购员通过独立候选接口读取订单 ID、单号、状态，并可调整跨销售员订单归属；候选数据不包含客户、销售价格或利润。
- 只读采购员的候选接口和保存接口均拒绝；成本摘要保留总量和金额，但对无权销售关联显示“销售订单（详情受限）”。
- 无权角色不能进入采购页面；旧 `?detail=1` 采购详情 URL 被路由到访问受限页面。
- 商品成本和公共费用守恒：商品成本 `10000`，公共运费 `1000`，订单 A `3000 + 300`，订单 B `2000 + 200`，库存 `5000 + 500`，总成本 `11000`。
- 保存仍使用版本号和事务；取消销售订单、版本冲突或输入失败不会写入部分分配；不生成付款、库存或销售单据。
- OperationLog 保留操作人、时间、`cost_allocation` 前后值和采购单号；采购员读取日志时不返回销售订单和其他受保护字段。

## 复现与修补证据

修补前的真实 Django APIClient 复现见 [`reproduction-before-fix.log`](reproduction-before-fix.log)：基线测试中，跨销售订单保存实际返回 `403`。最终后端 API 断言和权限矩阵见 [`api-evidence.json`](api-evidence.json)。

## 测试结果

| 范围 | 命令/结果 |
| --- | --- |
| 后端 ISS-039、采购成本、采购数据范围 | 25 项通过；见 [`backend-targeted.log`](backend-targeted.log) |
| 前端 Node 单元/源码回归 | 146 项通过；见 [`node-unit.log`](node-unit.log) |
| 前端生产构建 | 2009 个模块转换，构建通过；见 [`frontend-build.log`](frontend-build.log) |
| 真实 Chrome | 3 项通过：授权采购员、只读采购员、无权角色；见 [`browser-chrome.log`](browser-chrome.log) |

浏览器用独立 5197 端口加载当前 worktree，使用真实 Chrome（`PLAYWRIGHT_CHANNEL=chrome`）。测试覆盖采购旧详情 URL、候选来源、跨订单保存、刷新恢复、只读 403、无权路由和窄屏布局。截图：

- [`authorized-1440px.png`](authorized-1440px.png)
- [`authorized-refresh-1440px.png`](authorized-refresh-1440px.png)
- [`authorized-700px.png`](authorized-700px.png)
- [`readonly-1440px.png`](readonly-1440px.png)
- [`no-permission-700px.png`](no-permission-700px.png)

浏览器页面使用隔离的 mock API 复现三种 UI 角色；真实 Django 权限、金额守恒、版本冲突、失败原子性和审计由后端测试覆盖。当前环境未提供可用于跨账号真实登录的浏览器服务账号，因此没有把 mock Chrome 结果表述为真实登录集成验收。

## 差异边界

修改集中在采购成本权限判断、最小候选 API、采购成本弹窗来源选择、采购页候选加载和对应回归测试。没有改金额计算服务、银行付款、库存、销售单据、报表查询引擎、共享模板模型或审批流程。最终提交 SHA 以分支推送后的 Git 记录为准，本轮不合并 master、不关闭 Issue，等待统一独立审查。
