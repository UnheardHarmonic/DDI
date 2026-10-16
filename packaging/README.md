# DDI V13.0 打包配置

## 当前打包脚本

- `DDI_V13.0.spec`
- `DDI_V13.0_GUI.spec`
- `DDI_V13.0_onefile.spec`
- `DDI_V13.0_GUI_onefile.spec`
- `build_release.ps1`

构建发布结果统一写入项目级 `dist`；PyInstaller 中间文件统一写入 `runtime/archive/generated/build`，不再在 `packaging` 下生成 `release`。

## 单文件版说明

`DDI_V13.0_onefile.spec` 与 `DDI_V13.0_GUI_onefile.spec` 生成仅含两个可执行文件的单文件分发（`dist\DDI_V13.0_单文件版`），已剔除 torch/torchvision 等无关依赖。单文件版每次启动需要自解压（约 10 秒），配置、授权与运行产物从可执行文件所在目录读取：`config\license.json` 放在 exe 旁即可生效。

## 全量账密内嵌

四个 spec 均把 `ddi_framework\account_config_local.py` 内嵌为运行资源。程序在打包环境优先读取 exe 旁的同名覆盖文件，不存在时使用内嵌全量账密，交付后无需另行配置账号。`license_tool.py` 与 `ddi_license_*.pem` 签发材料不参与任何构建。

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
- 交付时发送整个 `dist\DDI_V13.0` 目录，其中包含终端版 `DDI_V13.0.exe` 与 GUI 版 `DDI_V13.0_GUI.exe`，而不是只发送任一可执行文件。
- `docs` 和维护者个人参考材料不属于分发内容。

## GUI 构建说明

- 图形界面使用固定版本 `PySide6==6.11.1` 和 QML / Qt Quick；不再依赖 CustomTkinter、Tk Canvas 或系统壁纸亚克力。
- `DDI_V13.0_GUI.spec` 会收集 PySide6 Qt Quick 运行资源和项目 `ui` 资源目录，确保 `Main.qml` 能在 onedir 发布包中加载。
- `build_release.ps1` 安装 GUI 依赖时优先使用清华 PyPI 镜像，并将 GUI 与终端合并到同一个 `DDI_V13.0` onedir 目录。
- 终端使用 `_cli_internal` 独立运行时目录，GUI 使用 `_internal` 独立运行时目录，避免终端依赖覆盖 Qt 运行库。
