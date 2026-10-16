# -*- coding: utf-8 -*-
"""
DDI 协议直连任务入口。

本模块负责读取全局任务参数、选择商业账号、派发平台适配器，并统一控制登录、查询、导出和本地落地流程。
"""

# 导入命令行参数解析模块。
import argparse

# 导入 JSON 序列化模块。
import json

# 导入操作系统路径与目录模块。
import os

# 导入平台信息模块。
import platform

# 导入进程退出码模块。
import sys

# 导入日期时间模块。
from datetime import datetime

# 导入单调时钟模块。
import time

# 导入异常堆栈格式化模块。
import traceback


# 定义 Python 运行环境校验函数。
def validate_python_runtime():

    """
    校验当前 Python 解释器与二进制扩展模块版本是否一致。

    :return: None。
    :rtype: None
    """

    # 捕获标准库二进制扩展导入异常。
    try:

        # 导入套接字底层扩展模块。
        import _socket

    # 处理解释器与二进制扩展版本冲突。
    except ImportError as error:

        # 构建解释器版本文本。
        version_text = ".".join(str(version_part) for version_part in sys.version_info[:3])

        # 构建错误说明文本。
        message = "\n".join([
            "Python 运行环境异常：当前解释器与已加载的标准库二进制扩展版本不一致。",
            f"当前解释器: {sys.executable}",
            f"当前版本: {version_text}",
            "处理方式: 在 PyCharm 运行配置中选择同一套 Python 解释器，并清空 PYTHONPATH/PYTHONHOME 中指向其他 Python 版本的路径。",
            f"原始错误: {error}",
        ])

        # 抛出运行环境异常。
        raise RuntimeError(message) from error


# 校验 Python 运行环境。
validate_python_runtime()

# 导入账号配置字典、读取函数和运行期配置函数。
from ddi_framework.account_config import ACCOUNTS, ensure_runtime_account_config, filter_account_names_by_dimension, get_account, iter_enabled_accounts, list_account_dimension_values, load_runtime_account_config, resolve_runtime_enabled, save_runtime_account_config

# 导入硬件信息采集函数。
from ddi_framework.hardware_profile import read_hardware_profile

# 导入授权校验异常类型。
from ddi_framework.license_guard import LicenseError

# 导入运行授权校验函数。
from ddi_framework.license_guard import ensure_runtime_license

# 导入标准日志打印器。
from ddi_framework.print_handler import PrintHandler

# 导入启动像素头像打印函数。
from ddi_framework.startup_avatar_art import print_startup_avatar_art

# 导入当前版本启动更新日志读取函数。
from ddi_framework.startup_changelog import get_current_startup_changelog

# 导入受管目录说明自动补齐函数。
from ddi_framework.directory_docs import ensure_directory_documents

# 导入全局任务配置读取函数。
from ddi_framework.task_config import get_task_config

# 导入共享推荐线程数构建函数。
from ddi_framework.task_core import build_recommended_max_workers as build_shared_recommended_max_workers

# 导入统一日期范围对象。
from ddi_framework.task_core import DateRangeSpec

# 导入公共任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入统一无界面任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入 Excel 任务日志记录器。
from ddi_framework.task_log import TaskExcelLogger

# 导入公共任务日志记录函数。
from ddi_framework.task_execution import record_task_log

# 导入公共异常阶段解析函数。
from ddi_framework.task_execution import resolve_error_stage

# 导入公共无界面任务运行时。
from ddi_framework.task_runtime import DdiTaskRuntime

# 导入 Colorama 控制台兼容初始化函数。
from colorama import init as colorama_init


