# Q6 报价状态验收记录

共同起点为 `3048697fdba660390fe9361fa12ac8517a170fb1`。指定 SJERP 远端的 S5 分支指向同一完整 SHA。Q6 使用独立工作树。

| 项目 | 核销进度 |
| --- | --- |
| QUO-01 | 六组通过。SKU 无匹配后重新检索并选择两条商品，2 箱折合 20 pcs，库存缺口 5 pcs；另一 SKU 的 3 pcs 可覆盖。存在缺口时真实保存返回 201。 |
| QUO-02 | 六组通过。负价定位第二条单价，81 字符型号收到真实 400 并定位第一条型号。纠正后保存 201，重开回读两个明细。 |
| QUO-03 | 六组通过。原版与修订风险取消均无导出请求；对正式原版和修订版各自的目标导出 GET 注入 400，解除后真实重试 200。逐组实际下载并对账原版与修订 XLSX。完整打印及分页沿用原延期。 |
| QUO-04 | 沿用六组报价加载错误、真实重试、条款备注回显及上一报价隔离。六组实测草稿禁用、发送、本人申请及自批入口隐藏、撤回和待审批失效。更正审批、草稿生成及批准后失效六组通过；拒绝与替换的 1366×768 两档补跑通过，其他有效组合沿用原证据。 |

## QUO-04 证据接续

- [S5 运行记录](../sales-state-closeout-05/so-01.json)的取证源码为 `fd5d19429f54ca117065385fa251c33f4cfce75b`。执行 `git diff --quiet fd5d1942 HEAD -- frontend backend` 返回 0。S5 专项对目标报价的工作台 GET 注入 400，移除拦截后使用界面重试并等待真实成功响应，核对正确报价和条款备注，且旧备注未出现。记录的六组尺寸和原生缩放均有对应的 `quo-04-loaded-*.png`。
- [双人审批候选记录](../ui-sales-state-evidence-01/party-approval/run.json)记录了申请、本人不能审批、另一身份审批。截图组合为三个尺寸的 100%。[主体专项](../party-version-closeout-20261105/README.md)另有审批生成草稿和工作簿对账。两份记录仍需比对当前源码及入口后才能抵扣主体矩阵。
- 当前 `QuoteDetailModal.vue` 中有待审批更正/替换、不同身份审批、批准更正后生成草稿、批准替换后填写关联新单，以及有条件的撤回、拒绝和失效入口。旧专项 `party-lifecycle-real.spec.js` 确实操作撤回和拒绝并回读请求状态，不能由此推定失效或其他组合通过。

## 本地运行

从 `frontend` 执行 `node --test src/components/SalesRules.test.js src/components/QuoteEditorModal.test.js src/components/QuoteDetailModal.test.js`，14 项通过。最终源码的 `npm run build` 通过。并行运行的本地 `npm run test:unit` 为 196 通过、1 失败，失败项是两独立工作树运行器的身份连接超时。该用例未改，单独复跑另记。Q6 专项独立执行结果见下方。当前没有将矩阵缺项列为不适用。

## U4 接线待办

接线包含两条独立专项、隔离身份、合成种子、Chrome 和证据归档。公共配置本次没有变更，详见 U4 清单。

## Q6 独立专项

运行入口为 `node frontend/scripts/run-isolated-browser-tests.mjs --business-test quote-state-closeout-06.spec.js`。从本机忽略配置载入隔离 codex 凭据，设置 `ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_USE_CHROME=1` 和 `ISOLATED_TEST_PYTHON`。通过 Chrome 设置调整原生缩放，逐组合核对 DPR 和 CSS 视口宽度。测试从隔离根读取登录会话，业务请求走该轮 Django，独立合成数据以 Q6 命名。

