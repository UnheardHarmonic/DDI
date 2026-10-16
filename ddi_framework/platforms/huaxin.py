# -*- coding: utf-8 -*-
"""
四川华信药业有限责任公司 FineReport 协议适配器。

本模块通过 FineDecision 登录、FineReport 报表会话、参数提交和分页内容接口完成原始报表数据的协议查询与 Excel 落地。

:return: 模块提供四川华信药业 FineReport 平台适配器。
:rtype: None
"""

# 导入 Base64 编解码模块。
import base64

# 导入 HTML 实体解码函数。
from html import unescape

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入日期时间模块。
from datetime import datetime

# 导入 URL 查询编码函数。
from urllib.parse import quote

# 导入 URL 查询编码函数。
from urllib.parse import urlencode

# 导入 PKCS7 填充器。

# 导入 AES 分组密码对象。

# 导入 AES 算法配置。

# 导入 ECB 分组模式配置。

# 导入 Excel 工作簿类。
from openpyxl import Workbook

# 导入平台适配器基类。
# 导入通用 AES-ECB 加密函数。
from ddi_framework.reverse_utils import aes_ecb_pkcs7_base64

from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient


# 定义数据类型与 FineReport 模板映射。
REPORT_TEMPLATES = {
    "购进流向": "xl/供应商报表/10001商品采购报表.cpt",
    "库存": "xl/供应商报表/10002商品库存报表.cpt",
    "配送流向": "xl/供应商报表/10003门店商品销售明细报表.cpt",
}


# 定义标准字段与 FineReport 原始字段映射。
STANDARD_FIELD_MAP = {
    "购进流向": [("日期", "购进日期"), ("仓库", "仓库"), ("货品id", "货号"), ("品名", "名称"), ("规格", "规格"), ("生产厂家", "厂家"), ("单位", "单位"), ("数量", "数量"), ("供应商", "供应商"), ("供应商编码", "供应商编码"), ("批号", "批号"), ("有效期", "效期"), ("单价", "单价"), ("金额", "金额")],
    "库存": [("库存日期", "库存日期"), ("仓库", "仓库名称"), ("货品id", "货号"), ("品名", "名称"), ("规格", "规格"), ("生产厂家", "厂家"), ("单位", "单位"), ("库区", "库区"), ("库存数量", "库存数量"), ("批号", "批号"), ("有效期", "效期"), ("供应商", "供应商"), ("供应商编码", "供应商编码"), ("库存金额", "库存金额"), ("单价", "单价")],
    "配送流向": [("日期", "日期"), ("门店编码", "门店编码"), ("门店名称", "门店名称"), ("门店缩写", "门店缩写"), ("货品id", "货号"), ("品名", "名称"), ("规格", "规格"), ("生产厂家", "厂家"), ("单位", "单位"), ("数量", "数量"), ("批号", "批号"), ("有效期", "效期"), ("单价", "单价"), ("金额", "金额")],
}


