$ErrorActionPreference = 'Stop'

# 固定 Python 子进程使用 UTF-8 解析中文依赖文件。
$env:PYTHONUTF8 = '1'

# 使用国内 PyPI 镜像安装 GUI 依赖。
$guiPypiMirror = 'https://pypi.tuna.tsinghua.edu.cn/simple'

# 解析 DDI 项目根目录。
$projectRoot = Split-Path -Parent $PSScriptRoot

# 解析终端入口打包配置路径。
$cliSpecPath = Join-Path $PSScriptRoot 'DDI_V12.0.spec'

# 解析 GUI 入口打包配置路径。
$guiSpecPath = Join-Path $PSScriptRoot 'DDI_V12.0_GUI.spec'

# 解析发布根目录。
$releaseRoot = Join-Path $projectRoot 'dist'

# 解析共享双入口发布目录。
$distributionRoot = Join-Path $releaseRoot 'DDI_V12.0'

# 解析 GUI 临时构建输出目录。
$guiDistributionRoot = Join-Path $releaseRoot 'DDI_V12.0_GUI_BUILD'

# 解析终端构建工作目录。
$cliBuildRoot = Join-Path $projectRoot 'runtime\archive\generated\build\DDI_V12.0'

# 解析 GUI 构建工作目录。
$guiBuildRoot = Join-Path $projectRoot 'runtime\archive\generated\build\DDI_V12.0_GUI'

# 确保发布根目录存在。
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

# 解析发布根目录绝对路径。
$resolvedReleaseRoot = [System.IO.Path]::GetFullPath($releaseRoot)

# 解析共享发布目录绝对路径。
$resolvedDistributionRoot = [System.IO.Path]::GetFullPath($distributionRoot)

# 校验共享发布目录仍位于发布根目录内。
if (-not ($resolvedDistributionRoot.StartsWith($resolvedReleaseRoot, [System.StringComparison]::OrdinalIgnoreCase))) {
    throw "发布目录不在允许范围内：$resolvedDistributionRoot"
}

# 清理历史共享发布目录。
if (Test-Path -LiteralPath $distributionRoot -PathType Container) {
    Remove-Item -LiteralPath $distributionRoot -Recurse -Force
}

# 校验 GUI 构建依赖可安装。
python -m pip install -r (Join-Path $projectRoot 'requirements-gui.txt') -i $guiPypiMirror --disable-pip-version-check

# 打包终端入口到共享发布目录。
python -m PyInstaller $cliSpecPath --noconfirm --clean --distpath $releaseRoot --workpath $cliBuildRoot

# 校验终端入口打包命令执行成功。
if ($LASTEXITCODE -ne 0) {
    throw "终端入口 PyInstaller 构建失败，退出码：$LASTEXITCODE"
}

# 打包 GUI 入口到临时构建目录。
python -m PyInstaller $guiSpecPath --noconfirm --clean --distpath $releaseRoot --workpath $guiBuildRoot

# 校验 GUI 入口打包命令执行成功。
if ($LASTEXITCODE -ne 0) {
    throw "GUI 入口 PyInstaller 构建失败，退出码：$LASTEXITCODE"
}

# 校验终端入口发布目录已生成。
if (-not (Test-Path -LiteralPath $distributionRoot -PathType Container)) {
    throw "终端发布目录未生成：$distributionRoot"
}

# 校验 GUI 临时发布目录已生成。
if (-not (Test-Path -LiteralPath $guiDistributionRoot -PathType Container)) {
    throw "GUI 临时发布目录未生成：$guiDistributionRoot"
}

# 复制 GUI 可执行文件到共享发布目录。
Copy-Item -LiteralPath (Join-Path $guiDistributionRoot 'DDI_V12.0_GUI.exe') -Destination (Join-Path $distributionRoot 'DDI_V12.0_GUI.exe') -Force

# 复制 GUI 独立运行时目录到共享发布目录。
Copy-Item -LiteralPath (Join-Path $guiDistributionRoot '_internal') -Destination $distributionRoot -Recurse -Force

# 定义 GUI 运行时中会覆盖系统 Qt ICU 的旧版文件名。
$guiLegacyIcuNames = @('icuuc.dll', 'icudt58.dll')

# 遍历 GUI 运行时旧版 ICU 文件名。
foreach ($legacyIcuName in $guiLegacyIcuNames) {

    # 解析 GUI 运行时旧版 ICU 文件路径。
    $legacyIcuPath = Join-Path (Join-Path $distributionRoot '_internal') $legacyIcuName

    # 删除会抢占 Qt6Core 系统 ICU 的旧版文件。
    if (Test-Path -LiteralPath $legacyIcuPath -PathType Leaf) {

        # 清理 GUI 运行时旧版 ICU 文件。
        Remove-Item -LiteralPath $legacyIcuPath -Force
    }
}

# 解析 GUI 临时发布目录绝对路径。
$resolvedGuiDistributionRoot = [System.IO.Path]::GetFullPath($guiDistributionRoot)

# 校验 GUI 临时发布目录仍位于发布根目录内。
if (-not ($resolvedGuiDistributionRoot.StartsWith($resolvedReleaseRoot, [System.StringComparison]::OrdinalIgnoreCase))) {
    throw "GUI 临时发布目录不在允许范围内：$resolvedGuiDistributionRoot"
}

# 删除已合并的 GUI 临时发布目录。
Remove-Item -LiteralPath $guiDistributionRoot -Recurse -Force

# 定位共享发布目录中的运行产物目录。
$runtimeRoot = Join-Path $distributionRoot 'runtime'

# 解析运行产物目录绝对路径。
$resolvedRuntimeRoot = [System.IO.Path]::GetFullPath($runtimeRoot)

# 校验运行产物目录仍位于共享发布目录内。
if (-not ($resolvedRuntimeRoot.StartsWith($resolvedDistributionRoot, [System.StringComparison]::OrdinalIgnoreCase))) {
    throw "运行产物目录不在允许范围内：$resolvedRuntimeRoot"
}

# 清理发布目录中不应交付的运行产物目录。
if (Test-Path -LiteralPath $runtimeRoot -PathType Container) {
    Remove-Item -LiteralPath $runtimeRoot -Recurse -Force
}

# 创建共享配置目录。
$configRoot = Join-Path $distributionRoot 'config'

# 确保共享配置目录存在。
New-Item -ItemType Directory -Path $configRoot -Force | Out-Null

# 复制商业启停运行配置。
Copy-Item -LiteralPath (Join-Path $projectRoot 'config\account_runtime.json') -Destination (Join-Path $configRoot 'account_runtime.json') -Force

# 复制 GUI 快捷方案模板。
Copy-Item -LiteralPath (Join-Path $projectRoot 'config\gui_presets.json') -Destination (Join-Path $configRoot 'gui_presets.json') -Force

# 复制同事使用说明。
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'COLLEAGUE_GUIDE.md') -Destination (Join-Path $distributionRoot 'COLLEAGUE_GUIDE.md') -Force


