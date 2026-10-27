# ISS-002 依赖安全审计

## 审计结论

- 审计基线：`46353a5436637832f5adadb7bdef6b45cdeada23`
- 分支：`codex/audit-iss002-dependency-security`
- 审计日期：2026-10-27
- 最终提交：以本分支交付时 `git rev-parse HEAD` 为准；精确 SHA 见本任务交付回执。
- 范围：`frontend/package.json`、`frontend/package-lock.json`、`backend/requirements.txt`、后端实际 import/运行路径及干净环境验证。
- 本轮没有运行 `npm audit fix`、`pip-audit --fix`、GitHub Actions 或生产部署，也没有合并 master。

结论不是由 advisory 数量直接推导。初始锁定前端树确有真实 advisory，且 axios、Vue、DRF、Pillow 等均能在源码中找到实际使用路径；其中一部分只存在于测试/构建链，另一部分只在 SSR、Node adapter、GIS、cache middleware 或 authtoken 等当前应用未启用的路径中可达。对可做兼容性较低的补丁/次版本修复已实施并验证；Pillow 的修复需要跨越当前 `<12` 约束的重大版本，保留并登记为延期高风险项。

## 依赖清单与实际使用

### 前端直接依赖

| 依赖 | manifest 类型 | 本轮最终锁定版本 | 实际使用/结论 |
|---|---|---:|---|
| `@vitejs/plugin-vue` | dependencies（构建工具，分类偏宽） | 6.0.8 | 只在 `vite.config.js` 构建路径使用，无业务运行时 import |
| `axios` | dependencies | 1.21.0 | `src/api.js` 创建全局 API client，进入浏览器业务运行时 |
| `lucide-vue-next` | dependencies | 1.0.0 | Vue 页面图标；npm 安装时给出弃用警告，非本轮安全漏洞，未改名迁移 |
| `pinyin-pro` | dependencies | lockfile 解析版本 | 前端业务代码使用；本轮 audit 未报告 advisory |
| `vite` | dependencies（构建工具，分类偏宽） | 8.3.5 | `package.json` scripts 和 `vite.config.js` 使用；不进入生产 bundle，但因 manifest 分类会出现在 `--omit=dev` 安装集合 |
| `vue` | dependencies | 3.5.44 | `src/main.js` 及大量 `.vue` 文件使用，进入生产 bundle |
| `vue-router` | dependencies | 5.2.0 | `src/router.js` 及页面导航使用；本轮 audit 未报告 advisory |

### 前端开发依赖

| 依赖 | 最终锁定版本 | 实际路径 |
|---|---:|---|
| `@playwright/test` | lockfile 解析版本 | 浏览器测试工具 |
| `@vue/test-utils` | 2.4.11 | Vue 组件测试；依赖 `@vue/server-renderer` |
| `jsdom` | 30.0.1 | Vitest DOM 环境；引入 `undici` |
| `vitest` | 4.1.12 | Vitest 测试运行器；引入 `@vitest/mocker` |

锁文件为 lockfileVersion 3，最终干净安装为 227 packages，npm audit metadata 为 production 106、development 120、optional 27（总计 251 个节点；npm 的计数包含 peer/optional 展开方式）。

### 后端直接依赖

| requirements 约束 | 干净审计环境解析版本 | 实际使用路径 | 本轮结论 |
|---|---:|---|---|
| `Django>=5.2.17,<6.1` | 6.0.9 | 全部 Django settings、models、views、middleware | 已将最低安全下限上调；6.0.6 的 advisory 在干净环境清零 |
| `djangorestframework>=3.18.2,<4` | 3.18.3 | `crm/views.py`、serializers、routers、JSON/multipart parser | 已修复 parser/content negotiation advisory |
| `django-cors-headers>=4.7,<5` | 4.9.0 | `settings.py` middleware/app | 本轮无 advisory |
| `dj-database-url>=2.3,<4` | 3.1.2 | `settings.py` 数据库 URL | 本轮无 advisory |
| `psycopg[binary]>=3.2,<4` | 3.3.6 + binary 3.3.6 | PostgreSQL 配置/数据库驱动 | 本轮无 advisory |
| `Pillow>=11.0,<12` | 11.3.0 | `crm/services/sku_images.py`、Packing List/报价 Excel 图片路径 | 直接运行时高风险，修复需 12/13，延期 |
| `bleach>=6.2,<7` | 6.4.0 | `crm/serializers.py` HTML 清洗 | 本轮无 advisory |
| `openpyxl>=3.1.5,<4` | 3.1.5 | 报价、Packing List、Excel 导入导出 | 本轮无 advisory |
| `pycountry==26.2.16` | 26.2.16 | 已将国家目录 vendored 到 `crm/country_registry.py` | 本轮无 advisory；运行时不依赖动态读取国家库 |

