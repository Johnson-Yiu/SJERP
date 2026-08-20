# 报价版本树与修订说明 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让报价修订保存真实父版本和修改说明，并在工作台以树状结构和可返回导航呈现。

**Architecture:** 在 Quote 上增加直接父版本及说明，继续以 root_quote 聚合链级数据；修订接口在服务端固定父节点。工作台返回平坦版本集合，前端根据 parent_quote 构建树和详情返回栈。

**Tech Stack:** Django/DRF、SQLite/Django migrations、Vue 3、Vite。

**Spec:** `docs/superpowers/specs/2026-08-19-quotation-version-tree-design.md`

## Global Constraints

- 报价编号继续使用 `SJYYYYMMDDCCNNN-n`，不因分支改变。
- 历史报价、PI、Excel、订单与重要备注必须保持可用。
- 新修订必须提供非空的中文或英文修改说明。

---

### Task 1: 后端版本关系与修订说明

**Files:**
- Modify: `backend/crm/models.py`, `backend/crm/serializers.py`, `backend/crm/views.py`
- Create: `backend/crm/migrations/0014_quote_parent_and_revision_summary.py`
- Test: `backend/crm/tests/test_quotes.py`

- [ ] 写失败测试：空 `revision_summary` 的 `/revise/` 返回 400；从 `-1` 修订创建 `-3` 时 `parent_quote=-1`。
- [ ] 运行 `py manage.py test crm.tests.test_quotes.QuoteApiTests`，确认新增断言失败。
- [ ] 增加字段、迁移历史父节点、修订校验与工作台序列化字段。
- [ ] 重跑同一测试并确认通过。
- [ ] 提交后端改动。

### Task 2: 编辑器与版本树界面

**Files:**
- Modify: `frontend/src/components/QuoteEditorModal.vue`, `frontend/src/components/QuoteDetailModal.vue`, `frontend/src/components/EntityDetailModal.vue`
- Modify: `frontend/src/components/QuoteDetailModal.manual-test.md`

- [ ] 先更新人工验收清单，加入修改说明、树状分支、详情返回和显眼返回/关闭控件。
- [ ] 修订编辑器传递必填 `revision_summary`；原始新建不显示该字段。
- [ ] 将工作台版本列表转换为父子树，显示说明并保留 PI 预览、详情切换。
- [ ] 用版本栈实现“返回上一版本”，并统一详情导航样式。
- [ ] 运行 `npm run build`；在 5228 报价页验证不保存的浏览流程。
- [ ] 提交前端改动。

### Task 3: 端到端验证

**Files:**
- Modify: `README.md`（如已有报价说明，补充树状版本与修改说明）

- [ ] 运行 `py manage.py test` 和 `npm run build`。
- [ ] 运行 `py manage.py check`、`py manage.py makemigrations --check --dry-run`、`git diff --check`。
- [ ] 审核迁移对既有报价、订单、备注和导出的兼容性。
- [ ] 提交验证文档更新。
