# ISS-058 前端性能基线报告

## 1. 任务与结论

- 项目：SUNJACK-ERP
- 任务：ISS-058-FRONTEND-PERFORMANCE-BASELINE
- 测量分支：`codex/measure-iss058-frontend-performance`
- 测量基线：`46353a5436637832f5adadb7bdef6b45cdeada23`
- 测量日期：2026-10-27（Asia/Shanghai）

结论：本次只提交测量报告，不进行前端重构。

构建结果证明当前入口包存在明显的包体预算风险：主 JS 产物为 1,126.22 kB，Vite 给出“存在超过 500 kB 的 chunk”警告；路由中只有报表中心、历史订单分析、SKU 交易单位使用动态导入，其余主要业务页面会进入主包。但在本次本地生产预览和 Chrome 观测中，经营概览、报价管理、库存页面均能完成渲染并显示业务数据，尚不足以证明已经形成稳定、可复现的用户可感知前端性能问题。

因此本次不做无依据的按需加载或全站重构。后续若真实网络、低端设备或受限带宽测量确认首屏确有明显延迟，再针对主包中的非首屏页面做最小范围路由分包，并重新验证权限和关键交互。

## 2. 测试环境与边界

- 操作系统：Windows 本地开发环境
- Node.js：`v24.16.0`
- npm：`11.13.0`
- Vite：`8.2.0`
- Chrome：`155.0.8059.86`
- 前端生产预览：`http://127.0.0.1:4187/`
- API：前端使用相对路径 `/api`，通过本地 Vite 配置代理到 `127.0.0.1:8100`
- 测量范围：本地 loopback、生产构建产物、真实本地 Chrome 页面观测

本报告中的所有传输时间都是本地 loopback 结果，不包含真实公网网络、TLS、CDN、跨地域链路、移动设备 CPU 或受限网络条件。Chrome 连接器提供的只读页面评估作用域未暴露 `performance` 时间线，因此没有把浏览器桥接调用耗时冒充为 FCP、LCP、TTI 或真实用户网络指标。

## 3. 生产构建原始结果

执行命令：

```text
cd frontend
npm run build
```

构建输出摘要：

```text
vite v8.2.0 building client environment for production...
✓ 2013 modules transformed.
✓ built in 17.10s
BUILD_EXIT_CODE=0
BUILD_ELAPSED_MS=30925
```

`17.10s` 是 Vite 内部构建时间；`30.925s` 是 PowerShell 从启动 npm 到进程结束的本地墙钟时间，包含 Node/npm 启动及输出开销。

构建警告：

```text
(!) Some chunks are larger than 500 kB after minification.
Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking
```

### 3.1 产物体积

以下 gzip 数值由构建产物使用 gzip 压缩计算得到；不是对真实公网响应的测量。

| 产物 | 原始字节 | 原始 KiB | gzip 字节 | gzip KiB | 类型 |
| --- | ---: | ---: | ---: | ---: | --- |
| `assets/index-BYhubQT2.js` | 1,126,218 | 1,099.82 | 393,477 | 384.25 | 主 JS |
| `assets/index-Bpml0PSE.css` | 386,217 | 377.17 | 63,432 | 61.95 | 主 CSS |
| `assets/_plugin-vue_export-helper-BExYQ_OI.js` | 128,333 | 125.33 | 49,219 | 48.07 | modulepreload helper |
| `assets/ReportsPage-DMDp3LGS.js` | 51,153 | 49.95 | 16,434 | 16.05 | 报表中心路由 JS |
| `assets/ReportsPage-BTHBXwkU.css` | 18,047 | 17.62 | 3,422 | 3.34 | 报表中心路由 CSS |
| `assets/HistoryOrdersPage-DgJFNhf3.js` | 12,769 | 12.47 | 4,478 | 4.37 | 历史订单路由 JS |
| `assets/HistoryOrdersPage-5Xkjdeuh.css` | 6,556 | 6.40 | 1,533 | 1.50 | 历史订单路由 CSS |
| `assets/TradeUnitsPage-C3jY_ECs.js` | 10,633 | 10.38 | 4,324 | 4.22 | SKU 交易单位路由 JS |
| `assets/TradeUnitsPage-BagMfA07.css` | 2,894 | 2.83 | 891 | 0.87 | SKU 交易单位路由 CSS |
| `index.html` | 566 | 0.55 | 369 | 0.36 | HTML |
| **全部 dist 产物** | **1,743,386** | **1,702.53** | **537,579** | **524.98** | — |

按 `index.html` 的 modulepreload 和 stylesheet 引用计算，首屏入口静态资源包括 HTML、主 JS、主 CSS 和 Vue helper，构建 gzip 合计约 **506,497 bytes / 494.63 KiB**；这只是静态构建预算，不等于 Chrome 的真实首屏完成时间，也不包含 API 响应。

### 3.2 路由分包现状

基线 `frontend/src/router.js` 中，只有以下路由使用动态导入：

- `/reports` → `ReportsPage`
- `/historical-orders` → `HistoryOrdersPage`
- `/sku-trade-units` → `TradeUnitsPage`

经营概览、报价、订单、客户、采购、库存、财务、产品资料等主要页面通过静态 import 或复用已导入页面进入主包。这解释了主 JS 体积大、而已生成路由分包相对较小的构建结果。

## 4. 本地生产预览与 Chrome 观测

### 4.1 本地资源传输

使用本地 Vite preview 通过 `HttpClient` 顺序读取每个产物 3 次，记录中位数。Vite preview 响应未返回 `Content-Encoding`，因此下表是本地未压缩 HTTP 响应的读取时间，不是 gzip 网络时间。

