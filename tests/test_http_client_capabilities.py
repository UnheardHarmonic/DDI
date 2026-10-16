# -*- coding: utf-8 -*-
"""协议请求客户端能力扩展测试。

覆盖自定义 TLS 上下文注入与请求级禁用重定向两类会话能力。
"""

# 导入套接字服务器模块。
import socketserver

# 导入 HTTP 服务器模块。
import threading

# 导入单元测试框架。
import unittest

# 导入 HTTP 服务基类。
from http.server import BaseHTTPRequestHandler, HTTPServer

# 导入协议请求客户端。
from ddi_framework.http_client import ProtocolHttpClient


# 定义测试用 HTTP 请求处理器。
class _ProbeHandler(BaseHTTPRequestHandler):

    """
    返回可控行为的本地探针响应。

    :return: 探针处理器实例。
    :rtype: _ProbeHandler
    """

    # 关闭标准库日志噪声。
    def log_message(self, format, *args):

        """
        静默探针请求日志。

        :param format: 日志格式。
        :type format: str
        :param args: 日志参数。
        :type args: tuple
        :return: None。
        :rtype: None
        """

        # 不输出任何日志。
        return

    # 定义 GET 响应方法。
    def do_GET(self):

        """
        处理探针 GET 请求并按路径返回响应。

        :return: None。
        :rtype: None
        """

        # 判断是否为重定向路径。
        if self.path == "/redirect":

            # 返回 302 重定向响应。
            self.send_response(302)

            # 写入重定向目标头。
            self.send_header("Location", "/final")

            # 结束响应头。
            self.end_headers()

            # 返回空响应体。
            return

        # 判断是否为最终路径。
        if self.path == "/final":

            # 返回命中最终路径的响应。
            body = b"final-page"

        # 其他路径返回通用响应。
        else:

            # 返回普通响应体。
            body = b"root-page"

        # 写入 200 响应。
        self.send_response(200)

        # 写入内容类型头。
        self.send_header("Content-Type", "text/plain")

        # 写入内容长度头。
        self.send_header("Content-Length", str(len(body)))

        # 结束响应头。
        self.end_headers()

        # 写入响应体。
        self.wfile.write(body)


# 定义协议请求客户端测试用例。
class TestProtocolHttpClientCapabilities(unittest.TestCase):

    """
    协议请求客户端扩展能力测试。

    :return: 测试用例实例。
    :rtype: TestProtocolHttpClientCapabilities
    """

    # 定义测试类初始化钩子。
    @classmethod
    def setUpClass(cls):

        """
        启动本地探针 HTTP 服务器。

        :return: None。
        :rtype: None
        """

        # 创建探针服务器。
        cls.server = HTTPServer(("127.0.0.1", 0), _ProbeHandler)

        # 记录探针地址。
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

        # 启动服务器线程。
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)

        # 开始服务。
        cls.thread.start()

    # 定义测试类清理钩子。
    @classmethod
    def tearDownClass(cls):

        """
        关闭本地探针 HTTP 服务器。

        :return: None。
        :rtype: None
        """

        # 停止服务器服务循环。
        cls.server.shutdown()

        # 关闭服务器套接字。
        cls.server.server_close()

    # 定义默认跟随重定向测试方法。
    def test_default_follows_redirect(self):

        """
        验证默认请求自动跟随重定向。

        :return: None。
        :rtype: None
        """

        # 初始化协议客户端。
        client = ProtocolHttpClient(self.base_url)

        # 发送默认 GET 请求。
        result = client.request("GET", f"{self.base_url}/redirect", {})

        # 断言跟随重定向后命中最终页面。
        self.assertEqual(result.status_code if hasattr(result, "status_code") else result.status, 200)

        # 断言响应体为最终页面。
        self.assertIn(b"final-page", result.body)

    # 定义禁用重定向测试方法。
    def test_no_redirect_returns_302(self):

        """
        验证请求级禁用重定向时保留 302 原始响应。

        :return: None。
        :rtype: None
        """

        # 初始化协议客户端。
        client = ProtocolHttpClient(self.base_url)

        # 发送禁用重定向的请求。
        result = client.request("GET", f"{self.base_url}/redirect", {}, allow_http_error=True, follow_redirects=False)

        # 断言保留 302 状态码。
        status = result.status_code if hasattr(result, "status_code") else result.status

        # 校验状态码语义。
        self.assertEqual(status, 302)

    # 定义 TLS 上下文注入测试方法。
    def test_ssl_context_injection(self):

        """
        验证自定义 TLS 上下文注入 opener 构建。

        :return: None。
        :rtype: None
        """

        # 导入 SSL 模块。
        import ssl

        # 创建默认 TLS 上下文。
        context = ssl.create_default_context()

        # 初始化带上下文的协议客户端。
        client = ProtocolHttpClient(self.base_url, ssl_context=context)

        # 断言上下文被保存。
        self.assertIs(client.ssl_context, context)

        # 发送普通 HTTP 请求验证会话可用。
        result = client.request("GET", f"{self.base_url}/", {})

        # 断言普通请求正常返回。
        self.assertIn(b"root-page", result.body)


# 运行测试入口。
if __name__ == "__main__":

    # 启动单元测试。
    unittest.main()
