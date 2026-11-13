# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cancel-refund-closeout-02.spec.js >> A closeout real Chrome cash attribution, cancellation retry and partial termination
- Location: browser-tests\cancel-refund-closeout-02.spec.js:9:1

# Error details

```
Error: expect(locator).not.toContainText(expected) failed

Locator: getByRole('dialog', { name: '订单工作台' }).locator('.payment-card')
Expected substring: not "当前待收"
Received string: " 回款状态：已取消净实收含已分配的预收现金，扣除退款和银行退回。0%应收计划USD 0.00净实收USD 0.00当前待收已取消"
Timeout: 30000ms

Call log:
  - Expect "not toContainText" getByRole('dialog', { name: '订单工作台' }).locator('.payment-card') with timeout 30000ms
  - waiting for getByRole('dialog', { name: '订单工作台' }).locator('.payment-card')
    62 × locator resolved to <article data-v-39de5d98="" class="workbench-card payment-card">…</article>
       - unexpected value " 回款状态：已取消净实收含已分配的预收现金，扣除退款和银行退回。0%应收计划USD 0.00净实收USD 0.00当前待收已取消"

```

```yaml
- article:
  - heading "回款状态：已取消" [level=3]
  - paragraph: 净实收含已分配的预收现金，扣除退款和银行退回。
  - text: 0%
  - term: 应收计划
  - definition: USD 0.00
  - term: 净实收
  - definition: USD 0.00
  - term: 当前待收
  - definition: 已取消
```

# Test source

