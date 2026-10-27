# -*- coding: utf-8 -*-
"""
DDI Qt Quick 图形界面入口。

本模块仅启动 PySide6 与 QML 展示层，并把公共任务事件交给 GUI ViewModel。
登录、查询、导出、Excel 和授权仍由 ddi_framework 无界面公共层处理。
"""

# 导入 Qt GUI 启动函数。
from ddi_gui_qt import main

# 导入公共事件接收器以兼容展示层测试和外部调用。
from ddi_gui_qt import QueueTaskEventSink


# 判断当前文件是否以脚本方式运行。
if __name__ == "__main__":

    # 启动 Qt Quick 图形界面并返回进程退出码。
    raise SystemExit(main())
