# INTEGRATION-VALIDATION-04 定向验收

- 远端统一分支基线：`2536efe1a97dec0597ab7c5c28750eea25f47d68`；核心 `78bcedb217d3d6ca0a05c9348e72d37c35801312` 为祖先。
- 完整合入权限 `bbfe475ef546b5d0fc3db8dbda0f456f0b042e9d` 和新品 `f63e984f33b86fb00c0de1daeb6a66fd4d42fc78`；两者均为当前候选祖先。应用/测试候选 `3d6fba7c1164bc9763fd475eac23c5a6f2f04b2c`。本报告提交只增文档及证据。
- 权限证据目录 add/add 冲突：30 项为行尾差异，保留统一分支现有证据；一项运行脚本实质不同，保留现有版本并将来源版本另存 `docs/uat-evidence/access-readiness-20261105/run_postgres-access-source.py.txt`。路由局部保留登录与新品提醒入口。未整文件覆盖业务实现。
- 根据用户最新决定停止尚未完成的本地全量：完整默认业务浏览器套件 **NOT_RUN**；原生打印延期；GitHub Actions **NOT_RUN**。不据定向成功推断全套通过。

## 定向结果

| 范围 | 命令 | 结果 |
|---|---|---|
| 后端（内存 SQLite） | `manage.py test crm.tests.test_new_product_reminders crm.tests.test_access_readiness_format_and_role --verbosity 1` | 15 项，退出 0，跳过 1 项 PostgreSQL 并发；执行于 `8fa12797356c79e2c9b5b0a5f78a114b11f5eab1`，之后仅两处登录测试等待条件变更 |
| 前端 | `npx vitest run tests/new-product-reminders.spec.js tests/organization-access-ux.spec.js --environment jsdom` | 17/17，退出 0；同上候选 |
| 运行器 | `node --test infrastructure-tests/runner-validation.test.mjs` | 20/20，退出 0；同上候选；覆盖默认业务和受限配置接线，不等同全套执行 |
| 独立受限登录真实 Chrome | `node scripts/run-isolated-browser-tests.mjs --business-test access-session-real.spec.js` | 当前候选 4/4，退出 0，桌面及窄屏；独立受限数据库和权限 |
| CSV 业务浏览器 | `node scripts/run-isolated-browser-tests.mjs --business-test import-ux.spec.js` | 当前候选 6/6，退出 0；API 为模拟数据。真实 CSV 见 `customer-template.csv`、`failure-report.csv` |
| 报价 XLSX | `node scripts/run-isolated-browser-tests.mjs --business-test quote-editor-mobile-actions.spec.js`，`EXPORT_STABILITY_CHROME=1` | 原候选 `539b50468cffe5076f2dd426f4182aa401afc22a` 1/1，真实文件 10218 字节，openpyxl 读取 PI 表 35×13；SHA256 `300b3388fe48e06fa9be5427a577996fcd8000d7b013a11e72106d84aebfe7a2` |

`backend-targeted.log` 中的 500 与 `audit failure` 为审计失败注入测试，非运行失败。浏览器原始私有日志包含临时隔离令牌，保留在本地任务目录；本目录提交脱敏摘要、页面快照、截图及下载文件。

## 先前候选结果与失败现场

原冻结候选 `539b50468cffe5076f2dd426f4182aa401afc22a` 在用户调整范围前完成 SQLite 1473 项退出 0、跳过 87；PostgreSQL 17 1473 项退出 0、跳过 32，合成备份恢复 PASS。原始运行日志和 `previous-full-result.json` 在本目录；运行整体按用户指示中断，不能记为全部通过。Windows POSIX 和符号链接等跳过及真实 Linux 恢复仍需目标环境。

此前和本轮各有受限登录以及 CSV 布局页卡在整页 `load`，快照已显示登录表单/导入页面。测试改等待 DOM 后仍保留原安全/布局断言；失败摘要和快照保留，不证明阻塞资源根因。历史 CSV 与报价下载取消的根因仍 UNKNOWN，本轮定向下载未复现，不覆盖历史失败。旧失败详见统一分支 `candidate-d7-full-evidence`、`candidate-d5-full-evidence`。

## 边界

主体版本、多标签继续独立开发；未启用正式 RBAC、导入真实数据、部署或合并 master。Linux 跨 UID 和真实恢复、原生打印、完整浏览器业务套件及上线前完整 CI 均未完成。无上线就绪结论。
