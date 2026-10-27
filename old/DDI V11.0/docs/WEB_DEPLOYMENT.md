# DDI 网页入口部署

## 架构

同事浏览器通过 Cloudflare Access 登录后访问 Cloudflare Tunnel。隧道将请求转发到部署电脑上的 DDI Web 服务。服务仍在部署电脑中运行公共 DDI 任务层，账号密码、授权文件、Cookie 和源码不会传到浏览器或 Cloudflare Pages。任务完成后，同事可下载自己任务生成的 Excel 与任务日志 ZIP 文件。

```text
同事浏览器 -> Cloudflare Access -> Cloudflare Tunnel -> 部署电脑上的 DDI Web 服务 -> 商业平台
```

Cloudflare Pages 或 Workers 不能直接运行本项目：项目依赖 Python、PySide、Windows 文件系统、授权文件和对外商业平台会话。它们可以承载静态页面，但不能替代 DDI 协议执行服务。

## 发布前安全要求

1. 先在 GitHub 将仓库改名为 `reverse-power`。GitHub 仓库链接名仅允许英文字母、数字、点、连字符与下划线；项目中文名称“逆向神力”已在 README 和网页服务中显示。
2. 将仓库设为 Private，再推送源码。
3. 轮换 `ddi_framework/account_config_local.py` 中全部商业平台密码。该文件包含明文凭据，不得提交到 GitHub。
4. 将真实的 `ddi_framework/account_config_local.py`、`config/account_runtime.json`、`config/license.json` 仅保留在部署电脑；它们已加入 `.gitignore`。
5. 所有生成文件只存放在 `runtime/`，并定期清理会话、Cookie、日志和导出结果。
6. 提交的 `ddi_framework/account_config.py` 是空白账号密码模板。首次部署必须复制生成 `account_config_local.py`，再填入私有凭据。

## GitHub 初始化

在项目根目录执行以下命令。首次 `push` 时 Git Credential Manager 会要求登录 GitHub。

```powershell
git remote set-url origin https://github.com/UnheardHarmonic/reverse-power.git
git push -u origin main
```

执行 `git status` 前必须确认以下敏感文件没有出现在暂存区：

```powershell
git check-ignore -v ddi_framework/account_config_local.py config/account_runtime.json config/license.json
```

## 部署电脑

部署电脑必须长期在线，并安装本项目要求的 Python 运行环境。建议使用单独的 Windows 账户运行服务，并将项目目录的读写权限限制为维护人员。

每次更新使用以下流程：

```powershell
git pull --ff-only origin main
python -X utf8 -m pip install -r requirements-web.txt
$env:DDI_ALLOWED_EMAILS = '同事1@公司域名,同事2@公司域名'
python -X utf8 -m ddi_web
```

首次部署完成后，请安装 [NSSM](https://nssm.cc/) 并将其目录加入 `PATH`，再以管理员身份运行 `packaging/install_web_service.ps1` 将网页服务注册为 Windows 服务。以后更新只需要在部署电脑管理员 PowerShell 中运行：

```powershell
.\packaging\update_web_service.ps1
```

脚本只拉取 GitHub 主分支并重启网页服务，不会覆盖 `account_config_local.py`、授权文件、运行期配置或 Cloudflare Tunnel 凭据。

## Cloudflare Access 与 Tunnel

### 无域名免费测试

没有域名时可以使用 Cloudflare Quick Tunnel。它会生成一次性的 `trycloudflare.com` 地址，不需要付款或绑定域名；启动脚本窗口必须保持打开，地址在隧道停止后失效。该模式使用服务端随机访问口令保护网页，适合临时内网协作测试，不适合作为长期固定入口。

```powershell
.\packaging\start_quick_tunnel.ps1
```

脚本会输出访问口令，随后 Cloudflare 会输出临时网址。把两者一起发给同事；同事首次打开网页时输入访问口令。不要把口令提交到 GitHub 或写入脚本文件。

1. 在 Cloudflare Zero Trust 创建一个 Access Application，例如 `DDI 网页入口`。
2. 仅允许公司邮箱、指定邮箱列表或指定身份提供商组访问；不要使用公开 Allow policy。
3. 在部署电脑执行 `cloudflared tunnel login`，选择自己的 Cloudflare 域名。
4. 创建 Tunnel：`cloudflared tunnel create ddi-web`。
5. 将 Tunnel UUID 写入 `cloudflared/config.yml`，并把本地服务设为 `http://127.0.0.1:8787`。
6. 创建公开主机名，例如 `ddi.example.com`，绑定到该 Tunnel。
7. 安装 Tunnel 服务：`cloudflared service install`，随后使用 Windows 服务管理器确认它随系统启动。

`DDI_ALLOWED_EMAILS` 必须和 Cloudflare Access Policy 的允许人员保持一致；应用服务会再次检查该邮箱，避免仅通过 Tunnel 访问就取得任务权限。

示例配置：

```yaml
tunnel: <Tunnel UUID>
credentials-file: C:\\Users\\<Windows 用户>\\.cloudflared\\<Tunnel UUID>.json

ingress:
  - hostname: ddi.example.com
    service: http://127.0.0.1:8787
  - service: http_status:404
```

## 未决项

- 需要确认同事的 Cloudflare Access 身份来源：公司邮箱、Google/Microsoft 登录或一次性验证码。
- 需要确认部署电脑的位置和是否可以长期在线；若不能，则需改为 Windows 云服务器。
- 发布完成后，应安排 `runtime/web/` 的周期清理，清理间隔应与数据留存要求一致。
