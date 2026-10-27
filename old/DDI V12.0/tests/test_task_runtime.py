# -*- coding: utf-8 -*-
"""
DDI 公共任务运行时测试。

本模块使用模拟公共执行函数验证运行时会正确调用公共协议服务，不触发入口或内部回调同名遮蔽。
"""

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入函数模拟模块。
from unittest.mock import patch

# 导入商业账号配置。
from ddi_framework.account_config import ACCOUNTS

# 导入任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入公共任务运行时。
from ddi_framework.task_runtime import DdiTaskRuntime

# 导入 Excel 任务日志记录器。
from ddi_framework.task_log import TaskExcelLogger

# 导入公共日志输出器。
from ddi_framework.print_handler import PrintHandler


# 定义公共任务运行时测试类。
class TaskRuntimeTests(unittest.TestCase):

    """
    验证公共任务运行时对公共协议执行函数的调用关系。

    :return: None。
    :rtype: None
    """

    # 定义公共执行函数调用测试方法。
    def test_runtime_calls_the_public_protocol_executor(self):

        """
        验证运行时会调用公共协议执行函数并返回成功汇总。

        :return: None。
        :rtype: None
        """

        # 读取首个已配置商业名称。
        company_name = next(iter(ACCOUNTS))

        # 创建临时运行目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 构建无界面任务请求。
            request = TaskRequest("login", "全部", "2026-06-01", "2026-06-30", f"{project_root}/cookies", f"{project_root}/downloads", f"{project_root}/logs", 1)

            # 模拟授权校验结果。
            license_result = {"授权状态": "有效"}

            # 模拟公共协议执行结果。
            protocol_result = {"商业名称": company_name}

            # 模拟公共协议执行函数。
            with patch("ddi_framework.task_runtime.ensure_runtime_license", return_value=license_result), patch("ddi_framework.task_runtime.execute_protocol_company", return_value=protocol_result) as executor_mock:

                # 创建公共任务运行时。
                runtime = DdiTaskRuntime(project_root)

                # 执行模拟单商业任务。
                execution_result = runtime.execute(request, [company_name])

            # 断言公共协议执行函数被调用一次。
            executor_mock.assert_called_once()

            # 断言模拟任务执行成功。
            self.assertEqual(execution_result.task_result.success_count, 1)

            # 断言模拟任务未记录失败。
            self.assertEqual(execution_result.task_result.failure_count, 0)

    # 定义阶段时间线脱敏测试方法。
    def test_task_logger_publishes_sanitized_timeline_records(self):

        """
        验证阶段时间线监听器不会接收路径或异常详情字段。

        :return: None。
        :rtype: None
        """

        # 初始化接收时间线记录的列表。
        timeline_records = []

        # 创建临时日志目录。
        with tempfile.TemporaryDirectory() as output_dir:

            # 创建带时间线监听器的任务日志记录器。
            logger = TaskExcelLogger(output_dir, "2026-06-01", "2026-06-30", timeline_listener=timeline_records.append)

            # 写入包含敏感路径和异常详情的完整日志。
            logger.record(company_name="甲商业", platform_name="alpha", data_type="库存", stage="查询", status="成功", message="查询完成", record_count=3, file_path="D:/private/output.xlsx", cookie_path="D:/private/cookie.txt", error_detail="private error")

        # 断言监听器接收到一条时间线记录。
        self.assertEqual(len(timeline_records), 1)

        # 读取脱敏时间线记录。
        timeline_record = timeline_records[0]

        # 断言时间线记录不包含业务文件路径。
        self.assertNotIn("业务文件绝对路径", timeline_record)

        # 断言时间线记录不包含 Cookie 路径。
        self.assertNotIn("Cookie文件绝对路径", timeline_record)

        # 断言时间线记录不包含异常详情。
        self.assertNotIn("异常详情", timeline_record)

        # 断言运行日志保持当前固定字段集合。
        self.assertEqual(list(logger.rows[0]), ["运行日期", "任务开始时间", "阶段开始时间", "阶段结束时间", "耗时秒数", "商业名称", "平台", "数据类型", "查询开始日期", "查询结束日期", "执行阶段", "执行状态", "记录数量", "业务文件绝对路径", "Cookie文件绝对路径", "执行说明", "异常详情"])

    # 定义控制台镜像开关传递测试方法。
    def test_runtime_passes_console_output_option_to_print_handler(self):

        """
        验证公共运行时会将展示层指定的终端输出开关传给日志输出器。

        :return: None。
        :rtype: None
        """

        # 读取首个已配置商业名称。
        company_name = next(iter(ACCOUNTS))

        # 创建临时运行目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 构建关闭终端镜像的公共任务请求。
            request = TaskRequest("login", "全部", "2026-06-01", "2026-06-30", f"{project_root}/cookies", f"{project_root}/downloads", f"{project_root}/logs", 1, console_output_enabled=False)

            # 模拟授权校验结果。
            license_result = {"授权状态": "有效"}

            # 模拟公共协议执行结果。
            protocol_result = {"商业名称": company_name}

            # 模拟授权和协议执行服务并记录日志输出器构造参数。
            with patch("ddi_framework.task_runtime.ensure_runtime_license", return_value=license_result), patch("ddi_framework.task_runtime.execute_protocol_company", return_value=protocol_result), patch("ddi_framework.task_runtime.PrintHandler", wraps=PrintHandler) as printer_constructor:

                # 创建公共任务运行时。
                runtime = DdiTaskRuntime(project_root)

                # 执行模拟单商业任务。
                runtime.execute(request, [company_name])

            # 读取公共日志输出器构造时的关键字参数。
            constructor_kwargs = printer_constructor.call_args.kwargs

        # 断言公共运行时传递了关闭终端镜像参数。
        self.assertFalse(constructor_kwargs["console_output_enabled"])
