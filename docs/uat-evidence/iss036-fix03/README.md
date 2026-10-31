# ISS-036-FIX-03 历史交易单位快照语义冲突验收记录

日期：2026-10-27
规则来源：用户 2026-10-24 规则包 `ISS-036_允许合理尾箱、不得破坏最小计量单位.md`
统一基线：`46353a5436637832f5adadb7bdef6b45cdeada23`
分支：`codex/fix-iss036-snapshot-conflicts`
实现提交：`0189b87b75ff1694d6e368fe2998f68e4d3bface`

## 复核结论

当前 `ShipmentPackageSerializer.validate` 只比较历史快照的 `factor`，无法识别同系数但 `base_unit`、`unit` 或 `allow_fraction` 不同的交易单位语义。本轮检查 `TradeUnitLine`、`SKUTradeUnit` 与 `normalize_trade` 后确认：快照中的换算/拆分语义字段为 `factor`、`base_unit`、`unit`、`allow_fraction`；`name` 只用于展示，供应商、启用状态、默认状态及备注不在历史快照中，也不影响本校验的换算语义。

修复使用完整四字段语义键。快照缺失、非字典、factor 缺失/不可解析/非有限/非正数、单位字段缺失或类型无效、allow_fraction 不是布尔值时，继续按歧义数据处理，不从当前 SKU 或交易单位推断。语义冲突时不选择优先快照，也不增加不可拆分限制；完全一致的有效快照仍执行限制，允许分数快照保持可分数装箱，`factor=1` 的不可拆分单位继续生效。

## 回归覆盖

- 不同 `factor` 的历史冲突：既有回归继续确认不增加不可拆分限制。
- 相同 factor、不同 `base_unit`：不增加不可拆分限制。
- 相同 factor、不同 `unit`：不增加不可拆分限制。
- 相同 factor、不同 `allow_fraction`：不增加不可拆分限制。
- 完全一致的语义快照：仍拒绝非法分数；仅展示 `name` 不同不改变语义。
- 缺失 factor、非字典、非法 factor：不触发 500，不推断限制。
- factor=1、factor=5、合法尾箱、混装及允许分数：既有回归继续覆盖。

未修改库存、发货数量、采购、财务金额、付款规则或历史数据；未新增数据库迁移。

## 本轮测试

以下命令均在本地隔离 SQLite、开发身份下执行；未运行 GitHub CI、未连接生产 PostgreSQL、未部署：

- `python manage.py test crm.tests.test_actual_packing --verbosity 1`：39 项通过。
- `python manage.py check`：通过，`System check identified no issues (0 silenced)`。
- `python manage.py makemigrations crm --check --dry-run`：通过，`No changes detected in app 'crm'`；同时出现既有 `unable to open database file` 迁移历史检查 warning，不影响本次无变化结论。
- `python manage.py test crm.tests.test_actual_packing crm.tests.test_trade_units --verbosity 1`：55 项通过。
- `npm run test:unit`：156 项通过。
- `npx vitest run tests/trade-units.spec.js --environment jsdom`：1 个文件、4 项通过。首次非提升权限运行因 Worktree `node_modules/.vite-temp` 创建 EPERM 失败，权限重试通过。
- `npm run build`：通过，2018 个模块转换；仅有既有大 chunk warning。首次非提升权限运行同样因 Vite 临时目录 EPERM 失败，权限重试通过。
- `git diff --check`：通过。

异常日志中的预期 `Bad Request` 和故障注入 traceback 由既有测试主动覆盖，测试最终结果为 `OK`，不代表新增业务失败。

## 未解决事项

ISS-036 继续保持 `FIXED_PENDING_REVIEW`。同一发货中同 SKU 多个历史交易单位快照若语义冲突，本轮只安全地按歧义处理；业务仍需明确历史归属/优先级及可复核规则，才能决定后续是否允许更精细的校验。生产 PostgreSQL、真实物流数据、代理环境和 CI 未验证；本轮没有浏览器或视觉变更，因此没有新增 Chrome 截图。

ISS-018 的最近核实引用已从 FIX-02 实现提交改为集成验证 HEAD `46353a5436637832f5adadb7bdef6b45cdeada23`，其 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING` 状态保持不变。
