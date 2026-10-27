# Qt 与 Web 展示资源

本目录集中保存两个展示入口的静态资源，避免 `gui_qml` 与 `web` 形成重复的顶层目录。

- `Main.qml`：Qt Quick 界面，负责参数采集、商业筛选、任务状态和事件展示。
- `index.html`：本机浏览器页面结构。
- `styles.css`：Web GUI 的色彩、布局、响应式和交互状态样式。
- `app.js`：Web 参数采集、任务提交、SSE 事件消费和产物下载。

Qt 和 Web 都只调用公共 ViewModel、TaskRequest 和本机任务 API，不实现平台登录、查询、字段映射或 Excel 规则。
