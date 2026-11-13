# P1-05 操作反馈补验

范围仅为包装默认配置、采购草稿、销售订单导入。保留 A/B/C/D 业务修复，未新增迁移或修改业务状态定义。

集成来源 `5111e7471be6ad712f3fb09238c60e54795009f0`，正常合并提交 `9d70faba035b44cbe127a0045bb8162f73bb495d`；修复源码 `1d96c5ca0d6e5b0011a50918c5f0a0907b15cd03`。

| 项目 | 当前结果与依据 |
|---|---|
| 默认包装 | 当前基线已有修复；慢 PUT 期间显示保存中并禁用退出，503 后保持装箱数 5/净重 0.5，重试 PUT 200 后 GET 回读同一配置。未重复改组件。 |
| 采购草稿 | 已复现并修复：提交挂起时关闭按钮直接卸载抽屉。将 saving 接入现有 busy guard，提交中禁用关闭/取消；失败后恢复编辑、取消与重试。 |
| 销售订单导入 | 已复现并修复：丢响应后同一错误出现两个 alert。保留结果/重试旁提示；尚无预览结果时使用顶部提示，不丢错误信息。原批次恢复与幂等业务机制不变。 |

验收用例复用 `ui-sales-completion-02/seed.py` 的包装及采购来源，与 `sales-order-import-real.spec.js` 首场景和原有隔离 XLSX seed。新增 focused spec 为 `frontend/browser-tests/prelaunch-p1-05-feedback-02.spec.js`，必须通过其专用隔离 profile 运行，普通套件的环境不匹配跳过不计通过。

命令：

```text
npx vitest run tests/unsaved-changes.spec.js tests/quote-editor-availability.spec.js tests/sales-order-import-ux.spec.js tests/import-ux.spec.js --maxWorkers=1
npm run build
npm run test:browser:isolated -- --business-test prelaunch-p1-05-feedback-02.spec.js
```

Chrome 使用本机 `codex` 验收账号；凭据仅由 Git 忽略配置注入进程。设置 `ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_USE_CHROME=1`、8955/8956 端口，以及当前目录 `final` 的绝对证据路径。仅一个 Chrome profile；SQLite 和媒体均由隔离 runner 创建、校验身份并清理。

本地定向 Vitest：4 文件 56 项通过；build 通过，有既有大 chunk 提示。原始 Chrome 首跑两项失败分别为真实采购提交中关闭缺陷，以及真实导入重复 alert 导致严格定位冲突，未把失败当作通过。修复前状态截图与失败详情保留在 `screenshots/before`；修复后的 1366×768 和 1920×1080 原图、接口回读和源码 SHA 保留在 `screenshots/final`。

不使用强制点击。包装失败为请求拦截返回 503；采购失败同样返回 503，成功请求真实落入隔离数据库。导入让服务端实际完成后丢弃首次响应，重新加载、重新选原文件、使用原预览凭证再次确认，要求返回同一 batch_id、仅一张草稿，并 GET 回读结果及下载真实错误 CSV。慢请求各状态通过闸门控制，不靠固定延时截图。

状态为 FIXED_PENDING_REVIEW；协调任务将在最终统一候选精确 HEAD 复验，不自行关闭 Issue。

最终专用 Chrome：2 项通过、0 跳过；Chrome 156.0.8078.80，源码 `5f0d4adb0935f8190b97a85c4cbb2d4163666b93`（仅较业务提交增加截图前关闭忙提示、滚动到反馈区域的脚本调整）。原生 100% 缩放，PNG 尺寸与 SHA-256 见 [manifest](screenshots/manifest.json)。包装/采购回读见 [result.json](screenshots/final/result.json)，导入原批次幂等与查询见 [p1-05-result.json](screenshots/final/p1-05-result.json)。

人工复看了失败提示、重试按钮、提交中和成功状态原图：字段及错误信息可读；导入错误已明确处于重试按钮附近，没有被全局提示遮挡。原始日志在 [logs](logs)。
