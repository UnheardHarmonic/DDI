# 逆向神力

DDI 协议直连数据导出工具。

项目通过统一的公共业务层执行各商业平台的登录、查询、Excel 导出与任务日志；终端、桌面 GUI 和网页入口均复用同一套无界面任务运行时。

## 网页入口

网页入口通过 Cloudflare Access 与 Cloudflare Tunnel 暴露给已授权同事。账号密码、授权文件、Cookie 和商业平台会话只存放在部署电脑，不提交到 GitHub，也不会下发到浏览器；同事可下载自己任务生成的 Excel 与日志 ZIP 文件。

完整部署步骤见 [网页入口部署说明](docs/WEB_DEPLOYMENT.md)。

## 本地运行

```powershell
python -X utf8 -m pip install -r requirements-web.txt
Copy-Item .\ddi_framework\account_config.py .\ddi_framework\account_config_local.py
$env:DDI_ALLOWED_EMAILS = 'colleague@example.com'
python -X utf8 -m ddi_web
```

服务仅监听 `127.0.0.1:8787`，必须通过 Cloudflare Tunnel 对外提供访问，不应直接暴露公网端口。
