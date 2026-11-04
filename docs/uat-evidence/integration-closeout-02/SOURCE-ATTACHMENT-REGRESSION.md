# ISS-007 跟进保存后立即重开回归

日期：2026-11-05
范围：仅 `ResourcePage.vue` 的跟进记录编辑路径及对应 Vue 回归测试。未修改历史、财务、运维、共享台账或 workflow。未提交 Git，也未执行 Chrome 浏览器测试。

## 调查结论

主审提供的 CI 运行记录显示，GitHub Actions run `41868099905` 的 Frontend job `126707482414` 在 `iss007-attachment-real.spec.js:49` 保存成功后立即重开时，等待 5 秒仍未找到 `ISS007-沟通纪要.txt`，表单内容为空；后续两个场景未运行。本轮没有重新访问该 CI 或 Chrome，因此这部分作为收到的证据记录。

新增确定性 Vitest 将保存后的列表刷新挂起，再立即点击旧列表行的“编辑跟进记录”。修前失败，收到的 `openEdit(row)` 直接把列表摘要作为完整记录：先 `resetForm()`，再把摘要缺失的正文等字段写成空字符串，并把缺少的 `attachments` 归为空数组。保存中的列表刷新尚未完成时，旧摘要仍可见，因而正文和附件都不会出现在重开的表单。该复现确认了组件中与报告现象吻合的直接失效路径；它不单独证明那次 Chrome 运行所收取的具体列表响应字节。

## 最小修复

`frontend/src/views/ResourcePage.vue`：跟进记录 `openEdit` 收到缺少附件数组或任一配置字段的列表行时，先按记录 ID 请求详情，再填充表单和已保存附件；详情请求失败时显示错误并停止打开。已有完整详情不会额外请求；其他资源类型逻辑未改。

## 回归结果

| 验收项 | 实际结果 |
|---|---:|
| 修前确定性 deferred 刷新/立即重开用例 | 0 通过，1 失败；命令退出码 1。正文断言实际值为空字符串。 |
| 修后单独运行新用例 | 1 通过，0 失败；退出码 0。 |
| 相关 Vitest 最终回归：新用例、`customer-followup-races.spec.js`、`follow-up-safety.spec.js`、`follow-up-richtext-and-attachments.spec.js` | 4 个测试文件通过；27 通过，0 失败，退出码 0。 |
| `ResourcePage.test.js` Node 单元测试 | 9 通过，0 失败，0 跳过；退出码 0。 |
| 原 Chrome 三场景 | 本轮未执行；主审负责最终集成 Chrome 验收。原记录仅第一个场景失败，后两个未运行，不能记作通过。 |

修前测试日志生成时，最终测试文件尚未加入“断言后释放 deferred 刷新”的清理步骤；失败断言与最终文件相同，新增步骤位于断言之后。修后最终整组日志对应已包含清理步骤的测试文件。

## 文件与原始日志

- 代码：`frontend/src/views/ResourcePage.vue`
- 新测试：`frontend/tests/iss007-save-reopen-race.spec.js`
- 修前失败：`docs/uat-evidence/integration-closeout-02/logs/iss007-save-reopen-pre-fix.log`
- 修后单测：`docs/uat-evidence/integration-closeout-02/logs/iss007-save-reopen-post-fix.log`
- 相关测试最终整组：`docs/uat-evidence/integration-closeout-02/logs/iss007-related-vue-regression-final.log`
- `ResourcePage.test.js`：`docs/uat-evidence/integration-closeout-02/logs/iss007-resourcepage-unit.log`
- 另有一次清理步骤加入前的中间整组日志：`docs/uat-evidence/integration-closeout-02/logs/iss007-related-vue-regression.log`；同为 27/27 通过，最终结果以 `...-final.log` 为准。

浏览器验收仍待主审在最终集成版本重跑原三场景；应确认保存 toast 后立即重开可见正文及附件，并记录实际结果。该等待不影响本轮 Vitest 对组件复现路径的修复验证。

## 主审后续实证与浏览器标签更正

补修代码已提交78b1eb0cbf05bec5865d98803fb9cebf62cb0202。其后两轮原三场景均3/3通过（23.9秒、21.4秒），第二轮已保留8张截图与HTTP文件摘要，但两轮未设置PLAYWRIGHT_CHANNEL，因此实际为默认Chromium，不能计作Google Chrome。第一次PowerShell路径表达式也设置失败，使用runner默认Python/临时证据位置，截图随安全清理删除；原日志保留，不冒充留存证据。第二次明确使用独立Python3.12。主审已目视检查第二轮的桌面/窄屏表单正文，附件区在滚动区域外，不能把这些图称为附件可见证明。

已提交f92824b的8行截图/更强可见性断言，仅补充滚动到已保存附件的1440×950、390×844真实视口截图，不改变原断言和三个场景。该提交已以显式PLAYWRIGHT_CHANNEL=chrome完成真实Chrome156验收：3/3通过、0失败/跳过，19.5秒；10张实际截图与HTTP字节摘要保留，独占进程/端口及临时数据库/媒体清理完成。主审已目视确认已保存附件在1440×950及390×844视口可见，正文也保留；不是空态或复用图。详见attachment-regression-result.json及attachment-regression-logs.zip（只脱敏12处已关闭隔离令牌）。最终历史来源整合后仍按其具体变更执行适用回归，不把本次结果扩展到未接收来源。


## 主审最终浏览器身份更正（2026-11-05）

上一段f928“显式环境变量即真实Chrome”的判断错误，原runner会覆盖该变量。f928实际默认Chromium，3/3和原图字节不变；保留旧描述作为审计轨迹，不作为Chrome证明。e768改为测试文件级test.use({channel:'chrome'})，原三个场景在真实Google Chrome156中3/3通过、0失败/跳过、23.7秒。attachment-google-chrome-e768-result.json及日志ZIP含实际Google exe同进程启动与CDP版本；10图及HTTP摘要保留。应用backend/frontend/src/templates/锁定依赖与447d相同。
