# ISS-020 正式报价与 PI 导出一致性证据

本目录保存 ISS-020 在独立 SQLite、独立 Django/前端端口和真实 Chrome 页面上的当前证据。数据库只用于本轮合成验收，不代表生产数据或生产部署安全。

## 当前范围

- 版本 A `ISS020-Q-A`：USD，已保存，红色历史图片、版本 A 收件人和条款。
- 版本 B `ISS020-Q-A-1`：EUR，修订版，邮箱显式为空，数量/价格/条款不同；修订复用保存的图片快照。
- 主档随后改名、改地址、改型号并替换蓝色图片；两个版本的 PI/XLSX 仍读取保存版本。
- `ISS020-Q-INCOMPLETE`：人为构造的历史不完整版本，仅用于验证 HTTP 422、字段提示和不生成文件。

## 运行方式

```powershell
$env:DATABASE_URL = 'sqlite:///C:/.../docs/uat-evidence/iss-020-quote-export/iss020-quote-export-evidence.sqlite3'
python docs/uat-evidence/iss-020-quote-export/prepare_evidence.py
python docs/uat-evidence/iss-020-quote-export/capture_api.py
```

启动后端时使用隔离端口 `28341`，前端使用隔离端口 `28342` 并将 `VITE_API_PROXY_PORT=28341`。`capture_api.py` 只访问该隔离 HTTP 服务并保存真实响应字节。

## 验收记录

详见 `TEST_LOG.md`、`browser-manual-log.md`、`api-evidence.json` 和本轮 Chrome Use 截图。实际 XLSX 由 Django 导出端点生成，用 openpyxl 只读检查，不以手工拼接文件替代导出。当前文件包含 `xl/media/` 历史图片、版本号、收件人、币种表头和英文金额大写。

权限验收仍以当前测试套件为依据：匿名/无导出权限返回 403，跨客户数据范围对报价详情及导出返回 404；开发身份本地服务按 AGENTS.md 统一享有开发超级管理员访问，不能冒充正式员工登录或生产权限验收。

生产 PostgreSQL、反向代理、真实账户及 Microsoft Excel 打印机未在本地环境验证，须独立审查/部署环境补验。Chrome 扩展最初因其他 Chrome Use 会话冲突短暂不可用，随后已恢复并完成桌面与 390px 窄屏截图；独立浏览器下载事件未在等待窗口内返回，实际 XLSX HTTP 字节已成功保存并核验。
