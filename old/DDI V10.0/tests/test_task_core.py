# -*- coding: utf-8 -*-
"""
DDI 无界面任务协调层单元测试。

本模块使用模拟商业执行函数验证筛选、快捷方案、启停持久化、事件发布、失败隔离和安全停止行为。
"""

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入商业筛选函数。
from ddi_framework.task_core import filter_company_names

# 导入平台首字母索引构建函数。
from ddi_framework.task_core import build_platform_initial_index

# 导入支持数据类型汇总函数。
from ddi_framework.task_core import list_supported_data_types

# 导入推荐线程数构建函数。
from ddi_framework.task_core import build_recommended_max_workers

# 导入 GUI 快捷方案读取函数。
from ddi_framework.task_core import load_gui_presets

# 导入 GUI 快捷方案保存函数。
from ddi_framework.task_core import save_gui_presets

# 导入任务取消控制器。
from ddi_framework.task_core import TaskCancellation

# 导入任务协调器。
from ddi_framework.task_core import TaskCoordinator

# 导入任务事件接收接口。
from ddi_framework.task_core import TaskEventSink

# 导入任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入 ANSI 控制序列清理函数。
from ddi_framework.task_core import strip_ansi_escape_codes

# 导入正式商业账号配置。
from ddi_framework.account_config import ACCOUNTS


# 定义测试事件接收器。
class TestEventSink(TaskEventSink):

    """
    收集测试期间发布的任务事件。

    :return: None。
    :rtype: None
    """

    # 定义测试事件接收器初始化方法。
    def __init__(self):

        """
        初始化事件收集列表。

        :return: None。
        :rtype: None
        """

        # 初始化任务事件列表。
        self.events = []

    # 定义任务事件收集方法。
    def publish(self, event):

        """
        收集测试任务事件。

        :param event: 任务事件对象。
        :type event: object
        :return: None。
        :rtype: None
        """

        # 追加当前任务事件。
        self.events.append(event)


