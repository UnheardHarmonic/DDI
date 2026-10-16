# -*- coding: utf-8 -*-
"""
平台协议适配器基类。

本模块定义各商业平台适配器需要实现的统一方法，入口程序通过这些方法执行登录、查询、导出和 Excel 落地。
"""

# 导入公共下载命名工具。
from ddi_framework.download_watcher import DownloadWatcher


# 定义平台协议适配器基类。
class BasePlatform:

    """
    平台协议适配器基类。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台协议适配器实例。
    :rtype: BasePlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化平台协议适配器。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param account: 商业账号配置。
        :type account: dict
        :param printer: 日志打印器。
        :type printer: PrintHandler | None
        :return: None。
        :rtype: None
        """

        # 保存商业公司名称。
        self.company_name = company_name

        # 保存商业账号配置。
        self.account = account

        # 保存日志打印器。
        self.printer = printer

    # 定义平台登录抽象方法。
    def login(self):

        """
        执行平台登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 要求子类实现登录流程。
        raise NotImplementedError

    # 定义平台能力声明读取方法。
    def capabilities(self):

        """
        返回平台适配器的声明能力。

        :return: 平台能力字典。
        :rtype: dict
        """

        # 读取账号配置声明的数据类型。
        declared_types = tuple(self.account.get("数据类型列表", []) or [])

        # 返回公共层使用的平台能力。
        return {
            "data_types": declared_types,
            "supports_date_filter": not bool(self.account.get("库存快照", False)),
            "inventory_snapshot": bool(self.account.get("库存快照", False)),
            "supports_paging": bool(self.account.get("支持分页", True)),
            "supports_native_export": bool(self.account.get("支持原生导出", False)),
            "requires_captcha": bool(self.account.get("需要验证码", False)),
            "dynamic_fields": bool(self.account.get("动态字段", False)),
            "max_query_days": self.account.get("最大查询天数"),
            "allow_company_code_split": bool(self.account.get("允许多公司代码拆分", False)),
            "temporary_browser_fallback": bool(self.account.get("临时浏览器兜底", False)),
        }

    # 定义统一查询兼容入口。
    def query(self, data_type, date_range):

        """
        通过统一日期范围对象执行旧版查询适配器。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 公共日期范围对象。
        :type date_range: DateRangeSpec
        :return: 平台原始查询结果。
        :rtype: object
        """

        # 调用既有协议查询实现。
        return self.query_flow(data_type, start_date=date_range.start_date, end_date=date_range.end_date)

    # 定义统一查询落地入口。
    def query_to_excel(self, data_type, date_range, output_dir=None):

        """
        通过统一日期范围对象执行查询并生成 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 公共日期范围对象。
        :type date_range: DateRangeSpec
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径或路径集合。
        :rtype: str | list[str]
        """

        # 调用既有查询落地实现保持商业兼容。
        return self.query_flow_to_excel(data_type, start_date=date_range.start_date, end_date=date_range.end_date, output_dir=output_dir)

    # 定义统一导出兼容入口。
    def export(self, data_type, date_range, output_dir=None):

        """
        通过统一日期范围对象执行旧版导出适配器。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 公共日期范围对象。
        :type date_range: DateRangeSpec
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: 平台导出结果。
        :rtype: object
        """

        # 调用既有协议导出实现。
        return self.export_flow(data_type, start_date=date_range.start_date, end_date=date_range.end_date, output_dir=output_dir)

    # 定义平台导出抽象方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出指定类型流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出结果。
        :rtype: dict
        """

        # 要求子类实现导出流程。
        raise NotImplementedError

    # 定义平台查询抽象方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 要求子类实现查询流程。
        raise NotImplementedError

    # 定义平台查询落地抽象方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型流向数据并生成 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 要求子类实现查询落地流程。
        raise NotImplementedError

    # 定义标准输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date=None, end_date=None):

        """
        构建标准输出文件名。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准输出文件名。
        :rtype: str
        """

        # 读取公共任务层传入的日期范围上下文。
        date_range = getattr(self, "_ddi_date_range", None)

        # 读取当前任务日期模式。
        date_mode = getattr(date_range, "mode", "custom")

        # 读取当前任务开始日期。
        effective_start_date = getattr(date_range, "start_date", "") or start_date

        # 读取当前任务结束日期。
        effective_end_date = getattr(date_range, "end_date", "") or end_date

        # 读取商业是否声明库存为当前快照。
        is_snapshot_inventory = bool("库存" in data_type and self.account.get("库存快照", False))

        # 初始化公共下载命名工具。
        watcher = DownloadWatcher("")

        # 返回公共命名工具生成的标准文件名。
        return watcher.build_target_name(self.company_name, data_type, self.resolve_output_query_date(data_type, effective_start_date, effective_end_date), ".xlsx", start_date=effective_start_date, end_date=effective_end_date, date_mode=date_mode, snapshot_date=self.resolve_output_query_date(data_type, effective_start_date, effective_end_date) if is_snapshot_inventory else None)

    # 定义标准输出命名日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        解析标准输出文件名使用的业务日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准输出文件名使用的业务日期。
        :rtype: str | None
        """

        # 判断当前数据类型是否为库存类。
        if "库存" in data_type:

            # 返回库存类优先使用的查询结束日期。
            return end_date or start_date

        # 返回流向类优先使用的查询开始日期。
        return start_date or end_date

    # 定义导出文件商业名前缀构建方法。
    def build_export_company_name(self):

        """
        构建导出文件使用的商业名称前缀。

        :return: 带 DDI 标识的商业名称。
        :rtype: str
        """

        # 返回带 DDI 标识的商业名称。
        return f"「DDI」{self.company_name}"
