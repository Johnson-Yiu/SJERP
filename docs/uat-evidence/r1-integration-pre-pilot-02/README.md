# R1-INTEGRATION-PRE-PILOT-02 综合验收（未封版）

## 来源和集成

2026-10-29 从 GitHub 重新核实六个分支 HEAD，均与指定值一致。按 B、C、D、E、F 顺序合并到 A，合并完成提交为 `c771ec3468b84242804b7533053d4630072cf5a9`；修复测试后的最终代码提交为 `1a9d69fa0a8a375160ddb3f5b7d54cd51ca8e708`。本报告作为后续文档提交记录验收。

| 来源 | SHA |
| --- | --- |
| A | `54e715bdc568b80ba624186fecd866550676cf38` |
| B | `dfa36058206fe7021ff6e6192fbbd247fb471947` |
| C | `0fb8f09e344b319a02a86a3ded38deb3d37f5afe` |
| D | `f82554686478f62e3a60ed69bb4144e8c052ac7c` |
| E | `58577c809168a36c5b8f0d331b795d4c8d11f9f2` |
| F | `5499da5a80029233fb38e8101c2cfca0adecbece` |

## 冲突和重点检查

- `ProductPage.vue`：实际冲突；保留分类各层级可选择行为，并合入附加分类提示及其他自动合并文案。
- `ResourcePage.vue`：实际冲突由行尾格式导致全文件冲突；以 ISS-007 版本保留待上传文件、保存后失败重试和附件处理，再加入客户、联系人、跟进空状态文案。
- `PurchaseOrderPage.vue`：自动合并；保留收货 `request_key` 和采购文案。ISS-006 后端指纹及事务逻辑来自 B。
- `overview-reports.spec.js`：自动合并；保留新权限文案、限制来源请求、隐藏导出按钮和财务入口的原断言。
- `resourceConfigs.js`：自动合并；基础及财务、库存配置均纳入。
- `PROJECT_ISSUES.md`、`PROJECT_PHASES.md`、`requirements.txt`、`requirements.lock`：与 A 相比无变化。
- `0090_fulfillment_request_idempotency.py`：保留 B 迁移，依赖 `0089_operationlog_operator_protect`，包含收货及发货请求键和指纹；模型一致性检查通过，SQLite 迁移成功。PostgreSQL 实际迁移仍待验证。
- 两份来源验收 README 的 Markdown 行尾空格作格式修正，未改变历史验收含义。

## 集成版验证

