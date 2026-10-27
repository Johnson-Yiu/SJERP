# final-cross-module-ux 六项失败修复验收

日期：2026-10-28
基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
分支：`codex/repair-final-cross-module-ux`
范围：`frontend/browser-tests/final-cross-module-ux.spec.js`

## 结论

六项失败的根因是测试 mock 过时，不是报价/订单列表产品代码缺陷。当前页面展示保存后的正式主体事实：报价使用 `buyer_company_name`，非草稿订单使用 `customer_name_snapshot`。原 mock 只提供当前客户主档字段 `customer_name`，因此页面按既有安全回退逻辑显示“历史主体未记录”，六项视口均无法找到测试客户。

本轮只补齐 endpoint-specific mock 字段：报价增加 `buyer_company_name`，订单增加 `customer_name_snapshot`。没有删除断言、修改客户名称、增加等待时间、改变列表渲染逻辑或降低布局验收标准。

## 隔离复现证据

固定基线上的原始测试结果：`6 failed`（报价/订单 × 1440、1280、1024）。修复环境依赖链接后，临时诊断记录了真实请求、响应、控制台和 DOM：

| 页面 | 请求与响应 | 实际表格客户单元格 |
|---|---|---|
| `/quotes` | `GET /api/session/current-operator/` 200 对象；`GET /api/quotes/?search=&status=&customer=&ordering=-updated_at&page=1` 200 数组；`GET /api/customers/?page=1` 200 数组 | `历史主体未记录` |
| `/orders` | `GET /api/session/current-operator/` 200 对象；`GET /api/orders/?search=&page=1` 200 数组 | `历史主体未记录` |

`listAll()` 的当前契约同时接受数组和 `{results, next}` 分页对象；本测试返回数组是合法的，不是失败原因。页面 console 在依赖链路正常后没有业务错误；根因由 DOM 和响应体共同确认。

当前代码证据：

- `DocumentPage.vue` 的 `quotePartyName()` 读取 `row.buyer_company_name`。
- `DocumentPage.vue` 的 `orderPartyName()` 对确认订单读取 `row.customer_name_snapshot`。
- 后端 `QuoteSerializer`/`OrderSerializer` 使用模型中的保存快照字段，当前主档 `customer_name` 只用于关系筛选和参考展示。

## 代码修改

仅修改 `frontend/browser-tests/final-cross-module-ux.spec.js` 的 fixture：

```js
...(type === 'quotes'
  ? { buyer_company_name: customer.name }
  : { customer_name_snapshot: customer.name })
```

原有客户列可见性、报价客户列最小宽度 `>= 200px`、订单两个筛选控件高度 `>= 42px`、圆角 `8px`、以及页面级无横向溢出断言均保留。

## 测试日志

以下均为本地隔离 worktree 执行，未运行 GitHub Actions：

| 命令 | 结果 |
|---|---|
| `node node_modules/@playwright/test/cli.js test browser-tests/final-cross-module-ux.spec.js --workers=1 --reporter=line`（修复后） | `6 passed`，38.7s |
| `node --test` | `156 passed, 0 failed` |
| `node --test src/views/DocumentPage.test.js src/api.test.js` | `24 passed, 0 failed` |
| `node D:\\Codex项目\\森爵照明管理系统\\frontend\\node_modules\\vitest\\vitest.mjs run tests/crm-list.vitest.js --environment jsdom` | `1 file / 5 tests passed` |
| `python manage.py check` | `System check identified no issues` |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `node D:\\Codex项目\\森爵照明管理系统\\frontend\\node_modules\\vite\\bin\\vite.js build` | `2018 modules transformed; build succeeded`；保留既存大 chunk warning |

隔离 worktree 的 npm optional native binding 链接不完整，直接调用本地 Vite 8.3/Vitest 时出现环境错误；验证使用本机已完成的同项目 Vite 8.2/Vitest 4.1.11 运行时，不改 package.json、lockfile 或源码。该环境差异已如实记录，不能解释为业务测试通过或生产构建环境等价。

## Chrome 视觉证据

使用 Chrome Use 连接的 Chrome extension 浏览器，访问独立本地 Vite（5196）与仅监听 `127.0.0.1:48123` 的临时 mock API；未连接生产服务。Chrome 页面实际显示测试客户，桌面截图与窄屏截图保存在本目录：

- [报价 1440px](quotes-1440.png)
- [订单 1440px](orders-1440.png)
- [报价 390px](quotes-390.png)
- [订单 390px](orders-390.png)

截图采集指标：

| 页面/宽度 | viewport | document/body scrollWidth | 说明 |
|---|---:|---:|---|
| 报价 / 1440 | 1440 | 1440 / 1440 | 通过 |
| 订单 / 1440 | 1440 | 1440 / 1440 | 通过 |
| 报价 / 390 | 390 | 390 / 390 | 通过 |
| 订单 / 390 | 390 | 393 / 393 | 窄屏边界：表格约 966px，处于 `.table-wrap { overflow: auto }` 内；截图无页面级滚动条，但根宽度多 3px |

390px 订单边界不是本次六项失败的原因，也没有改变原自动化断言来掩盖它。建议后续单独补修/复审移动端根宽度与数据表滚动容器；本轮不修改产品布局，以免把 mock 契约修复混入无关 UI 变化。

## 待后续复审

- 独立审查确认测试 mock 与现行正式主体快照契约一致。
- 独立复审 390px 订单根宽度 3px 边界，并决定是否需要独立移动端 UX 修补。
- 本地结果不代表生产员工账号、生产 API 或生产部署验收。
- 本轮未部署、未合并 `master`、未关闭 Issue、未创建 GitHub Actions 运行。