# 定义终端任务事件接收器。
class TerminalTaskEventSink:

    """
    将公共任务协调进度映射为终端动态状态行。

    :param printer: 终端标准日志输出器。
    :type printer: PrintHandler
    :return: None。
    :rtype: None
    """

    # 定义终端事件接收器初始化方法。
    def __init__(self, printer):

        """
        保存终端进度展示需要使用的日志输出器。

        :param printer: 终端标准日志输出器。
        :type printer: PrintHandler
        :return: None。
        :rtype: None
        """

        # 保存终端日志输出器。
        self.printer = printer

    # 定义公共任务事件接收方法。
    def publish(self, event):

        """
        仅将批量调度事件映射为终端动态进度，避免重复输出协议日志。

        :param event: 公共任务层发布的结构化任务事件。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        # 忽略非批量调度事件，协议日志仍由公共 PrintHandler 输出。
        if event.event_type not in {"task_started", "task_progress", "task_finished"}:

            # 结束当前非调度事件处理。
            return

        # 读取公共协调器提供的进度载荷。
        payload = dict(event.payload or {})

        # 读取当前已完成商业数量。
        completed_count = int(payload.get("完成", 0) or 0)

        # 读取当前商业总数量。
        total_count = int(payload.get("总数", payload.get("商业数量", 0)) or 0)

        # 读取当前成功商业数量。
        success_count = int(payload.get("成功", 0) or 0)

        # 读取当前失败商业数量。
        failure_count = int(payload.get("失败", 0) or 0)

        # 读取当前停止商业数量。
        stopped_count = int(payload.get("停止", 0) or 0)

        # 构建终端动态任务进度文本。
        progress_text = f"任务队列 {completed_count}/{total_count} 家｜成功 {success_count}｜失败 {failure_count}｜停止 {stopped_count}"

        # 判断当前事件表示批量任务结束。
        if event.event_type == "task_finished":

            # 清理终端已有的动态状态行。
            self.printer.clear_live_status()

            # 输出终端可追溯的最终批量汇总。
            self.printer.info(progress_text)

            # 结束当前最终状态处理。
            return

        # 刷新终端底部动态进度行。
        self.printer.live_status(progress_text)


# 定义交互菜单颜色编码映射。
MENU_COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

# 定义交互菜单颜色包装函数。
def menu_color(text, color):

    """
    构建交互菜单彩色文本。

    :param text: 原始文本。
    :type text: object
    :param color: 颜色名称。
    :type color: str
    :return: 彩色文本。
    :rtype: str
    """

    # 读取颜色编码。
    color_code = MENU_COLORS.get(color, "")

    # 读取颜色重置编码。
    reset_code = MENU_COLORS["reset"]

    # 返回颜色包装后的文本。
    return f"{color_code}{text}{reset_code}"


# 定义交互菜单标题打印函数。
def print_menu_title(title, detail=""):

    """
    打印交互菜单标题。

    :param title: 标题文本。
    :type title: str
    :param detail: 标题说明。
    :type detail: str
    :return: None。
    :rtype: None
    """

    # 构建标题分隔线。
    separator = "─" * 72

    # 输出标题前置空行。
    print()

    # 输出标题上边界。
    print(menu_color(separator, "gray"))

    # 输出标题文本。
    print(menu_color(title, "cyan"))

    # 判断是否存在标题说明。
    if detail:

        # 输出标题说明。
        print(menu_color(detail, "gray"))

    # 输出标题下边界。
    print(menu_color(separator, "gray"))


# 定义交互菜单选项打印函数。
def print_menu_options(title, options):

    """
    打印交互菜单选项集合。

    :param title: 选项组标题。
    :type title: str
    :param options: 选项键值列表。
    :type options: list[tuple[str, str]]
    :return: None。
    :rtype: None
    """

    # 打印选项组标题。
    print_menu_title(title)

    # 遍历选项键值列表。
    for option_key, option_text in options:

        # 构建选项序号文本。
        key_text = menu_color(option_key, "yellow")

        # 输出当前选项。
        print(f"  {key_text}  {option_text}")


# 定义交互菜单状态标签构建函数。
def build_menu_status_label(enabled_status):

    """
    构建商业启停状态标签。

    :param enabled_status: 商业启用状态。
    :type enabled_status: bool
    :return: 彩色状态标签。
    :rtype: str
    """

    # 构建状态文本。
    status_text = "启用" if enabled_status else "停用"

    # 构建状态颜色。
    status_color = "green" if enabled_status else "red"

    # 返回彩色状态标签。
    return menu_color(f"[{status_text}]", status_color)


# 定义交互菜单提示打印函数。
def print_menu_message(status_text, message, color):

    """
    打印交互菜单状态提示。

    :param status_text: 状态文本。
    :type status_text: str
    :param message: 提示内容。
    :type message: str
    :param color: 状态颜色。
    :type color: str
    :return: None。
    :rtype: None
    """

    # 构建状态标签。
    status_label = menu_color(f"[{status_text}]", color)

    # 输出状态提示。
    print(f"{status_label} {message}")


# 定义交互菜单硬件字段打印函数。
def print_menu_runtime_detail(label, value, color="cyan"):

    """
    在交互菜单中打印单个运行环境字段。

    :param label: 字段标签。
    :type label: str
    :param value: 字段取值。
    :type value: object
    :param color: 字段颜色。
    :type color: str
    :return: None。
    :rtype: None
    """

    # 判断字段值是否为空。
    if not value:

        # 使用未知文本兜底。
        value = "未知"

    # 打印字段标签和值。
    print(f"  {menu_color(label, 'gray')}  {menu_color(value, color)}")


# 定义交互菜单硬件列表打印函数。
def print_menu_runtime_list(label, values, color="cyan"):

    """
    在交互菜单中打印列表型运行环境字段。

    :param label: 字段标签。
    :type label: str
    :param values: 字段值列表。
    :type values: list[str]
    :param color: 字段颜色。
    :type color: str
    :return: None。
    :rtype: None
    """

    # 读取非空字段值列表。
    cleaned_values = [str(item) for item in values if item]

    # 判断字段值列表是否为空。
    if not cleaned_values:

        # 打印未知字段。
        print_menu_runtime_detail(label, "未知", color)

        # 返回空结果。
        return None

    # 遍历字段值列表。
    for index, item_text in enumerate(cleaned_values, start=1):

        # 构建当前字段标签。
        item_label = label if index == 1 else f"{label}{index}"

        # 打印当前字段。
        print_menu_runtime_detail(item_label, item_text, color)

    # 返回空结果。
    return None


# 定义交互菜单运行环境概览打印函数。
def print_menu_runtime_profile(runtime_profile, recommended_max_workers):

    """
    在交互菜单中打印当前电脑运行环境概览。

    :param runtime_profile: 运行环境概览信息。
    :type runtime_profile: dict
    :param recommended_max_workers: 推荐线程数。
    :type recommended_max_workers: int
    :return: None。
    :rtype: None
    """

    # 打印运行环境概览标题。
    print_menu_title("运行环境概览", "启动自检")

    # 打印主机名称。
    print(f"  {menu_color('主机名称', 'gray')}  {menu_color(runtime_profile.get('machine_name', '未知'), 'cyan')}")

    # 打印操作系统。
    print(f"  {menu_color('操作系统', 'gray')}  {menu_color(runtime_profile.get('system_text', '未知'), 'cyan')}")

    # 打印 Python 版本。
    print(f"  {menu_color('解释器', 'gray')}  {menu_color(runtime_profile.get('python_text', '未知'), 'cyan')}")

    # 打印整机型号。
    print_menu_runtime_detail("整机型号", runtime_profile.get("computer_text", ""), "cyan")

    # 打印主板型号。
    print_menu_runtime_detail("主板型号", runtime_profile.get("baseboard_text", ""), "cyan")

    # 打印 BIOS 信息。
    print_menu_runtime_detail("BIOS", runtime_profile.get("bios_text", ""), "cyan")

    # 打印 CPU 型号。
    print_menu_runtime_detail("CPU 型号", runtime_profile.get("cpu_name", "未知"), "cyan")

    # 打印逻辑核心数量。
    print(f"  {menu_color('逻辑核心', 'gray')}  {menu_color(runtime_profile.get('logical_cpu_count', 1), 'yellow')}")

    # 打印物理内存总量。
    print(f"  {menu_color('物理内存', 'gray')}  {menu_color(format_bytes_text(runtime_profile.get('total_memory_bytes', 0)), 'green')}")

    # 打印内存装机容量。
    print_menu_runtime_detail("内存装机", runtime_profile.get("memory_installed_text", ""), "green")

    # 打印内存条型号。
    print_menu_runtime_list("内存条", runtime_profile.get("memory_module_texts", []), "green")

    # 打印显卡型号。
    print_menu_runtime_list("显卡", runtime_profile.get("gpu_texts", []), "cyan")

    # 打印磁盘型号。
    print_menu_runtime_list("磁盘", runtime_profile.get("disk_texts", []), "cyan")

    # 打印网卡型号。
    print_menu_runtime_list("网卡", runtime_profile.get("network_texts", []), "cyan")

    # 打印显示器型号。
    print_menu_runtime_list("显示器", runtime_profile.get("monitor_texts", []), "cyan")

    # 打印电池信息。
    print_menu_runtime_list("电池", runtime_profile.get("battery_texts", []) or ["未检测到电池"], "yellow")

    # 打印声卡信息。
    print_menu_runtime_list("声卡", runtime_profile.get("sound_texts", []), "cyan")

    # 打印当前可用内存。
    print(f"  {menu_color('可用内存', 'gray')}  {menu_color(format_bytes_text(runtime_profile.get('available_memory_bytes', 0)), 'green')}")

    # 打印推荐线程数。
    print(f"  {menu_color('线程建议', 'gray')}  {menu_color(recommended_max_workers, 'yellow')}")

    # 打印空行分隔后续菜单。
    print()


# 定义控制台编码初始化函数。
def initialize_console_encoding():

    """
    初始化 Windows 控制台中文输入输出编码。

    :return: None。
    :rtype: None
    """

    # 初始化 Windows 控制台 ANSI 转换层。
    colorama_init(autoreset=False, strip=False)

    # 捕获控制台编码初始化异常。
    try:

        # 判断当前系统是否为 Windows。
        if os.name == "nt":

            # 导入 ctypes 模块。
            import ctypes

            # 设置控制台输出代码页为 UTF-8。
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)

            # 设置控制台输入代码页为 UTF-8。
            ctypes.windll.kernel32.SetConsoleCP(65001)

        # 判断标准输出是否支持重新配置。
        if hasattr(sys.stdout, "reconfigure"):

            # 配置标准输出编码。
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")

        # 判断标准错误是否支持重新配置。
        if hasattr(sys.stderr, "reconfigure"):

            # 配置标准错误编码。
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        # 判断标准输入是否支持重新配置。
        if hasattr(sys.stdin, "reconfigure"):

            # 配置标准输入编码。
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")

    # 忽略非交互终端中的编码初始化异常。
    except Exception:

        # 返回空值。
        return


# 定义布尔环境变量解析函数。
def read_truthy_environment(name):

    """
    解析布尔型环境变量开关。

    :param name: 环境变量名称。
    :type name: str
    :return: 环境变量是否为启用状态。
    :rtype: bool
    """

    # 读取环境变量原始文本。
    raw_value = os.environ.get(name, "")

    # 标准化环境变量文本。
    value = raw_value.strip().lower()

    # 判断环境变量是否属于启用值集合。
    return value in {"1", "true", "yes", "y", "on"}


# 定义打包运行态识别函数。
def is_packaged_executable():

    """
    判断当前进程是否运行在 PyInstaller 打包环境中。

    :return: 当前进程是否为打包后的可执行文件。
    :rtype: bool
    """

    # 读取 PyInstaller 注入的冻结运行标识。
    frozen_flag = getattr(sys, "frozen", False)

    # 返回布尔化后的冻结运行标识。
    return bool(frozen_flag)


# 定义异常堆栈格式化函数。
def format_exception_traceback(error):

    """
    将异常对象转换为完整堆栈文本。

    :param error: 异常对象。
    :type error: BaseException
    :return: 完整异常堆栈文本。
    :rtype: str
    """

    # 读取异常类型。
    error_type = type(error)

    # 格式化异常堆栈行列表。
    traceback_lines = traceback.format_exception(error_type, error, error.__traceback__)

    # 拼接异常堆栈文本。
    traceback_text = "".join(traceback_lines)

    # 返回去除尾部空白后的堆栈文本。
    return traceback_text.rstrip()


# 定义错误退出暂停判断函数。
def should_pause_console_on_exit(exit_code):

    """
    判断进程退出前是否需要停留控制台。

    :param exit_code: 进程退出码。
    :type exit_code: int
    :return: 是否需要等待用户确认后关闭控制台。
    :rtype: bool
    """

    # 判断当前退出码是否为成功。
    if int(exit_code or 0) == 0:

        # 成功退出不执行控制台停留。
        return False

    # 判断是否显式关闭错误停留。
    if read_truthy_environment("DDI_DISABLE_PAUSE_ON_ERROR"):

        # 显式关闭时不执行控制台停留。
        return False

    # 判断是否显式开启错误停留。
    if read_truthy_environment("DDI_PAUSE_ON_ERROR"):

        # 显式开启时执行控制台停留。
        return True

    # 仅在打包运行态默认执行错误停留。
    return is_packaged_executable()


# 定义错误退出控制台停留函数。
def pause_console_before_error_exit(exit_code):

    """
    在错误退出前停留控制台窗口。

    :param exit_code: 进程退出码。
    :type exit_code: int
    :return: None。
    :rtype: None
    """

    # 判断当前退出是否需要控制台停留。
    if not should_pause_console_on_exit(exit_code):

        # 无需停留时直接返回。
        return

    # 打印错误退出分隔空行。
    print()

    # 打印错误退出分隔线。
    print("=" * 72)

    # 打印错误退出码。
    print(f"程序执行失败，退出码：{exit_code}")

    # 打印错误查看提示。
    print("请查看上方错误信息，或检查本次运行日志文件。")

    # 捕获非交互输入环境中的等待异常。
    try:

        # 等待用户确认后关闭窗口。
        input("按 Enter 键关闭窗口...")

    # 忽略无法读取标准输入的环境异常。
    except (EOFError, KeyboardInterrupt, OSError):

        # 返回空值。
        return


# 定义启动像素头像打印函数。
def print_startup_avatar():

    """
    在交互终端启动时打印像素头像。

    :return: None。
    :rtype: None
    """

    # 判断是否显式禁用启动头像。
    if os.environ.get("DDI_NO_STARTUP_AVATAR", "").strip() == "1":

        # 结束启动头像打印流程。
        return

    # 输出头像前置空行。
    print()

    # 调用硬编码启动像素头像打印函数。
    print_startup_avatar_art()

    # 输出启动标题文本。
    print(f"  {menu_color('DDI V14.0', 'green')}")

    # 输出头像后置空行。
    print()

    # 保持头像内容在控制台中停留。
    sleep_for_startup_panel(3)


# 定义启动展示停留函数。
def sleep_for_startup_panel(seconds):

    """
    控制启动展示内容在控制台中的停留时间。

    :param seconds: 停留秒数。
    :type seconds: int | float
    :return: None。
    :rtype: None
    """

    # 判断是否显式跳过启动展示停留。
    if read_truthy_environment("DDI_SKIP_STARTUP_WAIT"):

        # 结束启动展示停留流程。
        return

    # 计算非负停留秒数。
    wait_seconds = max(0.0, float(seconds or 0))

    # 判断停留秒数是否为空。
    if wait_seconds <= 0:

        # 结束启动展示停留流程。
        return

    # 按指定秒数阻塞启动流程。
    time.sleep(wait_seconds)


# 定义启动更新日志打印函数。
def print_startup_changelog():

    """
    打印当前版本启动更新日志。

    :return: None。
    :rtype: None
    """

    # 判断是否显式禁用启动更新日志。
    if os.environ.get("DDI_NO_STARTUP_CHANGELOG", "").strip() == "1":

        # 结束启动更新日志打印流程。
        return

    # 读取当前版本启动更新日志文本。
    changelog_text = get_current_startup_changelog()

    # 判断更新日志文本是否为空。
    if not changelog_text.strip():

        # 结束启动更新日志打印流程。
        return

    # 输出更新日志前置空行。
    print()

    # 输出当前版本更新日志文本。
    print(changelog_text)

    # 输出更新日志后置空行。
    print()

    # 保持更新日志内容在控制台中停留。
    sleep_for_startup_panel(3)


# 定义项目根目录解析函数。
def get_project_root():

    """
    获取源码运行或打包运行时的项目根目录。

    :return: 项目根目录。
    :rtype: str
    """

    # 判断当前程序是否为 PyInstaller 打包后的可执行文件。
    if bool(getattr(sys, "frozen", False)):

        # 返回可执行文件所在目录。
        return os.path.dirname(os.path.abspath(sys.executable))

    # 返回源码入口文件所在目录。
    return os.path.dirname(os.path.abspath(__file__))


# 定义命令行参数显式传入判断函数。
def has_command_option(option_name):

    """
    判断命令行是否显式传入指定参数。

    :param option_name: 命令行参数名称。
    :type option_name: str
    :return: 参数是否显式传入。
    :rtype: bool
    """

    # 遍历全部命令行参数。
    for command_arg in sys.argv[1:]:

        # 判断当前参数是否与目标参数完全一致。
        if command_arg == option_name:

            # 返回参数已显式传入状态。
            return True

        # 判断当前参数是否为目标参数的等号赋值形式。
        if command_arg.startswith(option_name + "="):

            # 返回参数已显式传入状态。
            return True

    # 返回参数未显式传入状态。
    return False


# 定义 Windows CPU 型号读取函数。
def read_windows_cpu_name():

    """
    读取 Windows 注册表中的 CPU 型号文本。

    :return: CPU 型号文本。
    :rtype: str
    """

    # 判断当前系统是否不是 Windows。
    if os.name != "nt":

        # 返回当前平台处理器文本。
        return platform.processor().strip()

    # 捕获 Windows 注册表读取异常。
    try:

        # 导入 Windows 注册表模块。
        import winreg

        # 打开 CPU 信息注册表项。
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key_obj:

            # 读取 CPU 型号文本。
            cpu_name = winreg.QueryValueEx(key_obj, "ProcessorNameString")[0]

        # 返回去除空白后的 CPU 型号文本。
        return str(cpu_name).strip()

    # 处理 Windows 注册表读取异常。
    except Exception:

        # 返回平台处理器文本或架构文本。
        return platform.processor().strip() or platform.machine().strip()


# 定义物理内存状态读取函数。
def read_memory_status():

    """
    读取当前电脑的物理内存总量与可用量。

    :return: 物理内存状态。
    :rtype: dict
    """

    # 初始化内存状态字典。
    memory_status = {"total_bytes": 0, "available_bytes": 0}

    # 判断当前系统是否不是 Windows。
    if os.name != "nt":

        # 返回空内存状态。
        return memory_status

    # 捕获 Windows 内存状态读取异常。
    try:

        # 导入 ctypes 模块。
        import ctypes

        # 定义 Windows 内存状态结构体。
        class MemoryStatusEx(ctypes.Structure):

            """
            Windows GlobalMemoryStatusEx 结构体。

            :return: 内存状态结构体实例。
            :rtype: MemoryStatusEx
            """

            # 声明 Windows 内存状态字段。
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        # 初始化内存状态结构体实例。
        native_memory_status = MemoryStatusEx()

        # 写入结构体长度。
        native_memory_status.dwLength = ctypes.sizeof(MemoryStatusEx)

        # 判断 Windows 内存状态读取是否成功。
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(native_memory_status)):

            # 写入物理内存总量。
            memory_status["total_bytes"] = int(native_memory_status.ullTotalPhys)

            # 写入物理内存可用量。
            memory_status["available_bytes"] = int(native_memory_status.ullAvailPhys)

    # 处理 Windows 内存状态读取异常。
    except Exception:

        # 返回当前内存状态。
        return memory_status

    # 返回当前内存状态。
    return memory_status


# 定义字节大小格式化函数。
def format_bytes_text(size_bytes):

    """
    将字节大小格式化为易读文本。

    :param size_bytes: 原始字节大小。
    :type size_bytes: int
    :return: 格式化后的大小文本。
    :rtype: str
    """

    # 判断原始字节大小是否为空或小于等于零。
    if not size_bytes or int(size_bytes) <= 0:

        # 返回未知大小文本。
        return "未知"

    # 计算吉字节单位数值。
    size_gb = float(size_bytes) / float(1024 ** 3)

    # 返回格式化后的吉字节文本。
    return f"{size_gb:.1f} GB"


# 定义运行环境概览构建函数。
def build_runtime_profile():

    """
    构建当前电脑运行环境概览信息。

    :return: 运行环境概览信息。
    :rtype: dict
    """

    # 读取当前电脑主机名称。
    machine_name = os.environ.get("COMPUTERNAME", "").strip() or platform.node().strip() or "未知"

    # 读取当前电脑硬件型号信息。
    hardware_profile = read_hardware_profile()

    # 读取 CPU 型号文本。
    cpu_name = hardware_profile.get("cpu_text") or read_windows_cpu_name() or "未知"

    # 读取逻辑核心数量。
    logical_cpu_count = int(os.cpu_count() or 1)

    # 读取物理内存状态。
    memory_status = read_memory_status()

    # 构建系统名称文本。
    system_text = f"{platform.system()} {platform.release()}".strip()

    # 构建 Python 版本文本。
    python_text = f"Python {platform.python_version()} {platform.machine()}".strip()

    # 构建运行环境概览信息。
    runtime_profile = {
        "machine_name": machine_name,
        "system_text": system_text or "未知",
        "python_text": python_text or "未知",
        "cpu_name": cpu_name,
        "logical_cpu_count": logical_cpu_count,
        "total_memory_bytes": int(memory_status.get("total_bytes", 0) or 0),
        "available_memory_bytes": int(memory_status.get("available_bytes", 0) or 0),
    }

    # 合并硬件型号信息。
    runtime_profile.update(hardware_profile)

    # 返回运行环境概览信息。
    return runtime_profile


# 定义推荐线程数构建函数。
def build_recommended_max_workers(runtime_profile, fallback_worker_count):

    """
    根据当前电脑配置构建推荐线程数。

    :param runtime_profile: 运行环境概览信息。
    :type runtime_profile: dict
    :param fallback_worker_count: 配置文件中的兜底线程数。
    :type fallback_worker_count: int
    :return: 推荐线程数。
    :rtype: int
    """

    # 调用无界面共享推荐线程数规则。
    return build_shared_recommended_max_workers(runtime_profile, fallback_worker_count)


# 定义项目相对路径解析函数。
def resolve_project_path(project_root, path_value):

    """
    将默认相对路径解析为项目目录下的绝对路径。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :param path_value: 原始路径配置。
    :type path_value: str
    :return: 解析后的路径。
    :rtype: str
    """

    # 判断路径配置是否为空。
    if not path_value:

        # 返回空路径配置。
        return path_value

    # 判断路径配置是否已经是绝对路径。
    if os.path.isabs(path_value):

        # 返回原始绝对路径。
        return path_value

    # 返回项目目录下的绝对路径。
    return os.path.join(project_root, path_value)


# 定义项目运行产物目录规范化函数。
def normalize_runtime_artifact_path(project_root, path_value, artifact_category):

    """
    将项目内部的运行产物路径收敛到 runtime 分类目录。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :param path_value: 原始运行产物目录。
    :type path_value: str
    :param artifact_category: 运行产物分类名称。
    :type artifact_category: str
    :return: 规范化后的运行产物目录。
    :rtype: str
    """

    # 判断原始目录是否为空。
    if not path_value:

        # 返回空目录。
        return ""

    # 解析原始目录为绝对路径。
    resolved_path = os.path.abspath(resolve_project_path(project_root, path_value))

    # 标准化项目根目录的绝对路径。
    normalized_project_root = os.path.abspath(project_root)

    # 标准化运行产物根目录的绝对路径。
    runtime_root = os.path.join(normalized_project_root, "runtime")

    # 判断原始目录是否位于项目目录内。
    try:

        # 比较原始目录与项目根目录的公共路径。
        is_project_internal = os.path.normcase(os.path.commonpath([normalized_project_root, resolved_path])) == os.path.normcase(normalized_project_root)

    # 处理不同磁盘盘符无法计算公共路径的情况。
    except ValueError:

        # 标记原始目录为项目外目录。
        is_project_internal = False

    # 保留用户显式指定的项目外目录。
    if not is_project_internal:

        # 返回项目外绝对目录。
        return resolved_path

    # 判断原始目录是否已经归类到运行产物根目录。
    is_runtime_internal = os.path.normcase(os.path.commonpath([runtime_root, resolved_path])) == os.path.normcase(runtime_root)

    # 保留已经归类的运行产物目录。
    if is_runtime_internal:

        # 返回已有运行产物目录。
        return resolved_path

    # 计算原始目录相对项目根目录的路径。
    relative_path = os.path.relpath(resolved_path, normalized_project_root)

    # 返回按分类收敛后的运行产物目录。
    return os.path.join(runtime_root, "custom", artifact_category, relative_path)


# 定义日期文本标准化函数。
def normalize_date_text(date_value):

    """
    将任务日期文本标准化为 YYYY-MM-DD 格式。

    :param date_value: 原始日期文本。
    :type date_value: object
    :return: 标准日期文本。
    :rtype: str
    """

    # 判断原始日期是否为空。
    if not date_value:

        # 返回空日期文本。
        return ""

    # 转换原始日期为去除空白后的文本。
    date_text = str(date_value).strip()

    # 定义允许的日期输入格式。
    accepted_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]

    # 遍历允许的日期输入格式。
    for date_format in accepted_formats:

        # 捕获当前格式解析异常。
        try:

            # 返回标准化后的日期文本。
            return datetime.strptime(date_text, date_format).strftime("%Y-%m-%d")

        # 当前格式不匹配时继续尝试下一个格式。
        except ValueError:

            # 继续处理下一个日期格式。
            continue

    # 抛出日期格式异常。
    raise ValueError(f"日期格式无效：{date_text}，请使用 YYYY-MM-DD 格式")


# 定义任务日期参数标准化函数。
def normalize_args_dates(args):

    """
    标准化任务命令行或交互菜单中的日期参数。

    :param args: 命令行参数命名空间。
    :type args: argparse.Namespace
    :return: 命令行参数命名空间。
    :rtype: argparse.Namespace
    """

    # 标准化查询开始日期。
    args.start_date = normalize_date_text(args.start_date)

    # 标准化查询结束日期。
    args.end_date = normalize_date_text(args.end_date)

    # 返回更新后的命令行参数命名空间。
    return args


# 定义命令行参数解析函数。
def parse_args():

    """
    解析 DDI 任务命令行参数。

    :return: 命令行参数命名空间。
    :rtype: argparse.Namespace
    """

    # 读取全局任务配置作为命令行默认值。
    task_config = get_task_config()

    # 构建当前电脑运行环境概览。
    runtime_profile = build_runtime_profile()

    # 构建推荐线程数。
    recommended_max_workers = build_recommended_max_workers(runtime_profile, task_config["最大并发数"])

    # 判断命令行是否显式传入最大线程数。
    max_workers_provided = has_command_option("--max-workers")

    # 读取 DDI 项目根目录。
    project_root = get_project_root()

    # 创建命令行参数解析器。
    parser = argparse.ArgumentParser(description="DDI 协议直连任务入口")

    # 注册商业名称参数。
    parser.add_argument("--company", default="", help="指定商业名称，不填则运行全部启用账号")

    # 注册 Cookie 输出目录参数。
    parser.add_argument("--cookie-dir", default=resolve_project_path(project_root, task_config["Cookie目录"]), help="登录成功后的 Cookie 输出目录")

    # 注册任务动作参数。
    parser.add_argument("--action", default=task_config["执行动作"], choices=["login", "query", "export", "query_excel"], help="任务动作：login 登录，query 查询，export 导出，query_excel 查询并生成 Excel")

    # 注册业务数据类型参数。
    parser.add_argument("--data-type", default=task_config["数据类型"], help="业务数据类型，例如：配送流向")

    # 注册日期范围模式参数。
    parser.add_argument("--date-mode", default=task_config["日期模式"], choices=["previous_month_full", "previous_month_to_today", "custom"], help="日期模式：上月整月、上月1号至今天或自定义")

    # 注册查询开始日期参数。
    parser.add_argument("--start-date", default=task_config["开始日期"], help="查询开始日期，格式：YYYY-MM-DD")

    # 注册查询结束日期参数。
    parser.add_argument("--end-date", default=task_config["结束日期"], help="查询结束日期，格式：YYYY-MM-DD")

    # 注册输出目录参数。
    parser.add_argument("--output-dir", default=resolve_project_path(project_root, task_config["输出目录"]), help="查询结果和导出文件输出目录")

    # 注册录入明细生成参数。
    parser.add_argument("--copy-excel", dest="copy_excel", action="store_true", default=task_config["生成复制用Excel"], help="为当前商业本轮原始流向生成录入明细 Excel")

    # 注册录入明细禁用参数。
    parser.add_argument("--no-copy-excel", dest="copy_excel", action="store_false", help="不生成录入明细 Excel")

    # 注册运行日志目录参数。
    parser.add_argument("--log-dir", default=resolve_project_path(project_root, task_config["日志目录"]), help="本次运行 Excel 日志输出目录")

    # 注册控制台路径展示模式参数。
    parser.add_argument("--console-path-mode", default=task_config["控制台路径模式"], choices=["absolute", "relative"], help="控制台日志中的文件路径展示方式")

    # 注册最大并发数参数。
    parser.add_argument("--max-workers", default=recommended_max_workers, type=int, help="批量运行时同时执行的商业数量")

    # 注册交互菜单启动参数。
    parser.add_argument("--menu", action="store_true", help="启动交互菜单，适合打包 exe 后双击使用")

    # 注册交互菜单禁用参数。
    parser.add_argument("--no-menu", action="store_true", help="无命令行参数运行时不启动交互菜单")

    # 解析命令行参数。
    args = parser.parse_args()

    # 判断是否显式提供日期参数。
    explicit_dates = has_command_option("--start-date") or has_command_option("--end-date")

    # 显式输入任一日期时切换到自定义日期模式。
    if explicit_dates:
        args.date_mode = "custom"

    # 根据日期模式构造统一日期范围。
    args.date_range = DateRangeSpec.from_mode(args.date_mode, args.start_date, args.end_date)

    # 使用统一日期范围回填任务日期。
    args.start_date = args.date_range.start_date
    args.end_date = args.date_range.end_date

    # 规范化 Cookie 会话文件目录。
    args.cookie_dir = normalize_runtime_artifact_path(project_root, args.cookie_dir, "cookies")

    # 规范化查询结果和 Excel 文件目录。
    args.output_dir = normalize_runtime_artifact_path(project_root, args.output_dir, "results")

    # 规范化 Excel 运行日志目录。
    args.log_dir = normalize_runtime_artifact_path(project_root, args.log_dir, "logs")

    # 标准化最大线程数下限。
    args.max_workers = max(1, int(args.max_workers or recommended_max_workers))

    # 记录当前电脑运行环境概览。
    args.runtime_profile = runtime_profile

    # 记录推荐线程数。
    args.recommended_max_workers = recommended_max_workers

    # 记录当前线程数来源。
    args.max_workers_source = "手动指定" if max_workers_provided else "配置推荐"

    # 返回解析后的命令行参数。
    return args


# 定义交互菜单启动判断函数。
def should_start_interactive_menu(args):

    """
    判断当前运行是否需要进入交互菜单。

    :param args: 命令行参数命名空间。
    :type args: argparse.Namespace
    :return: 是否启动交互菜单。
    :rtype: bool
    """

    # 判断命令行是否显式禁用菜单模式。
    if args.no_menu:

        # 返回菜单模式关闭状态。
        return False

    # 判断命令行是否显式指定菜单模式。
    if args.menu:

        # 返回菜单模式启用状态。
        return True

    # 判断程序是否没有接收任何额外命令行参数。
    no_command_args = len(sys.argv) == 1

    # 返回无参数运行时的菜单启动状态。
    return no_command_args


# 定义交互菜单读取函数。
def read_menu_input(prompt_text, default_value=""):

    """
    读取交互菜单输入内容。

    :param prompt_text: 输入提示文本。
    :type prompt_text: str
    :param default_value: 默认输入值。
    :type default_value: str
    :return: 用户输入值或默认值。
    :rtype: str
    """

    # 拼接默认值展示文本。
    default_text = f" {menu_color('[' + str(default_value) + ']', 'yellow')}" if default_value else ""

    # 读取用户输入内容。
    value = input(f"{menu_color(prompt_text, 'cyan')}{default_text}{menu_color(':', 'gray')} ").strip()

    # 返回用户输入值或默认值。
    return value or default_value


# 定义商业名称列表打印函数。
def print_menu_companies(company_names=None, title="可选商业"):

    """
    打印交互菜单可选商业名称。

    :param company_names: 指定展示的商业名称列表。
    :type company_names: list[str] | None
    :param title: 列表标题。
    :type title: str
    :return: None。
    :rtype: None
    """

    # 读取全量商业名称列表。
    all_company_names = list(ACCOUNTS.keys())

    # 读取本次展示的商业名称列表。
    display_company_names = company_names if company_names is not None else all_company_names

    # 打印列表标题。
    print_menu_title(title)

    # 遍历账号配置中的商业名称。
    for company_name in display_company_names:

        # 读取当前商业账号配置。
        account = ACCOUNTS[company_name]

        # 读取当前商业在全量列表中的序号。
        company_index = all_company_names.index(company_name) + 1

        # 构建商业序号文本。
        index_text = menu_color(f"{company_index:02d}.", "yellow")

        # 构建商业组织维度文本。
        detail_text = build_menu_company_detail_text(account)

        # 打印当前商业序号、名称和组织维度。
        print(f"  {index_text} {company_name} {menu_color(detail_text, 'gray')}")


# 定义菜单商业维度说明构建函数。
def build_menu_company_detail_text(account):

    """
    构建菜单中展示的商业组织维度说明。
    :param account: 商业账号配置。
    :type account: dict
    :return: 商业组织维度说明。
    :rtype: str
    """

    # 读取商业负责人。
    owner_name = account.get("负责人", "")

    # 读取商业大区。
    region_name = account.get("大区", "")

    # 读取商业省份。
    province_name = account.get("省份", "")

    # 读取商业平台。
    platform_name = account.get("平台", "")

    # 返回商业组织维度说明文本。
    return f"| 负责人: {owner_name} | 大区: {region_name} | 省份: {province_name} | 平台: {platform_name}"


# 定义菜单主功能选择函数。
def select_menu_main_action():

    """
    读取交互菜单中的主功能选择。

    :return: 主功能标识。
    :rtype: str
    """

    # 定义主功能编号映射。
    action_map = {"1": "run", "2": "account_status", "0": "exit"}

    # 打印主功能选择说明。
    print_menu_options("主菜单", [("1", "运行任务"), ("2", "商业启停管理"), ("0", "退出")])

    # 持续读取主功能选择直到合法。
    while True:

        # 读取主功能输入。
        action_value = read_menu_input("请选择主菜单", "1")

        # 转换主功能序号为功能标识。
        action_value = action_map.get(action_value, action_value)

        # 判断主功能标识是否有效。
        if action_value in ["run", "account_status", "exit"]:

            # 返回主功能标识。
            return action_value

        # 打印主功能无效提示。
        print_menu_message("错误", "主菜单选项无效，请输入 1、2 或 0。", "red")


# 定义运行期菜单配置读取函数。
def load_menu_runtime_config(project_root):

    """
    读取交互菜单使用的运行期账号启停配置。

    :param project_root: 项目根目录。
    :type project_root: str
    :return: 运行期账号启停配置。
    :rtype: dict
    """

    # 确保运行期配置文件存在并完成商业补齐。
    ensure_runtime_account_config(project_root)

    # 读取运行期配置文件内容。
    runtime_config = load_runtime_account_config(project_root)

    # 读取商业启停配置集合。
    companies_config = runtime_config.get("商业启停", {})

    # 判断商业启停配置是否为字典。
    if not isinstance(companies_config, dict):

        # 使用空商业启停配置。
        companies_config = {}

    # 写回标准商业启停配置集合。
    runtime_config["商业启停"] = companies_config

    # 返回运行期配置内容。
    return runtime_config


# 定义运行期菜单配置保存函数。
def save_menu_runtime_config(project_root, runtime_config):

    """
    保存交互菜单更新后的运行期账号启停配置。

    :param project_root: 项目根目录。
    :type project_root: str
    :param runtime_config: 运行期账号启停配置。
    :type runtime_config: dict
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 读取商业启停配置集合。
    companies_config = runtime_config.get("商业启停", {})

    # 判断商业启停配置是否为字典。
    if not isinstance(companies_config, dict):

        # 使用空商业启停配置。
        companies_config = {}

    # 初始化标准商业启停配置。
    normalized_config = {}

    # 遍历源码账号配置中的商业。
    for company_name, account in ACCOUNTS.items():

        # 读取运行期配置或源码默认启用状态。
        enabled_status = companies_config.get(company_name, account.get("启用", True))

        # 写入布尔化后的商业启停状态。
        normalized_config[company_name] = bool(enabled_status)

    # 写回标准商业启停配置。
    runtime_config["商业启停"] = normalized_config

    # 保存运行期配置文件。
    return save_runtime_account_config(runtime_config, project_root)


