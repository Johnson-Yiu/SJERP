# CI 恢复与补测

2026-11-11 从 A3 `dd019e98f932668ae851dc0c4c7f602f888d51f9` 建立独立验收分支。H2 `84ea87801693d3b512ef28a76f684444af332685` 已在祖先链。E1-R2 `6242c5c3b85efdb3f904c8a4de7b8909a2bedcba` 和 E2-R2 `958421df61a2ac6dd9e66b685f2d0101e13321c5` 的末两条测试和证据增量已接收。

## 预验收

| 源码 | 工作流 | 已核对结果 |
| --- | --- | --- |
| `608e12039875e92b2edec22c692f702c7200d819` | [Linux operations acceptance](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735784) | media-fence、postgres-role-receipts、nginx-private-media 均成功 |
| `608e12039875e92b2edec22c692f702c7200d819` | [CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/42963735974) | 记录见 GitHub 对应 run；最终认证待 H3、U3 接收后冻结 |

[远端分支快照](remote-heads.tsv)、[Actions 记录](actions-runs.jsonl)和[分支清单](branch-inventory.csv)按远端分支头及精确 SHA 对照。无匹配运行表示当前快照中未查到该分支头的运行。祖先关系来自 Git 提交图。其他分支仍需核对等价补丁、替代关系和继续交付范围。最终认证 SHA 和 run/job 列待实测填写。

旧资金草稿缺少可证明的账号及表单归属，现行行为保留旧记录并提示人工核对。旧草稿不会作为重试载荷。账号范围内的当前已提交待核对记录可重放原载荷。浏览器测试以网络请求为证据，后端使用真实数据库断言幂等。历史 A3 的 24 条逐例非通过记录以及后续 P2B 定向三项失败保留在[原报告](../release-integration-acceptance-03/README.md)。

完整打印成品及分页继续按原延期处理。
