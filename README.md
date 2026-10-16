# 逆向神力

DDI 协议直连数据导出工具。

项目通过统一的公共业务层执行各商业平台的登录、查询、Excel 导出与任务日志；终端、桌面 GUI 和网页入口均复用同一套无界面任务运行时。

## 本机 Web GUI

网页入口仅用于本机浏览器操作：服务固定监听 `127.0.0.1`，不包含 Cloudflare Access、Tunnel、临时访问口令或云端任务归属控制。账号密码、授权文件、Cookie 与商业平台会话均只保留在本机运行目录。

## 本地运行

```powershell
python -X utf8 -m pip install -r requirements-web.txt
Copy-Item .\ddi_framework\account_config.py .\ddi_framework\account_config_local.py
python -X utf8 .\run_ddi_web.py
```

可通过 `--port` 修改本机端口。服务不会监听公网地址。
