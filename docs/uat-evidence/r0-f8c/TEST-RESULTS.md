# R0-F8C 测试记录

2026-10-16，本地Windows；命令在本轮验收工作树运行。精确最终HEAD的Backend/PostgreSQL/Frontend CI通过情况由交付消息及对应GitHub运行绑定；不以基线CI代替。

| 检查 | 命令 | 结果 |
|---|---|---|
| Backend完整 | `python manage.py test` | 720项OK，10个既有skip，328.103秒；自动创建/销毁测试库 |
| 系统与迁移 | `python manage.py check`、`python manage.py makemigrations --check --dry-run` | 无问题，无迁移变化 |
| Node完整 | `npm run test:unit` | 最终121 PASS |
| typography | `node --test tests/detail-drawer-typography.spec.js` | 1 PASS |
| Vitest完整 | `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers=2` | 60文件、603项PASS，203.01秒 |
| Playwright完整 | `npx playwright test --workers=2` | 127 PASS，5.7分钟，退出0 |
| 页面最终专项 | `npx playwright test browser-tests/organization-access-ux.spec.js --workers=2` | 16 PASS，1.3分钟；最终范围说明恢复后重验 |
| Build | `npm run build` | 最终PASS，1.73秒；既有bundle提示保留 |
| 隔离DB/配置 | 专用库执行`verify_isolated.py` | 四次核对预置角色和权限不变；成员0、RBAC=false、development_superadmin_enabled=true |
| 原图 | `python docs/uat-evidence/r0-f8c/generate_manifest.py` | 30张原始JPEG尺寸、文件名及SHA-256核对 |

新增Vitest11项覆盖：渲染不改服务端对象、原查看/操作联动、角色切换取消/放弃、POST与回读延迟、重复调用、导航/Back/unload、拒绝保留、筛选下完整提交、已提交回读失败只读重试、最高/只读模板、查询失败重试、401/403/500/网络、防循环和安全恢复。已有functional-rbac11项保持原权限拒绝/侧栏断言，并补角色GET及实际编辑后保存。

新增Playwright16项：三尺寸40模块长名称矩阵及固定头/列计算边界；dirty确认和可控POST/GET导航保护；保存/读取失败、重试、重开；模拟只读入口；两个状态页三尺寸与安全返回；401/403/500/网络服务失败、空权限无返回、恢复防循环。初次fixture返回空数组造成Dashboard模拟数据错误，已复用既有dashboard fixture纠正；没有修改真实Dashboard代码。最终专项及完整运行不再依赖该错误。

回归发现原CRM/共享主数据范围说明不能在文案简化中省略，已恢复其明确区分并保留原Node断言，最终121项全通过。代码与正式权限策略未因测试放宽。

Windows临时5195测试服务在初次专项完成16项后退出清理等待，核对确切端口/路径后停止该临时服务；后续完整及最终专项在允许正常清理测试子进程的环境运行，均正常退出。没有停5204页面服务或改变断言来掩盖失败。

实际浏览器证据与模拟API严格分开：真实API停服造成Vite代理500、真实保存/回读/重开、权限服务恢复已有原图/日志/数据库证据；401/403/网络abort和只读用户为自动fixture。没有真实员工账号、正式RBAC、全站权限/UAT或独立图片视觉PASS。

一次只读核对从错误工作目录运行，相对SQLite路径指向新空文件并报缺表，未生成通过记录或改业务数据；随后增加解析后绝对路径校验，并在backend工作目录完成四次核对。误建的0字节空测试文件已移除，专用隔离库保留，用户库未操作。
