# 集成接线

独立组件 `frontend/src/components/NewProductReminders.vue`，路由 `/new-product-reminders`，模块权限 followups；服务端另要求客户查看及客户数据范围。

- `tag=新品提醒` 或 API `tag=new-product-reminder`：固定类型筛选，类型来自独立记录，不解析备注。
- `customer=<ID>`：限定列表和新建预选客户。
- `follow_up=<ID>`：新建来源跟进，可选，服务端检查属于同一客户。
- `detail=<需求ID>`：精确重开；详情允许定位已作废需求，仍检查权限/范围。
- `search=<关键词>`、`state=active|void|all`、`page=<页>`：列表状态；查询改变清理旧详情，异步详情不能覆盖后来选择。

已有主档沿用 `/customers?detail=<ID>`、`/follow-ups?detail=<ID>`、`/products?detail=<ID>`。

本包对 ResourcePage 仅增加顶部入口和客户/跟进行的链接；router 仅增加一个路由。没有修改标签页容器或导航架构。标签页包可替换这些链接的打开方式，保留查询参数及精确记录 ID。若共享文件产生冲突，保留其最新结构后手工接回这两处入口；不要整文件覆盖。

后端共享文件最小差异：models.py 追加模型及拒绝集合删除的管理器；urls.py 注册；views.py 在客户/联系人/跟进/产品的现有删除规则中纳入新品提醒保护。服务和序列化均在专属 new_product_reminders.py。