# 定义商业启停状态列表打印函数。
def print_menu_company_statuses(project_root, company_names=None, title="商业启停状态"):

    """
    打印运行期商业启停状态列表。

    :param project_root: 项目根目录。
    :type project_root: str
    :param company_names: 指定展示的商业名称列表。
    :type company_names: list[str] | None
    :param title: 列表标题。
    :type title: str
    :return: None。
    :rtype: None
    """

    # 读取运行期账号启停配置。
    runtime_config = load_menu_runtime_config(project_root)

    # 初始化启用商业数量。
    enabled_count = 0

    # 初始化停用商业数量。
    disabled_count = 0

    # 读取全量商业名称列表。
    all_company_names = list(ACCOUNTS.keys())

    # 读取本次展示的商业名称列表。
    display_company_names = company_names if company_names is not None else all_company_names

    # 打印列表标题。
    print_menu_title(title)

    # 遍历账号配置中的商业名称。
    for company_name in display_company_names:

        # 读取当前商业账号配置。
        account = ACCOUNTS[company_name]

        # 读取当前商业在全量列表中的序号。
        index = all_company_names.index(company_name) + 1

        # 解析当前商业启用状态。
        enabled_status = resolve_runtime_enabled(company_name, account, runtime_config)

        # 累加启用商业数量。
        enabled_count += 1 if enabled_status else 0

        # 累加停用商业数量。
        disabled_count += 0 if enabled_status else 1

        # 构建商业序号文本。
        index_text = menu_color(f"{index:02d}.", "yellow")

        # 构建当前商业状态标签。
        status_label = build_menu_status_label(enabled_status)

        # 构建平台标识文本。
        platform_text = menu_color(account.get("平台", ""), "cyan")

        # 构建商业组织维度文本。
        detail_text = build_menu_company_detail_text(account)

        # 打印当前商业序号、状态、名称和平台。
        print(f"  {index_text} {status_label} {company_name} {menu_color(detail_text, 'gray')}")

    # 打印商业启停汇总。
    print(f"\n{menu_color('汇总:', 'cyan')} 启用 {menu_color(enabled_count, 'green')} 家，停用 {menu_color(disabled_count, 'red')} 家。")


