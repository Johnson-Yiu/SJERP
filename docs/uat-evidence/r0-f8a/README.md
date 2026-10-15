# R0-F8A 原始浏览器证据

2026-10-15，独立r0f8a-ux.sqlite3，Django8115/Vite5202，开发超级管理员。全部为合成R0F8A资料。

[46张截图](SCREENSHOTS.md)、[机器清单](manifest.json)、[原始采集记录](capture-records.json)。`generate_manifest.py`只读取原图核对请求、DOM、JPEG实际像素和文件名，计算SHA-256，不修改图片。

| 前缀（除404均三尺寸） | 操作状态 |
|---|---|
| certificates-list | 有效/临期/过期/无有效期样本与长编号列表 |
| certificate-create | 新建分组表单，文件URL和日期输入 |
| certificate-error | 超150字符实际API拒绝，中文错误及输入保留 |
| certificate-detail | 本轮新建临时证书详情，无有效期与文件入口；其后已按场景删除 |
| certificate-edit | 临时证书编辑签发机构 |
| certificate-expiry-detail | 既有合成样本日期改10月25日，服务端10天后到期，长内容与产品入口 |
| certificates-expired-filter | 已过期筛选及刷新恢复 |
| certificates-empty | 搜索无结果空态 |
| certificate-missing-file-1024 | 真实缺失链接404，仅此尺寸，不证明任何正向文件内容/授权 |
| hs-list | 长描述、备注与状态，表格局部滚动 |
| hs-create | 新建表单；示范重复编码保存前 |
| hs-duplicate-error | 真实重复编码拒绝，已重拍自然中文提示 |
| hs-edit | 本轮新编码停用前的编辑 |
| hs-assignment-error | 停用编码分配新产品被拒绝，选择保留 |
| hs-assignment | 36产品中筛9项批选，显示1项从其他编码移入 |
| hs-selected-reopened | 保存9项后重开只看已选，准确9项；其后解除1项为8项 |

使用受支持Codex内置浏览器截图API直接保存原始JPEG，不编辑。视口切换后先观察绘制，再采集；不符图剔除重拍，详情见验收报告。页面截图是当时操作状态，不代表种子或最终隔离库始终相同。

`seed_isolated.py`只允许指定空SQLite库。先在backend设置DATABASE_URL=sqlite:///r0f8a-ux.sqlite3并migrate，再用manage.py shell -c读取UTF-8脚本执行。不得对用户库运行。

[测试摘要](TEST-RESULTS.md)与[完整验收矩阵](../../R0-F8A-产品证书与HS编码验收.md)。自动化、Codex实际目视与ChatGPT独立视觉分别记录，后者待审；ISS-007/017等文件与授权事项保留。
