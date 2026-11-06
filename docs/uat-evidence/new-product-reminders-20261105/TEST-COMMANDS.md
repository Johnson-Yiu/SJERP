# 实际验收命令与环境

执行根目录为独立 worktree，未使用主工作区数据库。下列 `P` 的实际绝对路径为：
`D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/.tmp/closeout-python312/Scripts/python.exe`。
版本 Python 3.12.16 / Django 6.0.9；Node 使用本机安装。锁文件未改。

## 应用源码及本地回归

- 本包定向：根目录 `P backend/manage.py test crm.tests.test_new_product_reminders --verbosity 2`。
- 最终迁移一致性：`DATABASE_URL=sqlite:///:memory:`，`P backend/manage.py makemigrations --check --dry-run`，No changes detected。
- 前端依赖：frontend 中 `npm ci --offline --no-audit --no-fund`。
- Node 全量：frontend 中 `node --test --test-concurrency=1`；PATH 首项为 P 所在目录，设置 ISOLATED_TEST_PYTHON=P。原始默认全量和重复专项均保留。
- Node 失败专项：`node --test --test-name-pattern="two independent worktree runtimes" infrastructure-tests/runner-validation.test.mjs`；沙箱内、外保持原 120 秒预算与断言。
- 前端最终全量：frontend 中 `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers 2 --reporter verbose`。
- 字体专项：frontend 中 `node --test tests/detail-drawer-typography.spec.js`。
- 构建：frontend 中 `npm run build`。

## SQLite 全量

原始串行 `P manage.py test --verbosity 1` 在 backend 执行，发现 OpenSSL 环境缺项；错误保留。Django 自带 --parallel 在 Windows 对动态导入的财务测试类不可序列化，不据该中断宣称全量完成。

替代执行：根目录 `P docs/uat-evidence/new-product-reminders-20261105/scripts/run-sqlite-full.py`。三个独立串行进程分别使用内存 SQLite 和独立 MEDIA_ROOT，沿用 DevelopmentAccessTestRunner 及全部原测试。完整发现列表、三个选择列表按 Counter 比较，证明所有 ID 及重复次数完全一致；不删断言，不跳过额外用例。脚本记录源码 HEAD 并检查应用目录在运行首尾不变。

环境：APP_STAGE=development、DJANGO_DEBUG=1、DEVELOPMENT_SUPERADMIN=1、RBAC_ENFORCEMENT=0、AUDIT_LOG_ENABLED=1、OPS_TEST_OPENSSL=`D:/Program Files/Git/usr/bin/openssl.exe`。输出子目录由 REMINDER_FULL_OUTPUT 指定；407d9dc 对应 sqlite-final，e168a532 对应 sqlite-frozen-e168。正式开发默认配置未改。

## 真实 PG17.11

根目录：`P docs/uat-evidence/review-integration-batch-20261104/run-postgres-regression.py --postgres-bin C:/Users/Johnson/AppData/Local/Temp/sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f/pgsql/bin`。

REVIEW_TEST_LABELS=`crm.tests.test_new_product_reminders`，REVIEW_EVIDENCE_ROOT 指向本报告内各自新目录。脚本创建其自有隔离集群、源库、测试库与媒体；测试库与备份源分开，原有业务数据库未连接。第一次沙箱内 pg_ctl restricted token 失败；获批在沙箱外执行，不绕过工具审批。原脏源码拒绝和各次原始结果分别保存。

## 浏览器、真实 HTTP、数据库

- 九配置全量沿用 `node docs/uat-evidence/local-release-validation-20261105/browser-suite.mjs`，RELEASE_CANDIDATE_SHA=17d1775077c03954a866bde354f6c30a3f57652f；RELEASE_EVIDENCE_ROOT 为 full-browser；运行中后续独立组件补修的限制已在 README 说明。
- 超时原文件补验：frontend 中 `node scripts/run-isolated-browser-tests.mjs --business-test iss008-chinese-aliases.spec.js`，自有 DB/媒体/进程清理见日志。
- `scripts/chrome-uat.mjs`、`scripts/chrome-layout.mjs` 为前期真实 Chrome 自动化；只操作本地合成资料。用户后续指定后，交互验收只使用内置浏览器，完成截图和 DOM 归档。
- 本包 UAT 地址为 API 8176、Vite 5276，数据库 `.tmp-reminder-uat.sqlite3`，媒体 `.tmp-reminder-media`；单独受限 HTTP 进程 8177 使用该合成库的独立副本 `.tmp-reminder-scope.sqlite3`，不更改默认开发身份。
- `scripts/http-captured-records.py`、`scripts/http-captured-scope.py` 是本次具体记录 ID 的捕获脚本；受限会话只保存在临时本机文件，不发布凭据。重新执行须先准备同等合成样本及新会话，不能指向真实库。
- `scripts/verify-captured-database.py` 独立通过 ORM 重读 Chrome #2/#3、内置浏览器 #56 和 HTTP #57，核对版本、审计及自由文本；stdout 与真实 HTTP JSON 分开保留。
- 本地合成数据库副本仅在 .private 保留，SHA256 与端口释放证据见 cleanup.json；不推送 session 或原始数据库。

GitHub Actions NOT_RUN；所有提交 [skip ci]，不合 master、不部署。

最终 PG17 使用相同命令与 REVIEW_TEST_LABELS，REVIEW_EVIDENCE_ROOT 为 pg17-final，源码 013be1f5。该源码相对全量 e168a532 仅修正测试线程的显式连接关闭，不改变业务逻辑或断言。
