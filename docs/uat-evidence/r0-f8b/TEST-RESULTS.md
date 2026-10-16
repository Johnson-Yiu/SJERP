# R0-F8B 自动化与文件验证记录

2026-10-16，本地Windows；命令在当前验收工作树执行。最终精确HEAD的Linux/PostgreSQL结果以同提交GitHub CI为准，交付消息提供运行链接。

| 检查 | 命令 | 结果 |
|---|---|---|
| Backend完整 | `python manage.py test` | 720项，OK，10个既有skip；Django自动创建/销毁test数据库 |
| Backend安全导入 | `python manage.py test crm.tests.test_safe_csv_import` | 12项PASS；包含新增原token重放400/客户数不变断言；未修改核心代码 |
| Django配置/迁移 | `python manage.py check` / `python manage.py makemigrations --check --dry-run` | 无问题，无迁移变化 |
| Node完整 | `npm run test:unit` | 121 PASS |
| typography | `node --test tests/detail-drawer-typography.spec.js` | 1 PASS |
| Vitest完整最终运行 | `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers=2` | 59文件、592项PASS，137.44秒 |
| Playwright完整最终运行 | `npx playwright test --workers=2` | 111 PASS，4.4分钟，退出0 |
| Frontend生产构建 | `npm run build` | PASS；保留既有大bundle/插件耗时提示，不属于构建错误 |
| 真实下载/DB离线核对 | `python docs/uat-evidence/r0-f8b/verify_files_database.py` | PASS：4份实际模板、1份实际失败CSV、BOM/字段/行号/转义、DB计数与具体字段 |
| 原图清单 | `python docs/uat-evidence/r0-f8b/generate_manifest.py` | 22张原图，请求/DOM/像素/文件名一致，SHA-256重算 |

新增Vitest 6项（另保留原冲突测试）：可控preview/confirm/execute Promise、禁止重复请求/路由离开/卸载、取消零执行、失败保文件清token、类型变化旧响应丢弃、换文件失效、不完整响应不能成功、模板失败重试。部分场景组合在同一个用例中。

新增Playwright 6项：三尺寸长文件/25条长错误布局与分页；下载实际字节含BOM/双引号/逗号/换行；可控延迟请求中导航与Back保护、取消零写入、成功返回；模拟受限入口及模板重试。此套路由mock仅证明前端行为；真实CSV chooser/真实Django/实际DB证据另见主验收报告。

完整套件继续覆盖客户、供应商、联系人、跟进、产品/分类/参数、SKU/库存/包装/交易单位、证书/HS、财务、概览/报表、报价与订单。没有改共享组件和正式权限设置。

本地运行说明：第一次完整Vitest 591项通过，Windows退出fork时有两条终止超时提示；补响应形状用例后的最终完整运行592项干净通过。第一次完整Playwright111项正常退出；最终运行111项用例均通过后，Windows临时5195 Vite服务的退出清理等待，核对确切进程/端口后停止该测试服务，runner随后报告111 passed及exit0。未修改断言、重试掩盖失败或停止5203真实验收服务。Linux CI仍需独立核对精确HEAD三项SUCCESS。

真实浏览器的模态确认、文件选择、文件下载、HTTP拒绝与重新预览均与自动mock分开记录。真实后端原子回滚/无效和过期token由Django隔离TestCase覆盖；不宣称浏览器实际制造中途数据库异常或正式员工权限/审计UAT。
