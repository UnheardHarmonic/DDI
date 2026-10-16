# Qt 展示资源

本目录保存 Qt Quick 桌面界面的展示资源。

- `Main.qml`：Qt Quick 界面，负责参数采集、商业筛选、任务状态和事件展示。

展示层只调用公共 ViewModel、TaskRequest 和任务运行时接口，不实现平台登录、查询、字段映射或 Excel 规则。