| 资源 | HTTP 状态 | 响应字节 | 3 次读取中位数 |
| --- | ---: | ---: | ---: |
| `/index.html` | 200 | 566 | 5.06 ms |
| `/assets/index-BYhubQT2.js` | 200 | 1,126,218 | 14.48 ms |
| `/assets/index-Bpml0PSE.css` | 200 | 386,217 | 4.06 ms |
| `/assets/_plugin-vue_export-helper-BExYQ_OI.js` | 200 | 128,333 | 5.42 ms |
| `/assets/ReportsPage-DMDp3LGS.js` | 200 | 51,153 | 7.78 ms |
| `/assets/ReportsPage-BTHBXwkU.css` | 200 | 18,047 | 10.72 ms |
| `/assets/HistoryOrdersPage-DgJFNhf3.js` | 200 | 12,769 | 3.21 ms |
| `/assets/TradeUnitsPage-C3jY_ECs.js` | 200 | 10,633 | 4.88 ms |

主 JS 第一次读取为 144.55 ms，后两次为 14.18 ms、14.48 ms；这说明本地冷启动和本地热读取差异明显，但不能外推到真实网络。

### 4.2 代表性页面

通过真实 Chrome 打开 `http://127.0.0.1:4187/` 并观察可见页面状态：

| 页面 | Chrome 观测结果 | 记录边界 |
| --- | --- | --- |
| `/` 经营概览 | 在显式等待 5,000 ms 后，页面从“刷新中…”变为“刷新数据”，并显示销售与客户、销售趋势、品类表现、重点客户、待跟进事项、账面收支等数据 | 只能证明在该本地环境的 5 秒观察点已就绪；未把 5 秒写成 FCP/LCP/TTI |
| `/quotes` 报价管理 | 页面显示报价项目 45、报价版本 50、进行中 21、已接受 27，并渲染报价表及“查看/创建修订版/导出”等操作 | 证明代表性列表页在本地 Chrome 可渲染并可见关键交互；未把浏览器桥接调用耗时当作页面指标 |
| `/inventory` 库存 | 页面显示 SKU 数量 6、实际库存、已预留、可用库存、在途采购，并渲染 6 条 SKU 数据 | 直接导航命令墙钟约 1,126 ms；该数值不包含可归因的完整 API/渲染就绪时间，因此只作导航观测参考 |
| `/reports` 报表中心 | 第一次 Chrome 观察时页面仍显示“正在加载报表选项…”；后续重新获取可访问性树时遇到 Chrome 连接器超时 | 这是需要后续单独复核的本地观测；当前证据不足以判断是前端包体、API、后端数据还是浏览器桥接造成 |

### 4.3 页面切换观测

尝试从经营概览通过 Chrome 页面内“报价管理”链接测量 SPA 点击切换时，浏览器连接器在 URL 等待/鼠标派发阶段超时，未获得可靠的页面切换数值。随后通过真实 Chrome 直接打开 `/quotes` 和 `/inventory`，确认两页可见内容正常，但这属于直接 URL 导航，不等价于 SPA 点击切换。

因此本报告不填入未经可靠采集的“页面切换耗时”。

## 5. 性能预算判断

项目当前没有在代码或文档中声明正式前端性能预算。为便于本次评审，使用以下临时工程观察线，不能视为产品验收标准：

- 主 JS gzip 目标观察线：≤ 300 KiB
- 首屏静态入口（HTML + 主 JS + 主 CSS + modulepreload helper）目标观察线：≤ 500 KiB
- 生产构建不出现 >500 kB minified chunk 警告

对照结果：

- 主 JS gzip：384.25 KiB，超过临时观察线 84.25 KiB。
- 首屏静态入口：494.63 KiB，接近但未超过临时观察线；这是构建 gzip 估算，不是实际网络传输。
- 主 JS 原始 minified 体积：1,099.82 KiB，触发 Vite >500 kB chunk 警告。

判断：包体预算风险为“需要后续优化评估”，但“用户可感知性能问题”在本次本地环境中仍为“证据不足”。本地 loopback 读取很快，经营概览、报价管理、库存均能完成数据渲染；报表中心的加载停留尚未完成归因，也没有可靠的重复 Chrome 时间线数据。

## 6. 是否需要优化及依据

本次不优化，依据如下：

1. 已确认主包过大并存在 eager import，但这属于结构性风险，不等于已经造成用户可感知卡顿。
2. 本地 Chrome 已能完成多个代表性业务页面的首屏数据渲染和关键操作展示。
3. 当前测量未覆盖真实网络、低端 CPU、移动端或受限带宽，不能把本地结果外推成线上事实。
4. `/reports` 的一次加载停留没有稳定复现和归因，不能据此贸然改动路由加载、API 请求或依赖。
5. 按任务规则，证据不足时只提交测量报告，不进行无依据重构。

建议后续若继续推进：先用 Chrome DevTools 在固定网络/CPU profile 下重复测量首屏和 SPA 点击切换，并把 `/reports` 的 API 请求耗时与前端渲染耗时拆开；若确认主包是主要瓶颈，再优先把非首屏页面改为最小范围动态导入，并执行权限、报价、库存和关键交互回归。

## 7. 本地验证与交付状态

- `npm run build`：通过，退出码 0。
- 生产预览：`http://127.0.0.1:4187/` 返回 HTTP 200。
- Chrome：已打开并观察经营概览、报价管理、库存、报表中心页面。
- 源码：未修改；本分支仅新增本报告。
- GitHub CI：未触发本地测试之外的 CI；提交将使用 `[skip ci]`。
- `master`：未合并。
- Issue：未关闭。