| 状态 | 检查 | 实际结果 |
| --- | --- | --- |
| PASS | Python 3.12.14 安装 `requirements.lock`、`pip check` | 安装成功，依赖检查通过；`typing-extensions` 为 3.12 条件依赖 |
| PASS | Django `check`、`makemigrations --check --dry-run` | 无系统检查问题、无模型迁移差异 |
| PASS | Python 3.12 全量 Django 测试（SQLite） | 1011 项：993 passed、0 failed、18 skipped；运行 491.703 秒，跳过项不能替代 PostgreSQL 验证 |
| PASS | SQLite 隔离迁移 | 应用至 CRM 0090，`migrate --check` 通过 |
| PASS | `crm.tests.test_iss006_pre_uat` | Python 3.12、内存 SQLite：3 passed、0 failed、0 skipped；不替代 PostgreSQL 并发验证 |
| PASS | `test_sku_images`、`test_customer_h1`、`test_product_category_sku_identity_safety` | Python 3.12、内存 SQLite：34 passed、0 failed、0 skipped，覆盖图片、跟进附件和分类 SKU 安全 |
| PASS | `npm ci` | 安装成功，audit 0 vulnerabilities；有 glob 与 lucide 废弃警告 |
| PASS | `npm run test:unit` | 169 passed、0 failed、0 skipped |
| PASS | `node --test tests/detail-drawer-typography.spec.js` | 1 passed、0 failed、0 skipped |
| PASS | `node --test tests/ux-copy-sales-purchase.spec.js` | 3 passed、0 failed、0 skipped；该文件被 Vitest 收集时另有失败，见下文 |
| FIX REQUIRED | CI 的 Vitest 命令，修复前 | 655 passed、9 failed；70 文件中 61 passed、9 failed，其中 3 个文件没有 Vitest suite。详见下文 |
| PASS | 修复过期文案和无障碍选择器后的 6 个 Vitest 文件 | 79 passed、0 failed |
| FIX REQUIRED | CI 的 Vitest 命令，修复后重跑 | Vitest 664 passed、0 failed；但 70 文件中 67 passed、3 failed，Node 测试被错误收集并另报 3 项 `ERR_INVALID_URL_SCHEME`；命令退出码 1 |
| PASS | 修正测试运行器归属后重跑 CI 的 Vitest 命令 | 68 文件、667 passed、0 failed、0 skipped；退出码 0 |
| PASS | 隔离基础设施 Playwright smoke | 1 passed、0 failed；Node 基础设施测试包含在上述 `test:unit` 中 |
| PASS | 隔离 `overview-reports.spec.js` | 16 passed、0 failed，包含受限来源和导出权限 |
| PASS | 隔离 `inventory-ux.spec.js` | 9 passed、0 failed |
| PASS | 隔离 `product-master-ux.spec.js` | 19 passed、0 failed |
| PASS | `npm run build` | 构建成功；主 JS 1,130.04 kB，仍有超过 500 kB chunk 的警告 |
| BLOCKED | 全量 Playwright | 未执行：存在硬编码本机 55154 和默认 55208 的真实 API 测试，不能保证不连接已有服务；隔离 runner 当前只允许单文件选择 |
| BLOCKED | PostgreSQL | 未发现 PostgreSQL 服务、客户端或 Docker；PostgreSQL 迁移与并发验收未执行 |
| NEEDS VERIFICATION | 全量视觉验收 | 本次尚未完成集成版桌面与窄屏截图；不得把来源分支截图当作集成证据 |

### Vitest 失败详情

执行 `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：

- `payment-plan-filters.spec.js` 3 项、`payment-plan-order-context.spec.js` 1 项：测试按旧的“到期日从/至”aria-label 查找 input，页面当前为“计划到期日从/至”，触发空 DOMWrapper。
- `phase2a-list-shell.spec.js` 1 项：断言客户空状态包含“新建客户”，当前文案为“添加客户资料，记录负责人和跟进计划。”。
- `purchase-payment.spec.js` 1 项：预期“付款已记录为支出流水”，页面显示“付款已登记为支出流水”。
- `quote-editor-availability.spec.js` 1 项：预期“当前报价交期”，页面显示“本报价参考交期”。
- `unsaved-changes.spec.js` 2 项：按旧按钮文本查找结果为 undefined，无法触发操作。
- `infrastructure-tests/isolated-runtime.spec.js` 是 Playwright 测试、`infrastructure-tests/runner-validation.test.mjs` 是 Node 测试，Vitest 误收集；`tests/ux-copy-sales-purchase.spec.js` 是 Node 测试，Vitest 中 `import.meta.url` 造成 `ERR_INVALID_URL_SCHEME`，并报告无 Vitest suite。未通过修改配置或排除用例掩盖失败。

上述 9 项行为测试已更新过期文案或 aria-label，原业务断言保留；涉及的 6 个测试文件定向重跑 79/79 通过。随后限制 Vitest 不收集由 Node 和 Playwright 执行的基础设施文件，并将销售文案 Node 测试迁入 Vitest，保留原断言。Node 基础设施通过 `test:unit` 运行，Playwright 基础设施单独通过隔离 smoke 运行；修正后完整 CI Vitest 命令 667/667 通过。

## 后续验收

需要改造或建立能确认所有请求都指向本轮隔离 API 的全量 Playwright 环境；完成集成版截图、附件上传及快照、收发货重复请求、MOQ 和其余业务流程验收；在独立 PostgreSQL 测试实例验证 0090 与并发。11 月 1 日 CI 和正式环境仍需执行与核对上述未验证项。此报告不是上线或封版许可。原始运行输出为本地终端输出，未另存完整日志文件。
