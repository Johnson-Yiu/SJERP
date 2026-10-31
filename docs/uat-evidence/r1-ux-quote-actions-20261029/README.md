# R1-UX-QUOTE-ACTIONS-01 验收记录

本目录记录报价编辑器底部操作区的响应式布局修复。测试数据由专用脚本写入隔离启动器创建的临时 SQLite；不会连接或修改用户业务数据库。业务代码仅调整按钮的布局 class 和组件内窄屏样式，保存、预览、导出及重复提交保护逻辑未改动。

## 执行方式

在 `frontend` 目录运行以下命令；隔离启动器会分配 API/Vite 端口、创建临时数据库和 MEDIA_ROOT，并在运行 Playwright 前验证两个服务及 `/api` 代理的 runId、token、数据库路径和 MEDIA_ROOT：

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
$env:R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR = (Resolve-Path '../docs/uat-evidence/r1-ux-quote-actions-20261029').Path
npm run test:browser:isolated -- --business-test quote-editor-mobile-actions.spec.js
```

完整回归命令及结果见下方测试记录。实际截图通过本地 Chrome/Playwright 操作生成，未使用模拟页面或人工拼图。

## 浏览器截图

使用 `PLAYWRIGHT_CHANNEL=chrome` 启动本机 Chrome Stable（Playwright headless 渲染），浏览器标识为 Chrome 156.0.0.0。截图均来自真实页面交互，非 mock 页面或拼图。四项按钮均在视口内，文字没有横向溢出：

| 视口 | 场景 | 结果 | 文件 |
|---:|---|---|---|
| 1440px | 报价编辑器底部四项操作，单行 | 通过 | `chrome-quote-actions-1440.png` |
| 1024px | 报价编辑器底部四项操作，单行 | 通过 | `chrome-quote-actions-1024.png` |
| 390px | 取消/预览并排；两个保存操作各占整行，主保存宽 366px | 通过 | `chrome-quote-actions-390.png` |
| 320px | 取消/预览并排；两个保存操作各占整行，主保存宽 296px | 通过 | `chrome-quote-actions-320.png` |

## 行为验证

通过：清洁草稿的“取消”关闭编辑器；“预览报价单”打开预览，关闭后仍保留已选 SKU 明细；“保存报价”POST `/api/quotes/` 返回 HTTP 201 并关闭编辑器；“保存并导出 Excel”POST 返回 HTTP 201、导出 GET `/api/quotes/2/export/` 返回 HTTP 200，并产生 `.xlsx` 下载（实际文件保存至本次隔离运行目录，记录文件名和字节数后由启动器清理）。浏览器测量、用户代理及 API 状态详见 `browser-results.json`；合成夹具和本次隔离数据库/MEDIA_ROOT 路径详见 `fixture.json`。隔离启动器在运行后清除了带本次所有权标记的临时目录。

## 自动化与构建

- `node --test src/components/QuoteEditorModal.test.js infrastructure-tests/runner-validation.test.mjs`：19/19 通过；包括端口占用、错误代理身份及两个独立工作树并发隔离。
- `npm run test:browser:isolated -- --business-test quote-editor-mobile-actions.spec.js`：1/1 通过。迁移检查、直接 API 身份、Vite 身份、代理身份均通过。
- `npm run test:unit`：170/170 通过。
- `npm run build`：通过，2018 个模块构建完成。构建报告现有主 JS chunk 超过 500 kB 的警告（1,126.77 kB，gzip 393.72 kB）；本任务未调整拆包。
- `git diff --check`：通过。
- 未触发 GitHub Actions。
