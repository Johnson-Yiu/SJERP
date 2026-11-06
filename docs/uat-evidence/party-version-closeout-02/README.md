# PARTY-VERSION-CLOSEOUT-02：当前结论

**部分完成，尚不具备关闭 ISS-037 或整体验收通过条件。** 本分支从 `792edff6b696c4ad1f5bc65f9e91f623b5b964c0` 继续，使用独立工作树、合成账号、隔离数据库和媒体。最终代码以本报告所在提交的树为准。CI 因项目额度暂停，未运行，不能记为通过；等待独立复审。

已实现申请拒绝、撤回、失效和重新申请，保留申请、审批及终态记录；报价、销售单、采购单的更正复用既有主体版本链及独立认证账号审批；新单法律主体替换绑定获批目标、关联原单，不自动迁移或复制原单收付和履约。已接入双方资料的草稿录入、版本化审批、未知与留空区分以及详情展示。正式化、重试和资料篡改拒绝均有专项测试。

**未完成：**现有报价 PI 预览、打印模板及 XLSX 仍主要消费原报价字段及保存模板，未完整消费独立账单地址、收货地址、收件人等扩展资料；含扩展资料的报价法律主体替换因此安全拒绝。注册资料的独立字段及既有文件中的准确位置尚需明确和实现。未完成当前主体版本与所有现有正式文件的对账；这不是用户延期的打印成品及分页范围。扩展资料审批差异的桌面和 390px 真实浏览器复核、含扩展资料 SO/PO 替换完整界面流程，仍须补验；现有合成账号只能证明两个认证账号，不证明自然人独立。历史未知资料不能由当前主档补造。不得把部分通过写成整个工作包完成。

## 测试矩阵

| 验证 | 当前结果与证据 |
| --- | --- |
| SQLite 后端全量 | 1559 项运行，99 项条件跳过，其余通过：[原始日志](logs/sqlite-full-final.log)。不将跳过记为通过。首次全量有 4 失败、1 错误：[日志](logs/sqlite-full-resume.log)；原因是新增更早的回退保护与旧迁移夹具不匹配，保留回退拒绝及数据、迁移状态不变断言后，[相关文件 8 项重跑通过](logs/quote-buyer-tax-migration-targeted-final.log)。 |
| PostgreSQL 17.10 | 独立临时集群、168 项通过；0108 升级到最新迁移、模型检查、带数据回退拒绝及数据保留通过，测试库已清理，781 项源码哈希前后一致：[测试](logs/pg17-final-retry3/party-tests.log)、[运行结果](logs/pg17-final-retry3/result.json)。首次沙箱启动因受限令牌失败；第一次真实 PG 有 4 失败、5 错误：[日志](logs/pg17-final-retry/party-tests.log)，已针对夹具、测试清理桩、合法先批准后失效、旧申请重试分别处理。 |
| 前端 | Node 179 项通过：[日志](logs/frontend-node-final.log)；有效 Vitest 81 文件、766 项通过：[日志](logs/vitest-full-final.log)；[生产构建](logs/frontend-build-final.log)通过，保留大 chunk 提示。Node 排除在 Vitest 外的 Node 测试文件由 Node 运行器覆盖。 |
| 草稿双方资料 Chrome | 报价、SO、PO 保存并重开：[日志](logs/party-details-ui-chrome-retry.log)、[销售截图](party-details-ui/order.png)。首次页面加载超时：[日志](logs/party-details-ui-chrome.log)。该用例为桌面草稿路径，不代表正式文件或窄屏已覆盖。 |
| SO/PO 更正 Chrome | 两个合成认证账号进行申请、审批和生效；桌面及 390×844，原快照、金额和商品明细不变：[日志](logs/chrome-document-final-retry.log)、[采购窄屏](browser-final/document-party/purchase-390.png)、[销售桌面](browser-final/document-party/order-desktop.png)、[HTTP](browser-final/document-party/http-results.json)。用户可验证账号不同，不能据此证明真实人员独立。 |
| 报价替换 Chrome | 两个合成账号，申请 201、审批 200、创建草稿 200、PI 200：[日志](logs/replacement-quote-chrome-fixed.log)、[HTTP](replacement-quote-fixed/replacement-quote/http-results.json)、[390px](replacement-quote-fixed/replacement-quote/new-draft-390.png)。旧测试在国家明确留空时读取主档国家导致创建 400：[失败](logs/replacement-quote-chrome-resume.log)、[响应诊断](logs/replacement-quote-chrome-diagnosis-2.log)；已改用获批快照并保留空值断言。样例不含完整扩展资料。 |
| 拒绝/撤回 Chrome | 中间版本的真实操作、HTTP 与截图：[日志](logs/chrome-lifecycle-retry.log)、[拒绝](lifecycle/rejected-390.png)、[撤回](lifecycle/withdrawn-desktop.png)、[HTTP](lifecycle/http-results.json)；不冒充最终源码的完整生命周期视觉验收。 |
| 现有正式文件 | 上一工作包实际 XLSX 及历史快照对账保留在 [旧报告](../party-version-closeout-20261105/README.md)；本包没有完成最终源码下完整扩展资料 XLSX 对账。 |

运行使用锁定 Python 3.12 环境；核心命令为 `python manage.py test crm --noinput --verbosity 1`、`npm run test:unit`、`vitest run`（单 worker，有效 spec）、`npm run build`、隔离浏览器运行器对应 spec；PostgreSQL 可复执行脚本及迁移日志位于 [pg17-final-retry3](logs/pg17-final-retry3/)。测试库、媒体目录和账号均为隔离合成数据，没有连接业务库。浏览器意外中止的一次仅到迁移阶段，专属临时目录核对标记后清理：[日志](logs/chrome-document-final.log)。

## 集成注意事项

本包新增 `crm.0113` 至 `crm.0117`，须在集成时核对其他分支的编号和依赖；不能覆盖既有迁移或绕过回退保护。共享接线包括 `models.py`、`party_version.py`、`party_version_api.py`、`serializers.py`、`views.py`、`urls.py`、`quote_party_approval_guard.py`、销售和采购生命周期中的主体快照捕获、仅测试数据库使用的 `postgres_test_cleanup.py`，以及三类详情组件。合并时逐项保留其他任务修改。没有修改公共台账或导出 helper；生产权限、基础设施和正式 RBAC 未启用或验收。

## 历史与原始失败

- [报价生命周期首次浏览器超时](logs/chrome-lifecycle-first.log)，[销售采购中间浏览器失败](logs/chrome-document-second.log)。
- [PostgreSQL 探索轮测试通过但清理失败](logs/pg17-lifecycle-exploratory-02/result.json)，不能计为通过。
- [首次 Node 全量](logs/frontend-node-first.log)、[提前终止的 SQLite](logs/sqlite-full-first.log)和[提前终止的 Vitest](logs/vitest-full-first.log)保留；不作为全量通过依据。
- 完整双方资料在旧模板的消费缺口、历史未知和后续新模板版本待统一集成及独立审查处理；本包不修改公共台账。

隔离运行器产生的临时令牌已在归档日志中按可复执行脚本脱敏；原始通过／失败和 HTTP 结果未改写。
