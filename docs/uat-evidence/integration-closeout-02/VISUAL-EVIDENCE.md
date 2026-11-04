# 关键页面截图与操作证据索引

- 任务：`INTEGRATION-CLOSEOUT-02`
- 起点及核对时HEAD：`8087f2c68b19a302a25e814ec8ce6113d91d4750`
- 截图：**187张**。逐图实际尺寸、格式、模式、EXIF/内嵌元数据、字节数、SHA256、源码SHA、操作/合成数据、路径和覆盖边界见 `visual-evidence.json`。
- 操作文件的字节数与SHA256见JSON的 `operation_artifacts`。
- 只核对磁盘证据；未重跑打印/Chrome/测试，未改前端，未提交。

## 截图批次

| 批次 | 数量 | 源码来源 | 覆盖边界 |
|---|---:|---|---|
| 实际IAB及日志面板 | 10 | 页面源前端 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`；附件图 `0914002b5d8b3c848b1a78d2cc6e0419764d9053`；日志面板含未提交变动，SHA `UNKNOWN` | 客户/跟进及70字节合成附件保存重开；development identity不证明员工认证。IAB窄屏首页原图375×812。 |
| Chrome路由访问 | 26 | manifest记录HEAD `d6ebad3a6cd2358e0db14761c33ebbfaf34b0f50`；因未提交侧栏修复，生成源码 `UNKNOWN` | 13路由桌面/窄屏，仅导航；无pageerror。空态不支持正向闭环。 |
| CI 41829100528截图归档 | 124 | 候选 `1f189c3f74fda2908620dd3860230d860f1cbb43` | 124/124逐项manifest字节和SHA吻合。该次Frontend 268通过、2失败、0跳过；ISS039快照失败不能被截图抵消。 |
| 财务Chrome旧运行 | 6 | 关联固定来源 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`；生成checkout未记录，SHA `UNKNOWN` | 合成双用户审批/过账/核对重开及匿名账户事实；不证明业务登录或真实员工。 |
| 最终CI财务截图 | 6 | CI 41839476121，生成源码SHA `8087f2c68b19a302a25e814ec8ce6113d91d4750` | 归档6张真实Chrome截图；suite summary `allPassed=true`，9条命令均exit 0。仅为8087版本，不代表后续906财务后台修复的新画面。 |
| 历史Chrome | 5 | 关联历史来源 `a0729a0965850028fe52f5b6fcc3e825f23b1289`；运行SHA `UNKNOWN` | 首次合成审批/执行首轮遇外部字体网络拒绝；后续截图重开同一applicationId=1，不是新审批。 |
| ISS039修复后Chrome | 10 | 关联候选应用 `1f189c3f74fda2908620dd3860230d860f1cbb43`、helper参考 `03b524d`；精确组合SHA `UNKNOWN` | 隔离合成SQLite/Media定向截图；不能抵消旧CI失败，也不替代完整CI。 |

实际Chrome类别共 **179** 张；IAB/Chrome及CI来源逐图分别标明。187张图像全部可解码且均无EXIF条目；其中179张无内嵌metadata键，另8张JPEG仅报告标准JFIF相关info键。CI 41829100528旧ZIP内124张缺失或manifest哈希不匹配：**0**；新CI 41839476121选集21个成员也全部匹配长度和SHA。manifest的`artifact_sha256`绑定原始60MB GitHub归档（`adbe1f662425afb408fc84eb1b66b3407a3634a83735e935e6623249aea849bc`），紧凑选集归档由baseline-ci-log-manifest的`compact_evidence_sha256`绑定（`b0b4a1395d772e6dafe6246be78a3af41cc8507f8c27e1b053c0b6641240fbb8`）。主审重新计算两者各自摘要均匹配，并逐字节确认选集21个成员与原始归档一致；两种不同归档的摘要不同不构成完整性错误。图像未重编码。

## 操作与合成数据

- 客户/跟进：IAB中合成资料保存并重开；空列表只是空态。附件为70字节合成TXT，实际HTTP下载与原文件逐字节一致，见 `artifacts/ui-attachment-http-manifest.json`。
- 销售/采购/履约：sales、procurement、denials HTTP manifest，以及XLSX/CSV和数据库快照按JSON路径和hash登记。它们是隔离合成真实HTTP证据，不是Chrome逐步操作截图；synthetic session不证明业务login。
- 财务：合成maker/reviewer进行审批、过账、核对和保存重开；另有匿名事实页与实际CSV/PDF。凭证及HTTP文件均留哈希。无真实资金数据、真实员工身份或正式认证验收。
- 最终CI 41839476121另含6张来源SHA精确为`8087f2c68b19a302a25e814ec8ce6113d91d4750`的真实Chrome财务图：`account-facts-1440.png` 1440×1050、`account-facts-390.png` 390×2222、`reconciliation-completed-1440.png` 1440×1050、`reconciliation-completed-390.png` 390×1576、`reconciliation-reopened-1440.png` 1440×1050、`reconciliation-reopened-390.png` 390×1576（完整ZIP成员路径及逐图SHA在JSON）。归档suite summary为`allPassed=true`且9/9命令退出码0。这些只对应8087源码，不能代表后续`90683506f5d9447974302d83c89ba27351d5dfd4`财务后台修复后的截图；该修复没有新浏览器截图。
- 历史：关联DB快照记录12条来源、3条`not_connected`、0正式资金/库存履约事实。首次Chrome日志保留外部`fonts.googleapis.com`网络拒绝；重开是同一已执行申请。
- ISS039：修补后截图按两视口和五流程阶段索引，并链接HTTP/数据库快照及合成fixture。其定向证据独立于CI41829100528的2项失败。

## 结论边界

空页或空列表不支持正向业务闭环；CI截图不抵消同次CI失败；Chrome测试合成身份不等于ERP业务登录、真实员工、正式RBAC或部署验收。历史首轮Chrome有外部网络错误，后续是重开而非第二次审批。**本索引只是开发侧证据元数据与来源自查，不是ChatGPT独立复审；独立视觉复核仍待完成。**本轮未重跑打印，完整打印成品/分页仍依既有范围处理。最终CI财务截图精确来自8087，不能代表后续906财务后台改动。

最终核验时HEAD观察值为`90683506f5d9447974302d83c89ba27351d5dfd4`，与扫描开始时的起点不同；本索引依据起始`8087f2c68b19a302a25e814ec8ce6113d91d4750`采集，子任务未操作HEAD；该变化是主审提交统一财务修复9068350，归属明确且无前端改动。JSON记录了首末HEAD观察事实和后续核对，未把任何旧截图改称906生成。

JSON数组逐张记录187张截图和58项文件证据。原始日志/fixture路径保留；无法从运行记录锁定的生成源码SHA明确标为`UNKNOWN`，相关来源只作关联引用。
