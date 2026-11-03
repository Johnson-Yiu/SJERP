# ISS-037 卖方与模板冻结：实施及待核验记录

固定基线 `a55469c1b07e4f13037c6644c69d8a35ef0496a0`；分支 `codex/r1-iss037-seller-template-freeze-20261103`。本项仍需集成验证、权限和独立复审，不能据此关闭 ISS-037。

## 实现范围

新报价保存时将卖方、银行资料、XLSX 模板字节、渲染配置和打印 HTML 资源以摘要关联到版本；修订继承父版。正式 API、预览、打印和 XLSX 使用保存的资源。历史报价缺少来源或摘要校验失败时拒绝以当前资料重建，未改动已发布迁移或批量回填。源代码检索没有发现旧正式报价文件的归档入口；这不证明外部没有原件，不能声称旧原件已经可访问，需另行核实。摘要能检测不一致，不能防止有权同时修改内容和摘要的数据库管理员；普通模型操作有保护，数据库级不可变性仍需独立审查。

未保存的新报价预览读取当前模板并明确是草稿；修订草稿预览读取父版，历史来源缺失时拒绝预览，不用当前卖方冒充。修订预览买方使用父版快照，空值不填入当前主档。实际正式打印资源仍需对图片加载和完整历史文件保真进行专项复审。

## 实际验证

CPython 3.12.16、Django 6.0.9；16 项锁定版本相符，`pip check` 通过。所有数据为合成数据，使用独立 SQLite、临时 MEDIA_ROOT，未连接业务数据库。

- `crm.tests.test_quote_template_snapshot crm.tests.test_quote_template_migration`：12 项通过；包含新建与修订预览来源、历史未知拒绝、模板变更后 API 和实际 XLSX 单元格比对、失败回滚及迁移正反向。
- `crm.tests.test_quotes crm.tests.test_quote_unknown_buyer crm.tests.test_iss020_quote_export crm.tests.test_quote_revision_tree`：84 项通过。首次误指定不存在的 `test_quote_xlsx` 模块导致导入错误；更正为实际模块后重跑通过。
- `npm run test:unit`：177 项通过；`npm run build` 通过，保留现有大包警告。
- 真实 Chrome：已保存 PI 在 [1440px](screenshots/saved-pi-1440.png)、[390px](screenshots/saved-pi-390.png) 使用隔离 API 预览、点击打印入口并观察到 iframe 的 `beforeprint` 事件；这不等同于核实最终打印机或 PDF 文件。新增[修订草稿场景](screenshots/revision-draft-preview-1440.png)首次因合成夹具未填写修订说明而超时，填写说明后重跑三项全部通过。
- 初次 [CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41621677414) 的 Backend 与 PostgreSQL 通过，Frontend 的 Vitest 1 项失败：旧测试监听主窗口 `print`，实现改为打印保存版本的 iframe。测试已改为验证 iframe 的打印调用并保留历史内容和导出断言，针对 `tests/final-polish.spec.js` 重跑 19 项通过；新提交完整 CI 尚需执行。
- 第二次 [CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41624923109) 的两个 Backend 均通过，Frontend 有三项浏览器失败，原测试在外层文档查找已移入 iframe 的金额、收件人或图片。保留原有内容及图片断言并改为定位 iframe 后，收件人快照与 ISS-007 图片的真实隔离浏览器专项分别通过；金额显示测试是原有 API mock 场景，补充新接口的合成 `print_html` 后通过，不作为真实后端证据。

## 待办

核实打印图片与实际输出、模板权限及旧文件归档；执行 PostgreSQL 和完整前端集成 CI；验证未保存新建/修订草稿和错误状态的真实浏览器交互。当前不包含完整双方主体字段、审批分离或历史来源核实流程。
