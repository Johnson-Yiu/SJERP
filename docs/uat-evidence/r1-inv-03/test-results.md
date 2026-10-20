# R1-INV-03 测试执行结果

## 已通过

```text
python manage.py test crm.tests.test_inventory_reference --verbosity 1
Ran 2 tests in 2.306s
OK

node --test src/views/PurchaseOrderPage.test.js
tests 9 / pass 9 / fail 0

npm run test:unit
tests 137 / pass 137 / fail 0

npm run build
vite build: success, 2005 modules transformed

python -c "...call_command('test', verbosity=1)"  # 临时将 settings.MEDIA_ROOT 指向隔离媒体目录
Ran 770 tests in 292.948s
OK (skipped=13)
```

全量 SQLite 测试保留项目既有的 13 个 skip；输出中的 Bad Request、Forbidden 和受 mock 主动触发的 Internal Server Error 均属于既有错误分支断言，最终汇总为 OK。第一次直接运行曾因受管 worktree 无法创建 `backend/media` 报 1 个环境错误，未修改代码，之后以测试进程级 `MEDIA_ROOT` 覆写重跑通过。

## 未执行/阻断

- 本机没有可用的 PostgreSQL 监听服务（5432 无监听，未安装 `docker`/`psql`），因此没有伪造 PostgreSQL 结果。
- GitHub Actions 按用户确认的本月免费额度耗尽策略暂缓；没有创建 [skip ci] 以外的无意义提交，也没有反复触发 CI。

## 范围回归

后端测试包含既有库存、采购、订单、财务和迁移回归；本轮新增的接口测试确认库存详情复用权威指标、无库存权限时数量为 `null` 且库存详情接口返回 `403`。前端自动测试确认采购编辑器只读库存参考接入，不改变采购数量/保存契约。