# 定义四川华信 FineReport 平台适配器。
class HuaxinPlatform(BasePlatform):

    """
    四川华信药业有限责任公司 FineReport 协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 四川华信药业协议适配器实例。
    :rtype: HuaxinPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化四川华信药业 FineReport 协议适配器。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param account: 商业账号配置。
        :type account: dict
        :param printer: 日志打印器。
        :type printer: PrintHandler | None
        :return: None。
        :rtype: None
        """

        # 调用平台基类初始化逻辑。
        super().__init__(company_name, account, printer=printer)

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 保存报表服务器根地址。
        self.base_url = account.get("接口根地址", "https://college.scxinglin.com/xl/ReportServer").rstrip("/")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.base_url}/login")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", self.login_page_url)

        # 保存报表内容查询超时秒数。
        self.query_timeout_seconds = int(account.get("查询超时秒", 180))

        # 初始化协议 HTTP 客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化 FineDecision 访问令牌。
        self.access_token = ""

        # 初始化当前登录状态。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        使用 FineDecision AES 登录协议建立访问令牌。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("四川华信 FineReport 登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页以读取动态 AES 密钥和建立站点 Cookie。
        login_page = self.http.get(self.login_page_url)

        # 解码登录页 HTML 文本。
        login_html = login_page.body.decode("utf-8", errors="replace")

        # 提取 FineDecision 前端加密配置。
        cipher_config = self.extract_cipher_config(login_html)

        # 使用动态前端密钥加密登录密码。
        encrypted_password = self.encrypt_aes_ecb_pkcs7_base64(str(self.account.get("密码", "")), cipher_config["frontSeed"])

        # 构建 FineDecision 登录 JSON 请求体。
        payload = {"username": str(self.account.get("账号", "")), "password": encrypted_password, "validity": -1, "sliderToken": "", "origin": "", "encrypted": True}

        # 构建 JSON 登录请求头。
        headers = self.build_json_headers(self.login_page_url)

        # 编码登录请求体。
        request_data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 提交 FineDecision 登录请求。
        result = self.http.request("POST", self.login_api_url, headers=headers, data=request_data, timeout=60)

        # 解析登录响应数据。
        response_data = self.decode_json_response(result)

        # 读取登录访问令牌。
        access_token = str(response_data.get("data", {}).get("accessToken", ""))

        # 校验登录响应包含访问令牌。
        if not access_token:

            # 抛出脱敏后的登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{response_data.get('errorMsg') or response_data.get('message') or '平台未返回访问令牌'}")

        # 保存当前会话访问令牌。
        self.access_token = access_token

        # 标记当前会话已完成登录。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("Cookie", len(list(self.http.cookie_jar)), "cyan")))

        # 返回不含令牌的登录摘要。
        return {"登录状态": "成功", "Cookie数量": len(list(self.http.cookie_jar))}


    # 定义原始数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的原始报表记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 查询 FineReport 原始数据。
        query_result = self.query_huaxin_data(data_type, start_date, end_date)

        # 返回原始记录列表。
        return query_result["rows"]

    # 定义 Excel 查询落地方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成标准 Excel 文件。

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

        # 查询 FineReport 原始数据。
        query_result = self.query_huaxin_data(data_type, start_date, end_date)

        # 解析默认输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建标准输出文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 构建完整 Excel 输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入标准字段与全部原始字段。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], data_type, output_path)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path


    # 定义 FineReport 主查询方法。
    def query_huaxin_data(self, data_type, start_date, end_date):

        """
        初始化 FineReport 会话、提交参数并分页解析报表内容。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果、原始表头和日期范围。
        :rtype: dict
        """

        # 校验数据类型已配置报表模板。
        self.validate_data_type(data_type)

        # 确保当前 HTTP 会话已登录。
        self.ensure_login()

        # 解析当前数据类型的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(data_type, start_date, end_date)

        # 校验流向报表的单月参数约束。
        self.validate_query_range(data_type, resolved_start_date, resolved_end_date)

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, resolved_start_date, resolved_end_date)

        # 创建当前报表模板的会话上下文。
        report_context = self.initialize_report_session(data_type)

        # 构建当前报表参数字段。
        report_parameters = self.build_report_parameters(data_type, resolved_start_date, resolved_end_date)

        # 提交当前报表参数字段。
        self.submit_report_parameters(report_context, report_parameters)

        # 通知 FineReport 当前浏览器视口信息。
        self.collect_preview_info(report_context)

        # 分页获取并解析当前报表内容。
        headers, rows = self.fetch_all_report_pages(report_context)

        # 校验流向结果日期范围。
        self.validate_result_date_range(data_type, rows, resolved_start_date, resolved_end_date)

        # 打印查询结果摘要。
        self.ph.success(self.ph.join(self.ph.kv("报表模板", REPORT_TEMPLATES[data_type], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果字典。
        return {"headers": headers, "rows": rows, "start_date": resolved_start_date, "end_date": resolved_end_date}

    # 定义报表会话初始化方法。
    def initialize_report_session(self, data_type):

        """
        打开 FineReport 模板并提取会话编号。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表会话上下文。
        :rtype: dict
        """

        # 读取当前数据类型的报表模板路径。
        template_path = REPORT_TEMPLATES[data_type]

        # 以保留斜杠的形式编码模板路径。
        encoded_template = quote(template_path, safe="/")

        # 构建报表入口地址。
        entry_url = f"{self.base_url}/view/report?viewlet={encoded_template}"

        # 构建报表入口请求头。
        headers = self.build_html_headers(self.login_page_url)

        # 写入 FineDecision Bearer 授权头。
        self.apply_authorization_header(headers)

        # 访问 FineReport 模板入口。
        result = self.http.request("GET", entry_url, headers=headers, timeout=self.query_timeout_seconds)

        # 解码报表入口 HTML。
        entry_html = result.body.decode("utf-8", errors="replace")

        # 从入口页面提取报表会话编号。
        session_id = self.extract_report_session_id(entry_html)

        # 打印报表会话初始化日志。
        self.ph.info(self.ph.join(self.ph.kv("报表会话", session_id, "cyan"), self.ph.kv("报表", template_path, "cyan")))

        # 返回报表会话上下文。
        return {"entry_url": entry_url, "session_id": session_id, "data_type": data_type}

    # 定义报表参数构建方法。
    def build_report_parameters(self, data_type, start_date, end_date):

        """
        构建页面实际提交的 FineReport 参数字段。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: FineReport 参数字典。
        :rtype: dict
        """

        # 解析查询开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析查询结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断当前报表是否为购进流向。
        if data_type == "购进流向":

            # 返回购进报表的月份参数与商品筛选参数。
            return {"LABEL0": "[5f00][59cb][6708][4efd][ff1a]", "SYM": int(start_value.strftime("%Y%m")), "LABEL1": "[5546][54c1][540d][79f0][ff1a]", "PRODUCT": "", "LABEL2": "[7ed3][675f][6708][4efd][ff1a]", "EYM": int(end_value.strftime("%Y%m"))}

        # 判断当前报表是否为库存。
        if data_type == "库存":

            # 返回库存报表的商品筛选参数。
            return {"LABEL1_C_C": "[5546][54c1][540d][79f0][ff1a]", "PRODUCT": ""}

        # 返回门店销售报表的月份和精确日期参数。
        return {"LABEL0": "[67e5][8be2][6708][4efd][ff1a]", "YM": int(start_value.strftime("%Y%m")), "LABEL0_C_C_C": "[5f00][59cb][65e5][671f][ff1a]", "SDT": start_value.strftime("%Y%m%d"), "LABEL0_C_C_C_C": "[7ed3][675f][65e5][671f][ff1a]", "EDT": end_value.strftime("%Y%m%d")}

    # 定义报表参数提交方法。
    def submit_report_parameters(self, report_context, parameters):

        """
        提交 FineReport 参数面板字段。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :param parameters: FineReport 参数字典。
        :type parameters: dict
        :return: 参数提交响应数据。
        :rtype: dict
        """

        # 构建 FineReport 参数提交接口地址。
        url = f"{self.base_url}/view/report?op=fr_dialog&cmd=parameters_d"

        # 编码参数提交表单体。
        request_data = urlencode({"__parameters__": json.dumps(parameters, ensure_ascii=False, separators=(",", ":")), "_": str(int(time.time() * 1000))}).encode("utf-8")

        # 构建带会话编号的表单请求头。
        headers = self.build_form_headers(report_context["entry_url"], report_context["session_id"])

        # 提交 FineReport 参数请求。
        result = self.http.request("POST", url, headers=headers, data=request_data, timeout=self.query_timeout_seconds)

        # 解析参数提交响应数据。
        response_data = self.decode_json_response(result)

        # 校验参数提交状态。
        if str(response_data.get("status", "success")).lower() not in ("success", "true"):

            # 抛出报表参数提交异常。
            raise RuntimeError(f"{self.company_name} 报表参数提交失败：{response_data}")

        # 打印参数提交成功日志。
        self.ph.info(self.ph.kv("报表参数", "提交成功", "green"))

        # 返回参数提交响应数据。
        return response_data

    # 定义预览信息提交方法。
    def collect_preview_info(self, report_context):

        """
        提交 FineReport 预览视口信息以完成报表上下文初始化。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :return: None。
        :rtype: None
        """

        # 构建预览信息收集接口地址。
        url = f"{self.base_url}/preview/info/collect"

        # 编码浏览器预览信息表单体。
        request_data = urlencode({"webInfo": json.dumps({"webResolution": "1280*745", "fullScreen": 1}, separators=(",", ":"))}).encode("utf-8")

        # 构建带会话编号的表单请求头。
        headers = self.build_form_headers(report_context["entry_url"], report_context["session_id"])

        # 提交浏览器预览信息。
        self.http.request("POST", url, headers=headers, data=request_data, timeout=60)

    # 定义全部报表页面读取方法。
    def fetch_all_report_pages(self, report_context):

        """
        分页读取 FineReport 内容并合并原始记录。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :return: 原始表头与全部记录。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化已解析原始表头。
        headers = []

        # 初始化全部原始记录集合。
        rows = []

        # 初始化报表总页数。
        total_pages = 1

        # 初始化当前报表页码。
        page_number = 1

        # 循环读取所有报表页。
        while page_number <= total_pages:

            # 获取当前页 FineReport 内容响应。
            page_data = self.fetch_report_page(report_context, page_number)

            # 解析当前页 HTML 文本。
            page_headers, page_rows = self.parse_report_content(page_data.get("html", ""))

            # 判断当前页是否首次返回表头。
            if page_headers and not headers:

                # 保存当前报表原始表头。
                headers = page_headers

            # 合并当前页原始记录。
            rows.extend(page_rows)

            # 解析当前响应中的报表总页数。
            total_pages = self.extract_total_pages(page_data.get("html", ""), total_pages)

            # 打印当前分页解析日志。
            self.ph.info(self.ph.join(self.ph.kv("报表分页", f"{page_number}/{total_pages}", "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan")))

            # 进入下一页。
            page_number += 1

        # 返回原始表头与全部原始记录。
        return headers, rows

    # 定义单页报表读取方法。
    def fetch_report_page(self, report_context, page_number):

        """
        读取指定页码的 FineReport 页面内容。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :param page_number: 报表页码。
        :type page_number: int
        :return: FineReport 页面响应数据。
        :rtype: dict
        """

        # 构建报表内容查询参数。
        query = {"_": int(time.time() * 1000), "__boxModel__": "true", "op": "page_content", "pn": page_number, "__webpage__": "true", "_paperWidth": 699, "_paperHeight": 745, "__fit__": "false"}

        # 构建报表内容查询接口地址。
        url = f"{self.base_url}/view/report?{urlencode(query)}"

        # 构建带会话编号的 AJAX 请求头。
        headers = self.build_ajax_headers(report_context["entry_url"], report_context["session_id"])

        # 请求当前 FineReport 页面内容。
        result = self.http.request("GET", url, headers=headers, timeout=self.query_timeout_seconds)

        # 解析并返回当前页面 JSON 数据。
        return self.decode_json_response(result)

    # 定义 FineReport 内容解析方法。
    def parse_report_content(self, html_text):

        """
        从 FineReport 网格 HTML 提取完整原始字段和数据记录。

        :param html_text: FineReport 页面 HTML 文本。
        :type html_text: str
        :return: 原始表头与原始记录。
        :rtype: tuple[list[str], list[dict]]
        """

        # 按 FineReport 单元格坐标提取表格矩阵。
        matrix = self.extract_cell_matrix(html_text)

        # 识别包含日期和名称字段的表头行。
        header_row_number = self.find_header_row(matrix)

        # 判断响应是否缺少可识别表头。
        if header_row_number is None:

            # 抛出报表表头缺失异常。
            raise RuntimeError(f"{self.company_name} FineReport 响应未识别到原始表头")

        # 读取表头行原始单元格。
        header_cells = matrix[header_row_number]

        # 按列索引读取原始表头文本。
        raw_headers = [header_cells[column_index] for column_index in sorted(header_cells)]

        # 标准化原始表头并处理重复名称。
        headers = self.normalize_headers(raw_headers)

        # 保存表头列索引顺序。
        column_indexes = sorted(header_cells)

        # 初始化当前页原始记录集合。
        rows = []

        # 遍历表头之后的 FineReport 行。
        for row_number in sorted(matrix):

            # 跳过表头及其之前的行。
            if row_number <= header_row_number:

                # 继续读取下一行。
                continue

            # 读取当前行单元格字典。
            current_cells = matrix[row_number]

            # 读取当前行文本值。
            raw_values = [current_cells.get(column_index, "") for column_index in column_indexes]

            # 合并当前行文本用于汇总行判断。
            row_text = " ".join(value for value in raw_values if value).strip()

            # 跳过空白、合计和页脚行。
            if not row_text or "合计" in row_text or "Powered by" in row_text:

                # 继续读取下一行。
                continue

            # 跳过不满足有效字段数量的数据行。
            if sum(1 for value in raw_values if value) < 2:

                # 继续读取下一行。
                continue

            # 按完整原始表头组装当前记录。
            row = {header: raw_values[index] if index < len(raw_values) else "" for index, header in enumerate(headers)}

            # 保存当前原始记录。
            rows.append(row)

        # 返回原始表头和当前页原始记录。
        return headers, rows

    # 定义 FineReport 单元格矩阵提取方法。
    def extract_cell_matrix(self, html_text):

        """
        根据 FineReport 单元格 ID 提取带隐藏字段的二维矩阵。

        :param html_text: FineReport 页面 HTML 文本。
        :type html_text: str
        :return: 行号到列号文本的矩阵。
        :rtype: dict[int, dict[int, str]]
        """

        # 初始化 FineReport 行列矩阵。
        matrix = {}

        # 还原 FineReport 单元格 ID 中的 HTML 连字符实体。
        normalized_html = str(html_text or "").replace("&#45;", "-")

        # 定义带坐标单元格的匹配表达式。
        pattern = r"<td\b(?=[^>]*\bid\s*=\s*['\"]([A-Z]+)(\d+)-0-\d+['\"])[^>]*>(.*?)</td>"

        # 遍历 FineReport 响应中的坐标单元格。
        for column_name, row_text, cell_html in re.findall(pattern, normalized_html, flags=re.IGNORECASE | re.DOTALL):

            # 将 Excel 列名转换为数字列索引。
            column_index = self.column_name_to_index(column_name)

            # 解析当前单元格行号。
            row_number = int(row_text)

            # 清洗当前单元格完整文本。
            cell_text = self.strip_html(cell_html)

            # 初始化当前行单元格字典。
            matrix.setdefault(row_number, {})

            # 保留同一坐标下较完整的单元格文本。
            if len(cell_text) >= len(matrix[row_number].get(column_index, "")):

                # 写入当前单元格文本。
                matrix[row_number][column_index] = cell_text

        # 返回 FineReport 行列矩阵。
        return matrix

    # 定义表头行识别方法。
    def find_header_row(self, matrix):

        """
        在 FineReport 矩阵中定位原始业务表头所在行。

        :param matrix: 行号到列号文本的矩阵。
        :type matrix: dict[int, dict[int, str]]
        :return: 表头行号。
        :rtype: int | None
        """

        # 初始化候选表头行号。
        selected_row_number = None

        # 初始化候选表头有效字段数量。
        selected_cell_count = -1

        # 遍历 FineReport 所有行。
        for row_number, cells in matrix.items():

            # 读取当前行非空文本。
            values = [value for value in cells.values() if value]

            # 合并当前行文本用于表头关键词识别。
            combined_text = " ".join(values)

            # 判断当前行是否同时包含日期和名称表头语义。
            if "日期" not in combined_text or "名称" not in combined_text:

                # 继续检查下一行。
                continue

            # 判断当前行是否具有更多有效字段。
            if len(values) <= selected_cell_count:

                # 继续检查下一行。
                continue

            # 保存当前最完整的表头行号。
            selected_row_number = row_number

            # 保存当前表头有效字段数量。
            selected_cell_count = len(values)

        # 返回表头行号。
        return selected_row_number

    # 定义 FineReport 列名转换方法。
    def column_name_to_index(self, column_name):

        """
        将 FineReport Excel 风格列名转换为零基列索引。

        :param column_name: Excel 风格列名。
        :type column_name: str
        :return: 零基列索引。
        :rtype: int
        """

        # 初始化列索引数值。
        column_index = 0

        # 遍历列名中的每个字母。
        for character in str(column_name).upper():

            # 累积当前 Excel 列名对应的数值。
            column_index = column_index * 26 + ord(character) - ord("A") + 1

        # 返回零基列索引。
        return column_index - 1

    # 定义 FineReport HTML 文本清洗方法。
    def strip_html(self, html_fragment):

        """
        清洗 FineReport 单元格内的标签、换行和 HTML 实体。

        :param html_fragment: 单元格 HTML 片段。
        :type html_fragment: str
        :return: 清洗后的单元格文本。
        :rtype: str
        """

        # 将换行标签替换为空格。
        text = re.sub(r"<br\s*/?>", " ", str(html_fragment or ""), flags=re.IGNORECASE)

        # 移除其余 HTML 标签。
        text = re.sub(r"<[^>]+>", "", text)

        # 解码实体并折叠空白字符。
        return re.sub(r"\s+", " ", unescape(text).replace("\xa0", " ")).strip()

    # 定义原始表头标准化方法。
    def normalize_headers(self, raw_headers):

        """
        标准化原始表头并为重复字段增加序号。

        :param raw_headers: 原始表头列表。
        :type raw_headers: list[str]
        :return: 标准化后表头列表。
        :rtype: list[str]
        """

        # 初始化表头出现次数字典。
        name_counts = {}

        # 初始化标准化表头集合。
        normalized_headers = []

        # 遍历原始表头文本。
        for index, raw_header in enumerate(raw_headers, start=1):

            # 解析当前原始表头名称。
            field_name = str(raw_header or "").strip() or f"字段{index}"

            # 累积当前表头出现次数。
            name_counts[field_name] = name_counts.get(field_name, 0) + 1

            # 判断当前表头是否首次出现。
            if name_counts[field_name] == 1:

                # 保存首次出现的表头名称。
                normalized_headers.append(field_name)

                # 继续处理下一项表头。
                continue

            # 保存带序号的重名表头名称。
            normalized_headers.append(f"{field_name}_{name_counts[field_name]}")

        # 返回标准化表头集合。
        return normalized_headers

    # 定义报表总页数提取方法。
    def extract_total_pages(self, html_text, default_pages):

        """
        从 FineReport 脚本中提取当前报表总页数。

        :param html_text: FineReport 页面 HTML 文本。
        :type html_text: str
        :param default_pages: 默认页数。
        :type default_pages: int
        :return: 报表总页数。
        :rtype: int
        """

        # 匹配 FineReport 总页数赋值。
        matched_pages = re.search(r"reportTotalPage\s*=\s*(\d+)", str(html_text or ""))

        # 判断响应中是否包含总页数。
        if not matched_pages:

            # 返回调用方默认页数。
            return default_pages

        # 返回至少为一页的总页数。
        return max(1, int(matched_pages.group(1)))

    # 定义报表会话编号提取方法。
    def extract_report_session_id(self, html_text):

        """
        从 FineReport 模板入口页面提取会话编号。

        :param html_text: FineReport 入口 HTML 文本。
        :type html_text: str
        :return: FineReport 会话编号。
        :rtype: str
        """

        # 匹配 FineReport 会话注册调用。
        session_match = re.search(r"FR\.SessionMgr\.register\('([^']+)'", str(html_text or ""))

        # 判断入口页面是否包含会话编号。
        if session_match:

            # 返回当前会话编号。
            return session_match.group(1)

        # 抛出报表会话缺失异常。
        raise RuntimeError(f"{self.company_name} 报表入口未返回 sessionID")

    # 定义 FineDecision 加密配置提取方法。
    def extract_cipher_config(self, login_html):

        """
        从 FineDecision 登录页提取动态 AES 前端密钥。

        :param login_html: 登录页 HTML 文本。
        :type login_html: str
        :return: FineDecision 加密配置。
        :rtype: dict
        """

        # 匹配 JSON.parse 形式的前端系统配置。
        config_match = re.search(r"Dec\.system\s*=\s*JSON\.parse\('(.+?)'\);", str(login_html or ""), flags=re.DOTALL)

        # 判断登录页是否包含系统配置。
        if not config_match:

            # 抛出前端加密配置缺失异常。
            raise RuntimeError(f"{self.company_name} 登录页缺少 FineDecision 加密配置")

        # 读取 JavaScript 字符串内的 JSON 文本。
        config_text = config_match.group(1)

        # 将 JavaScript 转义文本还原为 JSON 文本。
        config_text = config_text.replace("\\/", "/").replace('\\"', '"')

        # 解析 FineDecision 系统配置。
        config_data = json.loads(config_text)

        # 校验前端 AES 密钥存在。
        if not config_data.get("frontSeed"):

            # 抛出前端 AES 密钥缺失异常。
            raise RuntimeError(f"{self.company_name} 登录页缺少 frontSeed")

        # 返回 FineDecision 系统配置。
        return config_data

    # 定义 AES 密码加密方法。
    def encrypt_aes_ecb_pkcs7_base64(self, plain_text, secret_key):

        """
        使用 FineDecision AES-ECB-PKCS7 规则加密登录密码。

        :param plain_text: 登录明文密码。
        :type plain_text: str
        :param secret_key: 动态 AES 密钥。
        :type secret_key: str
        :return: Base64 密文。
        :rtype: str
        """

        # 调用通用 AES-ECB-PKCS7 加密能力。
        return aes_ecb_pkcs7_base64(plain_text, secret_key)


    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型是否已配置 FineReport 模板。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否存在报表模板。
        if data_type in REPORT_TEMPLATES:

            # 已接入数据类型时直接返回。
            return

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

    # 定义查询日期解析方法。
    def resolve_query_dates(self, data_type, start_date, end_date):

        """
        解析流向日期范围或库存快照日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 开始日期与结束日期。
        :rtype: tuple[str, str]
        """

        # 读取当前本地日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 判断当前数据类型是否为库存。
        if data_type == "库存":

            # 返回库存导出当天日期。
            return today_text, today_text

        # 返回流向使用的查询日期范围。
        return start_date or today_text, end_date or start_date or today_text

    # 定义查询日期范围校验方法。
    def validate_query_range(self, data_type, start_date, end_date):

        """
        校验 FineReport 流向日期顺序和单月参数限制。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 判断库存报表是否无需日期范围校验。
        if data_type == "库存":

            # 库存使用平台当前快照时直接返回。
            return

        # 解析开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断日期顺序是否有效。
        if start_value > end_value:

            # 抛出日期顺序异常。
            raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{start_date} > {end_date}")

        # 判断报表月份参数是否跨月。
        if start_value.strftime("%Y%m") != end_value.strftime("%Y%m"):

            # 抛出 FineReport 报表跨月限制异常。
            raise ValueError(f"{self.company_name} 单次{data_type}查询仅支持同一自然月，请拆分月份执行")

    # 定义查询分隔线打印方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印包含开始日期和结束日期的标准查询分隔线。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印标准数据类型查询日志。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向记录中的业务日期未超出请求范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 原始记录列表。
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

            # 库存快照无需按日期区间过滤。
            return

        # 初始化返回业务日期集合。
        business_dates = []

        # 遍历当前查询的原始记录。
        for row in rows:

            # 拼接全部可能包含日期的原始字段文本。
            row_text = " ".join(str(value) for key, value in row.items() if "日期" in key)

            # 匹配当前记录中的日期文本。
            matched_date = re.search(r"(\d{4})[-/]?(\d{2})[-/]?(\d{2})", row_text)

            # 判断当前记录是否包含可解析日期。
            if not matched_date:

                # 继续处理下一条记录。
                continue

            # 保存标准化业务日期。
            business_dates.append("-".join(matched_date.groups()))

        # 判断当前响应是否包含可校验业务日期。
        if not business_dates:

            # 无可解析日期时直接返回。
            return

        # 判断返回最小日期是否越过查询开始日期。
        if min(business_dates) < start_date:

            # 抛出结果日期下界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期早于查询开始日期：{min(business_dates)} < {start_date}")

        # 判断返回最大日期是否越过查询结束日期。
        if max(business_dates) > end_date:

            # 抛出结果日期上界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期晚于查询结束日期：{max(business_dates)} > {end_date}")

    # 定义 HTML 请求头构建方法。
    def build_html_headers(self, referer):

        """
        构建 FineDecision HTML 请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 返回 FineDecision HTML 请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": referer, "User-Agent": self.http.user_agent()}

    # 定义 JSON 请求头构建方法。
    def build_json_headers(self, referer):

        """
        构建 FineDecision JSON 登录请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 返回 FineDecision JSON 请求头。
        return {"Accept": "application/json, text/javascript, */*; q=0.01", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/json;charset=UTF-8", "Origin": self.build_origin(), "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    # 定义表单请求头构建方法。
    def build_form_headers(self, referer, session_id):

        """
        构建带 FineReport 会话编号的表单请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :param session_id: FineReport 会话编号。
        :type session_id: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 构建 FineReport 表单请求头。
        headers = {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": self.build_origin(), "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest", "sessionID": session_id}

        # 写入 FineDecision Bearer 授权头。
        self.apply_authorization_header(headers)

        # 返回表单请求头。
        return headers

    # 定义 AJAX 请求头构建方法。
    def build_ajax_headers(self, referer, session_id):

        """
        构建带 FineReport 会话编号的 AJAX 请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :param session_id: FineReport 会话编号。
        :type session_id: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 构建 FineReport AJAX 请求头。
        headers = {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest", "sessionID": session_id}

        # 写入 FineDecision Bearer 授权头。
        self.apply_authorization_header(headers)

        # 返回 AJAX 请求头。
        return headers

    # 定义授权请求头写入方法。
    def apply_authorization_header(self, headers):

        """
        将当前 FineDecision 访问令牌写入请求头。

        :param headers: 待写入的请求头字典。
        :type headers: dict
        :return: None。
        :rtype: None
        """

        # 判断当前会话是否存在访问令牌。
        if self.access_token:

            # 写入 Bearer 授权请求头。
            headers["Authorization"] = f"Bearer {self.access_token}"

    # 定义 JSON 响应解析方法。
    def decode_json_response(self, result):

        """
        解码 FineDecision JSON 响应体。

        :param result: 协议 HTTP 响应对象。
        :type result: HttpResult
        :return: JSON 响应字典。
        :rtype: dict
        """

        # 解码响应体文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 解析并返回 JSON 响应字典。
        return json.loads(response_text)

    # 定义服务源地址构建方法。
    def build_origin(self):

        """
        从报表服务器地址构建站点源地址。

        :return: 站点源地址。
        :rtype: str
        """

        # 匹配协议和主机部分。
        matched_origin = re.match(r"https?://[^/]+", self.base_url)

        # 返回匹配到的站点源地址。
        return matched_origin.group(0) if matched_origin else self.base_url

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, raw_headers, data_type, output_path):

        """
        写入标准字段前置并保留全部原始字段的 Excel 文件。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param raw_headers: 原始字段列表。
        :type raw_headers: list[str]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param output_path: Excel 输出路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 读取当前数据类型的标准字段映射。
        standard_fields = STANDARD_FIELD_MAP[data_type]

        # 构建完整原始字段 Excel 表头。
        raw_excel_headers = [f"原始_{header}" for header in raw_headers]

        # 构建标准字段前置的完整 Excel 表头。
        excel_headers = [field_name for field_name, _ in standard_fields] + raw_excel_headers

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称为数据类型。
        worksheet.title = data_type

        # 写入 Excel 表头。
        worksheet.append(excel_headers)

        # 遍历全部原始记录。
        for row in rows:

            # 读取标准字段值集合。
            standard_values = [row.get(raw_field, "") for _, raw_field in standard_fields]

            # 读取完整原始字段值集合。
            raw_values = [row.get(header, "") for header in raw_headers]

            # 写入当前 Excel 数据行。
            worksheet.append(standard_values + raw_values)

        # 应用项目统一 Excel 样式。
        apply_standard_excel_style(worksheet)

        # 保存 Excel 工作簿。
        workbook.save(output_path)
