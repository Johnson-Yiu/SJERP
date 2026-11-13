# PRODUCT-DRAFT-PROTECTION-01 / C 包验收

范围：R05，原 P1-06，产品能力预览相关 P1-01，产品日志 P2-11，SKU 包装候选相关 P2-05。公共对话框和全局容器由 D 负责；本包未改业务状态、权限、成本、取消退款或真实数据。

## 基线与实现

- 集成基线：`d7d155b994b652f6f4f777edde22a257a8ed7a2e`。
- 公共 guard 导出来源：`e2d0f432e46b91447442b21cd47d0c22da2ec403`，本分支对应 `56ebf770`。
- C 源码提交：`440e13b363f30825478d5388e842ac375b7481e5`，正常推送 `codex/product-draft-protection-01`。
- 供应能力规则与参数方案分别记录 dirty/busy；使用既有 scope 与工作区保护。保存/继续/删除失败不清除 dirty；提交中编辑区 inert、不能离开。
- 同产品刷新保留组件、当前产品页和输入；参数方案加载不替换打开草稿，迟到加载通过请求序号丢弃。刷新错误保留旧详情和编辑器并显示重试。
- 一个产品级路由守卫统一询问 scope；内嵌 SupplierBatchBindingDrawer 不重复注册路由守卫，独立使用仍保留默认保护。
- 操作日志公开 URL 固定为 `operation_logs`，内部 `__operation_logs` 不再写入 URL。原 watcher 会把公开 URL 改回内部名，刷新恢复器拒绝内部名而回总览。
- 批量启停反馈主体已在基线实现。本轮保留该实现，补足失败计数、失败对象、选择保留、刷新保持、重试和状态回读断言；避免父刷新卸载结果。

## 自动回归

- Vitest：5 文件 60 项通过（sku-management、unsaved-changes、product-workspace、entity-detail-quote-create、sku-ux）。其中 C 文件 14 项，覆盖部分/全失败、重试、失败保存/继续、路由/刷新/提交中保护、迟到加载。
- Node：ProductSkuManagement 定向 1 项通过。
- 生产构建通过；现有大 chunk 提示保留。
- 源码阶段 GitHub Actions：`43474624777`（最终结果以 D 集成认证及 GitHub 状态为准，不用本地检查代替 CI）。

## Chrome 方法与边界

使用系统 Chrome、登录测试超级管理员 codex、隔离 SQLite 和 MEDIA_ROOT；端口 8953/8954。每次运行前后验证隔离身份，临时库由 runner 自行清理。未访问真实库。

普通鼠标点击、实际 checkbox 边缘点击、预览按钮 Enter、表单填写、原生 beforeunload 取消、工作区切换/关闭均通过实际交互执行。没有 force 点击或用 DOM 存在代替结果。

失败保存及 SKU 拒绝路径由 Playwright 精确拦截对应写请求返回 400；成功写入、重试和所有状态回读使用真实隔离 API。这样的拒绝注入只覆盖前端失败恢复，不能证明后端所有业务拒绝条件。

P2-05 已在 Chrome 1366×768、1920×1080 实际验证长名称搜索/点击选择、无匹配搜索、新建包装入口及放弃返回；SKUPage 当前基线已有修复，无需重复修改。宽表保留横向滚动，没有扩大移动端改版。

P2-11 普通 business profile 关闭审计，因此该轮截图准确标为“未启用”；真实启用且空日志已通过 D 的 `--audit-product-draft-test` 专用隔离 profile 验证，不伪造环境开关。

## 运行记录说明

早期探索失败保留：HMR 中断；测试在继续草稿请求完成前计算输入数量导致多加空白参数（后端正确拒绝）；并发共享 Vite optimizer 引起慢加载/认证等待超时。已修正等待条件并采用最终冻结源码验证。它们不是业务通过证据。

最终运行编号、逐项状态及截图索引见下表。全局 Issue 状态与 P1/P2 统一台账由 D 更新，待独立复审。

## 修复前证据

独立对照工作树应用代码保持 `d7d155b994b652f6f4f777edde22a257a8ed7a2e`，只接入隔离缓存和登录等待工具提交，工具层 HEAD 为 `faec4794d24f08a71f42fea93071d2552a120265`。运行 `5ec4262f-86c4-4272-a062-596a431568f1` 通过，5 张截图位于 `before/artifacts/5ec4262f-86c4-4272-a062-596a431568f1/product-draft-before-docum-081b8-ct-draft-loss-and-log-reset/`：

