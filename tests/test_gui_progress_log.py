# -*- coding: utf-8 -*-
"""
GUI 队列进度日志防刷屏契约测试。

本模块验证队列进度事件只原地刷新页首状态条、不再写入滚动日志，
同时保留真实业务事件的日志输出，全部离线执行不触网。
"""

# 导入操作系统环境模块。
import os

# 指定 Qt 离屏渲染平台，保证无显示器环境可运行。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入 Qt 应用对象。
from PySide6.QtWidgets import QApplication

# 导入任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入 GUI 视图模型。
from ddi_gui_qt import DdiGuiViewModel


# 定义队列进度防刷屏测试套件。
class GuiProgressLogTests(unittest.TestCase):

    """
    验证队列进度事件的日志防刷屏与状态条刷新行为。

    :return: 测试套件实例。
    :rtype: GuiProgressLogTests
    """

    # 定义套件级初始化方法。
    @classmethod
    def setUpClass(cls):

        """
        创建离屏 Qt 应用与 GUI 视图模型。

        :return: None。
        :rtype: None
        """

        # 复用或创建全局 Qt 应用实例。
        cls.app = QApplication.instance() or QApplication([])

        # 创建 GUI 视图模型实例。
        cls.viewModel = DdiGuiViewModel(str(Path(__file__).resolve().parents[1]))

    # 定义队列进度不写入滚动日志验证。
    def test_progress_events_do_not_flood_log(self):

        """
        验证连续进度事件零日志行且状态条文本原地更新。

        :return: None。
        :rtype: None
        """

        # 连续投递五条队列进度事件。
        for round_index in range(5):

            # 构建队列进度事件。
            event = TaskEvent(event_type="task_progress", message="任务队列运行中", status="信息", payload={"完成": 2, "总数": 5, "成功": 2, "失败": 0, "停止": 0, "运行中": 3, "待提交": 0, "耗时秒": round_index + 0.5})

            # 同步事件到视图模型。
            refresh_flags = self.viewModel.handle_task_event(event)

            # 批量落盘待写日志。
            self.viewModel.publish_event_refreshes(refresh_flags)

        # 断言滚动日志零进度行。
        self.assertEqual(self.viewModel.log_model.rowCount(), 0)

        # 断言待写日志集合为空。
        self.assertEqual(len(self.viewModel.pending_log_rows), 0)

        # 断言状态条文本携带完成度与耗时。
        self.assertEqual(self.viewModel.task_state["status"], "任务运行中 · 完成 2/5 · 运行中 3 · 耗时 4.5秒")

    # 定义真实事件日志保留验证。
    def test_real_events_still_logged(self):

        """
        验证商业完成与批量结束事件正常写入滚动日志。

        :return: None。
        :rtype: None
        """

        # 构建商业完成事件。
        company_event = TaskEvent(event_type="company_finished", message="商业任务执行完成", status="成功", company_name="测试商业", data_type="配送流向", payload={"完成": 1, "总数": 5, "并发槽位": 0})

        # 同步商业完成事件。
        refresh_flags = self.viewModel.handle_task_event(company_event)

        # 批量落盘待写日志。
        self.viewModel.publish_event_refreshes(refresh_flags)

        # 构建批量结束事件。
        finish_event = TaskEvent(event_type="task_finished", message="批量任务已结束", status="成功", payload={"完成": 5, "总数": 5, "成功": 5, "失败": 0, "停止": 0, "运行中": 0, "待提交": 0, "耗时秒": 30.0})

        # 同步批量结束事件。
        refresh_flags = self.viewModel.handle_task_event(finish_event)

        # 批量落盘待写日志。
        self.viewModel.publish_event_refreshes(refresh_flags)

        # 断言滚动日志恰好保留两条真实事件。
        self.assertEqual(self.viewModel.log_model.rowCount(), 2)

        # 断言任务已结束状态复位。
        self.assertFalse(self.viewModel.task_state["running"])

        # 断言结束状态文本。
        self.assertEqual(self.viewModel.task_state["status"], "任务执行完成")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
