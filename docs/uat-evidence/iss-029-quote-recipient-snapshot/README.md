# ISS-029 报价收件人版本快照

基线：`b3559f3bf83b967d06166bd409b00fc92e4e5902`
分支：`codex/iss-029-quote-recipient-snapshot`
测试日期：2026-10-25。交付整理：2026-10-26。状态：`FIXED_PENDING_REVIEW`，等待独立审查。

规则来源：已完整读取用户提供路径 `C:\Users\Johnson\Desktop\SUNJACK-ERP_B8E5A1A7E599AEE6B4A7E4A48C%85_2026-10-24\新增议题逐项移交\ISS-029_报价收件人资料按报价版本保存.md`，并核对相邻 ISS-020、`docs/TaskH1-客户跟进报价链路.md`、原始 UAT 的 P2 邮箱记录及 ISS-037 集成验收。

已确认缺口：创建报价时使用真假值判断预填，显式空邮箱会被主联系人邮箱替代；前端联系人异步响应可能覆盖手工输入或较新客户的预填。复用现有 Quote 收件人字段及修订链，分别改为仅缺失字段预填、手工编辑优先和请求序号检查。无新模型、无迁移、无客户主档写入。

已有正确行为：保存报价不可原地改写，修改通过新修订版本留痕；修订继承上一版收件人四字段；标记发送/接受不重取主档；PI API 和 Excel DTO 读取保存的指定版本。空历史字段继续保持空，不用新主联系人伪造历史。

规则原文 SHA-256：`8088563092bc4fe08b096f6be6ae373f8fa6118fb40a5b8ddb97bef138830ce2`。

## 验收结果

| 场景 | 证据与结果 |
|---|---|
| 新报价预填 | 真实 Chrome 从主联系人带入姓名、邮箱、电话及客户地址；API 缺省字段仍自动预填 |
| 手填优先、不回写主档 | Chrome 手填 A 后保存成功，联系人仍为原值；前端 4 个新增用例覆盖已有预填、清空、异步返回和切换客户 |
| 草稿保存与重开 | GET 指定版本返回完整四字段；Chrome 重开 B 的修订起点，空邮箱仍为空 |
| 空邮箱 / 错误邮箱 | 显式空值保存成功；错误邮箱真实 HTTP 400，前端保留输入；后端创建/修订失败均不新增报价 |
| 正式版本 / 修订 A、B | A 标记已发送后创建 B；B 初始继承 A，随后四字段独立修改，旧版保持不变 |
| 联系人及客户主档变化 | 隔离主联系人改为 changed-master@example.com、客户地址修改后，A/B 的详情、PI API 和 XLSX 仍保留各自版本 |
| 未保存输入与正式导出 | 在 B 编辑器填写 unsaved@example.com 而不保存；正式 PI 和实际下载的 Excel 邮箱保持 B 的空值 |
| 历史兼容 | 旧空字段的 PI 和修订保持为空；不新增模型、迁移或历史回填；既有状态动作和行级快照不变 |
| 权限 | 全量中既有未登录导出拒绝、view-only 无 export 的 403、越权客户导出/修订 404、数据范围和关联权限回归通过；受限身份只存在于测试中 |

真实 Chrome 使用完整应用连接本轮隔离 Django + SQLite，没有 mock API。数据库在 `fixture.json` 记录；仅包含合成客户、联系人、SKU、两版报价。开发身份仍为服务端既有超级管理员，不将它宣称为正式登录审计人。

版本 A：`SJ20261025DE001`，已发送，`Version A Recipient` / `version-a@example.com` / `+49 222 A` / `Version A Berlin Address`。

版本 B：`SJ20261025DE001-1`，草稿，`Version B Recipient` / 空邮箱 / `+49 333 B` / `Version B Berlin Address`。修改说明保留在数据库与 API 中。

## 实际文件、响应和截图

- `version-a.xlsx`：10,159 字节，SHA-256 `8d4881dbbf8895a77147c5fa68a1a6ccca3c381e4e8f553c3bd17b4dba75bbca`。
- `version-b-empty-email.xlsx`：10,141 字节，SHA-256 `f832d4bce22e022c64641201d0563b5b3b83badabef708c98cf0a701f79add58`。
- `version-b-with-unsaved-input.xlsx`：10,142 字节，SHA-256 `213bf7c5c6dca6f0b8e8a8d7356468a700e63abd2cd790be8c32451f4818c0ab`。
- `api-evidence.json`：真实 HTTP 400/201/200 响应、主档变更及版本读取。
- `export-reconciliation.json`：数据库快照与三个实际 XLSX 的 `PI!B4/B5/B7/B8`、`L9` 对账；空邮箱单元格为空，没有当前主档或未保存邮箱。
- `chrome-version-b-editor-1440.png`、`chrome-version-a-saved-pi-1440.png`、`chrome-version-b-saved-pi-1440.png`、`chrome-version-b-saved-pi-700.png`：真实 Chrome 截图。已人工目视核对字段与办公文案；700px 保留既有纸张宽度并可横向滚动，本轮未改 PI 布局。

文件由现有应用导出端点生成并由 Chrome 实际下载，未另造工作簿。使用 openpyxl 只读打开并核验单元格；本轮未执行 Microsoft Excel 桌面程序或打印机验收。

## 测试日志

详见 `test-results.md`；原始日志一并提交。Django 全量 881 项，成功结束，13 项跳过；Node 151 项、有效 Vitest 652 项、生产构建、真实 Chrome 完整业务场景 1 项（含 1440px/700px）、模型/迁移检查通过。

本轮没有新增 Issue ID、没有关闭 Issue。历史 UAT 的非空邮箱丢失未在当前普通保存流程重现；这不作为“历史误报”关闭，已确认的空值和竞态缺陷单独有回归。ISS-020/025/080 仅兼容性审查，不并案或宣称完成相邻任务。

## 复现与审查边界

使用新建的专用目录中的 `iss029-recipient-evidence.sqlite3`，设置 `DATABASE_URL` 后运行 `prepare_evidence.py`，启动隔离后端 8299，再在 frontend 执行 `npx playwright test --config playwright.iss029.config.js --reporter=list`，最后运行 `verify_exports.py`。脚本不会删除已有数据库；再次采集时请使用新的隔离目录，以保留原样本。

GitHub CI 按最终推送提交核对，结果见交付记录。当前报告的本地测试不代表 PostgreSQL 或生产环境验收；独立代码、权限和视觉审查仍待完成。
