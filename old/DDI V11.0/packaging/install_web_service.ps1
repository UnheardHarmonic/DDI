<#
.SYNOPSIS
安装或更新 DDI 网页入口 Windows 服务。

.DESCRIPTION
本脚本使用 NSSM 创建仅在本机回环地址监听的 DDI 网页服务。
Cloudflare Tunnel 负责对外转发；脚本不会开放 Windows 防火墙端口。

.PARAMETER AllowedEmails
允许访问网页入口的 Cloudflare Access 邮箱列表，使用英文逗号分隔。

.PARAMETER ServiceName
Windows 服务名称。

.PARAMETER PythonExecutable
部署电脑使用的 Python 解释器路径。

.OUTPUTS
System.String
服务安装或更新结果说明。
#>

# 声明服务安装所需的邮箱、服务名与 Python 解释器参数。
param(
    [Parameter(Mandatory = $true)] [string]$AllowedEmails,
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

# 解析私有账号配置文件路径。
$LocalAccountConfigPath = Join-Path $ProjectRoot 'ddi_framework\account_config_local.py'

# 查找 NSSM 服务管理器可执行文件。
$NssmCommand = Get-Command nssm.exe -ErrorAction SilentlyContinue

# 校验部署电脑已安装 NSSM 服务管理器。
if (-not $NssmCommand) {

    # 停止缺少 NSSM 服务管理器的服务安装。
    throw '未找到 nssm.exe。请先安装 NSSM 并将其目录加入 PATH，然后重新运行本脚本。'
}

# 校验部署电脑已配置私有账号文件。
if (-not (Test-Path -LiteralPath $LocalAccountConfigPath)) {

    # 停止未配置账号凭据的服务安装。
    throw "缺少私有账号配置文件：$LocalAccountConfigPath"
}

# 校验指定 Python 解释器可运行。
& $PythonExecutable -X utf8 -c "import sys; print(sys.executable)"

# 判断 Python 解释器校验是否失败。
if ($LASTEXITCODE -ne 0) {

    # 停止无效 Python 解释器的服务安装。
    throw "无法运行 Python 解释器：$PythonExecutable"
}

# 查询是否已存在同名 Windows 服务。
$ExistingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

# 停止已运行的同名服务。
if ($ExistingService -and $ExistingService.Status -ne 'Stopped') {

    # 停止现有 Windows 服务。
    Stop-Service -Name $ServiceName -Force
}

# 删除已存在的同名 NSSM 服务注册。
if ($ExistingService) {

    # 删除原有 NSSM 服务注册。
    & $NssmCommand.Source remove $ServiceName confirm
}

# 解析实际 Python 解释器路径。
$ResolvedPythonPath = (& $PythonExecutable -X utf8 -c "import sys; print(sys.executable)").Trim()

# 创建由 NSSM 托管的 Python 网页服务。
& $NssmCommand.Source install $ServiceName $ResolvedPythonPath '-X utf8 -m ddi_web'

# 设置网页服务的工作目录为项目根目录。
& $NssmCommand.Source set $ServiceName AppDirectory $ProjectRoot

# 设置网页服务仅使用明确允许邮箱列表。
& $NssmCommand.Source set $ServiceName AppEnvironmentExtra "DDI_ALLOWED_EMAILS=$AllowedEmails"

# 设置网页服务在异常退出后自动重启。
& $NssmCommand.Source set $ServiceName AppExit Default Restart

# 设置网页服务开机自动启动。
& $NssmCommand.Source set $ServiceName Start SERVICE_AUTO_START

# 启动新创建的网页服务。
Start-Service -Name $ServiceName

# 输出当前服务状态。
Get-Service -Name $ServiceName | Select-Object Name, Status, StartType
