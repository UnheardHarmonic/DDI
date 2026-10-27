# -*- coding: utf-8 -*-
"""
鸿翔一心堂 SRM FineReport 协议适配器。

本模块负责一心堂 SRM 的 RSA 登录、FineReport 授权跳转、供应商流向报表参数提交、分页读取和本地 Excel 生成。
"""

# 导入 Base64 编解码模块。
import base64

# 导入哈希摘要模块。
import hashlib

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入 SSL 上下文模块。
import ssl

# 导入时间模块。
import time

# 导入日期时间解析对象。
from datetime import datetime

# 导入 Cookie 容器。
from http.cookiejar import CookieJar

# 导入 URL 表单编码函数。
from urllib.parse import quote

# 导入 URL 表单编码函数。
from urllib.parse import urlencode

# 导入 URL 错误类型。
from urllib.error import HTTPError

# 导入 Cookie 处理器。
from urllib.request import HTTPCookieProcessor

# 导入 HTTPS 处理器。
from urllib.request import HTTPSHandler

# 导入 URL 请求对象。
from urllib.request import Request

# 导入 URL 打开器构建函数。
from urllib.request import build_opener

# 导入 RSA 公钥序列化工具。
from cryptography.hazmat.primitives import serialization

# 导入 RSA 填充模式。
from cryptography.hazmat.primitives.asymmetric import padding

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入 FineReport 表格解析器。
from ddi_framework.platforms.jsay import FineReportTableParser


# 定义一心堂 SRM 默认报表入口。
HXYXT_DEFAULT_REPORT_ENTRY = "/WebReport/decision/v10/entry/access/old-platform-reportlet-entry-941"


# 定义一心堂配送流向表头。
HXYXT_FLOW_HEADERS = ["序号", "公司", "分部", "过账日期", "商品编码", "商品名称", "收货方", "收货方名称", "数量", "说明"]


