# -*- coding: utf-8 -*-
"""
FineReport 平台公共骨架。

本模块沉淀 FineReport 系平台共享的表格解析器、报表行组装、分页合并、
FineDecision 登录三元组（加密配置提取、登录体构建、JSON 登录提交）以及
FineDecision 会话与请求头能力；商业专属的报表定义、字段契约与入口定位
由各平台适配器自行维护。
"""

# 导入 JSON 编解码模块。
import json

# 导入正则表达式模块。
import re

# 导入 Cookie 对象。
from http.cookiejar import Cookie

# 导入 HTML 解析器基类。
from html.parser import HTMLParser

# 导入 URL 解析函数。
from urllib.parse import urlparse

# 导入平台适配器基类。
from ddi_framework.platforms.base import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入通用 AES-ECB 加密函数。
from ddi_framework.reverse_utils import aes_ecb_pkcs7_base64

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


# 定义 FineReport 平台公共基类。
class FineReportPlatformBase(BasePlatform):

    """
    FineReport 系平台公共会话骨架。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :param api_root_default: 接口根地址缺省值。
    :type api_root_default: str
    :param decision_path_default: FineDecision 应用路径缺省值。
    :type decision_path_default: str
    :return: 平台适配器实例。
    :rtype: FineReportPlatformBase
    """

    # 定义平台初始化方法。
    def __init__(self, company_name, account, printer=None, api_root_default="", decision_path_default="/WebReport/decision"):

        """
        初始化 FineReport 平台公共会话。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param account: 商业账号配置。
        :type account: dict
        :param printer: 日志打印器。
        :type printer: PrintHandler | None
        :param api_root_default: 接口根地址缺省值。
        :type api_root_default: str
        :param decision_path_default: FineDecision 应用路径缺省值。
        :type decision_path_default: str
        :return: None。
        :rtype: None
        """

        # 调用平台基类初始化逻辑。
        super().__init__(company_name, account, printer=printer)

        # 初始化日志打印器。
        self.ph = printer or PrintHandler()

        # 保存接口根地址。
        self.api_base_url = account.get("接口根地址", api_root_default).rstrip("/")

        # 保存 FineDecision 应用路径。
        self.decision_path = account.get("应用路径", decision_path_default)

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.api_base_url}{self.decision_path}/login")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", self.login_page_url)

        # 保存平台源地址。
        self.origin_url = self.build_origin(self.api_base_url)

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 初始化登录令牌。
        self.access_token = ""

        # 初始化登录状态。
        self.logged_in = False


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

        # 调用通用 AES-ECB-PKCS7 加密能力。
        return aes_ecb_pkcs7_base64(plain_text, secret_key)

    def extract_cipher_config(self, login_html):
        """
        从登录页提取 FineDecision 前端加密配置。

        :param login_html: 登录页 HTML 文本。
        :type login_html: str
        :return: 前端加密配置。
        :rtype: dict
        :raises RuntimeError: 登录页缺少加密配置或 frontSeed 时抛出。
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

    def extract_total_pages(self, html_text):
        """
        从报表页面 HTML 中提取总页数。

        :param html_text: 报表页面 HTML 文本。
        :type html_text: str
        :return: 总页数。
        :rtype: int
        """

        # 查找总页数字段。
        matched = re.search(r"reportTotalPage=(\d+)", str(html_text or ""))

        # 判断总页数字段是否存在。
        if not matched:

            # 不存在时返回默认单页值。
            return 1

        # 返回解析后的总页数。
        return int(matched.group(1))

    def merge_page_rows(self, merged_headers, merged_rows, page_headers, page_rows):
        """
        合并分页返回的表头与数据行。

        :param merged_headers: 已合并表头。
        :type merged_headers: list[str]
        :param merged_rows: 已合并数据行。
        :type merged_rows: list[dict]
        :param page_headers: 当前页表头。
        :type page_headers: list[str]
        :param page_rows: 当前页数据行。
        :type page_rows: list[dict]
        :return: 合并后的表头与数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化当前合并表头副本。
        current_headers = list(merged_headers)

        # 遍历当前页表头。
        for header_name in page_headers:

            # 判断当前字段是否已存在于合并表头。
            if header_name in current_headers:

                # 已存在时进入下一项表头。
                continue

            # 将新字段追加到合并表头末尾。
            current_headers.append(header_name)

        # 初始化合并后数据行集合。
        normalized_rows = []

        # 遍历历史数据行。
        for row in merged_rows:

            # 按最新合并表头重建历史数据行。
            normalized_rows.append({header_name: row.get(header_name, "") for header_name in current_headers})

        # 遍历当前页数据行。
        for row in page_rows:

            # 按最新合并表头重建当前页数据行。
            normalized_rows.append({header_name: row.get(header_name, "") for header_name in current_headers})

        # 返回合并后的表头与数据行。
        return current_headers, normalized_rows
