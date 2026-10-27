# -*- coding: utf-8 -*-
"""
DDI PySide6 与 QML 展示桥接层。

本模块向 QML 提供商业筛选、运行期账号编辑、任务事件和可视化状态。
公共协议执行只通过 DdiTaskRuntime 调用，展示层不实现任何平台业务协议。
"""

# 导入双端队列工具。
from collections import deque

# 导入系统路径工具。
import os

# 导入平台运行环境信息工具。
import platform

# 导入线程安全队列工具。
import queue

# 导入系统运行信息工具。
import sys

# 导入后台线程工具。
import threading

# 导入单调时间工具。
import time

# 导入日期时间工具。
from datetime import datetime

# 导入 Qt 核心对象与模型工具。
from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, QTimer, QUrl, Signal, Slot, Qt

# 导入 Qt 桌面服务工具。
from PySide6.QtGui import QGuiApplication, QDesktopServices

# 导入 Qt QML 应用引擎。
from PySide6.QtQml import QQmlApplicationEngine

# 导入 Qt Quick Controls 样式控制器。
from PySide6.QtQuickControls2 import QQuickStyle

# 导入硬件信息采集函数。
from ddi_framework.hardware_profile import read_hardware_profile

# 导入商业账号配置。
from ddi_framework.account_config import ACCOUNTS

# 导入账号覆盖清除函数。
from ddi_framework.account_config import clear_runtime_account_override

# 导入有效账号读取函数。
from ddi_framework.account_config import get_effective_account

# 导入账号可编辑字段读取函数。
from ddi_framework.account_config import get_runtime_editable_account_fields

# 导入维度取值函数。
from ddi_framework.account_config import list_account_dimension_values

# 导入运行期账号配置函数。
from ddi_framework.account_config import load_runtime_account_config

# 导入运行期账号覆盖保存函数。
from ddi_framework.account_config import save_runtime_account_override

# 导入运行期启用状态解析函数。
from ddi_framework.account_config import resolve_runtime_enabled

# 导入运行期账号配置保存函数。
from ddi_framework.account_config import save_runtime_account_config

# 导入公共商业筛选函数。
from ddi_framework.task_core import filter_company_names

# 导入 GUI 快捷方案读取函数。
from ddi_framework.task_core import load_gui_presets

# 导入 GUI 快捷方案保存函数。
from ddi_framework.task_core import save_gui_presets

# 导入任务取消控制器。
from ddi_framework.task_core import TaskCancellation

# 导入任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入统一日期范围对象。
from ddi_framework.task_core import DateRangeSpec

# 导入事件接收协议。
from ddi_framework.task_core import TaskEventSink

# 导入数据类型大类汇总函数。
from ddi_framework.task_core import list_data_type_categories

# 导入数据类型大类归一化函数。
from ddi_framework.task_core import normalize_data_type_category

# 导入全局任务配置读取函数。
from ddi_framework.task_config import get_task_config

# 导入当前版本启动更新日志读取函数。
from ddi_framework.startup_changelog import get_current_startup_changelog
from ddi_framework.directory_docs import ensure_directory_documents

# 导入公共无界面任务运行时。
from ddi_framework.task_runtime import DdiTaskRuntime

# 导入 Windows 原生玻璃窗口适配函数。
from gui_windows_effects import enable_native_glass


# 定义阶段时间文本转换函数。
def parse_timeline_epoch(timestamp_text):

    """
    将公共任务日志时间转换为前端甘特图使用的毫秒时间戳。

    :param timestamp_text: 公共任务日志中的阶段时间文本。
    :type timestamp_text: str | object
    :return: 自 Unix 纪元开始的毫秒数，无法解析时返回零。
    :rtype: float
    """

    # 判断阶段时间已经是日期时间对象。
    if isinstance(timestamp_text, datetime):

        # 返回日期时间对象对应的毫秒时间戳。
        return timestamp_text.timestamp() * 1000

    # 标准化阶段时间文本。
    normalized_text = str(timestamp_text or "").strip()

    # 判断阶段时间文本为空。
    if not normalized_text:

        # 返回空时间对应的零值。
        return 0.0

    # 定义公共日志兼容的时间文本格式。
    timestamp_formats = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S")

    # 遍历全部兼容时间格式。
    for timestamp_format in timestamp_formats:

        # 尝试按当前格式解析阶段时间。
        try:

            # 返回转换后的毫秒时间戳。
            return datetime.strptime(normalized_text, timestamp_format).timestamp() * 1000

        # 处理当前格式不匹配的时间文本。
        except ValueError:

            # 尝试下一种兼容时间格式。
            continue

    # 尝试按 ISO 日期时间格式解析阶段时间。
    try:

        # 返回转换后的毫秒时间戳。
        return datetime.fromisoformat(normalized_text).timestamp() * 1000

    # 处理不符合公共任务日志格式的时间文本。
    except ValueError:

        # 返回无法解析时间对应的零值。
        return 0.0


# 定义 Qt 增量日志模型。
class GuiLogListModel(QAbstractListModel):

    """
    向 QML 提供有界且可批量追加的结构化日志模型。

    :return: None。
    :rtype: None
    """

    # 定义日志字段对应的 QML 角色编号。
    TimeRole = Qt.UserRole + 1

    # 定义日志类型对应的 QML 角色编号。
    TypeRole = Qt.UserRole + 2

    # 定义日志状态对应的 QML 角色编号。
    StatusRole = Qt.UserRole + 3

    # 定义商业名称对应的 QML 角色编号。
    CompanyRole = Qt.UserRole + 4

    # 定义日志消息对应的 QML 角色编号。
    MessageRole = Qt.UserRole + 5

    # 定义初始化方法。
    def __init__(self, maximum_rows=3000, parent=None):

        """
        初始化有界日志存储与 QML 角色映射。

        :param maximum_rows: 可保留的最大日志行数。
        :type maximum_rows: int
        :param parent: Qt 父对象。
        :type parent: QObject | None
        :return: None。
        :rtype: None
        """

        # 调用 Qt 列表模型初始化逻辑。
        super().__init__(parent)

        # 保存日志行容量上限。
        self.maximum_rows = max(1, int(maximum_rows))

        # 初始化结构化日志行集合。
        self.rows = []

    # 定义行数读取方法。
    def rowCount(self, parent=QModelIndex()):

        """
        返回当前日志模型中的可见行数。

        :param parent: 父模型索引。
        :type parent: QModelIndex
        :return: 当前日志行数。
        :rtype: int
        """

        # 判断当前读取的是顶层模型。
        if not parent.isValid():

            # 返回顶层日志行数。
            return len(self.rows)

        # 返回子项不存在时的行数。
        return 0

    # 定义角色数据读取方法。
    def data(self, index, role=Qt.DisplayRole):

        """
        返回指定日志行的 QML 角色数据。

        :param index: 日志模型索引。
        :type index: QModelIndex
        :param role: QML 请求的角色编号。
        :type role: int
        :return: 指定字段值。
        :rtype: object
        """

        # 判断索引无效或超出当前日志范围。
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.rows):

            # 返回空数据。
            return None

        # 读取当前日志行。
        row = self.rows[index.row()]

        # 定义角色与字段名称映射。
        role_names = {self.TimeRole: "time", self.TypeRole: "type", self.StatusRole: "status", self.CompanyRole: "company", self.MessageRole: "message"}

        # 返回当前角色对应的日志字段。
        return row.get(role_names.get(role, ""))

    # 定义 QML 角色名称方法。
    def roleNames(self):

        """
        返回 QML 可读取的日志字段名称。

        :return: 角色编号到字段名称的映射。
        :rtype: dict
        """

        # 返回 UTF-8 编码的 QML 角色映射。
        return {self.TimeRole: b"time", self.TypeRole: b"type", self.StatusRole: b"status", self.CompanyRole: b"company", self.MessageRole: b"message"}

    # 定义批量日志追加方法。
    def append_rows(self, rows):

        """
        批量追加日志并在容量超限时删除最旧行。

        :param rows: 待追加的结构化日志行。
        :type rows: list[dict]
        :return: None。
        :rtype: None
        """

        # 判断当前没有待追加日志。
        if not rows:

            # 结束空追加操作。
            return

        # 保留单批日志中符合容量的最新记录。
        rows = list(rows)[-self.maximum_rows:]

        # 计算追加前需要移除的最旧行数量。
        overflow_count = max(0, len(self.rows) + len(rows) - self.maximum_rows)

        # 判断需要移除最旧日志。
        if overflow_count:

            # 通知 QML 即将删除最旧日志范围。
            self.beginRemoveRows(QModelIndex(), 0, overflow_count - 1)

            # 删除超出容量的最旧日志。
            del self.rows[:overflow_count]

            # 通知 QML 最旧日志删除完成。
            self.endRemoveRows()

        # 读取当前追加起始行号。
        start_row = len(self.rows)

        # 通知 QML 即将追加日志范围。
        self.beginInsertRows(QModelIndex(), start_row, start_row + len(rows) - 1)

        # 追加当前批日志。
        self.rows.extend(rows)

        # 通知 QML 当前批日志追加完成。
        self.endInsertRows()

    # 定义日志清空方法。
    def clear(self):

        """
        清空当前任务的全部可见日志。

        :return: None。
        :rtype: None
        """

        # 通知 QML 即将重置整个日志模型。
        self.beginResetModel()

        # 清空日志行集合。
        self.rows.clear()

        # 通知 QML 日志模型重置完成。
        self.endResetModel()


