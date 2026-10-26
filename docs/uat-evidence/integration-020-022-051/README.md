# ISS-020 / ISS-022 / ISS-051 集成验收证据

日期：2026-10-26
统一基线：`28ba758388429f57c2e3516e12385a88ce6646a3`
集成分支：`codex/integration-020-022-051`

## 三项成果与最终集成

| 任务 | 原任务最终 SHA | 集成状态 |
|---|---|---|
| ISS-020 | `13b453de019193ae45c4fa1e15724040329da594` | 已集成，并补修历史金额兼容性 |
| ISS-022 | `6e7aaedd2cccef3150a5c7ee3135fd5f37dcee47` | 已从本地已验证提交集成；独立分支推送仍受 GitHub TLS 阻断 |
| ISS-051 | `8a3c8a0a0a67f896f62483ece5551f7d32fb868b` | 已集成；保留 `DEPLOYMENT_VERIFICATION_PENDING` |

本轮集成提交在本报告生成前仍待最终提交。最终 SHA、远端分支可见性和 CI run 会在提交后补入本文件及 `TEST_LOG.md`；不以本地 SHA 冒充远端交付。

## ISS-022：已确认并集成

独立分支的原有证据和本地提交经过核对后，直接 cherry-pick `6e7aaedd...`，没有重新开发 MOQ。唯一冲突是 `docs/PROJECT_PHASES.md` 的文档并行更新；保留 ISS-020、ISS-051 原记录并加入 ISS-022 记录，没有覆盖业务代码。

集成包含接续 `0085` 的 `0086_purchase_moq_exception`，没有删除、覆盖或改写已发布迁移。采购计划及真实 PO 按同供应商来源、同 SupplierSKU/适用 SKU 和基础单位合计；交易单位先准确换算；没有可靠 MOQ 时不提示；低于 MOQ 可以保存草稿，但正式下单首次返回 `purchase_moq_exception_required`，填写原因后保存原因、明细快照、时间、采购单和已认证操作员。没有自动补量、虚假数量、价格或内部参考成本改写，也没有改变采购生命周期。

真实 Chrome 采购回归的 `browser-log.json` 记录：等于 MOQ 下单 201；低于 MOQ 首次 400；取消后仍为草稿；补充例外原因后 200；详情展示例外审计；`status=ordered` 筛选请求 200；窄屏无横向溢出。截图见：

- [低于 MOQ 与单位换算提示](iss022-browser-final/04-low-moq-conversion-warning.png)
- [已下单采购单的 MOQ 例外审计](iss022-browser-final/07-moq-exception-persisted.png)
- [窄屏采购列表](iss022-browser-final/09-narrow-purchase-list.png)
- [浏览器网络日志](iss022-browser-final/browser-log.json)

独立分支多次 HTTPS 推送分别遇到 HTTP 408 和 TLS 握手失败；`git ls-remote`/GitHub API 在该传输故障期间不能证明独立分支可见。旧的 `codex/r1-moq-02` 未使用。本轮仅在集成分支保留这份本地已验证成果，最终推送结果单独报告。

## ISS-020：历史金额兼容性已补修

先在隔离 SQLite 复现了真实缺口：两行 `数量 1 × 单价 1.005` 的既有正式记录按旧算法为 `2.010`，而无兼容保护的当前派生值会变成 `2.02`；历史付款计划仍为 `2.0100`。这会使历史正式订单派生总额与付款计划不一致，属于已确认兼容性缺陷。

最小修复新增 `0087_amount_calculation_compatibility`：

- 旧正式 Quote/Order 保留版本 1，继续使用迁移前金额公式；不重算数据库金额、付款计划、汇率或应收事实。
- 新草稿/正式确认后的新单据使用版本 2 的逐行 `ROUND_HALF_UP` 口径。
- 已存在的正式报价被接受时不改写旧事实；尚未正式确认的草稿在确认时切换到当前口径。
- 内部版本字段不暴露为公开 API 字段；旧 API 键和权限保持不变。
- 正式 XLSX 对旧版本保留旧计算口径，对新版本使用当前统一口径。

新口径样本为：两行 `1.005` 得行金额 `1.01 + 1.01 = 2.02`；EUR 运费 `0.025`、折扣 `0.005` 分别为 `0.03`、`0.01`，最终 `2.04 EUR`。Quote 模型、详情 API、PI API、XLSX 和转销售订单均已对账。合同数量变更只生成预览差异，不修改旧付款计划。

## 浏览器证据

真实 Chrome 报价回归断言工作台显示 `EUR 2.04`、保存的 PI 预览显示 `2.04`，并完成 1440px 与 700px 视口。仓库内原有报价截图保留，另有本轮新截图保存在本机受控证据目录；由于 Windows 文件句柄拒绝覆盖仓库内旧报价图，未删除或覆盖原图。

- [报价工作台 1440px](chrome-quote-workbench-1440.png)
- [报价 PI 预览 1440px](chrome-quote-pi-1440.png)
- [报价 PI 预览 700px](chrome-quote-pi-700.png)
- `frontend/browser-tests/integration-020-051-evidence.spec.js`

采购真实 Chrome 使用隔离 SQLite、隔离媒体目录和当前集成前端/后端；报价页面使用确定性 API 夹具，数据库/API/XLSX 对账以 Django 专项测试为准。

## ISS-051 与部署边界

ISS-051 的配置隔离、开发身份和生产默认值拒绝逻辑保持不变；没有打开正式 RBAC、没有写入真实生产密钥、没有部署生产。真实生产服务器、反向代理 HTTPS、Cookie/HSTS、真实账号、PostgreSQL 以及 GitHub Actions 的可见成功步骤仍是 `DEPLOYMENT_VERIFICATION_PENDING`，不能将本地通过标记为 CI 或生产 PASS。

不合并 master，不正式部署，不自行关闭 Issue，等待独立审查。
