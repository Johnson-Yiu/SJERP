# REVIEW-INTEGRATION-BATCH-01 当前交付状态

用户最新CI约定（2026-11-05）：GitHub额度不足，当前后续提交使用[skip ci]，不再触发、等待或重跑Actions，不改workflow配置。旧运行保留实际结果；最终CI标记额度暂停/未执行，不能记为通过。继续本地全量、隔离PG17、真实Chrome和专项；无法本地执行的真实Linux跨UID/目标环境验收另列NEEDS VERIFICATION。独立复审及上线授权边界不变。

当前接收与回归更新（2026-11-05）：财务完整稳定来源e301a86044ffe56b72172a94dc3b00ae09401b05、Linux完整稳定来源4a4f338b09e9a464f1e66c24a905c35c970729bf均已合入（当前接收锚点536789f6dbafb2874b1abfd33ade2b30faa123a4），来源各自CI均成功，不能替代集成CI。a840冻结版本SQLite1330项1266通过/64跳过、PG1330项1300通过/30跳过，均0失败；合入财务来源后d4e8586的三条原反例SQLite3/3及财务PG30/30通过。Linux预审新发现0600签名回执跨UID交接缺口，归ISS-018，集成内最小修复及真实Linux回归中。历史接续仍在开发验收，未交付完整稳定SHA；当前不能称最终集成完成。最后已核实的统一分支三CI仍为906/41855319673，后文该CI只覆盖其精确SHA。

## 最新补修代码及实际CI

已正常推送代码 **90683506f5d9447974302d83c89ba27351d5dfd4**；[CI41855319673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41855319673)三项均SUCCESS，主审已读取实际job日志与artifact元数据绑定同一SHA。这是开发侧实证，不是ChatGPT对86项Issue的独立接受。

| 906精确CI | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| Backend（1317项） | 1259 | 0 | 58 |
| PostgreSQL17（1317项） | 1287 | 0 | 30 |
| Node | 179 | 0 | 0 |
| 字体规范 | 1 | 0 | 0 |
| Vitest | 720 | 0 | 0 |
| Chrome / Playwright | 270 | 0 | 0 |

生产构建通过3.21秒。完整日志已发布并只脱敏6个测试凭据字段：[ci-9068350-receipt.json](../integration-closeout-02/ci-9068350-receipt.json)、[ci-9068350-logs.zip](../integration-closeout-02/ci-9068350-logs.zip)。同代码本机PG专项12/12及恢复/HTTP另列；未接收的历史接续、Linux和财务反例完整来源不被该CI提前覆盖。后续文档/测试及来源提交的最终精确SHA CI仍须单独核对。

**最新已验产品代码：90683506f5d9447974302d83c89ba27351d5dfd4，CI41855319673三项成功；Issue独立复审未整体完成。** 分支`codex/r1-prelaunch-consolidation-20261104`。当前后续工作包为[INTEGRATION-CLOSEOUT-02](../integration-closeout-02/README.md)。本页中的“已验证版本”与后续文档或新来源提交分开，不把旧CI冒充新SHA结果。

## 已完成的基线8087验收

验收代码：`8087f2c68b19a302a25e814ec8ce6113d91d4750`；[CI 41839476121](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41839476121) 的 Backend、backend-postgres、Frontend 均 **SUCCESS**，用户已转述 ChatGPT 实际核实。该结论仅覆盖执行路径，不代表86项待复审Issue全部接受。

| 同一 SHA 的实际 CI | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| Backend（1312项） | 1254 | 0 | 58 |
| PostgreSQL 17（1312项） | 1282 | 0 | 30 |
| Node | 179 | 0 | 0 |
| Node-only 字体规范 | 1 | 0 | 0 |
| Vitest（77文件） | 720 | 0 | 0 |
| Playwright / Chrome | 270 | 0 | 0 |

生产构建成功（3.16秒）；`git diff --check`通过。最终SHA本地PG17专项另15/15通过、0失败/跳过，99表1081行128条迁移4文件恢复一致；恢复后真实HTTP为匿名403、无权403、授权200且字节一致、公开media直链404。额外命令专项8/8、真实GPG2/2属于分别记录的历史执行版本，不冒称本轮重跑。

可公开复核的精确版本回执：[baseline-8087-ci-receipt.json](../integration-closeout-02/baseline-8087-ci-receipt.json)。CI artifact SHA256 `adbe1f662425afb408fc84eb1b66b3407a3634a83735e935e6623249aea849bc`，包含财务PNG6、PDF2、CSV4和ISS039完整数据库快照2份；快照1075640–1075733字节，验证了此前默认1MiB输出缓冲补修。

