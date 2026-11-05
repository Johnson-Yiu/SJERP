# 真实 Django / SQLite / Chrome 财务 CSV

- 真实 Django 127.0.0.1:8299、独立 Vite 127.0.0.1:5299 和本目录 legal-api.sqlite3；不存在 mock。合成流水、凭证上传、资金事件建立与确认通过 Django APIClient 调用真实视图、校验及状态机，参见 seed-api.py 和 seed-api-final.log；初次因 testserver 不在 ALLOWED_HOSTS 失败，其后因重复候选被状态机拒绝，改用不同日期与金额后成功。先前试验用 isolated.sqlite3 中的直接写入记录没有用于本验证。
- chrome-real-retry.log：16 次真实 Chrome 下载通过：1440/390 × 2026-09/10 × 账面/实际资金 × 连续两次。results.json 给出每项状态、下载名、长度、SHA-256、金额、四种前缀及比对结果；CSV 文件为下载原件。每项经另一笔相同 URL 原始 HTTP 请求核对，响应字节与下载完全一致，含 EF BB BF；并检查所选金额与 `'=synthetic`、`'+synthetic`、`'-synthetic`、`'@synthetic`。独立 HTTP 请求并非浏览器发起导出请求的同一响应，隔离库在测试期间不变。
- 首次真实端到端在直接比较 Playwright response.body 与下载时失败（chrome-real.log）：response.body 比下载少 BOM 三字节。重试记录 browserResponseEqualsDownload=false、browserResponseEqualsDownloadWithoutBom=true，原始 HTTP 与下载一致；不能据此声称 Playwright 的 response.body 字节与下载完全相等。首次 screen-1440-09.png 被重试重新生成，首次截图原件未保留；原有财务证据目录的截图和日志未覆盖。
- 原专项首次模拟 500 的原始日志文件：UNKNOWN（没有保存独立文件，后续 chrome-test.log 是最终结果，未重建首次日志）。首次失败为 GET 客户端自动重试 500，测试等待立即出现错误超时；最终使用 400 模拟不可自动重试的请求失败，获得 3/3。原 Django 33/33 不变。
- 范围：这里覆盖财务概览和实际资金，不含账户资金页面；只核对合成数据的指定金额和四种前缀，非所有业务字段。CSV 比较按字节并保存 SHA-256，金额和公式检查为 UTF-8 文本包含断言。

## 修复前证据澄清（2026-11-05）

没有在修复前运行新增专项测试，也没有修复前版本的失败日志。因此，概览导出失败后无法直接重试，以及实际资金导出缺少并发保护、响应期间变更可能造成文件名与请求期间不一致，均属于阅读原代码后的静态推断；不能表述为修复前已实测复现。

修复后的模拟 Chrome 专项验证了概览失败后重试、期间切换和实际资金失败后重试及进行中禁用；未验证实际资金导出请求期间切换日期的完整场景。修复后的真实 Django/Chrome 结果、首次直接响应体比较失败与后续通过另一笔独立 HTTP 请求间接比较的限制，以上原有记录和日志保持不变。首次模拟 500 的原始文件仍为 UNKNOWN。

版本核对：该真实服务由同一会话中的 `python manage.py runserver` 启动，命令解析对应 `C:\Python314\python.exe`、Django 6.0.6；项目锁定 Django 6.0.9，因此此结果不是锁定依赖验证。服务进程未单独记录 sys.executable 和版本，路径为同会话命令解析证据。详见上一级 finance/README.md。
