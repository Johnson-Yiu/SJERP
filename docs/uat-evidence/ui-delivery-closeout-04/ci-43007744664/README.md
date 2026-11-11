# CI 43007744664

被测源码 `c21a1060cb99bdf6bda33a07c7ba01b990f4878f`。Backend、PostgreSQL 17、前端单元、Node 和 Vitest 通过。完整浏览器作业 74 个隔离运行中 73 个通过、1 个失败，随后构建步骤跳过。

唯一失败为 `ui-final-state-customer-contact-03.spec.js`。1366×768 原生 100% 完成失败提示、恢复、客户和联系人保存。切换原生 125% 后，Linux 日志显示真实候选请求返回 200，错误提示未出现。失败快照显示新建表单中已有候选。分类为测试故障注入与导航的异步时序。旧截图属于通过的第一组，失败现场以 DOM 快照及逐例报告为准。该作业产物没有此用例的 trace 文件。

修复将故障路由注册提前到导航前，并显式等待失败 HTTP 400 和重试成功响应。保留全部六组、错误提示、真实保存与详情读回断言。本地 Chrome 六组通过。其余三个 U3 补交专项在原 CI 均实际完成，并继续进入新候选矩阵。

[失败作业及完整日志](https://github.com/Johnson-Yiu/SJERP/actions/runs/43007744664/job/130479348269) · [修后浏览器证据](../ci-repair/customer/chrome-customer-contact/run.json)
