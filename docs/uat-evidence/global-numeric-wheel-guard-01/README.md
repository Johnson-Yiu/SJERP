# GLOBAL-NUMERIC-WHEEL-GUARD-01 验收证据

## 基线与范围

- 稳定集成基线：`f886b064c694589acd60e5a910c5858e26846376`（`[skip ci] Integrate receipt settlement entry`）。
- 独立工作树：`.task-worktrees/global-numeric-wheel-guard-01`；分支：`codex/global-numeric-wheel-guard-01`。
- 扫描范围：`frontend/src` 中原生 `input[type=number]`、`v-money-input`、`role=spinbutton`、数值输入法及已有 wheel 处理。原生数字控件覆盖金额、数量、单价、汇率、比例、尺寸、重量、箱规等页面字段；未发现需逐页移除的 wheel 处理器。
- 产品改动仅在前端全局入口和共享工具；后端只增加隔离浏览器测试用合成数据 fixture。没有修改财务表单、金额精度、业务字段类型、状态语义或后端业务逻辑。

## 实现行为

`frontend/src/utils/numericWheelGuard.js` 在窗口捕获阶段注册单个委托监听器，识别原生 number 输入和 `role=spinbutton`。命中时取消浏览器/自定义 wheel 步进，按原滚动方向和距离转发到最近可滚动祖先；遇到嵌套容器边界时继续检查外层容器，并尊重 `overscroll-behavior`。普通文字输入和文本域保留浏览器默认滚动。弱映射保证单例安装，卸载函数可重复安全调用。

`frontend/src/main.js` 启动时统一安装，HMR dispose 时清理。新增/切换路由、工作区标签、动态行及弹窗无需额外注册监听。

## 自动与真实 Chrome 验证

- 定向 Vitest：`src/utils/numericWheelGuard.test.js`，**4/4 通过**。覆盖数值与自定义 spinbutton 阻断、焦点输入框、普通文本控件、监听单例和清理。
- 隔离浏览器套件：`global-numeric-wheel-guard.spec.js`，**2/2 通过**。使用安装版 Chrome 和 Playwright `page.mouse.wheel()` 原生鼠标滚轮输入，不以合成 `WheelEvent` 作为阻断证据。
- 原生滚轮用例覆盖正/负数、小数、空值、只读、禁用、已聚焦/未聚焦、聚焦控件与指针分离、页面滚动、弹窗滚动、嵌套滚动与外层接续、动态新增行、工作区标签切换、普通文本框和文本域；滚轮不产生 input/change/save 事件或绑定模型变化。Tab、方向键、输入、粘贴和显式 stepUp 按钮仍可用。
- 真实 ERP 表单滚轮验证：财务记账金额、报价汇率、订单汇率、SKU 单个重量、包装模板尺寸、库存调整数量。数值、输入/change 事件计数和派生预览保持一致；拦截器确认没有发出非 GET API 请求。只有存在纵向滚动余量的表单容器才断言容器位置变化；固定布局无溢出时由通用页面/弹窗用例验证滚动行为。
- 后端由隔离 runner 建临时 SQLite 与媒体目录，加入一条合成客户、产品、SKU；测试完成后 runner 清理临时数据库和媒体目录。没有使用业务库。
- 生产构建：`npm run build`，成功；Vite 提示现有主 JS chunk 大于 500 kB。
- CI：**NOT_RUN**（按要求未触发）。

## 截图

以下图片来自上述隔离 Chrome 实际业务页面，使用合成数据；没有保存凭据。

| 页面 | 证据 |
| --- | --- |
| 页面、弹窗和嵌套滚动控件 | [通用滚轮布局](browser/global-numeric-wheel-guard.spec/chrome-page-and-dialog-wheel.png) |
| 财务记账 | [财务金额输入](browser/global-numeric-wheel-guard.spec/real-finance-form.png) |
| 报价 | [报价汇率输入](browser/global-numeric-wheel-guard.spec/real-quote-form.png) |
| 订单 | [订单汇率输入](browser/global-numeric-wheel-guard.spec/real-order-form.png) |
| SKU 包装 | [单个重量输入](browser/global-numeric-wheel-guard.spec/real-sku-packaging-form.png) |
| 包装管理 | [包装尺寸输入](browser/global-numeric-wheel-guard.spec/real-packaging-form.png) |
| 库存流水 | [库存调整数量输入](browser/global-numeric-wheel-guard.spec/real-inventory-form.png) |

测试使用更宽的视口检查桌面页面；没有覆盖全部业务字段的人工逐项巡检，也没有验证不同操作系统、浏览器的触控板驱动差异。公共问题台账按任务约定交由财务集成工作包汇总，本包不直接改写台账。
