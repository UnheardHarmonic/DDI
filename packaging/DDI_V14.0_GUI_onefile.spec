# -*- mode: python ; coding: utf-8 -*-
"""
DDI V14.0 图形界面单文件 PyInstaller 构建配置。

本 spec 将 Qt GUI 入口、QML 资源和全部依赖打包为单个可执行文件，不生成伴随运行时目录。
本 spec 仅用于打包独立 GUI 入口，不会被终端入口导入。
"""

# 导入路径对象。
from pathlib import Path

# 导入 PyInstaller 依赖收集函数。
from PyInstaller.utils.hooks import collect_all

# 解析 DDI 项目根目录。
project_root = Path(SPECPATH).resolve().parent

# 初始化数据文件集合。
datas = []

# 收集本机私有账号配置到运行资源根目录。
datas.append((str(project_root / "ddi_framework" / "account_config_local.py"), "."))

# 初始化二进制文件集合。
binaries = []

# 初始化隐藏导入集合。
hiddenimports = ["colorama", "bs4", "win32com.client"]

# 定义不参与打包的大体积无关依赖。
excludes = ["torch", "torchvision", "tensorboard", "huggingface_hub"]

# 收集 PySide6 Qt Quick 运行资源。
tmp_ret = collect_all("PySide6")

# 追加 PySide6 Qt Quick 数据文件。
datas += tmp_ret[0]

# 追加 PySide6 Qt Quick 二进制文件。
binaries += tmp_ret[1]

# 追加 PySide6 Qt Quick 隐藏导入。
hiddenimports += tmp_ret[2]

# 收集 QML 界面资源。
datas.append((str(project_root / "ui"), "ui"))

# 收集验证码识别运行依赖。
tmp_ret = collect_all("ddddocr")

# 追加验证码识别数据文件。
datas += tmp_ret[0]

# 追加验证码识别二进制文件。
binaries += tmp_ret[1]

# 追加验证码识别隐藏导入。
hiddenimports += tmp_ret[2]

# 收集 Excel 与平台适配运行依赖。
for package_name in ["onnxruntime", "cv2", "numpy", "PIL", "openpyxl", "xlrd", "olefile", "cryptography"]:

    # 收集当前运行依赖。
    tmp_ret = collect_all(package_name)

    # 追加当前运行依赖数据文件。
    datas += tmp_ret[0]

    # 追加当前运行依赖二进制文件。
    binaries += tmp_ret[1]

    # 追加当前运行依赖隐藏导入。
    hiddenimports += tmp_ret[2]

# 分析 GUI 入口依赖。
a = Analysis(
    [str(project_root / "run_ddi_gui.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# 构建 Python 模块归档。
pyz = PYZ(a.pure)

# 构建包含全部依赖的单文件 GUI 可执行文件。
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DDI_V14.0_GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
