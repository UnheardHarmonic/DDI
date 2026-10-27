# -*- coding: utf-8 -*-
"""
DDI 本机 Web GUI 启动入口。

本模块仅启动本机 FastAPI 服务和浏览器展示层，协议执行继续由公共任务运行时负责。
"""

# 导入命令行参数模块。
import argparse

# 导入浏览器打开工具。
import webbrowser

# 导入线程启动工具。
from threading import Timer

# 导入 Uvicorn 服务模块。
import uvicorn

# 导入本地 Web 应用。
from ddi_web import app

# 导入目录说明自愈服务。
from ddi_framework.directory_docs import ensure_directory_documents

# 解析本机项目根目录。
from pathlib import Path

# 计算启动入口所属项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parent


# 定义本机 Web 启动函数。
def main():

    """
    启动本机 Web GUI 并打开系统浏览器。

    :return: 服务退出码。
    :rtype: int
    """

    # 创建本机 Web 参数解析器。
    parser = argparse.ArgumentParser(description="DDI 本机 Web GUI")

    # 注册本机监听端口。
    parser.add_argument("--port", type=int, default=8787, help="本机 Web 端口")

    # 解析启动参数。
    args = parser.parse_args()

    # 启动服务前补齐缺失的受管目录说明。
    ensure_directory_documents(PROJECT_ROOT)

    # 延迟打开本机浏览器页面。
    Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}/")).start()

    # 启动本机 Uvicorn 服务。
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")

    # 返回正常退出码。
    return 0


# 判断当前模块是否被直接执行。
if __name__ == "__main__":

    # 启动本机 Web GUI。
    raise SystemExit(main())
