# A2 与 H1 集成验收

A2 远端分支 `codex/release-completion-acceptance-02` 指向 `8aba8356707be7610901810f68d1a8f76c131479`。该交付的最终业务冻结提交为其直接父提交 `d836ba21a657a3a61b770a1d124a5b1fb62a9f46`。H1 合入前的远端为 `ba77563c71beb5a4cb5ad79a413761d79bcca42b`。集成业务候选为 `fb2e973c06c55d685744cc97e3dc0bfd8d755253`。

- `reporting.py` 保留 D2 的分类快照身份，按 H1 的统一明细读取层累加金额及各单位的数量。
- 历史承接用例继续核对更正后的历史数量，断言改从新档的归档明细读取。中文更正表单、字段提示清除及旧版嵌套补充资料保留 A2 处理，页面同时接入 H1 商品关联。
- 采购详情同时使用 A2 的财务尝试恢复逻辑和 H1 的历史商品展示。核对 A2 的资金及收付款服务、恢复组合函数、采购付款弹窗与共享样式均与冻结源码一致。
- 迁移依赖为 `0128_merge_release_integration` → `0129_historical_product_linking` → `0130_history_product_candidate_rules`。A2 交付未修改此迁移链。用隔离 PostgreSQL 从 0128 带合成旧明细升级，核对原标识和金额，再执行新测试库回归。
- 集成提交 `293dd06d` 后，`fb2e973c` 仅将 H1 的 Vue 组件测试文件从 `.test.js` 改为 `.spec.js`。该变动让 Vitest 运行该测试，避免 Node 原生测试器误收。合并提交与最终候选的业务及浏览器测试源码相同。

E1 来源 `86a3a2fe96f0d0dad5fb5aa08d423ae633addcc4`，E2 来源 `50be7d8a377cffb0635ce193c02feb44f37cc985`。使用两条远端分支已有的取证脚本及合成种子，在 H1 工作树启动隔离浏览器实例。E1 取受共享样式影响的客户、销售入口，E2 取产品、采购、库存入口及采购详情各页签。

GitHub Actions 记为 `NOT_RUN`，交付提交使用 `[skip ci]`。

## 本机运行与重试

| 检查 | 命令或范围 | 结果 |
| --- | --- | --- |
| Node | `npm run test:unit` | 197 通过 |
| 排版 | `node --test tests/detail-drawer-typography.spec.js` | 1 通过 |
| Vitest | `node node_modules/vitest/vitest.mjs run tests src --environment jsdom --exclude '**/*.test.js' --exclude '**/detail-drawer-typography.spec.js' --pool=threads --maxWorkers=1 --reporter=verbose` | 90 文件、837 项通过。首轮双 worker 有 5 个文件启动超时，单 worker 完整重跑覆盖 |
| 前端构建 | `npm run build` | 通过，Vite 保留主包体积提示 |
| H1 Chrome | 独立 SQLite、实际账号、原生 100% 和 125%，1366／1440／390 | 批量预览、409 冲突、注入 503 后重试、SKU 跳转和历史归集通过。实际 CSV 随证据保存。首次登录等待 5 秒不足，复跑使用 45 秒等待。见 [截图与测量](a2-h1-history/chrome-checks.json) |
| E1 Chrome | 窄屏报价编辑，客户编辑、列表请求失败后重试及销售订单数量预览 | 报价编辑与扩展信息截图，客户编辑 HTTP 200，列表失败与恢复均有实图。客户保存后重定位未取得所需画面。数量预览复跑先完成订单确认，再取得预览 HTTP 200 和原生 100%／125% 图。见 [报价索引](a2-h1-e1/run.json)、[客户业务索引](a2-h1-e1-journeys/run.json) 和 [销售订单索引](a2-h1-e1-order/run.json) |
| A2 Chrome | `sales-order-import-real.spec.js` 及库存丢响应的定向复跑 | 首轮 10 通过、1 超时。单独复跑库存用例通过，11 项均已在同一源码取得通过记录。覆盖收款恢复、实际退款日期、资金复核和历史更正。见 [专项截图与结果](a2-h1-a2/) |
| E2 Chrome | 源脚本 `ui-product-operations-state-evidence-01.spec.js`，`PRODUCT_OPS_FOLLOWUP=candidate` | 60 张图，索引未报缺项，覆盖产品、采购、库存列表与采购详情页签。首次 Django 身份探针超时，120 秒后复跑成功。见 [60 项索引](a2-h1-e2/run.json) |

