# ISS-049 通用业务列表快捷筛选验收记录

- 基线：`c356e57014d28295485d52df23612c2fe6c02444`
- 分支：`codex/iss-049-quick-filters`
- 验收日期：2026-10-23
- 说明：浏览器验收使用独立工作树及本地最小样例数据；未复用其他任务分支数据库。

## 结果

- 客户管理：负责人、国家/地区、状态；组合筛选、重置、翻页、筛选回到第一页、刷新恢复均通过。
- 客户跟进：负责人、跟进方式、日期范围；保留既有 `due=true` 的“待跟进”状态筛选；组合、状态切换、重置、URL 恢复通过。
- 财务流水：复用既有日期范围、收支方向、状态筛选；收入 + 日期组合、已作废状态筛选通过；未改动 ISS-048 财务概览。
- 权限：后端测试覆盖负责人/国家选项和客户结果的销售范围约束，受限员工无法通过筛选扩大数据范围。
- 窄屏：700px 下三页 `document.documentElement.scrollWidth === innerWidth === 700`，筛选区无页面级横向溢出；表格保留局部横向滚动。

## 自动测试

| 命令 | 结果 |
| --- | --- |
| `python manage.py check` | 通过，无系统检查问题 |
| `python manage.py makemigrations --check --dry-run` | 通过，无迁移变更；非测试数据库检查有既有 SQLite 文件警告 |
| `python manage.py test crm.tests.test_issue_049_quick_filters --verbosity 1` | 5 项通过 |
| `python manage.py test crm.tests.BusinessFlowTests.test_follow_up_attachments_upload_and_context --verbosity 1` | 1 项通过 |
| `npm run test:unit` | 145 项通过 |
| `npx vitest run tests/crm-list.vitest.js --environment jsdom` | 4 项通过 |
| `npm run build` | 通过；Vite 转换 2009 modules，仅保留既有大 chunk 提示 |
| `PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/crm-ux.spec.js` | 9 项通过 |

全量 `python manage.py test crm` 首次运行共 815 项、13 项跳过，唯一错误是工作树缺少可写 `backend/media` 导致既有附件测试无法创建目录；补齐该忽略目录后，该测试单项通过。本次改动相关测试无失败。

## 截图

- [客户管理桌面](./iss-049-customers-desktop.png)
- [客户管理窄屏](./iss-049-customers-narrow.png)
- [客户跟进桌面](./iss-049-follow-ups-desktop.png)
- [客户跟进窄屏](./iss-049-follow-ups-narrow.png)
- [财务流水桌面](./iss-049-transactions-desktop.png)
- [财务流水窄屏](./iss-049-transactions-narrow.png)

## 遗留事项

- 财务流水页面本次复用已有筛选实现；该页面当前没有独立分页控件，因此没有新增财务分页逻辑。
- `npm install` 的依赖审计仍提示仓库既有 11 个漏洞；未在本 Issue 范围内升级依赖。
