# -*- coding: utf-8 -*-
"""
天济协同平台协议适配器。

本模块负责天济大药房协同平台（襄阳天济工作区）的会话登录、报表检索、
报表数据读取和本地 Excel 生成，库存类型合并门店库存与实时库存双工作表交付。
"""

# 导入操作系统路径模块。
import os

# 导入超文本解析器基类。
from html.parser import HTMLParser

# 导入正则表达式模块。
import re

# 导入日期时间模块。
from datetime import datetime

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入公共日志库。
from ddi_framework import PrintHandler

# 导入 Excel 标准样式函数。
from ddi_framework.excel_style import apply_standard_excel_style


# 定义数据类型到检索报表编号清单的映射常量（与浏览器抓包一致）。
REPORT_DATA_TYPE_IDS = {
    "配送流向": ["0O0LO3T0QP5"],
    "购进流向": ["0O0LOGUHNU9"],
    "纯销流向": ["0O0LOTGZ6TX"],
    "库存": ["0THNNBTDD11", "0O0LP22MLRT"],
}

# 定义库存报表编号到工作表名称的映射常量。
INVENTORY_SHEET_NAMES = {
    "0THNNBTDD11": "门店库存",
    "0O0LP22MLRT": "实时库存",
}

# 定义报表汇总行首列文本常量。
TOTAL_ROW_LABEL = "合计"

# 定义检索参数串提取正则（服务端在检索响应中下发）。
PARAM_JSON_PATTERN = re.compile(r"report_loadDataView\('[^']*',\s*'([^']+)'\)")


# 定义天济登录表单解析器。
class TianjiFormParser(HTMLParser):

    """
    解析天济平台页面中的全部表单字段。

    :return: 登录表单解析器实例。
    :rtype: TianjiFormParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化表单字段容器。

        :return: None。
        :rtype: None
        """

        # 调用父类初始化逻辑。
        super().__init__()

        # 初始化字段名到字段值的映射容器。
        self.inputs = {}

    # 定义开始标签处理方法。
    def handle_starttag(self, tag, attrs):

        """
        收集 input 表单字段。

        :param tag: 标签名称。
        :type tag: str
        :param attrs: 标签属性清单。
        :type attrs: list[tuple[str, str | None]]
        :return: None。
        :rtype: None
        """

        # 只关注 input 标签。
        if tag != "input":

            # 非 input 标签直接返回。
            return

        # 构建属性字典。
        attributes = dict(attrs)

        # 跳过按钮类字段。
        if attributes.get("type", "").lower() in ("submit", "button", "image"):

            # 按钮字段不参与请求体提交。
            return

        # 读取字段名称。
        field_name = attributes.get("name")

        # 仅登记命名字段。
        if field_name:

            # 记录字段当前值。
            self.inputs[field_name] = attributes.get("value", "")


