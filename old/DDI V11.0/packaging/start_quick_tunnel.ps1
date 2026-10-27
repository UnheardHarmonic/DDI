<#
.SYNOPSIS
Starts the local DDI web service and a free Cloudflare Quick Tunnel.

.DESCRIPTION
The script creates an ephemeral access key, starts the DDI API on loopback,
and starts a trycloudflare.com tunnel. Keep this console open while colleagues use the link.

.PARAMETER PythonExecutable
Specifies the Python executable used to run the local DDI API.

.PARAMETER Port
Specifies the loopback port used by the local DDI API.

.OUTPUTS
System.String
Writes the temporary access key and Cloudflare tunnel URL to the console.
#>

# Declares the optional local Python executable and loopback port parameters.
param(
    [string]$PythonExecutable,
    [int]$Port
)

# Sets UTF-8 encoding for PowerShell output.
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# Sets UTF-8 encoding for PowerShell console input.
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)

# Sets UTF-8 encoding for PowerShell console output.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# Sets UTF-8 encoding for Python process input and output.
$env:PYTHONIOENCODING = 'utf-8'

# Enables Python UTF-8 mode for the local service process.
$env:PYTHONUTF8 = '1'

# Resolves the project root from the packaging directory.
$ProjectRoot = Split-Path -LiteralPath $PSScriptRoot -Parent

# Assigns the project virtual-environment Python executable when none is supplied.
if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {

    # Stores the default project virtual-environment Python executable path.
    $PythonExecutable = '.\.venv\Scripts\python.exe'
}

# Assigns the DDI default web port when none is supplied.
if ($Port -le 0) {

    # Stores the DDI default loopback port.
    $Port = 8787
}

# Locates the Cloudflare Tunnel client executable.
$CloudflaredCommand = Get-Command cloudflared.exe -ErrorAction SilentlyContinue

# Stops startup when the Cloudflare Tunnel client is unavailable.
if (-not $CloudflaredCommand) {

    # Raises a clear installation requirement error.
    throw 'cloudflared.exe is required before starting a Quick Tunnel.'
}

# Resolves the configured Python executable relative to the project root.
$ResolvedPythonPath = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot $PythonExecutable)).Path

# Stops startup when the configured Python executable is unavailable.
if (-not (Test-Path -LiteralPath $ResolvedPythonPath -PathType Leaf)) {

    # Raises a clear Python executable error.
    throw "Python executable was not found: $ResolvedPythonPath"
}

# Generates an ephemeral high-entropy access key for the current tunnel session.
$TemporaryAccessKey = [Convert]::ToBase64String((1..24 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 256) })).TrimEnd('=')

# Passes the temporary access key only to the local DDI service process.
$env:DDI_TEMPORARY_ACCESS_KEY = $TemporaryAccessKey

# Removes Cloudflare Access allow-list configuration for the temporary tunnel mode.
Remove-Item Env:DDI_ALLOWED_EMAILS -ErrorAction SilentlyContinue

# Starts the DDI API with loopback-only network exposure.
$WebProcess = Start-Process -FilePath $ResolvedPythonPath -ArgumentList '-X','utf8','-m','uvicorn','ddi_web:app','--host','127.0.0.1','--port',([string]$Port) -WorkingDirectory $ProjectRoot -PassThru

# Waits briefly for the local API process to bind its loopback port.
Start-Sleep -Seconds 3

# Verifies that the local DDI homepage responds before opening the public tunnel.
try {

    # Requests the local homepage for service readiness confirmation.
    $null = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/" -TimeoutSec 10
}
catch {

    # Stops the local API process after startup verification fails.
    Stop-Process -Id $WebProcess.Id -Force -ErrorAction SilentlyContinue

    # Raises the local startup failure details.
    throw "DDI web service did not start: $($_.Exception.Message)"
}

# Writes the current ephemeral access key for authorized colleagues.
Write-Host "DDI temporary access key: $TemporaryAccessKey"

# Writes the sharing instruction before Cloudflare prints the public URL.
Write-Host 'Share the trycloudflare.com URL and this access key only with authorized colleagues.'

# Starts the free Cloudflare Quick Tunnel and keeps this console attached to it.
& $CloudflaredCommand.Source tunnel --url "http://127.0.0.1:$Port"

# Stops the local API process after the Cloudflare Quick Tunnel exits.
Stop-Process -Id $WebProcess.Id -Force -ErrorAction SilentlyContinue
