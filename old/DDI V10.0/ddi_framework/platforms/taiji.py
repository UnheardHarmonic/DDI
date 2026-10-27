# -*- coding: utf-8 -*-
"""
四川太极大药房连锁有限公司流向查询系统协议适配器。

本模块通过传统 JSP 表单协议完成登录、流向查询、HTML 表格解析和本地 Excel 落地。

:return: 模块提供太极流向查询系统平台适配器。
:rtype: None
"""

# 导入 HTML 实体解码函数。
from html import unescape

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入日期时间模块。
from datetime import datetime

# 导入 URL 表单编码函数。
from urllib.parse import urlencode

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入 Excel 工作簿类。
from openpyxl import Workbook

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient


# 定义太极流向系统平台适配器。
class TaijiPlatform(BasePlatform):

    """
    四川太极大药房连锁有限公司流向查询系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 太极流向查询系统平台适配器实例。
    :rtype: TaijiPlatform
    """

    # 定义页面返回表头到标准字段的映射。
    STANDARD_FIELD_MAP = {
        "购进流向": [("业务日期", "日期"), ("供应商ID", "供应商id"), ("供应商", "供应商"), ("商品ID", "货品id"), ("品名", "品名"), ("单位", "单位"), ("规格", "规格"), ("批号ID", "批号id"), ("批号", "批号"), ("数量", "数量"), ("单价", "单价"), ("金额", "金额")],
        "纯销流向": [("业务日期", "日期"), ("门店ID", "门店id"), ("门店名称", "门店名"), ("商品ID", "货品id"), ("品名", "品名"), ("规格", "规格"), ("单位", "单位"), ("生产厂家", "产地"), ("流水ID", "流水id"), ("批号", "批号"), ("数量", "数量"), ("单价", "单价"), ("金额", "金额")],
        "配送流向": [("业务日期", "日期"), ("门店ID", "门店id"), ("门店名称", "门店名"), ("商品ID", "货品id"), ("品名", "品名"), ("规格", "规格"), ("单位", "单位"), ("生产厂家", "产地"), ("批号ID", "批号id"), ("批号", "批号"), ("数量", "数量"), ("单价", "单价"), ("金额", "金额")],
        "库存": [("商品ID", "货品id"), ("品名", "品名"), ("单位", "单位"), ("规格", "规格"), ("批号ID", "批号id"), ("批号", "批号"), ("库存数量", "数量")],
    }

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化太极流向查询系统协议适配器。

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

        # 保存流向系统登录页地址。
        self.login_page_url = account.get("登录页", "http://222.178.193.127:15002/inout_query/")

        # 保存流向系统根地址。
        self.base_url = account.get("接口根地址", self.login_page_url).rstrip("/")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", urljoin(f"{self.base_url}/", "Login.do"))

        # 保存可选货品 ID 过滤条件。
        self.goods_id = str(account.get("货品ID", "")).strip()

        # 保存 HTML 查询响应超时时间。
        self.query_timeout_seconds = int(account.get("查询超时秒", 300))

        # 初始化协议 HTTP 会话客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录完成状态。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        使用 JSP AJAX 登录接口建立会话。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("太极大药房流向系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页以初始化 JSESSIONID 会话。
        self.http.get(self.login_page_url, referer=self.base_url)

        # 构建登录请求地址。
        request_url = f"{self.login_api_url}?{urlencode({'username': self.account.get('账号', ''), 'password': self.account.get('密码', '')})}"

        # 构建登录请求头。
        headers = self.http.ajax_form_headers(self.login_page_url)

        # 发送空请求体的登录 POST 请求。
        result = self.http.request("POST", request_url, headers=headers, data=b"", timeout=60)

        # 解析登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 校验登录结果标识。
        if response_text != "1":

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：平台未返回成功标识")

        # 标记当前会话已完成登录。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("Cookie", len(list(self.http.cookie_jar)), "cyan")))

        # 返回登录结果摘要。
        return {"登录状态": "成功", "Cookie数量": len(list(self.http.cookie_jar))}

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录会话 Cookie。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存当前 HTTP 会话 Cookie。
        self.http.save_cookie_file(cookie_path)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义平台查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的原始业务记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始业务记录列表。
        :rtype: list[dict]
        """

        # 查询平台 HTML 表格数据。
        query_result = self.query_taiji_data(data_type, start_date, end_date)

        # 返回原始业务记录集合。
        return query_result["rows"]

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成本地 Excel 文件。

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

        # 查询平台 HTML 表格数据。
        query_result = self.query_taiji_data(data_type, start_date, end_date)

        # 解析默认输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 构建 Excel 输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入标准字段与原始字段 Excel。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], data_type, output_path)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义平台导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        使用协议查询结果生成 Excel 文件。

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

        # 调用本地 Excel 落地流程。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义主查询方法。
    def query_taiji_data(self, data_type, start_date, end_date):

        """
        提交 JSP 表单并解析返回的 HTML 数据表。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果、原始表头和日期范围。
        :rtype: dict
        """

        # 校验数据类型是否已配置页面映射。
        self.validate_data_type(data_type)

        # 确保当前 HTTP 会话已经登录。
        self.ensure_login()

        # 解析当前请求的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(data_type, start_date, end_date)

        # 读取当前数据类型页面配置。
        page_config = self.account.get("页面映射", {}).get(data_type, {})

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, resolved_start_date, resolved_end_date)

        # 访问查询页面以保持页面会话上下文。
        form_url = self.build_page_url(page_config["查询页"])

        # 发送查询页面 GET 请求。
        self.http.get(form_url, referer=self.base_url)

        # 构建查询表单字段。
        payload = self.build_query_payload(page_config, resolved_start_date, resolved_end_date)

        # 构建数据详情页面地址。
        detail_url = self.build_page_url(page_config["详情页"])

        # 构建浏览器表单请求头。
        headers = self.http.browser_headers(form_url)

        # 写入表单内容类型。
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        # 写入站点来源地址。
        headers["Origin"] = self.http.base_url

        # 编码查询表单请求体。
        request_data = urlencode(payload).encode("utf-8")

        # 发送 HTML 表格查询请求。
        result = self.http.request("POST", detail_url, headers=headers, data=request_data, timeout=self.query_timeout_seconds)

        # 解码查询响应 HTML。
        html_text = result.body.decode("utf-8", errors="replace")

        # 校验查询响应未回退到登录页。
        self.validate_query_response(data_type, html_text)

        # 解析响应 HTML 中的数据表格。
        headers_row, rows = self.parse_result_table(html_text)

        # 校验流向业务日期范围。
        self.validate_result_date_range(data_type, rows, resolved_start_date, resolved_end_date)

        # 打印查询结果摘要。
        self.ph.success(self.ph.join(self.ph.kv("查询页面", page_config["详情页"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers_row), "cyan")))

        # 返回查询结果字典。
        return {"headers": headers_row, "rows": rows, "start_date": resolved_start_date, "end_date": resolved_end_date}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型是否配置对应 JSP 页面。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断当前数据类型是否存在页面映射。
        if data_type in self.account.get("页面映射", {}):

            # 已接入数据类型时直接返回。
            return

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

    # 定义登录状态确保方法。
    def ensure_login(self):

        """
        确保当前协议会话已完成登录。

        :return: None。
        :rtype: None
        """

        # 判断当前会话是否已登录。
        if self.logged_in:

            # 已登录时直接返回。
            return

        # 执行平台登录流程。
        self.login()

    # 定义查询日期解析方法。
    def resolve_query_dates(self, data_type, start_date, end_date):

        """
        解析数据类型查询需要的日期范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 解析后的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 读取当前本地日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 判断当前数据类型是否为库存。
        if data_type == "库存":

            # 返回库存导出日期。
            return today_text, today_text

        # 解析流向查询开始日期。
        resolved_start_date = start_date or today_text

        # 解析流向查询结束日期。
        resolved_end_date = end_date or resolved_start_date

        # 校验流向日期范围。
        self.validate_query_range(resolved_start_date, resolved_end_date)

        # 返回流向日期范围。
        return resolved_start_date, resolved_end_date

    # 定义日期范围校验方法。
    def validate_query_range(self, start_date, end_date):

        """
        校验流向查询日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 解析开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断日期范围顺序是否有效。
        if start_value <= end_value:

            # 有效日期范围时直接返回。
            return

        # 抛出开始日期晚于结束日期异常。
        raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{start_date} > {end_date}")

    # 定义查询日志分隔线打印方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印数据类型查询阶段分隔线。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印标准查询阶段日志。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

    # 定义页面地址构建方法。
    def build_page_url(self, page_path):

        """
        拼接当前系统页面地址。

        :param page_path: 页面相对路径。
        :type page_path: str
        :return: 页面完整地址。
        :rtype: str
        """

        # 返回相对页面的完整地址。
        return urljoin(f"{self.base_url}/", str(page_path).lstrip("/"))

    # 定义查询请求体构建方法。
    def build_query_payload(self, page_config, start_date, end_date):

        """
        构建 JSP 详情页表单字段。

        :param page_config: 数据类型页面配置。
        :type page_config: dict
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 表单字段字典。
        :rtype: dict
        """

        # 初始化货品和查询动作字段。
        payload = {"goodsid": self.goods_id, "method": "deletebank"}

        # 判断当前页面是否要求日期范围。
        if page_config.get("需要日期", True):

            # 写入开始日期字段。
            payload["startdate"] = start_date

            # 写入结束日期字段。
            payload["enddate"] = end_date

        # 返回查询表单字段。
        return payload

    # 定义查询响应校验方法。
    def validate_query_response(self, data_type, html_text):

        """
        校验详情页返回的系统状态。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param html_text: 查询响应 HTML。
        :type html_text: str
        :return: None。
        :rtype: None
        """

        # 判断响应是否回退到登录页面。
        if "id=\"username\"" in html_text or "function login()" in html_text:

            # 抛出登录态失效异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询时登录态失效")

        # 判断响应是否包含数据表格。
        if "<table" in html_text.lower():

            # 返回有效查询响应。
            return

        # 抛出无效查询页面异常。
        raise RuntimeError(f"{self.company_name} {data_type} 查询未返回有效数据表格")

    # 定义结果表格解析方法。
    def parse_result_table(self, html_text):

        """
        从详情页解析表头和原始数据行。

        :param html_text: 查询响应 HTML。
        :type html_text: str
        :return: 原始表头和记录字典列表。
        :rtype: tuple[list[str], list[dict]]
        """

        # 提取页面中的 HTML 表格片段。
        table_fragments = re.findall(r"<table\b[^>]*>(.*?)</table>", html_text, flags=re.IGNORECASE | re.DOTALL)

        # 判断页面是否返回表格。
        if not table_fragments:

            # 抛出表格缺失异常。
            raise RuntimeError(f"{self.company_name} 查询页面未返回 HTML 表格")

        # 解析第一个数据表格。
        table_rows = self.parse_html_rows(table_fragments[0])

        # 判断数据表格是否包含表头。
        if not table_rows:

            # 抛出表头缺失异常。
            raise RuntimeError(f"{self.company_name} 查询页面未返回结果表头")

        # 标准化原始表头名称。
        headers = self.normalize_headers(table_rows[0])

        # 初始化原始记录集合。
        rows = []

        # 遍历表头之后的页面数据行。
        for raw_row in table_rows[1:]:

            # 判断当前行是否包含有效内容。
            if not any(cell.strip() for cell in raw_row):

                # 空行直接跳过。
                continue

            # 按原始表头构建当前记录。
            row = {header: raw_row[index] if index < len(raw_row) else "" for index, header in enumerate(headers)}

            # 保存当前原始记录。
            rows.append(row)

        # 返回原始表头和记录集合。
        return headers, rows

    # 定义 HTML 行解析方法。
    def parse_html_rows(self, table_html):

        """
        解析单个 HTML 表格中的文本单元格。

        :param table_html: 表格 HTML 片段。
        :type table_html: str
        :return: 表格行和单元格文本集合。
        :rtype: list[list[str]]
        """

        # 初始化解析后的表格行集合。
        rows = []

        # 遍历表格中的 HTML 行片段。
        for row_html in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table_html, flags=re.IGNORECASE | re.DOTALL):

            # 提取当前行的单元格片段。
            cell_fragments = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL)

            # 判断当前行是否没有单元格。
            if not cell_fragments:

                # 无单元格行直接跳过。
                continue

            # 清洗当前行的文本单元格。
            row = [self.strip_html(cell_html) for cell_html in cell_fragments]

            # 保存当前表格行。
            rows.append(row)

        # 返回解析后的表格行集合。
        return rows

    # 定义 HTML 文本清洗方法。
    def strip_html(self, html_fragment):

        """
        清洗 HTML 单元格中的标签与实体编码。

        :param html_fragment: 单元格 HTML 片段。
        :type html_fragment: str
        :return: 清洗后的文本内容。
        :rtype: str
        """

        # 将换行标签转换为文本换行。
        text = re.sub(r"<br\s*/?>", "\n", str(html_fragment or ""), flags=re.IGNORECASE)

        # 移除其余 HTML 标签。
        text = re.sub(r"<[^>]+>", "", text)

        # 解码 HTML 实体并折叠空白字符。
        return re.sub(r"\s+", " ", unescape(text).replace("\xa0", " ")).strip()

    # 定义表头标准化方法。
    def normalize_headers(self, raw_headers):

        """
        标准化页面表头并处理重名字段。

        :param raw_headers: 页面原始表头列表。
        :type raw_headers: list[str]
        :return: 标准化后的原始表头列表。
        :rtype: list[str]
        """

        # 初始化表头出现次数字典。
        name_counts = {}

        # 初始化标准化表头集合。
        normalized_headers = []

        # 遍历页面原始表头。
        for index, raw_header in enumerate(raw_headers, start=1):

            # 解析当前表头名称。
            field_name = str(raw_header or "").strip() or f"字段{index}"

            # 递增当前表头出现次数。
            name_counts[field_name] = name_counts.get(field_name, 0) + 1

            # 判断当前表头是否首次出现。
            if name_counts[field_name] == 1:

                # 保存首次出现的表头。
                normalized_headers.append(field_name)

                # 进入下一项表头。
                continue

            # 保存带序号的重名表头。
            normalized_headers.append(f"{field_name}_{name_counts[field_name]}")

        # 返回标准化表头集合。
        return normalized_headers

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向结果的业务日期未超出请求范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果记录。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 判断当前数据类型是否为库存。
        if data_type == "库存":

            # 库存为当前快照时直接返回。
            return

        # 初始化返回日期集合。
        business_dates = []

        # 遍历查询结果记录。
        for row in rows:

            # 提取当前记录中的日期文本。
            date_text = str(row.get("日期", ""))

            # 匹配当前记录中的日期部分。
            matched_date = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_text)

            # 判断当前记录是否包含可解析日期。
            if not matched_date:

                # 不含日期的记录直接跳过。
                continue

            # 标准化当前业务日期。
            normalized_date = "-".join(part.zfill(2) if index else part for index, part in enumerate(matched_date.groups()))

            # 保存当前业务日期。
            business_dates.append(normalized_date)

        # 判断查询结果是否没有可解析日期。
        if not business_dates:

            # 无日期记录时直接返回。
            return

        # 判断结果最小日期是否早于请求开始日期。
        if min(business_dates) < start_date:

            # 抛出结果日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期早于查询开始日期：{min(business_dates)} < {start_date}")

        # 判断结果最大日期是否晚于请求结束日期。
        if max(business_dates) > end_date:

            # 抛出结果日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期晚于查询结束日期：{max(business_dates)} > {end_date}")

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, raw_headers, data_type, output_path):

        """
        写入标准字段前置且完整保留原始字段的 Excel。

        :param rows: 原始业务记录列表。
        :type rows: list[dict]
        :param raw_headers: 页面原始表头列表。
        :type raw_headers: list[str]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param output_path: Excel 输出路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 读取当前数据类型标准字段映射。
        standard_fields = self.STANDARD_FIELD_MAP.get(data_type, [])

        # 构建原始字段 Excel 表头。
        raw_excel_headers = [f"原始_{header}" for header in raw_headers]

        # 构建完整 Excel 表头。
        excel_headers = [field_name for field_name, _ in standard_fields] + raw_excel_headers

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type[:31]

        # 写入完整 Excel 表头。
        worksheet.append(excel_headers)

        # 遍历原始业务记录。
        for row in rows:

            # 构建标准字段单元格值。
            standard_values = [row.get(source_field, "") for _, source_field in standard_fields]

            # 构建原始字段单元格值。
            raw_values = [row.get(header, "") for header in raw_headers]

            # 写入标准字段和原始字段。
            worksheet.append(standard_values + raw_values)

        # 应用项目统一 Excel 样式。
        apply_standard_excel_style(worksheet)

        # 保存 Excel 工作簿。
        workbook.save(output_path)