## 完整稳定来源

| 来源 | 完整SHA | 来源成功CI |
|---|---|---|
| 起点 | 4388947d70d26bca66ca0bfc76b2383a2fc0d404 | 41782956426 |
| 打印封存 | b3d0d386de70d9efd77bf62cdbd87877fbccbfb8 | 41802910019 |
| 核心工作区 | e302199f7890c686a309f54aebe8cc31b6202f52 | 41808354916 |
| 财务 | 3a07e7ef1a9e63c98077d45492ba23b798c7fcdd | 41815451746 |
| 运维 | d289de36a3da3e4bd6531c812ec21a05f046d570 | 41814619508 |
| 历史归档 | a0729a0965850028fe52f5b6fcc3e825f23b1289 | 41822826770 |

五项完整稳定来源及起点均在已验证版本中；来源CI与集成CI分列。[来源回执](source-receipts.json)、[冲突处理](MERGE-RECORD.md)、[原始逐轮测试](TEST-RESULTS.md)、[源码tree等价证明](code-tree-equivalence.json)。后续接收历史实际接续、Linux运维、财务反例的完整稳定SHA，不合并移动HEAD，不以一次远端出现的提交视为完成交付。

## 当前门槛分类

| 范围 | 当前分类 | 具体下一步 / 边界 |
|---|---|---|
| 历史资金、未结、库存基准及剩余履约接通 | 待实施（开发及合成验收已授权） | 历史执行器当前仍创建三个`not_connected`；接收历史包完整稳定SHA，核查正式服务调用、审批、组原子性、重试幂等、库存/履约不重复和真实PG并发。不得用“缺真实资料”解释代码未开发。 |
| Linux一次性真实验收、恢复回执及故障验证 | 待交付、待验收（已授权） | 接收运维包固定SHA及专用Linux运行，区分真实内核/Nginx/受限DB角色结果与模拟结果。目标服务器尚未验不妨碍隔离Linux验收。 |
| 财务反例 / 内部真实性边界 | 定向复核中，不能预判通过或漏洞 | 接收反例包稳定测试和原始失败；仅确认可达产品缺陷后由统一集成协调公共服务补修。ORM管理员能造数据本身不是HTTP绕过证据。 |
| 86项FIXED_PENDING_REVIEW | 待ChatGPT逐项独立复审 | 依据风险/模块清单逐项审代码、正常与拒绝路径、实际文件及视觉；CI成功不自动关闭。 |
| 真实启用日、账户、余额、凭证和真实历史资料 | 外部资料；真实执行需单独授权 | 不猜值、不导入真实资料、不用合成身份替代实名。只在真实迁移/启用阶段请求相关资料。 |
| 正式鉴权、RBAC、真实员工审计 | 正式启用另行授权，设计/隔离证据分别审查 | 维持开发超级管理员约定，不将Django admin或合成session称为ERP登录。 |
| 目标生产配置、异地存储/密钥、RPO/RTO和告警 | 目标环境待验 / 外部条件 | 一次性Linux证据不替代目标环境和独立异地恢复；不部署或访问真实库。 |
| 完整打印成品及分页 | 用户明确延期 | 不追加重试/催办，不扩大到ISS-037其余主体快照要求。 |

保留警告：npm4项moderate开发依赖、构建chunk大于500kB、既有包/Actions运行时弃用告警；无无关依赖升级或workflow规避。

## Issue与视觉索引

当前计数和新增缺陷以[公共台账](../../PROJECT_ISSUES.md)顶部当前摘要为准。原86项待复审没有因CI成功关闭；详见[逐项复审清单](../integration-closeout-02/REVIEW-BACKLOG.md)及[视觉证据索引](../integration-closeout-02/VISUAL-EVIDENCE.md)。空页截图只证明空状态/布局，合成正向操作另有HTTP、数据库、实际文件和截图链。

## 历史章节（不作为当前派工/状态）

原首页、状态表及Issue矩阵完整原文已保存于[history/](../integration-closeout-02/history/)，逐文件字节数和SHA256见[history-manifest.json](../integration-closeout-02/history-manifest.json)。其中“运行中”“尚未提交”“最终CI待验”只描述当时时点；原候选CI41829100528的前端268通过/2失败保持原结论和原始日志，不改写为通过。后续03b524d修复完整快照输出、7a896d0修复财务证据根目录，最终8087三CI成功。

原始失败日志、截图、数据库和真实文件未重写。旧阶段实施和专项结果仍在TEST-RESULTS及各REVIEW文档中按原SHA追溯。本轮不合并master、不部署、不启用正式RBAC、不导入真实资料、不自行关闭Issue或宣布上线就绪。
