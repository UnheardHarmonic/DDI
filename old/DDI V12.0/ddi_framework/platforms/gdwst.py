# -*- coding: utf-8 -*-
"""
广东五嗣堂医药供应商查询平台协议适配器。

本模块负责广东五嗣堂医药供应商查询平台的验证码获取、协议登录、令牌保存和 Cookie 保存。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入随机数模块。
import random

# 导入时间模块。
import time

# 导入日期时间模块。
from datetime import datetime

# 导入 URL 解析函数。
from urllib.parse import urlencode, urlparse

# 导入验证码处理器。
from ddi_framework import CaptchaSolver

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义广东五嗣堂医药供应商查询平台协议适配器。
class GdwstPlatform(BasePlatform):

    """
    广东五嗣堂医药供应商查询平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 广东五嗣堂医药平台适配器实例。
    :rtype: GdwstPlatform
    """

    # 定义广东五嗣堂医药适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化广东五嗣堂医药平台适配器。

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

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", "http://219.128.255.166:14212/#/login")

        # 保存验证码接口地址。
        self.captcha_api_url = account.get("验证码接口", "http://219.128.255.166:14212/api/auth/captcha")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", "http://219.128.255.166:14212/api/auth/login")

        # 保存平台页面根地址。
        self.base_url = self.build_origin(self.login_page_url)

        # 保存报表查询接口地址。
        self.query_api_url = account.get("查询接口", f"{self.base_url}/jmreport/show")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化验证码处理器。
        self.captcha_solver = CaptchaSolver()

        # 初始化登录响应。
        self.login_result = {}

        # 初始化登录令牌。
        self.login_token = ""

        # 保存默认分页大小。
        self.page_size = int(account.get("分页大小", 100))

    # 定义广东五嗣堂医药登录方法。
    def login(self):

        """
        执行广东五嗣堂医药协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("广东五嗣堂医药登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 访问登录页以初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 执行带验证码重试的登录流程。
        return self.login_with_captcha_retry()

    # 定义带验证码重试的登录方法。
    def login_with_captcha_retry(self, max_retries=8):

        """
        使用验证码重试机制执行登录。

        :param max_retries: 最大验证码刷新次数。
        :type max_retries: int
        :return: 登录结果。
        :rtype: dict
        """

        # 初始化最后一次失败原因。
        last_error = ""

        # 循环获取验证码并提交登录。
        for retry_index in range(max_retries):

            # 打印验证码尝试日志。
            self.ph.info(self.ph.kv("图片验证码尝试", f"第 {retry_index + 1}/{max_retries} 次", "cyan"))

            # 捕获当前验证码登录异常。
            try:

                # 获取验证码上下文。
                captcha_context = self.get_captcha_context()

                # 识别验证码答案。
                captcha_code = self.solve_captcha_code(captcha_context["image_text"])

                # 打印验证码识别完成日志。
                self.ph.info(self.ph.kv("图片验证码识别完成", f"长度={len(captcha_code)}", "cyan"))

                # 构建登录请求体。
                payload = self.build_login_payload(captcha_context["uid"], captcha_code)

                # 打印正式登录请求日志。
                self.ph.info("提交正式登录请求: /api/auth/login")

                # 提交登录请求。
                result = self.post_login(payload)

                # 解析登录响应。
                login_result = self.decode_login_result(result)

                # 判断登录响应是否成功。
                if self.is_login_success(login_result):

                    # 保存登录响应。
                    self.login_result = login_result

                    # 保存登录令牌。
                    self.login_token = self.extract_login_token(login_result)

                    # 打印登录成功日志。
                    self.ph.success(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"))

                    # 返回登录响应。
                    return login_result

                # 记录登录失败原因。
                last_error = self.extract_login_message(login_result)

                # 打印验证码或登录失败日志。
                self.ph.warning("登录校验未通过，准备刷新验证码")

            # 处理验证码识别或登录提交异常。
            except Exception as error:

                # 记录当前异常原因。
                last_error = str(error)

                # 打印验证码处理失败日志。
                self.ph.warning("图片验证码识别或登录校验未通过，准备刷新验证码")

            # 最后一轮失败后跳过等待。
            if retry_index >= max_retries - 1:

                # 进入失败处理。
                continue

            # 计算失败后的等待秒数。
            delay_seconds = random.uniform(2.2, 4.4)

            # 打印等待日志。
            self.ph.wait(self.ph.kv("验证码失败后等待，预计", f"{delay_seconds:.1f} 秒", "cyan"))

            # 等待后再刷新验证码。
            time.sleep(delay_seconds)

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 登录失败：{last_error}")

    # 定义验证码上下文获取方法。
    def get_captcha_context(self):

        """
        获取登录验证码图片与验证码会话编号。

        :return: 验证码上下文字典。
        :rtype: dict
        """

        # 生成验证码会话编号。
        captcha_uid = int(time.time() * 1000)

        # 构建验证码请求参数。
        params = {"uid": captcha_uid}

        # 拼接验证码请求地址。
        request_url = f"{self.captcha_api_url}?{urlencode(params)}"

        # 打印验证码请求日志。
        self.ph.info("请求图片验证码: /api/auth/captcha")

        # 构建验证码请求头。
        headers = self.build_captcha_headers()

        # 请求验证码接口。
        result = self.http.request("GET", request_url, headers=headers)

        # 解码验证码响应文本。
        image_text = result.body.decode("utf-8", errors="replace").strip()

        # 返回验证码上下文。
        return {"uid": captcha_uid, "image_text": image_text}

    # 定义验证码请求头构建方法。
    def build_captcha_headers(self):

        """
        构建验证码请求头。

        :return: 验证码请求头。
        :rtype: dict
        """

        # 返回验证码接口请求头。
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
        }

    # 定义验证码答案识别方法。
    def solve_captcha_code(self, image_text):

        """
        识别验证码答案。

        :param image_text: 验证码图片 Data URL 文本。
        :type image_text: str
        :return: 验证码答案。
        :rtype: str
        """

        # 解码验证码图片字节。
        image_bytes = self.captcha_solver.decode_base64_image(image_text)

        # 识别验证码原始文本。
        raw_text = self.captcha_solver.solve_raw_text_image_with_ranges(image_bytes, "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

        # 清洗验证码文本。
        cleaned_text = "".join([char for char in str(raw_text or "") if char.isalnum()])

        # 校验验证码长度。
        if len(cleaned_text) < 4:

            # 抛出验证码识别异常。
            raise RuntimeError("图片验证码识别为空或长度不足")

        # 返回清洗后的验证码文本。
        return cleaned_text

    # 定义登录请求体构建方法。
    def build_login_payload(self, captcha_uid, captcha_code):

        """
        构建广东五嗣堂医药登录请求体。

        :param captcha_uid: 验证码会话编号。
        :type captcha_uid: int
        :param captcha_code: 验证码答案。
        :type captcha_code: str
        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录请求体。
        return {
            "username": self.clean_login_name(),
            "password": self.clean_login_password(),
            "captcha": captcha_code,
            "captchaId": captcha_uid,
        }

    # 定义登录请求提交方法。
    def post_login(self, payload):

        """
        提交广东五嗣堂医药登录请求。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建登录请求头。
        headers = self.build_login_headers()

        # 序列化登录请求体。
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 发送登录请求。
        return self.http.request("POST", self.login_api_url, headers=headers, data=body)

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建登录请求头。

        :return: 登录请求头。
        :rtype: dict
        """

        # 读取验证码接口下发的跨站请求令牌。
        xsrf_token = self.get_cookie_value("XSRF-TOKEN")

        # 返回登录接口请求头。
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": self.base_url,
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
            "X-Requested-With": "XMLHttpRequest",
        }

        # 写入服务端校验要求的 XSRF 请求头。
        if xsrf_token:

            # 浏览器登录请求使用 Cookie 同名值作为 X-XSRF-TOKEN。
            headers["X-XSRF-TOKEN"] = xsrf_token

        # 返回登录请求头。
        return headers

    # 定义 Cookie 值读取方法。
    def get_cookie_value(self, cookie_name):

        """
        从当前 CookieJar 中读取指定 Cookie 值。

        :param cookie_name: Cookie 名称。
        :type cookie_name: str
        :return: Cookie 值。
        :rtype: str
        """

        # 遍历当前会话 Cookie。
        for cookie in self.http.cookie_jar:

            # 返回目标 Cookie 值。
            if cookie.name == cookie_name:

                # 返回 Cookie 文本值。
                return str(cookie.value)

        # 返回空 Cookie 值。
        return ""

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析登录响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 登录响应数据。
        :rtype: dict
        """

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 处理空登录响应。
        if not response_text:

            # 返回空响应登录结果。
            return {"success": False, "message": "登录接口返回空响应"}

        # 尝试解析 JSON 响应。
        try:

            # 返回 JSON 响应数据。
            return json.loads(response_text)

        # 处理非 JSON 响应。
        except json.JSONDecodeError:

            # 返回原始响应文本。
            return {"success": False, "message": response_text}

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断登录响应是否成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 判断成功布尔字段。
        if login_result.get("success") is True:

            # 返回登录成功状态。
            return True

        # 判断登录令牌是否存在。
        if self.extract_login_token(login_result):

            # 返回登录成功状态。
            return True

        # 判断常见成功状态码。
        if str(login_result.get("code", "")) in ["0", "200"]:

            # 返回登录成功状态。
            return True

        # 返回登录失败状态。
        return False

    # 定义登录响应消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取登录响应消息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录响应消息。
        :rtype: str
        """

        # 返回响应消息字段。
        if login_result.get("message") or login_result.get("msg"):

            # 返回响应消息文本。
            return str(login_result.get("message") or login_result.get("msg"))

        # 返回令牌登录成功消息。
        if self.extract_login_token(login_result):

            # 返回令牌成功摘要。
            return "token"

        # 返回原始响应摘要。
        return str(login_result)

    # 定义登录令牌提取方法。
    def extract_login_token(self, login_result):

        """
        提取登录响应中的访问令牌。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 访问令牌。
        :rtype: str
        """

        # 遍历顶层常见令牌字段。
        for key in ["access_token", "accessToken", "token", "jwt"]:

            # 读取当前令牌字段值。
            token_value = login_result.get(key)

            # 返回非空令牌。
            if token_value:

                # 返回令牌文本。
                return str(token_value)

        # 读取响应数据字段。
        data = login_result.get("data")

        # 处理嵌套字典令牌字段。
        if isinstance(data, dict):

            # 遍历嵌套常见令牌字段。
            for key in ["access_token", "accessToken", "token", "jwt", "Authorization"]:

                # 读取当前令牌字段值。
                token_value = data.get(key)

                # 返回非空令牌。
                if token_value:

                    # 返回令牌文本。
                    return str(token_value)

        # 返回空令牌。
        return ""

    # 定义登录账号清洗方法。
    def clean_login_name(self):

        """
        读取清洗后的登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回去除两端空白后的账号。
        return str(self.account["账号"]).strip()

    # 定义登录密码清洗方法。
    def clean_login_password(self):

        """
        读取清洗后的登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回去除两端空白后的密码。
        return str(self.account["密码"]).strip()

    # 定义站点根地址构建方法。
    def build_origin(self, url):

        """
        根据页面地址构建站点根地址。

        :param url: 页面地址。
        :type url: str
        :return: 站点根地址。
        :rtype: str
        """

        # 解析页面地址。
        parsed_url = urlparse(url)

        # 返回协议与域名组成的站点根地址。
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录 Cookie 与认证令牌。

        :param output_dir: 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存 Cookie 文件。
        self.http.save_cookie_file(cookie_path)

        # 保存认证令牌文件。
        self.save_token_file(output_dir)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义令牌保存方法。
    def save_token_file(self, output_dir):

        """
        保存登录令牌到本地文件。

        :param output_dir: 输出目录。
        :type output_dir: str
        :return: 令牌文件路径。
        :rtype: str
        """

        # 构建令牌文件路径。
        token_path = os.path.join(output_dir, f"{self.company_name}_token.json")

        # 构建令牌文件内容。
        token_data = {"token": self.login_token, "login_result": self.login_result}

        # 写入令牌文件。
        with open(token_path, "w", encoding="utf-8") as file_obj:

            # 序列化令牌文件内容。
            json.dump(token_data, file_obj, ensure_ascii=False, indent=2)

        # 打印令牌保存日志。
        self.ph.success(self.ph.kv("登录令牌已保存", self.ph.path(token_path), "green"))

        # 返回令牌文件路径。
        return token_path

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询广东五嗣堂医药流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 查询指定类型完整数据。
        query_result = self.query_gdwst_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出广东五嗣堂医药流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :return: 导出文件路径。
        :rtype: str
        """

        # 使用分页查询结果生成本地 Excel 文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询广东五嗣堂医药流向数据并生成 Excel。

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

        # 查询指定业务数据。
        query_result = self.query_gdwst_data(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义广东五嗣堂医药数据查询方法。
    def query_gdwst_data(self, data_type, start_date, end_date):

        """
        查询广东五嗣堂医药指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果与表头。
        :rtype: dict
        """

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 校验流向类查询开始日期。
        if data_type in ["配送流向", "购进流向"] and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验流向类查询结束日期。
        if data_type in ["配送流向", "购进流向"] and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

        # 初始化当前页码。
        current_page = 1

        # 初始化累计数据行。
        all_rows = []

        # 初始化总记录数。
        total_count = None

        # 按页循环请求业务数据。
        while True:

            # 构建当前页查询参数。
            params = self.build_query_params(data_type, start_date, end_date, current_page)

            # 打印分页请求日志。
            self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", f"pageNo={current_page}", "cyan"), self.ph.kv("pageSize", params["pageSize"], "yellow")))

            # 发送当前页查询请求。
            result = self.get_query_page(data_type, params)

            # 解析当前页查询响应。
            page_result = self.decode_query_page(result)

            # 读取当前页数据行。
            page_rows = page_result["rows"]

            # 保存总记录数。
            total_count = page_result["total"]

            # 追加当前页数据行。
            all_rows.extend(page_rows)

            # 打印当前页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "yellow")))

            # 判断是否已经完成全部分页。
            if len(all_rows) >= int(total_count or 0) or not page_rows:

                # 结束分页循环。
                break

            # 递增页码。
            current_page += 1

        # 读取当前数据类型 Excel 表头。
        headers = self.build_excel_headers(data_type, all_rows)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{len(all_rows)} 条", "green"), self.ph.kv("表头数", len(headers), "cyan")))

        # 返回标准查询结果。
        return {"rows": all_rows, "headers": headers}

    # 定义登录状态确认方法。
    def ensure_login(self):

        """
        确认当前适配器已经持有登录令牌。

        :return: None。
        :rtype: None
        """

        # 当前会话已有令牌时直接返回。
        if self.login_token:

            # 返回空值。
            return

        # 执行协议登录。
        self.login()

    # 定义查询参数构建方法。
    def build_query_params(self, data_type, start_date, end_date, current_page):

        """
        构建报表分页查询参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param current_page: 当前页码。
        :type current_page: int
        :return: 查询参数。
        :rtype: dict
        """

        # 构建基础分页与令牌参数。
        params = {
            "id": self.report_config_for_data_type(data_type)["id"],
            "token": self.login_token,
            "delFlag": 0,
            "pageNo": current_page,
            "pageSize": str(self.page_size),
        }

        # 写入供应商出库查询的会计日期范围。
        if data_type == "配送流向":

            # 写入会计日期开始值。
            params["accdate_begin"] = start_date

            # 写入会计日期结束值。
            params["accdate_end"] = end_date

        # 写入供应商入库查询的生效日期范围。
        if data_type == "购进流向":

            # 写入生效日期开始值。
            params["accdate_begin"] = start_date

            # 写入会计日期结束值。
            params["accdate_end"] = end_date

        # 返回查询参数。
        return params

    # 定义查询请求提交方法。
    def get_query_page(self, data_type, params):

        """
        请求广东五嗣堂医药报表分页接口。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param params: 查询参数。
        :type params: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建报表查询请求体。
        payload = self.build_report_payload(data_type, params)

        # 构建授权查询请求头。
        headers = self.build_authorized_headers(data_type)

        # 序列化查询请求体。
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 发送报表查询请求。
        return self.http.request("POST", self.query_api_url, headers=headers, data=body, timeout=120)

    # 定义报表请求体构建方法。
    def build_report_payload(self, data_type, params):

        """
        构建积木报表查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param params: 报表参数。
        :type params: dict
        :return: 报表查询请求体。
        :rtype: dict
        """

        # 读取报表配置。
        report_config = self.report_config_for_data_type(data_type)

        # 返回报表请求体。
        return {
            "id": report_config["id"],
            "apiUrl": "",
            "params": json.dumps(params, ensure_ascii=False, separators=(",", ":")),
        }

    # 定义查询响应解析方法。
    def decode_query_page(self, result):

        """
        解析广东五嗣堂医药报表分页响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 分页查询结果。
        :rtype: dict
        """

        # 解析 JSON 响应。
        response_data = self.http.decode_json(result)

        # 校验响应状态。
        if response_data.get("success") is not True and str(response_data.get("code", "")) not in ["0", "200"]:

            # 抛出查询失败异常。
            raise RuntimeError(response_data.get("message") or response_data)

        # 读取报表结果字段。
        result_data = response_data.get("result") or {}

        # 读取报表数据列表。
        data_list = result_data.get("dataList") or {}

        # 读取主要分页节点。
        page_node = self.extract_first_page_node(data_list)

        # 读取分页数据行。
        rows = page_node.get("list") or []

        # 读取分页总数。
        total = page_node.get("total", page_node.get("count", len(rows)))

        # 返回分页查询结果。
        return {"rows": rows, "total": int(total or 0)}

    # 定义报表分页节点提取方法。
    def extract_first_page_node(self, data_list):

        """
        从报表 dataList 中提取第一个分页数据节点。

        :param data_list: 报表 dataList 字典。
        :type data_list: dict
        :return: 分页数据节点。
        :rtype: dict
        """

        # 遍历报表数据节点。
        for page_node in data_list.values():

            # 返回包含列表字段的分页节点。
            if isinstance(page_node, dict) and isinstance(page_node.get("list"), list):

                # 返回当前分页节点。
                return page_node

        # 返回空分页节点。
        return {"list": [], "total": 0}

    # 定义授权请求头构建方法。
    def build_authorized_headers(self, data_type):

        """
        构建授权业务请求头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 授权业务请求头。
        :rtype: dict
        """

        # 读取报表配置。
        report_config = self.report_config_for_data_type(data_type)

        # 读取跨站请求令牌。
        xsrf_token = self.get_cookie_value("XSRF-TOKEN")

        # 构建报表页面来源地址。
        referer = f"{self.base_url}/#/jmreport/shareView/{report_config['id']}?token={self.login_token}"

        # 构建授权请求头。
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": self.base_url,
            "Referer": referer,
            "Token": self.login_token,
            "User-Agent": self.http.user_agent(),
            "X-Access-Token": self.login_token,
        }

        # 写入 XSRF 请求头。
        if xsrf_token:

            # 使用 Cookie 同名值作为 X-XSRF-TOKEN。
            headers["X-XSRF-TOKEN"] = xsrf_token

        # 返回授权请求头。
        return headers

    # 定义数据类型报表配置读取方法。
    def report_config_for_data_type(self, data_type):

        """
        读取 DDI 数据类型对应的报表配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表配置。
        :rtype: dict
        """

        # 定义 DDI 数据类型与积木报表 ID 的映射关系。
        config_map = {
            "库存": {"id": "908896101984796672", "name": "供应商库存查询"},
            "配送流向": {"id": "908905641803415552", "name": "供应商出库查询"},
            "购进流向": {"id": "908903034942816256", "name": "供应商入库查询"},
        }

        # 返回当前数据类型报表配置。
        return config_map[data_type]

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验广东五嗣堂医药数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 校验数据类型是否存在。
        if data_type not in ["配送流向", "购进流向", "库存"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前广东五嗣堂医药暂未接入: {data_type}")

    # 定义 Excel 表头构建方法。
    def build_excel_headers(self, data_type, rows=None):

        """
        构建业务 Excel 表头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果数据行。
        :type rows: list[dict] | None
        :return: Excel 表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 定义库存表头。
        stock_headers = [("业务机构名称", "orgname"), ("供应商名称", "supplyname"), ("商品编码", "goodsno"), ("商品名称", "goodsname"), ("商品规格", "goodstype"), ("商品单位", "goodsunit"), ("生产企业", "factoryname"), ("生产日期", "makedate"), ("效期", "invaliddate"), ("生产批号", "makeno"), ("批号", "batchno"), ("数量", "qty")]

        # 定义出库表头。
        outbound_headers = [("出库单号", "accptno"), ("单据类型", "billcode"), ("会计日", "accdate"), ("业务机构名称", "orgname"), ("客户名称", "customname"), ("商品编码", "goodsno"), ("商品名称", "goodsname"), ("生产企业", "factoryname"), ("商品规格", "goodstype"), ("商品单位", "goodsunit"), ("批号", "batchno"), ("生产日期", "makedate"), ("有效期", "invaliddate"), ("数量", "qty"), ("销售价", "saleprice"), ("进价", "inprice")]

        # 定义入库表头。
        inbound_headers = [("入库单号", "accptno"), ("生效日期", "execdate"), ("业务机构名称", "orgname"), ("供应商名称", "supplyname"), ("商品编码", "goodsno"), ("商品名称", "goodsname"), ("生产企业", "factoryname"), ("商品规格", "goodstype"), ("商品单位", "goodsunit"), ("批号", "batchno"), ("生产日期", "makedate"), ("有效期", "invaliddate"), ("数量", "qty"), ("进价", "inprice")]

        # 读取预设表头。
        headers = {"库存": stock_headers, "配送流向": outbound_headers, "购进流向": inbound_headers}[data_type]

        # 没有数据行时返回预设表头。
        if not rows:

            # 返回预设表头。
            return headers

        # 读取预设字段集合。
        known_fields = {field_name for _, field_name in headers}

        # 遍历响应首行字段，追加未预设字段。
        for field_name in rows[0].keys():

            # 跳过已经预设的字段。
            if field_name in known_fields:

                # 继续下一个字段。
                continue

            # 追加接口原始字段。
            headers.append((field_name, field_name))

        # 返回表头配置。
        return headers

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建输出文件名。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 输出文件名。
        :rtype: str
        """

        # Delegate standard naming to the base platform.
        return super().build_output_file_name(data_type, start_date, end_date)

    # 定义流向月份标签构建方法。
    def build_month_label(self, start_date):

        """
        构建流向文件月份标签。

        :param start_date: 查询开始日期。
        :type start_date: str
        :return: 月份标签。
        :rtype: str
        """

        # 解析开始日期。
        date_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 返回 yy.m月 标签。
        return f"{date_value.year % 100}.{date_value.month}月"

    # 定义库存日期标签构建方法。
    def build_stock_date_label(self, end_date):

        """
        构建库存文件日期标签。

        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 库存日期标签。
        :rtype: str
        """

        # 读取导出当天日期。
        date_text = datetime.now().strftime("%Y-%m-%d")

        # 解析导出日期。
        date_value = datetime.strptime(date_text, "%Y-%m-%d")

        # 返回 yy.m.d 标签。
        return f"{date_value.year % 100}.{date_value.month}.{date_value.day}"

    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        写入查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param headers: 表头配置。
        :type headers: list[tuple[str, str]]
        :param output_path: 输出文件路径。
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

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = sheet_name[:31]

        # 写入表头行。
        worksheet.append([header_name for header_name, _ in headers])

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按表头顺序组装一行数据。
            worksheet.append([row.get(field_name, "") if isinstance(row, dict) else "" for _, field_name in headers])

        # 遍历所有导出列设置列宽。
        for column_index, header_item in enumerate(headers, start=1):

            # 读取当前列字母。
            column_letter = get_column_letter(column_index)

            # 读取当前表头名称。
            header_name = header_item[0]

            # 设置当前列宽。
            worksheet.column_dimensions[column_letter].width = max(12, min(34, len(str(header_name)) + 10))

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

    # 定义同名文件删除方法。
    def remove_existing_file(self, output_path):

        """
        删除已有同名输出文件。

        :param output_path: 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 判断同名文件是否存在。
        if not os.path.exists(output_path):

            # 返回空值。
            return

        # 删除已有文件。
        os.remove(output_path)
