# R0-F5 内置浏览器截图归档

2026-10-15，用户要求修复截图归档缺口。截图对应应用提交 `92e8c46` / 文档基线 `0ec186b`，隔离环境 `http://127.0.0.1:5197`，使用原 `r0f5-ux.sqlite3`；仅展示合成 UAT 记录。

当前文档提供 `tab.screenshot()`，返回 JPEG `Uint8Array`。正常保存方法已实际成功并通过 JPEG 解码复核：

```js
const fs = await import('node:fs/promises')
const screenshot = await tab.screenshot({ fullPage: false })
await fs.writeFile(absoluteAuthorizedPath, screenshot)
```

视口使用文档提供的 `browser.capabilities.get('viewport').set({ width, height: 1000 })`；截图前读取当前页面状态，核对实际 `innerWidth/innerHeight`。完成后 reset 视口。没有改用外部浏览器、CDP 或截图代理，没有安全拒绝被绕过。此前无专用保存接口即认定安全禁止的判断已纠正。

| 页面状态 | 1440px | 1280px | 1024px |
|---|---|---|---|
| 联系人列表 | [截图](contacts-list-1440.jpg) | [截图](contacts-list-1280.jpg) | [截图](contacts-list-1024.jpg) |
| 新建联系人 | [截图](contacts-create-1440.jpg) | [截图](contacts-create-1280.jpg) | [截图](contacts-create-1024.jpg) |
| 跟进列表 | [截图](follow-ups-list-1440.jpg) | [截图](follow-ups-list-1280.jpg) | [截图](follow-ups-list-1024.jpg) |
| 新建跟进 | [截图](follow-ups-create-1440.jpg) | [截图](follow-ups-create-1280.jpg) | [截图](follow-ups-create-1024.jpg) |

[默认视口归档功能验证](contacts-archive-check.jpg)。[文件尺寸及 SHA-256 清单](manifest.json)。截图是原始 JPEG，不裁切、不拼接、不伪造。1024视口的跟进列表/表单实际 `innerWidth/innerHeight` 均核对为1024×1000；截图 API 返回图像为1009×985，按返回值原样归档，未人为补边或缩放。其余指定视口图像尺寸与设定相同。

这些文件解除截图不可交付的问题，供 ChatGPT 独立复审。它们不等于独立视觉 PASS，也不证明附件文件内容/权限完整验收；ISS-007 和其他历史未覆盖项继续保留。
