# SUNJACK-ERP 内部工作区标签页

工作包 INTERNAL-WORKSPACE-TABS-01。固定基线 `10afcf16fbfc1d0c01a175094012b4b696483cfb`，分支 `codex/internal-workspace-tabs-20261105`。代码候选 `aa8ba801f02e051f694a4c4d9df5b8fb82ca4678`。验证日期为 2026-11-06（中国标准时间）。

- [入口映射](ENTRY-MAPPING.md) 和 [实际处理函数盘点](baseline-handler-map.json) 覆盖侧栏、列表、工作台、创建与编辑、下钻与返回、文件和危险动作。
- [导航契约](NAVIGATION-CONTRACT.md) 包含独立对象、新建草稿、页内导航、提交后接续、缓存和退出接线示例。
- [工作树观察](worktree-observation.json) 和 [共享差异观察](branch-conflict-observation.json) 记录固定观察时点。
- [验证结果](TEST-RESULTS.md) 分列本地自动回归、隔离数据库 API、真实 Chrome 及验收边界。
- [性能测量](PERFORMANCE.md) 包含固定合成负载、请求与挂载、资源清理及测量局限。

当前窗口最多保留 12 个工作区。关闭其他、关闭右侧或关闭单个标签时，取消放弃会保留原任务。活动工作区的业务地址可复制。切换账号或会话失效会清理旧工作区。浏览器刷新只恢复当前业务地址，Chrome 可在用户已经与页面交互时提示未保存内容。
