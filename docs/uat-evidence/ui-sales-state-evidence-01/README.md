# 客户与销售界面状态取证 01

[可达状态清单](states.md) · [截图与运行索引](screens/run.json) · [复现与复审记录](reproduction.md)

- 测试源码 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`。fetch 后与远端 `codex/release-integration-repair-01` 一致。取证分支上的后续文件是证据和本包脚本。
- 本机 Google Chrome `156.0.8078.80`，通过 CDP `Browser.getVersion` 读取运行版本。Playwright 启动独立的 Chrome 无头配置。Chrome 设置页切换原生 100%／125%，每张截图记录 DPR 和有效 CSS 宽度。输入视口为 1366×768、1440×900、390×844，390px 在 125% 下为 312 CSS px。
- 正常画面连接本包独立 Django 与 Vite，独立临时 SQLite、媒体和随机端口。运行器核对直连和代理的实例身份后才执行。真实登录隔离测试超管 codex，开发身份关闭。长客户名及联系人由真实 UI POST 创建，响应 201。其他合成样本的生成方式见本包脚本。
- 文件名格式为“状态编号-视口宽度-缩放百分比”。JSON 中的 `uncaptured` 是该次脚本未取得画面。运行通过只表示脚本完成，覆盖仍按各状态和截图核对。
- 本包执行 43 项定向 Node 检查，全部通过。业务代码、公共样本、公共运行器及台账均未修改。

## 可沿用证据

| 状态 | 既有文件及版本核对 | 可沿用边界 |
| --- | --- | --- |
| Q05 正式报价 XLSX | [实际文件](../release-integration-repair-01/browser/quote-editor-mobile-actions.spec/downloaded-quote.xlsx) · [运行数据](../release-integration-repair-01/browser/quote-editor-mobile-actions.spec/browser-results.json) · [清单](../release-integration-repair-01/download-manifest.json)。原记录业务候选 `019367baa389c2a73ea2d8c58162313e4868fcca`，证据入库 `9cd04fbb5bd8fd45b14b5b0e08c9cfb5de0cf2ec`。重新计算 SHA-256 为 `ab93e4420bcbc2fc4cfcea8b2008c519e47f574cbf5cc340b7f0fb3541f0b705`，与清单一致。 | 对比候选到本包基线，报价导出生产代码无差异。保留实际下载、风险确认后下载结果与保存路径。原截图保留为原版本布局证据，基线共享 CSS 已移除 body 的 320px 最小宽度。 |
| C02/C09 并行客户草稿 | [原截图](../release-integration-repair-01/browser/workspace-integration-real.spec/desktop-parallel-drafts.png)和[原验收](../release-integration-repair-01/README.md)。业务候选同上。 | 保留保存后原筛选返回及并行草稿复原的行为证据。 |
| C10 新品需求工作区 | [原截图](../release-integration-repair-01/browser/workspace-integration-real.spec/desktop-reminder.png)和[原验收](../release-integration-repair-01/README.md)。业务候选同上。 | 保留不同客户上下文隔离和需求保存的行为证据。 |

## 首轮截图边界

- C01、Q01、O01、C06 记录页面入口与可见区域。列表尚显示加载或数据落在视口外时，按截图所见判定。
- C02、C08、Q02、O02 为新建或编辑器；C03 为真实搜索无匹配。C07 以抽屉关闭按钮定位，可能落在进场过渡或真实加载中。最终客户详情以补充证据为准。
- 首轮 C04/C05 的表单选择器不符当前组件，C06 一组导航超时，C08 两组操作等待超时。这些属于取证失败记录。
- 表内未关联证据的校验、提交中、请求失败、保存后、只读、脏表单离开与相关业务组合仍待补验。重点包括主体版本审批、多阶段履约、发货及冲销、附件真实上传及重开和关联选择器子窗体。A2 责任及打印延期见状态清单。

## 复跑

在独立 worktree 根目录，按本机忽略配置加载 `ERP_TEST_USERNAME` 和 `ERP_TEST_PASSWORD`，配置 `ISOLATED_TEST_PYTHON` 及 `ISOLATED_CODEX_TEST_SUPERADMIN=1`。设置 `ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT` 为本目录绝对路径，`SALES_STATE_EVIDENCE_DIR` 为其中的单独运行子目录。基础矩阵使用默认配置。补验矩阵设置 `SALES_STATE_SUPPLEMENTAL=1`，加载与横移复核设置 `SALES_STATE_FOCUSED=1`。运行：

```text
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-sales-state-evidence-01.spec.js
```

## A2 固定候选

A2 还在处理候选时保留本包基线。取得冻结 SHA 后，比较 `workspaceRoutes.js`、`App.vue`、客户和单据页、抽屉/表单/选择器、`styles.css` 及相关 API 和后端，再按状态编号选取受影响分支补验。候选截图和测试源码 SHA 单独登记。

## 补充取证

补充矩阵沿用基线，索引见 [补充运行数据](supplemental/run.json)。本包种子建立一张长单号报价、一张长单号订单，各四条明细。种子只在校验通过的隔离库内运行。PI 预览保留软件内置的卖方模板，业务单据和买方数据使用合成记录。确认框样本停在确认前，待上传附件样本停在提交前。

补充编号：C05A 为两件待上传附件，C07R 为客户抽屉加载后，C11 为通过 Playwright 中止客户列表请求的受控尝试；O05D 为草稿详情；Q02R/Q02X 是报价新建在横移前后的比较。实际捕获状态以 JSON 中的 `file` 字段为准。首个补充运行因合成种子的订单明细字段错误退出，修正后复跑，错误未归为产品缺陷。

补充运行在 480 秒超时，已保留超时前落盘的 31 张截图。原脚本在截图前验证了缩放与有效宽度，但原始逐状态运行数据未落盘。补充索引从现有截图重建，未推算缺失的数值。后续脚本改为每个状态后落盘，可设置 `SALES_STATE_WIDTH=390` 等单视口定向补测。本轮 C11 未留下截图，因此受控失败未覆盖。
