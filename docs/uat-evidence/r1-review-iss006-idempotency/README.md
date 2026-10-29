# ISS-006 独立审查：幂等与事务安全

审查基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`；审查分支：`codex/r1-review-iss006-idempotency-20261029`
审查范围：收货、发货的请求幂等、数据库事务及锁、库存/收发货流水、审计副作用、迁移与失败边界。只读审查产品实现；本目录是本次唯一新增内容。未修改产品代码、测试脚本或共享台账。

## 结论摘要

**总体：FIX REQUIRED；ISS-006 验收仍为 NEEDS VERIFICATION。** 后端 SQLite 测试覆盖到的基本重放、相同 key 不同 payload、不同 key 的独立合法操作、缺 key 和回滚均通过；但发现两个有直接复现证据的问题，以及一个由代码锁范围和读写顺序支撑、尚待 PostgreSQL 并发实测确认的采购单状态竞争风险。SQLite 结果不能替代 PostgreSQL 锁语义验证。

| 分类 | 审查项 | 结论与依据 |
|---|---|---|
| PASS | 收货/发货相同 key 重放 | 后端 8 项测试中的重放断言通过；一个 key 只生成一组被断言的收货或发货库存副作用，重放返回已存响应及 `Idempotent-Replay: true`。见 `logs/backend-iss006-tests.log`、`logs/isolated-api-probes.log`。 |
| PASS | 相同 key 不同 payload、不同 key 同类业务操作 | 变更数量但复用 key 得 409 且没有第二条收货；不同 key 的两次合法收货及两次部分发货均获准，各自落独立业务记录。这是按请求身份去重，不是对语义相同业务操作全局去重。 |
| PASS | 事务/失败回滚、库存流水 | API 测试覆盖失败收货回滚；隔离 API 探针令多行发货在首行产生暂存副作用后、次行因库存不足失败，最终 Shipment、shipment movement、幂等行、审计行均为 0。 |
| PASS | key 边界、迁移正向保护 | 缺 key 被 400 拒绝；隔离探针验证 key 去首尾空白、128 字符接受、129 字符和控制字符拒绝。新库迁移、从 `0089` 升到当前 leaf、已有用户 sentinel 保留及 `makemigrations --check` 均通过。 |
| FIX REQUIRED | 浏览器存储不可用时重试 key 不稳定 | `frontend/src/utils/fulfillmentIdempotency.js:20-29,39-54`：sessionStorage 方法异常后每次回退新 UUID；存储属性 getter 异常则发生在 `try` 外。Node 探针确认同 payload 两次拿到不同 key，getter 异常直接向上抛。网络超时后服务端成功而浏览器没收到响应时，重试可能成为第二个合法操作。 |
| FIX REQUIRED | 收货/发货审计快照陈旧 | 收货 `views.py:469,488,497` 在事务/服务更新前快照旧 `purchase`；服务锁定并更新另一个 ORM 实例。发货 `views.py:2236,2256,2258` 同样把旧 `order` 传给审计，而服务重载并更新锁定实例。隔离 HTTP 探针均得到成功响应和正确数据库终态，但 audit after 仍是旧状态，`changed_fields=[]`。 |
| FIX REQUIRED | 同采购单不同 SKU 并发收货/冲销的父单状态竞争 | `fulfillment.py:319-334,382-384` 只锁收货明细/相关销售单/SKU，随后基于各自事务可见的 receipt 汇总计算状态并更新未锁定的 PurchaseOrder；不同 SKU 的不同明细可并行。两事务都先算出 `partial` 后依次写父行时，最终状态可能仍是 `partial`，即使所有明细均已收齐。冲销路径 `455-464,496-498` 有同类父状态重算。代码路径明确，尚无 PostgreSQL 动态复现。 |
| FIX REQUIRED | 冲销业务提交与审计不在同一事务 | `views.py:506-527` 调用自身 `@transaction.atomic` 的冲销服务并在服务返回（已提交）后写审计。若审计写入失败，冲销及冲销流水已提交而请求失败；重试会因已冲销被拒。服务用 `reversal_inventory_movement_id` 阻止第二次冲销副作用，但没有响应重放的幂等 key。 |
| BLOCKED | PostgreSQL 锁及并发回归 | 专用 Django 测试在 SQLite 明确 skip（1 项）。本轮未连接 PostgreSQL，因此相同 key 竞争、不同 SKU 收货/冲销竞争、死锁/隔离级别行为未动态验证。 |
| BLOCKED | 前端 Vitest | 默认 npm 缓存下在启动前遭 `EPERM`，工作树又无本地 `node_modules`/Vitest；改用系统临时缓存重试仍停在依赖解析/网络等待，约 40 秒无输出后中止，未进入测试收集。原错误摘要及重试结果见 `logs/frontend-vitest-blocked.log`。 |
| NEEDS VERIFICATION | 浏览器实际网络失败/刷新场景、冲销接口响应语义、迁移回滚策略 | 本轮没有 Chrome 端到端执行；回滚 `0090` 会撤销新建幂等表，历史 key 随之消失。需在明确的 PostgreSQL/浏览器与数据库回滚演练环境验收。 |

## 实现与证据索引

### 后端幂等协议

- `backend/crm/services/fulfillment.py:48-82` 校验并规范请求 key、规范化 payload 后使用 SHA-256 摘要；摘要绑定 operation、target、operator 和 payload。
- `backend/crm/models.py:104-133` 的 `FulfillmentIdempotency.key` 全局唯一；`operator` 使用 `PROTECT`。`begin_fulfillment_idempotency` 在嵌套 `atomic()` savepoint 中插入，捕获唯一约束冲突后锁定已有记录：摘要不同返回冲突、已成功返回原响应、处理中返回冲突。完成状态和响应写回同一业务事务。
- key 是全局唯一而非按 endpoint 局部唯一；同一个 key 跨 operator、操作或 target 复用均冲突。不同 key 表示不同命令，服务允许多个合法收货/部分发货，因此不能防止前端在存储不可用时换 key 重试。
- 失败的业务校验在外层原子事务中回滚幂等行，测试证明失败收货可用同一 key 修正 payload 后重新提交；这意味着失败响应不被缓存。

### 收货、发货、流水与锁

- 收货 `backend/crm/services/fulfillment.py:317-386` 在服务原子事务内锁 PurchaseOrderItem、相关销售单（按 pk 排序）及 SKU，再创建 `GoodsReceipt` 和 `InventoryMovement`、重算采购单状态并重平衡预留。审查发现父 PurchaseOrder 未锁，状态是跨明细汇总，形成上表的并发风险。
- 发货 `fulfillment.py:567-679` 锁订单、按 pk 排序锁该订单 SKU，再逐条锁 OrderItem；同一事务写 Shipment、ShipmentItem、销售出库流水、超发补充明细/应收计划（适用时）、预留和订单状态。隔离多行部分失败探针验证这些数据库副作用回滚。
- 收货/发货视图把 `begin`、服务操作、audit row、`complete` 包在同一外层 `transaction.atomic()`，因此正常 DB 事务下 audit/idempotency 与核心数据库写入一同提交或回滚。发货/收货 audit 的**快照内容**仍有旧实例问题；“同事务”并不保证快照正确。
- 冲销服务自身原子且会写调整出库流水并将原收货标记为已冲销；视图的 audit 在该原子服务之外。二次冲销会 400，而不是重放先前成功响应。

### 测试、迁移及日志

- `backend/crm/tests/test_iss006_idempotency.py:73-173` 有 7 个 API 场景：收货重放、同 key 改 payload、不同 key 收货、失败收货、发货重放、不同 key 部分发货、缺 key。审计测试只断言数量，不比较 before/after 状态。
- `test_iss006_idempotency.py:176-215` 有 PostgreSQL 专属相同 key 并发发货测试；当前 SQLite 下测试跳过。该测试仅覆盖相同 key 发货，不覆盖不同 SKU 的同采购单收货/冲销竞争。
- `backend/crm/migrations/0090_fulfillment_idempotency.py:6-45` 只 CreateModel、新表、唯一 key 和索引；没有改写/删除既有业务表数据的 data migration。隔离迁移演练保留迁移前用户 sentinel。反向迁移会删除幂等表，回滚后的历史重放保护不保留；生产回滚与保留政策未验证。
- 运行日志：`logs/backend-iss006-tests.log`、`logs/migration-check.log`、`logs/isolated-api-probes.log`、`logs/frontend-storage-probe.log`、`logs/frontend-vitest-blocked.log`。所有 Django 测试/探针使用独立临时 SQLite 与 MEDIA_ROOT；没有连接真实业务数据库。Node helper 探针不访问网络/数据库。

## SQLite 与 PostgreSQL 的边界

Django 文档明确说明 `select_for_update()` 在 SQLite 上不产生行锁；PostgreSQL 提供事务持有的行级锁。因此，本轮 SQLite 测试只能证明 SQLite 的基本约束/事务/业务路径，不能证明生产 PostgreSQL 的锁序列化、唯一冲突等待或竞争行为。官方资料：[Django `select_for_update()`](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update)、[PostgreSQL 显式锁定](https://www.postgresql.org/docs/17/explicit-locking.html)、[SQLite 隔离](https://www.sqlite.org/isolation.html) 与 [SQLite 事务](https://www.sqlite.org/lang_transaction.html)。

## 修复/验收建议

1. 前端将 `window.sessionStorage` 属性访问也纳入异常处理，并为当前页面的 pending 操作保留稳定 key；若无法持久化/保留请求身份，应明确阻止会导致重复写入的盲重试。增加 getter 抛错、get/set 抛错、响应丢失后重试用例。
2. 收货/发货审计从同一事务中锁定/重载的权威对象构造 before/after；为最终收齐的收货与最终发货断言 audit 状态转移及 `changed_fields`，不能仅断言审计行数。
3. 收货/冲销统一锁定父 PurchaseOrder（定义固定锁序，避免与 SKU/关联订单形成反向等待）后再写明细/库存并重新汇总状态；在 PostgreSQL `TransactionTestCase` 并发测试不同 SKU 的多明细收货，以及收货与冲销交叉竞争，验证终态、流水、库存、预留和审计一致。
4. 冲销的业务写入与审计写入放在同一个外层原子事务；确定冲销 endpoint 是否也需请求 key/成功响应重放，并测试“服务成功后审计写失败”的恢复语义。
5. 在 PostgreSQL CI/可控测试库跑专用并发用例及上述新增竞争场景；在真实 Chrome 验证存储受限、网络响应丢失、重复提交。另单独演练回滚 `0090` 对幂等历史的影响。

## 环境与限制

- 工作树：`C:\Users\Johnson\.codex\worktrees\r1-review-iss006\森爵照明管理系统`；审查开始 HEAD 为指定基线，分支为本报告所列独立分支。
- 数据库：测试运行配置为临时 SQLite；Django 测试 runner 使用自己的隔离测试库。媒体目录为同一临时根下 `media`。迁移演练另用独立临时 SQLite/MEDIA_ROOT。
- 未读取、写入或连接真实业务数据库；未修改产品实现、测试脚本或共享项目台账；未推送、开 PR、触发 Actions、切换 master 或部署。
- 受限项：PostgreSQL/Chrome 未执行；前端测试既无本地 Vitest，也无法在默认/临时 npm 缓存路径完成依赖解析。审查结论不将这些标为通过。
