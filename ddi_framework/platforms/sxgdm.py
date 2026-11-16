# -*- coding: utf-8 -*-
"""
山西国大万民药房 Scm 查询管理系统协议适配器。

本模块负责山西国大万民药房 Scm 查询管理系统（ASP 经典表格站）的
算术验证码登录、购进/配送/纯销/库存明细查询及原始字段 Excel 落地。
"""

# 导入操作系统路径模块。
import os

# 导入 HTML 解析器基类。
from html.parser import HTMLParser

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入正式原始 Excel 写入函数。
from ddi_framework.raw_fields import write_formal_raw_excel


# 定义数据类型与协议端点及日期能力映射。
DATA_TYPE_CONFIG = {
    "配送流向": {"端点": "S_SendDtl.asp", "日期字段": ("QueryBDate", "QueryEDate"), "需要开始日期": True},
    "购进流向": {"端点": "s_InStock.asp", "日期字段": ("QueryBDate", "QueryEDate"), "需要开始日期": True},
    "纯销流向": {"端点": "S_SaleDtl.asp", "日期字段": ("QueryBDate", "QueryEDate"), "需要开始日期": True},
    "库存": {"端点": "s_StockDtl.asp", "日期字段": ("QueryBDate", "QueryEDate"), "需要开始日期": False},
}


# 定义 Scm 表格解析器。
class ScmTableParser(HTMLParser):

    """
    解析 Scm 响应页面中的全部表格，供筛选真实数据表。

    :return: Scm 表格解析器实例。
    :rtype: ScmTableParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化表格集合与单元格缓冲。

        :return: None。
        :rtype: None
        """

        # 调用父类初始化逻辑。
        super().__init__()

        # 初始化全部表格集合（元素为表头与数据行）。
        self.tables = []

        # 初始化当前表格的表头。
        self.current_headers = None

        # 初始化当前表格的数据行集合。
        self.current_rows = []

        # 初始化当前行单元格集合。
        self.cells = []

        # 初始化当前单元格文本缓冲。
        self.text_parts = []

        # 初始化当前是否处于单元格内。
        self.in_cell = False

        # 初始化当前是否处于表格内。
        self.in_table = False

    # 定义开始标签处理方法。
    def handle_starttag(self, tag, attrs):

        """
        捕获表格、行与单元格的开始标签。

        :param tag: 标签名。
        :type tag: str
        :param attrs: 标签属性列表。
        :type attrs: list[tuple[str, str | None]]
        :return: None。
        :rtype: None
        """

        # 判断进入表格。
        if tag == "table":
            self.in_table = True
            self.current_headers = None
            self.current_rows = []

            # 结束处理。
            return

        # 判断进入表头或数据单元格。
        if tag in ("th", "td") and self.in_table:
            self.in_cell = True
            self.text_parts = []

            # 结束处理。
            return

        # 判断进入表格行。
        if tag == "tr" and self.in_table:
            self.cells = []

    # 定义结束标签处理方法。
    def handle_endtag(self, tag):

        """
        捕获单元格、行与表格的结束标签并装配数据。

        :param tag: 标签名。
        :type tag: str
        :return: None。
        :rtype: None
        """

        # 判断退出单元格。
        if tag in ("th", "td") and self.in_cell:
            self.cells.append("".join(self.text_parts).strip())
            self.in_cell = False

            # 结束处理。
            return

        # 判断退出表格行。
        if tag == "tr" and self.in_table and self.cells:
            if self.current_headers is None:
                self.current_headers = self.cells
            else:
                self.current_rows.append(self.cells)
            self.cells = []

            # 结束处理。
            return

        # 判断退出表格。
        if tag == "table" and self.in_table:
            self.tables.append((self.current_headers, self.current_rows))
            self.in_table = False

    # 定义文本片段处理方法。
    def handle_data(self, data):

        """
        累积当前单元格内的文本片段。

        :param data: 文本片段。
        :type data: str
        :return: None。
        :rtype: None
        """

        # 判断处于单元格内。
        if self.in_cell:
            self.text_parts.append(data)


