# PARTY-VERSION-INTEGRATION-01

- 基线 `b7ce265833320cc62a7b9aa57e08880f6013203f`（`codex/integration-validation-04`）；完整合入主体来源 `7cc8c4bf0249a3de53809836b7b3f233476a1648`，冻结测试代码 SHA `e7329cf29b43a7b2da7c6a90e32558234de0a3e0`。本报告提交只增加台账和证据。
- 后续对照 `aa15c9ba7584599e918c1dd14723d31e31158b3d` 与本分支共同祖先为上述 b7ce。它包含内部工作区标签、应用壳和身份接线，本轮未将该分支合入，不宣称已完成两者集成；后续须保留其接线并验证草稿、路由及账号隔离。
- `models.py`、`urls.py` 冲突各按双方内容局部保留；保留新品提醒 `0109_new_product_reminders` 与主体 `0109_quote_buyer_country_snapshot` 至 `0117` 的原样迁移，新增仅含依赖的 `0118_merge_party_reminders`。

## 定向验证

- PostgreSQL 17.10，隔离临时集群：从 `0109_new_product_reminders` 状态升级到 `0118`，迁移图及 `makemigrations --check` 通过。先在旧状态建立合成客户、旧报价（已保存买方名称、收件人、地址）及新品提醒，再升级；断言三个原快照、历史 `buyer_tax_id IS NULL`、提醒记录及迁移记录均保留。`snapshot-upgrade-result.json`、`snapshot-upgrade-verify-old.log`、`snapshot-upgrade-run_upgrade.py`。两次升级验证各退出 0，临时集群清理完成。
- 同一 PostgreSQL 候选：`run_postgres.py` 执行主体申请、历史快照、采购/销售替换、并发、提醒和报价输出等定向测试 213 项，0 跳过，退出 0；模拟受保护回退被预期拒绝（回退命令退出 1），确认原快照仍在，相关退出码见 `result.json` 和 `party-tests.log`。
- 前端：`npx vitest run tests/document-party-versions.spec.js tests/party-replacement-form.spec.js tests/new-product-reminders.spec.js --environment jsdom`，13/13，退出 0。
- Chrome 隔离 SQLite 和合成账号：`party-replacement-extended-20261106.spec.js` 1/1，销售及采购桌面/390px，包含原单资金、收货、发货及库存事实前后对照；`party-replacement-quote-real.spec.js` 1/1，报价替换和 PI。截图、结果及脱敏日志在本目录。两个合成账号不证明自然人独立。
- 合成 PI 与实际 XLSX：`generate_pi.py` 在内存 SQLite 生成无折扣、有折扣两套，PI 和 XLSX HTTP 200；已批准主体修改后修改客户主档，单元格仍使用批准快照。见 `no-discount.*` 和 `with-discount.*`；模板中的公司和银行值已换成合成内容。
- 锁定依赖安装 `npm ci` 退出 0，报告 4 个 moderate 依赖告警；未自动升级。GitHub Actions 与本地全量按用户要求 **NOT_RUN**；原生打印继续延期。

## 历史报价输出和首发影响

PI 数据与 XLSX 使用同一验证：无扩展资料时使用报价已保存快照。旧报价的买方公司、收件人、地址、税号、邮箱或电话只要有需要输出的值为 `NULL`，包括旧税号未知，即返回 HTTP 422；明确空字符串可通过该项。非空的买方国家、联系人、账单地址、收货地址在现有模板没有独立位置时返回 422；已保存非空卖方国家、税号、账单地址、收货地址、收件人同样被拒绝。卖方关键资料未知或与保存模板不一致、审批链或主体资料无效也拒绝。历史值不自动从主档填补、不改写原快照。

报价详情的 PI 预览与 Excel 导出把服务端错误展示在页面操作错误区；列表导出以“导出 [报价号] 失败”提示；新建后导出失败提示报价已保存但 Excel 导出失败。服务端说明“未知与留空无法区分”或“模板没有独立位置”，并返回字段名称；现有通用错误格式可能显示英文字段键。

**首发结论：条件性阻断。** 如首发业务需要输出上述受影响旧报价，则该单无法生成 PI/XLSX，需在不伪造未知事实的前提下先核实并采用经授权的主体修订或模板处理方案。两套资料明确的合成样本可正常出单，且新报价编辑器默认税号为空字符串；这不证明所有新单或所有真实历史数据可输出。没有访问真实业务库，受影响数量与首发业务覆盖仍待用户用真实资料核查，不可宣布首发全面无阻。

公开证据只含合成资料，浏览器私有原始日志含临时隔离令牌，保存在本地未提交；所提交摘要及文件哈希见 `manifest.json`。未合并 master、不部署、不启用正式 RBAC、不改真实历史。
