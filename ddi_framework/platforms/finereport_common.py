# -*- coding: utf-8 -*-
"""
FineReport 平台公共骨架。

本模块沉淀 FineReport 系平台共享的表格解析器、FineDecision 会话与请求头能力；
商业专属的报表定义、字段契约与登录流程由各平台适配器自行维护。
"""

# 导入 JSON 编解码模块。
import json

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
