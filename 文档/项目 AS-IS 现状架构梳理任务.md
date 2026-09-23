# 项目 AS-IS 现状架构梳理任务

请你以“资深软件架构师 + 代码审计工程师”的角色，对当前整个项目进行一次完整的 AS-IS（当前现状）分析。

## 一、任务目标

这一次任务的核心目的不是修改、重构或优化项目，而是：

**完整理解当前项目实际上是如何运行的，并把当前代码、数据库、模块、页面、接口和业务流程之间的关系整理成一套可以人工审核和编辑的项目说明资料。**

我后续会根据这些资料，结合我真正想实现的业务逻辑，对系统架构和业务流程进行人工调整，再让你按照调整后的 TO-BE 设计修改代码。

因此，本阶段必须严格区分：

- AS-IS：代码目前真实存在的结构和逻辑
- TO-BE：未来希望修改成的目标结构

本阶段只处理 AS-IS。

不要把你认为“更合理”的设计写成当前系统事实。

---

# 二、重要原则

## 1. 不修改代码

本次任务默认：

- 不修改业务代码
- 不修改数据库
- 不修改 API
- 不进行重构
- 不删除任何代码
- 不改变现有行为
- 不安装新的业务依赖

如果为了分析必须运行项目、测试、数据库查询或静态分析工具，可以执行，但不要产生业务行为变化。

---

## 2. 以代码为事实来源

不要根据文件名、模块名或者常见 ERP 设计进行猜测。

例如：

不能因为存在 `quotation` 模块，就默认它一定会生成订单。

必须实际追踪：

页面 → API → Service → 数据库 → 下游调用

确认真实代码路径后再写入文档。

无法确认的内容必须明确标记：

`⚠️ 未确认`

不要编造。

---

## 3. 区分“事实”和“推测”

文档中如果出现分析判断，请使用以下标记：

- `[CONFIRMED]`：已经从代码确认
- `[INFERRED]`：根据代码结构合理推测，但没有直接证据
- `[UNCLEAR]`：目前无法确认
- `[RISK]`：发现潜在架构风险
- `[DEAD CODE?]`：疑似废弃代码，但尚未确认

---

# 三、第一步：完整扫描项目

请首先扫描整个 repository，包括但不限于：

- 前端代码
- 后端代码
- 数据库 Schema
- migrations
- ORM models
- API routes
- services
- controllers
- hooks
- utils
- shared libraries
- types/interfaces
- 状态管理
- 权限系统
- 定时任务
- 导入导出逻辑
- Excel/PDF/文件生成逻辑
- 测试代码
- 配置文件
- 环境变量引用
- docs
- scripts
- seed 数据
- 已废弃但仍存在的代码

不要只扫描表面目录。

需要尽量追踪真正的依赖关系。

---

# 四、生成项目总体架构说明

创建：

`docs/as-is/01-system-overview.md`

至少包含：

## 系统基本信息

说明：

- 使用的技术栈
- 前端框架
- 后端框架
- 数据库
- ORM
- 状态管理
- API模式
- 身份认证方式
- 权限模型
- 文件存储方式
- 导出机制
- 主要第三方依赖

## 系统模块列表

按照真实代码结构识别所有主要业务模块。

例如可能包括但不限于：

- CRM
- 客户
- 联系人
- 产品
- Product
- SKU
- 分类
- 报价单
- 销售订单
- 采购
- 库存
- 入库
- 出库
- 包装
- 发货
- 财务
- 用户
- 权限
- OA
- 审批

不要照抄上面的模块，而是根据项目实际情况识别。

每个模块写明：

- 模块名称
- 模块职责
- 主要入口
- 主要页面
- 主要 API
- 主要 Service
- 主要数据库表
- 上游依赖
- 下游依赖

---

# 五、生成模块依赖关系

创建：

`docs/as-is/02-module-dependencies.md`

这是本次任务非常重要的一部分。

需要回答：

> 修改某个模块时，可能影响哪些其他模块？

对于每个核心模块，整理：

### 模块：XXX

依赖：

- 模块A
- 模块B

被以下模块依赖：

- 模块C
- 模块D

共享的数据：

- customer_id
- sku_id
- quotation_id
- ...

共享数据库表：

- xxx
- xxx

调用接口：

- xxx

被调用接口：

- xxx

可能产生的副作用：

- xxx

修改本模块时建议检查：

- 页面
- API
- 数据库
- 导出
- 报价
- 库存
- 财务
- 权限
- 测试
- 等

---

同时生成一张整体：

**模块依赖图**

优先使用 Mermaid：

```mermaid
graph LR
```

必须显示模块之间真实存在的依赖方向。

---

# 六、数据库 ER 图

创建：

`docs/as-is/03-database-er.md`

扫描完整数据库结构。

整理：

