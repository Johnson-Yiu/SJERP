# SJERP PILOT-DELIVERY-FINAL-EVIDENCE-01

发布源码为 `0b0654de5b079d244b74d752ed4b78710ec4881b`，已核对远端 `codex/pilot-delivery-closeout-04`。同 SHA 干净维护检出与运行包分开保留。

| 验证 | 结果 |
| --- | --- |
| CI | [43577214916](https://github.com/Johnson-Yiu/SJERP/actions/runs/43577214916) 的 Backend、PostgreSQL、Frontend 成功。浏览器回归、构建和制品上传成功。[浏览器与打印制品](https://github.com/Johnson-Yiu/SJERP/actions/runs/43577214916/artifacts/14109748157) |
| 运维 | [43577218735](https://github.com/Johnson-Yiu/SJERP/actions/runs/43577218735) 的角色与回执、Nginx 私有媒体、只读媒体防护成功 |
| 生成 | 按固定 SHA 执行 build_pilot_release.py build --offline，锁定 npm 依赖并构建 |
| 文件 | 331 文件、5,141,754 字节。独立复制及 ZIP 解包后运行 verify，逐文件字节数和 SHA-256 一致 |
| 启动与资源 | 独立合成 SQLite 迁移和 Django check 通过。回环 HTTP 首页、JS、CSS 均返回 200，静态内容与文件一致 |
| 登录 | Django HTTP 测试客户端实际提交 CSRF、登录和退出端点。登录和退出均 200，身份随会话变化 |
| 附件 | 上传 201，下载 200，逐字节一致，退出后访问得到预期拒绝 |
| 模板和导出 | 销售订单 XLSX 下载与包内 XLSX 可解析，销售 CSV 导出 200 且非空 |
| 失败项 | 本轮定向验收无失败。目标主机、实际 HTTPS、目标 PostgreSQL 与备份恢复仍待授权后验收 |

ZIP 为 SJERP-pilot-0b0654de5b07.zip，1,778,045 字节，SHA-256 `ccdbf9b9b01750b6ed697892d97844f4564bb8acff0700b3a32d964651887846`。RELEASE.json SHA-256 `46dc7f82543025530070b655d479b36cda05121700136cbd407eed9e5e64721c`。包与本机冒烟原始日志在 C:/Users/Johnson/AppData/Local/Temp/SJERP-final-evidence-20261114-231018。测试库和私有媒体位于包外。

本机定向测试；GitHub Actions 全量认证。当前提交只追加验收记录，已认证的发布源码保持原 SHA。本轮保留文件，SKU 修复继续待独立复审。
