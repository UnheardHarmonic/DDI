# 逆向神力

DDI 协议直连数据导出工具。

项目通过统一的公共业务层执行各商业平台的登录、查询、Excel 导出与任务日志；终端、桌面 GUI 和网页入口均复用同一套无界面任务运行时。

## 本地运行

```powershell
python -X utf8 -m pip install -r requirements-gui.txt
Copy-Item .\ddi_framework\account_config.py .\ddi_framework\account_config_local.py
python -X utf8 .\run_ddi.py --menu
```

桌面图形界面通过 `python -X utf8 .un_ddi_gui.py` 启动。
