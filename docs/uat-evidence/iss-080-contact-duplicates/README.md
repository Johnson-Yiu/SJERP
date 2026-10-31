# ISS-080 客户联系人疑似重复提醒

## 交付信息

- 分支：`codex/iss-080-contact-duplicates`
- 基线：`8b2b5c19e517addd9604b239211e199a789b739e`
- 实现提交：`efb2546b69ae4ace60715dcb97803145248d3a1b`
- 规则来源：用户 2026-10-24 规则包 `ISS-080_同一客户全量联系人疑似重复提醒.md`
- 相邻规则：复核 ISS-025、ISS-027、ISS-029；未改动其历史跟进、权限或报价快照规则。

## 实现与边界

- 新建/编辑联系人选择客户后，通过现有客户授权接口 `/contacts/?customer=<id>` 分页拉取该客户全部联系人，不使用当前列表的搜索、筛选或分页结果。
- 同一客户内按邮箱、保留国际区号的电话标准化，以及相同/明显相近姓名生成疑似匹配；编辑时排除当前联系人自身。
- 提示包含匹配原因和“查看联系人”入口；提醒为非阻断，允许人工继续创建。
- 复用既有服务端数据范围查询，未新增跨客户接口、迁移、联系人合并或历史报价/跟进写回。

## 自动化验收

- `python manage.py test crm.tests.test_issue_080_contact_duplicates --verbosity 2`：2 项通过。
- `python manage.py test crm --verbosity 0`：942 项通过，跳过 14 项；托管 Worktree 的默认 `backend/media` 目录 ACL 不可写，完整回归使用临时 `MEDIA_ROOT`，不改变应用代码。
- `npx vitest run tests/crm-list.vitest.js`：5 项通过。
- `npx vitest run tests/crm-saving.spec.js tests/inventory-ledger.spec.js tests/phase2c-editors.spec.js`：40 项通过。
- `npx vitest run tests --environment jsdom`：67 个有效测试文件、658 项通过；`tests/detail-drawer-typography.spec.js` 是既有无 Vitest suite 的 node:test 文件，未计入有效套件。
- `npm run test:unit -- src/api.test.js src/views/ResourcePage.test.js`：16 项通过。
- `npm run build`：通过；仅有既有大 chunk 提示。
- `npx playwright test browser-tests/crm-ux.spec.js --output <临时目录>`：11/11 通过，覆盖联系人筛选、客户全量联系人、邮箱/电话/姓名、编辑排除自身、继续保存及 390px 布局。
- `python manage.py check`、`python manage.py makemigrations --check --dry-run`：通过，无新增迁移。
- 失败路径日志中的 Bad Request/Forbidden/Internal Server Error 为既有负向回归断言；完整套件最终结果为 OK。

## Chrome Use 证据

使用真实 Chrome Use 在隔离 SQLite 数据库和开发身份下验证：

1. 桌面视口：新建联系人输入 `Lin Yu`，页面显示疑似重复、姓名原因和“查看联系人”，随后仍可保存，列表计数由 2 增至 3。
2. `390×844`：在搜索筛选结果为空时新建联系人，仍显示该客户全量联系人匹配和两个查看入口；表单、提醒、按钮均在窄屏可用。
3. 视觉截图已在本任务 Chrome Use 验收记录中保留；临时视口已恢复默认，未保留用户浏览器状态修改。

真实生产账号、生产数据库及跨员工真实业务数据未在本轮连接，生产/业务数据抽查仍需独立复审。

## 状态

ISS-080 更新为 `FIXED_PENDING_REVIEW`，等待独立代码、权限和视觉复审；不关闭 Issue、不合并 master、不修改其他工作树。
