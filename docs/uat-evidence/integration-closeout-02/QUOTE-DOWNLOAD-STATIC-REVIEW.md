# 报价导出下载静态审查

后续实测补记：原全量失败入口已明确为 `quote-editor-mobile-actions.spec.js:116`，归ISS-020的实际文件交付核实子项。以下是实测前静态快照，不能作为当前根因结论。静默诊断01实际复现取消：HTTP200、Blob完整、anchor已挂DOM、点击时用户激活有效、未到1秒revoke、无点击后导航或对话框。诊断04在269字符内部临时路径下通过，因此路径长不能直接认定为取消原因。各次原始计数及缺失日志限制见 `quote-download-diagnostic-02140bf/`；原全量262通过/1失败仍有效。下一最小调查是捕获失败当次Chrome下载中断原因，再决定修改产品生命周期还是隔离下载工具，不先改共享路由守卫、浏览器安全策略或原测试断言。

## 实测之前的静态快照（原文保留）

审查对象：冻结候选 `02140bf46df27ba1abf5b9018507c07aae825769`，仅检查报价导出调用链和浏览器下载/页面生命周期。未运行浏览器、未改源码或 Git。父级报告的 `262 pass / 1 fail (quote.saveAs canceled)` 仅作背景，本报告不复现该失败。

## 确定事实

- `frontend/src/api.js:47-59`：`downloadQuoteExport()` 先等待 `/quotes/{id}/export/` Blob 请求，再创建 Blob URL、向 `document.body` 添加 `<a download="{quoteNo}.xlsx">` 并同步调用 `click()`；1 秒后移除 anchor 并 revoke URL。这里没有与组件卸载绑定的取消/清理，也没有集中下载生命周期管理。
- `frontend/src/components/QuoteEditorModal.vue:292-310`：保存请求成功后先 `emit('saved', response.data)`，再（若“保存并导出”）等待 `downloadQuoteExport()`，成功后才 `emit('close')`。`emit('saved')` 不等待父级 async handler 完成。重试导出同样是等待下载后发 close。
- `frontend/src/views/DocumentPage.vue:269-276` 的 `handleQuoteSaved()` 会先清除 modal query、等待列表 `load()`，并在没有 `returnTo` 时再 `router.push()` 打开报价详情。若当前 URL 带 `create`/`edit`，`clearModalRoute()` 会 `router.replace()`；`route.query.create/edit` watcher 随后调用 `syncModalFromRoute()`，其无 action 分支将 `quoteEditorOpen=false`，可能在子组件的导出 Blob 请求仍等待时卸载编辑器。
- 因而“saved 事件 → 父级路由/列表异步工作”与“子级导出请求”存在确定的并行时序；但子级已经启动的 API Promise 没有被父级显式 abort，下载 anchor 被挂在 `document.body`，组件卸载本身也没有 revoke 此 URL。`router.replace/push` 是 Vue Router SPA 导航；静态代码未显示这条路径执行整页 `location` 跳转。
- 全局 `frontend/src/main.js:46-47` 的 `pagehide`/`beforeunload` 监听只保存滚动位置；没有全局下载 anchor 清理或 Blob URL 撤销。其他导出点各自设置延迟 revoke，没有发现会统一取消报价下载的全局卸载处理。
- 相关 Playwright 场景（如 `frontend/browser-tests/quote-editor-mobile-actions.spec.js:108-118`、`iss029-recipient-snapshot.spec.js:65-72`）在点击前注册 download waiter，随后 `saveAs()`。本次提供的信息未指出 262/1 中具体失败的 spec，故该归属为 UNKNOWN。

## 待验证假设（不是已确认根因）

1. **路由竞态可能影响时序，但单独不足以解释取消。** `saved` 监听会发起 replace、列表请求及可能的详情 push；这些可能在导出 GET 完成前关闭/卸载 modal。由于没有发现请求 abort、整页导航或卸载时 revoke，不能仅凭该竞态断言它取消了 Chrome 下载。建议 Dewey 用同 SHA 对照：延迟父级 replace/load 与不延迟，记录导出请求、anchor click、download 事件及页面卸载时序。
2. **用户激活跨异步边界可能丢失。** “保存并导出”在用户点击后先等待保存 POST，再等待单独的 Blob GET，最后以脚本 `anchor.click()` 触发下载。Chrome 对该异步链的实际处理需用受控场景确认；静态代码不能认定浏览器策略是本次根因。可对比直接导出与保存后导出，并保留同一上下文及下载生命周期。
3. **1 秒 revoke 的竞态尚无证据。** URL 在 `click()` 后固定 1 秒撤销；若 Chrome 已开始消费 Blob 通常应能继续，但本次没有事件时间戳证明下载启动早于 revoke。需要记录 click、`download` 事件、保存完成/取消与 revoke 的相对时间，再决定是否相关。

## 供父级验证的线索

最具体的代码线索是 `QuoteEditorModal` 在启动导出前发出未等待的 `saved` 事件，而 `DocumentPage.handleQuoteSaved` 会立刻清 query 并执行异步列表/详情导航；路由 watcher 可先卸载 modal。请 Dewey 将这条并行时序与父级同 SHA 的缓存内/外控制分开验证。当前证据只确认竞态存在，**不确认它导致 `saveAs canceled`**；本审查没有提出源码修复。
