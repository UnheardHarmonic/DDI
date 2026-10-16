# -*- coding: utf-8 -*-
"""
DDI 任务 Excel 日志记录器。

本模块负责记录单次运行中的商业、数据类型、执行阶段、执行状态、记录数量、文件路径和异常原因，并在任务结束时生成 Excel 日志文件。
"""

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入时间增量模块。
from datetime import timedelta

# 导入线程锁模块。
from threading import RLock


# 定义 DDI 任务 Excel 日志记录器。
class TaskExcelLogger:

    """
    DDI 任务 Excel 日志记录器。

    :param output_dir: 日志输出目录。
    :type output_dir: str
    :param task_start_date: 任务查询开始日期。
    :type task_start_date: str
    :param task_end_date: 任务查询结束日期。
    :type task_end_date: str
    :return: DDI 任务 Excel 日志记录器实例。
    :rtype: TaskExcelLogger
    """

    # 定义日志记录器初始化方法。
    def __init__(self, output_dir, task_start_date, task_end_date, task_action="", task_data_type="", realtime_save=True, timeline_listener=None):

        """
        初始化 DDI 任务 Excel 日志记录器。

        :param output_dir: 日志输出目录。
        :type output_dir: str
        :param task_start_date: 任务查询开始日期。
        :type task_start_date: str
        :param task_end_date: 任务查询结束日期。
        :type task_end_date: str
        :param task_action: 本次任务动作。
        :type task_action: str
        :param task_data_type: 本次任务数据类型。
        :type task_data_type: str
        :param realtime_save: 是否记录后实时保存日志文件。
        :type realtime_save: bool
        :param timeline_listener: 接收脱敏阶段时间线记录的可选回调。
        :type timeline_listener: callable | None
        :return: None。
        :rtype: None
        """

        # 保存日志输出目录。
        self.output_dir = output_dir

        # 保存任务查询开始日期。
        self.task_start_date = task_start_date

        # 保存任务查询结束日期。
        self.task_end_date = task_end_date

        # 保存本次任务动作。
        self.task_action = task_action

        # 保存本次任务数据类型。
        self.task_data_type = task_data_type

        # 保存实时保存开关。
        self.realtime_save = bool(realtime_save)

        # 保存可选的时间线记录监听回调。
        self.timeline_listener = timeline_listener

        # 保存本次任务开始时间。
        self.started_at = datetime.now()

        # 初始化日志记录列表。
        self.rows = []

        # 初始化日志写入锁。
        self.lock = RLock()

        # 构建固定日志文件路径。
        self.output_path = self.build_output_path()

        # 初始化最近一次保存异常。
        self.last_save_error = ""

    # 定义任务日志记录方法。
    def record(self, company_name="", platform_name="", data_type="", stage="", status="", message="", record_count="", file_path="", cookie_path="", error_detail="", started_at=None, ended_at=None):

        """
        记录一条 DDI 任务执行日志。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param platform_name: 平台标识。
        :type platform_name: str
        :param data_type: 数据类型名称。
        :type data_type: str
        :param stage: 执行阶段。
        :type stage: str
        :param status: 执行状态。
        :type status: str
        :param message: 执行说明。
        :type message: str
        :param record_count: 记录数量。
        :type record_count: int | str
        :param file_path: 业务输出文件路径。
        :type file_path: str
        :param cookie_path: Cookie 文件路径。
        :type cookie_path: str
        :param error_detail: 异常详情。
        :type error_detail: str
        :param started_at: 阶段开始时间。
        :type started_at: datetime | None
        :param ended_at: 阶段结束时间。
        :type ended_at: datetime | None
        :return: None。
        :rtype: None
        """

        # 使用日志锁保护多线程日志写入。
        with self.lock:

            # 使用当前时间补齐阶段结束时间。
            actual_ended_at = ended_at or datetime.now()

            # 使用阶段结束时间补齐阶段开始时间。
            actual_started_at = started_at or actual_ended_at

            # 计算阶段耗时秒数。
            duration_seconds = round((actual_ended_at - actual_started_at).total_seconds(), 2)

            # 转换业务输出路径为绝对路径。
            absolute_file_path = self.absolute_path(file_path)

            # 转换 Cookie 路径为绝对路径。
            absolute_cookie_path = self.absolute_path(cookie_path)

            # 构建完整结构化日志行。
            log_row = {
                "运行日期": self.started_at.strftime("%Y-%m-%d"),
                "任务开始时间": self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "阶段开始时间": actual_started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "阶段结束时间": actual_ended_at.strftime("%Y-%m-%d %H:%M:%S"),
                "耗时秒数": duration_seconds,
                "商业名称": company_name,
                "平台": platform_name,
                "数据类型": data_type,
                "查询开始日期": self.task_start_date,
                "查询结束日期": self.task_end_date,
                "执行阶段": stage,
                "执行状态": status,
                "记录数量": record_count,
                "业务文件绝对路径": absolute_file_path,
                "Cookie文件绝对路径": absolute_cookie_path,
                "执行说明": message,
                "异常详情": str(error_detail) if error_detail else "",
            }

            # 追加完整结构化日志行。
            self.rows.append(log_row)

            # 发布不包含路径和异常详情的阶段时间线记录。
            self.publish_timeline_row(log_row, actual_started_at, actual_ended_at)

            # 判断是否启用实时保存。
            if self.realtime_save:

                # 实时保存当前日志文件。
                self.save_safely()

    # 定义脱敏时间线记录发布方法。
    def publish_timeline_row(self, log_row, started_at, ended_at):

        """
        向可选监听器发布仅用于展示的阶段时间线记录。

        :param log_row: 已保存的完整任务日志行。
        :type log_row: dict
        :param started_at: 阶段开始时间。
        :type started_at: datetime
        :param ended_at: 阶段结束时间。
        :type ended_at: datetime
        :return: None。
        :rtype: None
        """

        # 判断时间线监听器是否不可用。
        if not callable(self.timeline_listener):

            # 结束时间线发布处理。
            return

        # 构建不含路径与异常详情的时间线展示载荷。
        timeline_row = {"商业名称": log_row.get("商业名称", ""), "平台": log_row.get("平台", ""), "数据类型": log_row.get("数据类型", ""), "执行阶段": log_row.get("执行阶段", ""), "执行状态": log_row.get("执行状态", ""), "记录数量": log_row.get("记录数量", ""), "执行说明": log_row.get("执行说明", ""), "阶段开始时间": started_at, "阶段结束时间": ended_at, "耗时秒数": log_row.get("耗时秒数", 0)}

        # 防止展示监听异常影响正式 Excel 日志写入。
        try:

            # 调用时间线监听器。
            self.timeline_listener(timeline_row)

        # 忽略展示层监听异常。
        except Exception:

            # 保持业务日志写入成功状态。
            return

    # 定义实时保存方法。
    def save_safely(self):

        """
        安全保存当前 Excel 日志文件。

        :return: None。
        :rtype: None
        """

        # 捕获实时保存异常，避免日志保存中断业务任务。
        try:

            # 保存当前 Excel 日志文件。
            self.save()

            # 清空最近一次保存异常。
            self.last_save_error = ""

        # 记录实时保存异常。
        except Exception as error:

            # 保存最近一次日志写入异常。
            self.last_save_error = str(error)

    # 定义绝对路径转换方法。
    def absolute_path(self, file_path):

        """
        转换文件路径为绝对路径。

        :param file_path: 原始文件路径。
        :type file_path: str
        :return: 绝对文件路径。
        :rtype: str
        """

        # 空路径直接返回空字符串。
        if not file_path:

            # 返回空字符串。
            return ""

        # 返回绝对路径。
        return os.path.abspath(str(file_path))

    # 定义日志文件路径构建方法。
    def build_output_path(self):

        """
        构建本次任务 Excel 日志文件路径。

        :return: Excel 日志文件路径。
        :rtype: str
        """

        # 创建日志输出目录。
        os.makedirs(self.output_dir, exist_ok=True)

        # 构建本次运行时间标签。
        run_label = self.started_at.strftime("%Y%m%d_%H%M%S")

        # 构建日志文件名称。
        file_name = f"DDI运行日志_{run_label}.xlsx"

        # 返回日志文件完整路径。
        return os.path.join(self.output_dir, file_name)

    # 定义 Excel 日志保存方法。
    def save(self):

        """
        保存 DDI 任务 Excel 日志。

        :return: Excel 日志文件路径。
        :rtype: str
        """

        # 导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 导入单元格填充样式。
        from openpyxl.styles import PatternFill

        # 导入单元格字体样式。
        from openpyxl.styles import Font

        # 导入单元格对齐样式。
        from openpyxl.styles import Alignment

        # 导入单元格边框样式。
        from openpyxl.styles import Border

        # 导入边框线条样式。
        from openpyxl.styles import Side

        # 导入单元格批注对象。
        from openpyxl.comments import Comment

        # 导入列字母转换函数。
        from openpyxl.utils import get_column_letter

        # 使用日志锁保护 Excel 日志保存。
        with self.lock:

            # 读取固定日志文件输出路径。
            output_path = self.output_path

            # 创建 Excel 工作簿。
            workbook = Workbook()

            # 读取默认工作表。
            worksheet = workbook.active

            # 设置工作表名称。
            worksheet.title = "本次运行明细"

            # 构建日志表头。
            headers = list(self.default_empty_row().keys())

            # 写入日志表头。
            worksheet.append(headers)

            # 遍历日志记录写入明细行。
            for row in self.rows:

                # 按表头顺序写入一行日志。
                worksheet.append([row.get(header, "") for header in headers])

            # 设置表头样式。
            self.style_header(worksheet, headers, PatternFill, Font, Alignment)

            # 设置数据行状态样式。
            self.style_status_rows(worksheet, headers, PatternFill, Font)

            # 设置列宽和冻结窗格。
            self.style_layout(worksheet, headers, get_column_letter, Alignment, Font, Border, Side)

            # 创建运行摘要工作表。
            summary_sheet = workbook.create_sheet("运行摘要", 0)

            # 设置运行摘要工作表内容。
            self.write_summary_sheet(summary_sheet, Alignment, Font, PatternFill, Border, Side)

            # 创建运行甘特图工作表。
            gantt_sheet = workbook.create_sheet("运行甘特图", 1)

            # 设置运行甘特图工作表内容。
            self.write_gantt_sheet(gantt_sheet, Alignment, Font, PatternFill, Border, Side, Comment)

            # 保存 Excel 日志文件。
            workbook.save(output_path)

            # 返回日志文件路径。
            return output_path

    # 定义默认空日志行构建方法。
    def default_empty_row(self):

        """
        构建默认空日志行。

        :return: 默认空日志行字典。
        :rtype: dict
        """

        # 返回字段顺序固定的空日志行。
        return {
            "运行日期": "",
            "任务开始时间": "",
            "阶段开始时间": "",
            "阶段结束时间": "",
            "耗时秒数": "",
            "商业名称": "",
            "平台": "",
            "数据类型": "",
            "查询开始日期": "",
            "查询结束日期": "",
            "执行阶段": "",
            "执行状态": "",
            "记录数量": "",
            "业务文件绝对路径": "",
            "Cookie文件绝对路径": "",
            "执行说明": "",
            "异常详情": "",
        }

    # 定义表头样式设置方法。
    def style_header(self, worksheet, headers, pattern_fill_class, font_class, alignment_class):

        """
        设置 Excel 日志表头样式。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param headers: 表头列表。
        :type headers: list[str]
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :return: None。
        :rtype: None
        """

        # 创建表头填充样式。
        header_fill = pattern_fill_class("solid", fgColor="244062")

        # 创建表头字体样式。
        header_font = font_class(name="等线", color="FFFFFF", bold=True, size=11)

        # 遍历表头单元格。
        for column_index, _ in enumerate(headers, start=1):

            # 读取当前表头单元格。
            cell = worksheet.cell(row=1, column=column_index)

            # 设置表头填充样式。
            cell.fill = header_fill

            # 设置表头字体样式。
            cell.font = header_font

            # 设置表头对齐样式。
            cell.alignment = alignment_class(horizontal="center", vertical="center")

    # 定义状态行样式设置方法。
    def style_status_rows(self, worksheet, headers, pattern_fill_class, font_class):

        """
        设置 Excel 日志状态行样式。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param headers: 表头列表。
        :type headers: list[str]
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :return: None。
        :rtype: None
        """

        # 读取执行状态列序号。
        status_column = headers.index("执行状态") + 1

        # 创建成功状态填充样式。
        success_fill = pattern_fill_class("solid", fgColor="EAF4EA")

        # 创建失败状态填充样式。
        failure_fill = pattern_fill_class("solid", fgColor="FCE8E6")

        # 创建警告状态填充样式。
        warning_fill = pattern_fill_class("solid", fgColor="FFF7DA")

        # 遍历数据行。
        for row_index in range(2, worksheet.max_row + 1):

            # 读取当前行状态文本。
            status_value = str(worksheet.cell(row=row_index, column=status_column).value or "")

            # 根据状态选择行填充样式。
            row_fill = self.resolve_status_fill(status_value, success_fill, failure_fill, warning_fill)

            # 遍历当前行所有单元格。
            for column_index in range(1, worksheet.max_column + 1):

                # 设置当前单元格填充样式。
                worksheet.cell(row=row_index, column=column_index).fill = row_fill

            # 设置状态单元格字体加粗。
            worksheet.cell(row=row_index, column=status_column).font = font_class(name="等线", bold=True, size=11)

    # 定义状态填充样式解析方法。
    def resolve_status_fill(self, status_value, success_fill, failure_fill, warning_fill):

        """
        根据执行状态解析行填充样式。

        :param status_value: 执行状态文本。
        :type status_value: str
        :param success_fill: 成功填充样式。
        :type success_fill: PatternFill
        :param failure_fill: 失败填充样式。
        :type failure_fill: PatternFill
        :param warning_fill: 警告填充样式。
        :type warning_fill: PatternFill
        :return: 行填充样式。
        :rtype: PatternFill
        """

        # 返回失败状态样式。
        if "失败" in status_value:

            # 返回失败填充样式。
            return failure_fill

        # 返回成功状态样式。
        if "成功" in status_value:

            # 返回成功填充样式。
            return success_fill

        # 返回警告状态样式。
        return warning_fill

    # 定义表格布局样式设置方法。
    def style_layout(self, worksheet, headers, column_letter_function, alignment_class, font_class, border_class, side_class):

        """
        设置 Excel 日志表格布局。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param headers: 表头列表。
        :type headers: list[str]
        :param column_letter_function: 列字母转换函数。
        :type column_letter_function: Callable[[int], str]
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param border_class: 边框样式类。
        :type border_class: type
        :param side_class: 边框线条样式类。
        :type side_class: type
        :return: None。
        :rtype: None
        """

        # 冻结表头行。
        worksheet.freeze_panes = "A2"

        # 启用自动筛选。
        worksheet.auto_filter.ref = worksheet.dimensions

        # 设置表头行高。
        worksheet.row_dimensions[1].height = 32

        # 创建浅色边框线条。
        thin_side = side_class(style="thin", color="D9E2F3")

        # 创建表格边框样式。
        table_border = border_class(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 遍历表头设置列宽。
        for column_index, header in enumerate(headers, start=1):

            # 读取当前列字母。
            column_letter = column_letter_function(column_index)

            # 计算当前列宽。
            column_width = self.resolve_column_width(header)

            # 设置当前列宽。
            worksheet.column_dimensions[column_letter].width = column_width

        # 遍历工作表行号设置行高。
        for row_index in range(2, worksheet.max_row + 1):

            # 设置数据行高。
            worksheet.row_dimensions[row_index].height = 30

        # 遍历工作表所有行。
        for row in worksheet.iter_rows():

            # 遍历当前行所有单元格。
            for cell in row:

                # 设置单元格垂直居中和自动换行。
                cell.alignment = alignment_class(vertical="center", wrap_text=True)

                # 设置单元格字体。
                cell.font = font_class(name="等线", size=11)

                # 设置单元格浅色边框。
                cell.border = table_border

        # 遍历表头单元格恢复表头字体。
        for column_index in range(1, worksheet.max_column + 1):

            # 设置表头字体。
            worksheet.cell(row=1, column=column_index).font = font_class(name="等线", color="FFFFFF", bold=True, size=11)

    # 定义运行摘要工作表写入方法。
    def write_summary_sheet(self, worksheet, alignment_class, font_class, pattern_fill_class, border_class, side_class):

        """
        写入运行摘要工作表。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param border_class: 边框样式类。
        :type border_class: type
        :param side_class: 边框线条样式类。
        :type side_class: type
        :return: None。
        :rtype: None
        """

        # 设置工作表标题。
        worksheet["A1"] = "DDI 本次运行摘要"

        # 设置任务时间范围。
        worksheet["A2"] = f"查询日期：{self.task_start_date} 至 {self.task_end_date}"

        # 计算商业任务总数。
        company_total = len([row for row in self.rows if row.get("执行阶段") == "商业任务" and row.get("执行状态") in ["成功", "失败"]])

        # 计算成功数据类型数量。
        success_count = len([row for row in self.rows if row.get("数据类型") and row.get("执行状态") == "成功"])

        # 计算失败记录数量。
        failure_count = len([row for row in self.rows if row.get("执行状态") == "失败"])

        # 计算总明细数量。
        total_count = len(self.rows)

        # 计算成功率。
        success_rate = f"{(success_count / (success_count + failure_count) * 100):.1f}%" if success_count + failure_count else "100.0%"

        # 写入摘要表头。
        worksheet.append(["指标", "数值", "说明"])

        # 写入商业任务数量。
        worksheet.append(["商业任务数", company_total, "商业任务成功或失败的最终状态数量"])

        # 写入成功数据类型数量。
        worksheet.append(["成功数据类型数", success_count, "成功生成文件或完成查询的数据类型数量"])

        # 写入失败记录数量。
        worksheet.append(["失败记录数", failure_count, "登录、验证码、查询、保存等失败记录数量"])

        # 写入日志明细数量。
        worksheet.append(["日志明细数", total_count, "本次运行写入的全部结构化日志行数"])

        # 写入成功率。
        worksheet.append(["成功率", success_rate, "按成功数据类型数与失败记录数估算"])

        # 写入日志生成时间。
        worksheet.append(["日志生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Excel 日志文件生成时间"])

        # 设置摘要标题合并区域。
        worksheet.merge_cells("A1:C1")

        # 设置摘要副标题合并区域。
        worksheet.merge_cells("A2:C2")

        # 设置列宽。
        worksheet.column_dimensions["A"].width = 22

        # 设置列宽。
        worksheet.column_dimensions["B"].width = 22

        # 设置列宽。
        worksheet.column_dimensions["C"].width = 48

        # 设置标题行高。
        worksheet.row_dimensions[1].height = 34

        # 设置副标题行高。
        worksheet.row_dimensions[2].height = 26

        # 创建标题填充样式。
        title_fill = pattern_fill_class("solid", fgColor="244062")

        # 创建表头填充样式。
        header_fill = pattern_fill_class("solid", fgColor="D9EAF7")

        # 创建浅色边框线条。
        thin_side = side_class(style="thin", color="D9E2F3")

        # 创建摘要边框样式。
        table_border = border_class(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 设置标题单元格样式。
        worksheet["A1"].fill = title_fill

        # 设置标题字体样式。
        worksheet["A1"].font = font_class(name="等线", color="FFFFFF", bold=True, size=16)

        # 设置标题对齐样式。
        worksheet["A1"].alignment = alignment_class(horizontal="center", vertical="center")

        # 设置副标题字体样式。
        worksheet["A2"].font = font_class(name="等线", color="666666", size=11)

        # 设置副标题对齐样式。
        worksheet["A2"].alignment = alignment_class(horizontal="center", vertical="center")

        # 遍历摘要区域所有单元格。
        for row in worksheet.iter_rows(min_row=3, max_row=9, min_col=1, max_col=3):

            # 遍历当前摘要行的单元格。
            for cell in row:

                # 设置摘要单元格字体。
                cell.font = font_class(name="等线", size=11)

                # 设置摘要单元格对齐。
                cell.alignment = alignment_class(vertical="center", wrap_text=True)

                # 设置摘要单元格边框。
                cell.border = table_border

        # 遍历摘要表头单元格。
        for cell in worksheet[3]:

            # 设置摘要表头填充。
            cell.fill = header_fill

            # 设置摘要表头字体。
            cell.font = font_class(name="等线", bold=True, color="1F4E78", size=11)

            # 设置摘要表头对齐。
            cell.alignment = alignment_class(horizontal="center", vertical="center")

        # 遍历摘要数据行设置行高。
        for row_index in range(3, 10):

            # 设置摘要数据行高。
            worksheet.row_dimensions[row_index].height = 30

        # 设置冻结窗格。
        worksheet.freeze_panes = "A4"

    # 定义运行甘特图工作表写入方法。
    def write_gantt_sheet(self, worksheet, alignment_class, font_class, pattern_fill_class, border_class, side_class, comment_class=None):

        """
        写入运行甘特图工作表。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param border_class: 边框样式类。
        :type border_class: type
        :param side_class: 边框线条样式类。
        :type side_class: type
        :param comment_class: 单元格批注样式类。
        :type comment_class: type | None
        :return: None。
        :rtype: None
        """

        # 构建甘特图基础记录。
        timeline_rows = self.build_gantt_rows()

        # 设置甘特图时间槽数量。
        slot_count = 48

        # 构建甘特图左侧元数据表头。
        metadata_headers = ["序号", "商业名称", "平台", "数据类型", "执行阶段", "执行状态", "记录数", "耗时", "起止时间", "任务详情"]

        # 读取元数据列数量。
        metadata_column_count = len(metadata_headers)

        # 构建甘特图默认时间轴表头。
        headers = metadata_headers + [f"T{index:02d}" for index in range(1, slot_count + 1)]

        # 判断甘特图记录是否为空。
        if not timeline_rows:

            # 写入时间轴标题。
            worksheet["A1"] = "运行时间轴"

            # 写入空数据提示。
            worksheet["A3"] = "暂无可绘制的阶段时间记录"

            # 占位指标区域末行。
            worksheet["A4"] = ""

            # 写入甘特图表头。
            worksheet.append(headers)

            # 设置空数据甘特图样式。
            self.style_gantt_sheet(worksheet, headers, alignment_class, font_class, pattern_fill_class, border_class, side_class)

            # 返回空值。
            return

        # 读取最早阶段开始时间。
        min_started_at = min(row["开始对象"] for row in timeline_rows)

        # 读取最晚阶段结束时间。
        max_ended_at = max(row["结束对象"] for row in timeline_rows)

        # 计算整体运行耗时秒数。
        total_seconds = max(1, (max_ended_at - min_started_at).total_seconds())

        # 计算每个时间槽的秒数。
        slot_seconds = max(1, round(total_seconds / slot_count, 2))

        # 构建真实时间轴表头。
        timeline_headers = [self.build_timeline_label(min_started_at, slot_seconds, slot_index) for slot_index in range(slot_count)]

        # 构建甘特图表头。
        headers = metadata_headers + timeline_headers

        # 计算成功阶段数量。
        success_count = len([row for row in timeline_rows if "成功" in str(row["执行状态"])])

        # 计算失败阶段数量。
        failure_count = len([row for row in timeline_rows if "失败" in str(row["执行状态"])])

        # 计算总记录数量。
        total_record_count = sum(row["记录数值"] for row in timeline_rows)

        # 读取最慢阶段记录。
        slowest_row = max(timeline_rows, key=lambda row: row["耗时数值"])

        # 读取首个失败阶段记录。
        first_failure_row = next((row for row in timeline_rows if "失败" in str(row["执行状态"]) or "异常" in str(row["执行状态"]) or "中断" in str(row["执行状态"])), None)

        # 合并时间轴标题区域。
        worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=metadata_column_count + slot_count)

        # 写入时间轴标题。
        worksheet["A1"] = "运行时间轴"

        # 写入整体耗时标签。
        worksheet["A2"] = "整体耗时"

        # 写入整体耗时数值。
        worksheet["B2"] = self.format_duration(total_seconds)

        # 写入阶段数量标签。
        worksheet["C2"] = "阶段数"

        # 写入阶段数量数值。
        worksheet["D2"] = len(timeline_rows)

        # 写入成功数量标签。
        worksheet["E2"] = "成功"

        # 写入成功数量数值。
        worksheet["F2"] = success_count

        # 写入失败数量标签。
        worksheet["G2"] = "失败"

        # 写入失败数量数值。
        worksheet["H2"] = failure_count

        # 写入记录数量标签。
        worksheet["I2"] = "记录数"

        # 写入记录数量数值。
        worksheet["J2"] = total_record_count

        # 写入开始时间标签。
        worksheet["A3"] = "开始"

        # 写入开始时间数值。
        worksheet["B3"] = min_started_at.strftime("%H:%M:%S")

        # 写入结束时间标签。
        worksheet["C3"] = "结束"

        # 写入结束时间数值。
        worksheet["D3"] = max_ended_at.strftime("%H:%M:%S")

        # 写入时间粒度标签。
        worksheet["E3"] = "时间粒度"

        # 写入时间粒度数值。
        worksheet["F3"] = f"{slot_seconds} 秒/格"

        # 写入查询范围标签。
        worksheet["G3"] = "查询范围"

        # 写入查询范围数值。
        worksheet["H3"] = f"{self.task_start_date} 至 {self.task_end_date}"

        # 写入最慢阶段标签。
        worksheet["A4"] = "最慢阶段"

        # 写入最慢阶段描述。
        worksheet["B4"] = f"{slowest_row['商业名称']} | {slowest_row['数据类型']} | {slowest_row['执行阶段']} | {self.format_duration(slowest_row['耗时数值'])}"

        # 写入登录阶段图例标签。
        worksheet["E4"] = "登录"

        # 写入查询阶段图例标签。
        worksheet["F4"] = "查询"

        # 写入 Excel 阶段图例标签。
        worksheet["G4"] = "Excel"

        # 写入复制阶段图例标签。
        worksheet["H4"] = "复制"

        # 写入商业任务图例标签。
        worksheet["I4"] = "商业任务"

        # 写入失败状态图例标签。
        worksheet["J4"] = "失败"

        # 写入甘特图表头。
        worksheet.append(headers)

        # 初始化关键节点列配置。
        marker_columns = []

        # 计算最慢阶段起始时间槽。
        slowest_start_slot = self.resolve_gantt_slot(slowest_row["开始对象"], min_started_at, total_seconds, slot_count)

        # 计算最慢阶段标记列。
        slowest_marker_column = metadata_column_count + slowest_start_slot

        # 设置最慢阶段表头标记。
        worksheet.cell(row=5, column=slowest_marker_column).value = f"↓ 最慢\n{slowest_row['开始对象'].strftime('%H:%M:%S')}"

        # 记录最慢阶段标记列。
        marker_columns.append({"列号": slowest_marker_column, "标题": "最慢阶段", "颜色": "4472C4", "底色": "D9EAF7"})

        # 判断是否存在失败阶段。
        if first_failure_row:

            # 计算失败阶段起始时间槽。
            failure_start_slot = self.resolve_gantt_slot(first_failure_row["开始对象"], min_started_at, total_seconds, slot_count)

            # 计算失败阶段标记列。
            failure_marker_column = metadata_column_count + failure_start_slot

            # 设置失败阶段表头标记。
            worksheet.cell(row=5, column=failure_marker_column).value = f"↓ 失败\n{first_failure_row['开始对象'].strftime('%H:%M:%S')}"

            # 记录失败阶段标记列。
            marker_columns.append({"列号": failure_marker_column, "标题": "失败节点", "颜色": "C00000", "底色": "FCE4D6"})

        # 按阶段耗时倒序排列甘特图记录。
        sorted_rows = sorted(timeline_rows, key=lambda row: (row["开始对象"], row["结束对象"], row["商业名称"]))

        # 初始化甘特图条形区域配置。
        bar_ranges = []

        # 遍历甘特图记录写入数据行。
        for row_number, gantt_row in enumerate(sorted_rows, start=1):

            # 构建起止时间文本。
            time_range_text = f"{gantt_row['开始对象'].strftime('%H:%M:%S')} - {gantt_row['结束对象'].strftime('%H:%M:%S')}"

            # 构建甘特图元数据列。
            metadata = [row_number, gantt_row["商业名称"], gantt_row["平台"], gantt_row["数据类型"], gantt_row["执行阶段"], gantt_row["执行状态"], gantt_row["记录数"], self.format_duration(gantt_row["耗时数值"]), time_range_text, self.build_gantt_detail_text(gantt_row)]

            # 写入甘特图元数据和时间槽。
            worksheet.append(metadata + [""] * slot_count)

            # 读取当前工作表行号。
            row_index = worksheet.max_row

            # 计算当前阶段起始时间槽。
            start_slot = self.resolve_gantt_slot(gantt_row["开始对象"], min_started_at, total_seconds, slot_count)

            # 计算当前阶段结束时间槽。
            end_slot = self.resolve_gantt_slot(gantt_row["结束对象"], min_started_at, total_seconds, slot_count)

            # 读取当前阶段填充样式。
            fill_style = self.resolve_gantt_fill(gantt_row["执行状态"], pattern_fill_class, gantt_row["执行阶段"])

            # 读取当前阶段强调色。
            accent_color = self.resolve_gantt_accent_color(gantt_row["执行状态"], gantt_row["执行阶段"])

            # 遍历当前阶段覆盖的时间槽。
            for slot_index in range(start_slot, end_slot + 1):

                # 读取当前时间槽单元格。
                cell = worksheet.cell(row=row_index, column=metadata_column_count + slot_index)

                # 写入甘特图块标记。
                cell.value = " "

                # 设置甘特图块填充样式。
                cell.fill = fill_style

            # 读取当前阶段起始时间槽单元格。
            label_cell = worksheet.cell(row=row_index, column=metadata_column_count + start_slot)

            # 读取当前阶段结束时间槽单元格。
            end_cell = worksheet.cell(row=row_index, column=metadata_column_count + end_slot)

            # 判断当前阶段是否覆盖多个时间槽。
            if end_cell.column > label_cell.column:

                # 合并当前阶段的时间条区域。
                worksheet.merge_cells(start_row=row_index, start_column=label_cell.column, end_row=row_index, end_column=end_cell.column)

            # 写入当前阶段标签文本。
            label_cell.value = self.build_gantt_bar_label(gantt_row)

            # 设置当前阶段标签对齐。
            label_cell.alignment = alignment_class(horizontal="left", vertical="center", wrap_text=False, shrink_to_fit=True)

            # 设置当前阶段标签字体。
            label_cell.font = font_class(name="等线", color="1F2937", bold=True, size=9)

            # 记录当前甘特条区域样式。
            bar_ranges.append({"行号": row_index, "起始列": label_cell.column, "结束列": end_cell.column, "强调色": accent_color, "阶段记录": gantt_row})

            # 判断是否需要写入完整信息批注。
            if comment_class:

                # 写入当前阶段完整信息批注。
                label_cell.comment = comment_class(self.build_gantt_comment_text(gantt_row), "DDI")

        # 设置甘特图工作表样式。
        self.style_gantt_sheet(worksheet, headers, alignment_class, font_class, pattern_fill_class, border_class, side_class)

        # 应用甘特图条形可读性样式。
        self.apply_gantt_bar_styles(worksheet, bar_ranges, alignment_class, font_class, border_class, side_class)

        # 应用甘特图关键节点标记。
        self.apply_gantt_marker_columns(worksheet, marker_columns, alignment_class, font_class, pattern_fill_class, border_class, side_class)

    # 定义甘特图记录构建方法。
    def build_gantt_rows(self):

        """
        构建甘特图阶段记录。

        :return: 甘特图阶段记录列表。
        :rtype: list[dict]
        """

        # 初始化甘特图记录列表。
        gantt_rows = []

        # 遍历结构化日志记录。
        for row in self.rows:

            # 解析阶段开始时间。
            started_at = self.parse_log_datetime(row.get("阶段开始时间"))

            # 解析阶段结束时间。
            ended_at = self.parse_log_datetime(row.get("阶段结束时间"))

            # 判断阶段时间是否完整。
            if not started_at or not ended_at:

                # 继续处理下一条日志。
                continue

            # 追加甘特图阶段记录。
            gantt_rows.append({
                "商业名称": row.get("商业名称", ""),
                "平台": row.get("平台", ""),
                "数据类型": row.get("数据类型", ""),
                "执行阶段": row.get("执行阶段", ""),
                "执行状态": row.get("执行状态", ""),
                "记录数": row.get("记录数量", ""),
                "记录数值": self.parse_number(row.get("记录数量", "")),
                "开始时间": row.get("阶段开始时间", ""),
                "结束时间": row.get("阶段结束时间", ""),
                "耗时秒数": row.get("耗时秒数", ""),
                "耗时数值": self.parse_number(row.get("耗时秒数", "")),
                "开始对象": started_at,
                "结束对象": ended_at,
            })

        # 返回甘特图记录列表。
        return gantt_rows

    # 定义数字解析方法。
    def parse_number(self, value):

        """
        解析日志中的数字字段。

        :param value: 原始数字文本。
        :type value: object
        :return: 解析后的数字。
        :rtype: float
        """

        # 判断原始值是否为空。
        if value in ("", None):

            # 返回默认零值。
            return 0

        # 捕获数字转换异常。
        try:

            # 返回浮点数字。
            return float(value)

        # 处理数字转换异常。
        except Exception:

            # 返回默认零值。
            return 0

    # 定义耗时文本格式化方法。
    def format_duration(self, seconds_value):

        """
        格式化阶段耗时文本。

        :param seconds_value: 耗时秒数。
        :type seconds_value: int | float
        :return: 耗时展示文本。
        :rtype: str
        """

        # 转换耗时秒数为整数。
        total_seconds = int(round(float(seconds_value or 0)))

        # 计算分钟数。
        minute_value = total_seconds // 60

        # 计算秒数余数。
        second_value = total_seconds % 60

        # 判断耗时是否达到一分钟。
        if minute_value:

            # 返回分钟秒数文本。
            return f"{minute_value}分{second_value:02d}秒"

        # 返回秒数文本。
        return f"{second_value}秒"

    # 定义日志时间解析方法。
    def parse_log_datetime(self, value):

        """
        解析日志时间文本。

        :param value: 日志时间文本。
        :type value: object
        :return: 日期时间对象。
        :rtype: datetime | None
        """

        # 判断日志时间是否为空。
        if not value:

            # 返回空时间对象。
            return None

        # 捕获日志时间解析异常。
        try:

            # 返回解析后的日期时间对象。
            return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")

        # 处理日志时间解析异常。
        except Exception:

            # 返回空时间对象。
            return None

    # 定义时间轴刻度文本构建方法。
    def build_timeline_label(self, min_started_at, slot_seconds, slot_index):

        """
        构建甘特图时间轴刻度文本。

        :param min_started_at: 最早阶段开始时间。
        :type min_started_at: datetime
        :param slot_seconds: 单个时间槽代表的秒数。
        :type slot_seconds: int | float
        :param slot_index: 时间槽下标。
        :type slot_index: int
        :return: 时间轴刻度文本。
        :rtype: str
        """

        # 计算当前时间槽对应的时间对象。
        slot_time = min_started_at + timedelta(seconds=float(slot_seconds) * slot_index)

        # 返回分钟级时间刻度文本。
        return slot_time.strftime("%H:%M")

    # 定义甘特图时间槽解析方法。
    def resolve_gantt_slot(self, current_time, min_started_at, total_seconds, slot_count):

        """
        解析日期时间对应的甘特图时间槽。

        :param current_time: 当前日期时间。
        :type current_time: datetime
        :param min_started_at: 最早开始时间。
        :type min_started_at: datetime
        :param total_seconds: 整体运行秒数。
        :type total_seconds: float
        :param slot_count: 时间槽数量。
        :type slot_count: int
        :return: 时间槽序号。
        :rtype: int
        """

        # 计算当前时间相对偏移秒数。
        offset_seconds = max(0, (current_time - min_started_at).total_seconds())

        # 计算当前时间槽序号。
        slot_index = int((offset_seconds / total_seconds) * max(1, slot_count - 1)) + 1

        # 返回限制后的时间槽序号。
        return max(1, min(slot_count, slot_index))

    # 定义甘特图填充样式解析方法。
    def resolve_gantt_fill(self, status_value, pattern_fill_class, stage_value=""):

        """
        根据执行状态解析甘特图填充样式。

        :param status_value: 执行状态文本。
        :type status_value: str
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param stage_value: 执行阶段文本。
        :type stage_value: str
        :return: 甘特图填充样式。
        :rtype: PatternFill
        """

        # 转换执行状态为文本。
        status_text = str(status_value)

        # 判断当前状态是否为失败。
        if "失败" in status_text or "异常" in status_text or "中断" in status_text:

            # 返回失败状态填充。
            return pattern_fill_class("solid", fgColor="FDE2E1")

        # 转换执行阶段为文本。
        stage_text = str(stage_value)

        # 判断当前阶段是否为登录。
        if "登录" in stage_text:

            # 返回登录阶段填充。
            return pattern_fill_class("solid", fgColor="DCEEFF")

        # 判断当前阶段是否为查询或导出。
        if "查询" in stage_text or "导出" in stage_text:

            # 返回查询阶段填充。
            return pattern_fill_class("solid", fgColor="DCF6E8")

        # 判断当前阶段是否为复制用文件生成。
        if "复制" in stage_text:

            # 返回复制阶段填充。
            return pattern_fill_class("solid", fgColor="EEE5FF")

        # 判断当前阶段是否为 Excel。
        if "Excel" in stage_text:

            # 返回 Excel 阶段填充。
            return pattern_fill_class("solid", fgColor="FFE8CC")

        # 判断当前阶段是否为商业任务。
        if "商业任务" in stage_text:

            # 返回商业任务阶段填充。
            return pattern_fill_class("solid", fgColor="D8F4F4")

        # 判断当前状态是否为成功。
        if "成功" in status_text or "完成" in status_text:

            # 返回成功状态填充。
            return pattern_fill_class("solid", fgColor="E1F3E6")

        # 返回普通状态填充。
        return pattern_fill_class("solid", fgColor="E4ECF8")

    # 定义甘特图强调色解析方法。
    def resolve_gantt_accent_color(self, status_value, stage_value=""):

        """
        根据执行状态和阶段解析甘特图条形强调色。

        :param status_value: 执行状态文本。
        :type status_value: str
        :param stage_value: 执行阶段文本。
        :type stage_value: str
        :return: 强调色十六进制文本。
        :rtype: str
        """

        # 转换执行状态为文本。
        status_text = str(status_value)

        # 判断当前状态是否为失败。
        if "失败" in status_text or "异常" in status_text or "中断" in status_text:

            # 返回失败强调色。
            return "C00000"

        # 转换执行阶段为文本。
        stage_text = str(stage_value)

        # 判断当前阶段是否为登录。
        if "登录" in stage_text:

            # 返回登录强调色。
            return "1D5F99"

        # 判断当前阶段是否为查询或导出。
        if "查询" in stage_text or "导出" in stage_text:

            # 返回查询强调色。
            return "1C7C4A"

        # 判断当前阶段是否为复制用文件生成。
        if "复制" in stage_text:

            # 返回复制强调色。
            return "7155A3"

        # 判断当前阶段是否为 Excel。
        if "Excel" in stage_text:

            # 返回 Excel 强调色。
            return "B85D00"

        # 判断当前阶段是否为商业任务。
        if "商业任务" in stage_text:

            # 返回商业任务强调色。
            return "178F92"

        # 判断当前状态是否为成功。
        if "成功" in status_text or "完成" in status_text:

            # 返回成功强调色。
            return "2D7D46"

        # 返回普通强调色。
        return "426A9E"

    # 定义甘特图块标签构建方法。
    def build_gantt_bar_label(self, gantt_row):

        """
        构建甘特图条形标签。

        :param gantt_row: 甘特图阶段记录。
        :type gantt_row: dict
        :return: 甘特图条形标签。
        :rtype: str
        """

        # 读取阶段文本。
        stage_text = str(gantt_row.get("执行阶段", "")).strip()

        # 读取耗时文本。
        duration_text = self.format_duration(gantt_row.get("耗时数值", 0))

        # 读取记录数文本。
        record_text = "" if gantt_row.get("记录数", "") in ("", None) else str(gantt_row.get("记录数", "")).strip()

        # 判断记录数是否存在。
        if record_text:

            # 返回包含记录数的标签。
            return f"{stage_text} | {duration_text} | {record_text}条"

        # 返回基础阶段标签。
        return f"{stage_text} | {duration_text}"

    # 定义甘特图详情文本构建方法。
    def build_gantt_detail_text(self, gantt_row):

        """
        构建甘特图左侧详情列文本。

        :param gantt_row: 甘特图阶段记录。
        :type gantt_row: dict
        :return: 甘特图详情文本。
        :rtype: str
        """

        # 读取商业名称文本。
        company_text = self.clean_gantt_text(gantt_row.get("商业名称", ""))

        # 读取数据类型文本。
        data_type_text = self.clean_gantt_text(gantt_row.get("数据类型", ""))

        # 读取阶段文本。
        stage_text = self.clean_gantt_text(gantt_row.get("执行阶段", ""))

        # 读取状态文本。
        status_text = self.clean_gantt_text(gantt_row.get("执行状态", ""))

        # 读取记录数文本。
        record_text = "" if gantt_row.get("记录数", "") in ("", None) else str(gantt_row.get("记录数", "")).strip()

        # 读取耗时文本。
        duration_text = self.format_duration(gantt_row.get("耗时数值", 0))

        # 构建详情文本片段。
        detail_parts = [company_text, data_type_text, stage_text, status_text, duration_text]

        # 判断记录数是否存在。
        if record_text:

            # 追加记录数文本。
            detail_parts.append(f"{record_text}条")

        # 返回详情文本。
        return " | ".join([part for part in detail_parts if part])

    # 定义甘特图文本清洗方法。
    def clean_gantt_text(self, value):

        """
        清洗甘特图展示文本。

        :param value: 原始展示值。
        :type value: object
        :return: 清洗后的展示文本。
        :rtype: str
        """

        # 判断原始值是否为空。
        if value in ("", None):

            # 返回空文本。
            return ""

        # 转换展示值为文本。
        text_value = str(value).strip()

        # 判断文本是否为空值占位。
        if text_value.lower() in ["none", "nan", "null"]:

            # 返回空文本。
            return ""

        # 返回清洗后的文本。
        return text_value

    # 定义甘特图批注文本构建方法。
    def build_gantt_comment_text(self, gantt_row):

        """
        构建甘特图条形批注文本。

        :param gantt_row: 甘特图阶段记录。
        :type gantt_row: dict
        :return: 甘特图条形批注文本。
        :rtype: str
        """

        # 构建批注字段集合。
        comment_lines = [
            f"商业名称：{gantt_row.get('商业名称', '')}",
            f"平台：{gantt_row.get('平台', '')}",
            f"数据类型：{gantt_row.get('数据类型', '')}",
            f"执行阶段：{gantt_row.get('执行阶段', '')}",
            f"执行状态：{gantt_row.get('执行状态', '')}",
            f"记录数：{gantt_row.get('记录数', '')}",
            f"耗时：{self.format_duration(gantt_row.get('耗时数值', 0))}",
            f"开始时间：{gantt_row.get('开始对象').strftime('%H:%M:%S') if gantt_row.get('开始对象') else ''}",
            f"结束时间：{gantt_row.get('结束对象').strftime('%H:%M:%S') if gantt_row.get('结束对象') else ''}",
        ]

        # 返回批注文本。
        return "\n".join(comment_lines)

    # 定义甘特图条形样式应用方法。
    def apply_gantt_bar_styles(self, worksheet, bar_ranges, alignment_class, font_class, border_class, side_class):

        """
        应用甘特图条形区域的可读性样式。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param bar_ranges: 甘特图条形区域配置列表。
        :type bar_ranges: list[dict]
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param border_class: 边框样式类。
        :type border_class: type
        :param side_class: 边框线条样式类。
        :type side_class: type
        :return: None。
        :rtype: None
        """

        # 遍历甘特图条形区域配置。
        for bar_config in bar_ranges:

            # 读取条形区域行号。
            row_index = bar_config["行号"]

            # 读取条形区域起始列。
            start_column = bar_config["起始列"]

            # 读取条形区域结束列。
            end_column = bar_config["结束列"]

            # 读取条形区域强调色。
            accent_color = bar_config["强调色"]

            # 读取阶段记录。
            gantt_row = bar_config["阶段记录"]

            # 创建强调边框线条。
            accent_side = side_class(style="medium", color=accent_color)

            # 创建浅色内部边框线条。
            inner_side = side_class(style="thin", color="D7DEE8")

            # 创建失败右侧边框线条。
            failure_side = side_class(style="medium", color="D00000")

            # 判断当前阶段是否失败。
            is_failure = any(word in str(gantt_row.get("执行状态", "")) for word in ["失败", "异常", "中断"])

            # 遍历条形区域覆盖列。
            for column_index in range(start_column, end_column + 1):

                # 读取当前条形单元格。
                cell = worksheet.cell(row=row_index, column=column_index)

                # 跳过合并区域附属单元格。
                if cell.__class__.__name__ == "MergedCell":

                    # 继续处理下一个单元格。
                    continue

                # 设置条形文本对齐方式。
                cell.alignment = alignment_class(horizontal="left", vertical="center", wrap_text=False, shrink_to_fit=True)

                # 设置条形文本字体。
                cell.font = font_class(name="等线", color="111827", bold=True, size=9)

                # 设置条形左侧强调边框。
                left_side = accent_side if column_index == start_column else inner_side

                # 设置条形右侧状态边框。
                right_side = failure_side if is_failure and column_index == end_column else inner_side

                # 写入条形区域边框。
                cell.border = border_class(left=left_side, right=right_side, top=accent_side, bottom=accent_side)

            # 读取条形区域标签单元格。
            label_cell = worksheet.cell(row=row_index, column=start_column)

            # 判断失败阶段是否需要追加标识。
            if is_failure and label_cell.value:

                # 追加失败状态前缀。
                label_cell.value = f"失败 | {label_cell.value}"

    # 定义甘特图关键节点列应用方法。
    def apply_gantt_marker_columns(self, worksheet, marker_columns, alignment_class, font_class, pattern_fill_class, border_class, side_class):

        """
        应用甘特图关键节点竖向标记。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param marker_columns: 标记列配置。
        :type marker_columns: list[dict]
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param border_class: 边框样式类。
        :type border_class: type
        :param side_class: 边框线条样式类。
        :return: None。
        :rtype: None
        """

        # 遍历关键节点列配置。
        for marker_config in marker_columns:

            # 读取标记列号。
            column_index = marker_config["列号"]

            # 创建标记线条。
            marker_side = side_class(style="dashed", color=marker_config["颜色"])

            # 创建标记底色。
            marker_fill = pattern_fill_class("solid", fgColor=marker_config["底色"])

            # 读取表头单元格。
            header_cell = worksheet.cell(row=5, column=column_index)

            # 设置表头标记底色。
            header_cell.fill = pattern_fill_class("solid", fgColor=marker_config["颜色"])

            # 设置表头标记字体。
            header_cell.font = font_class(name="等线", color="FFFFFF", bold=True, size=8)

            # 设置表头标记对齐。
            header_cell.alignment = alignment_class(horizontal="center", vertical="center", wrap_text=True)

            # 设置表头标记边框。
            header_cell.border = border_class(left=marker_side, right=marker_side, top=marker_side, bottom=marker_side)

            # 遍历数据区域行。
            for row_index in range(6, worksheet.max_row + 1):

                # 读取当前标记列单元格。
                cell = worksheet.cell(row=row_index, column=column_index)

                # 判断当前单元格是否为空。
                if cell.value in ("", None):

                    # 设置空节点背景。
                    cell.fill = marker_fill

                # 设置竖向虚线边框。
                cell.border = border_class(left=marker_side, right=cell.border.right, top=cell.border.top, bottom=cell.border.bottom)

    # 定义甘特图工作表样式设置方法。
    def style_gantt_sheet(self, worksheet, headers, alignment_class, font_class, pattern_fill_class, border_class, side_class):

        """
        设置甘特图工作表样式。

        :param worksheet: Excel 工作表对象。
        :type worksheet: Worksheet
        :param headers: 表头列表。
        :type headers: list[str]
        :param alignment_class: 对齐样式类。
        :type alignment_class: type
        :param font_class: 字体样式类。
        :type font_class: type
        :param pattern_fill_class: 填充样式类。
        :type pattern_fill_class: type
        :param border_class: 边框样式类。
        :type border_class: type
        :param side_class: 边框线条样式类。
        :return: None。
        :rtype: None
        """

        # 定义甘特图左侧元数据列数量。
        metadata_column_count = 10

        # 定义甘特图时间轴起始列。
        timeline_start_column = metadata_column_count + 1

        # 冻结甘特图元数据区域。
        worksheet.freeze_panes = worksheet.cell(row=6, column=timeline_start_column).coordinate

        # 关闭默认网格线。
        worksheet.sheet_view.showGridLines = False

        # 设置工作表缩放比例。
        worksheet.sheet_view.zoomScale = 90

        # 设置工作表标签颜色。
        worksheet.sheet_properties.tabColor = "2F5597"

        # 设置数据筛选范围。
        worksheet.auto_filter.ref = f"A5:{worksheet.cell(row=worksheet.max_row, column=worksheet.max_column).coordinate}"

        # 创建页面背景填充样式。
        page_fill = pattern_fill_class("solid", fgColor="F6F8FB")

        # 创建指标填充样式。
        metric_fill = pattern_fill_class("solid", fgColor="FFFFFF")

        # 创建指标标签填充样式。
        metric_label_fill = pattern_fill_class("solid", fgColor="EEF2F7")

        # 创建元数据表头填充样式。
        metadata_header_fill = pattern_fill_class("solid", fgColor="2F3747")

        # 创建时间轴表头填充样式。
        timeline_header_fill = pattern_fill_class("solid", fgColor="E8EDF5")

        # 创建时间轴背景填充样式。
        timeline_fill = pattern_fill_class("solid", fgColor="F8FAFD")

        # 创建奇数行填充样式。
        odd_row_fill = pattern_fill_class("solid", fgColor="FFFFFF")

        # 创建偶数行填充样式。
        even_row_fill = pattern_fill_class("solid", fgColor="F3F6FA")

        # 创建登录图例填充样式。
        login_fill = pattern_fill_class("solid", fgColor="DCEEFF")

        # 创建查询图例填充样式。
        query_fill = pattern_fill_class("solid", fgColor="DCF6E8")

        # 创建 Excel 图例填充样式。
        excel_fill = pattern_fill_class("solid", fgColor="FFE8CC")

        # 创建复制图例填充样式。
        copy_fill = pattern_fill_class("solid", fgColor="EEE5FF")

        # 创建商业任务图例填充样式。
        company_fill = pattern_fill_class("solid", fgColor="D8F4F4")

        # 创建失败图例填充样式。
        failure_fill = pattern_fill_class("solid", fgColor="FDE2E1")

        # 创建浅色边框线条。
        thin_side = side_class(style="thin", color="D7DEE8")

        # 创建主刻度边框线条。
        major_side = side_class(style="thin", color="AAB7C8")

        # 创建表格边框样式。
        table_border = border_class(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 创建主刻度边框样式。
        major_border = border_class(left=major_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 设置标题行高度。
        worksheet.row_dimensions[1].height = 30

        # 设置指标行高度。
        worksheet.row_dimensions[2].height = 28

        # 设置指标行高度。
        worksheet.row_dimensions[3].height = 24

        # 设置图例行高度。
        worksheet.row_dimensions[4].height = 24

        # 设置表头行高度。
        worksheet.row_dimensions[5].height = 28

        # 遍历工作表所有单元格设置基础样式。
        for row in worksheet.iter_rows():

            # 遍历当前行所有单元格。
            for cell in row:

                # 跳过合并区域的附属单元格。
                if cell.__class__.__name__ == "MergedCell":

                    # 继续处理下一个单元格。
                    continue

                # 设置基础字体。
                cell.font = font_class(name="等线", size=10, color="1F2937")

                # 设置基础对齐。
                cell.alignment = alignment_class(horizontal="center", vertical="center", wrap_text=True)

                # 设置基础边框。
                cell.border = table_border

                # 判断当前单元格是否已经绘制甘特图条。
                has_gantt_bar = cell.column >= timeline_start_column and cell.value not in ("", None)

                # 判断是否需要写入基础背景。
                if not has_gantt_bar:

                    # 设置基础背景。
                    cell.fill = page_fill

        # 设置标题单元格字体。
        worksheet["A1"].font = font_class(name="等线", color="1F2937", bold=True, size=16)

        # 设置标题单元格对齐。
        worksheet["A1"].alignment = alignment_class(horizontal="left", vertical="center")

        # 遍历指标区域单元格。
        for row_cells in worksheet.iter_rows(min_row=2, max_row=4):

            # 遍历当前指标行单元格。
            for cell in row_cells:

                # 跳过合并区域的附属单元格。
                if cell.__class__.__name__ == "MergedCell":

                    # 继续处理下一个单元格。
                    continue

                # 设置指标区域填充。
                cell.fill = metric_fill

                # 设置指标区域字体。
                cell.font = font_class(name="等线", size=10, color="1F2937")

        # 遍历指标标签单元格。
        for cell_address in ["A2", "C2", "E2", "G2", "I2", "A3", "C3", "E3", "G3", "A4", "I4"]:

            # 设置指标标签填充。
            worksheet[cell_address].fill = metric_label_fill

            # 设置指标标签字体。
            worksheet[cell_address].font = font_class(name="等线", bold=True, size=10, color="4B5563")

        # 设置登录图例填充。
        worksheet["E4"].fill = login_fill

        # 设置查询图例填充。
        worksheet["F4"].fill = query_fill

        # 设置 Excel 图例填充。
        worksheet["G4"].fill = excel_fill

        # 设置复制图例填充。
        worksheet["H4"].fill = copy_fill

        # 设置商业任务图例填充。
        worksheet["I4"].fill = company_fill

        # 设置失败图例填充。
        worksheet["J4"].fill = failure_fill

        # 遍历图例单元格。
        for cell_address in ["E4", "F4", "G4", "H4", "I4", "J4"]:

            # 设置图例字体。
            worksheet[cell_address].font = font_class(name="等线", bold=True, size=10, color="111827")

        # 遍历元数据表头单元格。
        for column_index in range(1, timeline_start_column):

            # 读取当前表头单元格。
            cell = worksheet.cell(row=5, column=column_index)

            # 设置元数据表头填充。
            cell.fill = metadata_header_fill

            # 设置元数据表头字体。
            cell.font = font_class(name="等线", color="FFFFFF", bold=True, size=10)

        # 遍历时间轴表头单元格。
        for column_index in range(timeline_start_column, worksheet.max_column + 1):

            # 读取当前时间轴表头单元格。
            cell = worksheet.cell(row=5, column=column_index)

            # 设置时间轴表头填充。
            cell.fill = timeline_header_fill

            # 设置时间轴表头字体。
            cell.font = font_class(name="等线", color="374151", bold=True, size=8)

            # 设置时间轴表头文字方向。
            cell.alignment = alignment_class(horizontal="center", vertical="center", text_rotation=45)

        # 定义甘特图固定列宽。
        width_map = {"A": 6, "B": 34, "C": 10, "D": 14, "E": 16, "F": 10, "G": 9, "H": 10, "I": 19, "J": 52}

        # 遍历固定列宽映射。
        for column_letter, column_width in width_map.items():

            # 设置固定列宽。
            worksheet.column_dimensions[column_letter].width = column_width

        # 遍历甘特图时间槽列。
        for column_index in range(timeline_start_column, worksheet.max_column + 1):

            # 读取当前时间槽列字母。
            column_letter = worksheet.cell(row=5, column=column_index).column_letter

            # 设置时间槽列宽。
            worksheet.column_dimensions[column_letter].width = 4.8

        # 遍历数据区域行。
        for row_index in range(6, worksheet.max_row + 1):

            # 设置数据行高度。
            worksheet.row_dimensions[row_index].height = 24

            # 读取当前行底色。
            row_fill = even_row_fill if row_index % 2 == 0 else odd_row_fill

            # 遍历元数据列。
            for column_index in range(1, timeline_start_column):

                # 设置元数据列底色。
                worksheet.cell(row=row_index, column=column_index).fill = row_fill

            # 遍历时间轴列。
            for column_index in range(timeline_start_column, worksheet.max_column + 1):

                # 读取当前时间轴单元格。
                cell = worksheet.cell(row=row_index, column=column_index)

                # 判断当前单元格是否没有甘特条。
                if cell.value in ("", None) and cell.__class__.__name__ != "MergedCell":

                    # 设置时间轴背景。
                    cell.fill = timeline_fill

                # 判断当前列是否为主刻度列。
                if (column_index - timeline_start_column) % 6 == 0:

                    # 设置主刻度边框。
                    cell.border = major_border

        # 设置最慢阶段单元格对齐。
        worksheet["B4"].alignment = alignment_class(horizontal="left", vertical="center", wrap_text=True)

    # 定义列宽解析方法。
    def resolve_column_width(self, header):

        """
        根据表头解析列宽。

        :param header: 表头名称。
        :type header: str
        :return: Excel 列宽。
        :rtype: int
        """

        # 定义固定列宽映射。
        width_map = {
            "运行日期": 12,
            "任务开始时间": 20,
            "阶段开始时间": 20,
            "阶段结束时间": 20,
            "耗时秒数": 10,
            "商业名称": 28,
            "平台": 10,
            "数据类型": 14,
            "查询开始日期": 14,
            "查询结束日期": 14,
            "执行阶段": 16,
            "执行状态": 12,
            "记录数量": 10,
            "业务文件绝对路径": 58,
            "Cookie文件绝对路径": 58,
            "执行说明": 36,
            "异常详情": 70,
        }

        # 返回匹配表头的列宽。
        return width_map.get(header, 18)
