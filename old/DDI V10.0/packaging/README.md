# DDI V10.0 打包配置

## 当前打包脚本

- `DDI_V10.0.spec`
- `DDI_V10.0_GUI.spec`
- `build_release.ps1`

## 标准打包命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1
```

## 分发目录约定

- `config\account_runtime.json` 位于分发目录根部，作为商业启停配置。
- `config\gui_presets.json` 位于分发目录根部，保存 GUI 快捷方案。
- `COLLEAGUE_GUIDE.md` 位于分发目录根部。
- `config\license.json` 不随包分发；同事电脑必须使用维护者签发的授权文件。
- `runtime\` 保存运行时生成的 Cookie、Excel 和日志。
- 交付时发送整个 `packaging\release\DDI_V10.0` 目录，其中包含终端版 `DDI_V10.0.exe` 与 GUI 版 `DDI_V10.0_GUI.exe`，而不是只发送任一可执行文件。
- `docs` 和维护者个人参考材料不属于分发内容。

## GUI 构建说明

- 图形界面使用固定版本 `PySide6==6.11.1` 和 QML / Qt Quick；不再依赖 CustomTkinter、Tk Canvas 或系统壁纸亚克力。
- `DDI_V10.0_GUI.spec` 会收集 PySide6 Qt Quick 运行资源和项目 `gui_qml` 资源目录，确保 `Main.qml` 能在 onedir 发布包中加载。
- `build_release.ps1` 安装 GUI 依赖时优先使用清华 PyPI 镜像，并将 GUI 与终端合并到同一个 `DDI_V10.0` onedir 目录。