# 定义无界面任务协调层测试类。
class TaskCoreTests(unittest.TestCase):

    """
    验证无界面任务协调层的核心行为。

    :return: None。
    :rtype: None
    """

    # 定义测试初始化方法。
    def setUp(self):

        """
        初始化测试账号配置、运行期配置和任务请求。

        :return: None。
        :rtype: None
        """

        # 初始化模拟商业账号配置。
        self.accounts = {"甲商业": {"负责人": "甲", "大区": "华东", "省份": "江苏", "平台": "alpha", "启用": True}, "乙商业": {"负责人": "乙", "大区": "华南", "省份": "广东", "平台": "beta", "启用": False}, "丙商业": {"负责人": "甲", "大区": "华东", "省份": "上海", "平台": "alpha", "启用": True}}

        # 初始化模拟运行期配置。
        self.runtime_config = {"商业启停": {"甲商业": True, "乙商业": False, "丙商业": True}}

        # 初始化无界面任务请求。
        self.request = TaskRequest("query_excel", "全部", "2026-06-01", "2026-06-30", "cookies", "downloads", "logs", 2)

    # 定义筛选测试方法。
    def test_filter_company_names_combines_conditions(self):

        """
        验证筛选条件按照交集过滤商业。

        :return: None。
        :rtype: None
        """

        # 按负责人和平台筛选商业。
        company_names = filter_company_names(self.accounts, owner_name="甲", platform_name="alpha")

        # 断言筛选结果保持原始配置顺序。
        self.assertEqual(company_names, ["甲商业", "丙商业"])

        # 按关键字筛选商业。
        company_names = filter_company_names(self.accounts, keyword="乙")

        # 断言关键字筛选结果正确。
        self.assertEqual(company_names, ["乙商业"])

    # 定义商业启停状态筛选测试方法。
    def test_filter_company_names_supports_runtime_enablement_status(self):

        """
        验证公共筛选接口可按运行期启停状态过滤商业。

        :return: None。
        :rtype: None
        """

        # 按运行期启用状态筛选商业。
        enabled_names = filter_company_names(self.accounts, runtime_enabled_map=self.runtime_config["商业启停"], status_filter="已启用")

        # 断言仅返回运行期已启用商业。
        self.assertEqual(enabled_names, ["甲商业", "丙商业"])

        # 按运行期停用状态筛选商业。
        disabled_names = filter_company_names(self.accounts, runtime_enabled_map=self.runtime_config["商业启停"], status_filter="已停用")

        # 断言仅返回运行期已停用商业。
        self.assertEqual(disabled_names, ["乙商业"])

    # 定义平台首字母索引测试方法。
    def test_platform_initial_index_groups_sorted_platform_names(self):

        """
        验证平台代码按首字母分组且保持字母顺序。

        :return: None。
        :rtype: None
        """

        # 构建模拟商业的平台首字母索引。
        platform_index = build_platform_initial_index(self.accounts)

        # 断言平台首字母索引的键按字母排序。
        self.assertEqual(list(platform_index.keys()), ["A", "B"])

        # 断言同首字母平台只保留一个排序后的代码。
        self.assertEqual(platform_index["A"], ["alpha"])

        # 断言另一首字母平台代码正确。
        self.assertEqual(platform_index["B"], ["beta"])

    # 定义数据类型展示层汇总测试方法。
    def test_supported_data_types_are_derived_from_account_configuration(self):

        """
        验证新增商业数据类型无需修改任一展示层选项列表。

        :return: None。
        :rtype: None
        """

        # 为模拟商业补充不同的数据类型声明。
        self.accounts["甲商业"]["数据类型列表"] = ["库存", "配送流向"]

        # 为另一模拟商业补充新增数据类型声明。
        self.accounts["乙商业"]["数据类型列表"] = ["总部库存"]

        # 从公共账号配置汇总展示层数据类型。
        data_types = list_supported_data_types(self.accounts)

        # 断言全部选项始终位于首位。
        self.assertEqual(data_types[0], "全部")

        # 断言新增数据类型会自动进入展示层列表。
        self.assertEqual(data_types[1:], ["库存", "总部库存", "配送流向"])

    # 定义 ANSI 清理测试方法。
    def test_strip_ansi_escape_codes_returns_plain_text(self):

        """
        验证 ANSI 颜色控制序列不会进入结构化 GUI 日志。

        :return: None。
        :rtype: None
        """

        # 清理包含颜色开始和结束序列的日志文本。
        plain_text = strip_ansi_escape_codes("\x1b[96m任务完成\x1b[0m")

        # 断言日志文本仅保留可展示内容。
        self.assertEqual(plain_text, "任务完成")

    # 定义推荐线程数测试方法。
    def test_recommended_max_workers_respects_hardware_limits(self):

        """
        验证推荐线程数同时受 CPU 和内存阈值限制。

        :return: None。
        :rtype: None
        """

        # 构建高规格运行环境概览。
        high_profile = {"logical_cpu_count": 16, "total_memory_bytes": 32 * 1024 ** 3}

        # 构建中等内存运行环境概览。
        medium_profile = {"logical_cpu_count": 12, "total_memory_bytes": 8 * 1024 ** 3}

        # 断言高规格环境线程数受全局十二线程上限限制。
        self.assertEqual(build_recommended_max_workers(high_profile, 3), 12)

        # 断言中等内存环境线程数受六线程内存阈值限制。
        self.assertEqual(build_recommended_max_workers(medium_profile, 3), 6)

    # 定义负责人标准化测试方法。
    def test_responsible_person_name_uses_yan_wei_xue(self):

        """
        验证账号维度中不再向界面暴露历史负责人名称。

        :return: None。
        :rtype: None
        """

        # 收集全部非空负责人名称。
        responsible_persons = {account.get("负责人", "") for account in ACCOUNTS.values() if account.get("负责人")}

        # 断言新负责人名称已写入运行期账号维度。
        self.assertIn("晏惟学", responsible_persons)

        # 断言历史负责人名称不会继续展示。
        self.assertNotIn("昊惟学", responsible_persons)

    # 定义快捷方案测试方法。
    def test_gui_presets_round_trip(self):

        """
        验证快捷方案可写入并从共享配置读取。

        :return: None。
        :rtype: None
        """

        # 创建临时项目目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 保存模拟快捷方案。
            save_gui_presets(project_root, {"华东": {"商业": ["甲商业", "丙商业"], "数据类型": "全部"}})

            # 读取保存后的快捷方案。
            preset_map = load_gui_presets(project_root)

            # 断言快捷方案内容保持一致。
            self.assertEqual(preset_map["华东"]["商业"], ["甲商业", "丙商业"])

    # 定义任务协调器构建方法。
    def build_coordinator(self, worker):

        """
        构建使用内存运行期配置的测试协调器。

        :param worker: 模拟单商业执行函数。
        :type worker: object
        :return: 测试协调器与事件接收器。
        :rtype: tuple[TaskCoordinator, TestEventSink]
        """

        # 初始化测试事件接收器。
        event_sink = TestEventSink()

        # 定义运行期配置读取函数。
        def load_config():

            """
            返回当前内存运行期配置。

            :return: 运行期配置。
            :rtype: dict
            """

            # 返回运行期配置。
            return self.runtime_config

        # 定义运行期配置保存函数。
        def save_config(runtime_config):

            """
            保存当前内存运行期配置。

            :param runtime_config: 运行期配置。
            :type runtime_config: dict
            :return: 配置路径占位值。
            :rtype: str
            """

            # 保存运行期配置。
            self.runtime_config = runtime_config

            # 返回配置路径占位值。
            return "memory://account_runtime.json"

        # 返回测试协调器和事件接收器。
        return TaskCoordinator(self.accounts, load_config, save_config, worker, event_sink), event_sink

    # 定义失败隔离和启停持久化测试方法。
    def test_coordinator_persists_enablement_and_isolates_failures(self):

        """
        验证勾选停用商业会持久启用且单商业失败不阻断其他商业。

        :return: None。
        :rtype: None
        """

        # 定义模拟单商业执行函数。
        def worker(company_name, account, request, cancellation):

            """
            返回模拟结果或抛出模拟异常。

            :param company_name: 商业名称。
            :type company_name: str
            :param account: 商业账号配置。
            :type account: dict
            :param request: 无界面任务请求。
            :type request: TaskRequest
            :param cancellation: 任务取消控制器。
            :type cancellation: TaskCancellation
            :return: 模拟执行结果。
            :rtype: dict
            """

            # 判断当前商业是否应模拟失败。
            if company_name == "乙商业":

                # 抛出模拟执行失败异常。
                raise RuntimeError("模拟失败")

            # 返回模拟执行结果。
            return {"商业名称": company_name}

        # 构建测试协调器和事件接收器。
        coordinator, event_sink = self.build_coordinator(worker)

        # 执行包含成功和失败商业的任务。
        result = coordinator.execute(self.request, ["甲商业", "乙商业"])

        # 断言成功商业数量正确。
        self.assertEqual(result.success_count, 1)

        # 断言失败商业数量正确。
        self.assertEqual(result.failure_count, 1)

        # 断言勾选停用商业已永久启用。
        self.assertTrue(self.runtime_config["商业启停"]["乙商业"])

        # 断言已发布任务完成事件。
        self.assertTrue(any(event.event_type == "task_finished" for event in event_sink.events))

        # 收集核心层发布的队列进度事件。
        progress_events = [event for event in event_sink.events if event.event_type == "task_progress"]

        # 断言任务执行期间持续发布队列进度事件。
        self.assertTrue(progress_events)

        # 读取最后一条队列进度事件。
        last_progress_event = progress_events[-1]

        # 断言标题行所需的队列统计字段完整。
        self.assertTrue({"完成", "总数", "成功", "失败", "运行中", "待提交", "耗时秒"}.issubset(last_progress_event.payload))

        # 收集商业生命周期事件类型。
        lifecycle_types = [event.event_type for event in event_sink.events if event.event_type in {"company_queued", "company_started", "company_finished"}]

        # 断言已发布等待、开始和完成事件。
        self.assertIn("company_queued", lifecycle_types)

        # 断言已发布实际开始事件。
        self.assertIn("company_started", lifecycle_types)

        # 断言已发布商业完成事件。
        self.assertIn("company_finished", lifecycle_types)

    # 定义安全停止测试方法。
    def test_coordinator_does_not_submit_pending_companies_after_stop(self):

        """
        验证预先请求停止时不提交任何待执行商业。

        :return: None。
        :rtype: None
        """

        # 初始化已执行商业名称列表。
        executed_names = []

        # 定义模拟单商业执行函数。
        def worker(company_name, account, request, cancellation):

            """
            记录被执行商业名称。

            :param company_name: 商业名称。
            :type company_name: str
            :param account: 商业账号配置。
            :type account: dict
            :param request: 无界面任务请求。
            :type request: TaskRequest
            :param cancellation: 任务取消控制器。
            :type cancellation: TaskCancellation
            :return: 模拟执行结果。
            :rtype: dict
            """

            # 记录当前被执行商业名称。
            executed_names.append(company_name)

            # 返回模拟执行结果。
            return {"商业名称": company_name}

        # 构建测试协调器和事件接收器。
        coordinator, _ = self.build_coordinator(worker)

        # 初始化任务取消控制器。
        cancellation = TaskCancellation()

        # 在任务提交前请求停止。
        cancellation.request_stop()

        # 执行已请求停止的任务。
        result = coordinator.execute(self.request, ["甲商业", "乙商业", "丙商业"], cancellation)

        # 断言没有商业被提交执行。
        self.assertEqual(executed_names, [])

        # 断言全部商业均标记为未启动即停止。
        self.assertEqual(result.stopped_count, 3)


# 判断当前文件是否以脚本方式运行。
if __name__ == "__main__":

    # 执行无界面任务协调层单元测试。
    unittest.main()
