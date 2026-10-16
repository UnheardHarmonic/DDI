# -*- mode: python ; coding: utf-8 -*-
"""
DDI V13.0 终端单文件 PyInstaller 构建配置。

本 spec 将终端入口与全部依赖打包为单个可执行文件，不生成伴随运行时目录。
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

# 收集验证码识别运行依赖。
tmp_ret = collect_all("ddddocr")
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all("onnxruntime")
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# 收集 Excel 与平台适配运行依赖。
for package_name in ["cv2", "numpy", "PIL", "openpyxl", "xlrd", "olefile", "cryptography"]:

    # 收集当前运行依赖。
    tmp_ret = collect_all(package_name)

    # 追加当前运行依赖数据文件。
    datas += tmp_ret[0]

    # 追加当前运行依赖二进制文件。
    binaries += tmp_ret[1]

    # 追加当前运行依赖隐藏导入。
    hiddenimports += tmp_ret[2]

# 分析终端入口依赖。
a = Analysis(
    [str(project_root / "run_ddi.py")],
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

# 构建包含全部依赖的单文件终端可执行文件。
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DDI_V13.0",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
