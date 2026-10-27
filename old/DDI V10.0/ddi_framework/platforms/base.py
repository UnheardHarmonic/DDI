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

        # 解析标准命名使用的业务日期。
        query_date = self.resolve_output_query_date(data_type, start_date, end_date)

        # 初始化公共下载命名工具。
        watcher = DownloadWatcher("")

        # 返回公共命名工具生成的标准文件名。
        return watcher.build_target_name(self.company_name, data_type, query_date, ".xlsx")

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
