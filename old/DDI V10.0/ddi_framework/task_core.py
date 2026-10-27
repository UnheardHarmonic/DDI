# -*- coding: utf-8 -*-
"""
DDI 无界面任务协调层。

本模块定义终端和图形界面共用的任务请求、事件、筛选、快捷方案和受控批量调度能力。
模块不导入终端菜单、图形界面或平台适配器，以保证业务协调接口可被不同展示层复用。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入单调时钟模块。
import time

# 导入线程池执行器。
from concurrent.futures import FIRST_COMPLETED

# 导入线程池执行器。
from concurrent.futures import ThreadPoolExecutor

# 导入线程池等待函数。
from concurrent.futures import wait

# 导入数据类定义工具。
from dataclasses import dataclass

# 导入数据类字段工具。
from dataclasses import field

# 导入日期时间工具。
from datetime import datetime

# 导入线程事件工具。
from threading import Event

# 导入线程锁工具。
from threading import RLock

# 导入协议类型工具。
from typing import Callable

# 导入协议类型工具。
from typing import Protocol


# 定义 GUI 快捷方案文件名。
GUI_PRESET_FILE_NAME = "gui_presets.json"

# 定义 ANSI 控制序列匹配表达式。
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


# 定义 ANSI 控制序列清理函数。
def strip_ansi_escape_codes(text):

    """
    清理文本中的 ANSI 颜色和控制序列。

    :param text: 可能包含 ANSI 控制序列的原始文本。
    :type text: object
    :return: 不包含 ANSI 控制序列的纯文本。
    :rtype: str
    """

    # 转换输入值为文本。
    source_text = str(text or "")

    # 移除 ANSI 控制序列。
    return ANSI_ESCAPE_PATTERN.sub("", source_text)


# 定义推荐线程数构建函数。
def build_recommended_max_workers(runtime_profile, fallback_worker_count):

    """
    根据电脑逻辑核心数和物理内存构建推荐并发线程数。

    :param runtime_profile: 运行环境概览信息。
    :type runtime_profile: dict
    :param fallback_worker_count: 配置文件中的兜底线程数。
    :type fallback_worker_count: int
    :return: 推荐并发线程数。
    :rtype: int
    """

    # 读取逻辑核心数量。
    logical_cpu_count = int(runtime_profile.get("logical_cpu_count", 0) or 0)

    # 读取物理内存总量。
    total_memory_bytes = int(runtime_profile.get("total_memory_bytes", 0) or 0)

    # 判断逻辑核心数量是否无效。
    if logical_cpu_count <= 0:

        # 返回至少为一的兜底线程数。
        return max(1, int(fallback_worker_count or 1))

    # 构建基于 CPU 的线程上限。
    cpu_based_limit = min(max(2, logical_cpu_count), 12)

    # 计算物理内存吉字节数。
    total_memory_gb = float(total_memory_bytes) / float(1024 ** 3) if total_memory_bytes > 0 else 0.0

    # 判断当前电脑是否至少具备 32GB 内存。
    if total_memory_gb >= 32.0:

        # 设置高内存线程上限。
        memory_based_limit = 12

    # 判断当前电脑是否至少具备 16GB 内存。
    elif total_memory_gb >= 16.0:

        # 设置中高内存线程上限。
        memory_based_limit = 8

    # 判断当前电脑是否至少具备 8GB 内存。
    elif total_memory_gb >= 8.0:

        # 设置中等内存线程上限。
        memory_based_limit = 6

    # 判断当前电脑是否至少具备 4GB 内存。
    elif total_memory_gb >= 4.0:

        # 设置低内存线程上限。
        memory_based_limit = 4

    # 处理低内存电脑。
    else:

        # 设置低内存线程上限。
        memory_based_limit = 2

    # 计算最终推荐线程数。
    recommended_workers = min(cpu_based_limit, memory_based_limit)

    # 返回至少为一的推荐线程数。
    return max(1, recommended_workers)


# 定义平台首字母索引构建函数。
def build_platform_initial_index(accounts):

    """
    按首字母构建可用于 GUI 快速筛选的平台代码索引。

    :param accounts: 全量商业账号配置。
    :type accounts: dict
    :return: 首字母到平台代码列表的映射。
    :rtype: dict[str, list[str]]
    """

    # 初始化平台首字母索引。
    initial_index = {}

    # 遍历全部商业账号配置。
    for account in accounts.values():

        # 读取当前平台代码。
        platform_name = str(account.get("平台", "")).strip()

        # 判断平台代码是否为空。
        if not platform_name:

            # 跳过平台代码为空的账号。
            continue

        # 读取平台代码首字母。
        initial = platform_name[0].upper()

        # 初始化当前首字母的平台集合。
        initial_index.setdefault(initial, set())

        # 记录当前平台代码。
        initial_index[initial].add(platform_name)

    # 返回按首字母和平台代码排序后的索引。
    return {initial: sorted(platform_names) for initial, platform_names in sorted(initial_index.items())}


# 定义支持数据类型汇总函数。
def list_supported_data_types(accounts):

    """
    从账号配置汇总全部可由展示层选择的数据类型。

    :param accounts: 全量商业账号配置。
    :type accounts: dict
    :return: 包含全部选项的排序数据类型列表。
    :rtype: list[str]
    """

    # 初始化数据类型集合。
    data_types = set()

    # 遍历全部商业账号配置。
    for account in accounts.values():

        # 遍历当前商业声明的数据类型列表。
        for data_type in account.get("数据类型列表", []) or []:

            # 标准化当前数据类型文本。
            normalized_data_type = str(data_type).strip()

            # 判断当前数据类型是否有效。
            if normalized_data_type:

                # 记录当前有效数据类型。
                data_types.add(normalized_data_type)

    # 返回全部选项和排序后的数据类型。
    return ["全部"] + sorted(data_types)


# 定义跨展示层的任务请求对象。
@dataclass(frozen=True)
class TaskRequest:

    """
    描述一次 DDI 查询任务的无界面参数。

    :param action: 任务动作。
    :type action: str
    :param data_type: 数据类型参数。
    :type data_type: str
    :param start_date: 查询开始日期。
    :type start_date: str
    :param end_date: 查询结束日期。
    :type end_date: str
    :param cookie_dir: Cookie 输出目录。
    :type cookie_dir: str
    :param output_dir: 业务文件输出目录。
    :type output_dir: str
    :param log_dir: Excel 任务日志目录。
    :type log_dir: str
    :param max_workers: 最大并发商业数量。
    :type max_workers: int
    :param copy_excel: 是否生成复制用 Excel。
    :type copy_excel: bool
    :param console_path_mode: 路径展示模式。
    :type console_path_mode: str
    :param console_output_enabled: 是否镜像结构化日志到标准输出。
    :type console_output_enabled: bool
    """

    # 保存任务动作。
    action: str

    # 保存数据类型参数。
    data_type: str

    # 保存查询开始日期。
    start_date: str

    # 保存查询结束日期。
    end_date: str

    # 保存 Cookie 输出目录。
    cookie_dir: str

    # 保存业务文件输出目录。
    output_dir: str

    # 保存 Excel 任务日志目录。
    log_dir: str

    # 保存最大并发商业数量。
    max_workers: int

    # 保存复制用 Excel 开关。
    copy_excel: bool = True

    # 保存控制台路径展示模式。
    console_path_mode: str = "relative"

    # 保存标准输出镜像开关。
    console_output_enabled: bool = True


# 定义跨展示层的任务事件对象。
@dataclass(frozen=True)
class TaskEvent:

    """
    描述任务协调层或日志层发出的结构化事件。

    :param event_type: 事件分类。
    :type event_type: str
    :param message: 事件说明。
    :type message: str
    :param status: 事件状态。
    :type status: str
    :param company_name: 关联商业名称。
    :type company_name: str
    :param data_type: 关联数据类型。
    :type data_type: str
    :param payload: 事件扩展数据。
    :type payload: dict
    :param created_at: 事件生成时间。
    :type created_at: datetime
    """

    # 保存事件分类。
    event_type: str

    # 保存事件说明。
    message: str

    # 保存事件状态。
    status: str = "信息"

    # 保存关联商业名称。
    company_name: str = ""

    # 保存关联数据类型。
    data_type: str = ""

    # 保存事件扩展数据。
    payload: dict = field(default_factory=dict)

    # 保存事件生成时间。
    created_at: datetime = field(default_factory=datetime.now)


# 定义任务完成汇总对象。
@dataclass
class TaskResult:

    """
    汇总一次多商业任务的执行结果。

    :param total_count: 计划执行商业数量。
    :type total_count: int
    :param success_count: 成功商业数量。
    :type success_count: int
    :param failure_count: 失败商业数量。
    :type failure_count: int
    :param stopped_count: 未启动即停止的商业数量。
    :type stopped_count: int
    :param company_results: 商业执行结果集合。
    :type company_results: dict
    :param errors: 商业失败原因集合。
    :type errors: dict
    """

    # 保存计划执行商业数量。
    total_count: int

    # 保存成功商业数量。
    success_count: int = 0

    # 保存失败商业数量。
    failure_count: int = 0

    # 保存未启动即停止的商业数量。
    stopped_count: int = 0

    # 保存商业执行结果集合。
    company_results: dict = field(default_factory=dict)

    # 保存商业失败原因集合。
    errors: dict = field(default_factory=dict)


# 定义任务事件接收接口。
class TaskEventSink(Protocol):

    """
    接收 DDI 任务结构化事件的展示层接口。

    :return: None。
    :rtype: None
    """

    # 定义事件发布接口。
    def publish(self, event: TaskEvent):

        """
        接收一条任务事件。

        :param event: 任务事件对象。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        ...


