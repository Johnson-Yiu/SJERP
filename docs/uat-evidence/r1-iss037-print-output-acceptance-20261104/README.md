# ISS-037 打印成品验收：进行中

## PRINT-ACCEPTANCE-CLOSEOUT 核查（2026-11-04）

### 用户协助实际打印（2026-11-04）

用户确认先前看到的打印窗口曾被取消；因此之前“未出现窗口”的表述仅是自动化未观察到，不能认定窗口不存在。随后在内置浏览器内打开隔离合成草稿 `SYNTH-6FEC752D` 的已保存 PI，用户在实际打印界面选择保存 PDF，并提供桌面文件。归档副本 `user-ui-print-synth-6FEC752D.pdf` SHA256 `e8cc7b7c0d795d16117c98bdec96ab251254192cfcb8371b80de6b07e1b9f044`，两页 A4；目视渲染 `user-print-page-1.png`、`user-print-page-2.png`。第一页可见合成买卖方、银行、商品文字及 USD 10.00，第二页仅有合成银行提示，打印页脚含本地隔离网址。当前打印设置含浏览器页眉页脚，尚未比较不同边距/页眉设置，不能仅凭本样本断言分页问题根因。样本无商品图片、收件人、长描述、多行，且为草稿而非正式报价，不作为完整正式打印矩阵通过。