# 定义商业序号文本解析函数。
def parse_menu_company_indexes(selection_text, company_names=None):

    """
    解析交互菜单中的商业序号文本。

    :param selection_text: 商业序号文本。
    :type selection_text: str
    :param company_names: 限定可选商业名称列表。
    :type company_names: list[str] | None
    :return: 商业名称列表。
    :rtype: list[str]
    """

    # 读取商业名称列表。
    company_names = company_names if company_names is not None else list(ACCOUNTS.keys())

    # 标准化序号分隔符。
    normalized_text = selection_text.replace("，", ",").replace("、", ",").replace(" ", ",")

    # 拆分并过滤空序号片段。
    index_parts = [item.strip() for item in normalized_text.split(",") if item.strip()]

    # 初始化选择的商业名称列表。
    selected_names = []

    # 遍历序号片段。
    for index_part in index_parts:

        # 判断当前片段是否为序号范围。
        if "-" in index_part:

            # 按范围分隔符拆分序号。
            range_parts = [item.strip() for item in index_part.split("-", 1)]

            # 判断范围起止序号是否为数字。
            if len(range_parts) != 2 or not range_parts[0].isdigit() or not range_parts[1].isdigit():

                # 抛出序号格式异常。
                raise ValueError(f"商业序号范围无效：{index_part}")

            # 读取范围开始序号。
            start_index = int(range_parts[0])

            # 读取范围结束序号。
            end_index = int(range_parts[1])

            # 判断范围顺序是否需要交换。
            if start_index > end_index:

                # 交换范围起止序号。
                start_index, end_index = end_index, start_index

            # 遍历范围内序号。
            for current_index in range(start_index, end_index + 1):

                # 判断当前序号是否在有效范围内。
                if not 1 <= current_index <= len(company_names):

                    # 抛出序号越界异常。
                    raise ValueError(f"商业序号超出范围：{current_index}")

                # 追加当前序号对应的商业名称。
                selected_names.append(company_names[current_index - 1])

            # 进入下一个序号片段。
            continue

        # 判断当前片段是否为数字序号。
        if index_part.isdigit():

            # 读取商业序号。
            company_index = int(index_part)

            # 判断商业序号是否在有效范围内。
            if not 1 <= company_index <= len(company_names):

                # 抛出序号越界异常。
                raise ValueError(f"商业序号超出范围：{company_index}")

            # 追加序号对应的商业名称。
            selected_names.append(company_names[company_index - 1])

            # 进入下一个序号片段。
            continue

        # 判断当前片段是否为完整商业名称。
        if index_part in ACCOUNTS:

            # 追加完整商业名称。
            selected_names.append(index_part)

            # 进入下一个序号片段。
            continue

        # 抛出无法识别的商业选择异常。
        raise ValueError(f"无法识别商业选择：{index_part}")

    # 按原始顺序去除重复商业。
    selected_names = list(dict.fromkeys(selected_names))

    # 返回选择的商业名称列表。
    return selected_names


