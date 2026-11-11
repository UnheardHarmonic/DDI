# -*- coding: utf-8 -*-
"""
国大药房供应商查询平台协议适配器。

本模块负责国药集团国大药房供应商查询平台（new_gyssystem）的协议登录、
大仓购进、大仓配送、门店纯销与大仓/门店库存查询及原始字段 Excel 落地。
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


# 定义数据类型与协议端点及筛选能力映射。
DATA_TYPE_CONFIG = {
    "购进流向": {"端点": "dcjh", "日期列": "进货日期", "需要日期": True, "需要公司": True},
    "配送流向": {"端点": "phlx", "日期列": "销售日期", "需要日期": True, "需要公司": True},
    "纯销流向": {"端点": "mdcx", "日期列": "销售日期", "需要日期": True, "需要公司": False},
    "库存": {"端点": "dckc", "日期列": "", "需要日期": False, "需要公司": True},
}

# 定义库存类型的门店库存附属端点与工作表命名映射。
INVENTORY_SHEET_CONFIG = {
    "dckc": "大仓库存",
    "mdkc": "门店库存",
}


# 定义供应商平台表格解析器。
class GysTableParser(HTMLParser):

    """
    解析供应商平台响应中的首个表格，输出表头标题与原始数据行。

    :return: 供应商平台表格解析器实例。
    :rtype: GysTableParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化表格状态、行集合与单元格缓冲。

        :return: None。
        :rtype: None
        """

        # 调用父类初始化逻辑。
        super().__init__()

        # 初始化表头标题列表。
        self.headers = []

        # 初始化数据行集合。
        self.rows = []

        # 初始化当前行单元格集合。
        self.cells = []

        # 初始化当前单元格文本缓冲。
        self.text_parts = []

        # 初始化当前单元格类型标记（th 为表头，td 为数据）。
        self.cell_kind = ""

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

        # 判断当前标签为表头或数据单元格。
        if tag in ("th", "td"):

            # 记录当前单元格类型。
            self.cell_kind = tag

            # 重置单元格文本缓冲。
            self.text_parts = []

            # 直接结束处理。
            return

        # 判断当前标签为表格行。
        if tag == "tr":

            # 重置当前行单元格集合。
            self.cells = []

    # 定义结束标签处理方法。
    def handle_endtag(self, tag):

        """
        捕获单元格与表格行的结束标签并装配数据。

        :param tag: 标签名。
        :type tag: str
        :return: None。
        :rtype: None
        """

        # 判断当前标签为表头或数据单元格。
        if tag in ("th", "td") and self.cell_kind:

            # 装配单元格文本。
            self.cells.append(("".join(self.text_parts)).strip())

            # 清空单元格类型标记。
            self.cell_kind = ""

            # 直接结束处理。
            return

        # 判断当前标签为表格行且已有单元格。
        if tag == "tr" and self.cells:

            # 判断当前行为表头行（全部为 th 类型且表头尚未写入）。
            if not self.headers:

                # 写入表头标题列表。
                self.headers = self.cells

                # 直接结束处理。
                return

            # 追加当前数据行。
            self.rows.append(self.cells)

    # 定义文本片段处理方法。
    def handle_data(self, data):

        """
        累积当前单元格内的文本片段。

        :param data: 文本片段。
        :type data: str
        :return: None。
        :rtype: None
        """

        # 判断当前处于单元格内。
        if self.cell_kind:

            # 追加文本片段。
            self.text_parts.append(data)


# 定义国大药房供应商查询平台适配器。
class GuodagysPlatform(BasePlatform):

    """
    国大药房供应商查询平台（new_gyssystem）协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 国大药房供应商查询平台适配器实例。
    :rtype: GuodagysPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化站点地址、系统路径与协议客户端。

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

        # 读取平台 HTTP 服务根地址。
        self.base_url = str(account.get("接口根地址", "")).rstrip("/")

        # 读取供应商系统部署路径。
        self.system_path = str(account.get("系统路径", "/new_gyssystem")).strip()

        # 读取查询公司选项编码。
        self.company_code = str(account.get("公司编码", "")).strip()

        # 读取查询请求超时时间。
        self.query_timeout_seconds = int(account.get("查询超时秒", 300))

        # 初始化带 Cookie 管理的协议客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态标识。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        提交登录 Servlet 表单请求并建立 JSP 会话。

        :return: 不含凭据的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("国大药房供应商平台登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页初始化 JSP 会话 Cookie。
        self.http.get(self.build_url("login.jsp"), referer=self.base_url + "/")

        # 构建登录表单字段。
        payload = self.build_login_payload()

        # 构建浏览器同款登录请求头。
        headers = self.build_login_headers()

        # 提交登录表单。
        result = self.http.request("POST", self.build_url("loginServlet?bj=0"), headers=headers, data=payload.encode("utf-8"), timeout=self.query_timeout_seconds, allow_http_error=True)

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", "replace").strip()

        # 校验登录响应为成功标记。
        self.validate_login_response(response_text)

        # 标记当前协议会话已登录。
        self.logged_in = True

        # 打印不含敏感值的登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("Cookie", len(list(self.http.cookie_jar)), "cyan")))

        # 返回不含敏感字段的登录结果。
        return {"登录状态": "成功", "Cookie数量": len(list(self.http.cookie_jar))}

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建登录 Servlet 需要的账号密码表单字段。

        :return: URL 编码前的登录表单文本。
        :rtype: str
        """

        # 拼接账号与密码表单字段（浏览器抓包确认无验证码字段）。
        return f"zh={self.account.get('账号', '')}&mm={self.account.get('密码', '')}"

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建对齐浏览器抓包的登录请求头。

        :return: 登录请求头字典。
        :rtype: dict
        """

        # 返回浏览器同款 Ajax 登录请求头。
        return {"Accept": "*/*", "X-Requested-With": "XMLHttpRequest", "Origin": self.base_url, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": self.build_url("login.jsp")}

    # 定义登录响应校验方法。
    def validate_login_response(self, response_text):

        """
        校验登录响应文本为成功标记。

        :param response_text: 登录 Servlet 响应文本。
        :type response_text: str
        :return: None。
        :rtype: None
        """

        # 判断响应文本不是成功标记。
        if response_text != "cg":

            # 抛出不含凭据的登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：平台返回 {response_text[:60] or '空响应'}")

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

        # 判断当前类型为库存双源类型。
        if data_type == "库存":

            # 合并大仓与门店库存记录。
            merged_rows = self.fetch_inventory_rows()

            # 返回合并后的库存记录。
            return merged_rows

        # 请求当前流向类型的全量表格记录。
        headers, rows = self.fetch_table_rows(data_type, self.resolve_config(data_type), start_date, end_date)

        # 校验流向记录的业务日期处于请求范围。
        self.validate_result_date_range(data_type, headers, rows, start_date, end_date)

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

        # 判断当前类型为库存双源类型。
        if data_type == "库存":

            # 生成大仓与门店双工作表库存 Excel。
            return self.write_inventory_excel(start_date, end_date, output_dir)

        # 解析当前流向类型的协议配置。
        config = self.resolve_config(data_type)

        # 解析当前查询的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(start_date, end_date)

        # 请求当前流向类型的全量表格记录。
        headers, rows = self.fetch_table_rows(data_type, config, resolved_start_date, resolved_end_date)

        # 校验流向记录的业务日期处于请求范围。
        self.validate_result_date_range(data_type, headers, rows, resolved_start_date, resolved_end_date)

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, resolved_start_date, resolved_end_date)

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入原始字段 Excel。
        self.write_rows_to_excel(rows, headers, output_path)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义库存双工作表 Excel 生成方法。
    def write_inventory_excel(self, start_date, end_date, output_dir):

        """
        查询大仓与门店库存并生成双工作表库存 Excel。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 生成当天日期文本用于文件命名。
        today_text = self.resolve_today_text()

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name("库存", today_text, today_text)

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 初始化双工作表集合。
        sheets = []

        # 遍历大仓与门店两个库存端点。
        for endpoint_code in ("dckc", "mdkc"):

            # 请求当前端点的全量表格记录。
            headers, rows = self.fetch_table_rows("库存", DATA_TYPE_CONFIG["库存"], None, None, endpoint_code=endpoint_code)

            # 追加当前工作表数据。
            sheets.append((INVENTORY_SHEET_CONFIG[endpoint_code], headers, rows))

            # 打印当前端点读取摘要。
            self.ph.info(self.ph.join(self.ph.kv(f"{INVENTORY_SHEET_CONFIG[endpoint_code]}记录", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 写入双工作表原始字段 Excel。
        self.write_sheets_to_excel(sheets, output_path)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv("库存 Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("工作表", f"{len(sheets)} 个", "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义协议配置解析方法。
    def resolve_config(self, data_type):

        """
        读取数据类型的协议端点与筛选能力配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 协议配置字典。
        :rtype: dict
        """

        # 判断数据类型已配置协议端点。
        if data_type in DATA_TYPE_CONFIG:

            # 返回协议配置字典。
            return DATA_TYPE_CONFIG[data_type]

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型存在于平台协议映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 调用协议配置解析完成校验。
        self.resolve_config(data_type)

    # 定义查询日期解析方法。
    def resolve_query_dates(self, start_date, end_date):

        """
        解析流向查询使用的日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 解析后的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 解析流向查询开始日期。
        resolved_start_date = str(start_date or self.resolve_today_text())

        # 解析流向查询结束日期。
        resolved_end_date = str(end_date or resolved_start_date)

        # 校验流向日期范围顺序。
        self.validate_query_range(resolved_start_date, resolved_end_date)

        # 返回流向查询日期范围。
        return resolved_start_date, resolved_end_date

    # 定义当天日期解析方法。
    def resolve_today_text(self):

        """
        生成当前导出日期文本。

        :return: 当天日期文本。
        :rtype: str
        """

        # 导入日期时间模块。
        from datetime import datetime

        # 返回当天日期文本。
        return datetime.now().strftime("%Y-%m-%d")

    # 定义全量表格请求方法。
    def fetch_table_rows(self, data_type, config, start_date, end_date, endpoint_code=None):

        """
        请求协议端点并解析全量原始表格记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param config: 协议配置字典。
        :type config: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param endpoint_code: 指定端点编码（库存双源时使用）。
        :type endpoint_code: str | None
        :return: 表头标题列表和原始记录字典列表。
        :rtype: tuple[list[str], list[dict]]
        """

        # 确保当前 HTTP 会话已经登录。
        self.ensure_login()

        # 解析实际使用的端点编码。
        actual_endpoint = endpoint_code or config["端点"]

        # 构建当前端点的查询表单文本。
        payload = self.build_query_payload(config, start_date, end_date)

        # 构建查询请求头。
        headers = self.build_query_headers(actual_endpoint)

        # 提交查询表单请求。
        result = self.http.request("POST", self.build_url(f"phServlet?lx={actual_endpoint}"), headers=headers, data=payload.encode("utf-8"), timeout=self.query_timeout_seconds, allow_http_error=True)

        # 解码响应 HTML 文本。
        response_text = result.body.decode("utf-8", "replace")

        # 解析响应表格的表头与数据行。
        table_headers, table_rows = self.parse_table(response_text)

        # 判断表头缺失时抛出响应异常。
        if not table_headers:

            # 抛出查询响应异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询响应未包含表格数据")

        # 按表头标题装配原始记录字典。
        rows = [dict(zip(table_headers, cells)) for cells in table_rows]

        # 打印协议查询完成摘要。
        self.ph.success(self.ph.join(self.ph.kv("查询端点", actual_endpoint, "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(table_headers), "cyan")))

        # 返回表头与原始记录。
        return table_headers, rows

    # 定义库存双源合并方法。
    def fetch_inventory_rows(self):

        """
        合并大仓与门店两个库存端点的原始记录。

        :return: 合并后的库存记录列表。
        :rtype: list[dict]
        """

        # 初始化合并记录集合。
        merged_rows = []

        # 遍历大仓与门店两个库存端点。
        for endpoint_code in ("dckc", "mdkc"):

            # 请求当前端点的全量表格记录。
            headers, rows = self.fetch_table_rows("库存", DATA_TYPE_CONFIG["库存"], None, None, endpoint_code=endpoint_code)

            # 合并当前端点记录。
            merged_rows.extend(rows)

        # 返回合并后的库存记录。
        return merged_rows

    # 定义查询表单构建方法。
    def build_query_payload(self, config, start_date, end_date):

        """
        构建协议端点提交的公司、产品与日期表单字段。

        :param config: 协议配置字典。
        :type config: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: URL 编码前的表单文本。
        :rtype: str
        """

        # 初始化表单字段集合。
        fields = []

        # 判断当前端点需要公司筛选。
        if config["需要公司"]:

            # 写入公司选项编码。
            fields.append(f"gs={self.company_code}")

        # 写入产品编码空值（全量口径）。
        fields.append(f"bm=")

        # 判断当前端点需要日期筛选。
        if config["需要日期"]:

            # 写入开始日期字段。
            fields.append(f"logmin={start_date}")

            # 写入结束日期字段。
            fields.append(f"logmax={end_date}")

        # 拼接表单文本。
        return "&".join(fields)

    # 定义查询请求头构建方法。
    def build_query_headers(self, endpoint_code):

        """
        构建对齐浏览器抓包的查询请求头。

        :param endpoint_code: 端点编码。
        :type endpoint_code: str
        :return: 查询请求头字典。
        :rtype: dict
        """

        # 返回浏览器同款表单查询请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Origin": self.base_url, "Content-Type": "application/x-www-form-urlencoded", "Referer": self.build_url(f"{endpoint_code}.jsp")}

    # 定义响应表格解析方法。
    def parse_table(self, response_text):

        """
        解析响应 HTML 中首个表格的表头与数据行。

        :param response_text: 响应 HTML 文本。
        :type response_text: str
        :return: 表头标题列表和数据行集合。
        :rtype: tuple[list[str], list[list[str]]]
        """

        # 构建表格解析器实例。
        parser = GysTableParser()

        # 解析响应文本。
        parser.feed(response_text)

        # 关闭解析器。
        parser.close()

        # 返回表头与数据行。
        return parser.headers, parser.rows

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, data_type, headers, rows, start_date, end_date):

        """
        校验流向记录日期未超出提交的查询范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param headers: 表头标题列表。
        :type headers: list[str]
        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 判断当前查询未提供日期范围。
        if not start_date or not end_date:

            # 结束无日期范围的校验。
            return

        # 读取当前数据类型的业务日期列。
        date_column = self.resolve_config(data_type)["日期列"]

        # 导入日期解析函数。
        from datetime import datetime

        # 解析请求开始日期对象。
        start_value = datetime.strptime(str(start_date), "%Y-%m-%d").date()

        # 解析请求结束日期对象。
        end_value = datetime.strptime(str(end_date), "%Y-%m-%d").date()

        # 遍历返回的原始记录。
        for row in rows:

            # 读取当前记录的业务日期文本。
            date_text = str(row.get(date_column, "")).strip()

            # 跳过空日期字段记录。
            if not date_text:

                # 继续校验下一条记录。
                continue

            # 解析日期文本前十位。
            record_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()

            # 判断记录日期是否处于请求范围。
            if start_value <= record_date <= end_value:

                # 继续校验下一条记录。
                continue

            # 抛出业务日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期超出查询范围：{date_text}")

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path):

        """
        按接口表头标题与顺序写入原始字段 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 表头标题列表。
        :type headers: list[str]
        :param output_path: Excel 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 装配字段定义列表。
        field_headers = [{"key": title, "title": title} for title in headers]

        # 写入原始标题、原始顺序和全部原始字段。
        write_formal_raw_excel(output_path, field_headers, rows, sheet_name="流向明细")

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)

    # 定义多工作表 Excel 写入方法。
    def write_sheets_to_excel(self, sheets, output_path):

        """
        按工作表集合写入多表原始字段 Excel。

        :param sheets: 工作表集合，元素为（表名, 表头, 记录）。
        :type sheets: list[tuple[str, list[str], list[dict]]]
        :param output_path: Excel 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 导入工作簿对象。
        from openpyxl import Workbook

        # 创建工作簿。
        workbook = Workbook()

        # 移除默认工作表。
        workbook.remove(workbook.active)

        # 遍历工作表集合。
        for sheet_name, headers, rows in sheets:

            # 创建当前工作表。
            worksheet = workbook.create_sheet(title=sheet_name)

            # 写入表头行。
            worksheet.append(headers)

            # 遍历当前表记录。
            for row in rows:

                # 按表头顺序装配单元格值。
                worksheet.append([row.get(title, "") for title in headers])

        # 保存工作簿文件。
        workbook.save(output_path)

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)

    # 定义完整 URL 构建方法。
    def build_url(self, path):

        """
        将系统内相对路径转换为平台完整 URL。

        :param path: 系统内相对路径。
        :type path: str
        :return: 完整接口地址。
        :rtype: str
        """

        # 拼接系统路径与相对路径。
        return f"{self.base_url}{self.system_path}/{path.lstrip('/')}"
