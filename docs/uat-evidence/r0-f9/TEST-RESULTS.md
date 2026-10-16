# R0-F9测试与证据核验

代码HEAD：0f0747a9d449e26e93885b3bf469a726f99ffaa8。后端Git树从b916fab到该HEAD完全一致。

- SQLite Backend：720，10个既有skip，通过；backend.log。
- Django check与makemigrations --check --dry-run：无问题/无变化。
- Node：121/121；typography独立1/1。
- Vitest：60文件，603/603。
- Playwright最终完整套件：139/139，5.6分钟，正常退出码0；包括新增12项。旧套件串行127通过，首轮未退出的日志不作为通过依据。
- Build：通过；主chunk约1.18MB的既有提示保留ISS-058。
- PostgreSQL：最终精确HEAD CI运行，必须核对backend-postgres SUCCESS才交付，不冒称本地执行。
- 真实Chrome：四个修改路由三尺寸原图chrome/*-baseline-*；内置浏览器27路由81张baseline-page。
- DB verify：合成入库2m、SKU库存102/预留20/可用82/在途18，应收500/核销10/待收490，联系人失败保留后重试/重开备注一致，员工0、RBAC=false、开发身份true。
- 索引真实浏览器核验：默认81/573；模块quotes为3/573；视口1280为1/573，原图href=quotes/baseline-page-1280.jpg，实际加载1280×1000；页面/表单/详情筛选和原图链接可用。
- manifest逐张重读原始JPEG、SHA-256和DOM文本哈希；69张像素不符（最终81张页面基线中17张），ISS-100保留。截图没有重编码或改图。

精确最终交付SHA和三项CI URL/结果见最终交付消息及对应GitHub Checks。交付文档提交frontend/backend Git树必须与source-baseline.json一致。代码/自动/实际操作、Codex目视及ChatGPT独立审图分别报告，后者仍待审。
