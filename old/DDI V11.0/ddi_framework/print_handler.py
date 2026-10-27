# -*- coding: utf-8 -*-
"""
DDI 控制台日志打印工具。

本模块负责输出带时间差、状态标签、颜色高亮和阶段分隔线的标准控制台日志。
"""

# 导入时间计数模块。
import time

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入系统输出模块。
import sys

# 导入日期时间模块。
from datetime import datetime

# 导入线程锁模块。
from threading import RLock

# 导入 Colorama 控制台兼容初始化函数。
from colorama import init as colorama_init

# 导入无界面任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入 ANSI 控制序列清理函数。
from ddi_framework.task_core import strip_ansi_escape_codes


# 定义 DDI 标准控制台输出器。
class PrintHandler:

    """
    DDI 标准控制台输出器。

    :return: 控制台输出器实例。
    :rtype: PrintHandler
    """

    # 保存上一条日志的单调时钟时间。
    last_message_time = None

    # 保存控制台输出锁。
    print_lock = RLock()

    # 保存动态状态行是否可见。
    live_status_visible = False

    # 定义控制台输出器初始化方法。
    def __init__(self, path_mode="relative", project_root=None, event_sink=None, console_output_enabled=True):

        """
        初始化控制台颜色配置。

        :param path_mode: 文件路径展示模式。
        :type path_mode: str
        :param project_root: 项目根目录。
        :type project_root: str | None
        :param event_sink: 可选的无界面任务事件接收器。
        :type event_sink: object | None
        :param console_output_enabled: 是否向标准输出镜像日志。
        :type console_output_enabled: bool
        :return: None。
        :rtype: None
        """

        # 初始化 Windows 控制台 ANSI 转换层。
        colorama_init(autoreset=False, strip=False)

        # 配置 ANSI 颜色编码映射。
        self.colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "cyan": "\033[96m",
            "gray": "\033[90m",
            "reset": "\033[0m",
        }

        # 保存控制台路径展示模式。
        self.path_mode = path_mode

        # 保存项目根目录路径。
        self.project_root = project_root or os.getcwd()

        # 保存可选的结构化事件接收器。
        self.event_sink = event_sink

        # 保存标准输出镜像开关。
        self.console_output_enabled = bool(console_output_enabled)

    # 定义信息日志输出方法。
    def info(self, message):

        """
        打印信息日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按信息状态打印日志。
        self._print("信息", message, "blue")

    # 定义成功日志输出方法。
    def success(self, message):

        """
        打印成功日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按成功状态打印日志。
        self._print("成功", message, "green")

    # 定义警告日志输出方法。
    def warning(self, message):

        """
        打印警告日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按警告状态打印日志。
        self._print("警告", message, "yellow")

    # 定义错误日志输出方法。
    def error(self, message):

        """
        打印错误日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按错误状态打印日志。
        self._print("错误", message, "red")

    # 定义等待日志输出方法。
    def wait(self, message):

        """
        打印等待日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按等待状态打印日志。
        self._print("等待", message, "cyan")

    # 定义商业上下文输出器构建方法。
    def for_company(self, company_name):

        """
        构建带商业名称上下文的控制台输出器。

        :param company_name: 商业公司名称。
        :type company_name: str
        :return: 商业上下文控制台输出器。
        :rtype: CompanyPrintHandler
        """

        # 返回商业上下文输出器。
        return CompanyPrintHandler(self, company_name)

    # 定义缓冲输出器构建方法。
    def buffered(self):

        """
        构建内存缓冲控制台输出器。

        :return: 内存缓冲控制台输出器。
        :rtype: BufferedPrintHandler
        """

        # 返回内存缓冲输出器。
        return BufferedPrintHandler(self)

    # 定义阶段分隔线输出方法。
    def section(self, title, detail=""):

        """
        打印阶段分隔线。

        :param title: 阶段标题。
        :type title: str
        :param detail: 阶段补充信息。
        :type detail: str
        :return: None。
        :rtype: None
        """

        # 构建阶段标题文本。
        section_text = f" {title} "

        # 拼接阶段补充信息。
        if detail:

            # 将阶段补充信息追加到标题文本中。
            section_text = f"{section_text}| {detail} "

        # 根据标题长度生成分隔线尾部。
        tail = "─" * max(8, 86 - len(section_text))

        # 判断是否需要镜像阶段分隔线到终端。
        if self.console_output_enabled:

            # 使用输出锁保护多线程控制台输出。
            with PrintHandler.print_lock:

                # 清理动态状态行。
                self.clear_live_status()

                # 输出阶段标题前的空行。
                print()

                # 输出带颜色的阶段分隔线。
                print(f"{self._time_badge()} {self._color('┌─' + section_text + tail, 'cyan')}")

        # 发布阶段分隔线事件。
        self.publish_event("section", title, "信息", {"详情": detail})

    # 定义高亮值构建方法。
    def value(self, text, color="cyan"):

        """
        构建高亮值文本。

        :param text: 需要高亮的值。
        :type text: object
        :param color: 颜色名称。
        :type color: str
        :return: 高亮值文本。
        :rtype: str
        """

        # 返回带颜色的文本值。
        return self._color(str(text), color)

    # 定义键值片段构建方法。
    def kv(self, key, value, color="cyan"):

        """
        构建高亮键值片段。

        :param key: 字段名称。
        :type key: str
        :param value: 字段值。
        :type value: object
        :param color: 值颜色。
        :type color: str
        :return: 键值片段。
        :rtype: str
        """

        # 返回带高亮值的键值文本。
        return f"{key}: {self.value(value, color)}"

    # 定义路径展示文本构建方法。
    def path(self, file_path):

        """
        根据控制台配置格式化文件路径展示文本。

        :param file_path: 原始文件路径。
        :type file_path: str
        :return: 控制台展示路径。
        :rtype: str
        """

        # 空路径直接返回空字符串。
        if not file_path:

            # 返回空路径展示值。
            return ""

        # 转换原始路径为字符串。
        path_text = str(file_path)

        # 绝对路径模式返回标准绝对路径。
        if self.path_mode == "absolute":

            # 返回绝对路径展示值。
            return os.path.abspath(path_text)

        # 读取标准绝对路径。
        absolute_path = os.path.abspath(path_text)

        # 读取标准项目根目录。
        absolute_root = os.path.abspath(self.project_root)

        # 捕获跨盘符或非法路径导致的相对路径转换异常。
        try:

            # 计算相对项目根目录的路径。
            relative_path = os.path.relpath(absolute_path, absolute_root)

        # 转换失败时保留原始路径文本。
        except ValueError:

            # 返回原始路径展示值。
            return path_text

        # 项目外路径保留原始路径文本。
        if relative_path.startswith(".."):

            # 返回原始路径展示值。
            return path_text

        # 返回项目内相对路径。
        return relative_path

    # 定义日志片段拼接方法。
    def join(self, *parts):

        """
        使用竖线拼接日志片段。

        :param parts: 日志片段。
        :type parts: tuple[object, ...]
        :return: 拼接后的日志文本。
        :rtype: str
        """

        # 返回过滤空片段后的拼接文本。
        return " | ".join([str(part) for part in parts if str(part)])

    # 定义标准日志输出方法。
    def _print(self, status, message, color):

        """
        打印一条标准日志。

        :param status: 状态名称。
        :type status: str
        :param message: 日志正文。
        :type message: str
        :param color: ANSI 颜色名称。
        :type color: str
        :return: None。
        :rtype: None
        """

        # 构建状态标签。
        badge = self._color(f"[{status}]", color)

        # 计算状态标签后的对齐空格。
        padding = " " * max(1, 6 - len(status))

        # 判断是否需要镜像标准日志到终端。
        if self.console_output_enabled:

            # 使用输出锁保护多线程控制台输出。
            with PrintHandler.print_lock:

                # 清理动态状态行。
                self.clear_live_status()

                # 输出标准日志行。
                print(f"{badge}{padding}{self._time_badge()} {message}")

        # 发布标准日志事件。
        self.publish_event("log", message, status)

    # 定义结构化事件发布方法。
    def publish_event(self, event_type, message, status="信息", payload=None):

        """
        向可选展示层发布不包含 GUI 类型的结构化事件。

        :param event_type: 事件分类。
        :type event_type: str
        :param message: 事件说明。
        :type message: object
        :param status: 事件状态。
        :type status: str
        :param payload: 事件扩展数据。
        :type payload: dict | None
        :return: None。
        :rtype: None
        """

        # 判断是否配置事件接收器。
        if self.event_sink is None:

            # 未配置事件接收器时直接结束。
            return

        # 构建无界面结构化事件对象。
        event = TaskEvent(str(event_type), strip_ansi_escape_codes(message), strip_ansi_escape_codes(status), payload=dict(payload or {}))

        # 发布结构化事件。
        self.event_sink.publish(event)

    # 定义动态状态行输出方法。
    def live_status(self, message):

        """
        在控制台底部刷新动态任务状态。

        :param message: 动态状态文本。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 构建动态状态文本。
        status_text = self.build_live_status_text(message)

        # 判断是否需要镜像动态状态到终端。
        if self.console_output_enabled:

            # 使用输出锁保护动态状态输出。
            with PrintHandler.print_lock:

                # 清理当前控制台行并输出动态状态。
                sys.stdout.write(f"\r\033[2K{status_text}")

                # 刷新标准输出缓冲区。
                sys.stdout.flush()

                # 记录动态状态行可见。
                PrintHandler.live_status_visible = True

        # 发布动态进度事件。
        self.publish_event("progress", message, "信息")

    # 定义动态状态行清理方法。
    def clear_live_status(self):

        """
        清理控制台底部动态任务状态。

        :return: None。
        :rtype: None
        """

        # 判断终端镜像关闭或动态状态行未显示。
        if not self.console_output_enabled or not PrintHandler.live_status_visible:

            # 返回空值。
            return

        # 清理当前控制台行。
        sys.stdout.write("\r\033[2K")

        # 刷新标准输出缓冲区。
        sys.stdout.flush()

        # 记录动态状态行已清理。
        PrintHandler.live_status_visible = False

    # 定义动态状态文本构建方法。
    def build_live_status_text(self, message):

        """
        构建动态状态行文本。

        :param message: 原始状态文本。
        :type message: object
        :return: 动态状态行文本。
        :rtype: str
        """

        # 移除状态文本中的 ANSI 颜色编码。
        clean_message = re.sub(r"\x1b\[[0-9;]*m", "", str(message))

        # 限制动态状态文本长度。
        clean_message = clean_message[-140:]

        # 返回动态状态行文本。
        return self._color(f"正在执行: {clean_message}", "cyan")

    # 定义时间标记构建方法。
    def _time_badge(self):

        """
        构建时间标记。

        :return: 时间标记。
        :rtype: str
        """

        # 读取当前时分秒文本。
        now_text = datetime.now().strftime("%H:%M:%S")

        # 读取当前单调时钟时间。
        now_tick = time.monotonic()

        # 处理第一条日志的时间差。
        if PrintHandler.last_message_time is None:

            # 第一条日志的时间差固定为零。
            delta_seconds = 0.0

        # 处理非第一条日志的时间差。
        else:

            # 计算当前日志与上一条日志的间隔秒数。
            delta_seconds = now_tick - PrintHandler.last_message_time

        # 更新上一条日志时间。
        PrintHandler.last_message_time = now_tick

        # 返回带颜色的时间标记。
        return self._color(f"{now_text} +{delta_seconds:.1f}s", "gray")

    # 定义颜色包装方法。
    def _color(self, text, color):

        """
        添加 ANSI 颜色。

        :param text: 原始文本。
        :type text: str
        :param color: 颜色名称。
        :type color: str
        :return: 带颜色文本。
        :rtype: str
        """

        # 读取指定颜色编码。
        color_code = self.colors.get(color, "")

        # 读取颜色重置编码。
        reset_code = self.colors["reset"]

        # 返回颜色包装后的文本。
        return f"{color_code}{text}{reset_code}"


