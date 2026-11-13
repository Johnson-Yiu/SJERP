# SJERP COST-CURRENCY-INTEGRITY-02

状态：FIXED_PENDING_REVIEW。B1/B2/B3 实现于独立分支 `codex/cost-currency-integrity-02`；等待协调候选的精确 HEAD 跨包复验及独立复审，不自行关闭 Issue。

共同基线：`d7d155b994b652f6f4f777edde22a257a8ed7a2e`。
业务提交：`3dfd2b813c209148aebdfe65d315fae632d179f5`（已正常推送，无跳过 CI 标记）。

## B1：历史接续

- 前端参考读取 `sku_cost_currency`；保留销售币种 `sku_currency` 的原有含义。
- 人工成本金额、明确的三位成本币种、核实状态与依据进入审批指纹及不可变 `line_links`。不换汇，不要求人工成本等于当前主档，也不重写历史原单。
- 受控创建通过内部 `save(preserve_cost_snapshot=True)` 保存完整快照，普通 API 没有该选项。普通新建订单仍由 SKU/报价确定成本币种和核实状态，客户端提交任意快照不能覆盖它们。
- 审核后改变主档金额/币种仍保留已审核人工快照；生成草稿、回读、正式确认均保持一致。历史接续草稿原有禁止普通 PATCH 的保护继续生效；申请表保存与重开通过正常服务进行，没有为验收放开直接修改。

## B2：派生 SKU

- 沿用现有选定来源 `source_ids[0]`，一起继承金额、成本币种、核实时间及核实人。没有增加平均成本算法。
- 仅派生服务使用内部 `save(preserve_unknown_cost_currency=True)`；来源未知币种保持未知，人工新建仍默认 CNY。
- 拆分覆盖 USD/EUR/CNY/未知币种；合并用 EUR 与 USD 不同金额来源确认选定来源一致。keep、refresh、旧 SKU/历史库存关联、生成后的报价和订单快照均有回归。

## B3：只读检查

命令：在已明确授权的数据副本执行 `python manage.py inspect_cost_integrity`。本轮仅在隔离合成数据执行，未读取或修改正式数据库。

- 比较历史接续 `line_links`、与批准指纹一致的原申请及当前订单行。原申请与不可变关联记录自身冲突才标 `confirmed_mismatch`；当前行不同、行被替换、金额证据缺失或可能后续人工更改标 `needs_review`。
- SKU 关系树未冻结当时成本及选择来源，不能根据今日父 SKU 推定历史错误。未知币种、与关系来源不同的后继成本列 `needs_review`。
- 不提供批量修正入口，不重标 CNY，不推算汇率。正式快照若需更正，必须结合原件走既有受控、留痕流程。
- 测试用数据库执行包装器拒绝全部非 SELECT SQL，验证检查器只读；合成后续人工改币种仍为待核实，合成原始记录冲突才为确认错配。

## 验证与复跑

- SQLite：`python manage.py test crm.tests.test_sku_cost_verification crm.tests.test_history_operational_contracts crm.tests.test_sku_plans_candidates --noinput`，46 项通过、2 个 PG 专项跳过（不记为通过）；另补只读原始记录冲突反例 1 项。
- PostgreSQL 17：已有隔离 runner `docs/uat-evidence/history-product-sku-linking-01/run-postgres.py --postgres-bin <PG17 bin> --test-label <模块或测试>`。核心 45 项全部通过（含并发和 TRUNCATE 不可变记录保护）；补测 keep/refresh、派生后报价/订单快照 2 项通过；只读报告反例单独记录。
- 前端：`npx vitest run tests/history-takeover.spec.js --maxWorkers=1`，14 项通过；`npm run build` 通过，存在既有大 chunk 提示。
- Chrome：`npm run test:browser:isolated -- --business-test cost-currency-integrity-02.spec.js`。设置 `ISOLATED_PLAYWRIGHT_USE_CHROME=1`、`ISOLATED_CODEX_TEST_SUPERADMIN=1`，凭据从 Git 忽略的本机 `local-data/codex-test.env` 注入，不写日志。证据根必须为当前工作树 `docs/uat-evidence` 内绝对路径；端口 B 为 8955/8956。
- 旧基线：独立 sparse worktree，仅检出应用源码，复制本次 spec/seed 作为测试工具，`COST_BASELINE=1`，9035/9036。应用代码仍是共同基线；不回退当前工作树。应复现错误的 SKU 销售币种参考和独立成本 EUR 保存 400。
- 最终 Chrome 视口 1366×768、1920×1080，原生 100%；原始图不裁切缩放。真实点击、保存响应及重新加载后的原生状态接口共同验证；未使用强制点击或 DOM 存在作为成功依据。

最终 Chrome 已通过，版本 156.0.8078.80，源码 SHA 为上述业务提交。旧基线用例也已通过预期反例断言（实际保存 400，不作为功能通过）。人工查看原图：旧图明确错误引用销售 USD；新图显示成本参考 CNY，人工 USD 与 9.3750 保存后保持一致，1366/1920 文案及输入框可读。

| 证据 | 路径 |
|---|---|
| 旧基线原始图 1366×768 | [baseline-1366.png](screenshots/baseline-1366.png) |
| 修复后原始图 1366×768 | [fixed-1366.png](screenshots/fixed-1366.png) |
| 修复后原始图 1920×1080 | [fixed-1920.png](screenshots/fixed-1920.png) |
| 源码 SHA、视口、Chrome、接口结果 | [旧基线](screenshots/baseline-result.json)、[修复后](screenshots/fixed-result.json) |
| 关键数据库、前端、Chrome 原始日志 | [logs](logs) |

只读原始冲突反例：SQLite 1 项通过；PostgreSQL17 与后续修改待核实反例合计 2 项通过。PG runner 均自行建立并关闭新集群，浏览器 runner 均确认自有 SQLite/MEDIA_ROOT 并在完成后清理，端口已释放。

业务提交 CI：<https://github.com/Johnson-Yiu/SJERP/actions/runs/43474478444>。Frontend Vitest 出现失败，后续 CI 浏览器及 build 为 skipped，不能称 CI 全绿；已定位为新品需求测试 5 项（scrollIntoView 在 jsdom 不存在及连带 wrapper 失败）与 SKU 管理旧文案断言 1 项；由协调任务收拢 D/C 包修复后在统一候选复验。本包本地定向 Vitest、独立真实 Chrome 和 build 已分别运行并通过。

## 原始失败及处理

1. 首次运行测试时修改中的模型尚未被已启动的 Python 进程重新载入，派生内部参数报错；进程重启后消失。
2. 新增测试错误地尝试普通 PATCH 接续草稿，被既有完整性校验拒绝；保留保护，改为验证拒绝、回读和正式确认。拆分用例产品名称重复，改为每种币种独立名称。
3. Chrome 脚本最初未展开原生 details，随后尾部额外 POST 缺 CSRF；分别修正展开和直接使用页面原生状态响应。页面本身保存及回读成功，但失败运行不作为最终通过。
4. 完整旧基线 worktree 因磁盘空间不足失败，Git 自动清理该新副本；改为 sparse 工作树，不清理共享或既有数据。旧基线端口占用后换用独立端口。

全局项目台账由协调任务维护。本包不涉及 A 的 Transaction 函数或取消退款成果，不产生迁移，不合并 master、不部署、不正式导入。
