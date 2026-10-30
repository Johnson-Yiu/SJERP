# A — ISS-006 前端幂等键存储异常

- 统一基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 新分支：`codex/r1-iss006-frontend-idempotency-bd324-20261030`
- 来源工作树：`codex/r1-iss006-frontend-idempotency-20261029`，原 HEAD `74b1ac29e85a80efbc0ed2200a1653ad19b4bfae`
- 迁移范围：仅幂等请求身份工具及履约收货/发货相关前端测试；未迁移旧分支文档或基线之外代码。

## 验收

使用 `frontend/package-lock.json` 执行 `npm ci`。验证 sessionStorage 属性读取异常、`getItem`/`setItem` 失败时保持安全停止、存储恢复后沿用同一请求身份、重复请求重放、请求内容变化生成新身份及成功后清理身份。

- 定向 Vitest：3 个文件，39 项通过。
- Node 单元测试：171 项通过，0 失败。
- `npm run build`：通过；构建工具报告现有主 bundle 超过 500 kB 的体积警告，不影响构建成功。

原始命令输出位于 `logs/`：`npm-ci.log`、`vitest-targeted.txt`、`node-unit.log`、`build.log`。Vitest 末尾空白已在转录时规范化；Node/npm 版本与锁文件安装输出见 `npm-ci.log`。

未连接生产服务；未运行 GitHub Actions。
