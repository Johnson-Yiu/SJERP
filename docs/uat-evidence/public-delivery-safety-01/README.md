# SEC1 公开交付检查

基线 `00f7753dfc40b417983335be05135cb76a945ee0`。使用 Git 对象只读扫描。完整 checkout 因 D 盘空间不足失败，采用 C 盘稀疏 worktree。扫描直接读取 Git 对象，因此不受稀疏路径影响。

| 范围 | 检查量 | 命中 |
| --- | --- | --- |
| 基线跟踪文件 | 14,267 个文件，7,502 个文本，6,762 个二进制，3 个超限 | 13 个数据库文件，76 处带口令连接串特征 |
| 本地取得的公开分支历史 | 256 个远端分支，1,313 个可达提交，16,331 个去重 blob，10,564 个文本，5,764 个二进制，3 个超限 | 10 个数据库对象，117 处带口令连接串特征 |
| 发布文档、样例及验收资料 | 当前树 8,715 项扩展名命中人工审阅类别。文档和日志文本经过特征检查 | 截图、压缩包内部、Office 内容、PDF、数据库记录和外部 Actions 产物未逐项审查 |

历史为分支可达 Git 对象快照，Git 对相同内容仅提供一个代表路径。未覆盖已删除分支、仅由标签或 PR 引用可达的对象、Git LFS 外部对象、超 4 MiB 内容、图片 OCR、二进制内部及提交消息。业务资料扩展名计数是人工核查范围，不能据此判断内容真实性。

## 分类与处置

- 当前和历史均未匹配本脚本检查的 GitHub 令牌、AWS 访问密钥 ID 或私钥头。尚无确认真实凭据公开的证据。
- 13 个数据库路径集中在 `docs/uat-evidence/export-stability-closeout-20261105/`（12 项）与 `docs/uat-evidence/integration-closeout-02/final-02140bf-history-chrome/artifacts/`（1 项）。文件名包含隔离、合成或脱敏标记，内容真实性待核实。当前保留原证据。若确认含真实资料，需协调授权处置公开文件和历史暴露。
- 连接串候选包括 CI、本地测试、部署示例和验收运行资料。连接串规则仅列人工复核。隔离数据库口令和占位示例属于预期候选，尚未对全部命中逐项完成分类。项目与 Git 提交身份不属于本脚本的凭据规则。
- 如后续确认任何公开凭据仍有效，应通知责任方撤销或轮换，并独立处置历史暴露。

## 执行与接线

- `python scripts/check_public_delivery.py --candidate HEAD` 扫描指定树。基线因既有数据库文件返回 1。
- `python scripts/check_public_delivery.py --public-history` 扫描本地 sjerp 远端跟踪分支。因数据库对象命中返回 1。
- `python -m unittest discover -s scripts -p test_check_public_delivery.py` 使用人工生成样例。
- 最终集成先在独立任务运行单测，再以 `python scripts/check_public_delivery.py --range BASE_SHA..HEAD_SHA` 检查新增可达对象。PR checkout 需取得两端提交和范围历史。保留非零退出状态，结果仅包含规则、位置与对象 ID。全树检查需先处置既有数据库命中。GitHub workflow 由最终集成方接线。
