# E2-R2 产品运营界面

## 产品详情修复

被测基线为 `43067137d0fba04b0be055e449e55a06dba6d208`。在产品列表打开合成长名称产品 EVID-P001，检查抽屉左缘、产品名称及左侧信息卡。桌面四组中，抽屉左缘均为 24 CSS px，可用工作区起点为 248 CSS px。窄屏 100% 进入关联证书后，关闭按钮没有获得焦点。原始 390×844、125% 的失败记录还捕获了过渡中位置，单凭该记录无法认定窄屏有稳态溢出。[原始失败记录和截图](chrome-baseline/failure.md)

产品抽屉和嵌套证书抽屉按所属工作区的实际宽度布局。产品长名称换行。进入嵌套证书时，焦点移至关闭按钮，父产品工作区仍显示产品名称。按 Esc 返回触发按钮，再按 Esc 关闭父抽屉并返回列表。修复集中在 `frontend/src/components/EntityDetailModal.vue` 和 `frontend/src/views/ProductPage.vue` 的产品抽屉分支。原有共享样式表未编辑。

最终被测产品源码为 `df1a32e0a2631fb14ce5e370ef4c9b14444a0de8`。通过六组 Chrome 矩阵，覆盖 1366×768、1440×900、390×844 和原生 100%／125%。桌面左缘为 272 CSS px，可用区起点为 248 CSS px。390×844、125% 下嵌套证书顶边与父抽屉顶边均为 130 CSS px。验证名称完整可见、信息卡和标签可达、内容区可滚动、关闭按钮可达、返回和键盘焦点恢复。浏览器为 Google Chrome 156.0.8078.80，使用独立持久上下文修改 Chrome 外观设置的原生缩放，并在页面读回 DPR。数据来自真实隔离 Django、独立 SQLite 和媒体目录，以测试库 codex 账号登录。截图绑定各次产品源码 SHA。[中间修复记录](chrome-product-detail/run.json) · [最终记录和截图](chrome-final/run.json)

## 自动化检查

| 检查 | 结果 |
| --- | --- |
| 产品、SKU、采购、库存、销售与采购文案定向 Vitest | 首次修复源码 14 文件 145 条通过 |
| 最终产品源码定向 Vitest | 4 文件 13 条通过，覆盖产品工作区、产品主档、库存导航及关联报价入口 |
| 最终产品源码定向 Node | 16 条通过，覆盖 ResourcePage、HistoryOrdersPage 和详情抽屉排版 |
| 隔离 SQLite 定向 Django | 69 条通过，覆盖产品与分类、SKU 身份及动态组合、SKU 图片、供应绑定、交易单位、采购关联和库存冲销 |
| GitHub Actions | NOT_RUN |
| 最终候选全量 SQLite、PostgreSQL 17、Node/Vitest、构建与通用浏览器 | A3 负责 |

详见[剩余状态与既有证据](gaps.md)。

## 隔离重跑

设置本机 `ISOLATED_TEST_PYTHON`、`ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT` 以及 Git 忽略的 codex 测试凭据。安装锁定的前端依赖后，在仓库根目录运行。记录目录应指向本包内独立的运行目录，防止覆盖原始截图。脚本会保留已采集的证据，并在必验断言失败时以失败退出。

```powershell
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-completion-02.spec.js
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-prefix-02.spec.js
node frontend/scripts/run-isolated-browser-tests.mjs --business-test ui-product-operations-parameter-02.spec.js
```

本包源码的 Vite 生产构建通过。Vite 报告原有大包体积警告。

## 补验与失败归因

- **型号前缀**通过。真实后端对已占用前缀返回 400。影响预览在六组尺寸可达，取消后读回产品和 SKU 的旧值，确认请求返回 200，读回产品前缀、受影响销售型号及不变的 SKU 编码。[通过记录](chrome-prefix-verified/run.json)
- **产品参数**通过。390×844、原生 125% 下真实 POST 返回 201。重新加载产品参数页面后，从列表打开已保存行，核对名称、参数值 48 和单位 V。[保存重开记录](chrome-parameter-cross-check/run.json)
- **销售与历史共用界面**通过定向检查。390×844、原生 100%／125% 下分别打开客户管理与历史订单分析，确认标题、活动工作区标签及顶栏底边与工作区顶边对齐。[跨模块记录](chrome-parameter-cross-check/run.json)
- **原始失败**保留。H1 重复运行四个桌面组合仍触发左裁断言，窄屏两个组合仍触发旧嵌套定位或焦点检查。[H1 重跑结果](chrome-baseline-repeat/run.json)
- **中间失败**保留。型号前缀首个样本缺少旧产品前缀，随后两个样本缺少参与销售型号生成的参数或缩写。参数首轮在保存自动打开的详情后直接点被覆盖的列表按钮，第二轮关闭详情后仍未返回独立参数列表。最终分别补齐合成前缀属性和明确重开参数列表。[前缀第一轮](chrome-prefix/run.json) · [前缀第二轮](chrome-prefix-final/run.json) · [前缀第三轮](chrome-prefix-third/run.json) · [参数第一轮](chrome-parameter-first/run.json) · [参数第二轮](chrome-parameter-second/run.json)