# 定义 Qt GUI 事件接收器。
class QueueTaskEventSink(TaskEventSink):

    """
    将后台公共任务事件安全投递到 Qt 主线程。

    普通信息日志使用有界缓冲，生命周期与错误事件可靠排队，阶段和队列进度保留最新状态。
    """

    # 定义初始化方法。
    def __init__(self):

        """
        初始化可靠事件队列与可合并日志缓冲。

        :return: None。
        :rtype: None
        """

        # 创建可靠生命周期事件队列。
        self.reliable_events = queue.Queue()

        # 创建普通信息事件缓冲。
        self.information_events = deque()

        # 创建普通信息事件锁。
        self.information_lock = threading.RLock()

        # 创建阶段与队列进度事件的合并通知队列。
        self.coalesced_events = queue.Queue()

        # 创建按业务键保存的最新阶段事件集合。
        self.pending_coalesced_events = {}

        # 创建合并事件集合锁。
        self.coalesced_lock = threading.RLock()

        # 设置普通信息事件最大容量。
        self.max_information_events = 1000

        # 初始化被合并日志数量。
        self.compacted_count = 0

    # 定义中等优先级事件合并键构建方法。
    def _coalesced_event_key(self, event):

        """
        为阶段和队列进度事件构建稳定的合并键。

        :param event: 待合并的任务事件。
        :type event: TaskEvent
        :return: 事件合并键，不需要合并时返回空值。
        :rtype: tuple[str, str, str] | None
        """

        # 判断当前事件属于阶段状态更新。
        if event.event_type == "task_timeline":

            # 按商业与数据类型保留每条拓扑分支的最新阶段。
            return ("task_timeline", str(event.company_name or ""), str(event.data_type or ""))

        # 判断当前事件属于队列进度更新。
        if event.event_type == "task_progress":

            # 全局队列进度只保留最新一条。
            return ("task_progress", "", "")

        # 返回普通可靠事件对应的空键。
        return None

    # 定义中等优先级事件读取方法。
    def _take_coalesced_event(self):

        """
        读取并删除一条已经合并的最新状态事件。

        :return: 当前合并事件。
        :rtype: TaskEvent
        :raises queue.Empty: 没有可读取的合并事件。
        """

        # 尝试读取一个待取出的业务合并键。
        key = self.coalesced_events.get_nowait()

        # 读取并删除该业务键对应的最新事件。
        with self.coalesced_lock:

            # 移除已经交给主线程消费的合并事件。
            event = self.pending_coalesced_events.pop(key, None)

        # 处理并发更新造成的空键通知。
        if event is None:

            # 将空通知视为当前没有可消费事件。
            raise queue.Empty()

        # 返回该业务键的最新事件。
        return event

    # 定义终止事件对应的合并状态清理方法。
    def _discard_terminal_coalesced_events(self, event):

        """
        清理终止生命周期之后不再需要的阶段状态事件。

        :param event: 当前终止生命周期事件。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        # 判断当前事件是否会结束单个商业或整批任务。
        if event.event_type not in {"company_finished", "company_stopped", "task_finished", "task_runtime_error"}:

            # 保留仍在运行中的阶段状态。
            return

        # 标准化当前事件关联的商业名称。
        company_name = str(event.company_name or "")

        # 删除当前终止范围内尚未消费的阶段状态。
        with self.coalesced_lock:

            # 构建需要删除的阶段或队列进度键集合。
            stale_keys = [key for key in self.pending_coalesced_events if (not company_name or (key[0] == "task_timeline" and key[1] == company_name))]

            # 清理已经失效的合并状态。
            for key in stale_keys:

                # 删除合并状态；队列中的键通知会在读取时被忽略。
                self.pending_coalesced_events.pop(key, None)

    # 定义可合并普通日志判断方法。
    def is_compactable_information_event(self, event):

        """
        判断事件是否可作为普通低优先级日志缓冲。

        :param event: 公共任务事件。
        :type event: TaskEvent
        :return: 是否可合并。
        :rtype: bool
        """

        # 返回普通信息日志和进度事件判断结果。
        return event.event_type in {"log", "progress"} and event.status == "信息"

    # 定义事件发布方法。
    def publish(self, event):

        """
        按事件可靠性将公共事件写入对应队列。

        :param event: 公共任务事件。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        # 清理终止生命周期对应的过期阶段状态。
        self._discard_terminal_coalesced_events(event)

        # 构建阶段或队列进度事件的合并键。
        coalesced_key = self._coalesced_event_key(event)

        # 判断当前事件属于可合并的中等优先级状态。
        if coalesced_key is not None:

            # 使用单键最新值减少并发事件洪峰。
            with self.coalesced_lock:

                # 仅在业务键首次进入队列时追加通知键。
                if coalesced_key not in self.pending_coalesced_events:

                    # 将业务键写入待消费队列。
                    self.coalesced_events.put(coalesced_key)

                # 保存该业务键最新状态事件。
                self.pending_coalesced_events[coalesced_key] = event

            # 结束中等优先级事件投递。
            return

        # 判断当前事件为可合并普通日志。
        if self.is_compactable_information_event(event):

            # 获取普通日志缓冲锁。
            with self.information_lock:

                # 判断缓冲容量已经达到上限。
                if len(self.information_events) >= self.max_information_events:

                    # 丢弃最旧普通日志。
                    self.information_events.popleft()

                    # 累加已合并日志数量。
                    self.compacted_count += 1

                # 保存当前普通日志。
                self.information_events.append(event)

            # 结束普通日志投递。
            return

        # 将可靠事件直接写入优先队列。
        self.reliable_events.put(event)

    # 定义非阻塞事件读取方法。
    def get_nowait(self):

        """
        优先读取可靠事件，再读取阶段或队列进度的最新状态，最后读取普通日志。

        :return: 当前可消费任务事件。
        :rtype: TaskEvent
        :raises queue.Empty: 当前没有可消费事件时抛出。
        """

        # 尝试读取可靠事件。
        try:

            # 返回可靠生命周期事件。
            return self.reliable_events.get_nowait()

        # 处理可靠队列为空情况。
        except queue.Empty:

            # 保持继续读取普通事件。
            pass

        # 尝试读取阶段或队列进度的最新合并事件。
        try:

            # 返回中等优先级状态事件。
            return self._take_coalesced_event()

        # 处理当前没有待消费合并事件。
        except queue.Empty:

            # 保持继续读取普通信息日志。
            pass

        # 获取普通日志缓冲锁。
        with self.information_lock:

            # 判断存在待展示合并通知。
            if self.compacted_count:

                # 保存当前已合并日志数量。
                compacted_count = self.compacted_count

                # 清空合并日志计数。
                self.compacted_count = 0

                # 返回日志合并提示事件。
                return TaskEvent("gui_log_compacted", f"为保持界面流畅，已合并 {compacted_count} 条普通日志", "警告")

            # 判断普通日志缓冲不为空。
            if self.information_events:

                # 返回最早普通日志。
                return self.information_events.popleft()

        # 抛出队列为空异常。
        raise queue.Empty()