# 定义山西国大万民 Scm 平台适配器。# 定义山西国大万民 Scm 平台适配器。
class SxgdmPlatform(BasePlatform):

    """
    山西国大万民药房 Scm 查询管理系统平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 山西国大万民 Scm 平台适配器实例。
    :rtype: SxgdmPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化站点地址、协议客户端与登录状态。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param account: 商业账号配置。
        :type account: dict
        :param printer: 日志打印器。
        :type printer: PrintHandler | None
        :return: None。
        :rtype: None
        """

        # 调用父类初始化逻辑。
        super().__init__(company_name, account, printer=printer)

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 读取站点根地址。
        self.base_url = str(account.get("接口根地址", "")).rstrip("/")

        # 读取查询请求超时时间。
        self.query_timeout_seconds = int(account.get("查询超时秒", 180))

        # 初始化带 Cookie 管理的协议客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态标识。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        完成登录页会话建立与生产商账密登录。

        :return: 不含凭据的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("国大万民 Scm 系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页建立 ASP 会话。
        self.http.get(f"{self.base_url}/", referer=f"{self.base_url}/")

        # 构建登录表单（验证码为纯前端装饰，服务端不校验，任意值即可）。
        payload = f"Username2={self.account.get('账号', '')}&Password2={self.account.get('密码', '')}&captcha2=0"

        # 构建登录请求头。
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": self.base_url, "Referer": f"{self.base_url}/"}

        # 提交生产商登录。
        result = self.http.request("POST", f"{self.base_url}/Admin_ChkLogin_S.asp", headers=headers, data=payload.encode("utf-8"), timeout=self.query_timeout_seconds, allow_http_error=True)

        # 解析响应文本（GB2312）。
        response_text = result.body.decode("gb2312", "replace")

        # 校验登录响应。
        self.validate_login_response(response_text)

        # 标记当前协议会话已登录。
        self.logged_in = True

        # 打印不含敏感值的登录成功日志。
        self.ph.success(self.ph.kv("登录状态", "成功", "green"))

        # 返回不含敏感字段的登录结果。
        return {"登录状态": "成功"}

    # 定义登录响应校验方法。
    def validate_login_response(self, response_text):

        """
        校验登录响应不含失败告警。

        :param response_text: 登录响应文本。
        :type response_text: str
        :return: None。
        :rtype: None
        """

        # 判断响应含失败告警脚本。
        if "alert(" in response_text:

            # 提取告警文本。
            import re

            # 读取告警内容。
            match = re.search(r"alert\('([^']*)'\)", response_text)
            message = match.group(1) if match else "未知错误"

            # 抛出不含凭据的登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{message}")

    # 定义协议配置解析方法。
    def resolve_config(self, data_type):

        """
        读取数据类型的协议端点与日期能力配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 协议配置字典。
        :rtype: dict
        """

        # 判断数据类型已配置。
        if data_type in DATA_TYPE_CONFIG:

            # 返回协议配置。
            return DATA_TYPE_CONFIG[data_type]

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型存在协议映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 调用协议配置解析完成校验。
        self.resolve_config(data_type)

    # 定义原始数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的全部原始业务记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 确保当前 HTTP 会话已经登录。
        self.ensure_login()

        # 解析协议配置。
        config = self.resolve_config(data_type)

        # 解析查询日期（紧凑 YYYYMMDD 格式，库存仅用截止日期）。
        query_begin, query_end = self.resolve_query_dates(start_date, end_date)

        # 构建查询表单体。
        fields = []

        # 按能力写入开始日期。
        if config["需要开始日期"]:
            fields.append(f"{config['日期字段'][0]}={query_begin}")

        # 写入截止日期。
        fields.append(f"{config['日期字段'][1]}={query_end}")

        # 写入空商品货号（全量口径）。
        fields.append("textfield=")

        # 构建查询请求头。
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": self.base_url, "Referer": f"{self.base_url}/{config['端点']}"}

        # 提交查询请求。
        result = self.http.request("POST", f"{self.base_url}/{config['端点']}?action=ListType", headers=headers, data="&".join(fields).encode("utf-8"), timeout=self.query_timeout_seconds, allow_http_error=True)

        # 解码响应页面（GB2312）。
        page_text = result.body.decode("gb2312", "replace")

        # 解析数据表格。
        table_headers, table_rows = self.parse_table(page_text)

        # 判断表头缺失。
        if not table_headers:

            # 抛出查询响应异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询响应未包含数据表格")

        # 按表头装配原始记录字典。
        rows = [dict(zip(table_headers, cells)) for cells in table_rows]

        # 打印协议查询完成摘要。
        self.ph.success(self.ph.join(self.ph.kv("查询端点", config["端点"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(table_headers), "cyan")))

        # 返回原始记录列表。
        return rows

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成原始字段 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 查询原始记录。
        rows = self.query_flow(data_type, start_date, end_date)

        # 解析当前查询的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(start_date, end_date)

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, resolved_start_date, resolved_end_date)

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 按行序合并全部原始字段。
        merged = []

        # 遍历记录收集字段。
        for row in rows:

            # 遍历字段名。
            for key in row.keys():

                # 追加新字段。
                if key not in merged:
                    merged.append(key)

        # 装配字段定义列表。
        field_headers = [{"key": title, "title": title} for title in merged]

        # 写入原始字段 Excel。
        write_formal_raw_excel(output_path, field_headers, rows, sheet_name=data_type)

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(merged), "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义查询日期解析方法。
    def resolve_query_dates(self, start_date, end_date):

        """
        解析查询日期并转换为紧凑 YYYYMMDD 格式。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 紧凑格式的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 导入日期时间模块。
        from datetime import datetime

        # 解析当前日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 解析开始日期。
        resolved_start_date = str(start_date or today_text)

        # 解析结束日期。
        resolved_end_date = str(end_date or today_text)

        # 校验日期范围顺序。
        self.validate_query_range(resolved_start_date, resolved_end_date)

        # 转换为紧凑格式并返回。
        return resolved_start_date.replace("-", ""), resolved_end_date.replace("-", "")

    # 定义表格解析方法。
    def parse_table(self, page_text):

        """
        解析响应页面中首个数据表格的表头与数据行。

        :param page_text: 响应 HTML 文本。
        :type page_text: str
        :return: 表头列表和数据行集合。
        :rtype: tuple[list[str], list[list[str]]]
        """

        # 构建表格解析器。
        parser = ScmTableParser()

        # 解析页面。
        parser.feed(page_text)

        # 关闭解析器。
        parser.close()

        # 选择数据表：优先行数最多的表格（跳过布局表）。
        best_headers, best_rows = None, []
        for headers, rows in parser.tables:
            if rows and len(rows) > len(best_rows):
                best_headers, best_rows = headers, rows

        # 返回数据表的表头与数据行。
        return best_headers, best_rows
