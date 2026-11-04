# 稳定完整来源接收与冲突记录

| 来源 | 已核对远端完整SHA | 精确SHA CI | 本包接收状态 |
|---|---|---|---|
| 打印封存 | b3d0d386de70d9efd77bf62cdbd87877fbccbfb8 | 41802910019三项成功 | 完整来源合入98bf4ea6108c913d0c6b31f77a25191df5e46e11；仅打印完整成品/分页按用户决定延期 |
| 核心工作区 | e302199f7890c686a309f54aebe8cc31b6202f52 | 41808354916三项成功 | 已审完整四提交范围，合并进行中 |

两个远端分支已经git ls-remote实际核对；源CI原始查询结果保存在本包logs/source-ci-*.json。源CI不替代集成最终CI。

## 文件处理

- AGENTS.md：唯一手工内容冲突。保留当前用户“按依赖/模块/冲突组织尽可能多任务、不设数量上限”，不恢复来源旧2–5限制；连续自查、集中交付、最终精确SHA CI、权限及部署授权边界保留。
- frontend/infrastructure-tests/runner-validation.test.mjs：Git自动合并后人工核对，保留本包自有子进程取消清理/诊断，保留打印来源xvfb/xauth可用性断言。只允许证据上传步骤使用always，业务检查仍禁止if或continue-on-error跳过/忽略失败。
- .github/workflows/ci.yml：接收打印来源已验证的虚拟显示及证据保留步骤，非通过修改workflow规避失败。Backend、真实PG17、Node、Node-only、Vitest、浏览器、构建步骤全部保留；没有减少任务或弱化断言。本包未另外改写workflow。
- QuotePreviewModal.vue：保留已保存PI图片/字体准备检查、失败提示及重试保护。不追加原生打印/分页新任务或宣称完整成品已独立接受。
- 核心Product/SKU/Resource/Document/Inventory/Purchase页面：审查来源完整差异，主要为晚响应失效、保存中导航保护、跨动作反馈及窄屏SKU字段布局。分类/SKU业务定义、收货请求幂等键、附件失败重试与待上传状态保留；最终行为仍需综合回归。

## 原始证据保留

来源原始CI/测试日志有尾随空白，导致整个集成差异的git diff --check报错。原始Git字节分别无损保存在print-source-raw-ci-logs.zip（2份）和core-source-raw-logs.zip（22份），仓库相对原路径、源SHA、原始及阅读副本摘要列在各manifest。历史路径的文本仅作为明确标头的阅读副本，去掉尾随空白；未删除失败、未改结果、未以阅读副本摘要冒充原始日志摘要。完整源提交作为合并祖先保留，原日志也可用git show精确源SHA取得。

本包首次浏览器回归还有两个测试把输出写到旧历史路径，已先保存本轮9个输出与双摘要，再恢复历史Git内容；仅修测试输出根目录，专项2/2及3/3通过，详见fixed-path-evidence-preservation.json。

财务、历史、运维未明确完整交付的SHA尚不接收，来源开发中检查点不得静默替代稳定来源。