# 定义 Qt QML 展示 ViewModel。
class DdiGuiViewModel(QObject):

    """
    管理 QML 所需的展示状态并调用无界面任务运行时。

    :param project_root: 项目根目录。
    :type project_root: str
    """

    # 定义商业列表变化信号。
    companiesChanged = Signal()

    # 定义筛选选项变化信号。
    filterOptionsChanged = Signal()

    # 定义日志变化信号。
    logsChanged = Signal()

    # 定义任务进度变化信号。
    taskChanged = Signal()

    # 定义网络状态变化信号。
    networkChanged = Signal()

    # 定义甘特记录变化信号。
    timelineChanged = Signal()

    # 定义账号抽屉数据变化信号。
    accountChanged = Signal()

    # 定义快捷方案变化信号。
    presetsChanged = Signal()

    # 定义界面提示变化信号。
    noticeChanged = Signal()

    # 定义减少动画偏好变化信号。
    reducedMotionChanged = Signal()

    # 定义设备详情变化信号。
    deviceDetailsChanged = Signal()

    # 定义设备采集状态变化信号。
    deviceLoadingChanged = Signal()

    # 定义后台硬件数据回送信号。
    hardwareProfileReady = Signal(object)

    # 定义初始化方法。
    def __init__(self, project_root):

        """
        初始化 GUI 展示状态、事件定时器和共享配置。

        :param project_root: 项目根目录。
        :type project_root: str
        :return: None。
        :rtype: None
        """

        # 调用 QObject 初始化方法。
        super().__init__()

        # 保存项目根目录绝对路径。
        self.project_root = os.path.abspath(project_root)

        # 创建公共任务事件接收器。
        self.event_sink = QueueTaskEventSink()

        # 初始化后台任务线程引用。
        self.run_thread = None

        # 初始化任务取消控制器。
        self.cancellation = None

        # 初始化商业选择集合。
        self.selected_names = set()

        # 初始化商业筛选条件。
        self.filters = {"keyword": "", "owner": "", "region": "", "province": "", "platform": "", "status": ""}

        # 初始化商业列表模型。
        self.company_rows = []

        # 初始化 QML 增量日志模型。
        self.log_model = GuiLogListModel(parent=self)

        # 初始化待批量写入日志行集合。
        self.pending_log_rows = []

        # 初始化任务网络节点模型。
        self.network_nodes = []

        # 初始化任务网络边模型。
        self.network_edges = []

        # 初始化任务网络节点首次入场时间索引。
        self.network_node_entered_at_ms = {}

        # 初始化商业任务状态模型。
        self.company_states = {}

        # 初始化商业数据类型拓扑。
        self.task_topology = {}

        # 初始化并发槽位状态。
        self.worker_slots = {}

        # 设置任务网络最多保留的历史商业节点数量。
        self.network_history_limit = 10

        # 初始化任务网络聚焦商业名称。
        self.network_focus_company = ""

        # 初始化任务网络聚合节点展开状态。
        self.network_focus_group = ""

        # 初始化按商业聚合的主甘特图模型。
        self.timeline_rows = []

        # 初始化阶段事件数量。
        self.timeline_stage_count = 0

        # 初始化阶段时间线显示范围。
        self.timeline_range = {"startEpoch": 0.0, "endEpoch": 0.0}

        # 初始化设备详情展示行。
        self.device_details = [{"label": "硬件扫描", "value": "正在后台采集设备型号与运行环境…"}]

        # 初始化设备信息采集状态。
        self.device_loading = True

        # 初始化设备信息采集线程引用。
        self.hardware_thread = None

        # 初始化当前账号抽屉数据。
        self.account_data = {}

        # 初始化任务运行状态。
        self.task_state = {"running": False, "status": "就绪", "total": 0, "completed": 0, "success": 0, "failure": 0, "stopped": 0, "runningCount": 0, "pending": 0, "elapsed": "0秒", "logPath": ""}

        # 初始化用户提示文本。
        self.notice_text = "原生毛玻璃工作台已就绪"

        # 初始化日志视图刷新间隔。
        self.log_refresh_interval_seconds = 0.20

        # 设置单次日志模型提交的最大行数。
        self.max_log_rows_per_refresh = 12

        # 初始化最近一次日志视图刷新时间。
        self.last_log_refresh_at = 0.0

        # 初始化待发布日志视图刷新标记。
        self.pending_log_refresh = False

        # 初始化任务摘要视图刷新间隔。
        self.task_refresh_interval_seconds = 0.16

        # 初始化最近一次任务摘要视图刷新时间。
        self.last_task_refresh_at = 0.0

        # 初始化待发布任务摘要视图刷新标记。
        self.pending_task_refresh = False

        # 初始化甘特时间线视图刷新间隔。
        self.timeline_refresh_interval_seconds = 0.30

        # 初始化最近一次甘特时间线视图刷新时间。
        self.last_timeline_refresh_at = 0.0

        # 初始化待发布甘特时间线视图刷新标记。
        self.pending_timeline_refresh = False

        # 初始化任务网络结构的合并刷新间隔。
        self.network_refresh_interval_seconds = 0.20

        # 初始化最近一次任务网络视图刷新时间。
        self.last_network_refresh_at = 0.0

        # 初始化待发布任务网络视图刷新标记。
        self.pending_network_refresh = False

        # 初始化减少动画偏好。
        self.reduced_motion = False

        # 读取 GUI 快捷方案配置。
        self.preset_map = load_gui_presets(self.project_root)

        # 读取不包含硬件扫描的启动概览数据。
        self.initial_data = self.build_initial_data()

        # 构建未启动任务时的协议流向网络。
        self.rebuild_network()

        # 连接后台硬件数据到主线程应用方法。
        self.hardwareProfileReady.connect(self.apply_hardware_profile)

        # 创建主线程事件消费定时器。
        self.event_timer = QTimer(self)

        # 设置事件消费间隔。
        self.event_timer.setInterval(32)

        # 绑定事件消费方法。
        self.event_timer.timeout.connect(self.consume_events)

        # 启动主线程事件消费。
        self.event_timer.start()

        # 刷新初始商业列表。
        self.refresh_companies()

        # 在线程中开始硬件信息采集。
        self.refreshDeviceDetails()

    # 定义项目初始数据属性。
    @Property("QVariantMap", constant=True)
    def initialData(self):

        """
        返回 QML 初始化时需要的公共配置选项。

        :return: 初始界面配置。
        :rtype: dict
        """

        # 返回缓存的启动概览副本。
        return dict(self.initial_data)

    # 定义启动概览构建方法。
    def build_initial_data(self):

        """
        读取轻量公共配置和版本日志以构建启动概览。

        :return: QML 初始化配置。
        :rtype: dict
        """

        # 读取全局任务默认配置。
        task_config = get_task_config()

        # 读取一次共享运行期账号配置。
        runtime_config = load_runtime_account_config(self.project_root)

        # 返回 QML 初始化配置字典。
        return {"owners": [""] + list_account_dimension_values("负责人"), "regions": [""] + list_account_dimension_values("大区"), "provinces": [""] + list_account_dimension_values("省份"), "platforms": [""] + sorted({str(account.get("平台", "")) for account in ACCOUNTS.values() if account.get("平台", "")}), "dataTypes": list_data_type_categories(ACCOUNTS), "defaultAction": task_config["执行动作"], "defaultDataType": task_config["数据类型"], "defaultDateMode": task_config["日期模式"], "defaultStartDate": task_config["开始日期"], "defaultEndDate": task_config["结束日期"], "defaultWorkers": task_config["最大并发数"], "companyCount": len(ACCOUNTS), "enabledCount": sum(resolve_runtime_enabled(name, account, runtime_config) for name, account in ACCOUNTS.items()), "environment": f"{platform.system()} · Python {platform.python_version()}", "changelog": get_current_startup_changelog()}

    # 定义商业列表属性。
    @Property("QVariantList", notify=companiesChanged)
    def companies(self):

        """
        返回当前筛选后的商业展示列表。

        :return: 商业展示行集合。
        :rtype: list[dict]
        """

        # 返回商业列表副本。
        return list(self.company_rows)

    # 定义 QML 增量日志模型属性。
    @Property(QObject, constant=True)
    def logs(self):

        """
        返回当前 QML 可增量消费的结构化日志模型。

        :return: 日志列表模型。
        :rtype: GuiLogListModel
        """

        # 返回有界日志模型实例。
        return self.log_model

    # 定义设备详情属性。
    @Property("QVariantList", notify=deviceDetailsChanged)
    def deviceDetails(self):

        """
        返回异步采集的脱敏设备详情。

        :return: 设备详情展示行。
        :rtype: list[dict]
        """

        # 返回设备详情副本。
        return list(self.device_details)

    # 定义设备采集状态属性。
    @Property(bool, notify=deviceLoadingChanged)
    def deviceLoading(self):

        """
        返回当前是否正在采集设备信息。

        :return: 是否正在采集。
        :rtype: bool
        """

        # 返回设备采集状态。
        return self.device_loading

    # 定义设备信息刷新方法。
    @Slot()
    def refreshDeviceDetails(self):

        """
        在线程中采集硬件详情并在主线程更新展示模型。

        :return: None。
        :rtype: None
        """

        # 判断已有硬件采集线程正在执行。
        if self.hardware_thread is not None and self.hardware_thread.is_alive():

            # 结束重复硬件采集请求。
            return

        # 标记设备详情正在采集。
        self.device_loading = True

        # 发布设备采集状态变化。
        self.deviceLoadingChanged.emit()

        # 定义后台硬件采集函数。
        def collect_hardware():

            """
            读取 Windows 硬件信息并投递到 Qt 主线程。

            :return: None。
            :rtype: None
            """

            # 读取当前设备硬件概览。
            hardware_profile = read_hardware_profile()

            # 将硬件结果通过 Qt 队列安全投递回主线程。
            self.hardwareProfileReady.emit(hardware_profile)

        # 创建后台硬件采集线程。
        self.hardware_thread = threading.Thread(target=collect_hardware, name="DDI-Hardware-Profile", daemon=True)

        # 启动后台硬件采集线程。
        self.hardware_thread.start()

    # 定义硬件信息应用方法。
    @Slot(object)
    def apply_hardware_profile(self, hardware_profile):

        """
        将后台采集的硬件信息转换为首页展示行。

        :param hardware_profile: 脱敏硬件信息字典。
        :type hardware_profile: dict
        :return: None。
        :rtype: None
        """

        # 读取标准化硬件信息字典。
        profile = dict(hardware_profile or {})

        # 定义非空列表文本拼接函数。
        def format_items(items):

            """
            将硬件文本列表合并为首页可换行说明。

            :param items: 硬件文本集合。
            :type items: list[str]
            :return: 合并后的硬件文本。
            :rtype: str
            """

            # 返回存在内容的硬件说明。
            return "\n".join(str(item) for item in list(items or []) if str(item).strip()) or "未检测到"

        # 构建设备详情展示行。
        self.device_details = [
            {"label": "设备名称", "value": os.environ.get("COMPUTERNAME", "") or platform.node() or "未知"},
            {"label": "当前用户", "value": profile.get("user_text") or "未检测到"},
            {"label": "MCP 地址", "value": profile.get("mcp_url_text") or "未配置"},
            {"label": "整机型号", "value": profile.get("computer_text") or "未检测到"},
            {"label": "主板", "value": profile.get("baseboard_text") or "未检测到"},
            {"label": "BIOS", "value": profile.get("bios_text") or "未检测到"},
            {"label": "系统", "value": profile.get("operating_system_text") or f"{platform.platform()} · Build {platform.version()}"},
            {"label": "CPU", "value": profile.get("cpu_text") or platform.processor() or "未检测到"},
            {"label": "逻辑核心", "value": str(os.cpu_count() or 1)},
            {"label": "内存总量", "value": profile.get("memory_installed_text") or "未检测到"},
            {"label": "内存模块", "value": format_items(profile.get("memory_module_texts"))},
            {"label": "显卡", "value": format_items(profile.get("gpu_texts"))},
            {"label": "磁盘", "value": format_items(profile.get("disk_texts"))},
            {"label": "物理网卡", "value": format_items(profile.get("network_texts"))},
            {"label": "活动网络", "value": format_items(profile.get("network_configuration_texts"))},
            {"label": "显示器", "value": format_items(profile.get("monitor_texts"))},
            {"label": "电池", "value": format_items(profile.get("battery_texts"))},
            {"label": "音频设备", "value": format_items(profile.get("sound_texts"))},
            {"label": "Python", "value": f"Python {platform.python_version()} · {platform.machine()}\n{sys.executable}"},
        ]

        # 标记设备信息采集结束。
        self.device_loading = False

        # 发布设备详情变化。
        self.deviceDetailsChanged.emit()

        # 发布设备采集状态变化。
        self.deviceLoadingChanged.emit()

    # 定义任务状态属性。
    @Property("QVariantMap", notify=taskChanged)
    def task(self):

        """
        返回当前任务汇总状态。

        :return: 任务汇总状态。
        :rtype: dict
        """

        # 返回任务状态副本。
        return dict(self.task_state)

    # 定义网络节点属性。
    @Property("QVariantList", notify=networkChanged)
    def networkNodes(self):

        """
        返回任务网络节点集合。

        :return: 网络节点集合。
        :rtype: list[dict]
        """

        # 返回网络节点副本。
        return list(self.network_nodes)

    # 定义网络边属性。
    @Property("QVariantList", notify=networkChanged)
    def networkEdges(self):

        """
        返回任务网络连线集合。

        :return: 网络连线集合。
        :rtype: list[dict]
        """

        # 返回网络边副本。
        return list(self.network_edges)

    # 定义甘特记录属性。
    @Property("QVariantList", notify=timelineChanged)
    def timelineRows(self):

        """
        返回本轮任务阶段时间线记录。

        :return: 时间线记录集合。
        :rtype: list[dict]
        """

        # 返回时间线记录副本。
        return list(self.timeline_rows)

    # 定义甘特图时间范围属性。
    @Property("QVariantMap", notify=timelineChanged)
    def timelineRange(self):

        """
        返回甘特图共享时间轴的起止范围。

        :return: 甘特图显示范围。
        :rtype: dict
        """

        # 返回时间轴范围副本。
        return dict(self.timeline_range)

    # 定义本轮商业主时间线初始化方法。
    def initialize_timeline_rows(self, company_names, data_type):

        """
        为每家已选商业建立一条等待状态的主甘特图记录。

        :param company_names: 当前任务选择的商业名称集合。
        :type company_names: list[str]
        :param data_type: 当前任务的数据类型。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 清空本轮商业主时间线记录。
        self.timeline_rows = []

        # 清空本轮阶段事件数量。
        self.timeline_stage_count = 0

        # 遍历当前任务选择的全部商业。
        for company_name in company_names:

            # 读取当前商业公共配置。
            account = ACCOUNTS.get(company_name, {})

            # 追加尚未开始执行的商业主时间线记录。
            self.timeline_rows.append({"company": str(company_name), "platform": str(account.get("平台", "")), "dataType": str(data_type or ""), "stage": "等待分配", "status": "等待", "recordCount": "", "startedAt": "", "endedAt": "", "startEpoch": 0.0, "endEpoch": 0.0, "active": False, "timelineOffset": -1.0, "timelineSpan": 0.0})

        # 清空尚未开始任务的甘特图显示范围。
        self.timeline_range = {"startEpoch": 0.0, "endEpoch": 0.0}

    # 定义商业主时间线记录读取方法。
    def resolve_timeline_row(self, company_name, data_type=""):

        """
        读取指定商业的主甘特图记录，不存在时按公共配置创建记录。

        :param company_name: 目标商业名称。
        :type company_name: str
        :param data_type: 目标商业当前数据类型。
        :type data_type: str
        :return: 指定商业的主甘特图记录。
        :rtype: dict
        """

        # 遍历当前轮全部商业主时间线记录。
        for row in self.timeline_rows:

            # 判断当前记录属于目标商业。
            if row.get("company") == company_name:

                # 使用非空数据类型更新当前商业展示信息。
                row["dataType"] = str(data_type or row.get("dataType", ""))

                # 返回已经存在的商业主时间线记录。
                return row

        # 读取目标商业公共配置。
        account = ACCOUNTS.get(company_name, {})

        # 创建缺少预置状态的商业主时间线记录。
        row = {"company": str(company_name), "platform": str(account.get("平台", "")), "dataType": str(data_type or ""), "stage": "等待分配", "status": "等待", "recordCount": "", "startedAt": "", "endedAt": "", "startEpoch": 0.0, "endEpoch": 0.0, "active": False, "timelineOffset": -1.0, "timelineSpan": 0.0}

        # 追加补建的商业主时间线记录。
        self.timeline_rows.append(row)

        # 返回补建的商业主时间线记录。
        return row

    # 定义甘特图几何刷新方法。
    def refresh_timeline_geometry(self, current_epoch=None):

        """
        依据每家商业真实起止时间计算主甘特图的共享横轴比例。

        :param current_epoch: 运行中条带延展到的毫秒时间戳。
        :type current_epoch: float | None
        :return: None。
        :rtype: None
        """

        # 使用当前系统时间补齐运行中商业的结束位置。
        display_now = float(current_epoch or time.time() * 1000)

        # 筛选已经实际开始执行的商业主时间线记录。
        dated_rows = [row for row in self.timeline_rows if float(row.get("startEpoch", 0.0) or 0.0) > 0.0]

        # 判断当前没有可绘制的商业主时间线记录。
        if not dated_rows:

            # 清空甘特图显示范围。
            self.timeline_range = {"startEpoch": 0.0, "endEpoch": 0.0}

            # 标记全部等待商业不参与条带绘制。
            for row in self.timeline_rows:

                # 清空当前商业条带的起点比例。
                row["timelineOffset"] = -1.0

                # 清空当前商业条带的持续比例。
                row["timelineSpan"] = 0.0

            # 结束本次几何刷新。
            return

        # 读取最早的商业实际开始时间。
        earliest_epoch = min(float(row["startEpoch"]) for row in dated_rows)

        # 读取每条商业主时间线的有效结束时间。
        effective_ends = [float(row.get("endEpoch", 0.0) or display_now) if row.get("active") else float(row.get("endEpoch", 0.0) or row["startEpoch"]) for row in dated_rows]

        # 读取最晚的商业有效结束时间。
        latest_epoch = max(effective_ends)

        # 计算至少一秒的真实时间跨度。
        actual_span = max(1000.0, latest_epoch - earliest_epoch)

        # 计算两侧保留的最小时间留白。
        padding_span = max(1500.0, actual_span * 0.08)

        # 计算带留白的显示开始时间。
        display_start = earliest_epoch - padding_span

        # 计算带留白的显示结束时间。
        display_end = latest_epoch + padding_span

        # 计算带留白的总显示跨度。
        display_span = max(1.0, display_end - display_start)

        # 遍历全部商业主时间线记录并写入共享横轴比例。
        for row in self.timeline_rows:

            # 读取当前商业实际开始时间。
            started_epoch = float(row.get("startEpoch", 0.0) or 0.0)

            # 判断当前商业尚未开始执行。
            if started_epoch <= 0.0:

                # 标记当前商业不参与甘特条带绘制。
                row["timelineOffset"] = -1.0

                # 清空当前商业持续比例。
                row["timelineSpan"] = 0.0

                # 继续处理下一条商业主时间线记录。
                continue

            # 读取当前商业固定结束时间。
            ended_epoch = float(row.get("endEpoch", 0.0) or 0.0)

            # 使用当前时刻延展仍在执行的商业条带。
            effective_end = max(started_epoch, display_now if row.get("active") else ended_epoch or started_epoch)

            # 计算当前商业在共享横轴中的起始比例。
            row["timelineOffset"] = max(0.0, min(1.0, (started_epoch - display_start) / display_span))

            # 计算当前商业在共享横轴中的持续比例。
            row["timelineSpan"] = max(0.0, min(1.0, (effective_end - started_epoch) / display_span))

        # 保存甘特图共享显示范围。
        self.timeline_range = {"startEpoch": display_start, "endEpoch": display_end}

    # 定义账号详情属性。
    @Property("QVariantMap", notify=accountChanged)
    def account(self):

        """
        返回当前账号抽屉数据。

        :return: 账号抽屉数据。
        :rtype: dict
        """

        # 返回账号数据副本。
        return dict(self.account_data)

    # 定义快捷方案属性。
    @Property("QVariantList", notify=presetsChanged)
    def presets(self):

        """
        返回按名称排序的 GUI 快捷方案。

        :return: 快捷方案集合。
        :rtype: list[dict]
        """

        # 返回快捷方案展示集合。
        return [{"name": name, "value": value} for name, value in sorted(self.preset_map.items())]

    # 定义提示文本属性。
    @Property(str, notify=noticeChanged)
    def notice(self):

        """
        返回当前界面提示文本。

        :return: 提示文本。
        :rtype: str
        """

        # 返回当前提示文本。
        return self.notice_text

    # 定义减少动画属性。
    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self):

        """
        返回当前减少动画偏好。

        :return: 是否减少动画。
        :rtype: bool
        """

        # 返回减少动画状态。
        return self.reduced_motion

    # 定义筛选条件写入方法。
    @Slot("QVariantMap")
    def applyFilters(self, filters):

        """
        保存 QML 筛选条件并刷新商业列表。

        :param filters: QML 传入的筛选条件。
        :type filters: dict
        :return: None。
        :rtype: None
        """

        # 标准化筛选条件字段。
        self.filters = {"keyword": str(filters.get("keyword", "")), "owner": str(filters.get("owner", "")), "region": str(filters.get("region", "")), "province": str(filters.get("province", "")), "platform": str(filters.get("platform", "")), "status": str(filters.get("status", ""))}

        # 刷新商业列表。
        self.refresh_companies()

    # 定义商业列表刷新方法。
    def refresh_companies(self):

        """
        基于共享运行期配置生成商业展示行。

        :return: None。
        :rtype: None
        """

        # 读取共享运行期账号配置。
        runtime_config = load_runtime_account_config(self.project_root)

        # 读取运行期启停映射。
        enabled_map = runtime_config.get("商业启停", {}) if isinstance(runtime_config, dict) else {}

        # 查询匹配当前筛选条件的商业名称。
        company_names = filter_company_names(ACCOUNTS, self.filters["keyword"], self.filters["owner"], self.filters["region"], self.filters["province"], self.filters["platform"], enabled_map, self.filters["status"])

        # 构建商业展示行集合。
        self.company_rows = [{"name": name, "platform": str(ACCOUNTS[name].get("平台", "")), "owner": str(ACCOUNTS[name].get("负责人", "")), "region": str(ACCOUNTS[name].get("大区", "")), "province": str(ACCOUNTS[name].get("省份", "")), "enabled": resolve_runtime_enabled(name, ACCOUNTS[name], runtime_config), "selected": name in self.selected_names, "dataTypes": "、".join(dict.fromkeys(normalize_data_type_category(value) for value in ACCOUNTS[name].get("数据类型列表", []) if str(value).strip()))} for name in company_names]

        # 发布商业列表变化信号。
        self.companiesChanged.emit()

    # 定义商业选择切换方法。
    @Slot(str)
    def toggleCompany(self, company_name):

        """
        切换单家商业的本轮任务选择状态。

        :param company_name: 商业名称。
        :type company_name: str
        :return: None。
        :rtype: None
        """

        # 判断商业已经被选择。
        if company_name in self.selected_names:

            # 移除当前商业选择。
            self.selected_names.remove(company_name)

        # 处理商业尚未选择情况。
        else:

            # 添加当前商业选择。
            self.selected_names.add(company_name)

        # 刷新选择状态。
        self.refresh_companies()

    # 定义启用商业全选方法。
    @Slot()
    def selectEnabledCompanies(self):

        """
        选择当前筛选结果中的全部已启用商业。

        :return: None。
        :rtype: None
        """

        # 读取共享运行期账号配置。
        runtime_config = load_runtime_account_config(self.project_root)

        # 遍历当前商业展示行。
        for row in self.company_rows:

            # 判断当前商业有效启用。
            if resolve_runtime_enabled(row["name"], ACCOUNTS[row["name"]], runtime_config):

                # 记录当前商业选择。
                self.selected_names.add(row["name"])

        # 刷新选择状态。
        self.refresh_companies()

    # 定义商业选择清除方法。
    @Slot()
    def clearSelection(self):

        """
        清空本轮全部商业选择。

        :return: None。
        :rtype: None
        """

        # 清空商业选择集合。
        self.selected_names.clear()

        # 刷新选择状态。
        self.refresh_companies()

    # 定义商业运行期开关写入方法。
    @Slot(str, bool)
    def setCompanyEnabled(self, company_name, enabled):

        """
        保存指定商业的运行期启用状态。

        :param company_name: 商业名称。
        :type company_name: str
        :param enabled: 是否启用。
        :type enabled: bool
        :return: None。
        :rtype: None
        """

        # 判断目标商业不存在。
        if company_name not in ACCOUNTS:

            # 设置商业不存在提示。
            self.set_notice("商业配置不存在")

            # 结束状态更新。
            return

        # 读取当前运行期账号配置。
        runtime_config = load_runtime_account_config(self.project_root)

        # 初始化商业启停配置字典。
        enabled_map = runtime_config.setdefault("商业启停", {})

        # 保存当前商业启用状态。
        enabled_map[company_name] = bool(enabled)

        # 写回共享运行期账号配置。
        save_runtime_account_config(runtime_config, self.project_root)

        # 刷新商业列表。
        self.refresh_companies()

        # 设置商业状态更新提示。
        self.set_notice(f"已{'启用' if enabled else '停用'} {company_name}")

    # 定义账号详情读取方法。
    @Slot(str)
    def openAccount(self, company_name):

        """
        读取指定商业允许编辑的运行期账号字段。

        :param company_name: 商业名称。
        :type company_name: str
        :return: None。
        :rtype: None
        """

        # 判断商业配置不存在。
        if company_name not in ACCOUNTS:

            # 设置账号不存在提示。
            self.set_notice("商业账号配置不存在")

            # 结束账号读取。
            return

        # 读取当前有效账号配置。
        account = get_effective_account(company_name, self.project_root)

        # 读取允许编辑字段。
        editable_fields = get_runtime_editable_account_fields(ACCOUNTS[company_name])

        # 保存账号抽屉展示数据。
        self.account_data = {"company": company_name, "platform": str(account.get("平台", "")), "fields": [{"name": field_name, "value": str(account.get(field_name, "")), "secret": field_name == "密码"} for field_name in editable_fields]}

        # 发布账号数据变化信号。
        self.accountChanged.emit()

    # 定义账号覆盖保存方法。
    @Slot(str, "QVariantMap")
    def saveAccount(self, company_name, fields):

        """
        保存指定商业的运行期账号覆盖字段。

        :param company_name: 商业名称。
        :type company_name: str
        :param fields: 账号覆盖字段。
        :type fields: dict
        :return: None。
        :rtype: None
        """

        # 捕获账号覆盖校验异常。
        try:

            # 读取当前有效账号字段。
            effective_account = get_effective_account(company_name, self.project_root)

            # 读取允许保存的账号字段名称。
            editable_fields = get_runtime_editable_account_fields(ACCOUNTS[company_name])

            # 组合未编辑字段与 QML 提交字段。
            merged_fields = {field_name: str(fields.get(field_name, effective_account.get(field_name, ""))) for field_name in editable_fields}

            # 保存允许的运行期账号覆盖。
            save_runtime_account_override(company_name, merged_fields, self.project_root)

            # 重新读取账号详情。
            self.openAccount(company_name)

            # 设置账号保存成功提示。
            self.set_notice(f"已保存 {company_name} 的运行期账号覆盖")

        # 处理账号覆盖保存失败。
        except Exception as error:

            # 设置账号保存失败提示。
            self.set_notice(f"账号保存失败：{error}")

    # 定义账号覆盖恢复方法。
    @Slot(str)
    def restoreAccount(self, company_name):

        """
        清除指定商业运行期账号覆盖。

        :param company_name: 商业名称。
        :type company_name: str
        :return: None。
        :rtype: None
        """

        # 捕获账号覆盖清除异常。
        try:

            # 清除指定商业运行期账号覆盖。
            clear_runtime_account_override(company_name, self.project_root)

            # 重新读取账号详情。
            self.openAccount(company_name)

            # 设置账号恢复成功提示。
            self.set_notice(f"已恢复 {company_name} 的默认账号配置")

        # 处理账号覆盖恢复失败。
        except Exception as error:

            # 设置账号恢复失败提示。
            self.set_notice(f"账号恢复失败：{error}")

    # 定义快捷方案保存方法。
    @Slot(str, "QVariantMap")
    def savePreset(self, preset_name, value):

        """
        保存当前界面任务参数和商业选择为快捷方案。

        :param preset_name: 快捷方案名称。
        :type preset_name: str
        :param value: 快捷方案内容。
        :type value: dict
        :return: None。
        :rtype: None
        """

        # 标准化快捷方案名称。
        normalized_name = str(preset_name).strip()

        # 判断快捷方案名称为空。
        if not normalized_name:

            # 设置快捷方案名称提示。
            self.set_notice("请输入快捷方案名称")

            # 结束快捷方案保存。
            return

        # 保存快捷方案内容副本。
        self.preset_map[normalized_name] = dict(value)

        # 写入共享 GUI 快捷方案配置。
        save_gui_presets(self.project_root, self.preset_map)

        # 发布快捷方案变化信号。
        self.presetsChanged.emit()

        # 设置快捷方案保存成功提示。
        self.set_notice(f"已保存快捷方案：{normalized_name}")

    # 定义快捷方案读取方法。
    @Slot(str, result="QVariantMap")
    def loadPreset(self, preset_name):

        """
        返回指定快捷方案内容供 QML 填充界面。

        :param preset_name: 快捷方案名称。
        :type preset_name: str
        :return: 快捷方案内容。
        :rtype: dict
        """

        # 读取指定快捷方案副本。
        preset = dict(self.preset_map.get(str(preset_name), {}))

        # 将历史方案中的原始别名迁移为当前界面大类。
        if isinstance(preset.get("dataTypes"), (list, tuple)):

            # 保持方案原有顺序并去除归并后的重复大类。
            preset["dataTypes"] = list(dict.fromkeys(normalize_data_type_category(value) for value in preset["dataTypes"] if str(value).strip()))

        # 返回迁移后的快捷方案内容。
        return preset

    # 定义减少动画写入方法。
    @Slot(bool)
    def setReducedMotion(self, enabled):

        """
        更新 GUI 减少动画偏好。

        :param enabled: 是否减少动画。
        :type enabled: bool
        :return: None。
        :rtype: None
        """

        # 保存标准化减少动画状态。
        self.reduced_motion = bool(enabled)

        # 发布减少动画状态变化信号。
        self.reducedMotionChanged.emit()

    # 定义任务启动方法。
    @Slot("QVariantMap")
    def startTask(self, parameters):

        """
        按当前 QML 参数启动无界面公共 DDI 任务。

        :param parameters: 任务参数字典。
        :type parameters: dict
        :return: None。
        :rtype: None
        """

        # 判断已有任务线程或任务状态仍在执行。
        if (self.run_thread is not None and self.run_thread.is_alive()) or self.task_state.get("running", False):

            # 设置任务运行中提示。
            self.set_notice("当前已有任务正在运行，请等待完成或请求安全停止")

            # 结束重复启动。
            return

        # 读取保持账号配置顺序的选中商业。
        selected_names = [name for name in ACCOUNTS if name in self.selected_names]

        # 判断尚未选择任何商业。
        if not selected_names:

            # 设置商业选择为空提示。
            self.set_notice("请至少选择一家商业后再执行")

            # 结束任务启动。
            return

        # 构建公共无界面任务请求。
        # 读取 GUI 传入的多选数据类型。
        selected_data_types = tuple(str(value).strip() for value in parameters.get("dataTypes", []) if str(value).strip())

        # 判断尚未选择任何数据类型。
        if not selected_data_types:

            # 设置数据类型选择为空提示。
            self.set_notice("请至少选择一种数据类型后再执行")

            # 结束任务启动。
            return

        # 兼容旧版单数据类型参数。
        legacy_data_type = str(parameters.get("dataType", "全部"))

        # 捕获日期模式和范围参数错误。
        try:

            # 构造统一日期范围对象。
            date_range = DateRangeSpec.from_mode(str(parameters.get("dateMode", "custom")), str(parameters.get("startDate", "")), str(parameters.get("endDate", "")))

        # 处理日期参数无效场景。
        except ValueError as error:

            # 设置日期参数错误提示。
            self.set_notice(f"日期参数无效：{error}")

            # 结束任务启动。
            return

        # 读取运行目录根路径。
        runtime_root = os.path.join(self.project_root, "runtime")

        # 构建公共无界面任务请求。
        request = TaskRequest(action=str(parameters.get("action", "query_excel")), data_type=legacy_data_type, data_types=selected_data_types, start_date=date_range.start_date, end_date=date_range.end_date, cookie_dir=os.path.join(runtime_root, "cookies"), output_dir=os.path.join(runtime_root, "downloads"), log_dir=os.path.join(runtime_root, "logs"), max_workers=max(1, int(parameters.get("maxWorkers", 1))), copy_excel=bool(parameters.get("copyExcel", True)), console_output_enabled=False, date_range=date_range, persist_selected_enablement=True)

        # 判断日期参数不完整。
        if not request.start_date or not request.end_date:

            # 设置日期缺失提示。
            self.set_notice("请完整填写开始日期和结束日期")

            # 结束任务启动。
            return

        # 创建本轮任务取消控制器。
        self.cancellation = TaskCancellation()

        # 清空本轮可见日志模型。
        self.log_model.clear()

        # 清空待写入日志集合。
        self.pending_log_rows = []

        # 重置待发布日志视图刷新标记。
        self.pending_log_refresh = False

        # 重置最近一次日志视图刷新时间。
        self.last_log_refresh_at = 0.0

        # 重置待发布任务摘要视图刷新标记。
        self.pending_task_refresh = False

        # 重置最近一次任务摘要视图刷新时间。
        self.last_task_refresh_at = 0.0

        # 重置待发布甘特时间线视图刷新标记。
        self.pending_timeline_refresh = False

        # 重置最近一次甘特时间线视图刷新时间。
        self.last_timeline_refresh_at = 0.0

        # 重置待发布任务网络视图刷新标记。
        self.pending_network_refresh = False

        # 重置最近一次任务网络视图刷新时间。
        self.last_network_refresh_at = 0.0

        # 为每家已选商业预置等待状态的主甘特图记录。
        self.initialize_timeline_rows(selected_names, ",".join(request.data_types))

        # 初始化商业任务状态。
        self.company_states = {name: {"status": "等待", "stage": "等待", "platform": str(ACCOUNTS[name].get("平台", "")), "recordCount": "", "updatedAt": 0.0} for name in selected_names}

        # 等待公共运行时发布真实任务拓扑。
        self.task_topology = {}

        # 清空上一轮任务网络聚焦商业。
        self.network_focus_company = ""

        # 清空上一轮任务网络聚合展开状态。
        self.network_focus_group = ""

        # 清空本轮并发槽位状态。
        self.worker_slots = {}

        # 清空本轮网络节点入场时间索引。
        self.network_node_entered_at_ms = {}

        # 初始化任务状态。
        self.task_state.update({"running": True, "status": "任务运行中", "total": len(selected_names), "completed": 0, "success": 0, "failure": 0, "stopped": 0, "runningCount": 0, "pending": len(selected_names), "elapsed": "0秒", "logPath": ""})

        # 同步清空后的 QML 时间线。
        self.timelineChanged.emit()

        # 重建本轮网络。
        self.rebuild_network()

        # 发布任务状态变化。
        self.taskChanged.emit()

        # 设置任务启动提示。
        self.set_notice(f"已提交 {len(selected_names)} 家商业，任务网络正在绽放")

        # 定义后台线程执行入口。
        def run_task():

            """
            在后台线程中调用公共 DDI 运行时。

            :return: None。
            :rtype: None
            """

            # 创建共享 GUI 事件接收器的公共运行时。
            runtime = DdiTaskRuntime(self.project_root, self.event_sink)

            # 执行当前选择的商业任务。
            try:

                # 调用公共运行时执行全部已选商业。
                runtime.execute(request, selected_names, self.cancellation)

            # 处理后台运行时未捕获异常。
            except Exception as error:

                # 发布可展示的任务运行时失败事件。
                self.event_sink.publish(TaskEvent("task_runtime_error", str(error), "失败"))

        # 创建承载公共 DDI 运行时的后台线程。
        self.run_thread = threading.Thread(target=run_task, name="DDI-Qt-GUI-Task", daemon=True)

        # 启动后台任务线程。
        self.run_thread.start()

    # 定义安全停止方法。
    @Slot()
    def requestStop(self):

        """
        请求停止尚未开始的商业任务。

        :return: None。
        :rtype: None
        """

        # 判断当前任务不存在取消控制器。
        if self.cancellation is None:

            # 结束停止请求。
            return

        # 请求公共协调器停止待提交商业。
        self.cancellation.request_stop()

        # 更新任务状态文字。
        self.task_state["status"] = "正在安全停止：运行中任务将完成收尾"

        # 发布任务状态变化。
        self.taskChanged.emit()

    # 定义任务日志打开方法。
    @Slot()
    def openTaskLog(self):

        """
        使用系统默认程序打开本次 Excel 任务日志。

        :return: None。
        :rtype: None
        """

        # 读取任务日志路径。
        log_path = str(self.task_state.get("logPath", ""))

        # 判断任务日志路径存在。
        if log_path and os.path.exists(log_path):

            # 使用桌面服务打开任务日志文件。
            QDesktopServices.openUrl(QUrl.fromLocalFile(log_path))

        # 处理任务日志尚未生成情况。
        else:

            # 设置任务日志不存在提示。
            self.set_notice("本次任务日志尚未生成")

    # 定义主线程事件消费方法。
    @Slot()
    def consume_events(self):

        """
        在 Qt 主线程内按时间预算消费后台任务事件。

        :return: None。
        :rtype: None
        """

        # 保存本轮消费起始单调时间。
        started_at = time.perf_counter()

        # 初始化本轮消费事件数量。
        processed_count = 0

        # 初始化本轮模型刷新标记。
        refresh_flags = {"logs": False, "task": False, "timeline": False, "network": False}

        # 设置单轮事件消费数量上限。
        max_events_per_cycle = 12

        # 设置单轮事件消费时间预算。
        event_time_budget_seconds = 0.003

        # 在事件数量和时间预算内持续消费事件。
        while processed_count < max_events_per_cycle and time.perf_counter() - started_at < event_time_budget_seconds:

            # 尝试读取下一条公共事件。
            try:

                # 读取当前事件。
                event = self.event_sink.get_nowait()

            # 处理当前没有待消费事件。
            except queue.Empty:

                # 结束本轮事件消费。
                break

            # 将当前事件同步到 QML 状态并累积本轮刷新标记。
            refresh_flags = self.handle_task_event(event, refresh_flags)

            # 累加已消费事件数量。
            processed_count += 1

        # 判断本轮存在待发布的日志模型更新。
        if refresh_flags["logs"]:

            # 标记日志模型将在节流窗口结束后发布。
            self.pending_log_refresh = True

            # 交由日志节流器决定本轮是否通知 QML。
            refresh_flags["logs"] = False

        # 判断本轮存在待发布的任务摘要更新。
        if refresh_flags["task"]:

            # 标记任务摘要将在节流窗口结束后发布。
            self.pending_task_refresh = True

            # 交由任务摘要节流器决定本轮是否通知 QML。
            refresh_flags["task"] = False

        # 判断本轮存在待发布的甘特时间线更新。
        if refresh_flags["timeline"]:

            # 标记甘特时间线将在节流窗口结束后发布。
            self.pending_timeline_refresh = True

            # 交由甘特时间线节流器决定本轮是否通知 QML。
            refresh_flags["timeline"] = False

        # 判断本轮存在待发布的任务网络更新。
        if refresh_flags["network"]:

            # 标记任务网络将在节流窗口结束后发布。
            self.pending_network_refresh = True

            # 交由任务网络节流器决定本轮是否通知 QML。
            refresh_flags["network"] = False

        # 获取当前刷新检查时间。
        refreshed_at = time.perf_counter()

        # 判断存在需要随当前时间延展的商业主甘特条带。
        has_active_timeline_row = any(bool(row.get("active")) for row in getattr(self, "timeline_rows", []))

        # 按时间线刷新间隔推进运行中的商业条带。
        if has_active_timeline_row and refreshed_at - self.last_timeline_refresh_at >= self.timeline_refresh_interval_seconds:

            # 使用当前时刻更新运行中商业的甘特条带长度。
            self.refresh_timeline_geometry()

            # 标记时间线模型需要在本轮通知 QML。
            refresh_flags["timeline"] = True

            # 保存当前甘特时间线刷新时间。
            self.last_timeline_refresh_at = refreshed_at

            # 清空已经由本轮直接发布的时间线刷新标记。
            self.pending_timeline_refresh = False

        # 判断日志节流窗口已经结束。
        if self.pending_log_refresh and refreshed_at - self.last_log_refresh_at >= self.log_refresh_interval_seconds:

            # 标记日志模型需要在本轮通知 QML。
            refresh_flags["logs"] = True

            # 保存当前日志模型刷新时间。
            self.last_log_refresh_at = refreshed_at

            # 清空待发布日志模型刷新标记。
            self.pending_log_refresh = False

        # 判断任务摘要节流窗口已经结束。
        if self.pending_task_refresh and refreshed_at - self.last_task_refresh_at >= self.task_refresh_interval_seconds:

            # 标记任务摘要模型需要在本轮通知 QML。
            refresh_flags["task"] = True

            # 保存当前任务摘要刷新时间。
            self.last_task_refresh_at = refreshed_at

            # 清空待发布任务摘要视图刷新标记。
            self.pending_task_refresh = False

        # 判断甘特时间线节流窗口已经结束。
        if self.pending_timeline_refresh and refreshed_at - self.last_timeline_refresh_at >= self.timeline_refresh_interval_seconds:

            # 标记甘特时间线模型需要在本轮通知 QML。
            refresh_flags["timeline"] = True

            # 保存当前甘特时间线刷新时间。
            self.last_timeline_refresh_at = refreshed_at

            # 清空待发布甘特时间线视图刷新标记。
            self.pending_timeline_refresh = False

        # 判断任务网络节流窗口已经结束。
        if self.pending_network_refresh and refreshed_at - self.last_network_refresh_at >= self.network_refresh_interval_seconds:

            # 标记任务网络模型需要在本轮通知 QML。
            refresh_flags["network"] = True

            # 保存当前任务网络模型刷新时间。
            self.last_network_refresh_at = refreshed_at

            # 清空待发布任务网络模型刷新标记。
            self.pending_network_refresh = False

        # 判断本轮没有任何模型需要刷新。
        if not any(refresh_flags.values()):

            # 结束空事件刷新。
            return

        # 按模型类型批量通知 QML 更新。
        self.publish_event_refreshes(refresh_flags)

    # 定义事件状态同步方法。
    def handle_task_event(self, event, refresh_flags=None):

        """
        将一条公共任务事件增量同步到 QML 任务、日志和网络模型。

        :param event: 公共任务事件。
        :type event: TaskEvent
        :param refresh_flags: 本轮事件消费的模型刷新标记。
        :type refresh_flags: dict | None
        :return: 更新后的模型刷新标记。
        :rtype: dict
        """

        # 初始化独立调用时的模型刷新标记。
        if refresh_flags is None:

            # 创建默认模型刷新标记。
            refresh_flags = {"logs": False, "task": False, "timeline": False, "network": False}

        # 读取标准化事件类型。
        event_type = str(event.event_type or "")

        # 读取标准化商业名称。
        company_name = str(event.company_name or "")

        # 读取事件扩展载荷。
        payload = dict(event.payload or {})

        # 追加结构化日志展示行。
        self.append_log_event(event)

        # 标记日志模型需要刷新。
        refresh_flags["logs"] = True

        # 判断事件携带任务拓扑。
        if event_type == "task_topology":

            # 保存商业数据类型真实拓扑。
            self.task_topology = {str(name): list(data_types) for name, data_types in dict(payload.get("商业数据类型", {})).items()}

            # 标记网络模型需要刷新。
            refresh_flags["network"] = True

        # 判断事件标识任务开始。
        if event_type == "task_started":

            # 初始化并发槽位展示状态。
            self.worker_slots = {int(slot): {"status": "空闲", "company": ""} for slot in payload.get("并发槽位列表", [])}

            # 标记网络模型需要刷新。
            refresh_flags["network"] = True

        # 判断事件关联具体商业。
        if company_name:

            # 创建或读取当前商业状态。
            state = self.company_states.setdefault(company_name, {"status": "等待", "stage": "等待", "platform": str(ACCOUNTS.get(company_name, {}).get("平台", "")), "recordCount": "", "taskStates": {}, "updatedAt": 0.0})

            # 为历史状态补齐数据类型阶段集合。
            state.setdefault("taskStates", {})

            # 读取当前商业的主甘特图记录。
            timeline_row = self.resolve_timeline_row(company_name, str(event.data_type or ""))

            # 读取当前生命周期事件的毫秒时间戳。
            event_epoch = event.created_at.timestamp() * 1000

            # 格式化当前生命周期事件的展示时间。
            event_time_text = event.created_at.strftime("%Y-%m-%d %H:%M:%S")

            # 处理商业进入队列事件。
            if event_type == "company_queued":

                # 写入商业等待状态。
                state.update({"status": "等待", "stage": "等待分配", "updatedAt": time.monotonic()})

                # 更新主甘特图中的等待状态说明。
                timeline_row.update({"status": "等待", "stage": "等待分配", "active": False})

                # 使用当前事件刷新商业主甘特图几何。
                self.refresh_timeline_geometry(event_epoch)

                # 标记时间线模型需要刷新。
                refresh_flags["timeline"] = True

                # 标记网络模型需要刷新。
                refresh_flags["network"] = True

            # 处理商业实际开始事件。
            if event_type == "company_started":

                # 写入商业运行状态。
                state.update({"status": "运行中", "stage": "协议执行", "updatedAt": time.monotonic()})

                # 写入商业实际开始执行的主甘特图时间。
                timeline_row.update({"status": "运行中", "stage": "协议执行", "startedAt": event_time_text, "endedAt": "", "startEpoch": event_epoch, "endEpoch": 0.0, "active": True})

                # 使用当前事件刷新商业主甘特图几何。
                self.refresh_timeline_geometry(event_epoch)

                # 标记时间线模型需要刷新。
                refresh_flags["timeline"] = True

                # 标记网络模型需要刷新。
                refresh_flags["network"] = True

            # 处理商业完成事件。
            if event_type == "company_finished":

                # 解析商业最终状态。
                company_status = str(event.status or "成功")

                # 读取商业任务终止时的关联数据类型。
                terminal_data_type = str(event.data_type or "")

                # 判断商业在某个具体数据类型上结束。
                if terminal_data_type and terminal_data_type != "全部":

                    # 创建或读取终止数据类型诊断状态。
                    terminal_state = state.setdefault("taskStates", {}).setdefault(terminal_data_type, {})

                    # 写入终止数据类型的最终步骤和异常信息。
                    terminal_state.update({"status": company_status, "stage": "商业任务" if company_status == "成功" else "任务终止", "recordCount": terminal_state.get("recordCount", state.get("recordCount", "")), "message": str(event.message or ""), "updatedAt": time.monotonic()})

                # 写入商业最终状态。
                state.update({"status": company_status, "stage": "商业任务" if company_status == "成功" else "任务终止", "lastMessage": str(event.message or ""), "updatedAt": time.monotonic()})

                # 补齐异常路径中缺失的商业开始时间。
                started_epoch = float(timeline_row.get("startEpoch", 0.0) or event_epoch)

                # 补齐异常路径中缺失的商业开始时间文本。
                started_at_text = str(timeline_row.get("startedAt", "") or event_time_text)

                # 写入商业最终状态和结束时间。
                timeline_row.update({"status": str(event.status or "成功"), "stage": "商业任务", "startedAt": started_at_text, "endedAt": event_time_text, "startEpoch": started_epoch, "endEpoch": event_epoch, "active": False})

                # 使用当前事件刷新商业主甘特图几何。
                self.refresh_timeline_geometry(event_epoch)

                # 标记时间线模型需要刷新。
                refresh_flags["timeline"] = True

                # 标记网络模型需要刷新。
                refresh_flags["network"] = True

            # 处理商业安全停止事件。
            if event_type == "company_stopped":

                # 写入商业停止状态。
                state.update({"status": "停止", "stage": "未开始", "updatedAt": time.monotonic()})

                # 判断当前商业已经开始执行。
                if float(timeline_row.get("startEpoch", 0.0) or 0.0) > 0.0:

                    # 写入已启动商业的停止结束时间。
                    timeline_row.update({"status": "停止", "stage": "已停止", "endedAt": event_time_text, "endEpoch": event_epoch, "active": False})

                # 处理尚未开始即停止的商业。
                else:

                    # 保留未开始商业不绘制时间条带的状态。
                    timeline_row.update({"status": "停止", "stage": "未开始", "active": False})

                # 使用当前事件刷新商业主甘特图几何。
                self.refresh_timeline_geometry(event_epoch)

                # 标记时间线模型需要刷新。
                refresh_flags["timeline"] = True

                # 标记网络模型需要刷新。
                refresh_flags["network"] = True

            # 判断事件携带并发槽位。
            if payload.get("并发槽位") is not None:

                # 标准化并发槽位编号。
                worker_slot = int(payload["并发槽位"])

                # 创建或读取当前槽位状态。
                slot_state = self.worker_slots.setdefault(worker_slot, {"status": "空闲", "company": ""})

                # 写入当前槽位商业名称。
                slot_state["company"] = company_name

                # 写入槽位任务状态。
                slot_state["status"] = "运行中" if event_type in {"company_queued", "company_started"} else str(event.status or "成功")

                # 标记网络模型需要刷新。
                refresh_flags["network"] = True

        # 判断事件为脱敏阶段时间线。
        if event_type == "task_timeline":

            # 累加本轮已接收的阶段事件数量。
            self.timeline_stage_count += 1

            # 读取阶段开始时间文本。
            started_at = str(payload.get("阶段开始时间", ""))

            # 读取阶段结束时间文本。
            ended_at = str(payload.get("阶段结束时间", ""))

            # 读取阶段开始毫秒时间戳。
            started_epoch = parse_timeline_epoch(payload.get("阶段开始时间", ""))

            # 读取阶段结束毫秒时间戳。
            ended_epoch = parse_timeline_epoch(payload.get("阶段结束时间", ""))

            # 更新商业主时间线的最新阶段信息。
            if company_name:

                # 读取当前商业主甘特图记录。
                timeline_row = self.resolve_timeline_row(company_name, str(event.data_type or payload.get("数据类型", "")))

                # 读取当前阶段名称。
                stage_name = str(payload.get("执行阶段", "执行中"))

                # 读取当前阶段状态。
                stage_status = str(payload.get("执行状态", event.status or "信息"))

                # 写入当前商业的最新阶段和记录数。
                timeline_row.update({"stage": stage_name, "recordCount": str(payload.get("记录数量", ""))})

                # 读取当前阶段所属的数据类型名称。
                stage_data_type = str(event.data_type or payload.get("数据类型", ""))

                # 判断当前阶段关联一个具体数据类型。
                if stage_data_type and stage_data_type != "全部":

                    # 创建或读取数据类型的独立诊断状态。
                    data_type_state = self.company_states.setdefault(company_name, {}).setdefault("taskStates", {}).setdefault(stage_data_type, {})

                    # 根据阶段事件状态生成数据类型节点状态。
                    data_type_status = stage_status if stage_status in {"成功", "失败", "错误", "停止"} else "运行中"

                    # 写入数据类型当前步骤、记录数和最后事件消息。
                    data_type_state.update({"status": data_type_status, "stage": stage_name, "recordCount": str(payload.get("记录数量", "")), "message": str(event.message or ""), "updatedAt": time.monotonic()})

                # 判断生命周期开始事件尚未到达但阶段已经开始。
                if float(timeline_row.get("startEpoch", 0.0) or 0.0) <= 0.0 and started_epoch > 0.0:

                    # 使用首个真实阶段开始时间补齐商业主时间线起点。
                    timeline_row.update({"startedAt": started_at, "startEpoch": started_epoch, "active": True, "status": "运行中"})

                # 判断当前阶段代表商业整体完成。
                if stage_name == "商业任务":

                    # 写入商业整体完成状态和结束时间。
                    timeline_row.update({"status": stage_status, "endedAt": ended_at, "endEpoch": ended_epoch or started_epoch, "active": False})

                # 依据最新商业主时间线刷新共享横轴比例。
                self.refresh_timeline_geometry(ended_epoch or started_epoch or event.created_at.timestamp() * 1000)

                # 标记时间线模型需要刷新。
                refresh_flags["timeline"] = True

                # 写入商业阶段说明。
                self.company_states.setdefault(company_name, {})["stage"] = stage_name

                # 写入商业记录数量。
                self.company_states.setdefault(company_name, {})["recordCount"] = str(payload.get("记录数量", ""))

                # 标记网络模型需要刷新。
                refresh_flags["network"] = True

        # 判断事件携带队列进度。
        if event_type in {"task_started", "task_progress", "task_finished"}:

            # 更新任务汇总数字。
            self.task_state.update({"total": int(payload.get("总数", self.task_state["total"])), "completed": int(payload.get("完成", self.task_state["completed"])), "success": int(payload.get("成功", self.task_state["success"])), "failure": int(payload.get("失败", self.task_state["failure"])), "stopped": int(payload.get("停止", self.task_state["stopped"])), "runningCount": int(payload.get("运行中", self.task_state["runningCount"])), "pending": int(payload.get("待提交", self.task_state["pending"])), "elapsed": f"{payload.get('耗时秒', 0)}秒"})

            # 标记任务模型需要刷新。
            refresh_flags["task"] = True

        # 判断事件为任务日志保存通知。
        if event_type == "task_log":

            # 保存任务日志文件路径。
            self.task_state["logPath"] = str(payload.get("文件", ""))

            # 标记任务模型需要刷新。
            refresh_flags["task"] = True

        # 判断事件为任务完成或运行时异常。
        if event_type in {"task_finished", "task_runtime_error"}:

            # 标记任务已结束。
            self.task_state["running"] = False

            # 写入任务完成状态文本。
            self.task_state["status"] = "任务执行完成" if event_type == "task_finished" else "任务执行失败"

            # 标记任务模型需要刷新。
            refresh_flags["task"] = True

            # 标记网络模型需要刷新。
            refresh_flags["network"] = True

        # 返回当前事件刷新标记。
        return refresh_flags

    # 定义事件批量刷新方法。
    def publish_event_refreshes(self, refresh_flags):

        """
        在单个事件循环周期内按需通知 QML 刷新模型。

        :param refresh_flags: 当前事件周期积累的模型刷新标记。
        :type refresh_flags: dict
        :return: None。
        :rtype: None
        """

        # 判断日志模型需要刷新。
        if refresh_flags["logs"]:

            # 批量写入当前待展示日志。
            self.log_model.append_rows(self.pending_log_rows[:self.max_log_rows_per_refresh])

            # 移除已经写入模型的日志集合。
            self.pending_log_rows = self.pending_log_rows[self.max_log_rows_per_refresh:]

            # 判断剩余日志仍需等待后续刷新周期提交。
            if self.pending_log_rows:

                # 保持日志模型的待刷新标记。
                self.pending_log_refresh = True

        # 判断任务模型需要刷新。
        if refresh_flags["task"]:

            # 发布任务模型变化信号。
            self.taskChanged.emit()

        # 判断时间线模型需要刷新。
        if refresh_flags["timeline"]:

            # 发布时间线模型变化信号。
            self.timelineChanged.emit()

        # 判断网络模型需要刷新。
        if refresh_flags["network"]:

            # 重建实际任务网络模型。
            self.rebuild_network()

    # 定义增量日志追加方法。
    def append_log_event(self, event):

        """
        将公共事件增量转成有限容量的 QML 日志行。

        :param event: 公共任务事件。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        # 构建当前日志展示行。
        row = {"time": event.created_at.strftime("%H:%M:%S"), "type": str(event.event_type), "status": str(event.status), "company": str(event.company_name), "message": str(event.message)}

        # 追加当前日志到待批量写入集合。
        self.pending_log_rows.append(row)

    # 定义网络模型重建方法。
    def rebuild_network(self):

        """
        根据真实任务拓扑、槽位和阶段状态生成 QML 神经网络模型。

        :return: None。
        :rtype: None
        """

        # 读取本轮全部真实商业名称。
        company_names = list(self.task_topology or self.company_states)

        # 筛选当前运行或已进入并发槽位的商业名称。
        active_names = {name for name, state in self.company_states.items() if state.get("status") == "运行中"}

        # 合并槽位占用商业到当前活跃集合。
        active_names.update(str(value.get("company", "")) for value in self.worker_slots.values() if value.get("company"))

        # 按最近状态更新时间读取已完成商业。
        completed_names = [name for name in company_names if name not in active_names and self.company_states.get(name, {}).get("status") in {"成功", "失败", "停止"}]

        # 按时间倒序排列已完成商业。
        completed_names = sorted(completed_names, key=lambda name: self.company_states.get(name, {}).get("updatedAt", 0.0), reverse=True)

        # 读取需要保留的最近完成商业。
        recent_completed_names = completed_names[:self.network_history_limit]

        # 初始化聚合节点点击后额外展开的商业集合。
        group_expanded_names = []

        # 判断当前聚焦待执行商业聚合节点。
        if self.network_focus_group == "pending":

            # 展开受限数量的待执行商业。
            group_expanded_names = [name for name in company_names if self.company_states.get(name, {}).get("status") in {"等待", "就绪", ""}][:self.network_history_limit]

        # 判断当前聚焦历史商业聚合节点。
        if self.network_focus_group == "history":

            # 展开最近历史节点之后的一组已完成商业。
            group_expanded_names = completed_names[self.network_history_limit:self.network_history_limit * 2]

        # 合并当前可见真实商业集合。
        visible_company_names = [name for name in company_names if name in active_names or name in recent_completed_names or name in group_expanded_names or name == self.network_focus_company]

        # 计算尚未展开的待执行商业数量。
        pending_count = sum(1 for name in company_names if name not in visible_company_names and self.company_states.get(name, {}).get("status") in {"等待", "就绪", ""})

        # 计算已聚合的历史商业数量。
        historical_count = max(0, len(completed_names) - sum(1 for name in visible_company_names if name in completed_names))

        # 初始化网络节点集合。
        nodes = [{"id": "root", "parent": "", "kind": "root", "title": "DDI 调度核心" if company_names else "DDI 协议流向", "detail": f"{len(company_names)} 家商业 · {len(self.worker_slots)} 个并发槽位" if company_names else "本机配置已就绪 · 等待任务提交", "diagnostics": f"任务状态：{self.task_state.get('status', '就绪')}\n商业数量：{len(company_names)}\n并发槽位：{len(self.worker_slots)}", "status": "运行中" if self.task_state["running"] else "就绪", "level": 0, "order": 0}]

        # 初始化网络边集合。
        edges = []

        # 判断当前尚未提交真实任务拓扑。
        if not company_names:

            # 追加本机商业配置读取节点。
            nodes.append({"id": "idle:configuration", "parent": "root", "kind": "idle", "title": "商业配置", "detail": f"{self.initial_data.get('enabledCount', 0)} 家启用商业", "diagnostics": f"当前启用商业：{self.initial_data.get('enabledCount', 0)}\n已登记商业：{self.initial_data.get('companyCount', 0)}\n数据来源：本机 account_config.py", "status": "就绪", "level": 1, "order": 0})

            # 追加配置到协议任务的连线。
            edges.append({"from": "root", "to": "idle:configuration", "level": 1})

            # 追加协议编排流向节点。
            nodes.append({"id": "idle:protocol", "parent": "idle:configuration", "kind": "idle", "title": "协议编排", "detail": "登录 · 查询 · 分页", "diagnostics": "协议执行：等待任务参数\n执行方式：平台适配器直连\n运行状态：未启动", "status": "就绪", "level": 2, "order": 0})

            # 追加配置到协议编排的连线。
            edges.append({"from": "idle:configuration", "to": "idle:protocol", "level": 2})

            # 追加标准化导出流向节点。
            nodes.append({"id": "idle:delivery", "parent": "idle:protocol", "kind": "idle", "title": "标准化导出", "detail": "Excel · 命名 · 日志", "diagnostics": "文件输出：等待任务启动\n标准字段：接口原始字段保留\n日志输出：公共 PrintHandler", "status": "就绪", "level": 3, "order": 0})

            # 追加协议编排到标准化导出的连线。
            edges.append({"from": "idle:protocol", "to": "idle:delivery", "level": 3})

        # 初始化可见数据类型节点的连续布局序号。
        task_node_order = 0

        # 遍历并发槽位。
        for slot_order, slot_number in enumerate(sorted(self.worker_slots)):

            # 读取当前槽位状态。
            slot_state = self.worker_slots[slot_number]

            # 构建槽位节点标识。
            slot_id = f"slot:{slot_number}"

            # 追加槽位节点。
            nodes.append({"id": slot_id, "parent": "root", "kind": "slot", "title": f"并发槽位 {slot_number}", "detail": slot_state.get("company", "等待任务"), "diagnostics": f"槽位编号：{slot_number}\n状态：{slot_state.get('status', '空闲')}\n当前商业：{slot_state.get('company', '') or '等待任务'}", "status": slot_state.get("status", "空闲"), "level": 1, "order": slot_order})

            # 追加调度核心到槽位连线。
            edges.append({"from": "root", "to": slot_id, "level": 1})

        # 遍历当前可见真实商业拓扑。
        for company_order, company_name in enumerate(visible_company_names):

            # 读取当前商业状态。
            state = self.company_states.get(company_name, {})

            # 构建商业节点标识。
            company_id = f"company:{company_name}"

            # 查找当前商业真实占用槽位。
            slot_number = next((slot for slot, value in self.worker_slots.items() if value.get("company") == company_name), None)

            # 解析商业父节点标识。
            parent_id = f"slot:{slot_number}" if slot_number is not None else "root"

            # 汇总商业下已知数据类型的阶段状态。
            data_type_summaries = [f"{data_type}：{dict(state.get('taskStates', {}).get(data_type, {})).get('status', state.get('status', '等待'))} · {dict(state.get('taskStates', {}).get(data_type, {})).get('stage', state.get('stage', '等待'))}" for data_type in self.task_topology.get(company_name, [])]

            # 拼接商业节点可展开的诊断信息。
            company_diagnostics = f"商业：{company_name}\n平台：{state.get('platform', ACCOUNTS.get(company_name, {}).get('平台', ''))}\n状态：{state.get('status', '等待')}\n当前步骤：{state.get('stage', '等待')}\n记录数量：{state.get('recordCount', '') or '暂无'}\n最近事件：{state.get('lastMessage', '') or '等待执行'}\n子任务状态：{'；'.join(data_type_summaries) or '等待拓扑'}"

            # 追加商业节点。
            nodes.append({"id": company_id, "parent": parent_id, "kind": "company", "title": company_name, "detail": f"{state.get('platform', ACCOUNTS.get(company_name, {}).get('平台', ''))} · {state.get('stage', '等待')}", "diagnostics": company_diagnostics, "status": state.get("status", "等待"), "level": 2, "order": company_order})

            # 追加商业父子连线。
            edges.append({"from": parent_id, "to": company_id, "level": 2})

            # 遍历当前商业数据类型。
            for data_type in self.task_topology.get(company_name, []):

                # 读取当前数据类型的独立阶段状态。
                data_type_state = dict(state.get("taskStates", {}).get(data_type, {}))

                # 解析当前数据类型的节点展示状态。
                data_type_status = data_type_state.get("status", state.get("status", "等待"))

                # 解析当前数据类型的最近执行步骤。
                data_type_stage = data_type_state.get("stage", state.get("stage", "等待执行"))

                # 解析当前数据类型的最近记录数量。
                data_type_record_count = data_type_state.get("recordCount", state.get("recordCount", ""))

                # 解析当前数据类型的最近事件消息。
                data_type_message = data_type_state.get("message", "")

                # 拼接数据类型节点的完整诊断信息。
                data_type_diagnostics = f"商业：{company_name}\n数据类型：{data_type}\n状态：{data_type_status}\n当前步骤：{data_type_stage}\n记录数量：{data_type_record_count or '暂无'}\n最近事件：{data_type_message or '等待执行'}"

                # 构建数据类型节点标识。
                task_id = f"task:{company_name}:{data_type}"

                # 追加数据类型节点。
                nodes.append({"id": task_id, "parent": company_id, "kind": "task", "title": str(data_type), "detail": f"{data_type_stage} · {data_type_record_count}", "diagnostics": data_type_diagnostics, "status": data_type_status, "level": 3, "order": task_node_order})

                # 递增下一数据类型节点的连续布局序号。
                task_node_order += 1

                # 追加商业到数据类型连线。
                edges.append({"from": company_id, "to": task_id, "level": 3})

        # 判断存在尚未展开的待执行商业。
        if pending_count:

            # 定义待执行聚合节点标识。
            pending_id = "aggregate:pending"

            # 追加待执行商业聚合节点。
            nodes.append({"id": pending_id, "parent": "root", "kind": "aggregate", "title": f"待执行商业 · {pending_count}", "detail": "将在分配并发槽位时自动展开", "diagnostics": f"聚合商业数量：{pending_count}\n展开行为：点击后显示下一组商业\n分配规则：按可用并发槽位调度", "status": "等待", "level": 2, "order": len(visible_company_names)})

            # 追加调度核心到待执行聚合连线。
            edges.append({"from": "root", "to": pending_id, "level": 2})

        # 判断存在已完成历史聚合商业。
        if historical_count:

            # 定义已完成聚合节点标识。
            history_id = "aggregate:history"

            # 追加已完成商业聚合节点。
            nodes.append({"id": history_id, "parent": "root", "kind": "aggregate", "title": f"已完成商业 · {historical_count}", "detail": f"保留最近 {len(recent_completed_names)} 家真实节点", "diagnostics": f"聚合商业数量：{historical_count}\n当前保留：{len(recent_completed_names)} 家\n展开行为：点击后显示下一组历史商业", "status": "成功", "level": 2, "order": len(visible_company_names) + 1})

            # 追加调度核心到已完成聚合连线。
            edges.append({"from": "root", "to": history_id, "level": 2})

        # 读取当前网络模型生成时刻。
        entered_at_base_ms = int(time.time() * 1000)

        # 为首次出现的节点分配分层入场时间。
        for node in nodes:

            # 读取当前节点唯一标识。
            node_id = str(node["id"])

            # 读取当前节点已有入场时间。
            entered_at_ms = self.network_node_entered_at_ms.get(node_id)

            # 判断当前节点首次出现于网络模型。
            if entered_at_ms is None:

                # 计算当前节点在层级内的受限入场延迟。
                entered_at_delay_ms = int(node["level"]) * 210 + min(int(node["order"]), 7) * 72

                # 保存当前节点首次入场时间。
                entered_at_ms = entered_at_base_ms + entered_at_delay_ms

                # 写入节点入场时间索引。
                self.network_node_entered_at_ms[node_id] = entered_at_ms

            # 向 QML 节点模型公开稳定的入场时间。
            node["enteredAt"] = entered_at_ms

        # 判断当前拓扑与已发布模型是否完全一致。
        if nodes == getattr(self, "network_nodes", []) and edges == getattr(self, "network_edges", []):

            # 避免无变化网络模型触发 QML 重排与画布重绘。
            return

        # 保存新的网络节点集合。
        self.network_nodes = nodes

        # 保存新的网络连线集合。
        self.network_edges = edges

        # 发布网络模型变化信号。
        self.networkChanged.emit()

    # 定义任务网络节点聚焦方法。
    @Slot(str)
    def focusNetworkNode(self, node_id):

        """
        根据商业或聚合节点标识展开受限的真实任务网络节点。

        :param node_id: 当前点击的网络节点标识。
        :type node_id: str
        :return: None。
        :rtype: None
        """

        # 标准化当前网络节点标识。
        normalized_node_id = str(node_id or "")

        # 判断当前节点为待执行聚合节点。
        if normalized_node_id == "aggregate:pending":

            # 设置待执行商业聚合展开状态。
            self.network_focus_group = "pending"

        # 判断当前节点为历史商业聚合节点。
        elif normalized_node_id == "aggregate:history":

            # 设置已完成商业聚合展开状态。
            self.network_focus_group = "history"

        # 判断当前节点为商业节点。
        elif normalized_node_id.startswith("company:"):

            # 保存被聚焦的商业名称。
            self.network_focus_company = normalized_node_id.removeprefix("company:")

            # 清空聚合节点展开状态。
            self.network_focus_group = ""

        # 处理不支持聚焦的节点类型。
        else:

            # 结束当前节点聚焦。
            return

        # 重建受限任务网络模型。
        self.rebuild_network()

    # 定义提示文本设置方法。
    def set_notice(self, text):

        """
        更新界面底部的操作提示文本。

        :param text: 提示文本。
        :type text: str
        :return: None。
        :rtype: None
        """

        # 保存标准化提示文本。
        self.notice_text = str(text)

        # 发布提示文本变化信号。
        self.noticeChanged.emit()