- 所有核心表
- Primary Key
- Foreign Key
- Unique Constraint
- 多对多关系
- 一对多关系
- 一对一关系

生成：

```mermaid
erDiagram
```

ER 图。

如果数据库规模较大：

同时提供：

1. 全局 ER 图
2. CRM ER 图
3. Product/SKU ER 图
4. Sales ER 图
5. Procurement ER 图
6. Inventory ER 图
7. Finance ER 图

具体按现有模块决定。

---

# 七、数据库 Data Dictionary

创建：

`docs/as-is/04-data-dictionary.md`

对于核心数据库表整理：

| Table | Field | Type | Nullable | Default | FK | Meaning | Used By |
|---|---|---|---|---|---|---|---|

尤其标明：

- ID字段
- 状态字段
- 金额字段
- SKU字段
- 数量字段
- 时间字段
- 软删除字段
- 版本字段

如果某个字段用途无法从代码确认：

标记：

`[UNCLEAR]`

---

# 八、业务流程图

创建目录：

`docs/as-is/flows/`

识别系统中真正存在的核心业务流程。

例如，如果项目存在这些流程，则分别整理：

- 产品创建
- SKU创建
- 客户创建
- 报价单创建
- 报价单编辑
- 报价单导出
- 报价单 → 销售订单
- 销售订单
- 采购
- 入库
- 出库
- 库存变动
- Packing List
- 发货
- 收款
- 付款
- 财务记账
- 审批

每个流程单独一个 Markdown 文件。

例如：

`flows/quotation-create.md`

必须包括：

### 触发入口

用户从哪里开始。

### 操作步骤

1.
2.
3.

### 数据读取

读取哪些表。

### 数据写入

写入哪些表。

### API调用

调用哪些 API。

### Service

调用哪些业务 Service。

### 副作用

例如：

- 更新库存
- 生成文件
- 创建记录
- 修改状态
- 写日志

### 下游影响

流程完成后哪些模块会受到影响。

最后生成 Mermaid：

```mermaid
flowchart TD
```

---

# 九、页面导航和页面流程

创建：

`docs/as-is/05-page-map.md`

整理系统所有主要页面：

页面：

`/products`

功能：

产品管理

调用：

`GET /api/products`

数据库：

`products`

可以跳转：

- SKU
- Product Detail

权限：

xxx

然后生成：

页面导航图 / Page Flow。

---

# 十、API Map

创建：

`docs/as-is/06-api-map.md`

整理所有主要 API。

格式例如：

| Method | Endpoint | Module | Controller | Service | Tables | Called By |
|---|---|---|---|---|---|---|

重点检查：

- API是否跨模块
- 哪些API修改数据库
- 哪些API具有副作用
- 哪些API同时修改多个表

---

# 十一、数据流图

创建：

`docs/as-is/07-data-flow.md`

从关键业务对象角度追踪数据。

例如：

SKU：

Product
↓
SKU
↓
Quotation
↓
Sales Order
↓
Shipment

但是必须根据实际代码生成。

重点对象：

- Customer
- Product
- SKU
- Quotation
- Sales Order
- Purchase Order
- Inventory
- Shipment
- Payment

生成 Mermaid Data Flow / Flowchart。

---

# 十二、Change Impact Matrix

创建：

`docs/as-is/08-change-impact-matrix.md`

这是以后开发最重要的参考资料之一。

建立矩阵：

| 修改对象 | Product | SKU | Quotation | Sales | Purchase | Inventory | Packing | Finance |
|---|---|---|---|---|---|---|---|---|

例如：

SKU字段变化：

- Product：Medium
- Quotation：High
- Sales：High
- Inventory：High
- Packing：High

但不要凭感觉评分。

必须根据真实代码关系判断。

等级：

- None
- Low
- Medium
- High
- Critical

并解释原因。

---

# 十三、核心对象生命周期

创建：

`docs/as-is/09-entity-lifecycle.md`

分析核心实体状态。

例如：

Quotation：

Draft
↓
Confirmed
↓
Converted
↓
Cancelled

Sales Order：

Draft
↓
Confirmed
↓
Processing
↓
Shipped
↓
Completed

必须完全根据代码中的真实状态生成。

同时检查：

- 状态字段在哪里定义
- 谁可以修改状态
- 什么条件下修改
- 状态改变会触发什么副作用

---

# 十四、跨模块耦合分析

创建：

`docs/as-is/10-coupling-analysis.md`

找出：

### 高耦合模块

例如某个 Service 同时：

- 修改订单
- 修改库存
- 修改财务

### Shared Utils

哪些工具函数被大量模块依赖。

### Shared Types

哪些类型修改后可能大面积影响项目。

### Global State

哪些全局状态影响多个页面。

### Database Coupling

是否多个模块直接操作同一张表。

### Hidden Dependency