后端使用 Windows Python 3.14.5、Django 6.0.9。PostgreSQL 17 与 SQLite 各使用独立测试库及媒体目录。PostgreSQL 命令为 `python docs/uat-evidence/history-product-sku-linking-01/run-postgres.py --full --postgres-bin <PG17-bin>`。SQLite 从 `backend` 运行 `python manage.py test --noinput -v 2`。两次均指定 UTF-8 和本机 OpenSSL。最早的全量尝试从仓库根目录启动，Django 未发现测试，已在正确目录重跑。

浏览器测试采用本机 Chrome 156 或仓库默认 Playwright 通道。E1、E2 和 A2 独立专项使用仓库隔离脚本及本机忽略配置。临时脚本只延长身份探针等待，实例标记、SQLite 与媒体目录校验保留。A2 销售导入种子要求使用其白名单证据目录，首轮误指定 H1 目录被拒绝。重跑使用白名单目录并单独归档本轮证据。

## 全量结果与剩余问题

- SQLite 全量在业务候选 `fb2e973c` 执行 1776 项，1654 通过、122 跳过，0 失败。PostgreSQL 全量在同一候选执行 1776 项，1737 通过、38 跳过、1 错误。唯一错误发生于 H1 并发用例准备上传时，前置 HTTP 413 用例的临时路径已不存在。未进入并发断言。[SQLite 输出](a2-h1-logs/sqlite-full.txt) · [PostgreSQL 输出](a2-h1-logs/postgres-full.txt)
- 后续提交 `e751b033` 固定 H1 并发夹具的上传设置，并让历史浏览器用例显式切换到关联 SKU 口径，补齐只读身份模拟。第一次 PostgreSQL 定向复跑 5 项断言通过，测试库销毁时发现两个线程连接仍开着。提交 `b1fb55e5c87e435a6b3e9f14a14dd64077c9cd39` 在 worker 退出时关闭连接。最终定向执行 HTTP 413 与 H1 全部用例，5/5 通过并完成测试库销毁与集群停止。历史报表两个浏览器文件共 4/4 通过。以上提交只改测试源码，未再重跑整套全量。全量原始结果与定向结果分别保留。[第一次定向](a2-h1-logs/postgres-assertions-first-retry.txt) · [最终定向](a2-h1-logs/postgres-upload-concurrency.txt) · [历史报表 02](a2-h1-logs/history-report-02.txt) · [历史报表 03](a2-h1-logs/history-report-03.txt)
- 通用 Playwright 运行 `npm run test:browser`。主组初次在 Django 身份探针超时。120 秒身份等待的主组复跑实际发现 289 项，231 通过、54 失败、1 跳过、3 未运行。真实会话子组 4/4。主组包含在 A2 源码即可确认的旧资金页面选择器，也包含超时、共用种子客户编号冲突、历史报表旧口径及只读身份模拟。其余失败按原始日志保留，未全部归因。因共用种子冲突未覆盖的订单和采购主体组在独立运行取得 4/4。独立共享报表和库存存储复跑分别 1/1、10/10。报价图片快照隔离复跑仍失败，PI iframe 内图片在 45 秒内保持隐藏。完整浏览器门槛继续待验。[主组输出](a2-h1-logs/browser-business-retry.txt) · [隔离组退出状态](a2-h1-logs/browser-profile-status.json) · [图片复跑](a2-h1-logs/image-preview-retry.txt)
- E1、E2 和 A2 专项按各自证据范围复核。H1 六组原生缩放、实际 CSV、409 和重试均通过。E1 客户保存后重新定位截图仍缺，E2 60 项截图索引无缺项。公共台账保留现有 Issue 状态，集成候选待独立复审。