# 定义商业选择读取函数。
def read_menu_company_selection(prompt_text, allow_multiple=True, company_names=None):

    """
    读取交互菜单中的商业序号选择。

    :param prompt_text: 输入提示文本。
    :type prompt_text: str
    :param allow_multiple: 是否允许选择多个商业。
    :type allow_multiple: bool
    :param company_names: 限定可选商业名称列表。
    :type company_names: list[str] | None
    :return: 商业名称列表。
    :rtype: list[str]
    """

    # 持续读取商业选择直到合法。
    while True:

        # 读取商业选择文本。
        selection_text = read_menu_input(prompt_text)

        # 判断是否输入空内容。
        if not selection_text:

            # 打印空选择提示。
            print_menu_message("提示", "请输入商业序号，例如 1 或 1,3,5 或 1-4。", "yellow")

            # 继续读取商业选择。
            continue

        # 捕获商业选择解析异常。
        try:

            # 解析商业序号文本。
            selected_names = parse_menu_company_indexes(selection_text, company_names)

        # 处理商业选择解析异常。
        except ValueError as error:

            # 打印解析失败提示。
            print_menu_message("错误", str(error), "red")

            # 继续读取商业选择。
            continue

        # 判断单选场景是否选择了多个商业。
        if not allow_multiple and len(selected_names) != 1:

            # 打印单选约束提示。
            print_menu_message("错误", "当前操作只能选择一个商业。", "red")

            # 继续读取商业选择。
            continue

        # 返回选择的商业名称列表。
        return selected_names


# 定义菜单维度选择函数。
def select_menu_dimension():

    """
    读取交互菜单中的组织维度选择。
    :return: 组织维度名称。
    :rtype: str
    """

    # 定义组织维度编号映射。
    dimension_map = {"1": "大区", "2": "省份", "3": "负责人"}

    # 打印组织维度选择说明。
    print_menu_options("区分维度", [("1", "大区"), ("2", "省份"), ("3", "负责人")])

    # 持续读取组织维度直到合法。
    while True:

        # 读取组织维度输入。
        dimension_value = read_menu_input("请选择区分维度", "1")

        # 转换组织维度编号。
        dimension_name = dimension_map.get(dimension_value, dimension_value)

        # 判断组织维度是否有效。
        if dimension_name in ["大区", "省份", "负责人"]:

            # 返回组织维度名称。
            return dimension_name

        # 打印组织维度无效提示。
        print_menu_message("错误", "区分维度无效，请输入 1、2、3 或维度名称。", "red")


# 定义菜单维度取值选择函数。
def select_menu_dimension_value(dimension_name):

    """
    读取交互菜单中的组织维度取值。
    :param dimension_name: 组织维度名称。
    :type dimension_name: str
    :return: 组织维度取值。
    :rtype: str
    """

    # 读取当前维度的取值列表。
    dimension_values = list_account_dimension_values(dimension_name)

    # 打印当前维度的取值列表。
    print_menu_title(f"可选{dimension_name}")

    # 遍历当前维度的取值列表。
    for index, dimension_value in enumerate(dimension_values, start=1):

        # 构建维度取值序号文本。
        index_text = menu_color(f"{index:02d}.", "yellow")

        # 打印当前维度取值。
        print(f"  {index_text} {dimension_value}")

    # 持续读取维度取值直到合法。
    while True:

        # 读取维度取值输入。
        selected_value = read_menu_input(f"请选择{dimension_name}")

        # 判断维度取值是否为序号。
        if selected_value.isdigit():

            # 转换维度取值序号为列表下标。
            selected_index = int(selected_value) - 1

            # 判断维度取值序号是否有效。
            if 0 <= selected_index < len(dimension_values):

                # 返回序号对应的维度取值。
                return dimension_values[selected_index]

        # 判断维度取值是否有效。
        if selected_value in dimension_values:

            # 返回维度取值。
            return selected_value

        # 打印维度取值无效提示。
        print_menu_message("错误", f"{dimension_name}取值无效，请输入序号或完整名称。", "red")


# 定义菜单维度商业筛选函数。
def select_menu_dimension_company_names():

    """
    通过组织维度读取商业名称列表。
    :return: 商业名称列表。
    :rtype: list[str]
    """

    # 读取组织维度名称。
    dimension_name = select_menu_dimension()

    # 读取组织维度取值。
    dimension_value = select_menu_dimension_value(dimension_name)

    # 按组织维度筛选商业名称。
    company_names = filter_account_names_by_dimension(dimension_name, dimension_value)

    # 打印筛选后的商业列表。
    print_menu_companies(company_names, f"{dimension_name}: {dimension_value}")

    # 返回筛选后的商业名称列表。
    return company_names


