# 2026-11-18 发布候选交接给 Codex

## 版本选择

候选分支：`codex/release-reconciliation-20261118`。父基线：`3bb0970148ff98025d44d6c5ee42e17bfe180002`。交接时使用 ChatGPT 最终交付的完整 40 位候选 SHA，以下以 `<APPROVED_FULL_SHA>` 表示；不要自动改选 master、最新分支或旧演练包。

[本次审查、接收范围、测试及阻塞](../uat-evidence/release-reconciliation-20261118/README.md)。用户要求整理合适版本后由 Codex 部署；本次整理没有操作 ALEX。现有部署拓扑与真实环境参数以现场已验收记录为准，不重新选择虚拟机安装路线。

## 先验收精确源码

保留已有工作区，在新的隔离检出取得完整历史并切到 `<APPROVED_FULL_SHA>`。检查 HEAD 与该 SHA 一致，跟踪文件无本地修改。

```text
git rev-parse HEAD
git status --short
python scripts/check_pilot_release_source.py <APPROVED_FULL_SHA>
python -m unittest discover -s scripts/tests -p "test_release_source_inventory.py" -v
```

必须核对同一 SHA 的 GitHub Actions：release-source、Backend、Backend PostgreSQL 17、Frontend 及适用 Linux 运维检查。若 GitHub 因账单/额度或 runner 条件未启动，明确报告外部阻塞；不使用旧提交绿灯，不删除断言，不绕过门禁。已有 CI 失败须判断并修复，若源码修改则交付新 SHA 并重新验收。

本轮本地真实浏览器被系统权限阻止。按 AGENTS 完成真实 Chrome 与对应浏览器回归，至少验证：

- 财务流水：桌面空表和有数据铺满可用区域，390px 横向滚动仅在表内；保留截图。
- MOQ：0.58 箱 ×100 件恰好达到58不误警，同来源两行0.29合计不误警，0.57箱低量仍提示，正式低量例外及留痕正常。
- 报价新建/修订：保存中关闭、取消、导航受阻，失败保值可重试；默认包装子表保存时父/子不能关闭。成功只产生一次业务写入。
- 历史预检：中文重复编号提示、切换工作簿晚响应隔离、下载绑定当前工作簿；预检不修改正式数据。抽查历史承接、财务、供应商、工作区新文案的桌面/窄屏显示。
- 新 `quote-risk-closeout-02.spec.js` 是合成 API 浏览器用例；另保留既有真实报价导出回归，不能拿合成响应证明 XLSX 内容正确。

## 构建并核对发布包

在干净的最终 SHA 检出中，使用锁文件和既有构建环境；发布输出目录必须是新目录，其父目录须已存在。

```text
python scripts/build_pilot_release.py build <APPROVED_FULL_SHA> <NEW_RELEASE_DIRECTORY>
python scripts/build_pilot_release.py verify <NEW_RELEASE_DIRECTORY> --expected-commit <APPROVED_FULL_SHA> --manifest-sha256 <TRUSTED_RELEASE_JSON_SHA256>
```

可信清单摘要应在构建端生成并记录在交付记录，再独立用于传输后核对；仅在目标包上现算摘要再拿来验证自己，不能证明运输前后相同。构建脚本已强制源码清单、精确 HEAD 和干净跟踪文件；包验证同时核对文件清单、字节摘要及前端版本文件。

Windows 可从源码检出运行已接收的核验工具：

```powershell
powershell -NoProfile -File scripts/lan-installer/Test-ErpRelease.ps1 -Bundle <NEW_RELEASE_DIRECTORY> -ExpectedCommit <APPROVED_FULL_SHA> -ManifestSha256 <TRUSTED_RELEASE_JSON_SHA256>
```

`Check-Alex.ps1` 可选用于现场只读检查，会写一份本地诊断报告；本轮未在 Windows 执行这两个脚本。它们位于源码目录，不假设打包脚本已把它们放进运行包。本次没有接收整套后续安装器脚本。

## ALEX 升级与交付

源码和包门槛通过后，按现有已验收流程备份数据库、私有媒体和部署配置，记录可恢复点及旧包身份，再切换服务。没有新增数据库迁移，但仍应核对现有迁移叶节点及目标状态；不要清库、导入合成 fixture 或恢复旧分支同号迁移。

部署后分别核对：实际服务端进程的启动路径/运行包、包清单与后端文件；实际浏览器访问的 `/release-info.json` 必须返回 `<APPROVED_FULL_SHA>`；首页 JS/CSS、登录、财务流水、采购、报价及上述改动的业务复验。静态版本文件只证明被访问的前端版本，不能单独代表后端已升级。

最终报告包含：完整源码 SHA、CI run/job 结果、Chrome证据、包路径与可信清单摘要、备份及恢复点、ALEX前后版本、实际验证结果和未完成项。不要把本次候选源码整理或旧 UAT 报告当作已完成部署，不自动合并 master。
