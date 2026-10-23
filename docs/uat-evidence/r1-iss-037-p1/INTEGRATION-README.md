# ISS-037 集成兼容性验收

日期：2026-10-24
基线：`54925e0a10a48c16ba3b66bbab9e433f48a0e2d7`
分支：`codex/next-iss-037-integration`

## 结论摘要

ISS-037 的主体快照实现已安全接入当前基线。报价/PI既有买方主体和 SKU 行级快照继续保留；正式销售订单在确认时保存客户六项主体字段；正式采购单在下单时保存供应商五项主体字段。修改客户/供应商主档后，历史单据仍显示原快照，当前主档仅作为明确的参考；旧数据没有快照时显示“历史主体未记录”，不以最新主档冒充历史。

本轮没有确认新的业务显示缺陷。集成过程中确认并修复了一个真实迁移兼容问题：旧分支的 `0078_formal_party_snapshots` 与当前基线的 `0078_historical_contract_scope`、`0079_shared_report_template` 同号；直接并列后从最新状态回退会重复删除快照字段。最终使用 `0080_formal_party_snapshots` 依赖 `0079_shared_report_template`，没有改写或删除任何已发布迁移。

## 迁移与后端证据

最终迁移顺序：

```text
crm.0077_rmb_cash_events
  -> crm.0078_historical_contract_scope
  -> crm.0079_shared_report_template
  -> crm.0080_formal_party_snapshots
```

命令结果：

```text
python manage.py makemigrations crm --check --dry-run
No changes detected in app 'crm'

python manage.py migrate --noinput
crm.0078_historical_contract_scope ... OK
crm.0079_shared_report_template ... OK
crm.0080_formal_party_snapshots ... OK

python manage.py test crm.tests.test_formal_party_snapshots crm.tests.test_cash_events.CashMigrationTests.test_additive_migration_preserves_historical_rows_and_decimal_fields
Ran 6 tests ... OK
P2A_MIGRATION_VERIFICATION {"vendor":"sqlite","all_legacy_rows_equal":true,"old_amount":"12.3401","old_rmb":"87.9034","old_allocated":"0.0001","new_bank_facts":0}
```

完整后端套件在隔离可写 `MEDIA_ROOT` 下通过：`Ran 821 tests in 363.719s`，`OK (skipped=13)`，system check 无问题。首次直接运行仅因当前 worktree 的 `backend/media/follow-up-attachments` 被 Windows 拒绝写入而报 1 个环境错误；未把该次结果记为通过，也未修改生产代码绕过它。

## API 与业务流程核对

隔离 SQLite 数据库使用客户/供应商改名前快照，随后修改主档名称和地址：

| 单据 | API 当前主档 | API 历史快照 | 状态/结果 |
|---|---|---|---|
| `QT-2026-001` | `ISS037 Buyer After Rename` | `ISS037 Buyer Before Rename` | `status_display=已接受` |
| `SO-2026-001` | `ISS037 Customer After Rename` | `ISS037 Customer Before Rename` | `status_display=已完成`；地址、联系人、电话、邮箱均为原值 |
| `PO-ISS037-001` | `ISS037 Supplier After Rename` | `ISS037 Supplier Before Rename` | `status_display=已下单`；地址、联系人、电话、邮箱均为原值 |

另外核对：

- 报价 `buyer_company_name`、`recipient_name`、买方地址/电话/邮箱和 PI 导出继续来自报价保存值。
- 正式订单/采购单快照字段为只读；匿名无客户/供应商查看权限时，当前主体和快照均被脱敏。
- 草稿仍可使用当前主档；正式确认/下单由既有 lifecycle 服务原子写入快照；旧正式单据空快照保持未知。
- 生命周期状态、数量、金额、SKU/交易单位快照及修订记录未改变。

## 前端自动化与构建

最终结果：

```text
npm run test:unit
149 passed, 0 failed

npx vitest run [62 个前端 spec + tests/crm-list.vitest.js] --environment jsdom --configLoader runner
Test Files 63 passed (63)
Tests 619 passed (619)

npx vite build --configLoader runner --outDir <isolated-writable-output>
✓ built; 2009 modules transformed
```

Vitest 首轮发现 3 个旧采购测试夹具只提供当前 `supplier_name`、没有正式 `supplier_name_snapshot`；在不改变业务逻辑的前提下补齐历史夹具后，整批通过。默认 `frontend/dist` 构建目录同样受 worktree Windows 权限限制，因此最终构建输出使用隔离可写目录；构建内容和模块转换均成功。

## 真实 Chrome 回归

在当前集成分支启动隔离 SQLite 后端和 Vite 前端，人工核对了：

- `/quotes`：列表显示 `ISS037 Buyer Before Rename`，并标注当前主档 `ISS037 Buyer After Rename`；详情显示历史主体和 PI/Excel 导出入口。
- `/orders?detail=1`：订单列表及详情显示 `ISS037 Customer Before Rename`，详情主体快照中的国家/地区、地址、联系人、电话和邮箱保持原值，并单独显示当前主档参考。
- `/purchase-orders?detail=1`：列表和详情显示 `ISS037 Supplier Before Rename`，采购状态显示“已下单”，状态筛选选项显示中文；详情显示供应商五项历史资料和当前主档参考。

保留的真实 Chrome 图片证据：

- [报价列表](quote-list-live.png)
- [报价详情](quote-detail-live.png)
- [销售订单详情](browser-order-detail-snapshot.png)
- [采购单列表](browser-purchase-list.png)
- [采购单详情](../r1-iss-037-p1-fix-01/purchase-detail-history-live.png)
- [缺失历史快照提示](../r1-iss-037-p1-fix-01/missing-history-live.png)

PI 导出样本：

- [原分支保留的 PI Excel 样本](../r1-iss-037-p1-fix-01/SJ20261021DE998-browser-export.xlsx)
- 本轮隔离 API 导出 HTTP 200，生成 10,186 字节的 `PI` 工作表；Buyer Name 为 `ISS037 Buyer Before Rename`，地址、邮箱、电话均为历史值。

## 缺陷分类与范围控制

- 已确认缺陷：同号迁移直接整合会破坏迁移回退顺序；已修复为 `0080_formal_party_snapshots`。
- 已修复缺陷：旧分支中报价/采购历史主体的部分展示入口遗漏；实现已随 `codex/r1-iss-037-p1` 及 FIX-01 保留并通过本轮 API/Chrome 核对。
- 历史误报：本轮没有复现“当前正式单据直接以最新主档冒充历史主体”；旧报告所述风险对应的是历史快照缺口，不能据此把当前实现误报为仍有缺陷。

本轮未修改 ISS-021 数量变更代码，未修改采购/销售生命周期转换规则，未启用正式 RBAC，未合并 `master`，未关闭 Issue。ISS-037 仍等待统一独立审查。

## 剩余风险

本地 PostgreSQL/CI 精确 HEAD 环境未在本轮伪造通过；当前报告的完整套件证据为隔离 SQLite。历史旧单据没有快照的主体继续按“历史主体未记录”呈现，是否允许业务补证需另行授权；本轮不回填、不推断。
