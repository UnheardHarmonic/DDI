# -*- coding: utf-8 -*-
"""
DDI 全局任务配置。

本模块保存每次批量导出的全局任务参数。平台适配器只接收入口程序解析后的任务参数，不在平台内部自行决定日期范围。
"""

# 导入日期时间模块。
from datetime import datetime

# 导入日期增减模块。
from datetime import timedelta

# 配置本次任务的默认执行动作。
DEFAULT_ACTION = "query_excel"

# 配置本次任务的默认数据类型。
DEFAULT_DATA_TYPE = "全部"

# 配置本次任务默认日期模式。
DEFAULT_DATE_MODE = "previous_month_full"

# 配置“全部”任务包含的数据类型顺序。
DEFAULT_DATA_TYPES = ["配送流向", "购进流向", "库存", "报损流向"]

# 配置登录 Cookie 输出目录。
DEFAULT_COOKIE_DIR = "runtime/cookies"

# 配置查询结果和 Excel 文件输出目录。
DEFAULT_OUTPUT_DIR = "runtime/downloads"

# 配置是否生成复制用标准流向 Excel。
DEFAULT_COPY_EXCEL_ENABLED = True

# 配置运行日志 Excel 输出目录。
DEFAULT_TASK_LOG_DIR = "runtime/logs"

# 配置控制台日志中的文件路径展示方式，支持 absolute 与 relative。
#   "relative"  终端打印 runtime\downloads\xxx.xlsx、runtime\cookies\xxx.json
#   "absolute"  终端打印 D:\PycharmProjects\...
DEFAULT_CONSOLE_PATH_MODE = "relative"

# 配置批量任务默认并发商业数量。
DEFAULT_MAX_WORKERS = 5


# 定义上个月起止日期构建函数。
def build_previous_month_date_range():

    """
    构建上个月的起始日期与结束日期。

    :return: 上个月起止日期文本。
    :rtype: tuple[str, str]
    """

    # 读取当前日期时间。
    current_datetime = datetime.now()

    # 构建本月第一天日期时间。
    current_month_first_day = current_datetime.replace(day=1)

    # 计算上个月最后一天日期时间。
    previous_month_last_day = current_month_first_day - timedelta(days=1)

    # 构建上个月第一天日期时间。
    previous_month_first_day = previous_month_last_day.replace(day=1)

    # 返回上个月起止日期文本。
    return previous_month_first_day.strftime("%Y-%m-%d"), previous_month_last_day.strftime("%Y-%m-%d")


# 定义全局任务配置读取函数。
def get_task_config():

    """
    获取全局任务配置。

    :return: 全局任务配置字典。
    :rtype: dict
    """

    # 构建上个月起止日期文本。
    start_date_text, end_date_text = build_previous_month_date_range()

    # 返回全局任务配置字典。
    return {
        "执行动作": DEFAULT_ACTION,
        "数据类型": DEFAULT_DATA_TYPE,
        "日期模式": DEFAULT_DATE_MODE,
        "数据类型列表": DEFAULT_DATA_TYPES,
        "开始日期": start_date_text,
        "结束日期": end_date_text,
        "Cookie目录": DEFAULT_COOKIE_DIR,
        "输出目录": DEFAULT_OUTPUT_DIR,
        "生成复制用Excel": DEFAULT_COPY_EXCEL_ENABLED,
        "日志目录": DEFAULT_TASK_LOG_DIR,
        "控制台路径模式": DEFAULT_CONSOLE_PATH_MODE,
        "最大并发数": DEFAULT_MAX_WORKERS,
    }
