# R1-FIN-P2-B 截图清单

截图由隔离本地页面 `http://127.0.0.1:5211/rmb-cash-events` 在业务内容加载完成后采集；数据为 `r1-fin-p2-b-isolated.sqlite3` 的合成资金事件。

| 视口 | 列表 | 已确认详情 | 观察点 |
|---|---|---|---|
| 1440×900 | [real-ui-list-1440.png](real-ui-list-1440.png) | [real-ui-detail-1440.png](real-ui-detail-1440.png) | 桌面列表、状态、银行净额、详情来源快照 |
| 1280×800 | [real-ui-list-1280.png](real-ui-list-1280.png) | [real-ui-detail-1280.png](real-ui-detail-1280.png) | 常用办公宽度，详情保持可读 |
| 1024×768 | [real-ui-list-1024.png](real-ui-list-1024.png) | [real-ui-detail-1024.png](real-ui-detail-1024.png) | 窄桌面，详情滚动和长编号换行 |

内置浏览器还实际完成了待确认、放弃原因、重新登记、确认和刷新后的状态核对；截图接口不把内置标签的二进制直接写入工作区，因此以同一隔离服务的Chromium截图文件作为可审查原图归档。
