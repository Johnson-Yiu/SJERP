# NEW-PRODUCT-REMINDERS-01

固定基线：10afcf16fbfc1d0c01a175094012b4b696483cfb。独立分支 codex/new-product-reminders-20261105。
公共台账由集成维护，本包不修改。AGENTS.md、PROJECT_ISSUES.md、PROJECT_PHASES.md、REVIEW_PROTOCOL.md 已核对；旧跟进 UI/附件结论不扩大到本包。历史问题不自行关闭。

## 现有能力与范围

复用 Customer、Contact、FollowUp、Product 主档、sales_scope、ModuleActionPermission、user_can 和不可变 OperationLog。现有主档没有通用标签模型；本包使用固定响应 tag=新品提醒及专属结构化记录，不解析旧备注。
需求是客户/跟进下的增量子记录，不复制客户或建立第二套沟通系统。可自由填写产品、规格及其他要求；联系人、产品、来源跟进均可选。客户及跟进引用不可通过普通修改迁移。
开发记录人及历史均明确“开发超级管理员（非实名员工）”，不把默认姓名当实名；即使旧开发审计开关关闭，本包仍写 OperationLog。

## 风险/权限矩阵

| 入口 | 服务器检查 | 完整性/拒绝 |
|---|---|---|
| 列表/关键词/固定标签/详情/历史 | 客户查看 + 跟进查看；客户范围 | 默认有效，显式作废/全部，记录粒度分页 |
| 新建 | 客户查看 + 跟进新建；客户范围 | 自由文本必填，关联同一客户；提交 UUID 幂等 |
| 修改 | 客户查看 + 跟进修改；客户范围 | 必填版本；禁止普通写入作废/记录人字段 |
| 作废 | 客户查看 + 跟进修改；客户范围 | 原因必填、CAS版本；不可恢复 |
| 关联展示/跳转 | 关联模块查看 + 目标既有范围 | 无权产品/联系人引用从响应及历史隐藏 |
| 删除/批量删除 | 不提供方法 | 405；ORM实例/集合拒绝删除；外键 PROTECT |
| 历史 | 同需求权限与范围 | 复用不可变审计；审计失败同事务回滚 |

## 导航接线契约

普通路由 `/new-product-reminders?tag=新品提醒&customer=<ID>&follow_up=<ID>&detail=<需求ID>&search=<关键词>&state=active|void|all&page=<页>`。
`customer` 限定列表及新建预选，`follow_up` 为新建来源，`detail` 精确重开包含已作废记录。客户/跟进沿用 `/customers?detail=<ID>`、`/follow-ups?detail=<ID>`。
ResourcePage 仅增加客户/跟进列表入口和行链接（未重构）；router 仅新增路由。ERP 标签页包后续按稳定契约替换这些入口，组件本身不依赖标签页容器。

## 验收状态

实施中，具体结果见最终 README 和 logs；GitHub Actions NOT_RUN（用户额度暂停）。不合 master、不部署、不启用正式 RBAC、不使用真实客户、不发送任何消息。
