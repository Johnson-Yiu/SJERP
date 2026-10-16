# R0-F8C 原始浏览器证据

2026-10-16；独立r0f8c-ux.sqlite3，Django8117/Vite5204。始终使用服务端开发超级管理员，不绑定员工、不启用RBAC。仅在合成角色保存权限；默认角色只读查看。

| 前缀（均3尺寸） | 实际状态 |
|---|---|
| organization-initial | 默认最高模板锁定、组织摘要和可搜索角色；最终文案 |
| organization-tree | 展开部门/岗位，合成长名称；最终文案 |
| matrix-draft | 合成角色勾选，查看/新建联动及未保存标记 |
| unsaved-confirmation | 真正dirty角色切换确认，先继续编辑再放弃 |
| matrix-saved | 第一次实际保存成功、服务器回读；过程状态 |
| save-service-error | 停止8117后保存报代理500，草稿保留、旧成功清除 |
| matrix-reopened | 恢复API后保存重试，刷新重开勾选一致 |
| access-denied | 开发身份直接打开拒绝页看布局；不声称开发超级管理员实际被权限拒绝 |
| access-service-error | 隔离API停服，current-operator真实读取失败；无假返回路径 |
| matrix-final | 最终保留CRM/共享主数据说明，筛选客户模块及已保存3项；矩阵/按钮均可见 |

[SCREENSHOTS.md](SCREENSHOTS.md)、[manifest.json](manifest.json)、[采集记录](capture-records.json)保存30张原始JPEG的视口/DOM/像素/SHA-256与URL/滚动位置。原图未经编辑、缩放或重编码。部分图是过程中的真实文案/选中状态，不代表最终库状态始终相同；最终矩阵以matrix-final为准。原始截图通过受支持API正常归档，独立图片视觉仍待ChatGPT审查。

[实际数据库核对](database-verification.json)证明预置角色/权限未变、员工0、RBAC关闭、开发身份保持启用。[seed_isolated.py](seed_isolated.py)只允许指定专用库；[verify_isolated.py](verify_isolated.py)只读核验。数据库本体不提交。真实后端/代理HTTP日志与访问状态失败/恢复DOM单独归档；模拟401/403/网络和只读身份见自动回归，不能替代正式员工UAT。

[主验收报告](../../R0-F8C-组织权限与访问状态验收.md) · [自动化记录](TEST-RESULTS.md)。
