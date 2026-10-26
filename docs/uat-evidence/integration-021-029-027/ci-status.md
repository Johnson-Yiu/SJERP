# CI / GitHub Actions 状态核实

核实时间：2026-10-26。

## 当前读取结果

使用仓库配置的 `origin`：`https://github.com/Johnson-Yiu/SUNJACK-ERP.git`。

- `gh auth status`：本地 `Johnson-Yiu` token 无效，提示需要重新登录。
- `gh run list --limit 10 ...`：GitHub API 返回 HTTP 404；随后 `gh repo view` 返回 HTTP 401 `Requires authentication`。
- 因当前凭证失效，不能把本轮最终 SHA 的 CI 运行状态说成已读取，也不能据此确认新的 billing 结果。

## 已有可核实额度阻断证据

仓库既有 ISS-021/ISS-029 精确任务证据记录：

- [ISS-021 CI run 40257290673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40257290673)
- 原始注释说明三个 job 在启动步骤前未启动，原因是近期付款失败或 spending limit 需要提高。

本轮没有修改账户、支付方式、额度或 GitHub Actions workflow，也没有用本地通过结果冒充 CI/PostgreSQL 通过。待仓库所有者恢复 GitHub 凭证和 Actions 额度后，应针对最终集成 SHA 重跑 `backend`、`frontend`、`backend-postgres`。