- 负价首次运行没有获得原生校验焦点。保存按钮的 `type=button` 直接调用组件校验，浏览器自动聚焦并非原实现的契约。实际缺口是“请填写每条 SKU 的本次售价”没有标识哪条单价。修复后提示明细序号与单价，并聚焦该输入。
- 超过既有 80 字符的报价型号由真实 POST 返回 400。修复前通用提示只写“商品明细”，修复后识别服务端索引对象，提示明细序号和报价型号，并聚焦对应输入。未改变后端限制。
- [报价校验聚焦时的修前叠层](screenshots/model-header-overlap-before.png)可见聚焦明细盖住标题。报价弹窗现在将标题与底部操作区置于明细之上，并把聚焦字段滚动到可见区域。
- 390×844 原生 100% 首轮第二次搜索后，正常复选框点击被 SKU 预览区遮挡。报价内的单列选择器增加独立结果区高度。390×844 原生 125% 首轮“标记为已发送”还被报价详情标题装饰伪元素命中，报价详情已将装饰层设为不接收指针事件。
- 独立后端回归 `python manage.py test crm.tests.test_party_request_lifecycle crm.tests.test_iss020_quote_export crm.tests.test_quote_template_snapshot --noinput` 在内存 SQLite 中发现 30 项，25 通过、5 跳过。Chrome 专项独立于通用 CI。

## 双人主体证据

[E1 双人拒绝/撤回及替换复跑](../ui-sales-completion-02/a3-followup.md)的 125% 结果记录独立申请人、复核人、真实 HTTP 和关联草稿 PI 回读。同范围 100% 证据见 [E1 主体生命周期补验](../ui-sales-completion-02/README.md#报价主体生命周期补验)。从归档提交 `608e1203` 到本次源码，`QuoteDetailModal.vue` 的主体分支未变，报价详情的唯一差异为标题装饰不接收指针。关联替换组件、主体服务、报价路由和模板快照实现无差异。按原记录实际尺寸沿用。Q6 独立补验见下。

[U4 接线与共享问题](U4.md)

## 六组专项与实际 XLSX

Chrome 156.0.8078.80，源码 `e1cda3a9fa8fd401509fa77d1e6c78a0166a85d9`，隔离运行 `869bccfd-1f4b-4963-ada0-156669515499`，端口 11774/11775。Playwright 专项 1/1 通过，内部六组全部通过，退出后释放本轮端口及临时数据库、媒体。证据提交仅追加文档和产物。

[逐组合运行结果](run.json)记录 12 个实际下载的 XLSX 文件的字节数、SHA-256、报价号、版本、买方、卖方快照匹配、币种、两行商品描述/型号、单位、数量、单价、小计和合计。以保存版本的真实 PI DTO 核对工作簿。原版为 USD 289.75，修订把散件数量由 3 改为 4，合计 USD 303.00；两版冻结模板哈希一致。报价号含修订后缀，工作簿通过完整单号绑定版本。文件来自仓库现有模板，公开证据只保留脱敏对账摘要，原件留在本地忽略的 `downloads/`。未将打印或分页纳入本轮核销。

## QUO-04 独立复核补验

从工作树根运行 `node frontend/scripts/run-isolated-browser-tests.mjs --business-test quote-state-closeout-06-review.spec.js`，使用与主专项相同的身份和 Chrome 环境参数。独立运行 `3059f05b-c075-41d3-9d51-610c49f9a167`，端口 9713/9714，源码 `37a53bc6da13ebfabe1307c8a1a0dcb5c078f907`。Playwright 1/1 通过，实际操作 16 项。

- 六组均以 codex 在真实界面独立批准待审批更正，生成草稿并读回批准地址。另六次先批准、再失效，并回读终态。
- 1366×768 原生 100%／125% 分别真实拒绝另一发起人的申请，并批准主体替换、生成关联草稿和读回目标客户。其他尺寸的相应动作精确沿用 E1 的原生两档实际结果。
- 审批的前置请求由隔离种子通过现行服务生成，发起人是只有夹具用的合成账号，无可用密码。浏览器只登录既有 codex。独立审核的身份与发起身份由真实后端区分。
- [复核运行记录](review-run.json)和 [复核截图](review/)保存六组结果。S5 的恢复证据用于报价加载和备注隔离。