`django-simpleui` 仅出现在当前全局 Python 环境的 `Required-by` 信息中，不在本仓库 requirements、settings 或 import 路径中，不纳入项目依赖结论。

## 前端 advisory 证据与处理

初始 `npm ci --ignore-scripts --no-audit --no-fund --no-progress` 后运行 `npm audit --json`：`2 moderate + 9 high = 11` 个漏洞节点；`npm audit --omit=dev` 为 7 high。最终定向升级后，两个命令均为 `0`。

| 节点/编号 | 初始范围 → 修复版本 | 类型与实际可达性 | 处理 |
|---|---|---|---|
| `axios`：`GHSA-vh66-26gq-q6x8`、`GHSA-9fr6-4gfg-395g`、`GHSA-c29m-xwm3-cm6r`、`GHSA-mghh-pgcx-3jjj`、`GHSA-x97p-jq2g-jp4f`、`GHSA-3pq3-5fj3-cg6v`、`GHSA-542g-h47m-68v8`、`GHSA-j8rh-479h-cp32`、`GHSA-4hqw-qxg8-jxx2`、`GHSA-m8m8-qj5v-23w3`、`GHSA-44g4-m2mj-wpvx`、`GHSA-r4gj-5m52-g5wh` | 1.0.0–1.19.0 → 1.21.0 | 直接生产依赖；`src/api.js` 真实使用。浏览器 bundle 不走 Node HTTP adapter，但配置污染/浏览器 adapter 相关 advisory 不能只按“前端”排除。 | `axios` 锁定 1.21.0；其转依赖 `follow-redirects` 定向更新到 1.16.2。 |
| `vue` / `@vue/server-renderer`：`GHSA-g2v6-rqmx-r4w6` | `<3.5.42` → Vue 3.5.44 | Vue 是生产运行时；当前应用没有 SSR server-renderer import，但 Vue 包依赖树包含该节点。 | Vue 及 compiler/runtime/server-renderer 同步到 3.5.44。 |
| `vite`：`GHSA-698v-4r3x-3vcv`、`GHSA-r825-w8mm-5pxw`、`GHSA-587h-7wmj-h5pm`、`GHSA-9jrq-w75r-8gcw`、`GHSA-rq7h-c2jc-7f22`、`GHSA-vfpm-58rq-9qcg` | 8.2.0–8.2.2 → 8.3.5 | manifest 中误列为 production dependency，但实际只在 dev/build server 及构建脚本出现；外部暴露 Vite dev server 仍需单独限制。 | 同大版本更新到 8.3.5，生产构建通过。 |
| `@vitest/mocker`：`GHSA-qxg6-89mg-rqv8`、`GHSA-xp26-3454-mjgp`；`vitest` 节点受其影响 | `@vitest/mocker` ≤4.1.11 → 4.1.12 | 开发测试依赖，不进入生产 bundle。 | Vitest 及相关包更新到 4.1.12。 |
| `follow-redirects`：`GHSA-q3jh-wrc6-jgq8`、`GHSA-8r9p-f939-6h3c` | 1.16.0 → 1.16.2 | axios 转依赖；初始 `--omit=dev` 仍可见，原因是 axios 的 production tree。 | 定向 transitive update。 |
| `nanoid`：`GHSA-2v37-7h3g-55p8` | <3.3.18 → 3.3.20 | postcss/compiler 构建链转依赖，非业务运行时。 | 锁文件定向更新。 |
| `source-map-js`：`GHSA-68fv-2mgg-jv7q` | <1.2.2 → 1.2.2 | Vue compiler/PostCSS/测试链转依赖；不作为业务输入解析器。 | 锁文件定向更新。 |
| `brace-expansion`：`GHSA-q2hr-2g5m-vwhr`、`GHSA-qhr7-859c-m2p7`、`GHSA-6j4f-fj2g-mc7p` | ≤2.1.6 → 2.1.7 | 测试工具链 dev-only。 | 锁文件定向更新。 |
| `undici`：`GHSA-3wwx-pv8p-q78v`、`GHSA-pmjh-fq2x-6v4x`、`GHSA-r53p-7pc4-xj5r`、`GHSA-rfgv-xxqx-mfg5`、`GHSA-3xpg-4rpp-hhhm`、`GHSA-2jfj-6hjv-fm6j`、`GHSA-2gqq-gqf2-x968`、`GHSA-w293-vg96-wgc3`、`GHSA-8436-99hf-9mmv`、`GHSA-vp8m-p9jh-q5pm`、`GHSA-rx4f-c7p8-82vq`、`GHSA-4qv8-2p9j-2685`、`GHSA-f72v-6w45-q472`、`GHSA-xjj6-f33q-929c` | 8.0.0–8.12.1 → 8.12.3 | `jsdom` 测试依赖 dev-only。 | 锁文件定向更新。 |

