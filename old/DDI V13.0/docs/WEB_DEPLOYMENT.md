# DDI 本机 Web GUI 使用说明

本机 Web GUI 仅用于当前电脑上的浏览器任务操作。服务默认监听 `127.0.0.1:8787`，不提供 Cloudflare Tunnel、Cloudflare Access、临时访问口令、云端文件归属或公网部署能力。

## 启动

```powershell
python -X utf8 -m pip install -r requirements-web.txt
python -X utf8 .\run_ddi_web.py
```

启动器会自动打开默认浏览器。需要调整端口时执行：

```powershell
python -X utf8 .\run_ddi_web.py --port 8788
```

## 使用规则

- 商业、负责人、大区、省份、平台、启停状态和数据类型均来自公共账号配置。
- 数据类型支持全局多选、全选与清空；商业未声明的类型会被跳过并写入任务结果。
- 日期模式支持上月整月、上月一日至今天和自定义范围。
- 本机 Web 的任务状态、事件记录和下载索引保留在 `runtime\work\web`；Cookie、原始 Excel、复制用 Excel 和日志仍由公共运行时分别写入 `runtime\cookies`、`runtime\downloads` 和 `runtime\logs`，不上传到外部服务。
- 浏览器只展示公共 `DdiTaskRuntime` 产生的任务事件和本机文件下载入口。
