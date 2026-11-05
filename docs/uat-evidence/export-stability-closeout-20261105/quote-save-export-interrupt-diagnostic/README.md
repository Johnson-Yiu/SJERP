# 报价保存并导出：最多三次独立失败诊断

锁定版本 Packing 390px 已完成后执行。本次 3 次各 1/1 通过，未复现历史 `download.saveAs: canceled`；**历史失败根因仍为 UNKNOWN，不能称已修复**。不继续重复。

每次从旧合成 SQLite 复制独立数据库、在副本中用 ORM 增加合成客户和 SKU，使用各自 Django / Vite 端口、Python 3.12.16 / Django 6.0.9、真实 Chrome channel；不连接业务数据库。每次重新启动服务，测试结束后关闭。原报价测试、产品源码及全量运行器未修改；副本保留原全部动作和断言，仅调整模块引用，增加 page/context 关闭及 download 事件日志，以及 `saveAs` 失败后调用 `download.failure()` / `download.path()` 的捕获并重新抛出异常。原文件及副本 SHA 见 `copy.raw.log`。每次首次测试失败即停止，本次没有失败。

| 次数 | Playwright 退出码 | 原始输出 | 页面及上下文事件 | 实际文件 |
|---|---:|---|---|---|
| 1 | 0，1/1 | `run-1/playwright.raw.log` | `run-1/lifecycle.jsonl` | `run-1/downloaded-quote.xlsx` |
| 2 | 0，1/1 | `run-2/playwright.raw.log` | `run-2/lifecycle.jsonl` | `run-2/downloaded-quote.xlsx` |
| 3 | 0，1/1 | `run-3/playwright.raw.log` | `run-3/lifecycle.jsonl` | `run-3/downloaded-quote.xlsx` |

每次 seed 和测试命令、退出码、独立端口见 `run-N/result.json`；各次 Django、Vite、seed 原始日志位于各自 `run-N/`。本轮入口命令是在工作树根以指定锁定 Python 运行 `docs/uat-evidence/export-stability-closeout-20261105/quote-save-export-interrupt-diagnostic/run.py`，原始输出 `orchestrator.raw.log`，退出码 0（`orchestrator.exit.txt`），逐次摘要 `summary.json`。运行器采用单 worker、无重试、30 秒单测试限制。服务是完成后由本诊断停止，不作为被测测试退出码。

三次均记录 download、page-close、context-close 的绝对时间，未进入失败分支，故没有本次失败的 `download.failure()` 值或失败时内部路径长度；**browser interruptReason 为 UNKNOWN，没有采集 chrome://downloads/ 的中断码**。即使失败，Playwright `download.failure()` 也不保证给出浏览器底层中断码，不能将 `canceled` 等同于具体原因。成功后没有额外调用 `download.path()`，因此本轮内部路径长度 UNKNOWN；路径长度已在另一个字节诊断中单独记录，不可当成本轮或旧失败的测量。

监听和同步记录本身可能影响时序；三次通过不覆盖历史失败，也不代替无诊断钩子的完整套件。未进行 CI、正式认证、正式数据或真实业务写入。XLSX 沿用应用模板，分享前检查其中预置卖方信息。
