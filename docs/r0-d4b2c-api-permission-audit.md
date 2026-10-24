# R0-D4B2-C API 权限审查

基线：`7e5e565`。本轮保留开发超级管理员入口和既有采购、财务、库存业务流程。

## 权限矩阵

| 数据域 / 入口 | 操作权限 | 数据范围及关联约束 |
| --- | --- | --- |
| 客户、联系人、跟进 | 各自模块的 view/create/update/delete/export | 客户归属按 self / department / department_tree / all；联系人、跟进沿客户归属。附件读取与跟进记录使用相同权限及范围。 |
| 报价、报价版本、销售订单、合同变更 | quotes / orders 模块权限；合同变更另需 finance 对应动作 | 报价及销售订单按客户范围；从报价、采购、财务、库存关联销售记录时同时校验 orders.view、范围及写权限。 |
| 供应商、采购、收货 | suppliers / purchases 模块权限 | 共享采购记录不按销售员归属隔离。关联销售订单的编号、客户和分摊只对有 orders.view 且在范围内的订单显示；写入分摊另需 orders.update。 |
| 库存、发货 | inventory 模块权限 | 企业库存流水共享；若流水或发货关联销售订单，订单信息遵守 orders.view 与客户范围，变更/冲销同时需要 orders.update。 |
| 财务流水、收付款计划 | transactions / finance 模块权限 | 客户收款及销售订单费用按客户范围；供应商付款、公共费用保持共享；订单/采购计划及流水关联需对应合同模块权限。 |
| Dashboard、报表、导出 | dashboard / reports；导出单独 reports.export；财务统计另需 finance 与 transactions | 每个来源只在来源模块有 view 时计算，继续套用来源数据范围；导出与屏幕统计复用同一查询范围。 |
| 导入、预览、执行 | imports 的 import；关联数据类型模块权限 | 预览和执行均校验权限、数据范围及签名快照；不允许通过导入写入无权客户或业务关联。 |
| SKU、产品、参数、证书、供应商来源 | 对应 products / skus / suppliers / parameters / certificates 等模块 | 共享产品档案依模块访问；嵌套订单、采购、库存和供应商数据须按来源模块及关联范围过滤。 |
| Context、Workbench、搜索与筛选 | 主对象模块 + 返回的关联模块 | 每个嵌套列表、统计、快照字段分别应用对应模块权限和数据范围；搜索只在已授权 queryset 中执行。 |
| 操作日志、历史快照 | 日志所属模块 view | 销售实体日志按对象客户范围筛选；采购共享日志不泄露无权订单、财务关联快照。 |
| 未映射 API | 必须显式映射模块或声明公开 | RBAC 启用时 fail closed；不以“已登录”代替模块权限。 |

## 初审风险清单

| ID | 级别 | 已确认风险 | 修复 / 处置 |
| --- | --- | --- | --- |
| C-01 | P1 · 已修复 | `action_for_request` 先按 SAFE_METHODS 判定，GET 导出可能被识别为 view。 | export 判断移到 SAFE_METHODS 之前；补充 GET 导出只认 export 的 API 回归。 |
| C-02 | P1 · 已修复 | RBAC 下未映射 API 默认为 authenticated-only。 | 未映射入口 fail closed；公开入口须显式声明；新增未映射 API 回归。 |
| C-03 | P1 · 已修复 | 报表部分 source 和 Dashboard 混用模块，可能经统计、嵌套订单或导出读到未授权模块数据。 | 来源模块权限、数据范围、Dashboard 统计和 CSV 查询统一按各自来源执行。 |
| C-04 | P1 · 已修复 | 操作日志只校验实体模块，未过滤客户数据范围；原始快照可能包含跨模块关联。 | 日志对象按实体归属和客户范围查询；关联快照按销售、财务、供应商及 SKU 权限脱敏。 |
| C-05 | P1 · 已修复 / 部署待确认 | Django 开发静态 `/media/` 路由可绕过 API 权限；附件及历史报价/SKU 图片含客户或业务文件。 | 移除静态直链，文件由认证 API 按记录模块和客户范围返回；生产外部存储 ACL 见 C-08。 |
| C-06 | P1 · 已修复 | 共享库存流水可直接提交不在范围内的 `order_id/related_orders`；SKU/库存嵌套也需复查模块字段。 | 创建/修改/冲销校验关联订单权限及数据范围；库存、采购、发货嵌套按来源模块脱敏。 |
| C-07 | P1 · 已修复 | 财务/订单/SKU Context 和序列化器存在不带 request/user 的调用；汇总或成本字段可能绕过关联模块权限。 | Context、动作序列化和搜索都使用服务端身份；财务汇总及跨模块字段按模块权限和数据范围过滤。 |
| C-08 | BLOCKED · 运维决策 | 生产对象存储/CDN/Nginx ACL 配置不在仓库内，无法证明外部文件源没有公开直链；历史证书记录可能保留外部 `file_url`。 | 应用 API 层已收口：新证书使用 ERP 私有文件，外部 URL 被拒绝且遗留外部值不再返回；上线前仍须由运维确认存储桶、CDN、反向代理私有策略，并清理/决定历史外部证书链接。 |

