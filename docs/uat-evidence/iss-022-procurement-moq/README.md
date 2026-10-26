# ISS-022 采购 MOQ 软提醒与共享 PO 合计验收

## 范围与基线

- 项目：SUNJACK-ERP
- 规则来源：`C:\Users\Johnson\Desktop\SUNJACK-ERP_B8E5A1A7E599AEE6B4A7E4A48C%85_2026-10-24\新增议题逐项移交\ISS-022_供应商MOQ软提醒和共享PO合计判定.md`
- 统一基线：`28ba758388429f57c2e3516e12385a88ce6646a3`
- 分支：`codex/iss-022-procurement-moq`
- 本轮 worktree：`C:\Users\Johnson\.codex\worktrees\iss-022-procurement-moq\森爵照明管理系统`
- 验收日期：2026-10-26

## 核实结论

历史代码的真实缺口不是数据库 MOQ 字段或采购状态值，而是两个入口的判定口径不一致：采购计划曾按销售单明细分别提示，多个销售单汇入同一真实 PO 时可能错误提示；正式下单路径没有按 PO 合计给出可留痕的软提醒。该缺口已按用户明确规则补修。

已修复：

1. 草稿采购计划和编辑页按同一供应商来源、同一真实采购单、基础单位合计后判断 MOQ；没有可靠 MOQ（来源缺失、MOQ 为 0）不产生阈值。
2. 采购单位换算后再比较基础数量，不自动补量、不创建虚假数量。
3. 低于 MOQ 仍可保存草稿；正式下单首次返回 `purchase_moq_exception_required`，用户填写原因后继续下单。
4. 例外以采购单一对一记录保存原因、MOQ 明细快照、采购单、时间和已认证操作员；详情/API 按既有查看权限脱敏。
5. 采购价格与 SupplierSKU 内部参考成本保持不变；状态转换和采购生命周期未重构。

历史台账中的 BLOCKED 原因是 MOQ 政策尚未确认。本轮规则已由用户明确，因此该历史阻塞被重新核实为实现缺口并进入 `FIXED_PENDING_REVIEW`；不代表 Issue 已关闭。

## 场景证据

| 场景 | 结果 | 证据 |
|---|---|---|
| 低于 MOQ | 9.00 pcs < 10.00 pcs，显示风险，草稿仍保留 | `04-low-moq-conversion-warning.png`、`06-cancel-keeps-draft.png` |
| 等于 MOQ | 10.00 pcs = 10.00 pcs，可直接保存并下单 | `01-equal-moq-draft.png`、`02-equal-moq-detail.png`、`03-equal-moq-ordered.png` |
| 高于 MOQ | 后端专项测试确认可直接下单 | `backend/crm/tests/test_purchase_moq.py` |
| 两张销售单合计到同一来源 | 采购计划先按 SupplierSKU 聚合后判断，不逐销售单误报 | `test_purchase_moq.py` 的计划合计测试 |
| 不同采购单位 | 交易单位按转换因子换成基础单位后比较 | `04-low-moq-conversion-warning.png`、专项后端测试 |
| 无 MOQ 资料 | 不凭空设阈值、不拦截 | 专项后端测试 |
| 越过提示与审计 | 取消原因弹窗保持草稿；填写原因后下单，详情保留原因、时间和明细快照 | `05-low-moq-exception-dialog.png`、`07-moq-exception-persisted.png`、`browser-log.json` |
| 状态筛选 | 下单后 `status=ordered` 查询返回 2 张采购单 | `08-ordered-filter.png`、`browser-log.json` |
| 窄屏布局 | 700px 页面无横向溢出 | `09-narrow-purchase-list.png`、`browser-log.json` |

浏览器流使用开发超级管理员环境；依据 `AGENTS.md`，开发身份不是正式审计人，因此该真实浏览器流的 `operator_id` 可为空。已认证 API 测试另外验证操作员、时间、采购单和原因均持久化，未伪造开发操作人。

## API 与数据库证据

- `browser-log.json` 保留真实 Chrome 网络记录：低 MOQ 首次下单返回 400、填写原因后同一采购单返回 200；等于 MOQ 直接返回 200。
- `fixture.json` 保留隔离场景的 SupplierSKU MOQ、交易单位和换算因子。
- 新迁移为 `backend/crm/migrations/0086_purchase_moq_exception.py`，接续当前 `0085_order_quantity_adjustment`，未复制、删除或重写已发布迁移。
- 原英文数据库状态值仍然使用，中文只用于页面提示、例外摘要和详情说明。

## 测试记录

通过的定向后端测试：

```text
crm.tests.test_purchase_moq crm.tests.test_procurement
crm.tests.test_supplier_sku.SupplierSKUApiTests.test_new_purchase_rejects_inactive_source_but_formal_history_remains_idempotent
Ran 27 tests ... OK
```

此前更宽的采购相关组合（含 purchase safety、purchase costs、trade units）也已通过 53 项；最终提交内容再由下方 Django 全量 918 项覆盖。

前端与浏览器：

```text
node --test src/views/PurchaseOrderPage.test.js        13 passed
npm run test:unit                                      153 passed
Vitest (tests, excluding repository detail-drawer test) 67 files / 656 tests passed
npm run build                                          success
Playwright / real Chrome                               1 passed
```

后端全量：

```text
python manage.py test crm                              917 tests, OK (skipped=13)
python manage.py check                                  no issues (0 silenced)
fresh SQLite migrate --noinput                          all migrations through crm.0086 OK
fresh SQLite migrate --check                            no pending migrations
```

生产构建仅有既有大 chunk 警告，无构建失败。第一次全量运行曾被 worktree `backend/media` 的 Windows 写权限阻断；将 `MEDIA_ROOT` 指向可写隔离目录后重跑，917 项全部通过。该环境修复不改变仓库代码。

## 限制与复审

- 本轮没有进入生产 PostgreSQL、生产代理/CDN 或正式 RBAC 账号验收；开发环境权限不等同于生产安全验收。
- 不自动合并 master，不自行关闭 Issue。
- 本证据目录、测试日志和截图必须与本分支最终提交 SHA 一起审查。
