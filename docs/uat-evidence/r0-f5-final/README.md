# R0-F5 最终保存竞态验收证据

2026-10-15，基线7774eeb，只修保存期间关闭/导航竞态。截图为Codex内置浏览器实际页面，使用文档的screenshot返回JPEG并正常writeFile保存；没有使用外部截屏通道或修改图像。截图对应未提交工作树的两个源文件哈希见[manifest](manifest.json)，最终代码提交见Git历史和本轮交付。

| 关键状态 | 1440×1000 | 1280×1000 | 1024×1000 |
|---|---|---|---|
| 联系人POST保存中（遮罩/Back后仍开） | [截图](contacts-saving-1440.jpg) | [截图](contacts-saving-1280.jpg) | [截图](contacts-saving-1024.jpg) |
| 跟进POST保存中（遮罩/Back后仍开） | [截图](follow-ups-saving-1440.jpg) | [截图](follow-ups-saving-1280.jpg) | [截图](follow-ups-saving-1024.jpg) |
| 联系人创建成功、列表刷新 | — | — | [截图](contacts-success-1024.jpg) |
| 联系人PUT失败、输入保留、可重提 | — | — | [截图](contacts-failure-1024.jpg) |
| 跟进创建成功、列表刷新 | — | — | [截图](follow-ups-success-1024.jpg) |
| 跟进PUT失败、输入保留、可重提 | — | — | [截图](follow-ups-failure-1024.jpg) |
| 跟进PUT重试成功、列表刷新 | — | — | [截图](follow-ups-retry-success-1024.jpg) |

截图中的跟进表单保持实际保存点击后的内部滚动位置；保存按钮/计划区域可见，完整表单要结合此前R0-F5截图。失败图片记录保留字段和恢复按钮；短暂错误toast在AX观察中确认“服务器暂时不可用”，不把图片中未显示的内容认定为视觉证据。1024跟进页面截图API可能返回1009×985，manifest保留实际图像尺寸；DOM实际innerWidth/Height为1024×1000，未补边/拉伸。

## 可控请求与隔离环境

本地Vite5198使用VITE_API_PROXY_PORT=8111；[controlled_proxy.py](controlled_proxy.py)只绑定127.0.0.1，转发至8109原隔离r0f5-ux.sqlite3，不连接用户已有数据库。控制文件mode=hold暂停record POST/PUT，mode=success释放到真实API，mode=fail直接返回503、不写数据库。该代理只是故障/时序注入工具，不是应用实现，也不是截图代理。验收后已停止代理/Vite5198、删除控制文件，浏览器临时视口已reset。

[实际写入尝试日志](request-attempts.jsonl)仅记录方法、隔离路径和时间，不包含请求正文/凭据。两条POST创建R0F5 FINAL合成联系人/跟进；每个对象一次失败PUT、一次真实成功重试PUT，再一次失败PUT补证可见输入，最后取消未保存修改。共8次明确操作，不能将不同时间的失败重试等同重复发送。快速双击是否仅发一次由自动化精确次数断言证明。

## 自动化

- `frontend/tests/crm-saving.spec.js`：12项可控Promise；两实体×POST/PUT成功/失败、旧放弃确认竞态、跟进clean但attachment pending、busy且clean文档离开。
- `frontend/browser-tests/crm-saving.spec.js`：8项；每实体3个视口POST未完成时关闭/导航/Back，以及PUT失败/双击重试；API fixture与真实后端证据分开。
- 完整Frontend：Node121/121、Node-only1/1、Vitest54文件546/546、全部Playwright55/55、Build SUCCESS；相关隔离Backend跟进回归12/12。精确最终HEAD三项CI由交付链接核验。

这些是Codex操作记录/截图和自动回归证据，ChatGPT独立视觉仍待复审。历史ISS-007附件文件授权/内容不在本轮关闭，ISS-080联系人重复提示范围只登记。
