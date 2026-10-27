# -*- coding: utf-8 -*-
"""
DDI 无界面公共任务运行时。

本模块将无界面任务请求连接到公共协议执行服务、授权校验、日志输出和 Excel 任务日志。
模块不导入终端入口、GUI 库或平台展示代码，终端与图形界面均可通过相同接口调用。
"""

# 导入操作系统路径模块。
import os

# 导入数据类定义工具。
from dataclasses import dataclass

# 导入账号配置与运行期开关函数。
from ddi_framework.account_config import ensure_runtime_account_config

# 导入有效账号配置构建函数。
from ddi_framework.account_config import get_effective_accounts

# 导入账号配置与运行期开关函数。
from ddi_framework.account_config import load_runtime_account_config

# 导入账号配置与运行期开关函数。
from ddi_framework.account_config import save_runtime_account_config

# 导入授权校验异常类型。
from ddi_framework.license_guard import LicenseError

# 导入运行环境授权校验函数。
from ddi_framework.license_guard import ensure_runtime_license

# 导入标准日志输出器。
from ddi_framework.print_handler import PrintHandler

# 导入无界面任务取消控制器。
from ddi_framework.task_core import TaskCancellation

# 导入无界面任务协调器。
from ddi_framework.task_core import TaskCoordinator

# 导入无界面任务事件接收接口。
from ddi_framework.task_core import TaskEventSink

# 导入无界面任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入无界面任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入无界面任务结果对象。
from ddi_framework.task_core import TaskResult

# 导入 Excel 任务日志记录器。
from ddi_framework.task_log import TaskExcelLogger

# 导入公共单商业协议执行函数。
from ddi_framework.task_execution import execute_company as execute_protocol_company

# 导入单商业数据类型解析函数。
from ddi_framework.task_execution import resolve_data_types


# 定义运行时执行结果对象。
@dataclass(frozen=True)
class RuntimeExecutionResult:

    """
    保存无界面运行时执行汇总与日志文件路径。

    :param task_result: 无界面任务协调结果。
    :type task_result: TaskResult
    :param log_path: Excel 任务日志路径。
    :type log_path: str
    """

    # 保存无界面任务协调结果。
    task_result: TaskResult

    # 保存 Excel 任务日志路径。
    log_path: str