## 全站入口盘点

API 路由来自 `backend/crm/urls.py` 的显式 APIView/function view 与 DRF router；逐项审查 ViewSet queryset、serializer、action 和请求权限。B2B 已审查通过的供应商、采购、收货、成本分摊规则在本轮只做回归，不扩大重构。

| 区域 | 当前映射 / 审查重点 | 状态 |
| --- | --- | --- |
| 客户、联系人、跟进 | customers / contacts / followups + 客户范围 | PASS：列表、详情、关联 Context、附件与跨客户写入均走服务端校验。 |
| 报价、订单、合同变更 | quotes / orders + 客户范围；跨模块费用与库存动作 | PASS：报价版本、合同变更及库存/采购/财务派生动作均校验范围和附加模块权限。 |
| 供应商、采购、收货、供应来源 | suppliers / purchases，共享采购；销售关联做双重授权 | PASS：共享采购可见；销售来源、成本分摊、草稿生成和收货关联受订单权限保护。 |
| 库存、发货 | inventory，共享库存；销售发货按关联订单范围 | PASS：共享库存流程保留；销售订单引用及冲销执行附加权限检查。 |
| 财务流水、计划、财务 Dashboard | transactions / finance，销售归属与共享付款分开 | PASS：销售流水受客户范围限制；供应商付款/公共费用共享；分配、核销、作废检查关联权限。 |
| 报表、Dashboard、CSV | reports/dashboard + 来源模块及来源范围 | PASS：总额、明细和导出采用相同来源范围；GET 导出须 reports.export。 |
| 导入/预览/执行 | imports；签名预览状态和关联范围 | PASS：预览和执行检查 imports 权限、目标模块权限及关联数据范围。 |
| 文件、日志、Context、Workbench | 父模块、关联模块和数据范围 | PASS：文件 API、操作日志和嵌套数据按所有者权限/范围过滤；部署 ACL 仍 BLOCKED。 |
| 产品/SKU/参数/证书/包装/贸易单位 | 每个 router 资源显式路径映射；库存/供应来源嵌套过滤 | PASS：资源映射明确；搜索字段和跨模块嵌套按模块权限裁剪。 |
| 组织、权限配置、公开会话入口 | 显式组织/权限映射；current-operator 显式 AllowAny | PASS：权限矩阵管理限管理员；current-operator 返回服务端计算的用户矩阵。 |

## 验证结果与限制

- 已运行 Django system check、迁移检查和完整 SQLite 后端回归；最终提交的确切结果以 master CI 为准。
- 前端 CI 包括 Node 单测、detail-drawer Node 检查、Vitest 和生产构建；本轮未修改前端业务行为。
- 使用 Codex 内置浏览器验收供应商列表/详情、采购列表/工作台和无 orders.view 的订单直达访问。临时 UI 测试账号仅有 suppliers.view、purchases.view、skus.view，仍可查看共享供应商/采购；关联销售订单与财务流水/付款统计隐藏，直接打开订单页返回 403。测试后清理临时账号、角色和采购数据。
- 开发身份保持服务端开发超级管理员约定；受限用户行为由临时独立 RBAC UI 进程和后端 API 回归验证。
- PostgreSQL 兼容性由仓库 PostgreSQL 17 CI 服务验证；本地没有 PostgreSQL 服务。
- BLOCKED 仅有生产对象存储/CDN/反向代理 ACL 和历史外部证书链接清理/公开策略，需要运维确认部署配置和业务决定；应用 API 已按所有者权限收口。ISS-017 本轮详细证据见 `docs/uat-evidence/iss-017-private-files/README.md`。
