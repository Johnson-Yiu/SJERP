# ISS-055 客户越权访问 404 中文安全语义验收

## 范围

- 基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
- 分支：`codex/fix-iss055-chinese-404`
- 本地验收 worktree：独立 worktree，未使用脏的共享主工作树
- 任务：`R1-REPAIR-05` / `ISS-055`

本轮只修复客户详情 API 和详情弹窗在 404 场景下暴露英文 Django 模型错误的问题。没有修改正式业务数据库、开发超级管理员入口、正式 RBAC 配置或共享项目台账。

## 验收结论

后端对未知客户和当前数据范围不可见客户统一返回：

```json
{"detail":"客户不存在或当前账号无权访问。"}
```

该响应保持 HTTP 404，不包含 `Customer` 等英文模型名称，也不区分客户是否真实存在。客户详情 context API 与客户详情 API 使用相同语义。

数据范围边界未改动：已有测试继续覆盖 `self`、`department`、`department_tree`、`all`；有权客户返回 200，受限范围外客户返回 404。

## 实施文件

- `backend/crm/error_messages.py`：集中定义客户安全 404 文案。
- `backend/crm/views.py`：只将客户详情查询的 Django `Http404` 转换为共享中文安全错误；权限和 queryset 不变。
- `backend/crm/context.py`：客户 context 查询使用相同中文安全错误。
- `frontend/src/components/EntityDetailModal.vue`：详情加载失败通过统一 `apiErrorMessage` 展示，避免直接显示后端英文异常。
- `backend/crm/tests/test_sales_data_scope.py`：补充四类数据范围、未知客户、隐藏客户及响应体一致性测试。
- `frontend/tests/customer-ux.spec.js`：补充前端中文安全错误展示测试。
- `frontend/browser-tests/iss055-customer-404-real.spec.js`、`frontend/playwright.iss055.config.js`：隔离账号真实 Chrome 回归及证据配置。

## 自动化测试

| 验证项 | 命令/结果 |
| --- | --- |
| Django 数据范围及 API | `crm.tests.test_sales_data_scope`：31 tests，`OK` |
| 前端客户回归 | `npx vitest run tests/customer-ux.spec.js --environment jsdom`：10 passed |
| API Node 测试 | `node --test src/api.test.js`：7 passed |
| Django 配置 | `manage.py check`：无问题 |
| 迁移一致性 | `manage.py makemigrations --check --dry-run`：No changes detected |
| 生产构建 | `npm run build`：成功；仅有既有 chunk size warning |
| 真实 Chrome | 6 passed，桌面 1440×900 与窄屏 390×844 均通过 |

首次无提权构建因 Windows Vite 临时目录 EPERM 失败；在独立 worktree 允许写入构建临时目录后，用相同 `npm run build` 成功，未发现代码构建错误。

## 隔离 UI 数据与请求证据

Chrome 使用独立 SQLite 数据库和隔离员工账号，账号只有 `self` 数据范围和客户查看权限；没有连接正式数据库，也没有启用共享开发超级管理员。测试覆盖有权客户 `1`、无权客户 `2` 和不存在客户 `999999`，并在每个场景使用桌面及 390px 窄屏视口。

结果：

- 有权客户：详情 context 请求 200，页面正常显示详情。
- 无权客户：详情 context 请求 404，页面显示“客户不存在或当前账号无权访问。”。
- 不存在客户：详情 context 请求 404，页面显示相同中文提示。
- 浏览器日志中未出现英文模型名称或客户存在性差异。

截图：

- [有权客户—桌面](./authorized-desktop.png) · [有权客户—窄屏](./authorized-narrow.png)
- [无权客户—桌面](./unauthorized-desktop.png) · [无权客户—窄屏](./unauthorized-narrow.png)
- [不存在客户—桌面](./unknown-desktop.png) · [不存在客户—窄屏](./unknown-narrow.png)

请求日志：

- [无权客户桌面日志](./unauthorized-desktop-browser-log.json)
- [不存在客户桌面日志](./unknown-desktop-browser-log.json)
- [全部 Playwright 结果](./playwright-report.json)

本地隔离数据初始化脚本为 `backend/browser-run/iss055/seed.py`，仅包含合成账号、合成客户和本地测试密码，不包含真实密钥或正式业务数据。

## 未执行事项

- 未连接或修改正式生产数据库。
- 未启用正式生产 RBAC，未修改 `DEVELOPMENT_SUPERADMIN` 或权限边界实现。
- 未修改 `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md` 等共享台账；ISS-055 保持原状态，等待独立审查。
- 未触发 GitHub Actions；提交使用 `[skip ci]`。
