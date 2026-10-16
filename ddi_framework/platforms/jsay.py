# -*- coding: utf-8 -*-
"""
江苏澳洋 FineReport 数据分析系统协议适配器。

本模块负责江苏澳洋医药物流有限公司 FineDecision 登录、报表参数提交、分 Sheet 数据读取和本地 Excel 生成。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 HTML 解析器基类。
from html.parser import HTMLParser

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入随机数模块。
import random

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入日期时间解析对象。
from datetime import datetime

# 导入 Cookie 对象。
from http.cookiejar import Cookie

# 导入 URL 表单编码函数。
from urllib.parse import urlencode

# 导入 URL 解析函数。
from urllib.parse import urlparse

# 导入 PKCS7 填充器。
from cryptography.hazmat.primitives import padding

# 导入分组密码对象。
from cryptography.hazmat.primitives.ciphers import Cipher

# 导入 AES 算法配置。
from cryptography.hazmat.primitives.ciphers import algorithms

# 导入分组模式配置。
from cryptography.hazmat.primitives.ciphers import modes

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义 FineReport 数据类型与报表页签映射。
REPORT_SHEETS = {
    "库存": {"reportIndex": 0, "sheetName": "库存", "sourceName": "库存"},
    "购进流向": {"reportIndex": 1, "sheetName": "购进", "sourceName": "购进"},
    "配送流向": {"reportIndex": 2, "sheetName": "销售", "sourceName": "销售"},
}


class FineReportTableParser(HTMLParser):
    """
    FineReport 预览表格 HTML 解析器。

    :return: FineReport 表格解析器实例。
    :rtype: FineReportTableParser
    """

    def __init__(self):
        """
        初始化 FineReport 表格解析状态。

        :return: None。
        :rtype: None
        """

        # 调用 HTML 解析器初始化逻辑。
        super().__init__(convert_charrefs=True)

        # 初始化表格行集合。
        self.rows = []

        # 初始化当前行缓存。
        self.current_row = None

        # 初始化当前单元格缓存。
        self.current_cell = None

        # 初始化当前单元格标题值。
        self.current_title = None

    def handle_starttag(self, tag, attrs):
        """
        处理 HTML 开始标签。

        :param tag: 标签名称。
        :type tag: str
        :param attrs: 标签属性列表。
        :type attrs: list[tuple[str, str | None]]
        :return: None。
        :rtype: None
        """

        # 判断当前标签是否为表格行。
        if tag == "tr":

            # 创建当前行缓存。
            self.current_row = []

            # 结束当前标签处理。
            return

        # 判断当前标签是否为单元格。
        if tag in ("td", "th") and self.current_row is not None:

            # 创建当前单元格文本缓存。
            self.current_cell = []

            # 读取单元格标题属性。
            self.current_title = dict(attrs).get("title")

    def handle_data(self, data):
        """
        处理 HTML 文本节点。

        :param data: 文本节点内容。
        :type data: str
        :return: None。
        :rtype: None
        """

        # 判断当前是否处于单元格内部。
        if self.current_cell is not None:

            # 保存当前单元格文本片段。
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        """
        处理 HTML 结束标签。

        :param tag: 标签名称。
        :type tag: str
        :return: None。
        :rtype: None
        """

        # 判断当前结束标签是否为单元格。
        if tag in ("td", "th") and self.current_cell is not None and self.current_row is not None:

            # 优先使用 title 属性中的完整文本。
            cell_value = self.current_title if self.current_title is not None else "".join(self.current_cell)

            # 保存清洗后的单元格值。
            self.current_row.append(str(cell_value or "").strip())

            # 清空当前单元格缓存。
            self.current_cell = None

            # 清空当前单元格标题值。
            self.current_title = None

            # 结束当前标签处理。
            return

        # 判断当前结束标签是否为表格行。
        if tag == "tr" and self.current_row is not None:

            # 判断当前行是否包含有效文本。
            if any(cell for cell in self.current_row):

                # 保存当前表格行。
                self.rows.append(self.current_row)

            # 清空当前行缓存。
            self.current_row = None


class JsayPlatform(BasePlatform):
    """
    江苏澳洋 FineReport 数据分析系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 江苏澳洋平台适配器实例。
    :rtype: JsayPlatform
    """

    def __init__(self, company_name, account, printer=None):
        """
        初始化江苏澳洋 FineReport 平台适配器。

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

        # 初始化日志打印器。
        self.ph = printer or PrintHandler()

        # 保存接口根地址。
        self.api_base_url = account.get("接口根地址", "http://fr.aoyang.com").rstrip("/")

        # 保存 FineDecision 应用路径。
        self.decision_path = account.get("应用路径", "/WebReport/decision")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.api_base_url}{self.decision_path}/login")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", self.login_page_url)

        # 保存报表入口编号。
        self.entry_id = account.get("流向入口ID", "10870e87-35d4-487b-8906-1a849438f19c")

        # 保存参数最大查询天数。
        self.max_query_days = int(account.get("最大查询天数", 90))

        # 保存平台源地址。
        self.origin_url = self.build_origin(self.api_base_url)

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 初始化登录令牌。
        self.access_token = ""

        # 初始化登录状态。
        self.logged_in = False

    def login(self):
        """
        执行江苏澳洋 FineDecision 协议登录。

        :return: 登录响应数据。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("江苏澳洋登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.join(self.ph.kv("访问登录页", self.login_page_url, "cyan"), self.ph.kv("账号", self.clean_login_name(), "cyan")))

        # 访问登录页以建立站点 Cookie。
        login_page = self.http.get(self.login_page_url)

        # 解码登录页 HTML。
        login_html = login_page.body.decode("utf-8", errors="replace")

        # 提取 FineDecision 前端加密配置。
        cipher_config = self.extract_cipher_config(login_html)

        # 构建登录请求体。
        payload = self.build_login_payload(cipher_config)

        # 提交登录 JSON 请求。
        result = self.post_login_json(payload)

        # 解析登录响应。
        response_data = self.decode_json_response(result)

        # 校验登录响应数据。
        self.validate_login_response(response_data)

        # 保存登录访问令牌。
        self.access_token = str(response_data.get("data", {}).get("accessToken", ""))

        # 写入 FineDecision 登录 Cookie。
        self.apply_token_cookies(self.access_token)

        # 标记当前登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("用户", response_data.get("data", {}).get("username", ""), "cyan")))

        # 返回登录响应数据。
        return response_data

    def build_login_payload(self, cipher_config):
        """
        构建 FineDecision 登录请求体。

        :param cipher_config: 前端加密配置。
        :type cipher_config: dict
        :return: 登录请求体。
        :rtype: dict
        """

        # 读取前端 AES 密钥。
        front_seed = cipher_config.get("frontSeed", "")

        # 加密登录密码。
        encrypted_password = self.encrypt_aes_ecb_pkcs7_base64(self.clean_login_password(), front_seed)

        # 返回登录请求体字段。
        return {"username": self.clean_login_name(), "password": encrypted_password, "validity": -1, "sliderToken": "", "origin": "", "encrypted": True}

    def post_login_json(self, payload):
        """
        提交 FineDecision 登录 JSON 请求。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建登录请求头。
        headers = self.build_json_headers(self.login_page_url)

        # 编码 JSON 请求体。
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 发送登录请求。
        return self.http.request("POST", self.login_api_url, headers=headers, data=data, timeout=60)

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

        # 查询 FineReport 数据。
        query_result = self.query_jsay_data(data_type, start_date, end_date)

        # 返回查询结果行。
        return query_result["rows"]



    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):
        """
        查询指定类型业务数据并生成 Excel。

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

        # 查询 FineReport 数据。
        query_result = self.query_jsay_data(data_type, start_date, end_date)

        # 使用当前工作目录作为默认输出目录。
        output_dir = output_dir or os.getcwd()

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 构建输出文件路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    def query_jsay_data(self, data_type, start_date, end_date):
        """
        查询江苏澳洋 FineReport 指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果、表头和日期范围。
        :rtype: dict
        """

        # 校验数据类型。
        self.validate_data_type(data_type)

        # 确保当前会话已经登录。
        self.ensure_login()

        # 解析查询日期范围。
        start_date, end_date = self.resolve_query_dates(start_date, end_date)

        # 校验查询日期跨度。
        self.validate_query_range(start_date, end_date)

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 初始化报表会话。
        report_context = self.initialize_report_session()

        # 提交报表参数。
        self.submit_report_parameters(report_context["session_id"], report_context["entry_url"], start_date, end_date)

        # 读取当前数据类型对应的报表内容。
        content_data = self.fetch_sheet_content(report_context["session_id"], report_context["entry_url"], data_type)

        # 解析报表 HTML 行。
        table_rows = self.parse_report_html(content_data.get("html", ""))

        # 组装表头和数据行。
        headers, rows = self.build_rows_from_table(table_rows)

        # 打印查询结果日志。
        self.ph.success(self.ph.join(self.ph.kv("报表页签解析完成", REPORT_SHEETS[data_type]["sheetName"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果。
        return {"headers": headers, "rows": rows, "start_date": start_date, "end_date": end_date}

    def initialize_report_session(self):
        """
        初始化 FineReport 报表会话。

        :return: 报表会话上下文。
        :rtype: dict
        """

        # 构建报表入口访问地址。
        entry_url = f"{self.api_base_url}{self.decision_path}/v10/entry/access/{self.entry_id}"

        # 构建报表入口请求头。
        headers = self.build_html_headers(f"{self.api_base_url}{self.decision_path}")

        # 写入授权请求头。
        self.apply_authorization_header(headers)

        # 访问报表入口。
        result = self.http.request("GET", entry_url, headers=headers, timeout=120)

        # 解码报表入口 HTML。
        html_text = result.body.decode("utf-8", errors="replace")

        # 提取报表会话编号。
        session_id = self.extract_report_session_id(html_text)

        # 打印会话初始化日志。
        self.ph.info(self.ph.join(self.ph.kv("报表会话", session_id, "cyan"), self.ph.kv("入口", self.entry_id, "cyan")))

        # 返回报表上下文。
        return {"entry_url": entry_url, "session_id": session_id}

    def submit_report_parameters(self, session_id, entry_url, start_date, end_date):
        """
        提交 FineReport 参数面板日期条件。

        :param session_id: 报表会话编号。
        :type session_id: str
        :param entry_url: 报表入口地址。
        :type entry_url: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 参数提交响应数据。
        :rtype: dict
        """

        # 构建参数提交地址。
        url = f"{self.api_base_url}{self.decision_path}/view/report?op=fr_dialog&cmd=parameters_d&sessionID={session_id}"

        # 构建参数字段。
        parameter_values = {"起始日期": start_date, "结束日期": end_date, "商品名称": ""}

        # 构建表单请求体。
        data = urlencode({"__parameters__": json.dumps(parameter_values, ensure_ascii=False, separators=(",", ":")), "_": str(int(time.time() * 1000))}).encode("utf-8")

        # 构建表单请求头。
        headers = self.build_form_headers(entry_url, session_id=session_id)

        # 发送参数提交请求。
        result = self.http.request("POST", url, headers=headers, data=data, timeout=120)

        # 解析参数提交响应。
        response_data = self.decode_json_response(result)

        # 校验参数提交结果。
        if str(response_data.get("status", "")).lower() != "success":

            # 抛出参数提交异常。
            raise RuntimeError(f"{self.company_name} 报表参数提交失败：{response_data}")

        # 打印参数提交日志。
        self.ph.info(self.ph.join(self.ph.kv("报表参数", "提交成功", "green"), self.ph.kv("起始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 返回参数提交响应。
        return response_data

    def fetch_sheet_content(self, session_id, entry_url, data_type):
        """
        读取 FineReport 指定 Sheet 的内容。

        :param session_id: 报表会话编号。
        :type session_id: str
        :param entry_url: 报表入口地址。
        :type entry_url: str
        :param data_type: 数据类型名称。
        :type data_type: str
        :return: Sheet 内容响应。
        :rtype: dict
        """

        # 读取报表页签配置。
        sheet_config = REPORT_SHEETS[data_type]

        # 构建报表内容请求地址。
        url = f"{self.api_base_url}{self.decision_path}/view/report?_={int(time.time() * 1000)}&__boxModel__=true&op=fr_view&cmd=view_content&sessionID={session_id}&reportIndex={sheet_config['reportIndex']}&iid={random.random()}"

        # 构建 AJAX 请求头。
        headers = self.build_ajax_headers(entry_url)

        # 发送报表内容请求。
        result = self.http.request("GET", url, headers=headers, timeout=180)

        # 返回 JSON 响应数据。
        return self.decode_json_response(result)

    def parse_report_html(self, html_text):
        """
        解析 FineReport 报表 HTML 表格。

        :param html_text: 报表 HTML 文本。
        :type html_text: str
        :return: 表格行集合。
        :rtype: list[list[str]]
        """

        # 创建 FineReport 表格解析器。
        parser = FineReportTableParser()

        # 解析报表 HTML 文本。
        parser.feed(str(html_text or ""))

        # 返回表格行集合。
        return parser.rows

    def build_rows_from_table(self, table_rows):
        """
        根据 FineReport 表格行构建表头和字典行。

        :param table_rows: 表格行集合。
        :type table_rows: list[list[str]]
        :return: 表头和数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 判断表格是否为空。
        if not table_rows:

            # 返回空表头和空数据。
            return [], []

        # 读取第一行作为表头。
        headers = self.normalize_headers(table_rows[0])

        # 初始化数据行集合。
        rows = []

        # 遍历表头之后的数据行。
        for raw_row in table_rows[1:]:

            # 跳过完全空白的数据行。
            if not any(cell for cell in raw_row):

                # 进入下一行。
                continue

            # 按表头组装字典行。
            row = {header: raw_row[index] if index < len(raw_row) else "" for index, header in enumerate(headers)}

            # 保存字典行。
            rows.append(row)

        # 返回表头和数据行。
        return headers, rows

    def normalize_headers(self, headers):
        """
        标准化表头并处理重复字段。

        :param headers: 原始表头列表。
        :type headers: list[str]
        :return: 标准化表头列表。
        :rtype: list[str]
        """

        # 初始化字段出现次数。
        name_counts = {}

        # 初始化标准化表头。
        normalized_headers = []

        # 遍历原始表头。
        for index, header in enumerate(headers, start=1):

            # 读取清洗后的字段名。
            field_name = str(header or "").strip() or f"字段{index}"

            # 递增字段出现次数。
            name_counts[field_name] = name_counts.get(field_name, 0) + 1

            # 判断字段是否首次出现。
            if name_counts[field_name] == 1:

                # 保存原始字段名。
                normalized_headers.append(field_name)

                # 进入下一个字段。
                continue

            # 保存带序号的重复字段名。
            normalized_headers.append(f"{field_name}_{name_counts[field_name]}")

        # 返回标准化表头。
        return normalized_headers

    def extract_cipher_config(self, login_html):
        """
        从登录页提取 FineDecision 前端加密配置。

        :param login_html: 登录页 HTML。
        :type login_html: str
        :return: 前端加密配置。
        :rtype: dict
        """

        # 查找独立前端密钥赋值。
        seed_match = re.search(r'Dec\.system\.frontSeed\s*=\s*"([^"]+)"', login_html)

        # 判断独立密钥赋值是否存在。
        if seed_match:

            # 返回独立密钥配置。
            return {"frontSeed": seed_match.group(1)}

        # 查找 JSON.parse 形式的系统配置。
        config_match = re.search(r"Dec\.system\s*=\s*JSON\.parse\('(.+?)'\);", login_html, re.S)

        # 判断系统配置是否存在。
        if not config_match:

            # 抛出加密配置缺失异常。
            raise RuntimeError(f"{self.company_name} 登录页缺少 FineDecision 加密配置")

        # 反转义 JavaScript 字符串中的 JSON 文本。
        config_text = config_match.group(1).encode("utf-8").decode("unicode_escape")

        # 解析系统配置 JSON。
        config_data = json.loads(config_text)

        # 校验前端密钥是否存在。
        if not config_data.get("frontSeed"):

            # 抛出密钥缺失异常。
            raise RuntimeError(f"{self.company_name} 登录页缺少 frontSeed")

        # 返回系统配置。
        return config_data

    def extract_report_session_id(self, html_text):
        """
        从报表入口 HTML 中提取报表会话编号。

        :param html_text: 报表入口 HTML。
        :type html_text: str
        :return: 报表会话编号。
        :rtype: str
        """

        # 查找当前会话编号赋值。
        session_match = re.search(r"currentSessionID\s*=\s*'([^']+)'", html_text)

        # 判断当前会话编号是否存在。
        if session_match:

            # 返回当前会话编号。
            return session_match.group(1)

        # 查找 SessionMgr 注册调用。
        register_match = re.search(r"FR\.SessionMgr\.register\('([^']+)'", html_text)

        # 判断注册调用是否存在。
        if register_match:

            # 返回注册调用中的会话编号。
            return register_match.group(1)

        # 抛出会话编号缺失异常。
        raise RuntimeError(f"{self.company_name} 报表入口缺少 sessionID")

    def encrypt_aes_ecb_pkcs7_base64(self, plain_text, secret_key):
        """
        使用 AES-ECB-PKCS7 加密文本并返回 Base64 密文。

        :param plain_text: 明文字段。
        :type plain_text: str
        :param secret_key: AES 密钥。
        :type secret_key: str
        :return: Base64 密文。
        :rtype: str
        """

        # 创建 PKCS7 填充器。
        padder = padding.PKCS7(algorithms.AES.block_size).padder()

        # 填充明文字节。
        padded_bytes = padder.update(str(plain_text).encode("utf-8")) + padder.finalize()

        # 创建 AES-ECB 加密器。
        encryptor = Cipher(algorithms.AES(str(secret_key).encode("utf-8")), modes.ECB()).encryptor()

        # 生成密文字节。
        cipher_bytes = encryptor.update(padded_bytes) + encryptor.finalize()

        # 返回 Base64 密文。
        return base64.b64encode(cipher_bytes).decode("ascii")

    def apply_token_cookies(self, access_token):
        """
        写入 FineDecision 登录令牌 Cookie。

        :param access_token: 登录访问令牌。
        :type access_token: str
        :return: None。
        :rtype: None
        """

        # 写入登录令牌 Cookie。
        self.add_cookie("fine_auth_token", access_token)

        # 写入记住登录有效期 Cookie。
        self.add_cookie("fine_remember_login", "-1")

        # 写入默认租户 Cookie。
        self.add_cookie("tenantId", "default")

    def add_cookie(self, name, value):
        """
        向协议客户端 Cookie 容器写入 Cookie。

        :param name: Cookie 名称。
        :type name: str
        :param value: Cookie 值。
        :type value: str
        :return: None。
        :rtype: None
        """

        # 解析接口主机域名。
        domain = urlparse(self.api_base_url).hostname or ""

        # 创建 Cookie 对象。
        cookie = Cookie(0, name, str(value), None, False, domain, True, False, "/", True, False, None, True, None, None, {}, False)

        # 写入 Cookie 容器。
        self.http.cookie_jar.set_cookie(cookie)


    def validate_login_response(self, response_data):
        """
        校验 FineDecision 登录响应。

        :param response_data: 登录响应数据。
        :type response_data: dict
        :return: None。
        :rtype: None
        """

        # 读取登录令牌。
        access_token = response_data.get("data", {}).get("accessToken")

        # 判断登录令牌是否存在。
        if access_token:

            # 登录令牌存在时直接返回。
            return

        # 读取平台错误消息。
        message = response_data.get("errorMsg") or response_data.get("message") or response_data

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 登录失败：{message}")

    def validate_data_type(self, data_type):
        """
        校验数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否存在页签映射。
        if data_type not in REPORT_SHEETS:

            # 抛出数据类型未接入异常。
            raise ValueError(f"江苏澳洋平台暂不支持数据类型：{data_type}")

    def validate_query_range(self, start_date, end_date):
        """
        校验 FineReport 查询日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 解析开始日期。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断开始日期是否晚于结束日期。
        if start_value > end_value:

            # 抛出日期范围异常。
            raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{start_date} > {end_date}")

        # 判断查询跨度是否超过平台限制。
        if (end_value - start_value).days > self.max_query_days:

            # 抛出日期跨度异常。
            raise ValueError(f"{self.company_name} 单次查询范围不能超过 {self.max_query_days} 天")

    def resolve_query_dates(self, start_date, end_date):
        """
        解析查询日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询开始日期与结束日期。
        :rtype: tuple[str, str]
        """

        # 读取当天日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 返回查询日期范围。
        return start_date or today_text, end_date or today_text

    def print_query_section(self, data_type, start_date, end_date):
        """
        打印查询阶段标题。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印业务查询标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

    def build_html_headers(self, referer):
        """
        构建 HTML 请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 返回 HTML 请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": referer, "User-Agent": self.http.user_agent()}

    def build_json_headers(self, referer):
        """
        构建 JSON 请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 返回 JSON 请求头。
        return {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/json;charset=UTF-8", "Origin": self.origin_url, "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    def build_form_headers(self, referer, session_id=""):
        """
        构建 FineReport 表单请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :param session_id: 报表会话编号。
        :type session_id: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 构建表单请求头。
        headers = {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": self.origin_url, "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

        # 判断是否需要写入会话头。
        if session_id:

            # 写入 FineReport 报表会话头。
            headers["sessionID"] = session_id

        # 写入授权请求头。
        self.apply_authorization_header(headers)

        # 返回表单请求头。
        return headers

    def build_ajax_headers(self, referer):
        """
        构建 FineReport AJAX 请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 构建 AJAX 请求头。
        headers = {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

        # 写入授权请求头。
        self.apply_authorization_header(headers)

        # 返回 AJAX 请求头。
        return headers

    def apply_authorization_header(self, headers):
        """
        写入 FineDecision 授权请求头。

        :param headers: 请求头字典。
        :type headers: dict
        :return: None。
        :rtype: None
        """

        # 判断访问令牌是否存在。
        if self.access_token:

            # 写入 Bearer 授权头。
            headers["Authorization"] = f"Bearer {self.access_token}"

    def decode_json_response(self, result):
        """
        解析 JSON 响应体。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 解码响应体文本。
        text = result.body.decode("utf-8", errors="replace")

        # 返回 JSON 解析结果。
        return json.loads(text)




    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):
        """
        写入查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param headers: 表头列表。
        :type headers: list[str]
        :param output_path: Excel 输出路径。
        :type output_path: str
        :param sheet_name: 工作表名称。
        :type sheet_name: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 导入列宽工具函数。
        from openpyxl.utils import get_column_letter

        # 删除已有同名文件。
        self.remove_existing_file(output_path)

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = sheet_name[:31]

        # 写入表头行。
        worksheet.append(headers)

        # 遍历结果行。
        for row in rows:

            # 按表头顺序写入当前行。
            worksheet.append([row.get(header, "") for header in headers])

        # 遍历表头列设置宽度。
        for column_index, header_name in enumerate(headers, start=1):

            # 读取列字母。
            column_letter = get_column_letter(column_index)

            # 设置列宽。
            worksheet.column_dimensions[column_letter].width = max(12, min(34, len(str(header_name)) + 10))

        # 冻结表头行。
        worksheet.freeze_panes = "A2"

        # 启用自动筛选。
        worksheet.auto_filter.ref = worksheet.dimensions

        # 创建输出目录。
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 保存 Excel 文件。
        try:

            # 将工作簿保存到目标路径。
            workbook.save(output_path)

        # 处理文件占用异常。
        except PermissionError as error:

            # 抛出带路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

    def remove_existing_file(self, output_path):
        """
        删除已有同名输出文件。

        :param output_path: 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 判断输出文件是否存在。
        if not os.path.exists(output_path):

            # 文件不存在时直接返回。
            return

        # 删除已有输出文件。
        os.remove(output_path)


    def clean_login_password(self):
        """
        读取并清洗登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回原始密码字符串。
        return str(self.account.get("密码", ""))

    def build_origin(self, url):
        """
        构建站点源地址。

        :param url: 平台根地址。
        :type url: str
        :return: 站点源地址。
        :rtype: str
        """

        # 解析 URL。
        parsed_url = urlparse(url)

        # 读取端口片段。
        port_part = f":{parsed_url.port}" if parsed_url.port else ""

        # 返回源地址。
        return f"{parsed_url.scheme}://{parsed_url.hostname}{port_part}"
