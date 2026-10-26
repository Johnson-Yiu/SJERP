# ISS-023 Sales Model 自动生成与人工设置验收

日期：2026-10-26  
基线：`f12b591cb90d6a5d8ebfedf1c559703377c92d84`  
分支：`codex/iss-023-sales-model`  
Worktree：独立托管 Worktree `C:\Users\Johnson\.codex\worktrees\iss-023-sales-model\森爵照明管理系统`

## 规则与现状审查

已读取用户 2026-10-24 规则包中的 ISS-023 原文，并核对 ISS-087、ISS-035、ISS-020、ISS-037 的现有实现。现有 SKU、报价快照、PI/XLSX 导出、身份冲突检查和权限入口已覆盖大部分规则，本轮没有重建型号生成器、报价快照或实际 SKU 录入流程，也没有批量重命名旧 SKU。

确认的真实缺口是：编辑 SKU 参数时，前端把新规则预览直接作为 `sales_model` 提交，后端又无条件用新预览覆盖保存值；这会覆盖人工型号，也会让“保存型号”和“新规则预览”混淆。

## 本轮最小修补

- `backend/crm/serializers.py`：参数身份变更时，仅当当前保存型号仍等于旧参数的自动生成值，才刷新到新生成值；人工型号不被自动逻辑覆盖；明确空值仍可作为历史 SKU 的空型号。
- `backend/crm/tests/test_sku_commercial_identity.py`：增加自动型号随参数变化刷新、人工型号改写后版本快照保留的回归。
- `frontend/src/views/SKUPage.vue`：提交保存的 Sales Model，并在身份确认/组合预览中继续区分当前保存型号和基于当前参数的预览。
- `frontend/src/views/SKUPage.test.js`：覆盖前端参数编辑提交保存型号的行为。

报价使用保存时的 SKU/型号快照，PI/XLSX 导出继续使用既有保存版本 DTO；缺少型号时保留 SKU Code、产品名称和描述，不改报价编号、修订链或正式单据历史快照。

## Chrome Use 证据

使用独立后端 `127.0.0.1:8102`、Vite `127.0.0.1:5192` 和隔离 SQLite 数据库进行真实 Chrome 验收：

- 桌面：打开历史空型号 `CHROME-SKU`，人工设置 `CUSTOM-CHROME`，确认身份更新后列表显示该型号；再编辑普通中文描述，型号仍保持 `CUSTOM-CHROME`。
- 窄屏：`390×844` 下导航收起、指标卡、筛选区和 SKU 列表均可见且可用；视口已在验收后恢复默认。
- 控制台错误：无 `error` 或 `warning` 日志。

截图：

- [桌面 SKU 列表](screenshots/desktop-sku-list.png)
- [390×844 窄屏 SKU 列表](screenshots/narrow-390x844-sku-list.png)

## 边界与遗留

- Chrome 使用开发身份 `Johnson`，符合 `AGENTS.md` 的开发超级管理员约定；未冒充正式员工账号，也未改变正式 RBAC。
- 真实生产 SKU 主数据的完整性仍需业务负责人按实际产品前缀/参数抽查；本轮不自动填充或批量重命名旧 SKU。
- 未连接生产数据库、未创建生产密钥或生产账号；真实部署、正式账号及生产数据验收不在本轮范围。
- 未新增数据库迁移；未修改 ISS-035、ISS-020、ISS-037 的历史快照规则，也未改变财务数据。
- 本轮不合并 `master`、不关闭 Issue，完成后等待独立审查。

