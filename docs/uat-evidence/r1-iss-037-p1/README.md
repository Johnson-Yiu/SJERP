# R1-ISS-037-P1 正式商业单据主体快照修复证据

状态：`LOCAL PASS / CI PENDING / FIXED_PENDING_REVIEW`

本轮基于 `origin/master` 的 `25405e1b25ff8a218b67883acf489ada8a53e146` 创建分支 `codex/r1-iss-037-p1`。不在审查分支开发，不合并其他未完成分支，不修改已发布迁移或历史正式单据。

## 实际修复范围

| 对象 | 本轮结果 | 历史兼容边界 |
| --- | --- | --- |
| Quote / QuoteItem / PI | 保留既有买方主体快照、报价修订链、SKU行级快照和 PI 导出逻辑；未重写生成器 | 原有快照继续使用；没有快照的历史值不补造 |
| Order | 新增客户名称、国家/地区、地址、联系人姓名、电话、邮箱六项快照；正式确认时原子化固定 | 旧订单新字段为空时显示“历史主体未记录”，不从当前 Customer 回填 |
| PurchaseOrder | 新增供应商名称、地址、联系人、电话、邮箱五项快照；正式下单时原子化固定 | 旧采购单新字段为空时保持未知，不从当前 Supplier 猜测 |
| Supplier | 新增可选地址字段并接入现有资料编辑 | 空地址明确留空，不从备注、链接推断 |
| 历史展示 | 正式 Order/PO 详情和列表优先用交易快照；当前主档仅以“当前主档参考”标注 | 原有关联关系、搜索和统计字段保留 |
| 权限 | 新增快照字段沿用客户/供应商查看权限；无权用户不会因新字段读取主体信息 | 未改变普通客户、供应商和销售订单权限 |

## 自动化测试

以下命令均在本 worktree 执行，退出码均为 `0`：

| 命令 | 结果 |
| --- | --- |
| `python manage.py makemigrations crm --check --dry-run` | `No changes detected` |
| `python manage.py test crm.tests.test_formal_party_snapshots --verbosity 1` | 5/5 通过 |
| `python manage.py test crm.tests.test_contract_lifecycle crm.tests.test_quotes crm.tests.test_procurement crm.tests.test_purchase_order_related_orders --verbosity 1` | 98/98 通过 |
| `python manage.py test crm.tests.test_cash_events.CashMigrationTests.test_additive_migration_preserves_historical_rows_and_decimal_fields --verbosity 1` | 1/1 通过；历史模型比较和最新迁移恢复通过 |
| `python manage.py test`（通过 `override_settings(MEDIA_ROOT=...)` 使用临时可写媒体目录） | 773 项，跳过 13 项，`OK` |
| `npm run test:unit` | 138/138 通过 |
| `npm run build` | Vite 构建成功；仅有既有 chunk 体积提示 |

全量测试中出现的 Bad Request、Forbidden 和故意注入的 Internal Server Error 日志均来自已有负向/事务回滚测试；最终结果为 `OK (skipped=13)`，没有未处理错误。

### 数据库迁移

真实 SQLite 临时数据库完成：

```text
0076_customer_owner_profile -> 0077_rmb_cash_events       PASS
0077_rmb_cash_events       -> 0078_formal_party_snapshots PASS
0078_formal_party_snapshots -> 0077_rmb_cash_events       PASS
0077_rmb_cash_events       -> 0078_formal_party_snapshots PASS
```

历史迁移测试现在通过 `project_state(...).apps` 使用 0076 和 0077 的历史模型比较数据，`finally` 使用迁移图实际 leaf nodes 恢复最新状态；没有读取 0078 字段，也没有修改 0076/0077 文件。测试输出中的历史金额 `12.3401`、人民币金额 `87.9034` 和已分配金额 `0.0001` 保持不变。

本机检查无 PostgreSQL 5432 监听（`NO_POSTGRES_LISTENER_5432`），因此 PostgreSQL 未宣称通过；GitHub Actions 按项目当前额度策略保持 `CI PENDING`。

## 真实 Chrome 证据

使用隔离 SQLite 数据库和开发环境真实 Chrome 操作，验证客户/供应商主档被修改后，正式历史单据仍显示原始交易主体：

- [销售订单列表：历史客户主体及当前主档参考](browser-order-list.png)
- [销售订单详情：交易主体快照](browser-order-detail-snapshot.png)
- [采购订单列表：历史供应商主体及当前主档参考](browser-purchase-list.png)
- [采购订单详情：交易主体快照](browser-purchase-detail-snapshot.png)
- [报价列表：已有报价/PI入口](browser-quote-list.png)
- [实际 PI Excel 导出](SJ20261021DE998-browser-export.xlsx)

实际导出的 `SJ20261021DE998-browser-export.xlsx` 使用 `openpyxl` 检查，工作表为 `PI`，Buyer Name、Recipient、Address、Email、Tel 均为报价保存的历史主体值，没有切换为当前 Customer 主档。

## 迁移整合风险

当前 P1 新增 `0078_formal_party_snapshots`；R1-SKU-01 有 `0078_sku_cost_verification`，R1-MOQ-02 有 `0078_purchase_moq_exceptions`。三条迁移均依赖 `0077_rmb_cash_events`，本分支未合并其他分支，也未重写或删除任何 0078 文件。未来正式整合时，应在集成分支依据各分支的实际最新迁移节点新增 merge migration，同时依赖三条独立 0078 节点；不要把任一功能迁移改成依赖另一条 0078，也不要修改已经执行过的迁移。

## 尚未完成/需要独立复审

- 本机 PostgreSQL 环境不可用，需在可用环境或 GitHub CI 恢复后补跑。
- 没有为历史缺失主体创建人工补证流程；如需补证，需另行确认业务规则和审计方案。
- 真实正式员工 RBAC 未在本轮开启；开发环境权限边界测试已覆盖新字段的生产模式脱敏逻辑，正式员工 UAT仍需单独授权。
- ISS-037 仅更新为 `FIXED_PENDING_REVIEW`，不标记 `CLOSED`，等待 ChatGPT 独立代码、数据和视觉审查。