# 定义商业启停状态批量更新函数。
def set_menu_company_statuses(project_root, company_names, enabled_status):

    """
    批量设置运行期商业启停状态。

    :param project_root: 项目根目录。
    :type project_root: str
    :param company_names: 商业名称列表。
    :type company_names: list[str]
    :param enabled_status: 启用状态。
    :type enabled_status: bool
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 读取运行期账号启停配置。
    runtime_config = load_menu_runtime_config(project_root)

    # 读取商业启停配置集合。
    companies_config = runtime_config["商业启停"]

    # 遍历需要设置状态的商业。
    for company_name in company_names:

        # 写入当前商业启停状态。
        companies_config[company_name] = bool(enabled_status)

    # 保存运行期账号启停配置。
    return save_menu_runtime_config(project_root, runtime_config)


# 定义商业启停状态反转函数。
def toggle_menu_company_statuses(project_root, company_names):

    """
    反转运行期商业启停状态。

    :param project_root: 项目根目录。
    :type project_root: str
    :param company_names: 商业名称列表。
    :type company_names: list[str]
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 读取运行期账号启停配置。
    runtime_config = load_menu_runtime_config(project_root)

    # 读取商业启停配置集合。
    companies_config = runtime_config["商业启停"]

    # 遍历需要反转状态的商业。
    for company_name in company_names:

        # 读取源码账号配置。
        account = ACCOUNTS[company_name]

        # 解析当前商业启用状态。
        enabled_status = resolve_runtime_enabled(company_name, account, runtime_config)

        # 写入反转后的商业启停状态。
        companies_config[company_name] = not enabled_status

    # 保存运行期账号启停配置。
    return save_menu_runtime_config(project_root, runtime_config)