初始 warning `glob@10.5.0` 与 `lucide-vue-next@1.0.0` 的 deprecated 提示不是 npm audit advisory；本轮没有借审计机会迁移图标库或重构构建链。

## Python advisory 证据与处理

本机原有全局环境版本为 Django 6.0.6、DRF 3.17.2、Pillow 11.3.0。仓库没有 Python lock 文件，因此分别用 `pip check`、项目 requirements 和临时隔离环境审计，不能把全局环境中的其它包当成项目依赖。

### 已修复

- Django：当前环境的 5 个 advisory identity 为 `CVE-2026-48588`、`CVE-2026-53877`、`CVE-2026-53878`、`CVE-2026-15830`、`CVE-2026-15307`（对应 PYSEC/GHSA 别名由 pip-audit 返回）；修复版本覆盖 6.0.7/6.0.8。源码未启用 `UpdateCacheMiddleware`/`cache_page`、GeoDjango/GDAL 或绕过 `HttpResponse` 的 header 输出路径，但仍将 requirements 下限安全地上调到 5.2.17，使解析到的 6.0.9 清零这些 advisory。
- DRF：`CVE-2026-114136`（JSON parser 可被攻击者命名 codec 放大内存）、`CVE-2026-114138`（无上限 Accept 协商 CPU 消耗）在当前 API 默认 parser/content negotiation 路径可达；`CVE-2026-114137`（`TokenProxy.delete()`）因项目使用 session authentication、未启用 `authtoken`，不属于当前可达路径。requirements 下限更新到 3.18.2，干净环境解析 3.18.3，3 项 advisory 均清零。

### 延期

Pillow 11.3.0 的 pip-audit 结果包含以下去重后的 CVE/GHSA identity（pip-audit 同时返回了 PYSEC 别名和重复记录）：

- 修复到 12.1.1：`CVE-2026-25990`。
- 修复到 12.2.0：`CVE-2026-40192`、`CVE-2026-42308`、`CVE-2026-42309`、`CVE-2026-42310`、`CVE-2026-42311`。
- 修复到 12.3.0：`CVE-2026-54058`、`CVE-2026-54059`、`CVE-2026-54060`、`CVE-2026-55379`、`CVE-2026-55380`、`CVE-2026-55798`、`CVE-2026-59197`、`CVE-2026-59198`、`CVE-2026-59199`、`CVE-2026-59200`、`CVE-2026-59204`、`CVE-2026-59205`。
- 修复到 13.0.0：`CVE-2026-112390`、`CVE-2026-112391`、`CVE-2026-112392`、`CVE-2026-112393`、`CVE-2026-112395`、`CVE-2026-112396`、`CVE-2026-112397`、`CVE-2026-112398`、`CVE-2026-112399`、`CVE-2026-112400`、`CVE-2026-112401`、`CVE-2026-112402`、`CVE-2026-112404`、`CVE-2026-112406`、`CVE-2026-112891`、`CVE-2026-112892`、`CVE-2026-112893`、`CVE-2026-112894`、`CVE-2026-112895`、`CVE-2026-112896`、`CVE-2026-112897`、`CVE-2026-112899`、`CVE-2026-112900`、`CVE-2026-112901`、`CVE-2026-114501`、`CVE-2026-96636`、`CVE-2026-96637`、`CVE-2026-96638`、`CVE-2026-96639`、`CVE-2026-96640`、`CVE-2026-96641`、`CVE-2026-96642`、`CVE-2026-96643`、`CVE-2026-96644`、`CVE-2026-96778`、`GHSA-78g4-xqwv-q3g8`。

Pillow 被 `crm/services/sku_images.py` 的授权 SKU 图片缩略图和 Excel 图片导出实际使用，不能标记为“仅测试依赖”。但从 `<12` 到 12/13 是重大版本跨越，需另开兼容性任务，先不改变图片解析、存储、历史文件或业务代码。上线前关闭条件：固定目标 Pillow 版本、图片格式/动画/EXIF/超大图片回归、旧 Excel/Packing List 回归、生产镜像重建和独立安全复审全部通过。

## 兼容性与可复现性

