# -*- coding: utf-8 -*-
"""
DDI 本机 Web 任务状态服务测试。

本模块验证本机 Web 的安全停止状态会如实反映公共任务协调器结果。

:return: 模块提供本机 Web 任务状态测试用例。
:rtype: None
"""

# 导入临时目录工具。
import tempfile

# 导入轻量对象容器。
from types import SimpleNamespace

# 导入单元测试框架。
import unittest

# 导入公共任务取消控制器。
from ddi_framework.task_core import TaskCancellation

# 导入本机 Web 任务服务。
from ddi_web import WebTaskService


# 定义本机 Web 任务服务测试类。
class WebTaskServiceTests(unittest.TestCase):

    """
    验证本机 Web 的任务完成和安全停止状态语义。

    :return: None。
    :rtype: None
    """

    # 定义任务完成状态解析测试方法。
    def test_completion_status_distinguishes_safe_stop(self):

        """
        验证存在未启动商业时任务终态为已停止而非已完成。

        :return: None。
        :rtype: None
        """

        # 创建隔离的本机 Web 服务目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 创建待测本机 Web 任务服务。
            service = WebTaskService(project_root)

            # 构造没有安全停止商业的任务汇总。
            completed_result = SimpleNamespace(stopped_count=0)

            # 构造包含安全停止商业的任务汇总。
            stopped_result = SimpleNamespace(stopped_count=2)

            # 解析正常完成任务的最终状态。
            completed_status, completed_message = service.resolve_completion_status(completed_result)

            # 解析安全停止任务的最终状态。
            stopped_status, stopped_message = service.resolve_completion_status(stopped_result)

            # 关闭测试创建的后台执行器。
            service.executor.shutdown(wait=True)

        # 断言正常任务保持已完成终态。
        self.assertEqual((completed_status, completed_message), ("已完成", "任务执行完成"))

        # 断言安全停止任务使用已停止终态。
        self.assertEqual((stopped_status, stopped_message), ("已停止", "任务已安全停止，未启动商业 2 家"))

    # 定义停止请求状态测试方法。
    def test_stop_marks_running_task_as_stop_requested(self):

        """
        验证运行中任务收到停止请求后立即公开停止请求状态。

        :return: None。
        :rtype: None
        """

        # 创建隔离的本机 Web 服务目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 创建待测本机 Web 任务服务。
            service = WebTaskService(project_root)

            # 创建运行中任务对应的取消控制器。
            cancellation = TaskCancellation()

            # 在锁内登记模拟运行中任务。
            with service.lock:

                # 保存浏览器可读取的模拟运行任务状态。
                service.records["task-1"] = {"task_id": "task-1", "status": "运行中", "message": "正在执行公共 DDI 任务", "result": None, "artifacts": []}

                # 保存模拟运行任务的取消控制器。
                service.cancellations["task-1"] = cancellation

            # 请求安全停止当前模拟运行任务。
            record = service.stop("task-1")

            # 关闭测试创建的后台执行器。
            service.executor.shutdown(wait=True)

        # 断言公共取消控制器已接收停止请求。
        self.assertTrue(cancellation.is_stop_requested())

        # 断言浏览器立即展示停止请求状态。
        self.assertEqual(record["status"], "停止请求中")

    # 定义终态任务停止保护测试方法。
    def test_stop_keeps_completed_task_in_terminal_status(self):

        """
        验证停止已结束任务时保留其已有终态。

        :return: None。
        :rtype: None
        """

        # 创建隔离的本机 Web 服务目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 创建待测本机 Web 任务服务。
            service = WebTaskService(project_root)

            # 在锁内登记已完成任务。
            with service.lock:

                # 保存浏览器可读取的已完成任务状态。
                service.records["task-2"] = {"task_id": "task-2", "status": "已完成", "message": "任务执行完成", "result": {"成功": 1}, "artifacts": []}

            # 请求停止已经完成的任务。
            record = service.stop("task-2")

            # 关闭测试创建的后台执行器。
            service.executor.shutdown(wait=True)

        # 断言已完成任务不被回写为停止请求中。
        self.assertEqual(record["status"], "已完成")


# 定义直接运行测试模块入口。
if __name__ == "__main__":

    # 执行本模块单元测试。
    unittest.main()