# 定义天济报表表格解析器。
class TianjiReportTableParser(HTMLParser):

    """
    解析报表数据响应中的表头与数据行。

    表头取 thead 内 th 元素的 data-field 与 data-title 属性，
    数据行取 tbody 内 tr 的 td 文本，保留接口原始标题与列顺序。

    :return: 报表表格解析器实例。
    :rtype: TianjiReportTableParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化表头与数据行容器。

        :return: None。
        :rtype: None
        """

        # 调用父类初始化逻辑。
        super().__init__()

        # 初始化表头清单（元素为 {"title": 标题, "field": 字段名}）。
        self.headers = []

        # 初始化数据行清单（元素为单元格文本列表）。
        self.rows = []

        # 初始化当前所在表格区段（thead 或 tbody）。
        self.section = None

        # 初始化当前表头单元格属性。
        self.header_item = None

        # 初始化当前表头单元格文本缓冲。
        self.header_text_parts = []

        # 初始化当前数据行缓冲。
        self.current_row = None

        # 初始化当前数据单元格文本缓冲。
        self.cell_text_parts = None

    # 定义开始标签处理方法。
    def handle_starttag(self, tag, attrs):

        """
        跟踪表格区段并进入表头或单元格采集状态。

        :param tag: 标签名称。
        :type tag: str
        :param attrs: 标签属性清单。
        :type attrs: list[tuple[str, str | None]]
        :return: None。
        :rtype: None
        """

        # 记录表头与表体区段起点。
        if tag in ("thead", "tbody"):

            # 保存当前区段名称。
            self.section = tag

            # 区段标签无需进一步处理。
            return

        # 进入表头单元格采集状态。
        if tag == "th" and self.section == "thead":

            # 构建属性字典。
            attributes = dict(attrs)

            # 初始化表头单元格结构。
            self.header_item = {"title": attributes.get("data-title", ""), "field": attributes.get("data-field", "")}

            # 清空表头文本缓冲。
            self.header_text_parts = []

            # 结束标签处理。
            return

        # 进入数据行采集状态。
        if tag == "tr" and self.section == "tbody":

            # 初始化当前数据行缓冲。
            self.current_row = []

            # 结束标签处理。
            return

        # 进入数据单元格采集状态。
        if tag == "td" and self.section == "tbody" and self.current_row is not None:

            # 初始化单元格文本缓冲。
            self.cell_text_parts = []

            # 结束标签处理。
            return

    # 定义文本数据处理方法。
    def handle_data(self, data):

        """
        收集表头与数据单元格内的文本片段。

        :param data: 文本数据片段。
        :type data: str
        :return: None。
        :rtype: None
        """

        # 处于表头单元格状态时收集标题文本。
        if self.header_item is not None:

            # 追加标题文本片段。
            self.header_text_parts.append(data)

            # 结束文本处理。
            return

        # 处于数据单元格状态时收集单元格文本。
        if self.cell_text_parts is not None:

            # 追加单元格文本片段。
            self.cell_text_parts.append(data)

    # 定义结束标签处理方法。
    def handle_endtag(self, tag):

        """
        在标签闭合时归档表头与数据行。

        :param tag: 标签名称。
        :type tag: str
        :return: None。
        :rtype: None
        """

        # 表头单元格闭合时归档标题。
        if tag == "th" and self.header_item is not None:

            # 属性缺失标题时回退使用单元格文本。
            if not self.header_item["title"]:

                # 使用采集到的单元格文本作为标题。
                self.header_item["title"] = "".join(self.header_text_parts).strip()

            # 归档表头单元格。
            self.headers.append(self.header_item)

            # 退出表头单元格状态。
            self.header_item = None

            # 结束标签处理。
            return

        # 数据单元格闭合时归档单元格文本。
        if tag == "td" and self.cell_text_parts is not None:

            # 归档清洗后的单元格文本。
            self.current_row.append("".join(self.cell_text_parts).strip())

            # 退出单元格状态。
            self.cell_text_parts = None

            # 结束标签处理。
            return

        # 数据行闭合时归档整行。
        if tag == "tr" and self.current_row is not None:

            # 跳过空行。
            if any(cell for cell in self.current_row):

                # 归档当前数据行。
                self.rows.append(self.current_row)

            # 退出数据行状态。
            self.current_row = None

            # 结束标签处理。
            return

        # 表头表体区段闭合时退出区段状态。
        if tag in ("thead", "tbody"):

            # 清空当前区段。
            self.section = None

# 定义报表汇总行剔除函数。
def strip_total_rows(rows):

    """
    剔除报表数据中的页面汇总行。

    平台每张报表末行携带「合计」汇总行，页面记录数口径不含该行，交付口径与其保持一致。

    :param rows: 报表数据行清单。
    :type rows: list[list[str]]
    :return: 剔除汇总行后的数据行清单。
    :rtype: list[list[str]]
    """

    # 仅剔除首列为合计的汇总行。
    return [row for row in rows if not (row and row[0] == TOTAL_ROW_LABEL)]


