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
`storageKey(key)` 生成账号与工作区隔离键。`storageKey(key, { accountOnly: true })` 仅用于报表图表布局等账号偏好。银行事实页的 sessionStorage 只保存流水号、幂等键、时间和尝试标记；表单金额、账户、分配、凭证与备注留在内存。业务幂等标识不能因切换标签更新。滚动恢复仅使用当前账号与工作区的会话键，键里不保留筛选词。
`useWorkspaceApi()` 提供 api/listAll，接口与既有调用兼容，绑定关闭信号及写入忙状态。保存成功广播过期提示；其他编辑器不会被自动重载。

工作区使用独立 memory router 与 route 注入；浏览器 router 只承载活动工作区 URL。`history.state.__workspace` 将浏览器历史项关联到同一窗口中的标签，不出现在业务 URL。兼容早期含 `__workspace` 的链接并移除临时查询字段。复制或直接访问链接仍按业务路由进入。刷新只恢复活动链接；未保存的表单只在内存保留。

最多同时挂载 12 个工作区，不做静默缓存淘汰。到达上限要求用户保存并关闭标签。关闭先检查整个批次，取消不删除任何标签；提交中不能关闭。

所有修改仅在本包工作树；主工作树和新品提醒包的未提交差异只留存观察。其他移动 HEAD 不作稳定依赖。

## 身份包接线与共享文件

`useWorkspaceNavigation().confirmExit()`：退出登录前调用；返回 false 时保留原身份和所有任务，返回 true 后再执行身份包原退出动作。强制会话失效无法阻止时，以清理旧任务和拒绝旧响应为先，不承诺恢复原内存草稿。

`adoptObject(location)`：保存成功且原表单已经标记 clean 后，把当前新建标签接续为已保存对象；不产生一个遗留草稿标签加一个详情标签。`openTask` 用于独立任务，`router.push/replace` 用于当前任务步骤；replace 会保留浏览器历史的替换语义。关闭对象详情或明确取消同路由新建草稿时，若原列表仍打开，恢复该列表的筛选、页码和滚动。报价保存并导出期间保留原编辑工作区，文件下载完成或用户结束编辑后再接续详情。直接链接进入且没有原列表时，当前工作区继续承接列表。

当前身份接口增加只读 `user_id` 元数据：真实已认证用户取服务端主键；匿名开发身份为 null。这个字段不是登录或权限判定，不把开发默认姓名变成真实操作人。App 以 user_id（兼容 profile ID）隔离缓存，不以显示姓名或前端角色判断授权。服务端 `development_superadmin_enabled()` 与原权限矩阵、RBAC 开关均保持原规则。

身份包成功登录、退出或账号变化时继续调用原 `setAccessOperator`；本包只增加过时请求世代保护，防止上一身份的权限请求成功/失败覆写新身份。API 401 发出会话边界信号，销毁旧标签并中止其绑定请求；响应 epoch 不符时拒绝旧响应。正式登录/退出产品界面仍由身份包拥有，合成切换验收不冒充真实员工登录验收。

共享冲突处理：App.vue 的原侧栏/身份区保留，只增加容器与边界接线；router.js 的原权限检查抽到 navigationAccess.js 并复用；原路由表逐项移到 workspaceRoutes.js；api.js 增加生命周期元数据，导出函数只增加可选 signal 配置；backend/crm/views.py 仅 current_operator 三个响应增加 user_id。不把其他包的移动 HEAD 合入，不整文件覆盖其他工作树。
