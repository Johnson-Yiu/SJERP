# CI 恢复与补测

2026-11-11 从 A3 `dd019e98f932668ae851dc0c4c7f602f888d51f9` 建立独立验收分支。H2 `84ea87801693d3b512ef28a76f684444af332685` 已在祖先链。E1-R2 `6242c5c3b85efdb3f904c8a4de7b8909a2bedcba` 和 E2-R2 `958421df61a2ac6dd9e66b685f2d0101e13321c5` 的末两条测试和证据增量已接收。

## 预验收

以下为接收 H3/U3 前的历史预验收记录。

| 源码 | 工作流 | 已核对结果 |
| --- | --- | --- |
| `608e12039875e92b2edec22c692f702c7200d819` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735784) | media-fence、postgres-role-receipts、nginx-private-media 均成功 |
| `608e12039875e92b2edec22c692f702c7200d819` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735974) | Backend 成功；PG17 1,746 通过、35 跳过、2 失败；Frontend 卡在 Node 步骤后终止 |
| `387d2f7e0c2cc0ba6efc0096272ef349d3525f5d` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965389360) | 三个 job 均成功 |
| `387d2f7e0c2cc0ba6efc0096272ef349d3525f5d` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965389358) | Backend 成功、PG17 失败；Frontend 卡在 Node 步骤后终止 |
| `8b1cdd42481f37debe41d6d75cd8aa50d4b53edb` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42967610334) | 三个 job 均成功 |
| `8b1cdd42481f37debe41d6d75cd8aa50d4b53edb` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42967610341) | Frontend Node 步骤通过；Vitest 836 通过、2 失败，浏览器步骤未运行 |

[远端分支快照](remote-heads.tsv)、[Actions 记录](actions-runs.jsonl)和[分支清单](branch-inventory.csv)按远端分支头及精确 SHA 对照。无匹配运行表示当前快照中未查到该分支头的运行，另列同 SHA 异分支运行和带跳过指令的原提交。祖先关系来自 Git 提交图。242 个分支头中，105 个是候选祖先，2 个接收了已审来源及缺失增量，20 个与候选祖先完整文件树相同，27 个为等价非合并补丁序列，25 个仅包含历史证据，6 个分支所改的非证据路径与候选一致，57 个仍需核对差异和交付范围。另按 2026-11-04 起的远端提交逐条列出原始 CI、等价补丁或已知替代关系。[逐提交清单](recent-commit-inventory.csv)

旧资金草稿缺少可证明的账号及表单归属，现行行为保留旧记录并提示人工核对。旧草稿不会作为重试载荷。账号范围内的当前已提交待核对记录可重放原载荷。浏览器测试以网络请求为证据，后端使用真实数据库断言幂等。历史 A3 的 24 条逐例非通过记录以及后续 P2B 定向三项失败保留在[原报告](../release-integration-acceptance-03/README.md)。

本地 Vitest 91 套件、838 项全部通过。Node 首轮 196 通过、1 失败，旧工作流契约只接受原 Vitest 命令。同步三套件要求后全量 197/197。真实 Chrome 的 P2B 回归 8/8 通过，包含首次提交响应丢失后按原请求重放、放弃后新表单使用新键、旧草稿跨账号不自动恢复和零自动写入。[逐例对照](cash-case-reconciliation.json)

E2 采购收货原证据记录了取消后焦点未恢复。修复后将焦点返回「验货入库」按钮，并将浏览器观测改为必过断言。真实 Chrome 156 在隔离库跑通组合收货、验证失败取消、重复提交保护和冲销，人工复看 390×844、125% 截图。[焦点截图](purchase-receipt-focus-390-125.png)

验货入库事件携带原触发按钮以恢复焦点。CI 中两个组件断言发现事件已增加该参数，定向更新后 11/11 通过，仍严格核对原采购对象和明细。Linux Node 步骤的静默子进程修复后，CI 已能完成 Node 并进入 Vitest。

E1 扩展 8、9、10 和 E2 库存操作、组合收货均在隔离库的真实 Chrome 预验收通过。严格刷新模式通过。销售旅程首次严格执行发现两段附件用例复用同名样本，重试场景改用独立文件并断言重开后只新增一条。后续修正恢复顺序和控件定位，真实 Chrome 严格旅程通过，228 张截图，0 项未完成。

PG17 首轮两项失败分别为归档商品清单的未声明排序，以及会话认证挑战下匿名请求的预期。测试保留商品项、数量、关联及汇总断言，并明确断言匿名 401 和 Session 挑战。两项在本地 SQLite 定向通过，PG17 待相应新候选验证。GitHub 隔离浏览器组使用每个隔离运行随机生成的临时测试凭据。

实际下载专项在真实 Chrome 8/8 通过。核对销售订单导入模板的工作簿结构、错误 CSV 的 BOM 与 SKU 提示、历史预检 CSV 的最新批次，以及财务 CSV 的核准非现金抵减行。保留四个合成样本和 SHA-256。[导出校验](preflight-export-manifest.json)

