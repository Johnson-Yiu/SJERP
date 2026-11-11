# CI 恢复与补测

2026-11-11 从 A3 `dd019e98f932668ae851dc0c4c7f602f888d51f9` 建立独立验收分支。H2 `84ea87801693d3b512ef28a76f684444af332685` 已在祖先链。E1-R2 `6242c5c3b85efdb3f904c8a4de7b8909a2bedcba` 和 E2-R2 `958421df61a2ac6dd9e66b685f2d0101e13321c5` 的末两条测试和证据增量已接收。

## 预验收

H3/U3 尚未完成和推送，当前工作属于预验收。

| 源码 | 工作流 | 已核对结果 |
| --- | --- | --- |
| `608e12039875e92b2edec22c692f702c7200d819` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735784) | media-fence、postgres-role-receipts、nginx-private-media 均成功 |
| `608e12039875e92b2edec22c692f702c7200d819` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735974) | Backend 成功；PG17 1,746 通过、35 跳过、2 失败；Frontend 卡在 Node 步骤后终止 |
| `387d2f7e0c2cc0ba6efc0096272ef349d3525f5d` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965389360) | 三个 job 均成功 |
| `387d2f7e0c2cc0ba6efc0096272ef349d3525f5d` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965389358) | Backend 成功、PG17 失败；Frontend 卡在 Node 步骤后终止 |
| `8b1cdd42481f37debe41d6d75cd8aa50d4b53edb` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42967610334) | 三个 job 均成功 |
| `8b1cdd42481f37debe41d6d75cd8aa50d4b53edb` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42967610341) | Frontend Node 步骤通过；Vitest 836 通过、2 失败，浏览器步骤未运行 |

[远端分支快照](remote-heads.tsv)、[Actions 记录](actions-runs.jsonl)和[分支清单](branch-inventory.csv)按远端分支头及精确 SHA 对照。无匹配运行表示当前快照中未查到该分支头的运行，另列同 SHA 异分支运行和带跳过指令的原提交。祖先关系来自 Git 提交图。242 个分支头中，105 个是候选祖先，2 个接收了已审来源及缺失增量，20 个与候选祖先完整文件树相同，27 个为等价非合并补丁序列，88 个仍需核对替代关系和交付范围。最终认证 SHA 和 run/job 列待实测填写。

旧资金草稿缺少可证明的账号及表单归属，现行行为保留旧记录并提示人工核对。旧草稿不会作为重试载荷。账号范围内的当前已提交待核对记录可重放原载荷。浏览器测试以网络请求为证据，后端使用真实数据库断言幂等。历史 A3 的 24 条逐例非通过记录以及后续 P2B 定向三项失败保留在[原报告](../release-integration-acceptance-03/README.md)。

本地 Vitest 91 套件、838 项全部通过。Node 首轮 196 通过、1 失败，旧工作流契约只接受原 Vitest 命令。同步三套件要求后全量 197/197。真实 Chrome 的 P2B 回归 8/8 通过，包含首次提交响应丢失后按原请求重放、放弃后新表单使用新键、旧草稿跨账号不自动恢复和零自动写入。[逐例对照](cash-case-reconciliation.json)

E2 采购收货原证据记录了取消后焦点未恢复。修复后将焦点返回「验货入库」按钮，并将浏览器观测改为必过断言。真实 Chrome 156 在隔离库跑通组合收货、验证失败取消、重复提交保护和冲销，人工复看 390×844、125% 截图。[焦点截图](purchase-receipt-focus-390-125.png)

验货入库事件携带原触发按钮以恢复焦点。CI 中两个组件断言发现事件已增加该参数，定向更新后 11/11 通过，仍严格核对原采购对象和明细。Linux Node 步骤的静默子进程修复后，CI 已能完成 Node 并进入 Vitest。

E1 扩展 8、9、10 和 E2 库存操作、组合收货均在隔离库的真实 Chrome 预验收通过。严格刷新模式通过。销售旅程首次严格执行发现两段附件用例复用同名样本，重试场景改用独立文件并断言重开后只新增一条。此修复以重跑结果核对。

PG17 首轮两项失败分别为归档商品清单的未声明排序，以及会话认证挑战下匿名请求的预期。测试保留商品项、数量、关联及汇总断言，并明确断言匿名 401 和 Session 挑战。两项在本地 SQLite 定向通过，PG17 待相应新候选验证。GitHub 隔离浏览器组使用每个隔离运行随机生成的临时测试凭据。

实际下载专项在真实 Chrome 8/8 通过。核对销售订单导入模板的工作簿结构、错误 CSV 的 BOM 与 SKU 提示、历史预检 CSV 的最新批次，以及财务 CSV 的核准非现金抵减行。保留四个合成样本和 SHA-256。[导出校验](preflight-export-manifest.json)

完整打印成品及分页继续按原延期处理。