例如：

修改 SKU Name

却可能影响：

- quotation export
- order export
- packing list
- search
- UI

将这些隐藏依赖尽可能列出来。

---

# 十五、风险和历史遗留问题

创建：

`docs/as-is/11-architecture-risks.md`

注意：

这里只记录发现，不进行修复。

例如：

- 重复业务逻辑
- 模块边界不清
- 循环依赖
- 数据库字段语义不一致
- 同一状态多套定义
- API直接操作多个模块
- 前端包含业务逻辑
- 后端缺少统一Service
- 废弃代码
- 重复组件
- Magic String
- Magic Number
- 无Foreign Key
- 数据一致性风险
- Transaction缺失
- 删除行为风险

每项注明：

严重程度：

- Low
- Medium
- High
- Critical

以及证据位置。

不要修改。

---

# 十六、生成项目 Mind Map

另外创建：

`docs/as-is/project-map.md`

建立整个系统的树状结构。

例如：

System
├── CRM
│   ├── Customer
│   └── Contact
├── Product
│   ├── Product
│   ├── SKU
│   └── Category
├── Sales
│   ├── Quotation
│   └── Sales Order
└── Inventory

但是结构必须根据真实项目生成。

---

# 十七、生成 XMind 可导入版本

我希望后续人工使用 XMind 修改架构。

因此请额外生成：

`docs/as-is/project-map.opml`

采用标准 OPML 2.0 格式。

内容至少包括：

- 系统
- 模块
- 子模块
- 页面
- 数据库
- API
- 依赖
- 流程

尽量保证可以直接导入 XMind。

同时生成：

`docs/as-is/project-map.md`

作为 Git 可追踪版本。

Markdown 是主版本。

OPML 是可视化编辑版本。

---

# 十八、生成 Architecture Index

创建：

`docs/as-is/README.md`

作为整个 AS-IS 文档入口。

例如：

# AS-IS Architecture

## System

- System Overview
- Module Dependencies
- Database ER
- Data Dictionary

## Business

- Product Flow
- Quotation Flow
- Sales Flow
- Inventory Flow

## Dependency

- API Map
- Data Flow
- Change Impact Matrix

## Architecture

- Coupling Analysis
- Architecture Risks

方便以后 Codex 快速阅读。

---

# 十九、建立“代码证据”

对于关键结论尽可能注明代码位置。

例如：

Quotation → SKU dependency

Evidence:

`src/services/quotation.ts`

`src/models/quotationItem.ts`

不要只给结论。

这样以后可以验证文档是否过期。

---

# 二十、不要自动进行架构优化

这是非常重要的要求。

即使你发现：

- 设计不合理
- 数据库结构不好
- 模块耦合严重
- 命名混乱
- 重复代码很多

也不要自动修改。

只需要写入：

`11-architecture-risks.md`

本阶段目标是：

**准确描述当前系统，而不是把当前系统改成你认为正确的系统。**

---

# 二十一、最终输出一个“系统现状摘要”

完成所有扫描后，再生成：

`docs/as-is/00-executive-summary.md`

使用非程序员也能够理解的语言说明：

1. 当前系统由哪些主要模块组成
2. 每个模块负责什么
3. 模块之间最重要的关系
4. 数据主要如何流动
5. 当前系统最核心的业务流程
6. 哪些模块耦合最严重
7. 修改哪些东西风险最大
8. 当前发现的主要架构问题
9. 哪些区域暂时无法确认

这份文件是给项目负责人阅读的，不要写得过于技术化。

---

# 二十二、执行方式

不要一次凭印象生成所有文档。

按照以下顺序执行：

1. 扫描代码目录
2. 识别技术栈
3. 识别数据库
4. 识别核心模块
5. 追踪模块依赖
6. 追踪核心业务流程
7. 追踪 API
8. 追踪数据库读写
9. 追踪跨模块调用
10. 生成文档
11. 再次交叉验证文档与代码
12. 修正文档中的错误或遗漏

如果项目较大，可以分批分析，但最终必须形成统一结果。

---

# 二十三、最后进行一次一致性审计

生成所有文档以后，再对以下内容进行交叉检查：

- ER图 vs ORM
- API Map vs routes
- Module Dependency vs imports/service calls
- Business Flow vs 实际代码
- Data Dictionary vs schema
- Page Map vs frontend routes
- Change Impact Matrix vs真实依赖

如果发现矛盾：

以实际代码为准并修正文档。

---

## 最终原则

这次工作的核心不是“帮我设计一个更好的系统”。

而是：

> **把当前项目真实存在的架构、业务逻辑、模块关系、数据库关系和数据流完整地还原出来。**

我要先看到系统现在到底长什么样。

等我人工修改这些 AS-IS 文档并形成 TO-BE 设计以后，再进行第二阶段的系统重构。