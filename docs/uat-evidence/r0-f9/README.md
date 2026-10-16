# R0-F9证据使用说明

先打开[index.html](index.html)，默认81张最终代码路由基线；可切换最终代码全部状态和全部过程图。原图均为浏览器返回的JPEG字节，未编辑、拉伸或重编码。相邻txt为当时DOM观察。

完整数据见manifest.json。请求尺寸与实际像素必须分别读取，差异由ISS-100保留；不能根据文件名判断精确像素。capture-records保留原始记录，manifest对闭包保留的旧sourceHead标签有透明metadataCorrection和recordedSourceHead。所有独立视觉待审。

最终代码0f0747a；交付文档提交应保持source-baseline.json的frontend/backend树不变。baseline-page为统一页面，baseline-new/detail/edit/payment-form为最终状态；较早记录用于过程追溯，不能混作最终基线。

真实UI使用专用SQLite r0f9-ux.sqlite3、API8118/Vite5205；无真实账号。seed只允许空专用库，verify只读断言合成写入。测试/HTTP/代理日志保留；PostgreSQL完整测试由最终HEAD CI执行。

重新生成元数据：从仓库运行`python docs/uat-evidence/r0-f9/generate_evidence.py`，只读取图像，不改写原图。最终报告在../../R0-F9-全站UIUX最终审查.md。