# 定义空任务事件接收器。
class NullTaskEventSink:

    """
    丢弃任务事件的默认接收器。

    :return: None。
    :rtype: None
    """

    # 定义事件丢弃方法。
    def publish(self, event: TaskEvent):

        """
        丢弃任务事件。

        :param event: 任务事件对象。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        # 显式忽略未订阅的事件。
        return None


# 定义线程安全的任务取消控制器。
class TaskCancellation:

    """
    控制受控队列是否继续提交尚未开始的商业任务。

    :return: None。
    :rtype: None
    """

    # 定义取消控制器初始化方法。
    def __init__(self):

        """
        初始化线程安全的停止事件。

        :return: None。
        :rtype: None
        """

        # 创建线程停止信号。
        self._event = Event()

    # 定义停止请求方法。
    def request_stop(self):

        """
        请求停止未开始的商业任务。

        :return: None。
        :rtype: None
        """

        # 设置线程停止信号。
        self._event.set()

    # 定义停止状态读取方法。
    def is_stop_requested(self):

        """
        读取是否已请求停止。

        :return: 是否停止提交后续任务。
        :rtype: bool
        """

        # 返回停止信号状态。
        return self._event.is_set()


# 定义 GUI 快捷方案路径解析函数。
def resolve_gui_preset_path(project_root):

    """
    解析 GUI 快捷方案配置文件路径。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :return: 快捷方案配置文件绝对路径。
    :rtype: str
    """

    # 拼接共享配置目录中的快捷方案文件路径。
    return os.path.join(str(project_root), "config", GUI_PRESET_FILE_NAME)


# 定义 GUI 快捷方案读取函数。
def load_gui_presets(project_root):

    """
    读取 GUI 快捷方案配置。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :return: 按名称索引的快捷方案集合。
    :rtype: dict
    """

    # 解析快捷方案配置文件路径。
    preset_path = resolve_gui_preset_path(project_root)

    # 判断快捷方案文件是否存在。
    if not os.path.exists(preset_path):

        # 返回空快捷方案集合。
        return {}

    # 打开快捷方案文件。
    with open(preset_path, "r", encoding="utf-8") as file_obj:

        # 读取 JSON 配置内容。
        preset_data = json.load(file_obj)

    # 判断 JSON 根对象是否为字典。
    if not isinstance(preset_data, dict):

        # 返回空快捷方案集合。
        return {}

    # 读取方案集合字段。
    preset_map = preset_data.get("快捷方案", {})

    # 判断方案集合是否为字典。
    if not isinstance(preset_map, dict):

        # 返回空快捷方案集合。
        return {}

    # 返回方案集合副本。
    return dict(preset_map)


# 定义 GUI 快捷方案保存函数。
def save_gui_presets(project_root, preset_map):

    """
    保存 GUI 快捷方案配置。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :param preset_map: 按名称索引的快捷方案集合。
    :type preset_map: dict
    :return: 快捷方案配置文件绝对路径。
    :rtype: str
    """

    # 解析快捷方案配置文件路径。
    preset_path = resolve_gui_preset_path(project_root)

    # 创建共享配置目录。
    os.makedirs(os.path.dirname(preset_path), exist_ok=True)

    # 构建规范化配置内容。
    preset_data = {"快捷方案": dict(preset_map)}

    # 打开快捷方案文件。
    with open(preset_path, "w", encoding="utf-8") as file_obj:

        # 写入 UTF-8 格式的 JSON 配置。
        json.dump(preset_data, file_obj, ensure_ascii=False, indent=2)

    # 返回保存后的配置文件路径。
    return preset_path


# 定义商业筛选函数。
def filter_company_names(accounts, keyword="", owner_name="", region_name="", province_name="", platform_name="", runtime_enabled_map=None, status_filter=""):

    """
    按组织维度、平台和名称关键字筛选商业。

    :param accounts: 全量商业账号配置。
    :type accounts: dict
    :param keyword: 商业名称模糊匹配关键字。
    :type keyword: str
    :param owner_name: 负责人筛选值。
    :type owner_name: str
    :param region_name: 大区筛选值。
    :type region_name: str
    :param province_name: 省份筛选值。
    :type province_name: str
    :param platform_name: 平台筛选值。
    :type platform_name: str
    :param runtime_enabled_map: 运行期商业启停映射。
    :type runtime_enabled_map: dict | None
    :param status_filter: 商业启停状态筛选值，支持“已启用”或“已停用”。
    :type status_filter: str
    :return: 满足全部条件的商业名称列表。
    :rtype: list[str]
    """

    # 标准化名称关键字。
    normalized_keyword = str(keyword).strip().lower()

    # 初始化筛选结果列表。
    selected_names = []

    # 标准化运行期启停映射。
    enabled_map = runtime_enabled_map if isinstance(runtime_enabled_map, dict) else {}

    # 标准化商业状态筛选值。
    normalized_status = str(status_filter or "").strip()

    # 遍历全部商业账号配置。
    for company_name, account in accounts.items():

        # 判断负责人是否匹配。
        if owner_name and account.get("负责人", "") != owner_name:

            # 跳过负责人不匹配的商业。
            continue

        # 判断大区是否匹配。
        if region_name and account.get("大区", "") != region_name:

            # 跳过大区不匹配的商业。
            continue

        # 判断省份是否匹配。
        if province_name and account.get("省份", "") != province_name:

            # 跳过省份不匹配的商业。
            continue

        # 判断平台是否匹配。
        if platform_name and account.get("平台", "") != platform_name:

            # 跳过平台不匹配的商业。
            continue

        # 读取当前商业的有效启用状态。
        enabled_status = bool(enabled_map.get(company_name, account.get("启用", True)))

        # 跳过未满足启用状态筛选的商业。
        if normalized_status == "已启用" and not enabled_status:

            # 继续检查下一家商业。
            continue

        # 跳过未满足停用状态筛选的商业。
        if normalized_status == "已停用" and enabled_status:

            # 继续检查下一家商业。
            continue

        # 判断商业名称是否包含关键字。
        if normalized_keyword and normalized_keyword not in company_name.lower():

            # 跳过名称不匹配的商业。
            continue

        # 追加满足全部条件的商业名称。
        selected_names.append(company_name)

    # 返回保持账号配置顺序的筛选结果。
    return selected_names


# 定义受控批量任务协调器。
class TaskCoordinator:

    """
    通过注入的商业执行函数协调多商业任务。

    :param accounts: 全量商业账号配置。
    :type accounts: dict
    :param runtime_config_loader: 运行期启停配置读取函数。
    :type runtime_config_loader: Callable[[], dict]
    :param runtime_config_saver: 运行期启停配置保存函数。
    :type runtime_config_saver: Callable[[dict], str]
    :param company_worker: 单商业执行函数。
    :type company_worker: Callable[[str, dict, TaskRequest, TaskCancellation], object]
    :param event_sink: 任务事件接收器。
    :type event_sink: TaskEventSink | None
    """

    # 定义任务协调器初始化方法。
    def __init__(self, accounts, runtime_config_loader, runtime_config_saver, company_worker, event_sink=None):

        """
        初始化无界面任务协调器。

        :param accounts: 全量商业账号配置。
        :type accounts: dict
        :param runtime_config_loader: 运行期启停配置读取函数。
        :type runtime_config_loader: Callable[[], dict]
        :param runtime_config_saver: 运行期启停配置保存函数。
        :type runtime_config_saver: Callable[[dict], str]
        :param company_worker: 单商业执行函数。
        :type company_worker: Callable[[str, dict, TaskRequest, TaskCancellation], object]
        :param event_sink: 任务事件接收器。
        :type event_sink: TaskEventSink | None
        :return: None。
        :rtype: None
        """

        # 保存全量商业账号配置。
        self.accounts = accounts

        # 保存运行期启停配置读取函数。
        self.runtime_config_loader = runtime_config_loader

        # 保存运行期启停配置保存函数。
        self.runtime_config_saver = runtime_config_saver

        # 保存单商业执行函数。
        self.company_worker = company_worker

        # 保存事件接收器或使用空接收器。
        self.event_sink = event_sink or NullTaskEventSink()

        # 初始化运行状态锁。
        self._lock = RLock()

    # 定义事件发布方法。
    def publish(self, event_type, message, status="信息", company_name="", data_type="", payload=None):

        """
        发布一条结构化任务事件。

        :param event_type: 事件分类。
        :type event_type: str
        :param message: 事件说明。
        :type message: str
        :param status: 事件状态。
        :type status: str
        :param company_name: 关联商业名称。
        :type company_name: str
        :param data_type: 关联数据类型。
        :type data_type: str
        :param payload: 事件扩展数据。
        :type payload: dict | None
        :return: None。
        :rtype: None
        """

        # 构建标准任务事件对象。
        event = TaskEvent(event_type, str(message), str(status), str(company_name), str(data_type), dict(payload or {}))

        # 向展示层发布任务事件。
        self.event_sink.publish(event)

    # 定义选中商业启用持久化方法。
    def enable_selected_companies(self, company_names):

        """
        将本次明确选中的商业持久化为启用状态。

        :param company_names: 需要启用的商业名称列表。
        :type company_names: list[str]
        :return: 更新后的运行期配置文件路径。
        :rtype: str
        """

        # 读取当前运行期配置。
        runtime_config = self.runtime_config_loader() or {}

        # 读取已有商业启停配置。
        enabled_map = runtime_config.get("商业启停", {})

        # 判断商业启停配置是否为字典。
        if not isinstance(enabled_map, dict):

            # 使用空商业启停配置。
            enabled_map = {}

        # 遍历明确选中的商业名称。
        for company_name in company_names:

            # 写入当前商业的永久启用状态。
            enabled_map[company_name] = True

        # 写回商业启停配置。
        runtime_config["商业启停"] = enabled_map

        # 保存更新后的运行期配置。
        config_path = self.runtime_config_saver(runtime_config)

        # 发布启停配置持久化事件。
        self.publish("runtime_config", "已持久化本次勾选商业的启用状态", "成功", payload={"配置文件": config_path, "商业数量": len(company_names)})

        # 返回运行期配置文件路径。
        return config_path

    # 定义任务执行方法。
    def execute(self, request, company_names, cancellation=None):

        """
        执行指定商业集合并安全停止后续排队任务。

        :param request: 无界面任务请求。
        :type request: TaskRequest
        :param company_names: 需要执行的商业名称列表。
        :type company_names: list[str]
        :param cancellation: 任务取消控制器。
        :type cancellation: TaskCancellation | None
        :return: 批量任务执行汇总。
        :rtype: TaskResult
        """

        # 按输入顺序去除重复商业名称。
        unique_names = list(dict.fromkeys([str(company_name) for company_name in company_names if str(company_name)]))

        # 校验本次任务是否选择商业。
        if not unique_names:

            # 抛出商业选择为空异常。
            raise ValueError("请至少选择一家商业后再执行任务")

        # 校验全部商业名称均已配置。
        unknown_names = [company_name for company_name in unique_names if company_name not in self.accounts]

        # 判断是否存在未配置商业。
        if unknown_names:

            # 抛出商业名称不存在异常。
            raise ValueError(f"商业配置不存在：{','.join(unknown_names)}")

        # 使用默认取消控制器补齐空值。
        cancellation = cancellation or TaskCancellation()

        # 将明确选择的商业永久启用。
        self.enable_selected_companies(unique_names)

        # 构建任务汇总对象。
        result = TaskResult(total_count=len(unique_names))

        # 记录任务队列启动时刻。
        queue_started_at = time.monotonic()

        # 读取有效最大并发数。
        worker_count = max(1, min(int(request.max_workers), len(unique_names)))

        # 发布任务开始事件。
        self.publish("task_started", "批量任务已开始", "信息", payload={"商业数量": len(unique_names), "商业名称列表": list(unique_names), "最大并发": worker_count, "并发槽位列表": list(range(1, worker_count + 1)), "完成": 0, "总数": result.total_count, "成功": 0, "失败": 0, "运行中": 0, "待提交": len(unique_names), "耗时秒": 0.0})

        # 初始化尚未提交的商业名称列表。
        pending_names = list(unique_names)

        # 初始化任务与商业名称和并发槽位映射。
        future_map = {}

        # 初始化可分配的真实并发槽位集合。
        available_slots = list(range(1, worker_count + 1))

        # 创建受控并发执行器。
        with ThreadPoolExecutor(max_workers=worker_count) as executor:

            # 在存在待提交或运行中任务时持续调度。
            while pending_names or future_map:

                # 在未请求停止时补齐可用执行槽位。
                while pending_names and len(future_map) < worker_count and not cancellation.is_stop_requested():

                    # 读取下一个待执行商业名称。
                    company_name = pending_names.pop(0)

                    # 分配当前商业实际占用的并发槽位。
                    worker_slot = available_slots.pop(0)

                    # 读取当前商业账号配置。
                    account = self.accounts[company_name]

                    # 发布任务进入队列事件。
                    self.publish("company_queued", "商业任务已提交", "等待", company_name, request.data_type, {"并发槽位": worker_slot})

                    # 定义当前商业的受控执行包装函数。
                    def execute_started_company(current_name=company_name, current_account=account, current_slot=worker_slot):

                        """
                        发布商业实际开始事件后执行公共商业任务。

                        :return: 单商业执行结果。
                        :rtype: dict
                        """

                        # 发布商业实际开始执行事件。
                        self.publish("company_started", "商业任务开始执行", "运行中", current_name, request.data_type, {"并发槽位": current_slot})

                        # 执行公共商业任务。
                        return self.company_worker(current_name, current_account, request, cancellation)

                    # 提交当前商业任务。
                    future = executor.submit(execute_started_company)

                    # 保存任务与商业名称映射。
                    future_map[future] = (company_name, worker_slot)

                # 判断是否已请求停止且仍有未提交商业。
                if cancellation.is_stop_requested() and pending_names:

                    # 保存未启动商业数量。
                    result.stopped_count += len(pending_names)

                    # 遍历未启动商业名称。
                    for company_name in pending_names:

                        # 发布未启动即停止事件。
                        self.publish("company_stopped", "任务停止，商业未开始执行", "停止", company_name, request.data_type, {"并发槽位": None})

                    # 清空未提交商业列表。
                    pending_names.clear()

                # 判断当前是否仍有运行中任务。
                if not future_map:

                    # 结束本轮受控调度。
                    continue

                # 等待至少一个商业任务完成。
                done_futures, _ = wait(set(future_map.keys()), timeout=0.2, return_when=FIRST_COMPLETED)

                # 判断本轮是否没有完成任务。
                if not done_futures:

                    # 发布队列进度事件。
                    self.publish("task_progress", "任务队列运行中", "信息", payload={"完成": result.success_count + result.failure_count, "总数": result.total_count, "成功": result.success_count, "失败": result.failure_count, "停止": result.stopped_count, "运行中": len(future_map), "待提交": len(pending_names), "耗时秒": round(time.monotonic() - queue_started_at, 1)})

                    # 继续等待下一轮任务状态。
                    continue

                # 遍历已完成任务。
                for future in done_futures:

                    # 读取对应商业名称。
                    company_name, worker_slot = future_map.pop(future)

                    # 捕获商业执行结果。
                    try:

                        # 读取商业执行结果。
                        company_result = future.result()

                        # 保存商业执行结果。
                        result.company_results[company_name] = company_result

                        # 累加成功商业数量。
                        result.success_count += 1

                        # 发布商业成功事件。
                        self.publish("company_finished", "商业任务执行完成", "成功", company_name, request.data_type, {"完成": result.success_count + result.failure_count, "总数": result.total_count, "并发槽位": worker_slot})

                    # 处理商业执行异常。
                    except Exception as error:

                        # 保存商业失败原因。
                        result.errors[company_name] = str(error)

                        # 累加失败商业数量。
                        result.failure_count += 1

                        # 发布商业失败事件。
                        self.publish("company_finished", str(error), "失败", company_name, request.data_type, {"完成": result.success_count + result.failure_count, "总数": result.total_count, "并发槽位": worker_slot})

                    # 归还已完成商业占用的并发槽位。
                    available_slots.append(worker_slot)

                    # 保持可分配槽位的稳定排序。
                    available_slots.sort()

                    # 发布完成商业后的队列进度事件。
                    self.publish("task_progress", "任务队列运行中", "信息", payload={"完成": result.success_count + result.failure_count, "总数": result.total_count, "成功": result.success_count, "失败": result.failure_count, "停止": result.stopped_count, "运行中": len(future_map), "待提交": len(pending_names), "耗时秒": round(time.monotonic() - queue_started_at, 1)})

        # 发布任务完成事件。
        self.publish("task_finished", "批量任务已结束", "成功" if result.failure_count == 0 else "警告", payload={"完成": result.success_count + result.failure_count, "总数": result.total_count, "成功": result.success_count, "失败": result.failure_count, "停止": result.stopped_count, "运行中": 0, "待提交": 0, "耗时秒": round(time.monotonic() - queue_started_at, 1)})

        # 返回任务执行汇总。
        return result
