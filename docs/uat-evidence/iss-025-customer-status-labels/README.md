# ISS-025 客户生命周期中文名称一致性验收

日期：2026-10-27  
统一基线：`7951ecb8c6196f773128ad5978bfcd0a5b30c6b5`  
分支：`codex/iss-025-customer-status-labels`  
代码提交：`a8dd277609d7364d301d1a330f717f00962d8619`

## 结论

基线问题仍可复现：客户列表已有 `contact -> 已联系` 的展示辅助逻辑，但客户详情使用模型原始展示名“联系人”，返单客户也存在“公司客户”与“返单客户”的展示差异。本轮采用展示层最小修复：统一客户生命周期展示映射，并为客户 API 提供 `status_display`；数据库中的状态代码和原有状态选项未改动。

未修改数据库状态枚举、自动状态推进、联系人数量与生命周期的关系、历史跟进/报价资料或筛选 URL 参数。旧客户仍返回原始 `status`，筛选和 URL 恢复机制保持不变。

## 自动化验收

- `python manage.py test crm --keepdb`：952 passed，15 skipped，OK。
- 最终改动后的定向后端测试：92 passed，OK，覆盖状态代码不变、客户 API、客户列表上下文、客户详情及联系人关联企业展示。
- `python manage.py makemigrations --check --dry-run`：`No changes detected`。
- `npm run test:unit`：154 passed，0 failed。
- `npx vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：659 passed，0 failed。
- `npm run build`：通过；仅保留既有 chunk size warning。

## Chrome Use 回归

使用真实 Chrome Use 完成桌面和 390×844 窄屏检查，使用隔离 SQLite 样本库，不连接生产数据库。覆盖：

- `/customers?status=contact`：筛选值、表格状态及详情徽章均显示“已联系”。
- 客户详情中的联系人实体仍显示为“联系人”，没有把生命周期状态误作联系人实体。
- 联系人详情的关联企业状态显示“已联系”。
- `/follow-ups?customer=1`：客户筛选、列表与刷新后的 URL 状态保持。
- `/reports?source=sales&group_by=customer&filter_customer=1`：报表筛选可用，未改变报表统计逻辑。

截图证据：

- [桌面客户列表](screenshots/desktop-customer-list.png)
- [桌面客户详情](screenshots/desktop-customer-detail.png)
- [390px 窄屏客户列表](screenshots/mobile-390-customer-list.png)

## 变更边界与遗留事项

- 变更文件：`backend/crm/customer_status.py`、`backend/crm/serializers.py`、`backend/crm/context.py`、`backend/crm/tests/test_issue_025_status_labels.py`、`frontend/src/views/ResourcePage.vue`、`frontend/src/views/ResourcePage.test.js`。
- 未新增迁移；未批量改写历史客户数据；未改变报价、订单或跟进事实推动状态的逻辑。
- 真实生产数据库、真实员工账号和全量业务数据抽查尚未执行，保留为 `BUSINESS_VERIFICATION_PENDING` / `DEPLOYMENT_VERIFICATION_PENDING`，不阻断本地代码验收。
- 本分支未合并 master，未关闭 Issue，等待独立代码、业务、权限和视觉复审。
