# ISS-020 / ISS-022 / ISS-051 集成验收证据

日期：2026-10-26
统一基线：`28ba758388429f57c2e3516e12385a88ce6646a3`
集成分支：`codex/integration-020-022-051`

## 集成范围

| 任务 | 成果 | 本轮状态 |
|---|---|---|
| ISS-020 | `codex/iss-020-quote-export`，最终分支 SHA `13b453de019193ae45c4fa1e15724040329da594` | 已集成并补修金额口径 |
| ISS-022 | 本地 `codex/iss-022-procurement-moq`，本地最终 SHA `6e7aaedd2cccef3150a5c7ee3135fd5f37dcee47` | 远端分支不可见，未纳入集成，BLOCKED |
| ISS-051 | `codex/iss-051-environment-isolation`，最终分支 SHA `8a3c8a0a0a67f896f62483ece5551f7d32fb868b` | 已集成；保留 `DEPLOYMENT_VERIFICATION_PENDING` |

ISS-022 本地工作树和原有测试/截图证据均保留。多次 HTTPS 推送返回 HTTP 408，随后 `git ls-remote` 出现 TLS 握手失败；SSH 受主机密钥校验阻断，因此没有声称远端已成功。旧的 `codex/r1-moq-02` 未使用。

## 冲突与代码变更

- cherry-pick ISS-020/051 时只有 `docs/PROJECT_PHASES.md` 发生文档冲突。
- 解决方式是保留 ISS-020 与 ISS-051 两个完整阶段记录；未覆盖业务代码、迁移或测试。
- 集成分支没有纳入 ISS-022 的 `0086_purchase_moq_exception` 或其采购代码。
- ISS-020 补修仅涉及统一金额辅助函数、Quote/Order 总额和导出 DTO 的逐行分币舍入；未批量重算历史数据。

## ISS-020 独立复现

使用两行 `数量 1 × 单价 1.005`，并加入 EUR 运费 `0.025`、折扣 `0.005`：

```text
逐行金额：1.01 + 1.01 = 2.02
运费：0.03
折扣：0.01
最终总额：2.04 EUR
```

集成后的 Quote 模型、报价详情 API、报价工作台夹具、PI 预览 API、正式 XLSX 和转订单金额均按该结果对账。数据库仍保存高精度单价，金额计算采用 `ROUND_HALF_UP`，没有静默改写历史报价。

## 浏览器证据

本轮使用真实 Chrome 对集成前端执行报价工作台与 PI 预览桌面/窄屏回归。浏览器 UI 使用确定性 API 夹具；真实数据库/API/XLSX 对账见后端专项测试。

- `chrome-quote-workbench-1440.png`
- `chrome-quote-pi-1440.png`
- `chrome-quote-pi-700.png`
- `frontend/browser-tests/integration-020-051-evidence.spec.js`

## 部署边界

ISS-051 的开发环境兼容与生产配置拒绝测试保留；生产真实服务器、代理、Cookie/HTTPS、真实账号、PostgreSQL 仍为 `DEPLOYMENT_VERIFICATION_PENDING`。源分支记录的 GitHub Actions run `40264628939`（ISS-051）和 `40286651906`（ISS-020）均为失败且没有可见 job steps，不能作为 PASS。集成分支本轮尚未获得新的 CI/PostgreSQL 通过证据。

不合并 master，不正式部署，不自行关闭 Issue，等待独立审查。