# 定义项目根目录解析函数。
def get_project_root():

    """
    解析源码或 PyInstaller 打包运行环境的项目根目录。

    :return: 项目根目录。
    :rtype: str
    """

    # 判断当前运行在 PyInstaller 打包环境。
    if getattr(sys, "frozen", False):

        # 返回可执行文件所在目录。
        return os.path.dirname(os.path.abspath(sys.executable))

    # 返回当前源码文件所在目录。
    return os.path.dirname(os.path.abspath(__file__))


# 定义 QML 文件路径解析函数。
def resolve_qml_path(project_root):

    """
    解析源码与 PyInstaller 环境中的主 QML 文件路径。

    :param project_root: 项目根目录。
    :type project_root: str
    :return: 主 QML 文件路径。
    :rtype: str
    """

    # 判断当前运行在 PyInstaller 打包环境。
    if getattr(sys, "frozen", False):

        # 返回 PyInstaller 临时资源目录中的 QML 文件。
        return os.path.join(getattr(sys, "_MEIPASS", project_root), "ui", "Main.qml")

    # 返回源码目录中的 QML 文件。
    return os.path.join(project_root, "ui", "Main.qml")


# 定义 Qt GUI 启动函数。
def main():

    """
    创建 Qt Quick 应用、注入 ViewModel 并启动事件循环。

    :return: 进程退出码。
    :rtype: int
    """

    # 在 Controls 加载前固定使用可自定义的 Basic 风格。
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    # 通过 Qt API 固定控件样式，避免系统原生样式忽略 QML 外观定义。
    QQuickStyle.setStyle("Basic")

    # 保留系统缩放的原始分数比例，避免 125% 等高 DPI 环境出现二次取整模糊。
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 创建 Qt GUI 应用实例。
    application = QGuiApplication(sys.argv)

    # 设置 Qt 应用组织名称。
    application.setOrganizationName("DDI")

    # 设置 Qt 应用名称。
    application.setApplicationName("DDI 逆向神力")

    # 解析项目根目录。
    project_root = get_project_root()

    # 补齐缺失的受管目录与用途说明文件。
    ensure_directory_documents(project_root)

    # 创建 QML 展示 ViewModel。
    view_model = DdiGuiViewModel(project_root)

    # 创建 QML 应用引擎。
    engine = QQmlApplicationEngine()

    # 向 QML 注入展示 ViewModel。
    engine.rootContext().setContextProperty("ddiViewModel", view_model)

    # 加载主 QML 文件。
    engine.load(QUrl.fromLocalFile(resolve_qml_path(project_root)))

    # 判断 QML 根对象加载失败。
    if not engine.rootObjects():

        # 返回 QML 加载失败退出码。
        return 1

    # 为已创建的 QML 主窗口启用 Windows 原生毛玻璃。
    enable_native_glass(engine.rootObjects()[0])

    # 启动 Qt 事件循环。
    return application.exec()


# 判断当前模块是否被 PyCharm 或命令行直接执行。
if __name__ == "__main__":

    # 启动 Qt Quick 图形界面并返回进程退出码。
    raise SystemExit(main())
