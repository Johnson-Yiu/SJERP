# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cancel-refund-closeout-02.spec.js >> A closeout real Chrome cash attribution, cancellation retry and partial termination
- Location: browser-tests\cancel-refund-closeout-02.spec.js:9:1

# Error details

```
Error: expect(locator).toBeHidden() failed

Locator: getByRole('dialog', { name: '调整订单数量' })
Expected: hidden
Error: strict mode violation: getByRole('dialog', { name: '调整订单数量' }) resolved to 2 elements:
    1) <section role="dialog" aria-modal="true" class="app-dialog" aria-labelledby="app-dialog-title-1" aria-describedby="app-dialog-message-1">…</section> aka getByRole('dialog', { name: '确认调整订单数量' })
    2) <form role="dialog" aria-modal="true" data-v-39de5d98="" aria-labelledby="quantity-adjustment-title" class="trade-shipment-dialog quantity-adjustment-dialog">…</form> aka getByRole('dialog', { name: '调整订单数量', exact: true })

Call log:
  - Expect "toBeHidden" getByRole('dialog', { name: '调整订单数量' }) with timeout 30000ms
  - waiting for getByRole('dialog', { name: '调整订单数量' })

```

# Test source

```ts
  38  |   async function openOrder(f) {
  39  |     await page.goto(new URL('/orders?search=' + f.number, baseURL).href)
  40  |     await page.getByRole('row').filter({ hasText: f.number }).click()
  41  |     await expect(wb).toBeVisible()
  42  |   }
  43  |   async function collect(name, target) {
  44  |     for (const zoom of [1, 1.25]) {
  45  |       await zoomControl.selectOption(String(zoom))
  46  |       for (const [width,height] of [[1366,768],[1920,1080],[390,844]]) {
  47  |         await page.setViewportSize({ width,height })
  48  |         await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
  49  |         if (width===390) await expect.poll(() => page.locator('.sidebar').evaluate(el=>el.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
  50  |         await expect(target).toBeVisible()
  51  |         await target.scrollIntoViewIfNeeded()
  52  |         const metrics = await target.evaluate(el => { const r=el.getBoundingClientRect();return { x:r.x,y:r.y,width:r.width,height:r.height,innerWidth,innerHeight,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight } })
  53  |         expect(metrics.x).toBeGreaterThanOrEqual(-1)
  54  |         expect(metrics.x+metrics.width).toBeLessThanOrEqual(metrics.innerWidth+1)
  55  |         const file = `${name}-${width}-${zoom*100}.png`
  56  |         await page.screenshot({ path:path.join(output,file) })
  57  |         captures.push({ name,width,height,zoom,metrics,file })
  58  |         await save()
  59  |       }
  60  |     }
  61  |     await zoomControl.selectOption('1')
  62  |     await page.setViewportSize({ width:1366,height:768 })
  63  |   }
  64  |   async function refund(f, amount, name) {
  65  |     await page.goto(new URL('/transactions?search=' + f.receiptNo, baseURL).href)
  66  |     await page.getByRole('row').filter({ hasText:f.receiptNo }).getByRole('button',{name:'详情',exact:true}).click()
  67  |     await page.getByRole('button',{name:'从本笔登记退款'}).click()
  68  |     const form=page.getByRole('dialog',{name:'登记退款'})
  69  |     await expect(form.getByLabel('退款对应订单')).toHaveValue(String(f.order))
  70  |     await expect(form.getByLabel('退款对应订单').getByRole('option',{name:'未分配预收款'})).toHaveCount(0)
  71  |     await form.getByLabel(/实际退款金额/).fill(String(amount))
  72  |     await form.getByLabel('退款依据').fill('合成实际原币退款凭证 '+name)
  73  |     await form.getByLabel('实际退款凭证').setInputFiles({name:name+'.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nSynthetic '+name+'\n%%EOF')})
  74  |     await form.getByRole('button',{name:'上传凭证',exact:true}).click()
  75  |     await expect(form.getByText(/凭证已上传/)).toBeVisible()
  76  |     if(name==='normal-100') await collect('refund-before-submit',form)
  77  |     const saved=page.waitForResponse(r=>r.url().endsWith('/refund-cash/') && r.request().method()==='POST')
  78  |     await form.getByRole('button',{name:'确认登记',exact:true}).click()
  79  |     const response=await saved
  80  |     expect(response.status(),await response.text()).toBe(201)
  81  |     await expect(form).toBeHidden()
  82  |   }
  83  |   try {
  84  |     await refund(fixture.paid,100,'normal-100')
  85  |     await openOrder(fixture.paid)
  86  |     await expect(wb.locator('.payment-card')).toContainText(/100\.00/)
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
  117 |     const qty=page.getByRole('dialog',{name:'调整订单数量'})
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
  137 |     await page.getByRole('button',{name:'确认提交',exact:true}).last().click()
> 138 |     await expect(qty).toBeHidden()
      |                       ^ Error: expect(locator).toBeHidden() failed
  139 |     await expect(wb).toContainText('已完成')
  140 |     await collect('terminate-after',wb)
  141 |     const details=await (await page.request.get('/api/orders/'+fixture.partial.order+'/workbench/')).json()
  142 |     await writeFile(path.join(output,'final-workbench.json'),JSON.stringify(details,null,2))
  143 |     for (const key of ['void','correction']) {
  144 |       const f=fixture[key]
  145 |       await openOrder(f)
  146 |       await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  147 |       await page.getByLabel('取消原因').fill('合成取消后验证允许的更正不复活应收')
  148 |       const cancellation=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  149 |       await page.getByRole('button',{name:'确认取消',exact:true}).click()
  150 |       expect((await cancellation).status()).toBe(200)
  151 |       await expect(page.getByLabel('取消原因')).toBeHidden()
  152 |       await page.goto(new URL('/transactions?search='+f.receiptNo,baseURL).href)
  153 |       const row=page.getByRole('row').filter({hasText:f.receiptNo})
  154 |       if (key==='void') {
  155 |         await row.getByRole('button',{name:'作废',exact:true}).click()
  156 |         const form=page.getByRole('dialog',{name:'作废财务流水'})
  157 |         await form.getByLabel('作废原因').fill('合成取消订单原收款更正作废')
  158 |         await collect('cancelled-void-before',form)
  159 |         const result=page.waitForResponse(r=>r.url().endsWith('/void/') && r.request().method()==='POST')
  160 |         await form.getByRole('button',{name:'确认作废',exact:true}).click()
  161 |         expect((await result).status()).toBe(200)
  162 |         await expect(form).toBeHidden()
  163 |       } else {
  164 |         await row.getByRole('button',{name:'详情',exact:true}).click()
  165 |         await page.getByRole('button',{name:'更正抹零',exact:true}).click()
  166 |         const form=page.getByRole('dialog',{name:'更正授权抹零'})
  167 |         await form.getByLabel(/更正金额/).fill('1')
  168 |         await form.getByLabel('更正原因').fill('合成取消订单后撤销错误非现金抵减')
  169 |         await collect('cancelled-correction-before',form)
  170 |         const result=page.waitForResponse(r=>r.url().includes('writeoff') && r.request().method()==='POST')
  171 |         await form.getByRole('button',{name:'追加更正',exact:true}).click()
  172 |         expect((await result).status()).toBe(201)
  173 |         await expect(form).toBeHidden()
  174 |       }
  175 |       await openOrder(f)
  176 |       await expect(wb).toContainText('已取消')
  177 |       await expect(wb.locator('.payment-card')).not.toContainText('当前待收')
  178 |       await collect('cancelled-'+key+'-after',wb)
  179 |       const result=await (await page.request.get('/api/orders/'+f.order+'/workbench/')).json()
  180 |       await writeFile(path.join(output,'cancelled-'+key+'-workbench.json'),JSON.stringify(result,null,2))
  181 |     }
  182 |     await save()
  183 |   } finally { await save(); await context.close() }
  184 | })
  185 | 
```