```ts
  87  |     await collect('normal-refund-after',wb)
  88  |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  89  |     await page.getByLabel('取消原因').fill('合成取消后按原收款分次退款')
  90  |     const cancelForm=page.locator('form').filter({has:page.getByRole('heading',{name:'取消订单',exact:true})})
  91  |     await collect('cancel-before-submit',cancelForm)
  92  |     const cancelled=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  93  |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
  94  |     const cancellation=await cancelled
  95  |     expect(cancellation.status(),await cancellation.text()).toBe(200)
  96  |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*900\.00/, {timeout:20000})
  97  |     await collect('cancel-after',wb)
  98  |     await refund(fixture.paid,400,'cancel-400')
  99  |     await openOrder(fixture.paid)
  100 |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*500\.00/)
  101 |     await refund(fixture.paid,500,'cancel-500')
  102 |     await openOrder(fixture.paid)
  103 |     await expect(wb.locator('.payment-card')).not.toContainText('待退款')
  104 |     await collect('cancel-refunds-complete',wb)
  105 |     await openOrder(fixture.partial)
  106 |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  107 |     await page.getByLabel('取消原因').fill('部分已发订单应当保留背景与原因')
  108 |     const refused=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  109 |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
  110 |     expect((await refused).status()).toBe(400)
  111 |     await expect(cancelForm.getByRole('alert')).toBeVisible()
  112 |     await expect(page.getByLabel('取消原因')).toHaveValue('部分已发订单应当保留背景与原因')
  113 |     await collect('cancel-rejection-retained',cancelForm)
  114 |     await cancelForm.getByRole('button',{name:'返回',exact:true}).click()
  115 |     await expect(wb).toBeVisible()
  116 |     await wb.getByRole('button',{name:'调整数量',exact:true}).click()
  117 |     const qty=page.getByRole('dialog',{name:'调整订单数量',exact:true})
  118 |     await qty.getByRole('checkbox').check()
  119 |     await qty.getByLabel('新的基础数量 A-CLOSE-SKU',{exact:true}).fill('40')
  120 |     await qty.getByLabel('新的基础数量 A-CLOSE-ZERO',{exact:true}).fill('0')
  121 |     await qty.getByLabel('变更原因').fill('合成部分履约终止，保留已发40件')
  122 |     await qty.getByRole('button',{name:'预览影响'}).click()
  123 |     await expect(qty).toContainText('请先在财务流水')
  124 |     await collect('terminate-paid-refund-guidance',qty)
  125 |     await qty.getByRole('button',{name:'取消',exact:true}).click()
  126 |     await refund(fixture.partial,600,'partial-before-terminate-600')
  127 |     await openOrder(fixture.partial)
  128 |     await wb.getByRole('button',{name:'调整数量',exact:true}).click()
  129 |     await qty.getByRole('checkbox').check()
  130 |     await qty.getByLabel('新的基础数量 A-CLOSE-SKU',{exact:true}).fill('40')
  131 |     await qty.getByLabel('新的基础数量 A-CLOSE-ZERO',{exact:true}).fill('0')
  132 |     await qty.getByLabel('变更原因').fill('实际退回超出履约金额后终止余项')
  133 |     await qty.getByRole('button',{name:'预览影响'}).click()
  134 |     await expect(qty.getByRole('button',{name:'确认调整'})).toBeEnabled()
  135 |     await collect('terminate-before-submit',qty)
  136 |     await qty.getByRole('button',{name:'确认调整'}).click()
  137 |     const applied=page.waitForResponse(r=>r.url().endsWith('/quantity-adjustments/') && r.request().method()==='POST')
  138 |     await page.getByRole('dialog',{name:'确认调整订单数量',exact:true}).getByRole('button',{name:'确认提交',exact:true}).click()
  139 |     const adjusted=await applied
  140 |     expect(adjusted.status(),await adjusted.text()).toBe(201)
  141 |     await expect(qty).toBeHidden()
  142 |     await expect(wb).toContainText('已完成')
  143 |     await collect('terminate-after',wb)
  144 |     const details=await (await page.request.get('/api/orders/'+fixture.partial.order+'/workbench/')).json()
  145 |     expect(details.order.status).toBe('completed')
  146 |     expect(Number(details.order.total_amount)).toBe(400)
  147 |     expect(details.items.map(row=>Number(row.quantity)).sort((a,b)=>a-b)).toEqual([0,40])
  148 |     expect(Number(details.fulfillment_summary.shipped_quantity)).toBe(40)
  149 |     expect(Number(details.fulfillment_summary.remaining_quantity)).toBe(0)
  150 |     expect(Number(details.payment_summary.paid_amount)).toBe(400)
  151 |     expect(Number(details.payment_summary.balance_amount)).toBe(0)
  152 |     await writeFile(path.join(output,'final-workbench.json'),JSON.stringify(details,null,2))
  153 |     for (const key of ['void','correction']) {
  154 |       const f=fixture[key]
  155 |       await openOrder(f)
  156 |       await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  157 |       await page.getByLabel('取消原因').fill('合成取消后验证允许的更正不复活应收')
  158 |       const cancellation=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  159 |       await page.getByRole('button',{name:'确认取消',exact:true}).click()
  160 |       expect((await cancellation).status()).toBe(200)
  161 |       await expect(page.getByLabel('取消原因')).toBeHidden()
  162 |       await page.goto(new URL('/transactions?search='+f.receiptNo,baseURL).href)
  163 |       const row=page.getByRole('row').filter({hasText:f.receiptNo})
  164 |       if (key==='void') {
  165 |         await row.getByRole('button',{name:'作废',exact:true}).click()
  166 |         const form=page.getByRole('dialog',{name:'作废财务流水'})
  167 |         await form.getByLabel('作废原因').fill('合成取消订单原收款更正作废')
  168 |         await collect('cancelled-void-before',form)
  169 |         const result=page.waitForResponse(r=>r.url().endsWith('/void/') && r.request().method()==='POST')
  170 |         await form.getByRole('button',{name:'确认作废',exact:true}).click()
  171 |         expect((await result).status()).toBe(200)
  172 |         await expect(form).toBeHidden()
  173 |       } else {
  174 |         await row.getByRole('button',{name:'详情',exact:true}).click()
  175 |         await page.getByRole('button',{name:'更正抹零',exact:true}).click()
  176 |         const form=page.getByRole('dialog',{name:'更正授权抹零'})
  177 |         await form.getByLabel(/更正金额/).fill('1')
  178 |         await form.getByLabel('更正原因').fill('合成取消订单后撤销错误非现金抵减')
  179 |         await collect('cancelled-correction-before',form)
  180 |         const result=page.waitForResponse(r=>r.url().includes('writeoff') && r.request().method()==='POST')
  181 |         await form.getByRole('button',{name:'追加更正',exact:true}).click()
  182 |         expect((await result).status()).toBe(201)
  183 |         await expect(form).toBeHidden()
  184 |       }
  185 |       await openOrder(f)
  186 |       await expect(wb).toContainText('已取消')
> 187 |       await expect(wb.locator('.payment-card')).not.toContainText('当前待收')
      |                                                     ^ Error: expect(locator).not.toContainText(expected) failed
  188 |       await collect('cancelled-'+key+'-after',wb)
  189 |       const result=await (await page.request.get('/api/orders/'+f.order+'/workbench/')).json()
  190 |       expect(result.order.status).toBe('cancelled')
  191 |       expect(Number(result.order.total_amount)).toBe(0)
  192 |       expect(Number(result.payment_summary.balance_amount)).toBe(0)
  193 |       expect(Number(result.payment_summary.paid_amount)).toBe(key==='void'?0:999)
  194 |       await writeFile(path.join(output,'cancelled-'+key+'-workbench.json'),JSON.stringify(result,null,2))
  195 |     }
  196 |     await save()
  197 |   } finally { await save(); await context.close() }
  198 | })
  199 | 
```