# 定义无界面 DDI 运行时。
class DdiTaskRuntime:

    """
    执行公共 DDI 协议任务的无界面运行时。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :param event_sink: 可选的任务事件接收器。
    :type event_sink: TaskEventSink | None
    """

    # 定义运行时初始化方法。
    def __init__(self, project_root, event_sink=None):

        """
        初始化无界面 DDI 运行时。

        :param project_root: DDI 项目根目录。
        :type project_root: str
        :param event_sink: 可选的任务事件接收器。
        :type event_sink: TaskEventSink | None
        :return: None。
        :rtype: None
        """

        # 保存项目根目录绝对路径。
        self.project_root = os.path.abspath(str(project_root))

        # 保存可选的任务事件接收器。
        self.event_sink = event_sink

    # 定义任务执行方法。
    def execute(self, request, company_names, cancellation=None):

        """
        执行指定商业集合的 DDI 协议任务。

        :param request: 无界面任务请求。
        :type request: TaskRequest
        :param company_names: 需要执行的商业名称列表。
        :type company_names: list[str]
        :param cancellation: 任务取消控制器。
        :type cancellation: TaskCancellation | None
        :return: 运行时执行结果。
        :rtype: RuntimeExecutionResult
        """

        # 按输入顺序去除空值和重复商业名称。
        unique_names = list(dict.fromkeys([str(company_name) for company_name in company_names if str(company_name)]))

        # 校验本次任务是否选择商业。
        if not unique_names:

            # 抛出商业选择为空异常。
            raise ValueError("请至少选择一家商业后再执行任务")

        # 确保共享运行期启停配置存在。
        ensure_runtime_account_config(self.project_root)

        # 读取本次任务使用的运行期账号配置。
        effective_accounts = get_effective_accounts(self.project_root)

        # 创建本次任务的输出目录。
        os.makedirs(request.cookie_dir, exist_ok=True)

        # 创建本次任务的业务文件目录。
        os.makedirs(request.output_dir, exist_ok=True)

        # 创建本次任务的日志目录。
        os.makedirs(request.log_dir, exist_ok=True)

        # 初始化结构化日志打印器。
        printer = PrintHandler(path_mode=request.console_path_mode, project_root=self.project_root, event_sink=self.event_sink, console_output_enabled=request.console_output_enabled)

        # 定义脱敏阶段时间线事件发布函数。
        def publish_timeline(timeline_row):

            """
            将公共阶段记录转换为展示层可消费的结构化事件。

            :param timeline_row: 不含敏感路径的阶段时间线记录。
            :type timeline_row: dict
            :return: None。
            :rtype: None
            """

            # 跳过不存在事件接收器的运行环境。
            if self.event_sink is None:

                # 结束时间线事件发布。
                return

            # 发布当前阶段时间线事件。
            self.event_sink.publish(TaskEvent("task_timeline", str(timeline_row.get("执行说明", "阶段已完成")), str(timeline_row.get("执行状态", "信息")), str(timeline_row.get("商业名称", "")), str(timeline_row.get("数据类型", "")), dict(timeline_row)))

        # 初始化批量 Excel 任务日志记录器。
        task_logger = TaskExcelLogger(request.log_dir, request.start_date, request.end_date, task_action=request.action, task_data_type=request.data_type, realtime_save=False, timeline_listener=publish_timeline)

        # 汇总本次任务涉及的负责人。
        owner_names = sorted({effective_accounts[company_name].get("负责人", "") for company_name in unique_names if company_name in effective_accounts and effective_accounts[company_name].get("负责人", "")})

        # 构建本次任务的商业与数据类型拓扑。
        task_topology = {company_name: list(resolve_data_types(request.data_type, effective_accounts.get(company_name, {}))) for company_name in unique_names}

        # 判断当前运行环境订阅了结构化事件。
        if self.event_sink is not None:

            # 发布仅包含业务结构的任务拓扑事件。
            self.event_sink.publish(TaskEvent("task_topology", "任务拓扑已生成", "信息", payload={"商业数据类型": task_topology}))

        # 执行运行环境授权校验。
        try:

            # 校验本次任务负责人是否具有授权。
            license_result = ensure_runtime_license(self.project_root, required_owner_names=owner_names)

        # 处理授权校验失败。
        except LicenseError:

            # 继续抛出授权异常。
            raise

        # 发布授权校验成功日志。
        printer.info(printer.join(printer.kv("授权校验", license_result.get("授权状态", "成功"), "green"), printer.kv("本次负责人", "、".join(owner_names) or "不限制", "cyan")))

        # 定义单商业协议执行函数。
        def execute_company(company_name, account, core_request, core_cancellation):

            """
            调用公共业务执行函数完成单商业协议任务。

            :param company_name: 商业名称。
            :type company_name: str
            :param account: 商业账号配置。
            :type account: dict
            :param core_request: 无界面任务请求。
            :type core_request: TaskRequest
            :param core_cancellation: 任务取消控制器。
            :type core_cancellation: TaskCancellation
            :return: 单商业协议执行结果。
            :rtype: dict
            """

            # 发布商业开始执行日志。
            printer.info(printer.join(printer.kv("商业开始执行", company_name, "cyan"), printer.kv("平台", account.get("平台", ""), "yellow")))

            # 调用公共协议执行函数。
            return execute_protocol_company(company_name, account, core_request.cookie_dir, core_request.action, core_request.data_type, core_request.start_date, core_request.end_date, core_request.output_dir, printer, task_logger=task_logger, copy_excel_enabled=core_request.copy_excel)

        # 定义运行期配置读取函数。
        def load_runtime_config():

            """
            读取共享运行期启停配置。

            :return: 运行期启停配置。
            :rtype: dict
            """

            # 返回共享运行期启停配置。
            return load_runtime_account_config(self.project_root)

        # 定义运行期配置保存函数。
        def save_runtime_config(runtime_config):

            """
            保存共享运行期启停配置。

            :param runtime_config: 运行期启停配置。
            :type runtime_config: dict
            :return: 配置文件路径。
            :rtype: str
            """

            # 保存共享运行期启停配置。
            return save_runtime_account_config(runtime_config, self.project_root)

        # 初始化无界面任务协调器。
        coordinator = TaskCoordinator(effective_accounts, load_runtime_config, save_runtime_config, execute_company, self.event_sink)

        # 执行受控批量任务。
        task_result = coordinator.execute(request, unique_names, cancellation)

        # 保存本次 Excel 任务日志。
        log_path = task_logger.save()

        # 发布任务日志保存事件。
        coordinator.publish("task_log", "本次运行日志已保存", "成功", payload={"文件": log_path})

        # 返回运行时执行结果。
        return RuntimeExecutionResult(task_result, log_path)