# 定义天济协同平台适配器。
class TianjiPlatform(BasePlatform):

    """
    天济大药房协同平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 天济协同平台适配器实例。
    :rtype: TianjiPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化天济协同平台适配器。

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

        # 初始化日志打印器。
        self.ph = printer or PrintHandler()

        # 保存站点根地址。
        self.base_url = account.get("接口根地址", "http://gys.tianjiyy.com:9090").rstrip("/")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.base_url}/Account/Login")

        # 保存报表工作区编号（襄阳天济）。
        self.workspace_id = account.get("工作区编号", "0O0LNH1Y131")

        # 保存检索页地址。
        self.search_url = account.get("检索地址", f"{self.base_url}/ReportView/ReportSearch?Length=10")

        # 保存条件表单接口地址。
        self.filter_url = account.get("条件表单接口", f"{self.base_url}/ReportView/ReportFilter")

        # 保存报表数据接口地址。
        self.report_data_url = account.get("报表数据接口", f"{self.base_url}/ReportView/ReportSearchData")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态。
        self.logged_in = False

        # 初始化最近一次检索参数串。
        self.param_json = ""

        # 保存报表数据请求超时秒数（万行级报表响应较慢，默认放宽到 60 秒）。
        self.report_timeout = int(account.get("请求超时秒数", 60))

    # 定义文本响应解码方法。
    def decode_response_text(self, result):

        """
        将响应体字节按 UTF-8 解码为文本。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 响应文本。
        :rtype: str
        """

        # 按站点字符集解码响应体。
        return result.body.decode("utf-8", "replace")

    # 定义平台登录方法。
    def login(self):

        """
        执行天济协同平台登录。

        登录页取防伪令牌后提交表单，以 302 跳转与 .MONOAUTH 会话 Cookie 判定成功。

        :return: 登录响应结果。
        :rtype: HttpResult
        """

        # 打印登录阶段标题。
        self.ph.section("天济协同登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 请求登录页以初始化会话 Cookie。
        login_page_result = self.http.get(self.login_page_url)

        # 解析登录页表单字段。
        parser = TianjiFormParser()

        # 喂入登录页文本。
        parser.feed(self.decode_response_text(login_page_result))

        # 构建登录请求体。
        payload = self.build_login_payload(parser.inputs)

        # 打印登录账号日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("防伪令牌", "已获取", "green")))

        # 提交登录表单（禁跟随重定向以观察 302）。
        login_result = self.http.request(
            "POST",
            self.login_page_url,
            headers=self.http.ajax_form_headers(self.login_page_url),
            data=urlencode(payload).encode("utf-8"),
            allow_http_error=True,
            follow_redirects=False,
        )

        # 校验登录响应状态。
        if not self.is_login_success(login_result):

            # 提取失败文案。
            failure_reason = self.extract_login_failure_reason(login_result)

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{failure_reason}")

        # 标记当前会话已登录。
        self.logged_in = True

        # 加载登录后首页确认会话可用。
        self.load_home_page()

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("正式登录成功", "登录成功", "green"))

        # 返回登录响应结果。
        return login_result

    # 定义登录请求体构建方法。
    def build_login_payload(self, page_inputs):

        """
        构建登录表单请求体。

        :param page_inputs: 登录页解析出的表单字段。
        :type page_inputs: dict
        :return: 登录表单字段。
        :rtype: dict
        """

        # 以登录页隐藏字段为基础。
        payload = dict(page_inputs)

        # 写入登录账号。
        payload["UserName"] = self.clean_login_name()

        # 写入登录密码。
        payload["Password"] = self.clean_login_password()

        # 固定不记住登录态。
        payload["RememberMe"] = "false"

        # 返回登录请求体。
        return payload

    # 定义登录成功判定方法。
    def is_login_success(self, login_result):

        """
        判定登录响应是否建立有效会话。

        :param login_result: 登录响应结果。
        :type login_result: HttpResult
        :return: 登录是否成功。
        :rtype: bool
        """

        # 判定响应是否为登录成功的站内跳转。
        redirected_to_home = login_result.status_code == 302 and login_result.headers.get("Location", "").startswith("/")

        # 判定会话中是否已下发授权 Cookie。
        has_auth_cookie = any(cookie.name == ".MONOAUTH" for cookie in self.http.cookie_jar)

        # 两个条件同时成立视为登录成功。
        return redirected_to_home and has_auth_cookie

    # 定义登录失败文案提取方法。
    def extract_login_failure_reason(self, login_result):

        """
        从登录响应中提取平台失败提示。

        :param login_result: 登录响应结果。
        :type login_result: HttpResult
        :return: 失败提示文本。
        :rtype: str
        """

        # 解码登录响应文本。
        response_text = self.decode_response_text(login_result)

        # 匹配平台返回的账号密码错误文案。
        match = re.search(r"([^<>]*不正确[^<>]*)", response_text)

        # 命中平台文案时返回该文案。
        if match:

            # 返回清洗后的失败文案。
            return match.group(1).strip()

        # 未命中平台文案时返回状态码概要。
        return f"HTTP {login_result.status_code}，未建立授权会话"

    # 定义登录后首页加载方法。
    def load_home_page(self):

        """
        加载登录后首页并确认会话身份。

        :return: None。
        :rtype: None
        """

        # 请求站点首页。
        home_result = self.http.get(f"{self.base_url}/")

        # 解码首页文本。
        home_text = self.decode_response_text(home_result)

        # 校验首页是否包含注销入口。
        if "注销[" not in home_text:

            # 抛出会话校验失败异常。
            raise RuntimeError(f"{self.company_name} 登录后首页未识别到登录态，请核对账号归属")

        # 返回空结果。
        return None

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        :raises ValueError: 数据类型未接入时抛出。
        """

        # 判断数据类型不在接入清单。
        if data_type not in REPORT_DATA_TYPE_IDS:

            # 抛出未接入类型异常。
            raise ValueError(f"{self.company_name} 未接入数据类型：{data_type}")

        # 返回空结果。
        return None

    # 定义检索日期解析方法。
    def resolve_query_dates(self, data_type, start_date, end_date):

        """
        解析本次检索使用的起止日期。

        流向类必须显式提供起止日期；库存类为当天快照，日期仅用于满足检索表单。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 起止日期二元组。
        :rtype: tuple[str, str]
        """

        # 判断库存类缺省日期时使用平台默认口径。
        if "库存" in data_type:

            # 缺省开始日期取当月一号。
            resolved_start = start_date or datetime.now().strftime("%Y-%m-01")

            # 缺省结束日期取当天。
            resolved_end = end_date or datetime.now().strftime("%Y-%m-%d")

            # 返回库存类解析结果。
            return resolved_start, resolved_end

        # 流向类必须显式提供起止日期。
        if not start_date or not end_date:

            # 抛出日期缺失异常。
            raise ValueError(f"{self.company_name} {data_type} 查询必须提供开始日期与结束日期")

        # 校验起止日期先后顺序。
        self.validate_query_range(start_date, end_date)

        # 返回流向类解析结果（平台数据实测两端含，按原样透传）。
        return start_date, end_date

    # 定义检索条件获取方法。
    def fetch_filter_fields(self):

        """
        获取检索条件表单的动态字段与防伪令牌。

        :return: 条件表单字段字典。
        :rtype: dict
        """

        # 请求条件表单接口。
        filter_result = self.http.post_form(self.filter_url, {"id": self.workspace_id}, f"{self.base_url}/")

        # 解码条件表单文本。
        filter_text = self.decode_response_text(filter_result)

        # 解析条件表单字段。
        parser = TianjiFormParser()

        # 喂入条件表单文本。
        parser.feed(filter_text)

        # 返回条件表单字段字典。
        return parser.inputs

    # 定义报表检索方法。
    def search_reports(self, data_type, start_date, end_date):

        """
        执行报表检索并取得检索参数串。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 检索参数串。
        :rtype: str
        """

        # 获取条件表单动态字段。
        filter_fields = self.fetch_filter_fields()

        # 初始化检索请求体。
        search_fields = {"__RequestVerificationToken": filter_fields.get("__RequestVerificationToken", "")}

        # 透传条件表单携带的报表编号与标题。
        for reserved_field in ("ReportId", "ReportTitle"):

            # 命中保留字段时透传。
            if reserved_field in filter_fields:

                # 写入保留字段。
                search_fields[reserved_field] = filter_fields[reserved_field]

        # 收集过滤参数索引清单。
        filter_indexes = sorted({int(match.group(1)) for name in filter_fields for match in [re.match(r"ReportFilter\[(\d+)\]\.ParamName", name)] if match})

        # 逐索引组装过滤参数三元组。
        for index in filter_indexes:

            # 读取参数名称。
            param_name = filter_fields.get(f"ReportFilter[{index}].ParamName", "")

            # 读取参数编号。
            param_id = filter_fields.get(f"ReportFilter[{index}].ParamID", "")

            # 按参数名称取本次查询值。
            param_value = self.resolve_filter_param_value(param_name, start_date, end_date)

            # 写入参数编号字段。
            search_fields[f"ReportFilter[{index}].ParamID"] = param_id

            # 写入参数名称字段。
            search_fields[f"ReportFilter[{index}].ParamName"] = param_name

            # 写入参数取值字段。
            search_fields[f"ReportFilter[{index}].ParamValue"] = param_value

        # 提交报表检索请求。
        search_result = self.http.post_form(self.search_url, search_fields, f"{self.base_url}/")

        # 解码检索响应文本。
        search_text = self.decode_response_text(search_result)

        # 提取服务端下发的检索参数串。
        match = PARAM_JSON_PATTERN.search(search_text)

        # 校验参数串提取结果。
        if not match:

            # 抛出检索参数缺失异常。
            raise RuntimeError(f"{self.company_name} 检索响应未返回报表参数串，请核对会话与工作区编号")

        # 返回检索参数串。
        return match.group(1)

    # 定义过滤参数取值解析方法。
    def resolve_filter_param_value(self, param_name, start_date, end_date):

        """
        按参数名称解析本次查询的过滤取值。

        :param param_name: 过滤参数名称。
        :type param_name: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 过滤参数取值。
        :rtype: str
        """

        # 开始日期参数取查询开始日期。
        if param_name == "startdate":

            # 返回开始日期。
            return start_date

        # 结束日期参数取查询结束日期。
        if param_name == "enddate":

            # 返回结束日期。
            return end_date

        # 其余参数（如品名）固定留空。
        return ""

    # 定义报表数据读取方法。
    def fetch_report_table(self, report_data_id, param_json):

        """
        读取指定报表的全量数据。

        :param report_data_id: 报表数据编号。
        :type report_data_id: str
        :param param_json: 检索参数串。
        :type param_json: str
        :return: 表头与数据行。
        :rtype: dict
        """

        # 构建报表数据请求体。
        payload = {"reportid": self.workspace_id, "reportdataid": report_data_id, "param_json": param_json}

        # 请求报表数据接口（大数据量报表按放宽后的超时执行）。
        data_result = self.http.request(
            "POST",
            self.report_data_url,
            headers=self.http.ajax_form_headers(f"{self.base_url}/"),
            data=urlencode(payload).encode("utf-8"),
            timeout=self.report_timeout,
        )

        # 解析报表表格。
        parser = TianjiReportTableParser()

        # 喂入报表数据文本。
        parser.feed(self.decode_response_text(data_result))

        # 剔除页面自身的汇总行。
        data_rows = strip_total_rows(parser.rows)

        # 返回表头与数据行。
        return {"headers": parser.headers, "rows": data_rows}

    # 定义日期范围校验方法。
    def validate_report_dates(self, data_type, table, start_date, end_date):

        """
        校验报表业务日期范围并记录快照日期。

        流向类要求全部业务日期落在请求区间内；库存类仅记录截至日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param table: 表头与数据行。
        :type table: dict
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 定位第一个日期标题列的位置。
        date_index = next((position for position, header in enumerate(table["headers"]) if "日期" in header["title"]), None)

        # 无日期列时跳过校验。
        if date_index is None:

            # 结束校验流程。
            return

        # 收集数据行中的规范日期值。
        date_values = [row[date_index] for row in table["rows"] if len(row) > date_index and re.match(r"^\d{4}-\d{2}-\d{2}$", row[date_index])]

        # 无日期数据时结束校验。
        if not date_values:

            # 结束校验流程。
            return

        # 计算业务日期最小值。
        min_date = min(date_values)

        # 计算业务日期最大值。
        max_date = max(date_values)

        # 库存类记录快照日期口径。
        if "库存" in data_type:

            # 打印库存快照日期日志。
            self.ph.info(self.ph.join(self.ph.kv("库存截至日期", max_date, "yellow"), self.ph.kv("快照口径", "当天库存，日期参数不参与过滤", "yellow")))

            # 库存类不参与区间校验。
            return

        # 判断业务日期超出请求区间。
        if min_date < start_date or max_date > end_date:

            # 抛出日期范围异常。
            raise RuntimeError(f"{self.company_name} {data_type} 业务日期越界：数据范围 {min_date}~{max_date}，请求范围 {start_date}~{end_date}")

        # 打印日期范围核对日志。
        self.ph.info(self.ph.kv("业务日期核对", f"{min_date}~{max_date}", "green"))

        # 返回空结果。
        return None

    # 定义数据行字典转换方法。
    def build_row_dicts(self, table, report_data_id):

        """
        将报表数据行转换为字段字典清单。

        库存双报表附加报表名称键，供查询 JSON 产物区分来源；
        重复字段名仅保留首个取值，Excel 交付不受影响。

        :param table: 表头与数据行。
        :type table: dict
        :param report_data_id: 报表数据编号。
        :type report_data_id: str
        :return: 字段字典行清单。
        :rtype: list[dict]
        """

        # 初始化字典行清单。
        row_dicts = []

        # 遍历报表数据行。
        for row in table["rows"]:

            # 初始化当前行字典。
            row_dict = {}

            # 按列位置写入字段取值。
            for position, header in enumerate(table["headers"]):

                # 跳过越界单元格。
                if position >= len(row):

                    # 结束当前行列写入。
                    break

                # 首次出现的字段写入取值。
                if header["field"] and header["field"] not in row_dict:

                    # 写入字段取值。
                    row_dict[header["field"]] = row[position]

            # 库存双报表附加报表名称。
            if report_data_id in INVENTORY_SHEET_NAMES:

                # 写入报表名称键。
                row_dict["报表名称"] = INVENTORY_SHEET_NAMES[report_data_id]

            # 归档当前行字典。
            row_dicts.append(row_dict)

        # 返回字典行清单。
        return row_dicts

    # 定义平台查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行。
        :rtype: list[dict]
        """

        # 校验数据类型已接入。
        self.validate_data_type(data_type)

        # 确保会话已登录。
        self.ensure_logged_in()

        # 解析本次检索起止日期。
        resolved_start, resolved_end = self.resolve_query_dates(data_type, start_date, end_date)

        # 打印查询阶段分隔线。
        self.print_query_section(data_type, resolved_start, resolved_end)

        # 执行检索取得参数串。
        self.param_json = self.search_reports(data_type, resolved_start, resolved_end)

        # 打印检索完成日志。
        self.ph.info(self.ph.kv("检索参数串", f"{self.param_json[:24]}...", "cyan"))

        # 初始化合并结果行。
        merged_rows = []

        # 逐报表读取数据。
        for report_data_id in REPORT_DATA_TYPE_IDS[data_type]:

            # 读取当前报表全量数据。
            table = self.fetch_report_table(report_data_id, self.param_json)

            # 校验报表业务日期范围。
            self.validate_report_dates(data_type, table, resolved_start, resolved_end)

            # 转换字典行并合并。
            merged_rows.extend(self.build_row_dicts(table, report_data_id))

            # 打印报表读取完成日志。
            self.ph.success(self.ph.kv(f"{INVENTORY_SHEET_NAMES.get(report_data_id, data_type)}读取完成", f"{len(table['rows'])} 条", "green"))

        # 返回合并结果行。
        return merged_rows

    # 定义报表工作簿写入方法。
    def write_report_excel(self, sheets, output_path):

        """
        将报表工作表集合写入 Excel 文件。

        :param sheets: 工作表清单（元素为工作表名、表头、数据行三元组）。
        :type sheets: list[tuple[str, list[dict], list[list[str]]]]
        :param output_path: 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 延迟导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 延迟导入列宽工具函数。
        from openpyxl.utils import get_column_letter

        # 创建 Excel 工作簿。
        workbook = Workbook(write_only=False)

        # 遍历工作表清单写入内容。
        for sheet_index, (sheet_name, headers, rows) in enumerate(sheets):

            # 首表复用默认工作表。
            if sheet_index == 0:

                # 读取默认工作表。
                worksheet = workbook.active

                # 设置工作表名称。
                worksheet.title = sheet_name[:31]

            # 后续表新建工作表。
            else:

                # 新建工作表。
                worksheet = workbook.create_sheet(sheet_name[:31])

            # 写入表头行（保留接口原始标题顺序）。
            worksheet.append([header["title"] for header in headers])

            # 遍历数据行写入原始单元格文本。
            for row in rows:

                # 按原始列顺序写入整行。
                worksheet.append(row)

            # 遍历所有导出列设置列宽。
            for column_index, header in enumerate(headers, start=1):

                # 读取当前列字母。
                column_letter = get_column_letter(column_index)

                # 按标题长度设置列宽。
                worksheet.column_dimensions[column_letter].width = max(12, min(34, len(header["title"]) + 10))

            # 冻结表头行。
            worksheet.freeze_panes = "A2"

            # 启用自动筛选。
            worksheet.auto_filter.ref = worksheet.dimensions

        # 创建输出目录。
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 删除已有同名文件。
        self.remove_existing_file(output_path)

        # 保存 Excel 文件。
        try:

            # 将工作簿保存到目标路径。
            workbook.save(output_path)

        # 处理文件被占用导致的保存异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

        # 应用项目标准 Excel 样式。
        apply_standard_excel_style(output_path)

        # 返回空结果。
        return None

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型业务数据并生成 Excel。

        流向类输出单工作表，库存类输出门店库存与实时库存双工作表。

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

        # 校验数据类型已接入。
        self.validate_data_type(data_type)

        # 确保会话已登录。
        self.ensure_logged_in()

        # 解析本次检索起止日期。
        resolved_start, resolved_end = self.resolve_query_dates(data_type, start_date, end_date)

        # 打印查询阶段分隔线。
        self.print_query_section(data_type, resolved_start, resolved_end)

        # 执行检索取得参数串。
        self.param_json = self.search_reports(data_type, resolved_start, resolved_end)

        # 打印检索完成日志。
        self.ph.info(self.ph.kv("检索参数串", f"{self.param_json[:24]}...", "cyan"))

        # 初始化工作表清单。
        sheets = []

        # 初始化总记录数。
        total_rows = 0

        # 逐报表读取并组装工作表。
        for report_data_id in REPORT_DATA_TYPE_IDS[data_type]:

            # 读取当前报表全量数据。
            table = self.fetch_report_table(report_data_id, self.param_json)

            # 校验报表业务日期范围。
            self.validate_report_dates(data_type, table, resolved_start, resolved_end)

            # 解析工作表名称（库存双报表用分表名，流向类用数据类型名）。
            sheet_name = INVENTORY_SHEET_NAMES.get(report_data_id, data_type)

            # 归档当前工作表。
            sheets.append((sheet_name, table["headers"], table["rows"]))

            # 累加总记录数。
            total_rows += len(table["rows"])

            # 打印报表读取完成日志。
            self.ph.success(self.ph.kv(f"{sheet_name}读取完成", f"{len(table['rows'])} 条", "green"))

        # 使用当前工作目录作为默认输出目录。
        output_dir = output_dir or os.getcwd()

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建输出文件名（库存类按导出当天快照命名）。
        file_name = self.build_output_file_name(data_type, resolved_start, resolved_end)

        # 构建输出文件路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_report_excel(sheets, output_path)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("工作表", "、".join(name for name, _, _ in sheets), "cyan"), self.ph.kv("记录数", f"{total_rows} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path
