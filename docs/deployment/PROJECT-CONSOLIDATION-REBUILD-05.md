# SJERP PROJECT-CONSOLIDATION-REBUILD-05

新仓库 E:/ERP/SJERP-Clean 从 GitHub master 独立克隆，源码 7b4e666758ba31a2afd36a7ef81635085a27ff24。旧工作树保留至数据备份和恢复门槛满足。发布和维护检出继续遵循 RELEASE-SLIM.md 与 PILOT-RECOVERY.md，已有发布 SHA 不变。

已验证 Django check、迁移无缺项、独立合成 SQLite 的迁移及登录后客户 API 回读、锁定 npm 依赖安装、SKU 定向 Node 测试和前端构建。合成库和媒体位于仓库外。未导入旧开发数据库。

受限备份位于 E:/ERP/SJERP-Archive-20261115-134619。Git bundle 已校验并从中恢复引用到独立裸仓库，完整对象检查成功。逐文件备份还需比对全量清单、处理失败项并验证关键文件恢复，完成前不从旧环境删除对应内容。

当前主干包含后续维护的销售导入与财务收款实现以及 ALEX 只读预检脚本。旧独有提交与未提交成果保留，尚待按用途复审。此分支仅记录重建测试及流程，不进入主干作为业务修改。
