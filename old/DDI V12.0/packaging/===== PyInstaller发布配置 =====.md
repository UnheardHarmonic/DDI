# PyInstaller 发布配置

本目录只保存发布构建所需的 spec、PowerShell 脚本和同事交付说明。构建中间文件和发布目录不在此长期保存，统一输出到 `runtime/archive/generated` 或用户指定的分发位置。

- `DDI_V12.0.spec`：终端入口构建配置。
- `DDI_V12.0_GUI.spec`：Qt GUI 构建配置，并收集 `ui` 资源。
- `build_release.ps1`：构建、合并和发布目录校验脚本。
- `COLLEAGUE_GUIDE.md`：交付给使用者的操作说明。