本次证明实际 UI 打印可经用户操作生成文件；自动化点击超时不等同应用未打开打印窗口。剩余真实 UI 打印矩阵、打印分页优化及模板/卖方变化后三方对账仍待核实；不自动修改旧快照或将这份单一合成样本扩展为 ISSUE 完成。此前提交 `8eeef9a90b1dbcdc3361d366a53528a5899beedd` 的 [CI #41774944240](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41774944240) 最终 backend、backend-postgres 成功，frontend 失败，具体原因见下文，未作为 PASS。

远端规则提交 `f5f23339278f9dd5a121093c9d86a8a9bba819a2` 已快进，原有三份本地未提交生成文件未覆盖。本地采用内存 SQLite 与专用临时媒体，`python manage.py test crm.tests.test_quote_template_snapshot crm.tests.test_quote_template_migration crm.tests.test_iss020_quote_export --verbosity 1`：19 项通过；`npm run build` 通过（保留原有大包警告）。这些只证明对应自动化，不等同 UI 成品矩阵。

规则提交的 [CI #41772625020](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41772625020)：backend、backend-postgres 成功；frontend 在隔离 Playwright 阶段失败，随后构建未运行。日志中 229 项通过、1 项失败；失败是本分支 `Chrome UI print to PDF` 强制 `headless:false`，Linux runner 报 `Missing X server or $DISPLAY`，浏览器没有启动。这是该测试的 CI 图形环境条件失败，不能据此推断产品打印成功或失败，也不能将其跳过写成通过。此前本机内置浏览器实际点击的输入调用超时，打印按钮保持禁用，无可见打印窗口、无 PDF；具体原因仍未确定。现有已保存版本样本是草稿，尚不能代替正式报价。

工作包状态：A 的两项现象及 CI 失败路径已定位，应用阻塞与浏览器/宿主的根因仍未隔离；B 的真实 UI PDF、正式文件逐页和模板变化后跨预览/XLSX/打印对账仍 BLOCKED；C 的本地后端定向及构建通过，完整最终 CI 需以新提交的真实结果另行核验。解除条件是在获准且可操作内置浏览器打印对话的隔离环境中取得实际 PDF，并对全部场景逐项对账；不更换为用户禁止的浏览器，不把独立渲染或打印事件当成 UI 成品。

基线 `d5abc64750d00c89d685bf12c0f8f67d4ba10a97`。本记录只覆盖合成数据的局部检查，**不构成实际 UI 打印成品验收通过**，不关闭 ISS-037。

## 本轮已核实

- 现有已保存 PI 的 iframe 打印入口直接调用 `print()`，没有等待图片或字体。隔离数据库、真实 Chrome 的图片失败回归先失败：图片已损坏，点击打印后没有出现“图片加载失败”提示。此前专项报告只证明 `beforeprint`，没有成品 PDF。
- 最小前端补修：已保存 PI 打印前检查 iframe、等待图片和字体，失败或超时显示中文提示并阻止打印；未保存草稿路径不变。没有修改模型、迁移或保存版本的模板。
- `npm run test:browser:isolated -- --business-test iss037-print-output-acceptance.spec.js`：独立运行中的前两项通过，覆盖图片失败提示及阻止打印、390×844 正常资源时调用打印。`image-failure-1440.png` 与 `saved-preview-390.png` 是该轮真实浏览器截图。资源正常测试替换了 `window.print` 为测试探针，不能证明实际输出。
- `npx vitest run tests/final-polish.spec.js --environment jsdom`：19 项通过；`npm run build` 通过，存在既有大包警告。隔离运行器完成 Django check 和全新 SQLite 迁移；真实 `/api/quotes/1/pi-data/` 返回 200。测试使用合成客户、卖方、银行、商品和隔离媒体，无业务数据库。
- 隔离内存 SQLite 执行 `python manage.py test crm.tests.test_quote_template_snapshot crm.tests.test_quote_template_migration --verbosity 1`：12 项通过；包含既有保存模板变更与 XLSX 检查，但并非本轮实际 UI 打印成品交叉验收。
- `independent-chrome-render.pdf` 是从保存报价 iframe 内容复制到独立页面后，由 Playwright Chrome `page.pdf()` 生成的单页 A4 **独立渲染样本**，不是用户界面打印成品。`independent-page-1.png` 为该 PDF 的人工目视页面：可见合成买卖方、银行与 10.00 USD；该夹具没有商品图片、收件人或长描述，不能据此认定相应验收通过。窄屏截图展示的是响应式屏幕预览，不代表纸张输出。

## 未完成及失败证据

2026-11-04 内置浏览器重试：按用户要求不使用 Chrome，采用 Codex 内置浏览器和独立 SQLite、私有媒体及合成报价 `SYNTH-0ABBAB0C`。服务标识校验和迁移检查通过，`/api/quotes/1/pi-data/` HTTP 200；界面可见保存版本的合成买卖方、银行和 USD 10.00。点击“导出 PI PDF”后浏览器输入调用超时，页面显示按钮被禁用，系统窗口列表未显示打印对话框；未获得 PDF。不能据此判断打印实现、内置浏览器或打印环境的具体故障根因。手工停止本轮测试服务后 4626/4627 无监听；本轮临时目录 `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-HO4Emj` 仍保留，未删除。此次预览为合成草稿，不代表正式报价成品验收。

2026-11-04 04:00 后续：`npm run test:browser:isolated -- --business-test iss037-print-font-failure.spec.js` 通过 1 项，真实 Chrome 中构造加载失败的字体，验证中文提示及未调用打印；见 `font-failure-1440.png`。复查本机存在 Microsoft Print to PDF，但不代表已取得 Chrome 成品。将 UI 同一按钮的触发改为异步，以排除测试等待同步打印调用作为唯一原因后，再运行原浏览器文件：图片和窄屏探针两项通过，UI 成品测试仍 30 秒超时、目录无 PDF，结果 **2 passed、1 failed**；该轮隔离服务和临时目录已正常清理。不能据此判断根因一定是 Chrome、打印对话或应用，需要在可操作打印对话的隔离桌面继续排查。

真实 UI 打印尝试使用独立 Chrome profile、`--kiosk-printing` 与 Save as PDF 配置，点击界面按钮；该测试 30 秒超时，未产生 PDF，随后 worker teardown 超时。测试汇总为 **2 passed、1 failed、1 teardown error**，不得写成全通过。隔离 API/Vite 已停止；仅定位并停止了命令行含本次临时目录的两个 Chrome 进程。临时目录 `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-sggleQ` 因 Chrome profile lock 保留，未清除用户数据。后续应先核实该路径及残留状态，再使用可控的真实 Chrome 打印对话或其他获准路径生成并人工检查 UI 成品。

尚未完成：实际 UI PDF/纸张；修改当前模板及卖方配置后同一报价的预览、XLSX、打印交叉对账；商品图片和收件人；长描述、多行多页、空字段、历史模板缺失及资源失败的完整矩阵；窄屏触发的实际纸张布局；原始 HTTP/测试日志归档。图片及字体加载失败提示已有定向验证，但不能扩展为所有资源异常全部通过。

下一步保留现有修复、隔离数据和首次失败事实；修复打印成品测试环境后重跑全部验收，检查 PDF 每页并与保存快照/XLSX 对账。不得因本记录或局部测试通过宣布任务完成。
