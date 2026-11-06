# SUNJACK-ERP FIRST-RELEASE-CONSOLIDATION-02

## 集成范围

- 基线：`b223c052902463b59e149409cf9941503aeab31f`。
- 来源：`945c2ae41ce59d55051bbab4664f3d7a4df0fbba`（原父提交为 `01b6fe73f77c2294a17d1b4e001d8e3afe83e27a`），按补丁接入独立分支 `codex/sunjack-first-release-consolidation-02`。
- 保留基线中的主体版本、历史资料只读预检、文件更换后清除旧预览状态、多标签工作区和账号隔离。没有改动主体/提醒迁移、权限实现或业务字段。
- 将前端导航、财务快捷入口、财务流水说明和路由标题统一为“银行资金记录”。路由仍为 `/rmb-cash-events`，权限仍使用 `transactions:view`；原页面能力不变。
- 销售订单导入留在独立后续集成中。

## 定向验收

### 真实 Chrome 与隔离账号

通过仓库隔离浏览器运行器，在一次性 SQLite、临时媒体目录中创建 `codex` 测试超管并通过登录页认证。浏览器身份为超级管理员，`development_superadmin=false`、`rbac_enforcement=false`；凭据没有写入证据或代码。Chrome 版本 `156.0.8078.80`。

- `first-release-consolidation-02.spec.js`：1/1。财务概览侧栏与快捷入口均显示“银行资金记录”，均到达 `/rmb-cash-events`；窄屏页面无横向溢出。实际 Chrome 页面截图见 `browser/first-release-consolidation-02.spec/`。
- 历史预检使用合成模板经浏览器同源表单提交至 `POST /api/import/history-preflight/?report=csv`；HTTP 200，Chrome 收到并保存 `history-preflight.csv`（553 字节，UTF-8 BOM）。CSV 包含合成来源单号 `COD-SO-SRC-1` 和预检结果，没有上传的历史地址。预检当前只有 API 入口，本次用例在真实 Chrome 中通过临时表单触发下载，没有冒充产品内的预检页面。文件：`browser/first-release-consolidation-02.spec/history-preflight.csv`。
- `quote-editor-mobile-actions.spec.js`：1/1。Chrome 点击“保存并导出 Excel”，报价保存 HTTP 201、导出 HTTP 200；浏览器下载 `SJ20261106DE002.xlsx`，10,198 字节。用 OpenPyXL 检查实际下载文件：PI 工作表范围 `A1:M35`，报价号、型号 `R1-QA-MODEL`、数量 `1`、单价/金额 `12.5` 均存在；无 Unicode 替换字符。SHA-256 为 `273130b6d1b563d00019854a8b2cb46132eb199997caa5de0192114231e77deb`。文件及解析记录见 `browser/quote-editor-mobile-actions.spec/`。资料均为合成验收数据。
- 截图由真实 Chrome 生成并人工检查：财务概览 1440px，银行资金记录 1440px/390px；报价编辑器 1440px/1024px/390px/320px。

### 历史预检、文件更换、标签页和账号隔离

- `crm.tests.test_history_import_preflight`：隔离 SQLite，23/23 通过，覆盖只读预检、权限、输入错误、CSV 输出及无业务副作用。
- Vitest 定向：`import-ux.spec.js` 与 `finance-contract-navigation.spec.js`，jsdom 环境 13/13 通过。包含更换 CSV 后清除旧预览令牌的回归。
- `workspace-tabs-real.spec.js`：按该既有用例依赖的默认隔离开发超管档重跑，6/6 通过；覆盖并行草稿、跨导航状态和列表分页/滚动。
- `workspace-integration-real.spec.js`：隔离受限会话与 RBAC，4/4 通过；覆盖不同账号的工作区上下文与新品提醒隔离。
- 曾用 codex 登录档试跑 `workspace-tabs-real.spec.js`，其中原用例的裸 `APIRequestContext` 创建客户请求缺少 CSRF，1 项返回 403；该用例原本依赖匿名开发超管档。按其原测试档完整重跑后 6/6 通过。该次身份试跑失败是测试请求缺 CSRF，不是应用数据隔离失败。
- 隔离浏览器运行器验证：20/20 通过，包含端口、API/SQLite 身份和并行工作树隔离。

没有运行本地全量或 GitHub Actions。没有对本任务执行 PostgreSQL 测试；本轮目标为浏览器导航、下载及已有回归，均在隔离 SQLite 上完成。

## 真实历史报价限制与建议

沿用 `first-release-integration-01` 的代表性检查结果；本轮没有查询真实历史数据库，也没有用主档覆盖未知值：

- `standard_en_no_discount` 与 `standard_en_with_discount` 常用模板的完整快照可生成 PI/XLSX。
- 历史买方税号为 `NULL` 时，PI 与 XLSX 返回 HTTP 422，数据库中的 `NULL` 保留。当前模板没有买方国家、联系人、账单地址、收货地址的独立位置；这些字段存在非空值时也可能阻止输出。卖方资料缺失或无法映射时同样可能被拒绝。
- 受影响旧报价的 PI/XLSX 出单会被阻断；先前定向 API 验证表明销售订单仍可保存和确认。确认修订保留未知税号，不从客户主档回填。
- 真实历史报价中受影响记录数量及客户覆盖率尚未核对。若首发必须导出此类报价，应按授权核实并更正历史值，或确定模板对未知/扩展主体字段的安全表达方式；不得自动补值。

## 仍待首发处理

1. 对真实旧报价的缺失必填主体字段及模板未映射字段，仍需核对实际覆盖数量并决定经授权的历史更正或安全输出方案。
2. 正式启用前仍需完成项目既定的全站权限设计与验收、独立复审和其余上线检查。当前分支没有关闭 RBAC/身份验收事项。

本报告不表示系统整体已达到首发就绪。