# 定义一心堂平台适配器。
class HxyxtPlatform(BasePlatform):

    """
    鸿翔一心堂 SRM FineReport 协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台适配器实例。
    :rtype: HxyxtPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化一心堂 SRM FineReport 协议适配器。

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

        # 保存站点根地址。
        self.site_root_url = account.get("站点根地址", "https://yxt-srm.hxyxt.com").rstrip("/")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.site_root_url}/user/login?redirect=%2Fhome")

        # 保存公钥接口地址。
        self.public_key_url = account.get("公钥接口", f"{self.site_root_url}/els/account/noToken/getEncryptedKey")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", f"{self.site_root_url}/els/account/login")

        # 保存 FineReport 跳转接口地址。
        self.fine_bridge_url = account.get("报表跳转接口", f"{self.site_root_url}/els/saleMaterialFlow/saleMaterialFlowHead/toFine")

        # 保存 FineReport 报表入口路径。
        self.report_entry_path = account.get("配送流向报表入口", HXYXT_DEFAULT_REPORT_ENTRY)

        # 保存 FineReport 决策路径。
        self.decision_path = account.get("决策路径", "/decision")

        # 保存登录账号。
        self.els_account = account.get("账号", "")

        # 保存登录子账号。
        self.sub_account = account.get("子账号", "")

        # 保存登录密码。
        self.password = account.get("密码", "")

        # 保存公司代码。
        self.company_code = str(account.get("公司代码", ""))

        # 保存公司代码名称。
        self.company_code_name = str(account.get("公司代码名称", ""))

        # 保存多公司代码查询配置。
        self.company_code_items = list(account.get("公司代码列表", []))

        # 保存文件名公司代码标记开关。
        self.company_name_marker_enabled = bool(self.company_code_items) or bool(account.get("文件名公司标记", False))

        # 保存当前公司代码名称。
        self.current_company_code_name = self.company_code_name

        # 保存供应商参数。
        self.supplier_user_id = str(account.get("供应商参数", ""))

        # 保存商品列表参数。
        self.item_list_value = str(account.get("商品列表参数", ""))

        # 保存默认商品列表参数。
        self.default_item_list_value = self.item_list_value

        # 保存分页纸张宽度。
        self.paper_width = int(account.get("纸张宽度", 754))

        # 保存分页纸张高度。
        self.paper_height = int(account.get("纸张高度", 779))

        # 保存查询日期字段名称。
        self.date_column = account.get("日期字段", "过账日期")

        # 保存最大查询天数。
        self.max_query_days = int(account.get("最大查询天数", 90))

        # 初始化 Cookie 容器。
        self.cookie_jar = CookieJar()

        # 初始化 HTTPS 上下文。
        self.ssl_context = ssl._create_unverified_context()

        # 初始化协议请求打开器。
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar), HTTPSHandler(context=self.ssl_context))

        # 初始化 SRM 访问令牌。
        self.access_token = ""

        # 初始化登录响应数据。
        self.login_data = {}

        # 初始化报表入口 HTML。
        self.entry_html = ""

        # 初始化报表会话编号。
        self.report_session_id = ""

        # 初始化登录状态。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        登录一心堂 SRM 并初始化 FineReport 会话。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("一心堂 SRM 登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页建立初始 Cookie。
        self.get_bytes(self.login_page_url, headers=self.build_html_headers(self.site_root_url))

        # 获取 RSA 公钥配置。
        key_data = self.get_json(self.public_key_url, headers=self.build_json_headers(self.login_page_url))

        # 构建登录请求体。
        payload = self.build_login_payload(key_data)

        # 提交登录请求。
        response_data = self.post_json(f"{self.login_api_url}?_t={int(time.time())}", payload, referer=self.login_page_url)

        # 校验登录响应。
        self.validate_login_response(response_data)

        # 保存登录响应数据。
        self.login_data = response_data

        # 保存访问令牌。
        self.access_token = response_data["result"]["token"]

        # 初始化 FineReport 会话。
        self.initialize_report_session()

        # 标记当前登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("报表会话", self.report_session_id, "cyan")))

        # 返回登录摘要。
        return {"status": "success", "session_id": self.report_session_id}

    # 定义会话保存方法。
    def save_cookie(self, output_dir):

        """
        保存一心堂 SRM 当前协议会话信息。

        :param output_dir: 会话信息输出目录。
        :type output_dir: str
        :return: 会话信息文件路径。
        :rtype: str
        """

        # 创建会话信息输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建会话信息文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 提取当前 Cookie 值。
        cookie_values = {cookie.name: cookie.value for cookie in self.cookie_jar}

        # 组装会话信息内容。
        cookie_data = {
            "site_root_url": self.site_root_url,
            "login_api_url": self.login_api_url,
            "report_entry_path": self.report_entry_path,
            "report_session_id": self.report_session_id,
            "access_token_present": bool(self.access_token),
            "company_code": self.company_code,
            "supplier_user_id": self.supplier_user_id,
            "item_list_value": self.item_list_value,
            "cookies": cookie_values,
        }

        # 打开会话信息文件。
        with open(cookie_path, "w", encoding="utf-8") as file_obj:

            # 写入会话信息内容。
            json.dump(cookie_data, file_obj, ensure_ascii=False, indent=2)

        # 打印会话保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回会话信息文件路径。
        return cookie_path

    # 定义登录请求体构建方法。
    def build_login_payload(self, key_data):

        """
        构建一心堂 SRM 登录请求体。

        :param key_data: 公钥接口响应数据。
        :type key_data: dict
        :return: 登录请求体。
        :rtype: dict
        """

        # 读取公钥数据。
        public_key_text = key_data["result"]["key"]

        # 读取公钥编号。
        key_id = key_data["result"]["keyId"]

        # 反序列化 RSA 公钥。
        public_key = serialization.load_der_public_key(base64.b64decode(public_key_text))

        # 使用 RSA PKCS1 v1.5 加密密码。
        encrypted_password = public_key.encrypt(self.password.encode("utf-8"), padding.PKCS1v15())

        # 转换加密密码为 Base64 文本。
        password_text = base64.b64encode(encrypted_password).decode("ascii")

        # 返回登录请求体。
        return {"loginType": None, "elsAccount": self.els_account, "subAccount": self.sub_account, "password": password_text, "keyId": key_id}

    # 定义登录响应校验方法。
    def validate_login_response(self, response_data):

        """
        校验一心堂 SRM 登录响应。

        :param response_data: 登录响应数据。
        :type response_data: dict
        :return: None。
        :rtype: None
        """

        # 判断登录响应是否成功。
        if response_data.get("success") is True and response_data.get("result", {}).get("token"):

            # 登录成功时直接返回。
            return

        # 读取错误消息。
        message = response_data.get("message") or response_data.get("msg") or response_data

        # 抛出登录异常。
        raise RuntimeError(f"{self.company_name} 登录失败：{message}")

    # 定义 FineReport 会话初始化方法。
    def initialize_report_session(self):

        """
        初始化 FineReport 供应商流向报表会话。

        :return: None。
        :rtype: None
        """

        # 构建报表入口绝对地址。
        entry_url = self.build_report_entry_url()

        # 构建报表授权跳转参数。
        query_text = urlencode({"token": self.access_token, "url": self.report_entry_path})

        # 构建报表授权跳转地址。
        bridge_url = f"{self.fine_bridge_url}?{query_text}"

        # 访问报表授权跳转地址。
        self.get_bytes(bridge_url, headers=self.build_token_headers(self.login_page_url))

        # 访问报表入口地址。
        entry_body = self.get_bytes(entry_url, headers=self.build_token_headers(bridge_url))

        # 解码报表入口 HTML。
        self.entry_html = entry_body.decode("utf-8", errors="replace")

        # 提取报表会话编号。
        self.report_session_id = self.extract_report_session_id(self.entry_html)

        # 补齐报表参数默认值。
        self.extract_default_report_parameters()

    # 定义报表默认参数提取方法。
    def extract_default_report_parameters(self):

        """
        从报表入口 HTML 中提取隐藏供应商参数和商品列表参数。

        :return: None。
        :rtype: None
        """

        # 判断供应商参数是否缺失。
        if not self.supplier_user_id:

            # 从 FR_USERNAME1 控件中提取供应商参数。
            self.supplier_user_id = self.extract_widget_value(self.entry_html, "FR_USERNAME1") or self.extract_widget_value(self.entry_html, "fr_username1")

        # 判断商品列表参数是否缺失。
        if not self.item_list_value:

            # 从 ITEMLIST 控件中提取商品列表参数。
            self.item_list_value = self.extract_widget_value(self.entry_html, "ITEMLIST") or self.extract_widget_value(self.entry_html, "itemlist")

        # 判断公司代码是否缺失。
        if not self.company_code:

            # 从公司代码控件中提取匹配名称对应的代码。
            self.company_code = self.extract_company_code_value()

    # 定义公司代码提取方法。
    def extract_company_code_value(self):

        """
        从 FineReport 公司代码控件中提取实际提交值。

        :return: 公司代码实际提交值。
        :rtype: str
        """

        # 解析公司代码控件候选项。
        option_values = self.extract_widget_options(self.entry_html, "公司代码")

        # 判断是否配置了公司代码名称。
        if self.company_code_name:

            # 遍历公司代码候选项。
            for option_value, option_text in option_values:

                # 判断候选项文本是否匹配配置名称。
                if self.company_code_name in option_text:

                    # 返回匹配的公司代码。
                    return option_value

        # 判断候选项是否存在。
        if option_values:

            # 返回第一个公司代码。
            return option_values[0][0]

        # 从公司代码控件中提取默认值。
        return self.extract_widget_value(self.entry_html, "公司代码")

    # 定义控件候选项提取方法。
    def extract_widget_options(self, html_text, widget_name):

        """
        从 FineReport 控件配置中提取候选项。

        :param html_text: 报表入口 HTML。
        :type html_text: str
        :param widget_name: 控件名称。
        :type widget_name: str
        :return: 候选项值与文本列表。
        :rtype: list[tuple[str, str]]
        """

        # 读取控件属性完整片段。
        control_text = self.extract_widget_control_text(html_text, widget_name)

        # 判断控件属性是否存在。
        if not control_text:

            # 返回空候选项列表。
            return []

        # 提取候选项值与文本。
        option_matches = re.findall(r'"value"\s*:\s*"([^"]*)"\s*,\s*"text"\s*:\s*"([^"]*)"', control_text)

        # 返回候选项列表。
        return [(value, text) for value, text in option_matches]

    # 定义控件属性完整片段提取方法。
    def extract_widget_control_text(self, html_text, widget_name):

        """
        从 FineReport 控件配置中提取 controlAttr 完整对象文本。

        :param html_text: 报表入口 HTML。
        :type html_text: str
        :param widget_name: 控件名称。
        :type widget_name: str
        :return: controlAttr 对象文本。
        :rtype: str
        """

        # 构建控件名称匹配表达式。
        widget_pattern = rf'"widgetName"\s*:\s*"{re.escape(widget_name)}"'

        # 查找控件名称位置。
        widget_match = re.search(widget_pattern, html_text)

        # 判断控件名称是否存在。
        if not widget_match:

            # 返回空配置文本。
            return ""

        # 查找控件属性字段位置。
        control_index = html_text.find('"controlAttr"', widget_match.end())

        # 判断控件属性字段是否存在。
        if control_index < 0:

            # 返回空配置文本。
            return ""

        # 查找控件属性对象起始位置。
        brace_index = html_text.find("{", control_index)

        # 判断对象起始位置是否存在。
        if brace_index < 0:

            # 返回空配置文本。
            return ""

        # 返回平衡花括号包裹的对象文本。
        return self.extract_balanced_object_text(html_text, brace_index)

    # 定义平衡对象文本提取方法。
    def extract_balanced_object_text(self, text, start_index):

        """
        按花括号层级提取 JSON 风格对象文本。

        :param text: 原始文本。
        :type text: str
        :param start_index: 起始花括号下标。
        :type start_index: int
        :return: 对象文本。
        :rtype: str
        """

        # 初始化花括号层级。
        depth = 0

        # 初始化字符串状态。
        in_string = False

        # 初始化转义字符状态。
        escaped = False

        # 遍历起始位置之后的全部字符。
        for current_index in range(start_index, len(text)):

            # 读取当前字符。
            char = text[current_index]

            # 处理字符串内的转义字符。
            if escaped:

                # 清除转义状态。
                escaped = False

                # 继续读取下一个字符。
                continue

            # 处理转义字符。
            if char == "\\":

                # 标记下一字符为转义字符。
                escaped = True

                # 继续读取下一个字符。
                continue

            # 处理字符串边界。
            if char == '"':

                # 切换字符串状态。
                in_string = not in_string

                # 继续读取下一个字符。
                continue

            # 跳过字符串内的结构字符。
            if in_string:

                # 继续读取下一个字符。
                continue

            # 处理对象起始花括号。
            if char == "{":

                # 增加对象层级。
                depth += 1

            # 处理对象结束花括号。
            if char == "}":

                # 减少对象层级。
                depth -= 1

                # 判断对象是否闭合。
                if depth == 0:

                    # 返回完整对象文本。
                    return text[start_index:current_index + 1]

        # 返回空对象文本。
        return ""

    # 定义控件值提取方法。
    def extract_widget_value(self, html_text, widget_name):

        """
        从 FineReport 控件配置中提取默认值。

        :param html_text: 报表入口 HTML。
        :type html_text: str
        :param widget_name: 控件名称。
        :type widget_name: str
        :return: 控件默认值。
        :rtype: str
        """

        # 构建控件值匹配表达式。
        pattern = rf'"widgetName"\s*:\s*"{re.escape(widget_name)}".{{0,1200}}?"value"\s*:\s*"([^"]*)"'

        # 查找控件值。
        matched = re.search(pattern, html_text, re.S)

        # 判断控件值是否存在。
        if matched:

            # 返回控件值文本。
            return matched.group(1)

        # 返回空字符串。
        return ""

    # 定义报表会话编号提取方法。
    def extract_report_session_id(self, html_text):

        """
        从 FineReport 入口 HTML 中提取报表会话编号。

        :param html_text: 报表入口 HTML。
        :type html_text: str
        :return: 报表会话编号。
        :rtype: str
        """

        # 查找当前会话编号。
        matched = re.search(r"currentSessionID\s*=\s*'([^']+)'", html_text)

        # 判断会话编号是否存在。
        if matched:

            # 返回会话编号。
            return matched.group(1)

        # 抛出会话缺失异常。
        raise RuntimeError(f"{self.company_name} 未能提取 FineReport 会话编号")

    # 定义查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行。
        :rtype: list[dict]
        """

        # 执行报表查询。
        query_result = self.query_hxyxt_data(data_type, start_date, end_date)

        # 返回查询结果行。
        return query_result["rows"]

    # 定义导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出指定数据类型业务数据。

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

        # 使用协议查询结果生成本地 Excel。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型业务数据并生成 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径或文件路径列表。
        :rtype: str | list[str]
        """

        # 使用当前目录作为默认输出目录。
        output_dir = output_dir or os.getcwd()

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 判断是否存在多公司代码配置。
        if self.company_code_items:

            # 初始化多公司输出路径。
            output_paths = []

            # 遍历公司代码配置。
            for company_code_item in self.company_code_items:

                # 应用当前公司代码配置。
                self.apply_company_code_item(company_code_item)

                # 执行当前公司代码报表查询。
                query_result = self.query_hxyxt_data(data_type, start_date, end_date)

                # 写入当前公司代码 Excel。
                output_path = self.write_query_result_to_excel(data_type, query_result, output_dir)

                # 保存当前公司代码输出路径。
                output_paths.append(output_path)

            # 返回多公司代码输出路径。
            return output_paths

        # 执行单公司代码报表查询。
        query_result = self.query_hxyxt_data(data_type, start_date, end_date)

        # 写入单公司代码 Excel。
        output_path = self.write_query_result_to_excel(data_type, query_result, output_dir)

        # 返回单公司代码输出路径。
        return output_path

    # 定义公司代码配置应用方法。
    def apply_company_code_item(self, company_code_item):

        """
        应用当前查询批次的公司代码配置。

        :param company_code_item: 公司代码配置。
        :type company_code_item: dict
        :return: None。
        :rtype: None
        """

        # 读取公司代码。
        self.company_code = str(company_code_item.get("公司代码", company_code_item.get("代码", "")))

        # 读取公司代码名称。
        self.company_code_name = str(company_code_item.get("公司代码名称", company_code_item.get("名称", "")))

        # 保存当前公司代码名称。
        self.current_company_code_name = self.company_code_name

        # 读取当前公司代码商品参数。
        item_list_value = company_code_item.get("商品列表参数", self.default_item_list_value)

        # 保存当前商品列表参数。
        self.item_list_value = str(item_list_value)

    # 定义查询结果 Excel 写入方法。
    def write_query_result_to_excel(self, data_type, query_result, output_dir):

        """
        将查询结果写入公司代码对应的 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_result: 查询结果。
        :type query_result: dict
        :param output_dir: 输出目录。
        :type output_dir: str
        :return: Excel 文件路径。
        :rtype: str
        """

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 构建输出文件路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(data_type, query_result["headers"], query_result["rows"], output_path)

        # 应用统一 Excel 样式。
        apply_standard_excel_style(output_path)

        # 打印 Excel 生成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date=None, end_date=None):

        """
        构建一心堂 SRM 标准输出文件名。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 输出文件名。
        :rtype: str
        """

        # 调用基类构建标准文件名。
        file_name = super().build_output_file_name(data_type, start_date, end_date)

        # 构建当前公司代码名称标记。
        company_marker = self.build_company_name_marker()

        # 判断是否存在公司代码名称标记。
        if not company_marker:

            # 返回标准文件名。
            return file_name

        # 构建商业名称前缀。
        company_prefix = f"「DDI」{self.company_name}"

        # 判断标准文件名是否包含商业名称前缀。
        if file_name.startswith(company_prefix):

            # 在商业名称与日期之间插入公司代码名称标记。
            return f"{company_prefix}{company_marker}{file_name[len(company_prefix):]}"

        # 拆分文件名主体和扩展名。
        file_stem, file_ext = os.path.splitext(file_name)

        # 返回兜底公司代码名称标记文件名。
        return f"{file_stem}{company_marker}{file_ext}"

    # 定义公司名称标记构建方法。
    def build_company_name_marker(self):

        """
        构建当前公司代码对应的文件名标记。

        :return: 文件名标记。
        :rtype: str
        """

        # 判断文件名公司代码标记是否启用。
        if not self.company_name_marker_enabled:

            # 返回空标记。
            return ""

        # 读取当前公司代码名称。
        company_name = self.current_company_code_name or self.company_code_name

        # 判断公司代码名称是否存在。
        if not company_name:

            # 返回空标记。
            return ""

        # 清理文件名非法字符。
        safe_company_name = re.sub(r'[\\/:*?"<>|]+', "_", company_name).strip()

        # 判断清理后的公司代码名称是否存在。
        if not safe_company_name:

            # 返回空标记。
            return ""

        # 返回下划线公司名称标记。
        return f"_{safe_company_name}"

    # 定义报表查询方法。
    def query_hxyxt_data(self, data_type, start_date, end_date):

        """
        查询一心堂 FineReport 供应商流向数据。

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

        # 确保当前会话已登录。
        self.ensure_login()

        # 解析查询日期范围。
        start_date, end_date = self.resolve_query_dates(start_date, end_date)

        # 校验查询日期跨度。
        self.validate_query_range(start_date, end_date)

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 提交 FineReport 参数。
        self.submit_report_parameters(start_date, end_date)

        # 读取全部分页行。
        headers, rows = self.fetch_all_page_rows()

        # 校验结果日期范围。
        self.validate_result_date_range(rows, start_date, end_date)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("供应商流向解析完成", "FineReport", "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果。
        return {"headers": headers, "rows": rows, "start_date": start_date, "end_date": end_date}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验一心堂支持的数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否为配送流向。
        if data_type == "配送流向":

            # 配送流向直接返回。
            return

        # 抛出不支持的数据类型异常。
        raise ValueError(f"{self.company_name} 仅支持 配送流向，当前数据类型：{data_type}")

    # 定义登录状态确认方法。
    def ensure_login(self):

        """
        确保当前协议会话已经登录。

        :return: None。
        :rtype: None
        """

        # 判断当前是否已经登录。
        if self.logged_in:

            # 已登录时直接返回。
            return

        # 执行登录流程。
        self.login()

    # 定义日期范围解析方法。
    def resolve_query_dates(self, start_date, end_date):

        """
        解析查询日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 读取当前日期。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 返回补齐后的日期范围。
        return start_date or today_text, end_date or today_text

    # 定义查询跨度校验方法。
    def validate_query_range(self, start_date, end_date):

        """
        校验查询日期范围。

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

        # 判断结束日期是否早于开始日期。
        if end_value < start_value:

            # 抛出日期范围异常。
            raise ValueError(f"{self.company_name} 查询结束日期不能早于开始日期：{start_date} ~ {end_date}")

        # 判断日期跨度是否超过平台限制。
        if (end_value - start_value).days > self.max_query_days:

            # 抛出日期跨度异常。
            raise ValueError(f"{self.company_name} 查询日期跨度超过 {self.max_query_days} 天：{start_date} ~ {end_date}")

    # 定义查询分段日志方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印查询阶段分隔线。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印数据类型查询分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan"), self.ph.kv("公司代码", self.company_code, "cyan"), self.ph.kv("公司名称", self.current_company_code_name, "cyan")))

    # 定义报表参数提交方法。
    def submit_report_parameters(self, start_date, end_date):

        """
        提交 FineReport 供应商流向报表参数。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: dict
        :rtype: dict
        """

        # 构建参数提交地址。
        url = f"{self.site_root_url}{self.decision_path}/view/report?op=fr_dialog&cmd=parameters_d&sessionID={self.report_session_id}"

        # 构建参数字典。
        parameters = self.build_report_parameters(start_date, end_date)

        # 构建表单请求体。
        data = urlencode({"__parameters__": json.dumps(parameters, ensure_ascii=False, separators=(",", ":")), "_": str(int(time.time() * 1000))}).encode("utf-8")

        # 构建请求头。
        headers = self.build_form_headers(self.build_report_entry_url(), session_id=self.report_session_id)

        # 发送参数提交请求。
        response_body = self.request_bytes("POST", url, headers=headers, data=data)

        # 解析响应数据。
        response_data = json.loads(response_body.decode("utf-8", errors="replace"))

        # 校验参数提交状态。
        if str(response_data.get("status", "")).lower() != "success":

            # 抛出参数提交异常。
            raise RuntimeError(f"{self.company_name} FineReport 参数提交失败：{response_data}")

        # 打印参数提交日志。
        self.ph.info(self.ph.join(self.ph.kv("报表参数", "提交成功", "green"), self.ph.kv("供应商参数", self.supplier_user_id, "cyan"), self.ph.kv("商品参数", self.item_list_value, "cyan")))

        # 返回响应数据。
        return response_data

    # 定义报表参数构建方法。
    def build_report_parameters(self, start_date, end_date):

        """
        构建 FineReport 供应商流向报表参数。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 报表参数。
        :rtype: dict
        """

        # 构建参数字典。
        parameters = {"公司代码": self.company_code, "开始日期": start_date, "结束日期": end_date, "ITEMLIST": self.item_list_value, "FR_USERNAME1": self.supplier_user_id}

        # 返回报表参数。
        return parameters

    # 定义全分页读取方法。
    def fetch_all_page_rows(self):

        """
        读取 FineReport 全部分页数据。

        :return: 表头和数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化当前页码。
        page_number = 1

        # 初始化总页数。
        total_pages = 1

        # 初始化合并表头。
        merged_headers = []

        # 初始化合并行数据。
        merged_rows = []

        # 构建 FineReport 客户端标识。
        client_id = self.build_client_id()

        # 循环读取全部分页。
        while page_number <= total_pages:

            # 读取当前页响应。
            response_data = self.fetch_page_content(page_number, client_id)

            # 读取当前页 HTML。
            html_text = response_data.get("html", "")

            # 解析当前总页数。
            total_pages = max(total_pages, self.extract_total_pages(html_text))

            # 解析当前页表格。
            table_rows = self.parse_report_html(html_text)

            # 构建当前页行数据。
            page_headers, page_rows = self.build_rows_from_table(table_rows)

            # 合并当前页行数据。
            merged_headers, merged_rows = self.merge_page_rows(merged_headers, merged_rows, page_headers, page_rows)

            # 打印分页读取日志。
            self.ph.info(self.ph.join(self.ph.kv("当前页", f"{page_number}/{total_pages}", "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan"), self.ph.kv("累计记录", len(merged_rows), "cyan")))

            # 页码递增。
            page_number += 1

        # 判断最终表头是否为空。
        if not merged_headers:

            # 使用默认表头兜底。
            merged_headers = list(HXYXT_FLOW_HEADERS)

        # 返回表头和行数据。
        return merged_headers, merged_rows

    # 定义单页内容读取方法。
    def fetch_page_content(self, page_number, client_id):

        """
        读取指定页码的 FineReport 页面内容。

        :param page_number: 页码。
        :type page_number: int
        :param client_id: FineReport 客户端标识。
        :type client_id: str
        :return: 页面内容响应。
        :rtype: dict
        """

        # 构建页面内容地址。
        url = (
            f"{self.site_root_url}{self.decision_path}/view/report?_={int(time.time() * 1000)}"
            f"&__boxModel__=true&op=page_content&sessionID={self.report_session_id}"
            f"&pn={page_number}&cid={quote(client_id)}&__webpage__=true"
            f"&_paperWidth={self.paper_width}&_paperHeight={self.paper_height}&__fit__=false"
        )

        # 构建请求头。
        headers = self.build_ajax_headers(self.build_report_entry_url(), session_id=self.report_session_id)

        # 读取响应体。
        response_body = self.get_bytes(url, headers=headers, timeout=180)

        # 解码响应文本。
        response_text = response_body.decode("utf-8", errors="replace")

        # 判断响应是否为 JSON。
        if response_text.lstrip().startswith("{"):

            # 返回 JSON 响应。
            return json.loads(response_text)

        # 抛出页面内容异常。
        raise RuntimeError(f"{self.company_name} FineReport 页面内容返回异常：{response_text[:120]}")

    # 定义 FineReport 客户端标识构建方法。
    def build_client_id(self):

        """
        构建 FineReport 浏览器并发校验使用的客户端标识。

        :return: 客户端标识。
        :rtype: str
        """

        # 读取固定指纹前缀。
        fingerprint_value = self.account.get("浏览器指纹", "feaee063741cb2a767189cd7bbccfe342")

        # 读取毫秒时间戳。
        timestamp_text = str(int(time.time() * 1000))

        # 拼接校验基础文本。
        base_text = f"{fingerprint_value}#{timestamp_text}"

        # 计算校验位。
        checksum_text = hashlib.md5(base_text.encode("utf-8")).hexdigest()[-8:]

        # 返回 FineReport 客户端标识。
        return f"{base_text}#{checksum_text}"

    # 定义总页数解析方法。
    def extract_total_pages(self, html_text):

        """
        从 FineReport HTML 中提取总页数。

        :param html_text: 页面 HTML。
        :type html_text: str
        :return: 总页数。
        :rtype: int
        """

        # 查找总页数字段。
        matched = re.search(r"reportTotalPage\s*=\s*(\d+)", str(html_text or ""))

        # 判断总页数字段是否存在。
        if matched:

            # 返回解析后的总页数。
            return int(matched.group(1))

        # 返回默认总页数。
        return 1

    # 定义 HTML 表格解析方法。
    def parse_report_html(self, html_text):

        """
        解析 FineReport 页面表格 HTML。

        :param html_text: 页面 HTML。
        :type html_text: str
        :return: 表格行数组。
        :rtype: list[list[str]]
        """

        # 创建 FineReport 表格解析器。
        parser = FineReportTableParser()

        # 输入 HTML 文本。
        parser.feed(html_text or "")

        # 返回解析后的表格行。
        return parser.rows

    # 定义表格行转换方法。
    def build_rows_from_table(self, table_rows):

        """
        将 FineReport 表格行转换为字典行。

        :param table_rows: 表格行数组。
        :type table_rows: list[list[str]]
        :return: 当前页表头和数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 判断表格行是否为空。
        if not table_rows:

            # 返回默认表头和空行。
            return list(HXYXT_FLOW_HEADERS), []

        # 提取表头行。
        headers = [cell for cell in table_rows[0] if str(cell).strip()]

        # 初始化结果行集合。
        rows = []

        # 遍历数据行。
        for row_values in table_rows[1:]:

            # 标准化当前行。
            normalized_values = self.normalize_row_values(headers, row_values)

            # 判断当前行是否为有效明细行。
            if not self.is_detail_row(headers, normalized_values):

                # 非明细行进入下一行。
                continue

            # 构建当前行字典。
            row_data = {headers[index]: normalized_values[index] if index < len(normalized_values) else "" for index in range(len(headers))}

            # 追加当前行。
            rows.append(row_data)

        # 返回表头和行集合。
        return headers, rows

    # 定义行值标准化方法。
    def normalize_row_values(self, headers, row_values):

        """
        标准化 FineReport 数据行长度。

        :param headers: 表头列表。
        :type headers: list[str]
        :param row_values: 原始行值。
        :type row_values: list[str]
        :return: 标准化后的行值。
        :rtype: list[str]
        """

        # 转换当前行值为字符串列表。
        values = [str(value or "").strip() for value in row_values]

        # 判断当前行是否包含冻结表左上角空单元格。
        if len(values) == len(headers) + 1 and not values[0]:

            # 移除冻结表左上角空单元格。
            values = values[1:]

        # 判断当前行是否缺少序号列。
        if len(values) == len(headers) - 1 and headers and headers[0] == "序号":

            # 使用当前第一列作为序号列对齐。
            values = values

        # 返回标准化行值。
        return values

    # 定义明细行判断方法。
    def is_detail_row(self, headers, values):

        """
        判断当前表格行是否为有效明细行。

        :param headers: 表头列表。
        :type headers: list[str]
        :param values: 标准化后的行值。
        :type values: list[str]
        :return: 是否为明细行。
        :rtype: bool
        """

        # 判断当前行是否为空。
        if not any(values):

            # 空行不是明细。
            return False

        # 判断当前行是否为合计行。
        if any(str(value).strip() == "合计" for value in values):

            # 合计行不是明细。
            return False

        # 判断日期字段是否存在于表头。
        if self.date_column not in headers:

            # 日期字段缺失时保留文本行。
            return True

        # 读取日期字段下标。
        date_index = headers.index(self.date_column)

        # 判断日期字段是否超出当前行长度。
        if date_index >= len(values):

            # 日期字段缺失时不是明细。
            return False

        # 返回日期字段是否符合明细日期格式。
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", values[date_index]))

    # 定义分页合并方法。
    def merge_page_rows(self, merged_headers, merged_rows, page_headers, page_rows):

        """
        合并分页表头和数据行。

        :param merged_headers: 已合并表头。
        :type merged_headers: list[str]
        :param merged_rows: 已合并数据行。
        :type merged_rows: list[dict]
        :param page_headers: 当前页表头。
        :type page_headers: list[str]
        :param page_rows: 当前页数据行。
        :type page_rows: list[dict]
        :return: 合并后的表头和数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化当前表头。
        current_headers = list(merged_headers)

        # 遍历当前页表头。
        for header_name in page_headers:

            # 判断表头是否已存在。
            if header_name in current_headers:

                # 已存在时进入下一项。
                continue

            # 追加新表头。
            current_headers.append(header_name)

        # 初始化标准化数据行。
        normalized_rows = []

        # 遍历已合并数据行。
        for row_data in merged_rows:

            # 按当前表头重建历史行。
            normalized_rows.append({header_name: row_data.get(header_name, "") for header_name in current_headers})

        # 遍历当前页数据行。
        for row_data in page_rows:

            # 按当前表头重建当前行。
            normalized_rows.append({header_name: row_data.get(header_name, "") for header_name in current_headers})

        # 返回合并结果。
        return current_headers, normalized_rows

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, rows, start_date, end_date):

        """
        校验结果业务日期范围。

        :param rows: 查询结果行。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 判断结果是否为空。
        if not rows:

            # 空结果不做日期范围校验。
            return

        # 初始化日期集合。
        result_dates = []

        # 遍历全部结果行。
        for row_data in rows:

            # 读取日期文本。
            date_text = str(row_data.get(self.date_column, "")).strip()

            # 判断日期文本是否为空。
            if not date_text:

                # 空日期进入下一行。
                continue

            # 解析结果日期。
            result_dates.append(datetime.strptime(date_text, "%Y-%m-%d"))

        # 判断日期集合是否为空。
        if not result_dates:

            # 无可校验日期时直接返回。
            return

        # 解析开始日期。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 读取最小业务日期。
        min_date = min(result_dates)

        # 读取最大业务日期。
        max_date = max(result_dates)

        # 判断结果日期是否越界。
        if min_date < start_value or max_date > end_value:

            # 抛出日期越界异常。
            raise RuntimeError(f"{self.company_name} 配送流向结果日期超出查询范围：{min_date:%Y-%m-%d} ~ {max_date:%Y-%m-%d}")

        # 打印日期范围校验日志。
        self.ph.info(self.ph.join(self.ph.kv("结果日期最小值", min_date.strftime("%Y-%m-%d"), "cyan"), self.ph.kv("结果日期最大值", max_date.strftime("%Y-%m-%d"), "cyan")))

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, data_type, headers, rows, target_path):

        """
        将查询结果写入 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param headers: 表头列表。
        :type headers: list[str]
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param target_path: 输出文件路径。
        :type target_path: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 导入列号转换函数。
        from openpyxl.utils import get_column_letter

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type[:31]

        # 写入表头。
        worksheet.append(headers)

        # 遍历结果行。
        for row_data in rows:

            # 写入当前行。
            worksheet.append([row_data.get(header_name, "") for header_name in headers])

        # 遍历表头设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

            # 计算当前列显示宽度。
            width = max([len(str(header_name))] + [len(str(row_data.get(header_name, ""))) for row_data in rows[:200]])

            # 设置当前列宽。
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(width + 2, 10), 45)

        # 保存 Excel 文件。
        workbook.save(target_path)

        # 关闭 Excel 工作簿。
        workbook.close()

    # 定义 JSON GET 请求方法。
    def get_json(self, url, headers=None):

        """
        发送 GET 请求并解析 JSON。

        :param url: 请求地址。
        :type url: str
        :param headers: 请求头。
        :type headers: dict | None
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 读取响应字节。
        response_body = self.get_bytes(url, headers=headers)

        # 返回 JSON 数据。
        return json.loads(response_body.decode("utf-8", errors="replace"))

    # 定义 JSON POST 请求方法。
    def post_json(self, url, payload, referer=None):

        """
        发送 JSON POST 请求。

        :param url: 请求地址。
        :type url: str
        :param payload: 请求体对象。
        :type payload: dict
        :param referer: 来源地址。
        :type referer: str | None
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 编码请求体。
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 构建请求头。
        headers = self.build_json_headers(referer or self.site_root_url)

        # 发送请求。
        response_body = self.request_bytes("POST", url, headers=headers, data=data)

        # 返回 JSON 响应。
        return json.loads(response_body.decode("utf-8", errors="replace"))

    # 定义 GET 字节请求方法。
    def get_bytes(self, url, headers=None, timeout=60):

        """
        发送 GET 请求并返回字节响应。

        :param url: 请求地址。
        :type url: str
        :param headers: 请求头。
        :type headers: dict | None
        :param timeout: 超时时间。
        :type timeout: int
        :return: 响应字节。
        :rtype: bytes
        """

        # 返回 GET 响应体。
        return self.request_bytes("GET", url, headers=headers or {}, timeout=timeout)

    # 定义底层字节请求方法。
    def request_bytes(self, method, url, headers=None, data=None, timeout=60):

        """
        发送底层 HTTP 请求并返回响应字节。

        :param method: 请求方法。
        :type method: str
        :param url: 请求地址。
        :type url: str
        :param headers: 请求头。
        :type headers: dict | None
        :param data: 请求体。
        :type data: bytes | None
        :param timeout: 超时时间。
        :type timeout: int
        :return: 响应字节。
        :rtype: bytes
        """

        # 构建请求对象。
        request = Request(url, data=data, headers=headers or {}, method=method)

        try:

            # 发送请求并读取响应。
            with self.opener.open(request, timeout=timeout) as response:

                # 返回响应字节。
                return response.read()

        except HTTPError as error:

            # 读取错误响应。
            error_body = error.read().decode("utf-8", errors="replace")

            # 抛出 HTTP 错误。
            raise RuntimeError(f"{self.company_name} HTTP {error.code}：{url}：{error_body[:200]}") from error

    # 定义报表入口地址构建方法。
    def build_report_entry_url(self):

        """
        构建 FineReport 入口绝对地址。

        :return: FineReport 入口地址。
        :rtype: str
        """

        # 返回报表入口绝对地址。
        return f"{self.site_root_url}{self.report_entry_path}"

    # 定义 HTML 请求头构建方法。
    def build_html_headers(self, referer):

        """
        构建 HTML 请求头。

        :param referer: 来源地址。
        :type referer: str
        :return: 请求头。
        :rtype: dict
        """

        # 返回 HTML 请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Referer": referer, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"}

    # 定义 JSON 请求头构建方法。
    def build_json_headers(self, referer):

        """
        构建 JSON 请求头。

        :param referer: 来源地址。
        :type referer: str
        :return: 请求头。
        :rtype: dict
        """

        # 返回 JSON 请求头。
        return {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Content-Type": "application/json", "Origin": self.site_root_url, "Referer": referer, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"}

    # 定义令牌请求头构建方法。
    def build_token_headers(self, referer):

        """
        构建带 SRM 令牌的请求头。

        :param referer: 来源地址。
        :type referer: str
        :return: 请求头。
        :rtype: dict
        """

        # 构建基础请求头。
        headers = self.build_html_headers(referer)

        # 写入 Authorization 请求头。
        headers["Authorization"] = f"Bearer {self.access_token}"

        # 写入 X-Access-Token 请求头。
        headers["X-Access-Token"] = self.access_token

        # 返回请求头。
        return headers

    # 定义表单请求头构建方法。
    def build_form_headers(self, referer, session_id=None):

        """
        构建表单请求头。

        :param referer: 来源地址。
        :type referer: str
        :param session_id: FineReport 会话编号。
        :type session_id: str | None
        :return: 请求头。
        :rtype: dict
        """

        # 构建基础请求头。
        headers = self.build_token_headers(referer)

        # 写入表单内容类型。
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        # 写入 AJAX 标识。
        headers["X-Requested-With"] = "XMLHttpRequest"

        # 写入会话请求头。
        if session_id:

            # 保存 FineReport 会话编号。
            headers["sessionID"] = session_id

        # 返回请求头。
        return headers

    # 定义 AJAX 请求头构建方法。
    def build_ajax_headers(self, referer, session_id=None):

        """
        构建 FineReport AJAX 请求头。

        :param referer: 来源地址。
        :type referer: str
        :param session_id: FineReport 会话编号。
        :type session_id: str | None
        :return: 请求头。
        :rtype: dict
        """

        # 构建基础请求头。
        headers = self.build_token_headers(referer)

        # 写入 AJAX 接收类型。
        headers["Accept"] = "text/html, */*; q=0.01"

        # 写入 AJAX 标识。
        headers["X-Requested-With"] = "XMLHttpRequest"

        # 写入会话请求头。
        if session_id:

            # 保存 FineReport 会话编号。
            headers["sessionID"] = session_id

        # 返回请求头。
        return headers