1. 前端将本次审计涉及的所有 direct `latest` 声明固定为已验证的精确版本：`@vitejs/plugin-vue` 6.0.8、axios 1.21.0、`lucide-vue-next` 1.0.0、Vite 8.3.5、Vue 3.5.44、`vue-router` 5.2.0、Vitest 4.1.12；没有主版本升级，也没有迁移图标库，减少下次安装漂移。
2. 后端只上调 requirements 最低版本，不修改模型、API、权限、财务数据或业务代码；干净环境实际解析 Django 6.0.9、DRF 3.18.3。
3. Vite 和 `@vitejs/plugin-vue` 仍位于 manifest 的 dependencies，属于现有打包分类问题；本轮未重排依赖区块，避免影响现有部署流程。生产镜像若只发布 `dist`，应在后续部署任务中明确 build stage/runtime stage 边界。
4. requirements 仍不是 lock 文件；生产环境必须记录实际解析版本并使用受控安装，不能只依赖宽范围约束。

## ISS-002-MANIFEST-PIN-FIX 复验

本次只将 `frontend/package.json` 中剩余的三个 `latest` 固定为当前 lockfile 已验证版本：`@vitejs/plugin-vue` 6.0.8、`lucide-vue-next` 1.0.0、`vue-router` 5.2.0。`package-lock.json` 仅同步根 package metadata，解析后的依赖树未变；未迁移图标库、未升级 Pillow、未修改业务代码。

| 本次命令 | 结果 |
|---|---|
| `npm ci --ignore-scripts --no-audit --no-fund` | 通过，added 227 packages；保留既有 deprecated warning |
| `npm audit` | 通过，0 vulnerabilities |
| `npm audit --omit=dev` | 通过，0 vulnerabilities |
| `npm run test:unit` | **156 passed，0 failed** |
| `npm run test:trade-units` | **1 file / 4 tests passed** |
| `npm run build` | **通过**；Vite 8.3.5，2018 modules transformed；保留既有 >500 kB chunk warning |

## 实际检查日志

| 检查 | 结果 |
|---|---|
| `npm ci --ignore-scripts --no-audit --no-fund --no-progress`（最终锁文件） | 通过，227 packages |
| 初始 `npm audit --json` | 2 moderate、9 high；证据见本报告 advisory 表 |
| 最终 `npm audit --json` | 通过，0 vulnerabilities |
| 最终 `npm audit --omit=dev --json` | 通过，0 vulnerabilities |
| `python -m pip check`（原环境） | `No broken requirements found` |
| 临时后端环境安装更新后 requirements | 通过，Django 6.0.9 / DRF 3.18.3 |
| 临时固定环境 `pip check` | `No broken requirements found` |
| 临时固定环境 pip-audit | Django/DRF 0；Pillow advisory 保留并按上表延期 |
| 后端 `python manage.py test` | **984 passed，18 skipped，0 failed** |
| `npm run test:unit` | **156 passed，0 failed** |
| `npm run test:trade-units` | **1 file / 4 tests passed** |
| `npm run build` | **通过**；Vite 8.3.5，2018 modules transformed；保留既有 >500 kB chunk warning |
| `npm exec -- vitest run`（非仓库有效脚本） | 56 files failed/53 passed；主要是将 node:test 文件当 Vitest suite 收集，以及未设置 jsdom 导致 `document/localStorage is not defined`。不将该命令冒充全量 Vitest PASS；仓库定义的 Node 156 项和 jsdom 定向 4 项已通过。 |
| GitHub CI / 生产部署 | 未触发、未执行 |

## 遗留风险与后续

- **高优先级**：Pillow 11.3.0 的实际图片解析路径仍在当前 requirements 约束内，需在独立任务中评估 12.x/13.x，不得用本轮的 Django/DRF 修复代替。
- **中优先级**：建立 Python lock/受控解析记录；当前 requirements 范围可随时间解析到不同版本。
- **中优先级**：把 Vite/插件从 production dependency 分类到明确的 build stage，或在部署文档中确认 production image 不安装 build tool。
- **低优先级**：`lucide-vue-next` 已被 npm 标记 deprecated，需单独评估迁移到 `@lucide/vue`，本轮未修改图标包。
- **测试维护**：将需要 jsdom 的 Vitest suite 与 node:test 文件分开配置；本轮未为此非安全配置问题改测试架构。

ISS-002 状态建议继续保持 `NEEDS_VERIFICATION`，原因是 Pillow 大版本风险、生产镜像实际解析版本、CI/PostgreSQL/真实外部暴露路径仍未在本轮验证。该报告可作为下一次独立复审的本地证据，但不是生产安全签字。
