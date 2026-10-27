<#
.SYNOPSIS
拉取 GitHub 最新代码并重启 DDI 网页入口服务。

.DESCRIPTION
本脚本只允许快进更新，安装清单依赖后重启既有 Windows 服务。
它不会修改私有账号配置、授权文件、运行期配置或 Cloudflare Tunnel 凭据。

.PARAMETER ServiceName
Windows 服务名称。

.PARAMETER PythonExecutable
部署电脑使用的 Python 解释器路径。

.OUTPUTS
System.String
更新后的 Git 提交信息与 Windows 服务状态。
#>

# 声明服务更新所需的服务名与 Python 解释器参数。
param(
    [string]$ServiceName = 'DDIWeb',
    [string]$PythonExecutable = 'python'
)

# 设置 PowerShell 输出编码为 UTF-8。
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# 设置控制台输入编码为 UTF-8。
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)

# 设置控制台输出编码为 UTF-8。
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# 解析当前脚本所在的项目根目录。
$ProjectRoot = Split-Path -LiteralPath $PSScriptRoot -Parent

# 切换到 Git 仓库根目录。
Set-Location -LiteralPath $ProjectRoot

# 校验当前工作区不存在未提交源码修改。
if (git status --porcelain) {

    # 停止包含未提交源码修改的自动更新。
    throw '工作区存在未提交修改，已停止自动更新。'
}

# 仅使用快进模式拉取远程主分支更新。
git pull --ff-only origin main

# 判断 Git 拉取操作是否失败。
if ($LASTEXITCODE -ne 0) {

    # 停止 Git 拉取失败后的依赖更新。
    throw 'GitHub 更新拉取失败。'
}

# 安装当前提交声明的网页运行依赖。
& $PythonExecutable -X utf8 -m pip install -r requirements-web.txt

# 判断依赖安装是否失败。
if ($LASTEXITCODE -ne 0) {

    # 停止依赖安装失败后的服务重启。
    throw '网页运行依赖安装失败。'
}

# 重启既有网页入口 Windows 服务。
Restart-Service -Name $ServiceName -Force

# 输出当前 Git 提交信息。
git log --oneline -1

# 输出更新后的服务状态。
Get-Service -Name $ServiceName | Select-Object Name, Status, StartType
