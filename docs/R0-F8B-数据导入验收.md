# R0-F8B 数据导入 UI/UX 验收

2026-10-16；仓库Johnson-Yiu/SUNJACK-ERP；目标master；基线`82514b1396e1e53d44bcd9314d19bbb65b0fbeed`。最终SHA及精确HEAD三项CI由本报告所在交付提交和GitHub Checks/交付消息绑定。

## 前阶段与范围

用户转述ChatGPT对R0-F8A独立代码、自动及已覆盖交互审查PASS，允许有条件封版；最终82514b1396e1e53d44bcd9314d19bbb65b0fbeed，[CI #38761364221](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38761364221)三项SUCCESS。ISS-092/093只记录该接受范围；独立图片视觉及ISS-007/017文件内容/授权缺口保留。

本轮只优化`ImportPage.vue`，继续使用现有客户、产品、SKU、财务流水接口、预览token和确认弹窗。后端仅增强既有测试的同token重放拒绝断言，没有修改导入核心、模型、唯一性、SKU身份、快照、金额、权限或正式RBAC。

## 优化及操作矩阵

| 流程 | 实现与结果 | 验证层次 |
|---|---|---|
| 类型选择 | 四类保留；切换清除文件、错误、结果及旧token；重置实际file input | Vitest、真实浏览器 |
| 模板 | 独立加载/错误/重试；没有真实非空字段时禁止下载；直接使用服务端字段 | Vitest、Playwright、四份实际下载 |
| 本地文件 | 显示名称、大小，明确UTF-8/BOM和5000记录限制；不声称选择即完成编码检测 | 内置浏览器真实chooser |
| 预览 | 文件已选、上传校验、通过/拒绝分阶段；明确尚未写入；预览请求只调用preview | 延迟请求自动回归、真实API/DB |
| 错误明细 | 行号/业务编号/原因表格，20项分页；解释逻辑记录行号和字段内换行；缺失产品提示自然中文 | 自动长表布局、真实重复/坏行；下载保留后端原始原因 |
| 正式执行 | 二次确认明确新增/更新数和覆盖风险；取消无execute；确认期间立即锁定，token绑定原文件上下文 | Vitest可控promise、Playwright、真实取消/写入 |
| 请求保护 | 方法级防重；类型/文件禁用；统一busy路由、浏览器Back、beforeunload保护；版本/卸载阻止旧响应写回 | 可控延迟Vitest/Playwright；不是靠即时mock推断 |
| 成功 | 只在完整合法的计数返回后显示已入库；移除可执行token；前往对应模块 | 实际四类成功及客户详情重开 |
| 失败恢复 | 保留文件，清除旧凭证，提示先核对记录再预览；网络失败不武断声称零写入 | 真实并发状态冲突、自动拒绝/不完整响应 |
| 只读 | 模拟受限operator不提供预览/执行；正式权限策略未变 | 模拟API回归，不等于真实员工UAT |
| 布局 | 1440/1280双栏；1024规则说明下移、类型两列；长文件/错误换行，表格局部滚动 | 3尺寸实际计算边界、Codex实际目视 |

## 隔离真实CSV与数据库结果

独立SQLite：`backend/r0f8b-ux.sqlite3`，从空库执行migrate；Django8116，Vite5203代理到8116。只创建F8B合成资料，未使用、清空或迁移用户业务库。开发超级管理员、默认开发姓名；非真实员工登录或正式审计身份。测试中断后重启相同专用服务，保留隔离库继续核对，没有重置数据库。

真实UI均通过Codex内置浏览器`filechooser.setFiles(绝对路径)`选择文件；预览/确认按钮向真实Django发multipart请求。没有以路由mock代替下面矩阵。全部源CSV见[files](uat-evidence/r0-f8b/files/manifest.json)，数据库各阶段完整合成字段/计数/哈希见[database-results.json](uat-evidence/r0-f8b/database-results.json)。`snapshot_database.py`以SQLite只读连接核对精确专用文件名。初始四表计数均0，最终客户2、产品1、SKU1、流水1。

| CSV场景 | 实际结果与数据库核对 |
|---|---|
| A 客户正确新增 | 预览total2/create2，四表仍0；确认取消后仍0；再次确认后客户2，其余0 |
| B 客户更新 | 预览update1且字段/哈希不变；确认后客户数仍2，名称和多行备注与CSV一致 |
| A/B 产品新增及更新 | 新增预览product0，执行后1；更新预览update1，执行后名称为中文产品更新；身份编号不变 |
| A/B SKU新增及更新 | 新增预览sku0，执行后1；更新后仍F8B-S01，成本3、默认价6，数量1；未改现有更新政策 |
| C 文件内重复客户编号 | 第3条记录F8B-DUP报重复（首次第2条），无执行入口；未产生F8B-DUP，整个文件预览回滚 |
| D 必填字段为空 | 第2条记录name为空被拒，无执行入口，数据库不变 |
| E SKU金额错误 | not-number被拒，未新增SKU |
| F 不存在引用 | SKU的product_code不存在被拒，未新增SKU；当前格式没有可任意引用SKU的额外列，不扩展格式 |
| G 中文/英文/特殊字符 | 客户、产品及SKU合成资料可预览/执行；DB字段按CSV核对 |
| H 逗号、双引号、换行 | Python标准csv.writer生成真实转义文件；客户多行notes原样入库，客户详情重开显示两行，实际字段比对PASS |
| I 空文件/错误表头/错误编码 | 空文件、缺code/name表头、GBK非UTF-8分别被真实400拒绝；保留文件可换文件重试 |
| J 财务正常/重复/非法 | 新增F8B-T01金额12.50成功，计数1；同号99被拒，原金额12.50保留；oops非法金额被拒，无新流水 |
| 执行时状态冲突 | 预览B后，用带精确路径/样本断言的专用脚本修改隔离客户notes；执行被拒，前后四表字段哈希完全相同；页面保留B文件并清token；重新预览执行update1恢复成功 |
| 同文件重复执行 | 后续重新选择A并取得新token，预览新增0/更新2，确认后更新2，客户数仍2，符合现有按编号更新规则；不宣称客户更新是禁止覆盖。财务相同流水号仍拒绝 |
| 原token重放/原子性 | 真实服务端TestCase验证原create token再次execute400且不变成更新；已有故障注入测试证明文件执行中途异常整单回滚。此为隔离后端自动验证，不声称真实浏览器制造中途写故障 |

[verify_files_database.py](uat-evidence/r0-f8b/verify_files_database.py)只读重算，核对不变阶段、业务计数、具体字段、多行内容以及下载文件；[结果JSON](uat-evidence/r0-f8b/file-database-verification.json)PASS。`inject_conflict.py`只作用于显式可销毁专用库与F8B-C01，不触及应用正式业务逻辑。过期/无效/换文件token由后端自动回归覆盖，不把mock时间过期宣称真实浏览器等待30分钟。

## 实际下载与编码

内置浏览器download事件返回实际下载路径，再复制原始字节归档，没有通过API另造下载。四类CSV模板均UTF-8 BOM，逐字段/顺序对照当前后端`IMPORT_FIELDS`完全相同。客户错误清单也有BOM，标准csv.reader解析为row=3、key=F8B-DUP及正确重复原因。Playwright另用含逗号、引号、换行的错误原因验证CSV下载字节和转义；该复杂错误下载用模拟API，与真实后端失败清单分开记录。

[实际下载文件](uat-evidence/r0-f8b/downloads/)、[download记录](uat-evidence/r0-f8b/download-records.json)、[编码/字段/哈希核对](uat-evidence/r0-f8b/file-database-verification.json)。下载记录中的本机路径为当时工具返回值，不保证后续机器存在。

## 浏览器、原图与独立视觉

[22张原始截图清单](uat-evidence/r0-f8b/SCREENSHOTS.md)、[manifest](uat-evidence/r0-f8b/manifest.json)、[操作说明](uat-evidence/r0-f8b/README.md)。原始JPEG未经缩放、编辑、重编码。请求视口、DOM视口、实际JPEG像素及文件名逐张相同；SHA-256由只读脚本重算。视口高度1000，长页面可自然滚动，截图不意味着全部内容都在首屏。

- 自动布局：1440/1280/1024真实计算边界、长文件名/25条长错误表、分页；PASS。
- Codex实际浏览器：四类真实API、文件选择/下载、预览/取消/写入/失败恢复、客户返回与详情重开，三尺寸目视；本报告列出的操作已检查。
- ChatGPT独立图片视觉：**待审**。本轮截图正常归档，没有截图导出BLOCKED；归档与自动化均不等于独立视觉PASS。

中断前部分操作没有保留独立完整HTTP状态日志；继续会话的真实模板GET、CSV preview/execute 200日志附[real-api-http.log](uat-evidence/r0-f8b/real-api-http.log)。较早拒绝路径有真实UI/DB证据，不补造丢失的HTTP日志。ISS-052的正式身份审计一致性、完整HTTP证据仍不足，继续NEEDS_VERIFICATION，本轮不申请关闭或宣称其完整验收通过。没有为了补证启用RBAC或真实员工账号。

## 自动化与交付边界

完整结果见[TEST-RESULTS.md](uat-evidence/r0-f8b/TEST-RESULTS.md)。Backend720（10个既有skip）、Node121、独立typography1；完整Vitest与Playwright、Build按最终日志记录。后端/PG/前端最终精确HEAD CI结果由交付消息和对应commit checks核对，不能拿基线CI代替。

ISS-094新增FIXED_PENDING_REVIEW；ISS-052保留并追加真实证据；ISS-092/093同步已接受代码范围；没有关闭历史Issue。全站覆盖清单已更新，组织/权限及其状态页尚未专项，不进入R0-F8C、集中历史修复、正式RBAC、员工UAT或部署。Push master及三项CI成功后停止，等待ChatGPT独立代码和图片复审。
