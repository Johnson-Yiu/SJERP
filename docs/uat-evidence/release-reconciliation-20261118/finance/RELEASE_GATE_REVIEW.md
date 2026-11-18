# 发布源码门禁独立复审

审查对象是父任务当前候选中的四文件，不是远端已提交/部署结果：

- `scripts/check_pilot_release_source.py`
- `scripts/build_pilot_release.py`
- `.github/workflows/ci.yml`
- `scripts/tests/test_release_source_inventory.py`

本次已读审版本逐文件 blob/SHA256 在 `release_gate_reviewed_files.json`。该记录之后若再修改相关逻辑，需要对应复核。

## 结论

当前实现具备实质门禁，没有发现需阻止交付整理的代码缺陷。门禁对源码、构建输入版本与包版本分别约束；它不能代替业务验收、最终SHA的CI结果及目标环境验证。

根任务 12 项 unittest 在本代理复跑中 **12/12通过**。另做了目标策略/CLI及工作区状态的独立临时仓库探针，结果见下。

## 门禁确实生效的位置

1. **源码检查不是可选提示。** `build()` 在 `git archive`、临时构建目录、依赖安装及 npm 构建之前调用 `verify_source(commit, repo=ROOT)`。失败抛错，不继续生成发布目录。既有“已接受修复后来被覆盖、祖先仍存在”的测试能拒绝该提交。
2. **构建请求绑定当前检出。** 完整40位小写SHA必须解析为该commit，HEAD必须与请求SHA相同，已跟踪文件在暂存区或工作区有改动都会拒绝。忽略普通未跟踪证据文件与实际 `git archive` 只导出已提交内容的行为一致。
3. **策略与被校验源码同版本。** 默认使用 `git show <commit>:docs/deployment/alex-source-inventory.json`，不会使用工作树未提交策略。缺清单、缺必需提交、祖先不满足、文件blob不一致或必需文本缺失均拒绝；`required_commits`/`reviewed_blobs` 不允许整体为空。
4. **CI串接正确。** `release-source` 全历史checkout，执行源码检查和12项回归；Backend、Backend PostgreSQL 17、Frontend 均 `needs: release-source`。门禁失败时业务job不会被当作成功完成；没有本次新增的跳过CI路径。
5. **发布包可核对指定版本。** `verify` 支持 `--expected-commit` 和 `--manifest-sha256`；先核对可信清单摘要，再核对清单SHA、逐文件字节/摘要及 `frontend/dist/release-info.json` 与清单一致。构建完成也以请求commit调用verify。

## 本轮发现并已处理的问题

### 1. 旧但自洽的提交仍能通过自己的策略

原补丁默认加载目标提交自己的策略，目标是避免工作树策略被改写。这意味着历史提交若满足当时的清单仍会通过，不能单凭此称“自动选择了最终批准版本”。临时仓库中构造新HEAD/新策略后，旧好提交依然通过自身策略，此结果符合现有设计。

父任务已补：构建HEAD与请求SHA一致、干净检出；验证发布包时可明确要求批准SHA和可信清单摘要。部署交接必须使用最终交付记录中的SHA，不把分支名或“最新”作为版本身份。即使加入HEAD约束，主动检出旧SHA再构建仍可成功，这是合理的历史构建能力，不能宣称已完全消灭人为选错版本。

### 2. Windows CRLF 的测试夹具误报

原测试在工作树文件上手算预期Git blob。模拟Windows CRLF写入且 `core.autocrlf=true` 时，Git存储LF，工作树哈希不同，正常提交被误判为 `content differs`。

父任务已将预期值改为 `git rev-parse <anchor>:page.txt`，以已提交对象为准。相同临时场景复核通过。证据：`release-gate-windows-fixture.json` 与 `release-gate-windows-fixture-recheck.json`。这只是换行场景模拟，不冒充真实Windows整套运行。

## 独立验证

### 已有回归复跑

在候选根目录：

```sh
python -m unittest discover -s scripts/tests -p 'test_release_source_inventory.py' -v
```

12/12通过，退出码0。日志 `release-gate-tests.log`。

覆盖：正确源、修复仍在祖先但内容回退、未提交策略修改不能放行、缺必需历史、拒绝分支名、构建前强制门禁、检出不匹配、工作区已跟踪改动、指定包SHA/可信清单、错误包版本、错误清单摘要、浏览器版本信息不一致。

### 额外只读审查探针（均在临时合成仓库/包）

- 不同HEAD已提交策略不改变旧目标读取的自身策略。
- 目标commit缺源码清单会拒绝。
- blob正确而required_text缺失，仍拒绝；不是被blob错误掩盖的假测试。
- 源码检查CLI默认目标策略、显式外部审计策略均成功，`HEAD` 名称拒绝。
- 已暂存但未提交的跟踪文件修改也拒绝。
- 普通未跟踪证据不触发dirty拒绝；仍会进入强制清单检查。
- 发布包CLI旧 `verify <dir>` 形式仍可运行；新两参数匹配通过，错误期望SHA拒绝。
- Windows换行模拟复核通过。

结构化结果：`release-gate-probes.json`、`release-gate-new-probes.json` 和 Windows 两份记录。

## 尚未证明、不要扩大描述的内容

- 本次逻辑测试使用临时合成Git仓库；没有替代最终候选完整历史检出的 `check_pilot_release_source.py <最终SHA>`。最终manifest必须更新为实际接收文件的blob，并在真实候选提交上通过门禁。
- 没有执行本次真实 `npm ci → 构建 → 发布包` 全流程，也没有创建可安装二进制发布目录；由最终候选构建步骤完成。
- CI配置读审和本地回归不等于远端Actions已运行。GitHub计费/runner以及最终SHA job结果仍须单独核对。
- `verify <dir>` 未传期望SHA时是包内部一致性检查；不证明该包就是本次最终批准版本。受信任的SHA和manifest摘要应来自交付/可信构建记录。
- 这里的策略是可版本化的评审清单，不是不可篡改的授权机制。源码和策略一起经人工改变仍需要独立评审；这不应靠新加无关安全框架解决。

## 最小建议

保留当前门禁及12项回归；将最终候选SHA与可信构建产生的RELEASE.json摘要写入Codex交接说明，并在包校验时传入。对最终SHA重新核对清单及三类业务CI，随后按既有Chrome/目标环境门槛验收。没有发现必须继续扩大本地测试范围的具体风险。
