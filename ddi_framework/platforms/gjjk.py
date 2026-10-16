# -*- coding: utf-8 -*-
"""
高济健康 SRM 平台协议适配器。

本模块负责广州市宝芝林大药房连锁有限公司在高济健康 SRM 平台的滑块校验、密码加密、协议登录和令牌落地。
"""

# 导入 Base64 编解码模块。
import base64

# 导入内存字节流模块。
import io

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入日期时间模块。
from datetime import datetime, timedelta

# 导入 URL 编码与解析函数。
from urllib.parse import quote, unquote, urlencode, urlparse, urlunparse

# 导入 AES-ECB 加密器。
from ddi_framework import AesEcbEncryptor

# 导入下载文件命名工具。
from ddi_framework import DownloadWatcher

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义高济健康 SRM 平台协议适配器。
class GjjkPlatform(BasePlatform):

    """
    高济健康 SRM 平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 高济健康 SRM 平台适配器实例。
    :rtype: GjjkPlatform
    """

    # 定义高济健康 SRM 适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化高济健康 SRM 平台适配器。

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
        self.login_page_url = account.get("登录页", "https://srm.cowellhealth.com/user/login")

        # 保存接口根地址。
        self.api_base_url = account.get("接口根地址", "https://api-retail.cowellhealth.com")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", f"{self.api_base_url}/api/loginWithVerifyCode")

        # 保存数据下载任务接口地址。
        self.export_task_api_url = account.get("下载任务接口", f"{self.api_base_url}/purchase-sync/api/srm/datacenter/getExport")

        # 保存下载中心任务列表接口地址。
        self.export_list_api_url = account.get("下载中心列表接口", f"{self.api_base_url}/scrm/api/fileDownloadTaskList")

        # 保存下载中心签名地址接口地址。
        self.sign_url_api_url = account.get("下载签名接口", f"{self.api_base_url}/purchase/api/getSignUrl")

        # 保存下载中心页面地址。
        self.download_center_url = account.get("下载中心页", "https://srm.cowellhealth.com/download/downloadCenter")

        # 保存下载任务等待秒数。
        self.export_wait_timeout = int(account.get("下载任务等待秒数", 180))

        # 保存下载任务轮询秒数。
        self.export_poll_interval = int(account.get("下载任务轮询秒数", 5))

        # 保存验证码初始化接口地址。
        self.code_api_url = account.get("验证码初始化接口", f"{self.api_base_url}/store/api/noauth/img/getCode")

        # 保存滑块图片接口地址。
        self.slider_image_api_url = account.get("滑块图片接口", f"{self.api_base_url}/store/api/noauth/img/getvalidateimg")

        # 保存滑块校验接口地址。
        self.slider_validate_api_url = account.get("滑块校验接口", f"{self.api_base_url}/store/api/noauth/img/tovalidateimg")

        # 保存平台页面根地址。
        self.web_origin = self.build_origin(self.login_page_url)

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 保存密码加密密钥。
        self.password_secret_key = account.get("密码加密密钥", "abcdefgabcdefg12")

        # 初始化登录响应。
        self.login_result = {}

        # 初始化登录令牌。
        self.login_token = ""

        # 初始化刷新令牌。
        self.refresh_token = ""

        # 初始化登录用户信息。
        self.user_info = {}

    # 定义高济健康 SRM 登录方法。
    def login(self):

        """
        执行高济健康 SRM 协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("高济健康 SRM 登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 请求登录页并初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 构建滑块校验会话编号。
        validate_key = self.build_validate_key()

        # 初始化验证码会话。
        self.initialize_captcha_session()

        # 获取滑块验证码上下文。
        slider_context = self.get_slider_context(validate_key)

        # 识别滑块横向校验坐标。
        validate_width = self.solve_slider_validate_width(slider_context["background_image"])

        # 提交滑块校验。
        slider_result = self.validate_slider(validate_key, validate_width)

        # 校验滑块响应是否成功。
        if not self.is_slider_success(slider_result):

            # 抛出滑块校验失败异常。
            raise RuntimeError(f"{self.company_name} 滑块校验失败：{slider_result}")

        # 构建登录请求体。
        payload = self.build_login_payload(validate_key, validate_width)

        # 打印正式登录请求日志。
        self.ph.info("提交正式登录请求: /api/loginWithVerifyCode")

        # 提交登录请求。
        result = self.post_login(payload)

        # 解析登录响应。
        login_result = self.decode_json_response(result)

        # 校验登录结果。
        if not self.is_login_success(login_result):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{self.extract_response_message(login_result)}")

        # 保存登录响应。
        self.login_result = login_result

        # 保存登录令牌。
        self.login_token = str(login_result.get("access_token") or "")

        # 保存刷新令牌。
        self.refresh_token = str(login_result.get("refresh_token") or "")

        # 保存登录用户信息。
        self.user_info = self.extract_user_info(login_result)

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("正式登录成功", self.user_info.get("name", ""), "green"), self.ph.kv("businessId", self.user_info.get("businessId", ""), "cyan")))

        # 返回登录响应。
        return login_result

    # 定义验证码会话编号构建方法。
    def build_validate_key(self):

        """
        构建滑块验证码会话编号。

        :return: 滑块验证码会话编号。
        :rtype: str
        """

        # 返回前端同源的验证码会话编号。
        return f"gj{int(time.time() * 1000)}"

    # 定义验证码会话初始化方法。
    def initialize_captcha_session(self):

        """
        初始化账号验证码会话。

        :return: 验证码初始化响应。
        :rtype: dict
        """

        # 构建验证码初始化查询参数。
        query_string = urlencode({"identifyKey": self.clean_login_name()})

        # 拼接验证码初始化接口地址。
        request_url = f"{self.code_api_url}?{query_string}"

        # 打印验证码初始化日志。
        self.ph.info("请求验证码初始化接口: /store/api/noauth/img/getCode")

        # 请求验证码初始化接口。
        result = self.http.request("GET", request_url, headers=self.build_common_headers())

        # 返回验证码初始化响应。
        return self.decode_json_response(result)

    # 定义滑块验证码上下文获取方法。
    def get_slider_context(self, validate_key):

        """
        获取滑块验证码背景图和拼图图标。

        :param validate_key: 滑块验证码会话编号。
        :type validate_key: str
        :return: 滑块验证码上下文字典。
        :rtype: dict
        """

        # 构建滑块图片查询参数。
        query_string = urlencode({"validateKey": validate_key})

        # 拼接滑块图片接口地址。
        request_url = f"{self.slider_image_api_url}?{query_string}"

        # 打印滑块图片请求日志。
        self.ph.info("请求滑块验证码图片: /store/api/noauth/img/getvalidateimg")

        # 请求滑块图片接口。
        result = self.http.request("GET", request_url, headers=self.build_common_headers())

        # 解析滑块图片响应。
        response_data = self.decode_json_response(result)

        # 读取滑块背景图文本。
        background_text = str(response_data.get("validateImgBase64") or "")

        # 校验滑块背景图文本。
        if not background_text:

            # 抛出滑块背景图缺失异常。
            raise RuntimeError(f"滑块接口未返回 validateImgBase64：{response_data}")

        # 解码滑块背景图片。
        background_image = self.decode_base64_image(background_text)

        # 读取滑块图标地址。
        small_image_url = str(response_data.get("smallImgUrl") or "")

        # 返回滑块验证码上下文。
        return {"background_image": background_image, "small_image_url": small_image_url, "response": response_data}

    # 定义滑块坐标识别方法。
    def solve_slider_validate_width(self, background_image):

        """
        识别高济健康 SRM 滑块缺口横向坐标。

        :param background_image: 滑块背景图字节流。
        :type background_image: bytes
        :return: 滑块校验横向坐标。
        :rtype: int
        """

        # 导入 OpenCV 模块。
        import cv2

        # 导入 NumPy 模块。
        import numpy as np

        # 导入 PIL 图片模块。
        from PIL import Image

        # 读取背景图为 RGB 图片。
        image = Image.open(io.BytesIO(background_image)).convert("RGB")

        # 转换图片为 NumPy 数组。
        image_array = np.array(image)

        # 转换图片为灰度图。
        gray_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

        # 提取高亮白色缺口区域。
        white_mask = (gray_image > 238).astype("uint8") * 255

        # 读取白色区域轮廓。
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 初始化候选轮廓列表。
        candidates = []

        # 遍历白色区域轮廓。
        for contour in contours:

            # 读取轮廓外接矩形。
            x_value, y_value, width_value, height_value = cv2.boundingRect(contour)

            # 读取轮廓面积。
            area_value = cv2.contourArea(contour)

            # 判断轮廓尺寸是否符合滑块缺口。
            if 10 <= width_value <= 80 and 10 <= height_value <= 80 and area_value >= 100:

                # 保存候选缺口轮廓。
                candidates.append((x_value, y_value, width_value, height_value, area_value))

        # 校验候选轮廓是否存在。
        if not candidates:

            # 抛出滑块缺口识别失败异常。
            raise RuntimeError("滑块背景图未识别到白色缺口")

        # 读取面积最大的候选轮廓。
        best_candidate = max(candidates, key=lambda item: item[4])

        # 读取缺口左侧横向坐标。
        validate_width = int(best_candidate[0])

        # 打印滑块识别日志。
        self.ph.info(self.ph.kv("滑块缺口坐标", validate_width, "cyan"))

        # 返回滑块校验横向坐标。
        return validate_width

    # 定义滑块校验提交方法。
    def validate_slider(self, validate_key, validate_width):

        """
        提交滑块验证码校验。

        :param validate_key: 滑块验证码会话编号。
        :type validate_key: str
        :param validate_width: 滑块横向校验坐标。
        :type validate_width: int
        :return: 滑块校验响应。
        :rtype: dict
        """

        # 构建滑块校验查询参数。
        query_string = urlencode({"validateKey": validate_key, "validateWidth": validate_width})

        # 拼接滑块校验接口地址。
        request_url = f"{self.slider_validate_api_url}?{query_string}"

        # 打印滑块校验请求日志。
        self.ph.info("提交滑块验证码校验: /store/api/noauth/img/tovalidateimg")

        # 请求滑块校验接口。
        result = self.http.request("GET", request_url, headers=self.build_common_headers())

        # 返回滑块校验响应。
        return self.decode_json_response(result)

    # 定义滑块校验成功判断方法。
    def is_slider_success(self, response_data):

        """
        判断滑块校验响应是否成功。

        :param response_data: 滑块校验响应。
        :type response_data: dict
        :return: 是否校验成功。
        :rtype: bool
        """

        # 返回滑块响应成功状态。
        return bool(response_data.get("success")) and response_data.get("resultContant") == "VALIDATEIMGSUCCESS"

    # 定义登录请求体构建方法。
    def build_login_payload(self, validate_key, validate_width):

        """
        构建高济健康 SRM 登录请求体。

        :param validate_key: 滑块验证码会话编号。
        :type validate_key: str
        :param validate_width: 滑块横向校验坐标。
        :type validate_width: int
        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录 JSON 字段。
        return {"username": self.clean_login_name(), "password": self.encrypt_password(), "type": "Account", "verifyKey": validate_key, "verifyValue": validate_width, "verifyCodeType": 1, "rememberMe": True, "srmLoginMark": True}

    # 定义密码加密方法。
    def encrypt_password(self):

        """
        加密高济健康 SRM 登录密码。

        :return: AES-ECB-PKCS7 Base64 密文。
        :rtype: str
        """

        # 返回前端同源的 AES-ECB 密码密文。
        return AesEcbEncryptor.encrypt_to_base64(self.clean_login_password(), self.password_secret_key)

    # 定义登录提交方法。
    def post_login(self, payload):

        """
        提交高济健康 SRM 登录请求。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 序列化登录请求体。
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 构建登录请求头。
        headers = self.build_login_headers()

        # 发送登录请求。
        return self.http.request("POST", self.login_api_url, headers=headers, data=body)

    # 定义通用请求头构建方法。
    def build_common_headers(self):

        """
        构建高济健康 SRM 通用接口请求头。

        :return: 通用接口请求头。
        :rtype: dict
        """

        # 返回浏览器通用请求头。
        return {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Origin": self.web_origin, "Referer": self.login_page_url, "User-Agent": self.http.user_agent()}

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建高济健康 SRM 登录接口请求头。

        :return: 登录接口请求头。
        :rtype: dict
        """

        # 构建基础请求头。
        headers = self.build_common_headers()

        # 设置 JSON 请求体类型。
        headers["Content-Type"] = "application/json;charset=UTF-8"

        # 读取当前 XSRF 令牌。
        xsrf_token = self.get_cookie_value("XSRF-TOKEN")

        # 判断 XSRF 令牌是否存在。
        if xsrf_token:

            # 写入 XSRF 请求头。
            headers["X-XSRF-TOKEN"] = xsrf_token

        # 返回登录请求头。
        return headers

    # 定义认证请求头构建方法。
    def build_authorized_headers(self):

        """
        构建高济健康 SRM 认证接口请求头。

        :return: 认证接口请求头。
        :rtype: dict
        """

        # 构建基础请求头。
        headers = self.build_common_headers()

        # 设置 JSON 请求体类型。
        headers["Content-Type"] = "application/json;charset=UTF-8"

        # 设置访问令牌认证头。
        headers["Authorization"] = f"Bearer {self.login_token}"

        # 读取当前 XSRF 令牌。
        xsrf_token = self.get_cookie_value("XSRF-TOKEN")

        # 判断 XSRF 令牌是否存在。
        if xsrf_token:

            # 写入 XSRF 请求头。
            headers["X-XSRF-TOKEN"] = xsrf_token

        # 返回认证接口请求头。
        return headers

    # 定义 Cookie 读取方法。
    def get_cookie_value(self, cookie_name):

        """
        读取当前会话中的指定 Cookie 值。

        :param cookie_name: Cookie 名称。
        :type cookie_name: str
        :return: Cookie 值。
        :rtype: str
        """

        # 遍历当前 Cookie 容器。
        for cookie in self.http.cookie_jar:

            # 判断 Cookie 名称是否匹配。
            if cookie.name == cookie_name:

                # 返回 Cookie 值。
                return str(cookie.value)

        # 返回空 Cookie 值。
        return ""

    # 定义 JSON 响应解析方法。
    def decode_json_response(self, result):

        """
        解析 JSON 响应体。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: JSON 响应字典。
        :rtype: dict
        """

        # 解码响应体文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 判断响应体是否为空。
        if not response_text.strip():

            # 返回空响应字典。
            return {}

        # 返回 JSON 响应对象。
        return json.loads(response_text)

    # 定义 Base64 图片解码方法。
    def decode_base64_image(self, image_text):

        """
        解码 Base64 图片文本。

        :param image_text: Base64 图片文本。
        :type image_text: str
        :return: 图片字节流。
        :rtype: bytes
        """

        # 读取 Base64 正文。
        raw_base64 = image_text.split("base64,", 1)[-1]

        # 返回图片字节流。
        return base64.b64decode(raw_base64)

    # 定义登录成功判断方法。
    def is_login_success(self, response_data):

        """
        判断登录响应是否成功。

        :param response_data: 登录响应数据。
        :type response_data: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 返回访问令牌存在状态。
        return bool(response_data.get("access_token"))

    # 定义响应消息提取方法。
    def extract_response_message(self, response_data):

        """
        提取接口响应消息。

        :param response_data: 接口响应数据。
        :type response_data: dict
        :return: 响应消息。
        :rtype: str
        """

        # 返回接口消息字段。
        return str(response_data.get("message") or response_data.get("errorMessage") or response_data.get("error") or response_data)

    # 定义登录用户信息提取方法。
    def extract_user_info(self, login_result):

        """
        提取登录用户信息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录用户信息。
        :rtype: dict
        """

        # 定义需要保留的用户信息字段。
        user_keys = ["businessId", "userId", "platformUserId", "loginName", "name", "phone", "roles", "type", "status", "expires_in"]

        # 返回登录用户信息字段。
        return {key: login_result.get(key) for key in user_keys if key in login_result}

    # 定义登录账号清洗方法。
    def clean_login_name(self):

        """
        清洗登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回去除首尾空白的登录账号。
        return str(self.account.get("账号") or "").strip()

    # 定义登录密码清洗方法。
    def clean_login_password(self):

        """
        清洗登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回原始登录密码。
        return str(self.account.get("密码") or "")

    # 定义登录状态校验方法。
    def ensure_login(self):

        """
        确保当前适配器已经完成登录。

        :return: None。
        :rtype: None
        """

        # 判断登录令牌是否存在。
        if self.login_token:

            # 登录令牌存在时直接返回。
            return

        # 执行登录流程。
        self.login()

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
        token_data = {"access_token": self.login_token, "refresh_token": self.refresh_token, "user_info": self.user_info, "login_result": self.login_result}

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
        查询高济健康 SRM 业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 抛出查询接口未接入异常。
        raise NotImplementedError("高济健康 SRM 当前仅完成登录协议，业务查询接口待抓包确认")

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出高济健康 SRM 业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: 导出结果。
        :rtype: dict
        """

        # 确保当前会话已经登录。
        self.ensure_login()

        # 读取提交前下载中心任务快照。
        existing_task_keys = self.snapshot_export_task_keys(data_type)

        # 记录下载任务提交时间。
        submitted_at = datetime.now()

        # 构建下载任务请求体。
        payload = self.build_export_task_payload(data_type, start_date, end_date)

        # 打印下载任务请求日志。
        self.ph.info(self.ph.join(self.ph.kv("提交下载任务", data_type, "cyan"), self.ph.kv("类型编码", payload.get("dataFlowTypeName"), "yellow")))

        # 提交下载任务请求。
        result = self.post_export_task(payload)

        # 解析下载任务响应。
        response_data = self.decode_json_response(result)

        # 校验下载任务响应。
        if not self.is_export_task_success(response_data):

            # 抛出下载任务创建失败异常。
            raise RuntimeError(f"{self.company_name} {data_type} 下载任务创建失败：{self.extract_response_message(response_data)}")

        # 打印下载任务创建成功日志。
        self.ph.success(self.ph.kv("下载任务已创建", "请到下载中心下载", "green"))

        # 等待下载中心生成本次任务。
        export_task = self.wait_for_export_task(data_type, submitted_at, existing_task_keys)

        # 下载本次任务对应的 Excel 文件。
        output_path = self.download_export_task(export_task, data_type, start_date, end_date, output_dir)

        # 返回本地 Excel 文件路径。
        return output_path

    # 定义下载任务请求体构建方法。
    def build_export_task_payload(self, data_type, start_date=None, end_date=None):

        """
        构建高济健康 SRM 数据下载任务请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 下载任务请求体。
        :rtype: dict
        """

        # 读取平台数据类型编码。
        platform_data_type = self.get_platform_data_type(data_type)

        # 构建基础下载任务请求体。
        payload = {"dataFlowTypeName": platform_data_type, "goodsCode": "", "goodsName": "", "companyCodeList": None, "viewAble": False}

        # 判断当前数据类型是否为月末库存。
        if data_type == "库存":

            # 读取库存月份。
            business_month = self.resolve_business_month(start_date, end_date)

            # 写入库存月份字段。
            payload["businessMonth"] = business_month

            # 返回库存下载任务请求体。
            return payload

        # 校验流向开始日期。
        if not start_date:

            # 抛出开始日期缺失异常。
            raise ValueError(f"{data_type} 下载任务必须提供 start_date")

        # 校验流向结束日期。
        if not end_date:

            # 抛出结束日期缺失异常。
            raise ValueError(f"{data_type} 下载任务必须提供 end_date")

        # 写入业务开始日期。
        payload["businessDateStart"] = start_date

        # 写入业务结束日期。
        payload["businessDateEnd"] = end_date

        # 返回流向下载任务请求体。
        return payload

    # 定义平台数据类型编码读取方法。
    def get_platform_data_type(self, data_type):

        """
        读取高济健康 SRM 平台数据类型编码。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 平台数据类型编码。
        :rtype: str
        """

        # 定义本地数据类型与平台数据类型编码映射。
        data_type_map = {"购进流向": "IN_STOCK", "配送流向": "STORE_DISTRIBUTION_ALL", "纯销流向": "STORE_SALE", "库存": "MONTH_END_STOCK"}

        # 校验数据类型是否已接入。
        if data_type not in data_type_map:

            # 抛出数据类型未接入异常。
            raise ValueError(f"高济健康 SRM 暂不支持数据类型：{data_type}")

        # 返回平台数据类型编码。
        return data_type_map[data_type]

    # 定义库存月份解析方法。
    def resolve_business_month(self, start_date=None, end_date=None):

        """
        解析月末库存下载任务的业务月份。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 业务月份。
        :rtype: str
        """

        # 读取优先日期。
        date_text = end_date or start_date

        # 校验日期是否存在。
        if not date_text:

            # 抛出业务月份缺失异常。
            raise ValueError("库存下载任务必须提供 start_date 或 end_date")

        # 返回业务月份文本。
        return str(date_text)[:7]

    # 定义下载任务提交方法。
    def post_export_task(self, payload):

        """
        提交高济健康 SRM 数据下载任务。

        :param payload: 下载任务请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 序列化下载任务请求体。
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 构建认证请求头。
        headers = self.build_authorized_headers()

        # 发送下载任务请求。
        return self.http.request("POST", self.export_task_api_url, headers=headers, data=body)

    # 定义下载任务成功判断方法。
    def is_export_task_success(self, response_data):

        """
        判断下载任务创建响应是否成功。

        :param response_data: 下载任务响应数据。
        :type response_data: dict
        :return: 是否创建成功。
        :rtype: bool
        """

        # 判断错误码字段是否表示成功。
        if str(response_data.get("errorKey", "0")) == "0":

            # 返回成功状态。
            return True

        # 判断响应体是否包含查询结果结构。
        if "result" in response_data or "resultList" in response_data:

            # 返回成功状态。
            return True

        # 返回失败状态。
        return False

    # 定义下载中心任务快照读取方法。
    def snapshot_export_task_keys(self, data_type):

        """
        读取提交下载任务前的下载中心任务标识集合。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 下载中心任务标识集合。
        :rtype: set[str]
        """

        # 读取下载中心第一页任务。
        response_data = self.list_export_tasks(page=0, size=50)

        # 提取下载中心任务列表。
        task_items = self.extract_export_task_items(response_data)

        # 筛选当前数据类型相关任务。
        related_items = [item for item in task_items if self.is_export_task_type_match(item, data_type)]

        # 返回任务稳定标识集合。
        return {self.build_export_task_key(item) for item in related_items}

    # 定义下载中心任务等待方法。
    def wait_for_export_task(self, data_type, submitted_at, existing_task_keys):

        """
        等待并定位下载中心内本次提交的导出任务。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param submitted_at: 下载任务提交时间。
        :type submitted_at: datetime
        :param existing_task_keys: 提交前已有任务标识集合。
        :type existing_task_keys: set[str]
        :return: 下载中心任务记录。
        :rtype: dict
        """

        # 计算下载中心轮询截止时间。
        deadline_at = datetime.now() + timedelta(seconds=self.export_wait_timeout)

        # 初始化最后一次候选任务列表。
        last_candidates = []

        # 循环等待下载中心生成任务。
        while datetime.now() <= deadline_at:

            # 读取下载中心第一页任务。
            response_data = self.list_export_tasks(page=0, size=50)

            # 提取下载中心任务列表。
            task_items = self.extract_export_task_items(response_data)

            # 筛选本次提交可能对应的任务。
            candidates = self.filter_export_task_candidates(task_items, data_type, submitted_at, existing_task_keys)

            # 保存最后一次候选任务列表。
            last_candidates = candidates

            # 筛选已完成且具备文件地址的候选任务。
            completed_candidates = [item for item in candidates if self.is_export_task_completed(item)]

            # 判断是否已存在可下载任务。
            if completed_candidates:

                # 选择最贴近本次提交的下载任务。
                export_task = self.select_export_task(completed_candidates, submitted_at)

                # 打印下载中心命中日志。
                self.ph.success(self.ph.join(self.ph.kv("下载中心已完成", export_task.get("name", ""), "green"), self.ph.kv("创建时间", export_task.get("createdDate", ""), "cyan")))

                # 返回下载任务记录。
                return export_task

            # 打印下载中心等待日志。
            self.ph.info(self.ph.join(self.ph.kv("等待下载中心", data_type, "cyan"), self.ph.kv("候选任务", len(candidates), "yellow")))

            # 等待下一次轮询。
            time.sleep(self.export_poll_interval)

        # 构建超时任务名称列表。
        candidate_names = [str(item.get("name") or "") for item in last_candidates]

        # 抛出下载中心等待超时异常。
        raise TimeoutError(f"{self.company_name} {data_type} 下载中心等待超时，候选任务：{candidate_names}")

    # 定义下载中心列表查询方法。
    def list_export_tasks(self, page=0, size=50, status=None):

        """
        查询下载中心任务列表。

        :param page: 零基分页页码。
        :type page: int
        :param size: 每页任务数量。
        :type size: int
        :param status: 任务状态编码。
        :type status: int | None
        :return: 下载中心列表响应。
        :rtype: dict
        """

        # 构建下载中心列表查询参数。
        query_params = {"page": page, "size": size, "platformType": 8, "sort": "createdDate,DESC"}

        # 判断是否限定任务状态。
        if status is not None:

            # 写入任务状态过滤条件。
            query_params["status"] = status

        # 编码下载中心列表查询参数。
        query_string = urlencode(query_params)

        # 拼接下载中心列表接口地址。
        request_url = f"{self.export_list_api_url}?{query_string}"

        # 请求下载中心列表接口。
        result = self.http.request("GET", request_url, headers=self.build_authorized_headers())

        # 返回下载中心列表响应。
        return self.decode_json_response(result)

    # 定义下载中心任务列表提取方法。
    def extract_export_task_items(self, response_data):

        """
        从下载中心响应中提取任务列表。

        :param response_data: 下载中心响应数据。
        :type response_data: dict
        :return: 下载中心任务列表。
        :rtype: list[dict]
        """

        # 判断响应数据是否为任务列表。
        if isinstance(response_data, list):

            # 返回响应任务列表。
            return response_data

        # 读取响应 result 字段。
        result_data = response_data.get("result")

        # 判断 result 字段是否为列表。
        if isinstance(result_data, list):

            # 返回 result 任务列表。
            return result_data

        # 判断 result 字段是否为字典。
        if isinstance(result_data, dict):

            # 读取嵌套 result 任务列表。
            nested_result = result_data.get("result")

            # 判断嵌套 result 是否为列表。
            if isinstance(nested_result, list):

                # 返回嵌套 result 任务列表。
                return nested_result

            # 读取嵌套 resultList 任务列表。
            nested_result_list = result_data.get("resultList")

            # 判断嵌套 resultList 是否为列表。
            if isinstance(nested_result_list, list):

                # 返回嵌套 resultList 任务列表。
                return nested_result_list

        # 读取顶层 resultList 任务列表。
        result_list = response_data.get("resultList")

        # 判断顶层 resultList 是否为列表。
        if isinstance(result_list, list):

            # 返回顶层 resultList 任务列表。
            return result_list

        # 返回空任务列表。
        return []

    # 定义下载中心任务候选筛选方法。
    def filter_export_task_candidates(self, task_items, data_type, submitted_at, existing_task_keys):

        """
        筛选下载中心中可能属于本次提交的任务。

        :param task_items: 下载中心任务列表。
        :type task_items: list[dict]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param submitted_at: 下载任务提交时间。
        :type submitted_at: datetime
        :param existing_task_keys: 提交前已有任务标识集合。
        :type existing_task_keys: set[str]
        :return: 候选下载任务列表。
        :rtype: list[dict]
        """

        # 计算服务端创建时间容错下限。
        lower_bound = submitted_at - timedelta(seconds=8)

        # 初始化候选任务列表。
        candidates = []

        # 遍历下载中心任务。
        for item in task_items:

            # 判断任务类型是否匹配。
            if not self.is_export_task_type_match(item, data_type):

                # 跳过任务类型不匹配的记录。
                continue

            # 构建任务稳定标识。
            task_key = self.build_export_task_key(item)

            # 判断任务是否属于提交前快照。
            if task_key in existing_task_keys:

                # 跳过提交前已经存在的任务。
                continue

            # 解析下载中心任务创建时间。
            created_at = self.parse_export_task_time(item.get("createdDate"))

            # 判断任务创建时间是否有效。
            if created_at is None:

                # 跳过缺少创建时间的任务。
                continue

            # 判断任务是否早于本次提交。
            if created_at < lower_bound:

                # 跳过早于本次提交窗口的任务。
                continue

            # 保存候选任务。
            candidates.append(item)

        # 返回候选任务列表。
        return candidates

    # 定义下载中心任务类型匹配方法。
    def is_export_task_type_match(self, task_item, data_type):

        """
        判断下载中心任务是否匹配指定数据类型。

        :param task_item: 下载中心任务记录。
        :type task_item: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否匹配当前数据类型。
        :rtype: bool
        """

        # 读取下载中心任务名称。
        task_name = str(task_item.get("name") or "")

        # 读取当前登录用户名称。
        user_name = self.get_export_task_user_name()

        # 读取下载中心任务类型关键词。
        task_keyword = self.get_export_task_keyword(data_type)

        # 判断任务名称是否包含类型关键词。
        if task_keyword not in task_name:

            # 返回类型不匹配状态。
            return False

        # 判断登录用户名是否存在。
        if user_name:

            # 返回登录用户名匹配状态。
            return task_name.startswith(f"{user_name}-")

        # 返回仅按类型关键词匹配的状态。
        return True

    # 定义下载中心任务完成判断方法。
    def is_export_task_completed(self, task_item):

        """
        判断下载中心任务是否已经完成并具备文件地址。

        :param task_item: 下载中心任务记录。
        :type task_item: dict
        :return: 是否可下载。
        :rtype: bool
        """

        # 读取任务状态编码。
        status_value = task_item.get("status")

        # 读取任务文件地址。
        file_url = str(task_item.get("fileUrl") or "")

        # 返回任务可下载状态。
        return str(status_value) == "2" and bool(file_url)

    # 定义下载中心任务选择方法。
    def select_export_task(self, task_items, submitted_at):

        """
        从候选任务中选择最贴近本次提交的任务。

        :param task_items: 候选任务列表。
        :type task_items: list[dict]
        :param submitted_at: 下载任务提交时间。
        :type submitted_at: datetime
        :return: 下载中心任务记录。
        :rtype: dict
        """

        # 返回按提交时间距离排序后的首个任务。
        return sorted(task_items, key=lambda item: self.export_task_sort_key(item, submitted_at))[0]

    # 定义下载中心任务排序键构建方法。
    def export_task_sort_key(self, task_item, submitted_at):

        """
        构建下载中心任务排序键。

        :param task_item: 下载中心任务记录。
        :type task_item: dict
        :param submitted_at: 下载任务提交时间。
        :type submitted_at: datetime
        :return: 排序键。
        :rtype: tuple
        """

        # 解析下载中心任务创建时间。
        created_at = self.parse_export_task_time(task_item.get("createdDate"))

        # 判断创建时间是否缺失。
        if created_at is None:

            # 返回低优先级排序键。
            return (999999999, "")

        # 计算任务创建时间与提交时间的差值秒数。
        delta_seconds = abs((created_at - submitted_at).total_seconds())

        # 返回排序键。
        return (delta_seconds, created_at.isoformat())

    # 定义下载中心任务标识构建方法。
    def build_export_task_key(self, task_item):

        """
        构建下载中心任务稳定标识。

        :param task_item: 下载中心任务记录。
        :type task_item: dict
        :return: 任务稳定标识。
        :rtype: str
        """

        # 读取下载中心任务编号。
        task_id = str(task_item.get("id") or "")

        # 判断任务编号是否存在。
        if task_id:

            # 返回任务编号标识。
            return f"id:{task_id}"

        # 读取下载中心任务名称。
        task_name = str(task_item.get("name") or "")

        # 读取下载中心任务创建时间。
        created_date = str(task_item.get("createdDate") or "")

        # 返回任务名称与创建时间组合标识。
        return f"name:{task_name}|created:{created_date}"

    # 定义下载中心任务时间解析方法。
    def parse_export_task_time(self, value):

        """
        解析下载中心任务创建时间。

        :param value: 下载中心创建时间字段。
        :type value: object
        :return: 创建时间。
        :rtype: datetime | None
        """

        # 判断时间值是否为空。
        if value in [None, ""]:

            # 返回空时间。
            return None

        # 判断时间值是否为数字。
        if isinstance(value, (int, float)):

            # 返回时间戳解析结果。
            return self.parse_timestamp_value(value)

        # 清洗时间文本。
        text_value = str(value).strip()

        # 判断时间文本是否为纯数字。
        if text_value.isdigit():

            # 返回数字时间戳解析结果。
            return self.parse_timestamp_value(int(text_value))

        # 统一 ISO 时间分隔符。
        normalized_text = text_value.replace("T", " ").split(".", 1)[0]

        # 遍历常见时间格式。
        for format_text in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"]:

            # 尝试按当前格式解析时间。
            try:

                # 返回格式解析后的时间。
                return datetime.strptime(normalized_text[:19], format_text)

            # 处理当前格式解析失败。
            except ValueError:

                # 继续尝试下一个时间格式。
                continue

        # 返回空时间。
        return None

    # 定义时间戳解析方法。
    def parse_timestamp_value(self, value):

        """
        解析秒级或毫秒级时间戳。

        :param value: 时间戳数值。
        :type value: int | float
        :return: 时间戳对应的本地时间。
        :rtype: datetime
        """

        # 转换时间戳为浮点数。
        timestamp_value = float(value)

        # 判断时间戳是否为毫秒级。
        if timestamp_value > 100000000000:

            # 转换毫秒时间戳为秒级。
            timestamp_value = timestamp_value / 1000

        # 返回本地时间。
        return datetime.fromtimestamp(timestamp_value)

    # 定义下载中心任务用户名读取方法。
    def get_export_task_user_name(self):

        """
        读取下载中心任务名称中的用户前缀。

        :return: 下载中心任务用户名称。
        :rtype: str
        """

        # 读取登录响应中的用户姓名。
        user_name = str(self.user_info.get("name") or "").strip()

        # 判断用户姓名是否存在。
        if user_name:

            # 返回用户姓名。
            return user_name

        # 返回登录账号文本。
        return str(self.user_info.get("loginName") or "").strip()

    # 定义下载中心任务类型关键词读取方法。
    def get_export_task_keyword(self, data_type):

        """
        读取数据类型对应的下载中心任务关键词。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 下载中心任务关键词。
        :rtype: str
        """

        # 定义本地数据类型与下载中心任务关键词映射。
        task_keyword_map = {"购进流向": "采购入库", "配送流向": "全体门店配送", "纯销流向": "门店销售", "库存": "月末库存"}

        # 校验数据类型是否存在。
        if data_type not in task_keyword_map:

            # 抛出数据类型未接入异常。
            raise ValueError(f"高济健康 SRM 暂不支持下载中心数据类型：{data_type}")

        # 返回下载中心任务关键词。
        return task_keyword_map[data_type]

    # 定义下载中心任务文件下载方法。
    def download_export_task(self, export_task, data_type, start_date=None, end_date=None, output_dir=None):

        """
        下载下载中心任务对应的 Excel 文件。

        :param export_task: 下载中心任务记录。
        :type export_task: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: 本地 Excel 文件路径。
        :rtype: str
        """

        # 读取下载中心任务文件地址。
        file_url = str(export_task.get("fileUrl") or "")

        # 校验任务文件地址是否存在。
        if not file_url:

            # 抛出任务文件地址缺失异常。
            raise RuntimeError(f"{self.company_name} {data_type} 下载中心任务缺少 fileUrl：{export_task}")

        # 获取二段签名下载地址。
        signed_url = self.get_signed_download_url(file_url)

        # 标准化签名下载地址中的非 ASCII 路径。
        request_url = self.normalize_download_url(signed_url)

        # 请求签名下载地址。
        result = self.http.request("GET", request_url, headers=self.build_file_download_headers(), timeout=120)

        # 构建本地输出文件路径。
        output_path = self.build_export_output_path(export_task, data_type, start_date, end_date, output_dir, file_url)

        # 创建本地输出目录。
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 写入 Excel 文件字节。
        with open(output_path, "wb") as file_obj:

            # 保存响应体到本地文件。
            file_obj.write(result.body)

        # 打印下载完成日志。
        self.ph.success(self.ph.join(self.ph.kv("文件下载完成", data_type, "green"), self.ph.kv("路径", self.ph.path(output_path), "cyan")))

        # 返回本地输出文件路径。
        return output_path

    # 定义下载地址标准化方法。
    def normalize_download_url(self, url):

        """
        标准化下载地址中的非 ASCII 路径字符。

        :param url: 原始下载地址。
        :type url: str
        :return: 标准化后的下载地址。
        :rtype: str
        """

        # 解析下载地址结构。
        parsed_url = urlparse(url)

        # 百分号编码下载地址路径。
        encoded_path = quote(parsed_url.path, safe="/%")

        # 返回标准化下载地址。
        return urlunparse((parsed_url.scheme, parsed_url.netloc, encoded_path, parsed_url.params, parsed_url.query, parsed_url.fragment))

    # 定义二段签名下载地址获取方法。
    def get_signed_download_url(self, file_url):

        """
        获取下载中心文件的二段签名下载地址。

        :param file_url: 下载中心任务文件地址。
        :type file_url: str
        :return: 签名下载地址。
        :rtype: str
        """

        # 构建签名接口查询参数。
        query_string = urlencode({"url": file_url})

        # 拼接签名接口地址。
        request_url = f"{self.sign_url_api_url}?{query_string}"

        # 请求签名接口。
        result = self.http.request("GET", request_url, headers=self.build_authorized_headers())

        # 解析签名接口响应。
        response_data = self.decode_json_response(result)

        # 提取签名下载地址。
        signed_url = self.extract_signed_url(response_data)

        # 校验签名下载地址是否存在。
        if not signed_url:

            # 抛出签名地址缺失异常。
            raise RuntimeError(f"{self.company_name} 下载签名接口未返回 url：{response_data}")

        # 返回签名下载地址。
        return signed_url

    # 定义签名下载地址提取方法。
    def extract_signed_url(self, response_data):

        """
        从签名接口响应中提取下载地址。

        :param response_data: 签名接口响应数据。
        :type response_data: dict
        :return: 签名下载地址。
        :rtype: str
        """

        # 读取顶层下载地址。
        direct_url = str(response_data.get("url") or "")

        # 判断顶层下载地址是否存在。
        if direct_url:

            # 返回顶层下载地址。
            return direct_url

        # 读取 result 字段。
        result_data = response_data.get("result")

        # 判断 result 字段是否为字典。
        if isinstance(result_data, dict):

            # 返回 result 内部下载地址。
            return str(result_data.get("url") or "")

        # 返回空下载地址。
        return ""

    # 定义文件下载请求头构建方法。
    def build_file_download_headers(self):

        """
        构建文件下载请求头。

        :return: 文件下载请求头。
        :rtype: dict
        """

        # 返回文件下载请求头。
        return {"Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": self.download_center_url, "User-Agent": self.http.user_agent()}

    # 定义导出文件输出路径构建方法。
    def build_export_output_path(self, export_task, data_type, start_date=None, end_date=None, output_dir=None, file_url=""):

        """
        构建下载中心导出文件的本地输出路径。

        :param export_task: 下载中心任务记录。
        :type export_task: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :param file_url: 下载中心任务文件地址。
        :type file_url: str
        :return: 本地输出路径。
        :rtype: str
        """

        # 读取输出目录。
        target_dir = output_dir or os.getcwd()

        # 构建标准业务文件名。
        raw_file_name = self.build_output_file_name(data_type, start_date, end_date, file_url)

        # 清洗本地文件名。
        file_name = self.sanitize_file_name(raw_file_name)

        # 返回本地文件完整路径。
        return os.path.join(target_dir, file_name)

    # 定义标准输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date=None, end_date=None, file_url=""):

        """
        构建高济健康 SRM 标准输出文件名。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param file_url: 下载中心任务文件地址。
        :type file_url: str
        :return: 标准输出文件名。
        :rtype: str
        """

        # 读取下载文件扩展名。
        extension_name = self.extract_file_extension(file_url)

        # 读取公共任务层传入的统一日期范围。
        date_range = getattr(self, "_ddi_date_range", None)

        # 读取当前任务日期模式。
        date_mode = getattr(date_range, "mode", "custom")

        # 读取最终生效的开始日期。
        effective_start_date = getattr(date_range, "start_date", "") or start_date

        # 读取最终生效的结束日期。
        effective_end_date = getattr(date_range, "end_date", "") or end_date

        # 读取业务日期。
        query_date = self.resolve_output_query_date(data_type, effective_start_date, effective_end_date)

        # 初始化下载命名工具。
        watcher = DownloadWatcher("")

        # 返回公共命名工具生成的文件名。
        return watcher.build_target_name(self.company_name, data_type, query_date, extension_name, start_date=effective_start_date, end_date=effective_end_date, date_mode=date_mode)


    # 定义输出日期范围文本构建方法。
    def build_output_date_part(self, start_date=None, end_date=None):

        """
        构建导出文件名中的日期范围文本。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 日期范围文本。
        :rtype: str
        """

        # 判断起止日期是否完整。
        if start_date and end_date:

            # 返回起止日期范围。
            return f"{start_date}_至_{end_date}"

        # 判断结束日期是否存在。
        if end_date:

            # 返回结束日期文本。
            return str(end_date)

        # 判断开始日期是否存在。
        if start_date:

            # 返回开始日期文本。
            return str(start_date)

        # 返回当前日期文本。
        return datetime.now().strftime("%Y-%m-%d")

    # 定义文件扩展名提取方法。
    def extract_file_extension(self, file_url):

        """
        从下载中心文件地址中提取文件扩展名。

        :param file_url: 下载中心任务文件地址。
        :type file_url: str
        :return: 文件扩展名。
        :rtype: str
        """

        # 解析文件地址路径。
        path_text = unquote(urlparse(file_url).path)

        # 读取路径中的文件名。
        base_name = os.path.basename(path_text)

        # 拆分文件扩展名。
        _, extension_name = os.path.splitext(base_name)

        # 判断扩展名是否存在。
        if extension_name:

            # 返回原始扩展名。
            return extension_name

        # 返回默认 Excel 扩展名。
        return ".xlsx"

    # 定义本地文件名清洗方法。
    def sanitize_file_name(self, file_name):

        """
        清洗 Windows 本地文件名中的非法字符。

        :param file_name: 原始文件名。
        :type file_name: str
        :return: 清洗后的文件名。
        :rtype: str
        """

        # 初始化清洗后的字符列表。
        cleaned_chars = []

        # 遍历原始文件名字符。
        for char in str(file_name):

            # 判断字符是否为 Windows 文件名非法字符。
            if char in '<>:"/\\|?*':

                # 写入替代下划线。
                cleaned_chars.append("_")

                # 继续处理下一个字符。
                continue

            # 写入原始字符。
            cleaned_chars.append(char)

        # 拼接清洗后的文件名。
        cleaned_name = "".join(cleaned_chars).strip()

        # 返回非空文件名。
        return cleaned_name or "download.xlsx"

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        通过高济健康 SRM 下载中心导出业务 Excel。

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

        # 调用平台导出流程生成 Excel 文件。
        return self.export_flow(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

