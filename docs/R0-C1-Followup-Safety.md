# R0-C1 — CRM Follow-up Safety

基线：9c08eb5b7836e195b3c034fcf90518f0c1160b34。范围仅 FollowUp / Customer.next_follow_up。

## 保存与计划规则

前后端都拒绝 content/result 同时为空或仅空白；主题、下一步仍可选。部分更新结合原记录检查，拒绝把已有沟通内容全部删空。

新增 next_follow_up_mode：keep 默认保留、set 设置日期、clear 明确取消。set 必须有日期；clear 显式提交非空日期返回 400，其余日期规范化为空。主列表编辑器与客户详情新增跟进均展示三个 radio；仅 set 显示日期控件；keep 显示当前客户计划；clear 提示“这会清除该客户当前的下次跟进日期。”，不额外弹确认。保存前错误在按钮旁可见。

客户计划按 followed_at 降序、id 降序寻找最近 set/clear，跳过 keep。保存、编辑、删除及更换客户重新计算；更换客户时双方都重算。无历史显式决定时新增/删除 keep 保留客户已有手工日期；删除或改成 keep 的最后一个显式决定在没有更早决定时清空。当前待跟进的 FollowUp 查询使用客户当前计划，避免最新 keep 记录无自身日期导致漏出待跟进队列。客户阶段函数原样保留；未修改 Dashboard 页面或其他业务逻辑。

## Migration

0073_followup_next_follow_up_mode：新增字段默认 keep；历史有日期标 set，无日期标 keep。RunPython 仅 bulk update FollowUp，不调用信号、不更新 Customer。开发环境 migration apply PASS，makemigrations --check --dry-run / Django check PASS。

## 自动验证

新增后端 8 项测试覆盖 A–L：空白沟通、content-only/result-only、keep 手工计划、set/clear、非法日期、删除恢复、keep 越过 set/clear、客户迁移、部分编辑、legacy backfill 不改客户、高位 id 同时间排序和当前待跟进查询。旧测试中原依赖空日期取消的场景改为显式 clear，有日期计划改为显式 set；不是放宽断言。后端完整 593 项 PASS（SQLite 跳过 10 项 PostgreSQL 专用测试）。

前端新增 5 项组件交互测试，覆盖主编辑器与客户详情快捷新增的前端拦截、三种安排、隐藏日期、null payload 和当前计划辅助提示。完整 Vitest 43 文件 438 项、Node 111 项、独立详情排版 1 项 PASS；production build PASS（已有 chunk 大小提示）。最终 production HEAD 的 CI 链接和三个作业结果在交付回复中记录。

## Chrome UAT

真实 Chrome + localhost:5191，仅操作现有专用测试客户 UAT-SR-FINAL-20261009-NEW（编号 202610090010）。

1. 客户/时间/方式齐全但 content/result 空白时保存被阻止，提示与保存按钮同时可见；未创建记录。
2. UAT-R0C1 保留当前跟进计划：仅填写 content，默认 keep，保存后重新打开新建编辑器，当前计划仍 2026-10-16。
3. UAT-R0C1 设置新的跟进日期：仅填写 result，set + 2026-10-25；保存后列表显示日期，重新打开新建编辑器当前计划为 2026-10-25。
4. UAT-R0C1 明确取消后续跟进：clear 提示明确，无日期输入；保存后列表日期为空，重新打开新建编辑器显示“暂无跟进日期”，客户详情下次跟进为“未安排”。
5. 客户详情快捷新增回归：默认 keep，日期隐藏；空沟通保存被同一文案阻止，radio 与错误均清晰可见，取消未保存表单。

三条 UAT-R0C1 记录保留供审查，不删除旧测试记录。中文可见文案人工检查完成；未做页面整体重构。

## 证据

图片仅 ux-review-evidence：ux-review/r0-c1-followup-safety/

- R0C1_01_followup_content_required.png
- R0C1_02_keep_existing_schedule.png
- R0C1_03_set_new_schedule.png
- R0C1_04_clear_schedule.png

4/4 完成，无缺失。Chrome 原始 JPG 只转 PNG，无裁剪、拼接或重绘；不进入 master，不合并证据分支。BLOCKED：无。最终 production/evidence SHA 和 exact-head CI 在交付回复记录。完成后停止，等待独立 ChatGPT 审查。