完整打印成品及分页继续按原延期处理。


## H3 和 U3 集成

- H3 接收 `ab8c8a62451f4a0b8ae61811d8c354bfd30d5146`，原分支 [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965318197)。
- U3 接收 `e8096616bf227ed242cf837a78fb87fd0736b87c`，原分支 [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965642393)。
- 初次合并冻结点 `17ecdcb8af94779e43c75c5adefb03de07d3c6b7` 采用 U3 的采购收货焦点和键盘处理，同时断言触发按钮、采购对象和收货明细。集成定向 Vitest 30/30，H3 390px 在 100% 和 125% 的 Chrome 验收均通过，U3 联系人恢复、详情及批次、SKU 和收货四项独立运行均通过。[截图和实际导出](integrated-chrome-samples/manifest.json)
- 初次合并 [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42969289222) 的 Backend 和 PostgreSQL 17 通过，Frontend 的 Node SKU 图片重试旧夹具失败，Vitest 与 Playwright 步骤未执行。[Linux 专项](https://github.com/Johnson-Yiu/SJERP/actions/runs/42969289251) 三项通过。
- 修正 SKU Node 夹具后 `85e2bcb8c6bfcbe31024f431d318bcb71c17a03b` 通过 [Linux 专项](https://github.com/Johnson-Yiu/SJERP/actions/runs/42969691020) 三项。[主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42969690828) 已确认绑定此 SHA。


合并后的本地全量诊断记录到 390px 资金台账下载在 HTTP 200 后取消。延长 Blob URL 的保留时间后，真实 Chrome 在 1440px 和 390px 均完成下载并验证 CSV。浏览器截图写入本次运行证据目录，历史报告图片已恢复为提交中的原样。原有成品打印用例移用本次隔离运行的短路径，Windows Chrome 已能启动，但实际 PDF 生成仍未验证，保留原延期范围及失败日志。


二次核对远端后，冻结时接收 H3 `1c478b0aa298d53ffca03a38d4200b0d122b27ea` 和 U3 `d65aca7a5e832a3108e19c1c63e5a5e548ee8542`。H3 将原始快照不变性按主键对照。U3 增加附件删除失败后继续编辑、采购焦点回退和销售退货回读。新增销售退货用例由独立配置执行。[远端快照](remote-heads-after-h3-u3.tsv)

`3adcc61afa9318fc0b86c45e4308cf866f9173eb` 的真实 Chrome 导出专项 8/8，四份实际样本留档。[样本及校验](final-exports-3adcc61a/manifest.json)


`1afd122e7060e8c7007f54914ba2f01f1c975f8c` 的最新 U3 联系人及附件失败恢复、销售退货、采购收货三个真实 Chrome 专项通过。H3/U3 集成定向 Vitest 30/30、后端定向 2/2。[附件失败窄屏截图](integrated-chrome-samples/attachment-delete-failed-390-125.png)

ISS-007 报价导出也复现了下载取消。延长报价 Blob URL 的保留时间后，真实 Chrome 完成报价及订单图片快照链路并重新下载带图片的 XLSX。[文件校验](integrated-chrome-samples/quote-download-check.json)


导入模板下载也复现了同类取消。现将导入、报价、装箱单、财务和历史报表的下载统一复用同一 Blob 保存逻辑，保留各自的文件名、内容及过期请求保护。修复后本地 Vitest 841/841、Vite 构建、真实 Chrome 销售导入与实际导出 8/8。


已完成的早期主 CI `a5d23e86c1b74137c86a8d006edf1daf1a2ae89b` 共 357 个浏览器用例通过、3 个按原夹具条件跳过。[逐例对照](preflight-a5d23e86-browser-cases.json) 中，A3 旧逐例 JSON 的 24 个非通过用例有 23 个复验通过，剩余 1 个因夹具条件跳过。新运行矩阵显式配置基础、跟进和完整夹具。后两个配置需要实际执行相关历史财务、原生缩放和完整交付用例。基础或跟进配置中的条件跳过由对应完整配置复验，单独计数。

`85e2bcb8c6bfcbe31024f431d318bcb71c17a03b` 的主 CI 终态为两个后端 job 通过、Frontend 失败。销售旅程在响应式重排时丢失滚动目标，E2 收货在浏览器应用缩放前读取了 DPR。`3adcc61afa9318fc0b86c45e4308cf866f9173eb` 的主 CI 也记录了 E2 和 U3 两套收货用例的缩放竞态。修复后的严格销售旅程、E2 收货和 U3 收货分别用真实 Chrome 跑通，各保留原有可见性、缩放和业务断言。[较早主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42969690828) · [收货失败主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42972261637)

`7dcf4fa4045ced161232ce894de2fd2f9f533cbc` 的 SQLite 1,666 通过、117 跳过，PostgreSQL 17 1,748 通过、35 跳过，Frontend 及 Linux 专项三个 job 均通过。Playwright 共 69 个配置，385 项通过、4 次按夹具条件跳过；对应的三个用例在完整夹具均通过。A3 逐例 JSON 的 24 个历史非通过用例均找到复验通过记录。真实 Chrome 的销售导入完整夹具 11/11，H3 390px、125% 通过，下载保留原文件和结构校验。[逐例结果](browser-7dcf4fa4-cases.json) · [实际文件及校验](certification-7dcf4fa4/verified-downloads/manifest.json) · [主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42976812877) · [Linux 专项](https://github.com/Johnson-Yiu/SJERP/actions/runs/42976812583)

更新后的远端快照共 244 个分支头。对原先待核对的 57 个分支逐路径追查后，8 个分支的每个差异文件版本均在候选祖先中有凭证。5 个由 A3 接收记录、后续实现及对应测试核对接续范围。另有 5 个 ISS-052 中间版本已由导入限额、审计来源、PostgreSQL 三张审计表和迁移回退的后继实现接续。其余 39 个仍有未匹配路径，其中 1 个原 SHA 已有两次完整 CI 成功。对剩下的 38 个，清单保留原始 CI、差异路径和已知后继，待核实仍需交付的差异后独立补验。[分支清单](branch-inventory.csv) · [差异路径和祖先凭证](historical-path-witnesses.json)

## 冻结候选 `7e99a5d394ddc0d96a3af04b74686307f754ca08`

H3 `1c478b0aa298d53ffca03a38d4200b0d122b27ea` 和 U3 `d65aca7a5e832a3108e19c1c63e5a5e548ee8542` 均为该候选的祖先。工作流由验收分支正常推送触发。

| 检查 | 结果 | Job |
| --- | --- | --- |
| Backend | 1,666 通过，117 跳过，0 失败 | [130389465694](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478188/job/130389465694) |
| Backend PostgreSQL 17 | 1,748 通过，35 跳过，0 失败 | [130389466023](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478188/job/130389466023) |
| Frontend | Node 197 + 1 通过，Vitest 91 套件 841 项通过，Playwright 全量和 Vite 构建通过 | [130389466108](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478188/job/130389466108) |
| Linux Nginx 私有媒体 | 通过 | [130389465901](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478124/job/130389465901) |
| Linux PostgreSQL 角色与签名回执 | 通过 | [130389466190](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478124/job/130389466190) |
| Linux 媒体栅栏 | 通过 | [130389466600](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478124/job/130389466600) |

Playwright 共 69 个配置，385 项通过、4 次条件跳过，0 失败，0 项因失败未运行。基础夹具跳过历史资金双人复核、长财务/历史记录原生缩放、完整交付流程各一次；跟进夹具再跳过完整交付流程一次。三项都在同一 SHA 的完整夹具中实际通过。A3 逐例 JSON 的 24 个历史非通过用例均在本轮找到通过结果，其中包括原报告最后保留的 3 项资金草稿用例。[冻结候选逐例和原始日志行号](browser-7e99a5d3-log-cases.json)

真实 Chrome 销售导入完整夹具 11/11，H3 窄屏 125% 1/1。实际下载校验覆盖销售模板工作簿、含 SKU 说明的错误 CSV、历史预检仅含最新选中文件来源、资金报表的非现金抵减，以及历史商品 CNY 200.00、USD 15.00 的独立合计。[实际下载及校验](certification-7e99a5d3/verified-downloads/manifest.json) · [客户编辑截图](certification-7e99a5d3/screenshots/sales-contact-saved-390-125.png) · [采购收货焦点截图](certification-7e99a5d3/screenshots/u3-receipt-focus-390-125.png) · [历史商品关联截图](certification-7e99a5d3/screenshots/h3-candidate-selected-390-125.png)

较早的 Windows SQLite 详细诊断发现两套签名回执测试因进程路径中缺少 OpenSSL 而未启动。将本机已有的 Git OpenSSL 加入该次运行的进程路径后，在冻结候选定向重跑，两套共 15/15 通过。Windows 的环境专属逐例跳过依据单列，GitHub Ubuntu SQLite 的跳过数来自其原始汇总。[Windows 诊断逐例跳过](skips-24de1013.json) · [冻结候选 PostgreSQL 17 逐例跳过](skips-7e99a5d3-pg17.json)

[主 CI 原始运行](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478188) · [Linux 专项原始运行](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478124) · [Playwright 原始产物](https://github.com/Johnson-Yiu/SJERP/actions/runs/42980478188/artifacts/13839269697)

本次认证适用于冻结源码和隔离环境。完整打印成品及分页仍按原范围延期，已执行的自动打印回归保留。正式部署、真实数据导入和正式员工权限启用未执行。
