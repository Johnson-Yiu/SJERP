# 财务概览连续 500 自动重试对照

运行：在本工作树根目录启动隔离前端副本 `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4900 --strictPort`，然后运行 `node docs/uat-evidence/export-stability-closeout-20261105/finance/retry-500-control/diagnose.cjs`。真实 Chrome 156.0.8078.80，1440px，API 为诊断脚本模拟，不连接后端。测试页面取自提交 56ce3588f544fcfeb98d431fb71d7e2d937f67db，页面 blob 与复制件均为 76bc2f4fdf5cfbad7842744c38e1167c174fea6a（setup.json）；其余前端为当前源码的隔离副本。所用 api.js 保存为 api-used.js；与 `git show 56ce3588:frontend/src/api.js` 字节相同，采用现有 GET 自动重试逻辑。

首次点击后 6 次请求（原始 1 次 + 5 次自动重试）全部模拟 HTTP 500。自动重试耗尽后页面显示“服务器暂时不可用，请稍后重试。”，导出按钮可用。再次手动点击后第 7 次请求返回模拟 HTTP 200，下载 `账面收支参考-2026-10-01-2026-10-19.csv`，检查 BOM 和内容成功；文件 SHA-256 ea6595c73c52df8fd58d559e24e83991ac833af976b1c1092a5ae3b5f0b0c7a1。测试脚本退出码 0。

完整事件及时间戳见 diagnose.log、events.json；保留下载、失败和成功截图、脚本及 Vite 日志。服务已停止，临时源码和 node_modules 链接已清理。本次为独立新增 500 诊断，不是重建此前未保留的首次 500 原始日志；原 400 证据未覆盖。
