# CI 恢复与补测

2026-11-11 从 A3 `dd019e98f932668ae851dc0c4c7f602f888d51f9` 建立独立验收分支。H2 `84ea87801693d3b512ef28a76f684444af332685` 已在祖先链。E1-R2 `6242c5c3b85efdb3f904c8a4de7b8909a2bedcba` 和 E2-R2 `958421df61a2ac6dd9e66b685f2d0101e13321c5` 的末两条测试和证据增量已接收。

## 预验收

H3/U3 尚未完成和推送，当前工作属于预验收。

| 源码 | 工作流 | 已核对结果 |
| --- | --- | --- |
| `608e12039875e92b2edec22c692f702c7200d819` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735784) | media-fence、postgres-role-receipts、nginx-private-media 均成功 |
| `608e12039875e92b2edec22c692f702c7200d819` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735974) | Backend 成功；PG17 和 Frontend 尚无已核对终态 |
| `387d2f7e0c2cc0ba6efc0096272ef349d3525f5d` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965389360) | 三个 job 均成功 |
| `387d2f7e0c2cc0ba6efc0096272ef349d3525f5d` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42965389358) | 已验证由本次分支推送触发，尚无已核对终态 |

[远端分支快照](remote-heads.tsv)、[Actions 记录](actions-runs.jsonl)和[分支清单](branch-inventory.csv)按远端分支头及精确 SHA 对照。无匹配运行表示当前快照中未查到该分支头的运行。祖先关系来自 Git 提交图。242 个分支头中，105 个是候选祖先，2 个接收了已审来源及缺失增量，20 个与候选祖先完整文件树相同，27 个为等价非合并补丁序列，88 个仍需核对替代关系和交付范围。最终认证 SHA 和 run/job 列待实测填写。

旧资金草稿缺少可证明的账号及表单归属，现行行为保留旧记录并提示人工核对。旧草稿不会作为重试载荷。账号范围内的当前已提交待核对记录可重放原载荷。浏览器测试以网络请求为证据，后端使用真实数据库断言幂等。历史 A3 的 24 条逐例非通过记录以及后续 P2B 定向三项失败保留在[原报告](../release-integration-acceptance-03/README.md)。

本地 Vitest 91 套件、838 项全部通过。真实 Chrome 的 P2B 回归 8/8 通过，包含首次提交响应丢失后按原请求重放、放弃后新表单使用新键、旧草稿跨账号不自动恢复和零自动写入。[逐例对照](cash-case-reconciliation.json)

E2 采购收货原证据记录了取消后焦点未恢复。修复后将焦点返回「验货入库」按钮，并将浏览器观测改为必过断言。真实 Chrome 156 在隔离库跑通组合收货、验证失败取消、重复提交保护和冲销，人工复看 390×844、125% 截图。[焦点截图](purchase-receipt-focus-390-125.png)

完整打印成品及分页继续按原延期处理。
