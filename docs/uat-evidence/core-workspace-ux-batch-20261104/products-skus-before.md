# Products/SKUs 修复前组件回归

基线 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`。从 `git show HEAD:frontend/src/views/{ProductPage,SKUPage}.vue` 创建同目录临时组件副本，两个新增 spec 仅替换组件导入路径；运行后 finally 清理副本与临时 spec，未回退工作文件。Vitest exit 1，4 failed / 1 passed。Python 控制台打印 Unicode 后另报 GBK 编码错误，完整 UTF-8 Vitest 日志此前已写入，不影响失败证据或 finally 清理。

```text

 RUN  v4.1.12 D:/Codex项目/森爵照明管理系统/.worktrees/core-workspace-ux-batch-20261104/frontend

 ❯ tests/product-workspace-batch-before.spec.js (2 tests | 2 failed) 146ms
   × stale product existence probe success cannot finish a newer load 118ms
   × stale product existence probe failure cannot finish a newer load 27ms
 ❯ tests/sku-workspace-batch-before.spec.js (3 tests | 2 failed) 411ms
   × stale supplier sources success cannot replace current SKU context 267ms
   × stale supplier sources failure cannot replace current SKU context 108ms

 Test Files  2 failed (2)
      Tests  4 failed | 1 passed (5)
   Start at  16:11:17
   Duration  18.98s (transform 4.45s, setup 1.23s, import 6.05s, tests 557ms, environment 19.98s)



⎯⎯⎯⎯⎯⎯⎯ Failed Tests 4 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  tests/product-workspace-batch-before.spec.js > stale product existence probe success cannot finish a newer load
 FAIL  tests/product-workspace-batch-before.spec.js > stale product existence probe failure cannot finish a newer load
AssertionError: expected false to be true // Object.is equality

- Expected
+ Received

- true
+ false

 ❯ tests/product-workspace-batch-before.spec.js:29:21
     27|   newest.resolve([{id:2,name:'新产品',code:'NEW',status:'active'}]);await…
     28|   expect(wrapper.vm.products[0].id).toBe(2)
     29|   expect(wrapper.vm.allProductsExist).toBe(true)
       |                     ^
     30|   expect(wrapper.vm.loading).toBe(false)
     31| })

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/4]⎯

 FAIL  tests/sku-workspace-batch-before.spec.js > stale supplier sources success cannot replace current SKU context
 FAIL  tests/sku-workspace-batch-before.spec.js > stale supplier sources failure cannot replace current SKU context
AssertionError: expected false to be true // Object.is equality

- Expected
+ Received

- true
+ false

 ❯ tests/sku-workspace-batch-before.spec.js:32:44
     30|   expect(wrapper.vm.supplierSourcesError).toBe('')
     31|   current.resolve([{id:22,supplier_name:'当前 SKU 来源'}]);await flushProm…
     32|   expect(wrapper.vm.supplierSources[0].id).toBe(22)
       |                                            ^
     33|   expect(wrapper.vm.supplierSourcesLoading).toBe(false)
     34| })

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[2/4]⎯


```
