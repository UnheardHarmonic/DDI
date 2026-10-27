# -*- coding: utf-8 -*-
"""
DDI Qt Quick 主线程流畅性测试。

本模块验证 GUI 事件分流、日志合并和展示层性能约束不依赖真实平台请求。
"""

# 导入内置打印函数模拟工具。
from unittest.mock import patch

# 导入日期时间构造工具。
from datetime import datetime, timedelta

# 导入单调时钟模块。
import time

# 导入线程同步模块。
import threading

# 导入轻量对象容器。
from types import SimpleNamespace

# 导入单元测试模块。
import unittest

# 导入 Qt 核心应用类型。
from PySide6.QtCore import QCoreApplication

# 导入公共账号配置。
from ddi_framework.account_config import ACCOUNTS

# 导入公共日志输出器。
from ddi_framework.print_handler import PrintHandler

# 导入公共任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入公共任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入 Qt GUI 事件接收器。
from ddi_gui_qt import DdiGuiViewModel, GuiLogListModel, QueueTaskEventSink


# 定义 GUI 主线程流畅性测试类。
class GuiResponsivenessTests(unittest.TestCase):

    """
    验证 Qt 展示适配器会限制低优先级日志工作量。

    :return: None。
    :rtype: None
    """

    # 定义 Qt 核心应用初始化方法。
    @classmethod
    def setUpClass(cls):

        """
        创建 ViewModel 定时器与信号所需的 Qt 应用实例。

        :param cls: 当前测试类。
        :type cls: type[GuiResponsivenessTests]
        :return: None。
        :rtype: None
        """

        # 复用已有 Qt 应用或创建核心应用。
        cls.qt_application = QCoreApplication.instance() or QCoreApplication([])

    # 定义可靠事件不会被日志合并测试方法。
    def test_reliable_events_are_prioritized_over_compactable_logs(self):

        """
        验证生命周期、阶段和错误事件始终优先于普通信息日志。

        :return: None。
        :rtype: None
        """

        # 创建 GUI 队列事件接收器。
        sink = QueueTaskEventSink()

        # 缩小普通信息日志缓冲容量以触发合并逻辑。
        sink.max_information_events = 2

        # 写入首条普通信息日志。
        sink.publish(TaskEvent("log", "普通日志一", "信息"))

        # 写入第二条普通信息日志。
        sink.publish(TaskEvent("log", "普通日志二", "信息"))

        # 写入第三条普通信息日志并触发最早日志合并。
        sink.publish(TaskEvent("log", "普通日志三", "信息"))

        # 写入不可合并的商业开始事件。
        sink.publish(TaskEvent("company_started", "商业开始执行", "运行中", "测试商业"))

        # 断言生命周期事件优先进入主线程。
        self.assertEqual(sink.get_nowait().event_type, "company_started")

        # 断言 GUI 会展示日志合并提示。
        self.assertEqual(sink.get_nowait().event_type, "gui_log_compacted")

        # 断言当前保留的首条日志正确。
        self.assertEqual(sink.get_nowait().message, "普通日志二")

    # 定义阶段事件可靠性测试方法。
    def test_section_event_with_information_status_is_reliable(self):

        """
        验证阶段事件不会因信息状态而进入可合并日志缓冲。

        :return: None。
        :rtype: None
        """

        # 创建 GUI 队列事件接收器。
        sink = QueueTaskEventSink()

        # 写入信息状态的阶段事件。
        sink.publish(TaskEvent("section", "查询阶段", "信息"))

        # 写入普通信息日志。
        sink.publish(TaskEvent("log", "接口请求中", "信息"))

        # 断言阶段事件仍优先被可靠队列消费。
        self.assertEqual(sink.get_nowait().event_type, "section")

    # 定义 GUI 输出镜像关闭测试方法。
    def test_print_handler_can_publish_events_without_console_output(self):

        """
        验证关闭终端镜像后仍可记录日志而不会写入标准输出。

        :return: None。
        :rtype: None
        """

        # 重置跨实例动态状态行标记。
        PrintHandler.live_status_visible = False

        # 创建用于接收结构化日志事件的 GUI 接收器。
        sink = QueueTaskEventSink()

        # 模拟标准打印函数。
        with patch("builtins.print") as print_mock:

            # 创建关闭终端镜像的公共日志输出器。
            printer = PrintHandler(event_sink=sink, console_output_enabled=False)

            # 输出普通日志。
            printer.info("GUI 仅展示日志")

            # 输出阶段分隔线。
            printer.section("模拟阶段")

            # 刷新缓冲日志。
            printer.buffered().flush()

        # 断言关闭镜像后没有调用标准打印函数。
        print_mock.assert_not_called()

        # 断言结构化阶段事件仍可被展示层接收。
        self.assertEqual(sink.get_nowait().event_type, "section")

    # 定义终端输出开关默认值测试方法。
    def test_task_request_keeps_terminal_output_enabled_by_default(self):

        """
        验证公共任务请求默认保持终端展示行为不变。

        :return: None。
        :rtype: None
        """

        # 构建未指定展示选项的公共任务请求。
        request = TaskRequest("login", "全部", "2026-06-01", "2026-06-30", "cookies", "downloads", "logs", 1)

        # 断言终端镜像输出默认保持开启。
        self.assertTrue(request.console_output_enabled)

    # 定义 Qt 性能约束源码测试方法。
    def test_qt_view_model_declares_time_budget_and_bounded_log_model(self):

        """
        验证 Qt ViewModel 声明事件预算、队列上限和日志容量边界。

        :return: None。
        :rtype: None
        """

        # 读取 Qt ViewModel 源码文本。
        with open("ddi_gui_qt.py", "r", encoding="utf-8") as source_file:

            # 保存 Qt ViewModel 完整源码文本。
            gui_source = source_file.read()

        # 断言 GUI 请求关闭标准输出镜像。
        self.assertIn("console_output_enabled=False", gui_source)

        # 断言事件轮询使用明确时间预算。
        self.assertIn("event_time_budget_seconds = 0.003", gui_source)

        # 断言可靠事件消费数量具有明确上限。
        self.assertIn("max_events_per_cycle = 24", gui_source)

        # 断言日志视图使用有界增量模型。
        self.assertIn("GuiLogListModel", gui_source)

        # 断言日志模型容量保持三千行上限。
        self.assertIn("maximum_rows=3000", gui_source)

        # 断言 GUI 使用原始高 DPI 缩放比例避免文字模糊。
        self.assertIn("HighDpiScaleFactorRoundingPolicy.PassThrough", gui_source)

        # 断言 Qt 应用名称使用产品名称。
        self.assertIn('application.setApplicationName("DDI 逆向神力")', gui_source)

    # 定义增量日志容量测试方法。
    def test_incremental_log_model_keeps_latest_rows(self):

        """
        验证增量日志模型只保留指定容量内的最新日志。

        :return: None。
        :rtype: None
        """

        # 创建容量为两行的增量日志模型。
        log_model = GuiLogListModel(maximum_rows=2)

        # 追加首批日志。
        log_model.append_rows([{"time": "10:00:00", "type": "log", "status": "信息", "company": "", "message": "一"}, {"time": "10:00:01", "type": "log", "status": "信息", "company": "", "message": "二"}])

        # 追加会触发容量淘汰的日志。
        log_model.append_rows([{"time": "10:00:02", "type": "log", "status": "信息", "company": "", "message": "三"}])

        # 断言日志模型保持容量上限。
        self.assertEqual(log_model.rowCount(), 2)

        # 断言最旧日志已被淘汰。
        self.assertEqual(log_model.data(log_model.index(0, 0), log_model.MessageRole), "二")

    # 定义批量刷新测试方法。
    def test_event_cycle_publishes_one_batched_refresh(self):

        """
        验证高频普通日志在单个定时器周期内只触发一次展示刷新。

        :return: None。
        :rtype: None
        """

        # 创建不执行初始化逻辑的 ViewModel 实例。
        view_model = DdiGuiViewModel.__new__(DdiGuiViewModel)

        # 创建待消费的 GUI 事件接收器。
        view_model.event_sink = QueueTaskEventSink()

        # 设置日志视图刷新节流参数。
        view_model.log_refresh_interval_seconds = 0.12

        # 设置最近一次日志视图刷新时间。
        view_model.last_log_refresh_at = 0.0

        # 设置待发布日志视图刷新标记。
        view_model.pending_log_refresh = False

        # 设置任务摘要视图刷新节流参数。
        view_model.task_refresh_interval_seconds = 0.08

        # 设置最近一次任务摘要视图刷新时间。
        view_model.last_task_refresh_at = 0.0

        # 设置待发布任务摘要视图刷新标记。
        view_model.pending_task_refresh = False

        # 设置甘特时间线视图刷新节流参数。
        view_model.timeline_refresh_interval_seconds = 0.12

        # 设置最近一次甘特时间线视图刷新时间。
        view_model.last_timeline_refresh_at = 0.0

        # 设置待发布甘特时间线视图刷新标记。
        view_model.pending_timeline_refresh = False

        # 设置任务网络视图刷新节流参数。
        view_model.network_refresh_interval_seconds = 0.12

        # 设置最近一次任务网络视图刷新时间。
        view_model.last_network_refresh_at = 0.0

        # 设置待发布任务网络视图刷新标记。
        view_model.pending_network_refresh = False

        # 写入足量的普通日志事件。
        for index in range(32):

            # 发布当前普通日志事件。
            view_model.event_sink.publish(TaskEvent("log", f"日志 {index}", "信息"))

        # 模拟单条事件处理函数。
        with patch.object(view_model, "handle_task_event", side_effect=lambda event, flags: {**flags, "logs": True}):

            # 模拟批量发布函数。
            with patch.object(view_model, "publish_event_refreshes") as publish_mock:

                # 消费当前定时器周期的事件。
                view_model.consume_events()

        # 断言本周期仅发布一次刷新。
        publish_mock.assert_called_once()

        # 断言日志模型被标记为需要刷新。
        self.assertTrue(publish_mock.call_args.args[0]["logs"])

    # 定义任务网络刷新节流测试方法。
    def test_network_refresh_is_throttled_between_event_cycles(self):

        """
        验证高频网络事件在节流窗口内不会重复重建 QML 网络模型。

        :return: None。
        :rtype: None
        """

        # 创建不执行初始化逻辑的 ViewModel 实例。
        view_model = DdiGuiViewModel.__new__(DdiGuiViewModel)

        # 创建待消费的 GUI 事件接收器。
        view_model.event_sink = QueueTaskEventSink()

        # 设置日志视图刷新节流参数。
        view_model.log_refresh_interval_seconds = 0.12

        # 设置最近一次日志视图刷新时间。
        view_model.last_log_refresh_at = 0.0

        # 设置待发布日志视图刷新标记。
        view_model.pending_log_refresh = False

        # 设置任务摘要视图刷新节流参数。
        view_model.task_refresh_interval_seconds = 0.08

        # 设置最近一次任务摘要视图刷新时间。
        view_model.last_task_refresh_at = 0.0

        # 设置待发布任务摘要视图刷新标记。
        view_model.pending_task_refresh = False

        # 设置甘特时间线视图刷新节流参数。
        view_model.timeline_refresh_interval_seconds = 0.12

        # 设置最近一次甘特时间线视图刷新时间。
        view_model.last_timeline_refresh_at = 0.0

        # 设置待发布甘特时间线视图刷新标记。
        view_model.pending_timeline_refresh = False

        # 设置任务网络视图刷新节流参数。
        view_model.network_refresh_interval_seconds = 0.12

        # 设置最近一次网络刷新时间为当前时刻。
        view_model.last_network_refresh_at = time.perf_counter()

        # 设置待发布网络刷新标记。
        view_model.pending_network_refresh = False

        # 写入触发网络变化的任务事件。
        view_model.event_sink.publish(TaskEvent("company_started", "商业开始执行", "运行中", "测试商业"))

        # 模拟当前事件会更新网络状态。
        with patch.object(view_model, "handle_task_event", side_effect=lambda event, flags: {**flags, "network": True}):

            # 模拟批量发布函数。
            with patch.object(view_model, "publish_event_refreshes") as publish_mock:

                # 消费仍处于网络节流窗口内的事件。
                view_model.consume_events()

                # 断言网络更新未在窗口内发布。
                publish_mock.assert_not_called()

                # 将最近网络刷新时间重置到节流窗口前。
                view_model.last_network_refresh_at = 0.0

                # 消费空周期以发布聚合后的网络刷新。
                view_model.consume_events()

        # 断言网络模型只发布一次聚合刷新。
        publish_mock.assert_called_once()

        # 断言本次刷新包含网络模型。
        self.assertTrue(publish_mock.call_args.args[0]["network"])

    # 定义网络节点入场时间稳定性测试方法。
    def test_network_nodes_keep_first_entry_time_between_state_refreshes(self):

        """
        验证网络模型刷新不会让既有节点重复播放入场动效。

        :return: None。
        :rtype: None
        """

        # 创建最小网络重建状态对象。
        network_state = SimpleNamespace(task_topology={"测试商业": ["购进流向", "配送流向"]}, company_states={"测试商业": {"status": "运行中", "stage": "协议执行", "platform": "测试平台", "recordCount": "12", "updatedAt": 1.0}}, worker_slots={1: {"status": "运行中", "company": "测试商业"}}, network_history_limit=10, network_focus_company="", network_focus_group="", task_state={"running": True}, network_node_entered_at_ms={}, networkChanged=SimpleNamespace(emit=lambda: None))

        # 首次构建任务网络模型。
        DdiGuiViewModel.rebuild_network(network_state)

        # 保存首轮网络节点入场时间。
        first_entry_times = {node["id"]: node["enteredAt"] for node in network_state.network_nodes}

        # 更新商业阶段以模拟运行期状态刷新。
        network_state.company_states["测试商业"].update({"stage": "数据写入", "recordCount": "36", "updatedAt": 2.0})

        # 再次构建任务网络模型。
        DdiGuiViewModel.rebuild_network(network_state)

        # 保存第二轮网络节点入场时间。
        second_entry_times = {node["id"]: node["enteredAt"] for node in network_state.network_nodes}

        # 断言既有根节点保留首轮入场时间。
        self.assertEqual(second_entry_times["root"], first_entry_times["root"])

        # 断言既有商业节点保留首轮入场时间。
        self.assertEqual(second_entry_times["company:测试商业"], first_entry_times["company:测试商业"])

    # 定义数据类型节点连续布局序号测试方法。
    def test_network_task_nodes_use_unique_layout_orders(self):

        """
        验证不同商业的数据类型节点不会复用同一布局序号。

        :return: None。
        :rtype: None
        """

        # 构造多商业多数据类型的最小网络状态对象。
        network_state = SimpleNamespace(task_topology={"商业一": ["购进", "配送", "库存"], "商业二": ["购进", "配送", "库存"], "商业三": ["购进", "配送", "库存"]}, company_states={"商业一": {"status": "运行中", "stage": "协议执行", "platform": "测试平台", "recordCount": "0", "updatedAt": 1.0}, "商业二": {"status": "运行中", "stage": "协议执行", "platform": "测试平台", "recordCount": "0", "updatedAt": 1.0}, "商业三": {"status": "运行中", "stage": "协议执行", "platform": "测试平台", "recordCount": "0", "updatedAt": 1.0}}, worker_slots={1: {"status": "运行中", "company": "商业一"}, 2: {"status": "运行中", "company": "商业二"}, 3: {"status": "运行中", "company": "商业三"}}, network_history_limit=10, network_focus_company="", network_focus_group="", task_state={"running": True}, network_node_entered_at_ms={}, networkChanged=SimpleNamespace(emit=lambda: None))

        # 重建多商业任务网络模型。
        DdiGuiViewModel.rebuild_network(network_state)

        # 提取全部数据类型节点布局序号。
        task_orders = [node["order"] for node in network_state.network_nodes if node["kind"] == "task"]

        # 断言全部数据类型节点的布局序号唯一。
        self.assertEqual(len(task_orders), len(set(task_orders)))

    # 定义真实时间轴比例计算测试方法。
    def test_timeline_geometry_uses_shared_real_time_range(self):

        """
        验证不同阶段依据真实起止时间获得不同的甘特横轴位置和宽度。

        :return: None。
        :rtype: None
        """

        # 创建仅承载时间线数据的 ViewModel 实例。
        view_model = DdiGuiViewModel.__new__(DdiGuiViewModel)

        # 写入两条具有不同起止时间的阶段记录。
        view_model.timeline_rows = [{"startEpoch": 1_000.0, "endEpoch": 3_000.0}, {"startEpoch": 2_000.0, "endEpoch": 9_000.0}, {"startEpoch": 0.0, "endEpoch": 0.0}]

        # 依据真实时间刷新共享时间轴几何。
        DdiGuiViewModel.refresh_timeline_geometry(view_model)

        # 读取用于绘制的阶段记录。
        first_row, second_row, waiting_row = view_model.timeline_rows

        # 断言共享时间轴覆盖两个阶段的真实范围。
        self.assertLess(view_model.timeline_range["startEpoch"], first_row["startEpoch"])

        # 断言共享时间轴在末尾保留显示留白。
        self.assertGreater(view_model.timeline_range["endEpoch"], second_row["endEpoch"])

        # 断言较晚开始的阶段位于较右位置。
        self.assertGreater(second_row["timelineOffset"], first_row["timelineOffset"])

        # 断言较长阶段拥有更宽的条带比例。
        self.assertGreater(second_row["timelineSpan"], first_row["timelineSpan"])

        # 断言未开始阶段不参与条带绘制。
        self.assertEqual(waiting_row["timelineOffset"], -1.0)

    # 定义商业主甘特图生命周期聚合测试方法。
    def test_timeline_aggregates_lifecycle_events_by_company(self):

        """
        验证甘特图按商业生命周期绘制一条主时间线，阶段事件只更新附属信息。

        :return: None。
        :rtype: None
        """

        # 创建完整 ViewModel 以复用真实事件同步路径。
        view_model = DdiGuiViewModel(".")

        # 停止自动事件定时器以便由测试逐条驱动事件。
        view_model.event_timer.stop()

        # 读取两个已配置商业名称。
        company_names = list(ACCOUNTS)[:2]

        # 构造带微秒的商业开始时间。
        started_at = datetime(2026, 7, 28, 9, 0, 0, 125_000)

        # 构造商业完成时间。
        finished_at = started_at + timedelta(seconds=18)

        # 初始化两家商业的主甘特图记录。
        view_model.initialize_timeline_rows(company_names, "全部")

        # 同步首家商业开始执行事件。
        refresh_flags = view_model.handle_task_event(TaskEvent("company_started", "商业任务开始执行", "运行中", company_names[0], "全部", {}, started_at))

        # 同步首家商业的中间阶段事件。
        refresh_flags = view_model.handle_task_event(TaskEvent("task_timeline", "查询完成", "信息", company_names[0], "配送流向", {"阶段开始时间": started_at, "阶段结束时间": started_at + timedelta(seconds=8), "执行阶段": "查询完成", "执行状态": "成功", "记录数量": "42"}, started_at + timedelta(seconds=8)), refresh_flags)

        # 同步首家商业完成事件。
        view_model.handle_task_event(TaskEvent("company_finished", "商业任务执行完成", "成功", company_names[0], "全部", {}, finished_at), refresh_flags)

        # 按商业完成时刻刷新甘特图几何。
        view_model.refresh_timeline_geometry(finished_at.timestamp() * 1000)

        # 读取已经完成的商业主时间线记录。
        completed_row = view_model.timeline_rows[0]

        # 读取尚未开始的商业主时间线记录。
        waiting_row = view_model.timeline_rows[1]

        # 断言阶段事件未新增第二条同商业甘特行。
        self.assertEqual(len(view_model.timeline_rows), 2)

        # 断言商业完成行保留真实起止时间。
        self.assertEqual(completed_row["endEpoch"], finished_at.timestamp() * 1000)

        # 断言带微秒的阶段开始时间已正确解析并保留为条带起点。
        self.assertEqual(completed_row["startEpoch"], started_at.timestamp() * 1000)

        # 断言阶段事件更新商业最新记录数量。
        self.assertEqual(completed_row["recordCount"], "42")

        # 断言已完成商业不再随当前时间延展。
        self.assertFalse(completed_row["active"])

        # 断言未开始商业仍保留等待状态而不绘制条带。
        self.assertEqual(waiting_row["timelineOffset"], -1.0)

    # 定义任务启动非阻塞测试方法。
    def test_start_task_returns_before_background_runtime_finishes(self):

        """
        验证任务运行时留在后台线程，任务启动槽位不会阻塞 Qt 主线程。

        :return: None。
        :rtype: None
        """

        # 创建完整 ViewModel 以验证真实启动路径。
        view_model = DdiGuiViewModel(".")

        # 读取一个公共配置中的有效商业名称。
        company_name = next(iter(ACCOUNTS))

        # 设置当前选中商业。
        view_model.selected_names = {company_name}

        # 创建后台运行时阻塞释放信号。
        runtime_release = threading.Event()

        # 记录启动槽位调用前的单调时间。
        started_at = time.perf_counter()

        # 模拟持续运行的公共任务，避免访问真实平台。
        with patch("ddi_gui_qt.DdiTaskRuntime.execute", side_effect=lambda *arguments: runtime_release.wait(1.0)):

            # 调用 GUI 任务启动槽位。
            view_model.startTask({"action": "login", "dataType": "全部", "startDate": "2026-07-01", "endDate": "2026-07-01", "maxWorkers": 1, "copyExcel": False})

            # 计算启动槽位的同步耗时。
            elapsed_seconds = time.perf_counter() - started_at

            # 断言后台运行线程已经建立。
            self.assertIsNotNone(view_model.run_thread)

            # 断言公共运行时仍在后台等待。
            self.assertTrue(view_model.run_thread.is_alive())

            # 断言启动槽位没有等待后台任务完成。
            self.assertLess(elapsed_seconds, 0.3)

            # 释放模拟公共运行时。
            runtime_release.set()

            # 等待后台任务线程收尾。
            view_model.run_thread.join(timeout=1.0)

        # 断言后台任务线程已结束。
        self.assertFalse(view_model.run_thread.is_alive())

    # 定义高频日志消费时间预算测试方法。
    def test_high_frequency_events_keep_each_main_thread_cycle_bounded(self):

        """
        验证高频后台日志不会让单次主线程事件消费长时间占用界面循环。

        :return: None。
        :rtype: None
        """

        # 创建完整 ViewModel 以执行真实事件消费路径。
        view_model = DdiGuiViewModel(".")

        # 停止自动定时器以便由测试逐轮驱动消费。
        view_model.event_timer.stop()

        # 放宽测试队列的信息日志容量以保留高频事件样本。
        view_model.event_sink.max_information_events = 1024

        # 写入高频普通日志事件。
        for index in range(256):

            # 发布当前日志事件。
            view_model.event_sink.publish(TaskEvent("log", f"高频日志 {index}", "信息"))

        # 初始化每轮主线程消费耗时集合。
        cycle_durations = []

        # 连续消费多个主线程周期。
        for _ in range(6):

            # 记录当前周期开始时间。
            cycle_started_at = time.perf_counter()

            # 消费本轮后台事件。
            view_model.consume_events()

            # 保存当前周期耗时。
            cycle_durations.append(time.perf_counter() - cycle_started_at)

        # 断言每轮消费均显著低于可感知卡顿阈值。
        self.assertLess(max(cycle_durations), 0.05)

    # 定义十并发生产者响应性测试方法。
    def test_ten_event_producers_keep_main_thread_cycles_bounded(self):

        """
        验证十个后台任务并发发布日志时主线程仍保持短时间预算。

        :return: None。
        :rtype: None
        """

        # 创建完整 ViewModel 以执行真实事件消费路径。
        view_model = DdiGuiViewModel(".")

        # 停止自动定时器以便由测试逐轮驱动消费。
        view_model.event_timer.stop()

        # 放宽信息日志容量以保留十并发生产者样本。
        view_model.event_sink.max_information_events = 2048

        # 定义后台任务日志生产函数。
        def produce_events(worker_index):

            """
            向线程安全事件接收器写入单个并发槽位的日志样本。

            :param worker_index: 当前模拟并发槽位编号。
            :type worker_index: int
            :return: None。
            :rtype: None
            """

            # 连续发布当前并发槽位的高频日志。
            for event_index in range(120):

                # 写入当前结构化日志事件。
                view_model.event_sink.publish(TaskEvent("log", f"槽位 {worker_index} 日志 {event_index}", "信息", f"模拟商业 {worker_index}"))

        # 创建十个模拟后台任务生产线程。
        producers = [threading.Thread(target=produce_events, args=(worker_index,)) for worker_index in range(10)]

        # 启动全部模拟后台任务生产线程。
        for producer in producers:

            # 启动当前后台日志生产线程。
            producer.start()

        # 等待全部后台日志生产线程结束。
        for producer in producers:

            # 等待当前后台日志生产线程结束。
            producer.join(timeout=1.0)

        # 初始化十并发场景的主线程周期耗时集合。
        cycle_durations = []

        # 消费足量主线程周期以覆盖十并发积压事件。
        for _ in range(24):

            # 记录当前周期开始时间。
            cycle_started_at = time.perf_counter()

            # 消费本轮后台事件。
            view_model.consume_events()

            # 保存当前周期耗时。
            cycle_durations.append(time.perf_counter() - cycle_started_at)

        # 断言十并发场景下每轮消费仍低于可感知卡顿阈值。
        self.assertLess(max(cycle_durations), 0.05)