# 定义带商业上下文的控制台输出器。
class CompanyPrintHandler:

    """
    带商业上下文的控制台输出器。

    :param base_printer: 基础控制台输出器。
    :type base_printer: PrintHandler
    :param company_name: 商业公司名称。
    :type company_name: str
    :return: 商业上下文控制台输出器实例。
    :rtype: CompanyPrintHandler
    """

    # 定义商业上下文输出器初始化方法。
    def __init__(self, base_printer, company_name):

        """
        初始化商业上下文控制台输出器。

        :param base_printer: 基础控制台输出器。
        :type base_printer: PrintHandler
        :param company_name: 商业公司名称。
        :type company_name: str
        :return: None。
        :rtype: None
        """

        # 保存基础控制台输出器。
        self.base_printer = base_printer

        # 保存商业公司名称。
        self.company_name = company_name

    # 定义信息日志输出方法。
    def info(self, message):

        """
        打印带商业上下文的信息日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 输出带商业上下文的信息日志。
        self.base_printer.info(self.with_company(message))

    # 定义成功日志输出方法。
    def success(self, message):

        """
        打印带商业上下文的成功日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 输出带商业上下文的成功日志。
        self.base_printer.success(self.with_company(message))

    # 定义警告日志输出方法。
    def warning(self, message):

        """
        打印带商业上下文的警告日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 输出带商业上下文的警告日志。
        self.base_printer.warning(self.with_company(message))

    # 定义错误日志输出方法。
    def error(self, message):

        """
        打印带商业上下文的错误日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 输出带商业上下文的错误日志。
        self.base_printer.error(self.with_company(message))

    # 定义等待日志输出方法。
    def wait(self, message):

        """
        打印带商业上下文的等待日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 输出带商业上下文的等待日志。
        self.base_printer.wait(self.with_company(message))

    # 定义阶段分隔线输出方法。
    def section(self, title, detail=""):

        """
        打印带商业上下文的阶段分隔线。

        :param title: 阶段标题。
        :type title: str
        :param detail: 阶段补充信息。
        :type detail: str
        :return: None。
        :rtype: None
        """

        # 输出原始阶段分隔线。
        self.base_printer.section(title, detail)

    # 定义商业上下文消息构建方法。
    def with_company(self, message):

        """
        构建带商业名称前缀的日志正文。

        :param message: 原始日志正文。
        :type message: object
        :return: 带商业名称前缀的日志正文。
        :rtype: str
        """

        # 构建商业名称前缀。
        company_prefix = self.base_printer.kv("商业", self.company_name, "cyan")

        # 返回带商业名称前缀的日志正文。
        return self.base_printer.join(company_prefix, message)

    # 定义高亮值构建方法。
    def value(self, text, color="cyan"):

        """
        构建高亮值文本。

        :param text: 需要高亮的值。
        :type text: object
        :param color: 颜色名称。
        :type color: str
        :return: 高亮值文本。
        :rtype: str
        """

        # 返回基础输出器的高亮值。
        return self.base_printer.value(text, color)

    # 定义键值片段构建方法。
    def kv(self, key, value, color="cyan"):

        """
        构建高亮键值片段。

        :param key: 字段名称。
        :type key: str
        :param value: 字段值。
        :type value: object
        :param color: 值颜色。
        :type color: str
        :return: 键值片段。
        :rtype: str
        """

        # 返回基础输出器的键值片段。
        return self.base_printer.kv(key, value, color)

    # 定义路径展示文本构建方法。
    def path(self, file_path):

        """
        根据控制台配置格式化文件路径展示文本。

        :param file_path: 原始文件路径。
        :type file_path: str
        :return: 控制台展示路径。
        :rtype: str
        """

        # 返回基础输出器的路径展示文本。
        return self.base_printer.path(file_path)

    # 定义日志片段拼接方法。
    def join(self, *parts):

        """
        使用竖线拼接日志片段。

        :param parts: 日志片段。
        :type parts: tuple[object, ...]
        :return: 拼接后的日志文本。
        :rtype: str
        """

        # 返回基础输出器的拼接文本。
        return self.base_printer.join(*parts)


# 定义内存缓冲控制台输出器。
class BufferedPrintHandler:

    """
    内存缓冲控制台输出器。

    :param base_printer: 基础控制台输出器。
    :type base_printer: PrintHandler
    :return: 内存缓冲控制台输出器实例。
    :rtype: BufferedPrintHandler
    """

    # 定义缓冲输出器初始化方法。
    def __init__(self, base_printer):

        """
        初始化内存缓冲控制台输出器。

        :param base_printer: 基础控制台输出器。
        :type base_printer: PrintHandler
        :return: None。
        :rtype: None
        """

        # 保存基础控制台输出器。
        self.base_printer = base_printer

        # 初始化缓冲日志行列表。
        self.lines = []

        # 初始化缓冲输出器上一条日志时间。
        self.last_message_time = None

    # 定义信息日志输出方法。
    def info(self, message):

        """
        缓冲信息日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按信息状态缓冲日志。
        self._print("信息", message, "blue")

    # 定义成功日志输出方法。
    def success(self, message):

        """
        缓冲成功日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按成功状态缓冲日志。
        self._print("成功", message, "green")

    # 定义警告日志输出方法。
    def warning(self, message):

        """
        缓冲警告日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按警告状态缓冲日志。
        self._print("警告", message, "yellow")

    # 定义错误日志输出方法。
    def error(self, message):

        """
        缓冲错误日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按错误状态缓冲日志。
        self._print("错误", message, "red")

    # 定义等待日志输出方法。
    def wait(self, message):

        """
        缓冲等待日志。

        :param message: 日志正文。
        :type message: str
        :return: None。
        :rtype: None
        """

        # 按等待状态缓冲日志。
        self._print("等待", message, "cyan")

    # 定义商业上下文输出器构建方法。
    def for_company(self, company_name):

        """
        构建带商业名称上下文的缓冲输出器。

        :param company_name: 商业公司名称。
        :type company_name: str
        :return: 商业上下文控制台输出器。
        :rtype: CompanyPrintHandler
        """

        # 返回商业上下文输出器。
        return CompanyPrintHandler(self, company_name)

    # 定义阶段分隔线输出方法。
    def section(self, title, detail=""):

        """
        缓冲阶段分隔线。

        :param title: 阶段标题。
        :type title: str
        :param detail: 阶段补充信息。
        :type detail: str
        :return: None。
        :rtype: None
        """

        # 构建阶段标题文本。
        section_text = f" {title} "

        # 拼接阶段补充信息。
        if detail:

            # 将阶段补充信息追加到标题文本中。
            section_text = f"{section_text}| {detail} "

        # 根据标题长度生成分隔线尾部。
        tail = "─" * max(8, 86 - len(section_text))

        # 缓冲阶段标题前的空行。
        self.lines.append("")

        # 缓冲带颜色的阶段分隔线。
        self.lines.append(f"{self._time_badge()} {self._color('┌─' + section_text + tail, 'cyan')}")

        # 刷新动态状态行。
        self.base_printer.live_status(f"{title} {detail}")

        # 发布缓冲阶段分隔线事件。
        self.base_printer.publish_event("section", title, "信息", {"详情": detail})

    # 定义缓冲输出方法。
    def flush(self):

        """
        输出并清空全部缓冲日志。

        :return: None。
        :rtype: None
        """

        # 判断是否需要镜像缓冲日志到终端。
        if self.base_printer.console_output_enabled:

            # 使用输出锁保护整块控制台输出。
            with PrintHandler.print_lock:

                # 清理动态状态行。
                self.base_printer.clear_live_status()

                # 遍历缓冲日志行。
                for line in self.lines:

                    # 输出当前缓冲日志行。
                    print(line)

        # 清空缓冲日志行。
        self.lines.clear()

    # 定义高亮值构建方法。
    def value(self, text, color="cyan"):

        """
        构建高亮值文本。

        :param text: 需要高亮的值。
        :type text: object
        :param color: 颜色名称。
        :type color: str
        :return: 高亮值文本。
        :rtype: str
        """

        # 返回基础输出器的高亮值。
        return self.base_printer.value(text, color)

    # 定义键值片段构建方法。
    def kv(self, key, value, color="cyan"):

        """
        构建高亮键值片段。

        :param key: 字段名称。
        :type key: str
        :param value: 字段值。
        :type value: object
        :param color: 值颜色。
        :type color: str
        :return: 键值片段。
        :rtype: str
        """

        # 返回基础输出器的键值片段。
        return self.base_printer.kv(key, value, color)

    # 定义路径展示文本构建方法。
    def path(self, file_path):

        """
        根据控制台配置格式化文件路径展示文本。

        :param file_path: 原始文件路径。
        :type file_path: str
        :return: 控制台展示路径。
        :rtype: str
        """

        # 返回基础输出器的路径展示文本。
        return self.base_printer.path(file_path)

    # 定义日志片段拼接方法。
    def join(self, *parts):

        """
        使用竖线拼接日志片段。

        :param parts: 日志片段。
        :type parts: tuple[object, ...]
        :return: 拼接后的日志文本。
        :rtype: str
        """

        # 返回基础输出器的拼接文本。
        return self.base_printer.join(*parts)

    # 定义标准日志缓冲方法。
    def _print(self, status, message, color):

        """
        缓冲一条标准日志。

        :param status: 状态名称。
        :type status: str
        :param message: 日志正文。
        :type message: str
        :param color: ANSI 颜色名称。
        :type color: str
        :return: None。
        :rtype: None
        """

        # 构建状态标签。
        badge = self._color(f"[{status}]", color)

        # 计算状态标签后的对齐空格。
        padding = " " * max(1, 6 - len(status))

        # 缓冲标准日志行。
        self.lines.append(f"{badge}{padding}{self._time_badge()} {message}")

        # 刷新动态状态行。
        self.base_printer.live_status(message)

        # 发布缓冲标准日志事件。
        self.base_printer.publish_event("log", message, status)

    # 定义时间标记构建方法。
    def _time_badge(self):

        """
        构建缓冲日志时间标记。

        :return: 时间标记。
        :rtype: str
        """

        # 读取当前时分秒文本。
        now_text = datetime.now().strftime("%H:%M:%S")

        # 读取当前单调时钟时间。
        now_tick = time.monotonic()

        # 处理第一条缓冲日志的时间差。
        if self.last_message_time is None:

            # 第一条缓冲日志的时间差固定为零。
            delta_seconds = 0.0

        # 处理非第一条缓冲日志的时间差。
        else:

            # 计算当前日志与上一条缓冲日志的间隔秒数。
            delta_seconds = now_tick - self.last_message_time

        # 更新上一条缓冲日志时间。
        self.last_message_time = now_tick

        # 返回带颜色的时间标记。
        return self._color(f"{now_text} +{delta_seconds:.1f}s", "gray")

    # 定义颜色包装方法。
    def _color(self, text, color):

        """
        添加 ANSI 颜色。

        :param text: 原始文本。
        :type text: str
        :param color: 颜色名称。
        :type color: str
        :return: 带颜色文本。
        :rtype: str
        """

        # 返回基础输出器的颜色文本。
        return self.base_printer._color(text, color)
