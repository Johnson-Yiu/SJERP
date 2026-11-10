# H1 原始 Chrome 失败

被测产品源码 43067137d0fba04b0be055e449e55a06dba6d208，Google Chrome 156.0.8078.80，真实隔离 Django 和 Chrome 原生缩放。以下保留原始断言输出。

# Test info

- Name: ui-product-operations-completion-02.spec.js >> product detail fits the available workspace and nested details restore focus
- Location: browser-tests\ui-product-operations-completion-02.spec.js:8:1

# Error details

```
Error: expect(received).toEqual(expected) // deep equality

- Expected  -  1
+ Received  + 65

- Array []
+ Array [
+   Object {
+     "height": 768,
+     "message": "expect(received).toBeGreaterThanOrEqual(expected)
+
+ Expected: >= 247
+ Received:    24",
+     "width": 1366,
+     "zoom": 1,
+   },
+   Object {
+     "height": 900,
+     "message": "expect(received).toBeGreaterThanOrEqual(expected)
+
+ Expected: >= 247
+ Received:    24",
+     "width": 1440,
+     "zoom": 1,
+   },
+   Object {
+     "height": 844,
+     "message": "expect(locator).toBeFocused() failed
+
+ Locator:  locator('.workspace-pane[aria-hidden=\"false\"] .product-context-drawer [role=\"dialog\"]').getByRole('button', { name: '关闭详情' })
+ Expected: focused
+ Received: inactive
+ Timeout:  5000ms
+
+ Call log:
+   - Expect \"toBeFocused\" locator('.workspace-pane[aria-hidden=\"false\"] .product-context-drawer [role=\"dialog\"]').getByRole('button', { name: '关闭详情' }) with timeout 5000ms
+   - waiting for locator('.workspace-pane[aria-hidden=\"false\"] .product-context-drawer [role=\"dialog\"]').getByRole('button', { name: '关闭详情' })
+     14 × locator resolved to <button aria-label=\"关闭详情\" data-v-9751b1ea=\"\" class=\"detail-close\">…</button>
+        - unexpected value \"inactive\"
+ ",
+     "width": 390,
+     "zoom": 1,
+   },
+   Object {
+     "height": 768,
+     "message": "expect(received).toBeGreaterThanOrEqual(expected)
+
+ Expected: >= 247
+ Received:    24",
+     "width": 1366,
+     "zoom": 1.25,
+   },
+   Object {
+     "height": 900,
+     "message": "expect(received).toBeGreaterThanOrEqual(expected)
+
+ Expected: >= 247
+ Received:    24",
+     "width": 1440,
+     "zoom": 1.25,
+   },
+   Object {
+     "height": 844,
+     "message": "expect(received).toBeLessThanOrEqual(expected)
+
+ Expected: <= 313
+ Received:    316.37716722488403",
+     "width": 390,
+     "zoom": 1.25,
+   },
+ ]
```