# 定义单商业启用函数。
def enable_only_menu_company(project_root, company_name):

    """
    只启用指定商业并关闭其他商业。

    :param project_root: 项目根目录。
    :type project_root: str
    :param company_name: 商业名称。
    :type company_name: str
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 读取运行期账号启停配置。
    runtime_config = load_menu_runtime_config(project_root)

    # 读取商业启停配置集合。
    companies_config = runtime_config["商业启停"]

    # 遍历全部商业名称。
    for current_company_name in ACCOUNTS.keys():

        # 设置当前商业启停状态。
        companies_config[current_company_name] = current_company_name == company_name

    # 保存运行期账号启停配置。
    return save_menu_runtime_config(project_root, runtime_config)


# 定义平台选择函数。
def select_menu_platform():

    """
    读取交互菜单中的平台选择。

    :return: 平台标识。
    :rtype: str
    """

    # 读取已配置平台列表。
    platform_names = sorted({account.get("平台", "") for account in ACCOUNTS.values() if account.get("平台", "")})

    # 打印平台列表标题。
    print_menu_title("可选平台")

    # 遍历平台列表。
    for index, platform_name in enumerate(platform_names, start=1):

        # 构建平台序号文本。
        index_text = menu_color(f"{index:02d}.", "yellow")

        # 打印当前平台序号和标识。
        print(f"  {index_text} {menu_color(platform_name, 'cyan')}")

    # 持续读取平台选择直到合法。
    while True:

        # 读取平台选择文本。
        platform_value = read_menu_input("请选择平台")

        # 判断平台选择是否为序号。
        if platform_value.isdigit():

            # 转换平台序号为列表下标。
            platform_index = int(platform_value) - 1

            # 判断平台序号是否在有效范围内。
            if 0 <= platform_index < len(platform_names):

                # 返回序号对应的平台标识。
                return platform_names[platform_index]

        # 判断平台选择是否为平台标识。
        if platform_value in platform_names:

            # 返回平台标识。
            return platform_value

        # 打印平台选择无效提示。
        print_menu_message("错误", "平台选择无效，请输入平台序号或平台标识。", "red")


# 定义启停状态选择函数。
def select_menu_enabled_status():

    """
    读取交互菜单中的启停状态选择。

    :return: 启用状态。
    :rtype: bool
    """

    # 定义启停状态编号映射。
    status_map = {"1": True, "2": False}

    # 打印启停状态选择说明。
    print_menu_options("目标状态", [("1", menu_color("启用", "green")), ("2", menu_color("停用", "red"))])

    # 持续读取启停状态直到合法。
    while True:

        # 读取启停状态输入。
        status_value = read_menu_input("请选择目标状态", "1")

        # 判断启停状态输入是否有效。
        if status_value in status_map:

            # 返回启停状态。
            return status_map[status_value]

        # 打印启停状态无效提示。
        print_menu_message("错误", "目标状态无效，请输入 1 或 2。", "red")


# 定义商业启停管理菜单函数。
def manage_runtime_account_menu(project_root):

    """
    执行商业启停管理交互菜单。

    :param project_root: 项目根目录。
    :type project_root: str
    :return: None。
    :rtype: None
    """

    # 定义启停管理菜单编号映射。
    action_map = {"1": "view", "2": "toggle", "3": "enable_all", "4": "disable_all", "5": "only_one", "6": "platform", "7": "view_dimension", "8": "dimension", "0": "back"}

    # 持续执行启停管理菜单。
    while True:

        # 打印启停管理菜单说明。
        print_menu_options("商业启停管理", [("1", "查看全部状态"), ("2", "按序号切换"), ("3", menu_color("全部启用", "green")), ("4", menu_color("全部停用", "red")), ("5", "只启用某一家"), ("6", "按平台设置"), ("7", "按维度查看"), ("8", "按维度设置"), ("0", "返回主菜单")])

        # 读取启停管理菜单输入。
        action_value = read_menu_input("请选择启停管理操作", "1")

        # 转换菜单序号为操作标识。
        action_value = action_map.get(action_value, action_value)

        # 判断是否返回主菜单。
        if action_value == "back":

            # 返回空值。
            return

        # 判断是否查看商业启停状态。
        if action_value == "view":

            # 打印商业启停状态列表。
            print_menu_company_statuses(project_root)

            # 进入下一轮菜单。
            continue

        # 判断是否按序号切换商业状态。
        if action_value == "toggle":

            # 打印商业启停状态列表。
            print_menu_company_statuses(project_root)

            # 读取需要切换的商业。
            selected_names = read_menu_company_selection("请输入需要切换的商业序号")

            # 反转选择商业的启停状态。
            config_path = toggle_menu_company_statuses(project_root, selected_names)

            # 打印配置保存提示。
            print_menu_message("完成", f"已切换 {len(selected_names)} 家商业，配置文件：{config_path}", "green")

            # 进入下一轮菜单。
            continue

        # 判断是否启用全部商业。
        if action_value == "enable_all":

            # 批量启用全部商业。
            config_path = set_menu_company_statuses(project_root, list(ACCOUNTS.keys()), True)

            # 打印配置保存提示。
            print_menu_message("完成", f"已启用全部商业，配置文件：{config_path}", "green")

            # 进入下一轮菜单。
            continue

        # 判断是否停用全部商业。
        if action_value == "disable_all":

            # 批量停用全部商业。
            config_path = set_menu_company_statuses(project_root, list(ACCOUNTS.keys()), False)

            # 打印配置保存提示。
            print_menu_message("完成", f"已停用全部商业，配置文件：{config_path}", "green")

            # 进入下一轮菜单。
            continue

        # 判断是否只启用一家商业。
        if action_value == "only_one":

            # 打印商业启停状态列表。
            print_menu_company_statuses(project_root)

            # 读取需要单独启用的商业。
            selected_names = read_menu_company_selection("请输入唯一启用的商业序号", allow_multiple=False)

            # 只启用选择的商业。
            config_path = enable_only_menu_company(project_root, selected_names[0])

            # 打印配置保存提示。
            print_menu_message("完成", f"已只启用 {selected_names[0]}，配置文件：{config_path}", "green")

            # 进入下一轮菜单。
            continue

        # 判断是否按组织维度查看商业状态。
        if action_value == "view_dimension":

            # 读取目标组织维度下的商业名称列表。
            selected_names = select_menu_dimension_company_names()

            # 打印目标组织维度下的商业启停状态。
            print_menu_company_statuses(project_root, selected_names, "维度商业启停状态")

            # 进入下一轮菜单。
            continue

        # 判断是否按组织维度设置商业状态。
        if action_value == "dimension":

            # 读取目标组织维度下的商业名称列表。
            selected_names = select_menu_dimension_company_names()

            # 读取目标启停状态。
            enabled_status = select_menu_enabled_status()

            # 批量设置目标组织维度下的商业状态。
            config_path = set_menu_company_statuses(project_root, selected_names, enabled_status)

            # 构建启停状态文本。
            status_text = "启用" if enabled_status else "停用"

            # 打印配置保存提示。
            print_menu_message("完成", f"已{status_text}所选维度下的 {len(selected_names)} 家商业，配置文件：{config_path}", "green")

            # 进入下一轮菜单。
            continue

        # 判断是否按平台设置商业状态。
        if action_value == "platform":

            # 读取目标平台标识。
            platform_name = select_menu_platform()

            # 读取目标启停状态。
            enabled_status = select_menu_enabled_status()

            # 读取目标平台下的商业名称列表。
            selected_names = [company_name for company_name, account in ACCOUNTS.items() if account.get("平台") == platform_name]

            # 批量设置目标平台商业状态。
            config_path = set_menu_company_statuses(project_root, selected_names, enabled_status)

            # 构建启停状态文本。
            status_text = "启用" if enabled_status else "停用"

            # 打印配置保存提示。
            print_menu_message("完成", f"已{status_text}平台 {platform_name} 下的 {len(selected_names)} 家商业，配置文件：{config_path}", "green")

            # 进入下一轮菜单。
            continue

        # 打印启停管理菜单无效提示。
        print_menu_message("错误", "启停管理选项无效，请输入 1、2、3、4、5、6、7、8 或 0。", "red")


# 定义菜单商业选择函数。
def select_menu_company(default_company=""):

    """
    读取交互菜单中的商业选择。

    :param default_company: 默认商业名称。
    :type default_company: str
    :return: 商业名称，空字符串表示运行全部启用商业。
    :rtype: str
    """

    # 打印商业选择说明。
    print_menu_title("商业选择", "直接回车运行全部启用商业，输入 ? 查看全部商业，输入 / 按大区、省份、负责人筛选。")

    # 持续读取商业选择直到合法。
    while True:

        # 读取商业名称输入。
        company_name = read_menu_input("请输入商业名称", default_company)

        # 判断是否运行全部启用商业。
        if not company_name:

            # 返回空商业名称。
            return ""

        # 判断是否需要打印商业列表。
        if company_name == "?":

            # 打印可选商业列表。
            print_menu_companies()

            # 继续读取商业选择。
            continue

        # 判断是否需要按组织维度筛选商业列表。
        if company_name == "/":

            # 打印组织维度筛选后的商业列表。
            select_menu_dimension_company_names()

            # 继续读取商业选择。
            continue

        # 判断输入是否为商业序号。
        if company_name.isdigit():

            # 转换商业序号为列表下标。
            company_index = int(company_name) - 1

            # 读取商业名称列表。
            company_names = list(ACCOUNTS.keys())

            # 判断商业序号是否在有效范围内。
            if 0 <= company_index < len(company_names):

                # 返回序号对应的商业名称。
                return company_names[company_index]

        # 判断输入是否为已配置商业名称。
        if company_name in ACCOUNTS:

            # 返回已配置商业名称。
            return company_name

        # 打印商业名称无效提示。
        print_menu_message("错误", "商业名称不存在，请重新输入，或输入 ? 查看全部商业。", "red")


# 定义菜单动作选择函数。
def select_menu_action(default_action):

    """
    读取交互菜单中的任务动作。

    :param default_action: 默认任务动作。
    :type default_action: str
    :return: 任务动作。
    :rtype: str
    """

    # 定义动作编号映射。
    action_map = {"1": "query_excel", "2": "login", "3": "query", "4": "export"}

    # 打印动作选择说明。
    print_menu_options("任务动作", [("1", "查询并生成 Excel"), ("2", "只登录"), ("3", "只查询 JSON"), ("4", "平台原始导出")])

    # 持续读取任务动作直到合法。
    while True:

        # 读取动作输入。
        action_value = read_menu_input("请选择任务动作", default_action)

        # 转换动作序号为动作名称。
        action_value = action_map.get(action_value, action_value)

        # 判断动作名称是否有效。
        if action_value in ["login", "query", "export", "query_excel"]:

            # 返回任务动作。
            return action_value

        # 打印动作无效提示。
        print_menu_message("错误", "任务动作无效，请输入 1、2、3、4 或动作名称。", "red")


# 定义菜单路径展示模式选择函数。
def select_menu_path_mode(default_path_mode):

    """
    读取交互菜单中的控制台路径展示模式。

    :param default_path_mode: 默认路径展示模式。
    :type default_path_mode: str
    :return: 路径展示模式。
    :rtype: str
    """

    # 定义路径模式编号映射。
    path_mode_map = {"1": "relative", "2": "absolute"}

    # 打印路径模式选择说明。
    print_menu_options("路径展示", [("1", "相对路径"), ("2", "绝对路径")])

    # 持续读取路径模式直到合法。
    while True:

        # 读取路径展示模式输入。
        path_mode = read_menu_input("请选择路径展示方式", default_path_mode)

        # 转换路径模式序号为模式名称。
        path_mode = path_mode_map.get(path_mode, path_mode)

        # 判断路径展示模式是否有效。
        if path_mode in ["relative", "absolute"]:

            # 返回路径展示模式。
            return path_mode

        # 打印路径展示模式无效提示。
        print_menu_message("错误", "路径展示方式无效，请输入 1、2、relative 或 absolute。", "red")


# 定义菜单最大线程数选择函数。
def select_menu_max_workers(default_max_workers, recommended_max_workers):

    """
    读取交互菜单中的最大线程数。

    :param default_max_workers: 当前默认线程数。
    :type default_max_workers: int
    :param recommended_max_workers: 推荐线程数。
    :type recommended_max_workers: int
    :return: 最大线程数。
    :rtype: int
    """

    # 构建默认线程策略编号。
    default_action = "1" if int(default_max_workers) == int(recommended_max_workers) else "2"

    # 打印线程策略选择说明。
    print_menu_options("并发线程", [("1", f"使用推荐线程数 {recommended_max_workers}"), ("2", "手动输入线程数")])

    # 持续读取线程策略直到合法。
    while True:

        # 读取线程策略输入。
        action_value = read_menu_input("请选择线程策略", default_action)

        # 判断是否采用推荐线程数。
        if action_value == "1":

            # 返回推荐线程数。
            return int(recommended_max_workers)

        # 判断是否手动输入线程数。
        if action_value == "2":

            # 持续读取手动线程数直到合法。
            while True:

                # 读取线程数输入。
                worker_text = read_menu_input("请输入最大线程数", default_max_workers)

                # 捕获线程数转换异常。
                try:

                    # 转换线程数为整数。
                    worker_count = int(str(worker_text).strip())

                # 处理线程数转换异常。
                except ValueError:

                    # 打印线程数格式无效提示。
                    print_menu_message("错误", "最大线程数必须为正整数。", "red")

                    # 继续读取线程数。
                    continue

                # 判断线程数是否小于等于零。
                if worker_count <= 0:

                    # 打印线程数范围无效提示。
                    print_menu_message("错误", "最大线程数必须大于 0。", "red")

                    # 继续读取线程数。
                    continue

                # 返回手动线程数。
                return worker_count

        # 打印线程策略无效提示。
        print_menu_message("错误", "线程策略无效，请输入 1 或 2。", "red")


# 定义交互菜单应用函数。
def apply_interactive_menu(args):

    """
    通过交互菜单更新任务参数。

    :param args: 命令行参数命名空间。
    :type args: argparse.Namespace
    :return: 更新后的命令行参数命名空间。
    :rtype: argparse.Namespace
    """

    # 打印运行环境概览。
    print_menu_runtime_profile(args.runtime_profile, args.recommended_max_workers)

    # 打印菜单标题。
    print_menu_title("DDI 协议直连工具", f"默认日期：{args.start_date} 至 {args.end_date}")

    # 读取 DDI 项目根目录。
    project_root = get_project_root()

    # 初始化菜单退出状态。
    args.menu_exit = False

    # 持续处理主菜单直到进入任务运行或退出。
    while True:

        # 读取主菜单功能选择。
        menu_action = select_menu_main_action()

        # 判断是否进入任务运行参数选择。
        if menu_action == "run":

            # 跳出主菜单循环。
            break

        # 判断是否进入商业启停管理。
        if menu_action == "account_status":

            # 执行商业启停管理菜单。
            manage_runtime_account_menu(project_root)

            # 继续读取主菜单。
            continue

        # 判断是否退出交互菜单。
        if menu_action == "exit":

            # 标记菜单退出状态。
            args.menu_exit = True

            # 返回命令行参数命名空间。
            return args

    # 读取商业选择。
    args.company = select_menu_company(args.company)

    # 读取任务动作。
    args.action = select_menu_action(args.action)

    # 读取数据类型。
    args.data_type = read_menu_input("请输入数据类型，全部表示按商业配置导出", args.data_type)

    # 读取日期模式。
    args.date_mode = read_menu_input("请输入日期模式（previous_month_full / previous_month_to_today / custom）", args.date_mode)

    # 根据日期模式读取或计算日期范围。
    if args.date_mode == "custom":

        # 读取自定义开始日期。
        args.start_date = read_menu_input("请输入开始日期", args.start_date)

        # 读取自定义结束日期。
        args.end_date = read_menu_input("请输入结束日期", args.end_date)

    # 按交互输入重建日期范围对象。
    args.date_range = DateRangeSpec.from_mode(args.date_mode, args.start_date, args.end_date)

    # 使用日期范围对象回填任务日期。
    args.start_date = args.date_range.start_date
    args.end_date = args.date_range.end_date

    # 读取控制台路径展示模式。
    args.console_path_mode = select_menu_path_mode(args.console_path_mode)

    # 读取最大线程数。
    args.max_workers = select_menu_max_workers(args.max_workers, args.recommended_max_workers)

    # 记录当前线程数来源。
    args.max_workers_source = "手动指定" if int(args.max_workers) != int(args.recommended_max_workers) else "配置推荐"

    # 返回更新后的命令行参数。
    return args


# 定义任务负责人列表解析函数。
def resolve_task_owner_names(args, project_root):

    """
    解析本次任务涉及的商业负责人列表。
    :param args: 命令行参数命名空间。
    :type args: argparse.Namespace
    :param project_root: DDI 项目根目录。
    :type project_root: str
    :return: 负责人列表。
    :rtype: list[str]
    """

    # 判断当前任务是否指定单个商业。
    if args.company:

        # 读取指定商业有效账号配置。
        account = get_account(args.company, project_root)

        # 读取指定商业负责人。
        owner_name = account.get("负责人", "")

        # 返回过滤空值后的负责人列表。
        return [owner_name] if owner_name else []

    # 读取当前启用商业账号列表。
    enabled_accounts = list(iter_enabled_accounts(project_root))

    # 读取当前启用商业的负责人集合。
    owner_names = {account.get("负责人", "") for company_name, account in enabled_accounts if account.get("负责人", "")}

    # 返回按文本排序后的负责人列表。
    return sorted(owner_names)


















# 定义最大并发数解析函数。
def resolve_max_workers(max_workers, task_count):

    """
    解析批量任务最大并发数量。

    :param max_workers: 命令行最大并发数量。
    :type max_workers: int
    :param task_count: 批量任务数量。
    :type task_count: int
    :return: 可用最大并发数量。
    :rtype: int
    """

    # 转换最大并发数为整数。
    worker_count = int(max_workers or 1)

    # 限制最小并发数。
    worker_count = max(1, worker_count)

    # 判断任务数量是否为空。
    if task_count <= 0:

        # 返回单线程并发数。
        return 1

    # 返回不超过任务数的并发数。
    return min(worker_count, task_count)


# 定义硬件列表日志文本构建函数。
def build_hardware_list_log_text(values, fallback_text="未知", limit=4):

    """
    构建列表型硬件日志文本。

    :param values: 硬件说明列表。
    :type values: list[str]
    :param fallback_text: 空列表兜底文本。
    :type fallback_text: str
    :param limit: 最大展示数量。
    :type limit: int
    :return: 硬件日志文本。
    :rtype: str
    """

    # 读取非空硬件说明。
    cleaned_values = [str(item) for item in values if item]

    # 判断硬件说明是否为空。
    if not cleaned_values:

        # 返回兜底文本。
        return fallback_text

    # 读取最大展示数量。
    max_count = max(1, int(limit or 1))

    # 读取展示范围内的硬件说明。
    visible_values = cleaned_values[:max_count]

    # 判断是否存在未展示硬件。
    if len(cleaned_values) > max_count:

        # 追加剩余数量说明。
        visible_values.append(f"另 {len(cleaned_values) - max_count} 项")

    # 返回硬件说明文本。
    return "；".join(visible_values)


# 定义启动运行环境概览日志打印函数。
def print_runtime_profile_summary(printer, runtime_profile, recommended_max_workers, current_max_workers, max_workers_source):

    """
    打印当前电脑运行环境概览与线程建议。

    :param printer: 标准日志打印器。
    :type printer: PrintHandler
    :param runtime_profile: 运行环境概览信息。
    :type runtime_profile: dict
    :param recommended_max_workers: 推荐线程数。
    :type recommended_max_workers: int
    :param current_max_workers: 当前任务线程数。
    :type current_max_workers: int
    :param max_workers_source: 当前线程数来源。
    :type max_workers_source: str
    :return: None。
    :rtype: None
    """

    # 打印运行环境概览分隔线。
    printer.section("运行环境概览", printer.join(printer.kv("主机", runtime_profile.get("machine_name", "未知"), "cyan"), printer.kv("系统", runtime_profile.get("system_text", "未知"), "cyan"), printer.kv("解释器", runtime_profile.get("python_text", "未知"), "cyan")))

    # 打印硬件信息与线程建议。
    printer.info(printer.join(printer.kv("CPU", runtime_profile.get("cpu_name", "未知"), "cyan"), printer.kv("逻辑核心", runtime_profile.get("logical_cpu_count", 1), "yellow"), printer.kv("物理内存", format_bytes_text(runtime_profile.get("total_memory_bytes", 0)), "green"), printer.kv("可用内存", format_bytes_text(runtime_profile.get("available_memory_bytes", 0)), "green"), printer.kv("推荐线程数", recommended_max_workers, "yellow"), printer.kv("当前线程数", current_max_workers, "cyan"), printer.kv("线程来源", max_workers_source, "cyan")))

    # 打印整机、主板和 BIOS 型号。
    printer.info(printer.join(printer.kv("整机", runtime_profile.get("computer_text") or "未知", "cyan"), printer.kv("主板", runtime_profile.get("baseboard_text") or "未知", "cyan"), printer.kv("BIOS", runtime_profile.get("bios_text") or "未知", "cyan")))

    # 打印内存条型号。
    printer.info(printer.join(printer.kv("内存装机", runtime_profile.get("memory_installed_text") or "未知", "green"), printer.kv("内存条", build_hardware_list_log_text(runtime_profile.get("memory_module_texts", [])), "green")))

    # 打印显卡和磁盘型号。
    printer.info(printer.join(printer.kv("显卡", build_hardware_list_log_text(runtime_profile.get("gpu_texts", []), limit=3), "cyan"), printer.kv("磁盘", build_hardware_list_log_text(runtime_profile.get("disk_texts", []), limit=4), "cyan")))

    # 打印网卡和显示器型号。
    printer.info(printer.join(printer.kv("网卡", build_hardware_list_log_text(runtime_profile.get("network_texts", []), limit=4), "cyan"), printer.kv("显示器", build_hardware_list_log_text(runtime_profile.get("monitor_texts", []), limit=3), "cyan")))

    # 打印电池和声卡型号。
    printer.info(printer.join(printer.kv("电池", build_hardware_list_log_text(runtime_profile.get("battery_texts", []), "未检测到电池", limit=2), "yellow"), printer.kv("声卡", build_hardware_list_log_text(runtime_profile.get("sound_texts", []), limit=3), "cyan")))


# 定义主执行函数。
def main():

    """
    执行 DDI 协议直连主流程。

    :return: 进程退出码。
    :rtype: int
    """

    # 初始化控制台中文编码。
    initialize_console_encoding()

    # 读取 DDI 项目根目录。
    project_root = get_project_root()

    # 补齐缺失的受管目录与用途说明文件。
    ensure_directory_documents(project_root)

    # 解析命令行参数。
    args = parse_args()

    # 打印启动像素头像。
    print_startup_avatar()

    # 打印当前版本启动更新日志。
    print_startup_changelog()

    # 根据启动方式应用交互菜单参数。
    if should_start_interactive_menu(args):

        # 读取交互菜单并更新任务参数。
        args = apply_interactive_menu(args)

    # 判断交互菜单是否选择退出。
    if getattr(args, "menu_exit", False):

        # 返回成功退出码。
        return 0

    # 标准化任务日期参数。
    args = normalize_args_dates(args)

    # 初始化标准日志打印器。
    printer = PrintHandler(path_mode=args.console_path_mode, project_root=project_root)

    # 打印运行环境概览与线程建议。
    print_runtime_profile_summary(printer, args.runtime_profile, args.recommended_max_workers, args.max_workers, args.max_workers_source)

    # 判断当前任务是否为批量并发模式。
    is_batch_mode = not bool(args.company)

    # 初始化 Excel 任务日志记录器。
    task_logger = TaskExcelLogger(args.log_dir, args.start_date, args.end_date, task_action=args.action, task_data_type=args.data_type, realtime_save=not is_batch_mode)

    # 捕获主流程异常并转换为进程退出码。
    try:

        # 确保运行期商业启停配置文件存在。
        runtime_config_path = ensure_runtime_account_config(project_root)

        # 打印运行期商业启停配置路径。
        printer.info(printer.kv("商业启停配置", printer.path(runtime_config_path), "cyan"))

        # 校验查询日期是否完整。
        if not args.start_date or not args.end_date:

            # 抛出日期缺失异常。
            raise ValueError("请在 task_config.py 或命令行参数中配置 start_date 和 end_date")

        # 创建 Cookie 输出目录。
        os.makedirs(args.cookie_dir, exist_ok=True)

        # 创建结果输出目录。
        os.makedirs(args.output_dir, exist_ok=True)

        # 创建运行日志输出目录。
        os.makedirs(args.log_dir, exist_ok=True)

        # 处理单商业指定执行模式。
        if args.company:

            # 构建单商业名称集合。
            company_names = [args.company]

        # 处理所有启用商业的批量执行模式。
        else:

            # 读取所有运行期启用商业名称。
            company_names = [company_name for company_name, _ in iter_enabled_accounts(project_root)]

        # 构建终端与图形入口共用的任务请求。
        request = TaskRequest(action=args.action, data_type=args.data_type, start_date=args.start_date, end_date=args.end_date, cookie_dir=args.cookie_dir, output_dir=args.output_dir, log_dir=args.log_dir, max_workers=args.max_workers, copy_excel=args.copy_excel, console_path_mode=args.console_path_mode, console_output_enabled=True, date_range=args.date_range)

        # 创建终端复用的公共无界面任务运行时。
        runtime = DdiTaskRuntime(project_root, TerminalTaskEventSink(printer))

        # 通过公共运行时执行单商业或批量协议任务。
        execution = runtime.execute(request, company_names)

        # 打印公共运行时保存的 Excel 日志路径。
        printer.success(printer.kv("本次运行日志已保存", printer.path(execution.log_path), "green"))

        # 根据失败数量返回进程退出码。
        return 0 if execution.task_result.failure_count == 0 else 1

    # 处理用户手动中断。
    except KeyboardInterrupt as error:

        # 打印手动中断日志。
        printer.warning("任务已手动中断")

        # 记录手动中断日志。
        record_task_log(task_logger, "", "", "", "手动中断", "中断", "用户手动中断任务", error_detail=error)

        # 保存手动中断时的 Excel 日志。
        log_path = task_logger.save()

        # 打印 Excel 日志保存路径。
        printer.warning(printer.kv("本次运行日志已保存", printer.path(log_path), "yellow"))

        # 返回中断退出码。
        return 130

    # 处理授权校验异常。
    except LicenseError as error:

        # 打印授权校验失败日志。
        printer.error(f"授权校验失败: {error}")

        # 记录授权校验失败日志。
        record_task_log(task_logger, "", "", "", "授权校验", "失败", "当前运行环境授权校验失败", error_detail=error)

        # 保存授权校验失败时的 Excel 日志。
        log_path = task_logger.save()

        # 打印 Excel 日志保存路径。
        printer.warning(printer.kv("本次运行日志已保存", printer.path(log_path), "yellow"))

        # 返回失败退出码。
        return 1

    # 处理主流程异常。
    except Exception as error:

        # 格式化主流程异常堆栈。
        error_traceback = format_exception_traceback(error)

        # 打印主流程失败日志。
        printer.error(f"任务执行失败: {error}")

        # 打印主流程异常堆栈标题。
        printer.error("异常堆栈如下：")

        # 打印主流程异常堆栈。
        print(error_traceback)

        # 记录主流程失败日志。
        record_task_log(task_logger, "", "", "", resolve_error_stage(error), "失败", "主流程执行失败", error_detail=error_traceback)

        # 保存主流程失败时的 Excel 日志。
        log_path = task_logger.save()

        # 打印 Excel 日志保存路径。
        printer.warning(printer.kv("本次运行日志已保存", printer.path(log_path), "yellow"))

        # 返回失败退出码。
        return 1


# 定义命令行入口执行函数。
def run_cli_entrypoint():

    """
    执行命令行入口并在错误退出前处理控制台停留。

    :return: 进程退出码。
    :rtype: int
    """

    # 执行主流程并读取退出码。
    exit_code = main()

    # 在错误退出前按运行态决定是否停留控制台。
    pause_console_before_error_exit(exit_code)

    # 返回主流程退出码。
    return exit_code


# 判断当前文件是否以脚本方式运行。
if __name__ == "__main__":

    # 执行主流程并设置进程退出码。
    sys.exit(run_cli_entrypoint())

