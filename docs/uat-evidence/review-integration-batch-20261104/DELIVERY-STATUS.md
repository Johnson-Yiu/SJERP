# REVIEW-INTEGRATION-BATCH-01 当前交付入口

当前统一分支`codex/r1-prelaunch-consolidation-20261104`，完整财务e301a860、Linux4a4f338、历史ba427474均已合入447d7816。当前冻结候选02140bf46df27ba1abf5b9018507c07aae825769另有两处前端下载生命周期补修，不能称整体应用树与447d相同。最终交付SHA以[综合报告](../integration-closeout-02/README.md)为准。

用户已要求因额度不足跳过后续CI；使用`[skip ci]`，不触发/等待Actions，不将旧CI视为本轮通过。

| 本轮范围 | 实际状态 |
|---|---|
| 当前02140候选 | SQLite1338通过/72跳过/0失败、PG1378通过/32跳过/0失败，均1410项；Node179、字体1、Vitest725及构建通过；适用Playwright262通过/1报价下载失败/0跳过，仍FIX REQUIRED |
| 当前历史接续与台账 | 真实Chrome五阶段及98次HTTP、live/发布副本核验通过；ISS-121转FIXED_PENDING_REVIEW，新增1项与原86队列分列。124ID：87 FPR、14 NEEDS、13 BLOCKED、0 OPEN、10 CLOSED；未关闭任何Issue |
| 447d SQLite | 1410项：1330通过、80跳过、0失败 |
| 447d真实PG17 | 1410项：1378通过、32跳过、0失败；102表1218行133迁移5文件恢复一致，三个恢复验证PASS，cleanup complete |
| 447d前端 | Node179、字体1、Vitest725通过；构建成功。适用Playwright261通过、2导出下载失败、0跳过；延期打印spec7项未执行，继续调查失败 |
| e768实际Google Chrome | 原附件3场景3/3；10图、HTTP摘要、Google exe启动及CDP版本，应用代码与447d一致 |
| 原86待独立复审 | 逐项代码入口/证据/关闭缺项已整理，不自行关闭，不当成ChatGPT独立接受 |
| 历史接续 | 完整稳定来源已接收并有集成PG及Chrome闭环证据；待独立复审及目标启用条件，不是缺真实资料而停止开发 |
| 真实Linux与目标配置 | 补修后跨UID未执行；来源旧Linux成功不替代集成补修后验收 |

[原始日志与失败](../integration-closeout-02/TEST-RESULTS.md)、[视觉索引](../integration-closeout-02/VISUAL-EVIDENCE.md)、[逐项复审包](../integration-closeout-02/REVIEW-BACKLOG.md)。78b/f928旧图实际为默认Chromium，不能由目录/环境名认定Google Chrome。来源精确SHA、原始失败和历史阶段说明均保留在综合报告历史章节/字节快照。

不合master、不部署、不启用正式RBAC、不导入真实资料；打印完整成品与分页按用户决定延期，未追加尝试。尚未宣布上线就绪。