- `before-rule-edited.png` / `before-rule-lost.png`：规则填写后切总览无提示，返回表单消失。
- `before-plan-edited.png` / `before-plan-lost.png`：参数填写后切总览无提示，再继续草稿无该参数。
- `before-log-reset.png`：日志页重载后总览激活。

这是一份隔离复现，不曾把当前工作树退回旧基线。

公共层叠新增实证：运行 `39bd4a9a-0348-402b-aafc-c97765d2049b` 最后绑定抽屉取消确认被遮挡，失败图保留为 before。D 统一修复来源 `4c0845a013f382b8b299af639e1755b529184795`，本分支对应 `38acb096`；C 未自行并行修改公共 CSS。

审计开启运行 `92200455-032d-4259-8c93-e16c79629cd0` 已得到真实空日志及刷新截图。该次运行在部分成功结果出现、列表刷新尚未结束时使用多元素 strict locator 导致测试失败；最终脚本明确等待刷新行数收敛后检查失败对象，保留原失败记录，不将该次标为全通过。


## 最终交付状态

最终 C 源码与验收脚本提交：`c83c56b194d4f6e029329a8eab551d316a814983`。冻结文件的真实 Chrome 审计 profile 运行 `12cab433-b3f6-4125-b03a-874ebd852a0c`：**1/1 PASS**（业务测试 58.2s，总运行约 2 分钟）。脚本逐项断言及日志见 [最终日志](logs/audited-chrome-final-pass.log)。最后新增焦点与不同详情切换分别通过 14 项、5 项定向 Vitest，最终构建通过。

| 编号/范围 | 状态 | 实际验证 |
|---|---|---|
| R05 供应能力规则 | 已修复并验证 | 1366×768、1920×1080、390×844 填写/预览；继续保留、明确放弃；失败保存后仍保护，成功保存 API 回读；桌面切工作区返回、关闭工作区取消、原生刷新取消均保留 |
| R05 SKU 参数方案 | 已修复并验证 | 同三视口修改、继续草稿取消、切页/关闭工作区取消保留；失败保存重试、成功保存回读与重开；明确放弃不覆盖已保存版本；迟到加载/后台刷新和 busy 离开由定向回归补充 |
| P1-01 产品相关子项 | 当前基线已有修复并验证 | 能力预览真实鼠标点击和 Enter；checkbox 边缘鼠标点击产生真实选中。库存调整浮层等其余部分由 D 统一核销 |
| P1-06 | 已修复并验证 | 停用全失败、部分成功、失败选择保留、重试成功；全部重新启用；每一步真实 API 回读。主体反馈已有实现，本包修复刷新保持并补完整测试，不重复改业务 |
| SupplierBatchBindingDrawer 回归 | 已修复并验证 | 继续编辑保留选择且焦点回关闭按钮；放弃后单次确认关闭且焦点回触发按钮；正常保存 API 回读含 manual 来源；后续关闭工作区不误报。公共层叠修复由 D 提供 |
| P2-05 包装候选子项 | 当前基线已有修复并验证 | 两桌面长文本候选/无匹配/点击选入/新建包装入口/放弃返回，SKUPage 未修改 |
| P2-11 | 已修复并验证 | 真审计开启下空日志、切入、刷新仍保留日志页；三视口重新打开。URL 不再写内部页签名 |

最终截图目录：[审计 Chrome 截图](artifacts/12cab433-b3f6-4125-b03a-874ebd852a0c/product-draft-protection-0-3400f-duct-logs-retain-real-state/)。其中 `rule-preview-before-save-*` / `rule-retained-*` / `rule-saved-*`、`plan-retained-*` / `plan-saved-readback-*` 分别记录保存前、继续编辑和保存回读状态；`batch-partial-real-readback.png`、`batch-total-failure-retained.png`、`batch-success-real-readback.png`、`binding-saved-real-readback.png` 记录真实结果。`audit-enabled-empty-log-reloaded.png` 记录真空日志。

包装两桌面截图在 [包装验收目录](artifacts/7151f1e4-0057-405d-8a63-81f3a8bcbeb8/product-draft-protection-0-e1399--empty-search-and-new-entry/)。该运行包装测试独立通过，随后产品测试因慢加载超时；没有把整个运行报为通过。

最后关闭工作区时，其自动摘要刷新请求被既有工作区生命周期取消，控制台保留“摘要刷新失败”警告；此前绑定保存、manual 来源及启停状态均已真实回读成功。没有真实数据库、资金、部署、正式导入或主分支合并。

本包没有未完成业务阻塞；状态为实施及验收完成、待 D 集成 CI 与独立复审，不能将本地通过写成全项目发布认证。
