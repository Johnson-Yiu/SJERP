# C5 状态矩阵

被测源码 `0c463f6d739d07c14eca50ae4cce9135171b9cf1`。每一格均在对应的真实 Chrome 组合实际执行。

| 状态 | 1366 / 100% | 1366 / 125% | 1440 / 100% | 1440 / 125% | 390 / 100% | 390 / 125% | 验收范围 |
|---|---|---|---|---|---|---|---|
| CRM-01 | PASS | PASS | PASS | PASS | PASS | PASS | 只读界面、关闭回列表 |
| CRM-02 | PASS | PASS | PASS | PASS | PASS | PASS | 拒绝保留两字段、真实重试与联系人读回 |
| CRM-03 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | 关联详情和返回内容通过，公共组件返回焦点为 BODY |
| CRM-04 | PASS | PASS | PASS | PASS | PASS | PASS | 重名提醒、拒绝保留、按钮可用与一次真实创建 |
| CRM-05 | PASS | PASS | PASS | PASS | PASS | PASS | 不同工作区草稿、附件、迟到读取与放弃确认 |
| NPD-01 | PASS | PASS | PASS | PASS | PASS | PASS | 待提交防重复、拒绝保留请求键、只增加一行 |
| NPD-02 | PASS | PASS | PASS | PASS | PASS | PASS | 真实 409、保留草稿、查看最新版本并重新处理 |
| NPD-03 | PASS | PASS | PASS | PASS | PASS | PASS | 取消、必填、作废、弱化状态与审计 |

实际视口依次为 1366×768、1440×900、390×844。每份逐例 JSON 还记录有效视口、DPR、截图和失败原因。

[1366-100](chrome/1366-100/run.json) · [1366-125](chrome/1366-125/run.json) · [1440-100](chrome/1440-100/run.json) · [1440-125](chrome/1440-125/run.json) · [390-100](chrome/390-100/run.json) · [390-125](chrome/390-125/run.json)

42 项通过，6 项因同一 CRM-03 焦点问题失败。独立 runner 返回失败，未覆盖该缺陷的通用 CI 不改变本矩阵。