型号前缀和产品参数只修改了隔离数据库里的合成资料。参数运行记录对应 `9083414b469257cb608f5d83d67d5684579058e6`，相对最终产品源码 `df1a32e0a2631fb14ce5e370ef4c9b14444a0de8` 的差异只有本包脚本和证据。产品代码等价可以用 `git diff df1a32e0 9083414b -- frontend/src backend` 复核。

## A3 复审后补验

- **客户详情编辑**。H1 的窄屏样式隐藏“编辑客户”。E2 保留这一个客户主操作，其余详情动作维持原有布局。单独验证 E2 修复时，入口已可点击且表单带回正确客户，原详情却仍挡住“取消”。E1 将表单移至详情上方并在编辑期间停用底层抽屉。组合源码 `41e88660a292026449bbe1bd944e6744f93c7cf8` 的 ResourcePage 与 E1 `b52f3edc5c4ea47ed265f86d94ccdce0134b24d6` 同文件内容。真实 Chrome 390×844 原生 100%／125% 均实测点击入口、回填及取消关闭。 [原始选择器失败](chrome-customer-edit-first/run.json) · [E2 单独复现遮挡](chrome-customer-edit-obscured/run.json) · [组合修复通过](chrome-customer-edit-combined/run.json)
- **共用抽屉回归**。客户编辑入口修复后的产品详情及嵌套证书仍通过六组视口与缩放。 [复验索引](chrome-customer-edit-product-regression/run.json)
- **SKU 历史版本**。更新产品型号前缀后，从原 SKU 打开历史版本。真实接口和页面均展示修改前的销售型号，SKU 编码不变。 [版本回显](chrome-prefix-version/run.json)
- **分类**。将无产品引用的合成分类拖至新父级后，重新加载核对持久化父级与继承属性只读。拖动子分类内两个自有属性后查看重排预览，确认并重新加载核对顺序。使用 DOM 拖放事件触发真实后端。 [分类重排](chrome-category-order/run.json)
- **供应来源和采购回填**。保存供应型号和参考价，切换同一 SKU 首选来源并核对旧首选撤销。采购单 CNY 与供应来源 USD 不一致时提示且留空，切换 USD 后明确选定档案回填 8.50，保存真实草稿并读回供应来源和单价。 [采购回填](chrome-supplier-purchase/run.json)
- **模拟浏览器用例**。A3 原记录中的 SKU 和包装只读失败，均由模拟会话少了 authenticated 字段导致。补齐字段后原 SKU 17 条、包装 9 条通过，原业务断言保留。真实后端证据见各自索引。GitHub Actions 为 NOT_RUN。

- **分类覆盖**。在子分类新增同名属性，重开后只显示子分类自有且可编辑的属性，真实接口中的有效属性也指向新记录。 [继承覆盖](chrome-category-override/run.json)
- **共享箱规和尾货策略**。共享箱规关联两个已验证 SKU，改为人工处理尾货时出现影响确认。确认后两条 SKU 保留箱规关联，但原验证失效。重开读回新策略。 [共享箱规](chrome-shared-carton/run.json)
- **交易规格停用**。采购草稿保存两箱、每箱 10 件及每箱 85 USD。读回基础数量 20、基础单价 8.50 USD 与交易快照。停用该规格后，旧采购草稿仍可打开并保留原换算快照，选择器标记为历史规格。 [采购和交易快照](chrome-supplier-purchase-trade/run.json)

- **SKU 动态组合和图片**。暂停出站请求观察提交中禁用，随后转发真实后端，一次保存 4 个不同 SKU。重新打开确认同样四组均归为已存在。上传并更换两张合成图片，每次读回新图片，清除后真实接口无图，刷新再进入编辑也无预览。图片修改未新增商业身份版本。 [SKU 组合和图片](chrome-sku-lifecycle/run.json)

## 待独立复审

- **SKU 图片删除后立即重开可能显示旧图**。390×844、原生 125% 下给新 SKU 上传和替换图片，保存时清除图片。真实 DELETE 成功且 SKU 详情接口已无图。列表刷新尚未完成时立即重开编辑，旧预览仍显示。候选位置为 `SKUPage.vue` 的 `persistSave` 成功分支先关闭编辑器再加载列表，以及 `openEdit` 从列表行读取图片。影响同页快速重开的编辑预览。 [原始失败和图片写入截图](chrome-sku-lifecycle-immediate-reopen/run.json)
- **库存详情缺少批次或货位标识**。在库存流水中按仓库名筛出同 SKU 的两条不同批次，打开第一条后，抽屉能展示流水号和仓库，但不显示已有批次。候选位置为 `EntityDetailModal.vue` 的库存 `detailInfo` 字段映射。影响同仓多批次的界面辨识。 [原始失败](chrome-same-warehouse-lot-label-missing/run.json)

以上问题保留供独立复审。批次号搜索沿用现有产品范围。
