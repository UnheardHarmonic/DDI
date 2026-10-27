# -*- coding: utf-8 -*-
"""
协议请求客户端。

本模块封装 Cookie 自动维护、请求头构造、表单请求和 JSON 请求等通用 HTTP 能力。
"""

# 导入 JSON 编解码模块。
import json

# 导入 Cookie 容器。
from http.cookiejar import CookieJar

# 导入数据类装饰器。
from dataclasses import dataclass

# 导入类型标注。
from typing import Any, Dict, Optional

# 导入 HTTP 异常对象。
from urllib.error import HTTPError, URLError

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入标准库请求对象。
from urllib.request import HTTPCookieProcessor, Request, build_opener


@dataclass
class HttpResult:
    """
    HTTP 响应结果。

    :param status_code: HTTP 状态码。
    :type status_code: int
    :param headers: 响应头字典。
    :type headers: Dict[str, str]
    :param body: 响应体字节数据。
    :type body: bytes
    :return: HTTP 响应结果实例。
    :rtype: HttpResult
    """

    # 保存 HTTP 状态码。
    status_code: int

    # 保存响应头字段。
    headers: Dict[str, str]

    # 保存响应体字节数据。
    body: bytes


class ProtocolHttpClient:
    """
    带 Cookie 管理的协议请求客户端。

    :param base_url: 平台根地址。
    :type base_url: str
    :return: 协议请求客户端实例。
    :rtype: ProtocolHttpClient
    """

    def __init__(self, base_url):
        """
        初始化协议请求客户端。

        :param base_url: 平台根地址。
        :type base_url: str
        :return: None。
        :rtype: None
        """

        # 保存平台根地址。
        self.base_url = base_url.rstrip("/")

        # 初始化 Cookie 容器。
        self.cookie_jar = CookieJar()

        # 初始化带 Cookie 管理的 opener。
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def request(self, method, url, headers, data=None, timeout=30, allow_http_error=False):
        """
        发送 HTTP 请求。

        :param method: HTTP 请求方法。
        :type method: str
        :param url: 请求地址。
        :type url: str
        :param headers: 请求头字典。
        :type headers: Dict[str, str]
        :param data: 请求体字节数据。
        :type data: Optional[bytes]
        :param timeout: 请求超时秒数。
        :type timeout: int
        :param allow_http_error: 是否将 HTTP 错误响应作为结果返回。
        :type allow_http_error: bool
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建标准库请求对象。
        request = Request(url=url, data=data, headers=headers, method=method)

        try:
            # 发送请求并读取响应。
            with self.opener.open(request, timeout=timeout) as response:
                # 读取响应体。
                body = response.read()

                # 返回响应结果。
                return HttpResult(response.status, dict(response.headers.items()), body)

        except HTTPError as error:
            # 读取错误响应体。
            body = error.read()

            # 判断调用方需要解析 HTTP 错误响应正文。
            if allow_http_error:

                # 返回保留状态码和错误正文的响应结果。
                return HttpResult(error.code, dict(error.headers.items()) if error.headers else {}, body)

            # 抛出包含响应内容的异常。
            raise RuntimeError(f"HTTP {error.code} 请求失败：{url}，响应：{body[:500]!r}") from error

        except URLError as error:
            # 抛出网络异常。
            raise RuntimeError(f"网络请求失败：{url}，原因：{error.reason}") from error

    def get(self, url, referer=None):
        """
        发送浏览器 GET 请求。

        :param url: 请求地址。
        :type url: str
        :param referer: 来源页面地址。
        :type referer: Optional[str]
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建浏览器请求头。
        headers = self.browser_headers(referer or self.base_url)

        # 发送 GET 请求。
        return self.request("GET", url, headers=headers)

    def post_form(self, url, payload, referer):
        """
        发送表单 POST 请求。

        :param url: 请求地址。
        :type url: str
        :param payload: 表单字段字典。
        :type payload: Dict[str, Any]
        :param referer: 来源页面地址。
        :type referer: str
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建 AJAX 表单请求头。
        headers = self.ajax_form_headers(referer)

        # 编码表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送 POST 请求。
        return self.request("POST", url, headers=headers, data=data)

    def post_json(self, url, payload, referer):
        """
        发送 JSON POST 请求。

        :param url: 请求地址。
        :type url: str
        :param payload: JSON 字段字典。
        :type payload: Dict[str, Any]
        :param referer: 来源页面地址。
        :type referer: str
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建 JSON 请求头。
        headers = self.json_headers(referer)

        # 编码 JSON 请求体。
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 发送 POST 请求。
        return self.request("POST", url, headers=headers, data=data)

    def decode_json(self, result):
        """
        解析 JSON 响应体。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: JSON 字典。
        :rtype: Dict[str, Any]
        """

        # 解码响应体文本。
        text = result.body.decode("utf-8", errors="replace")

        # 返回 JSON 解析结果。
        return json.loads(text)

    def export_cookie_header(self):
        """
        导出当前 Cookie 请求头。

        :return: Cookie 请求头字符串。
        :rtype: str
        """

        # 拼接 Cookie 键值对。
        return "; ".join([f"{cookie.name}={cookie.value}" for cookie in self.cookie_jar])

    def save_cookie_file(self, file_path):
        """
        保存 Cookie 到 JSON 文件。

        :param file_path: 输出文件路径。
        :type file_path: str
        :return: None。
        :rtype: None
        """

        # 构建 Cookie 列表。
        cookies = [{"name": cookie.name, "value": cookie.value, "domain": cookie.domain, "path": cookie.path, "expires": cookie.expires} for cookie in self.cookie_jar]

        # 写入 Cookie 文件。
        with open(file_path, "w", encoding="utf-8") as file_obj:
            json.dump(cookies, file_obj, ensure_ascii=False, indent=2)

    def browser_headers(self, referer):
        """
        构建浏览器基础请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: Dict[str, str]
        """

        # 返回浏览器基础请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": referer, "User-Agent": self.user_agent()}

    def ajax_form_headers(self, referer):
        """
        构建 AJAX 表单请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: Dict[str, str]
        """

        # 返回 AJAX 表单请求头。
        return {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": self.base_url, "Referer": referer, "User-Agent": self.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    def json_headers(self, referer):
        """
        构建 JSON 请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: Dict[str, str]
        """

        # 返回 JSON 请求头。
        return {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/json;charset=UTF-8", "Origin": self.base_url, "Referer": referer, "User-Agent": self.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    def user_agent(self):
        """
        返回浏览器 User-Agent。

        :return: User-Agent 字符串。
        :rtype: str
        """

        # 返回 Edge 浏览器 User-Agent。
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
