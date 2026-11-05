# Navigation contract v1 — INTERNAL-WORKSPACE-TABS-01

基线：10afcf16fbfc1d0c01a175094012b4b696483cfb。导航适配不修改权限、业务状态和动作确认。

调用入口：`useWorkspaceNavigation()`，不依赖 App 实例或标签容器 DOM。

```js
const navigation = useWorkspaceNavigation()
// 独立已保存对象：相同 path + detail/edit ID 复用同一工作区。
navigation.openTask({ path: '/orders', query: { detail: String(order.id) } })
// 新建任务：每次调用分配独立 UUID，即使路由完全相同。
navigation.newDraft({ path: '/orders', query: { create: '1', customer: String(customer.id) } })
// 当前任务步骤、筛选、详情子页继续使用 useRouter().push/replace。
// 确认、对象选择、入库/冲销、付款、附件和预览继续调用原处理函数。
```

`workspace` 为可选注入，独立挂载页面时为空；调用方保留原处理函数作为降级。
`storageKey(key)` 生成账号与工作区隔离键，不存储表单正文。业务幂等标识不能因切换标签更新。
`useWorkspaceApi()` 提供 api/listAll，接口与既有调用兼容，绑定关闭信号及写入忙状态。保存成功广播过期提示；其他编辑器不会被自动重载。

工作区使用独立 memory router 与 route 注入；浏览器 router 只承载活动工作区 URL。`__workspace` 是地址中的临时标签身份，不是后端筛选，不改变原深链接参数；原链接无此参数仍可进入。刷新只恢复活动链接，内存草稿不承诺跨刷新或崩溃恢复。

最多同时挂载 12 个工作区，不做静默缓存淘汰。到达上限要求用户保存并关闭标签。关闭先检查整个批次，取消不删除任何标签；提交中不能关闭。

所有修改仅在本包工作树；主工作树和新品提醒包的未提交差异只留存观察。其他移动 HEAD 不作稳定依赖。
