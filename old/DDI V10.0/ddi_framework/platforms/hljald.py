# -*- coding: utf-8 -*-
"""
黑龙江省阿拉丁医药有限公司伙伴自助系统协议适配器。

本模块负责黑龙江省阿拉丁医药有限公司伙伴自助系统的验证码获取、协议登录和 Cookie 保存。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入内存字节流模块。
from io import BytesIO

# 导入操作系统路径模块。
import os

# 导入随机数模块。
import random

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入 URL 参数编码函数。
from urllib.parse import urlencode

# 导入验证码处理器。
from ddi_framework import CaptchaSolver

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义黑龙江阿拉丁伙伴自助系统协议适配器。
class HljaldPlatform(BasePlatform):

    """
    黑龙江阿拉丁伙伴自助系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 黑龙江阿拉丁平台适配器实例。
    :rtype: HljaldPlatform
    """

    # 定义黑龙江阿拉丁适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化黑龙江阿拉丁平台适配器。

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
        self.login_page_url = account.get("登录页", "http://flow.hljbnfk.com/login?redirect=%2Findex")

        # 保存平台根地址。
        self.base_url = self.login_page_url.split("/login", 1)[0]

        # 保存验证码接口地址。
        self.captcha_api_url = account.get("验证码接口", urljoin(self.base_url, "/prod-api/captchaImage"))

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", urljoin(self.base_url, "/prod-api/login"))

        # 保存采购进项查询接口地址。
        self.purchase_query_url = account.get("采购进项接口", urljoin(self.base_url, "/prod-api/PurFlow/flowp/list"))

        # 保存销售流向查询接口地址。
        self.sale_query_url = account.get("销售流向接口", urljoin(self.base_url, "/prod-api/SaleFlow/flow/list"))

        # 保存库存查询接口地址。
        self.stock_query_url = account.get("库存接口", urljoin(self.base_url, "/prod-api/InvFlow/flowi/list"))

        # 保存默认分页大小。
        self.page_size = int(account.get("分页大小", 100))

        # 初始化登录令牌。
        self.login_token = ""

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化验证码处理器。
        self.captcha_solver = CaptchaSolver()

    # 定义黑龙江阿拉丁登录方法。
    def login(self):

        """
        执行黑龙江阿拉丁协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("黑龙江阿拉丁登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 请求登录页并初始化 Cookie。
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

                # 构建验证码答案候选列表。
                captcha_codes = self.build_captcha_code_candidates(captcha_context["image_bytes"])

                # 初始化本轮候选通过状态。
                captcha_accepted = False

                # 遍历当前验证码候选答案。
                for captcha_code in captcha_codes:

                    # 打印验证码识别完成日志。
                    self.ph.info(self.ph.kv("图片验证码候选", captcha_code, "cyan"))

                    # 构建登录请求体。
                    payload = self.build_login_payload(captcha_code, captcha_context["uuid"])

                    # 打印正式登录请求日志。
                    self.ph.info("提交正式登录请求: /prod-api/login")

                    # 发送登录请求。
                    result = self.post_login(payload)

                    # 解析登录响应。
                    login_result = self.http.decode_json(result)

                    # 判断登录是否成功。
                    if self.is_login_success(login_result):

                        # 保存登录令牌。
                        self.login_token = str(login_result.get("token") or "")

                        # 标记当前验证码已经通过。
                        captcha_accepted = True

                        # 打印登录成功日志。
                        self.ph.success(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"))

                        # 返回登录结果。
                        return login_result

                    # 记录登录失败原因。
                    last_error = self.extract_login_message(login_result)

                    # 打印候选未通过日志。
                    self.ph.warning(self.ph.kv("验证码候选未通过", captcha_code, "yellow"))

                # 判断当前验证码是否未通过。
                if not captcha_accepted:

                    # 打印验证码或登录失败日志。
                    self.ph.warning("登录校验未通过，准备刷新验证码")

            # 处理验证码识别或登录提交异常。
            except Exception as error:

                # 记录当前异常原因。
                last_error = str(error)

                # 打印验证码处理失败日志。
                self.ph.warning("图片验证码识别未通过，准备刷新验证码")

            # 最后一轮失败后跳过等待。
            if retry_index >= max_retries - 1:

                # 进入下一轮循环结束判断。
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

        # 打印验证码请求日志。
        self.ph.info("请求图片验证码: /prod-api/captchaImage")

        # 请求验证码接口。
        result = self.get_json(self.captcha_api_url)

        # 解析验证码接口响应。
        data = self.http.decode_json(result)

        # 校验验证码接口响应状态。
        if int(data.get("code", 0)) != 200:

            # 抛出验证码获取异常。
            raise RuntimeError(f"{self.company_name} 获取图片验证码失败：{data.get('msg') or data}")

        # 读取验证码图片 Base64 文本。
        image_base64 = str(data.get("img") or "")

        # 读取验证码会话编号。
        captcha_uuid = str(data.get("uuid") or "")

        # 校验验证码图片与会话编号。
        if not image_base64 or not captcha_uuid:

            # 抛出验证码数据缺失异常。
            raise RuntimeError(f"{self.company_name} 验证码响应缺少图片或 uuid")

        # 解码验证码图片字节。
        image_bytes = base64.b64decode(image_base64.split(",", 1)[-1])

        # 返回验证码上下文。
        return {"uuid": captcha_uuid, "image_bytes": image_bytes}

    # 定义验证码答案识别方法。
    def solve_captcha_code(self, image_bytes):

        """
        识别验证码答案。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :return: 验证码答案。
        :rtype: str
        """

        # 构建验证码答案候选列表。
        captcha_codes = self.build_captcha_code_candidates(image_bytes)

        # 返回首个验证码候选答案。
        if captcha_codes:

            # 返回首个候选答案。
            return captcha_codes[0]

        # 抛出验证码识别异常。
        raise RuntimeError("图片验证码识别为空")

    # 定义验证码答案候选构建方法。
    def build_captcha_code_candidates(self, image_bytes):

        """
        构建验证码答案候选列表。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :return: 验证码答案候选列表。
        :rtype: list[str]
        """

        # 初始化验证码答案候选列表。
        captcha_codes = []

        # 构建公共算式验证码候选。
        math_codes = self.captcha_solver.build_math_code_candidates(image_bytes)

        # 遍历公共算式验证码候选。
        for math_code in math_codes:

            # 保存非重复候选答案。
            if math_code and math_code not in captcha_codes:

                # 追加候选答案。
                captcha_codes.append(math_code)

        # 识别验证码原始文本。
        raw_text = self.recognize_captcha_text(image_bytes)

        # 解析算式验证码答案。
        math_code = self.parse_math_captcha(raw_text)

        # 保存平台算式解析答案。
        if math_code and math_code not in captcha_codes:

            # 追加平台算式解析答案。
            captcha_codes.append(math_code)

        # 清洗普通验证码文本。
        cleaned_text = "".join([char for char in raw_text if char.isalnum()])

        # 保存普通验证码文本。
        if cleaned_text and cleaned_text not in captcha_codes:

            # 追加普通验证码文本。
            captcha_codes.append(cleaned_text)

        # 返回候选答案列表。
        return captcha_codes[:3]

    # 定义验证码文本识别方法。
    def recognize_captcha_text(self, image_bytes):

        """
        识别验证码文本并合并多种预处理结果。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :return: 验证码识别文本。
        :rtype: str
        """

        # 初始化候选识别文本列表。
        candidate_texts = []

        # 遍历验证码图片预处理结果。
        for prepared_bytes in self.build_captcha_candidates(image_bytes):

            # 识别当前预处理图片。
            candidate_text = self.captcha_solver.solve_raw_text_image_with_ranges(prepared_bytes, "0123456789+-*/")

            # 保存非空候选文本。
            if candidate_text:

                # 追加候选识别文本。
                candidate_texts.append(candidate_text)

        # 遍历候选文本优先返回可解析算式。
        for candidate_text in candidate_texts:

            # 判断候选文本是否可解析为算式。
            if self.parse_math_captcha(candidate_text):

                # 返回可解析候选文本。
                return candidate_text

        # 返回首个候选文本。
        return candidate_texts[0] if candidate_texts else ""

    # 定义验证码图片候选构建方法。
    def build_captcha_candidates(self, image_bytes):

        """
        构建验证码识别候选图片。

        :param image_bytes: 原始验证码图片字节流。
        :type image_bytes: bytes
        :return: 候选图片字节流列表。
        :rtype: list[bytes]
        """

        # 导入图片处理对象。
        from PIL import Image

        # 使用内存字节流读取验证码图片。
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # 初始化候选图片列表。
        candidates = [image_bytes]

        # 遍历固定裁剪区域。
        for crop_box in [(0, 0, 100, 60), (0, 0, 110, 60), (5, 0, 105, 60), (0, 4, 110, 56)]:

            # 裁剪表达式主体区域。
            cropped_image = image.crop(crop_box)

            # 放大表达式主体区域。
            resized_image = cropped_image.resize((cropped_image.width * 4, cropped_image.height * 4), Image.Resampling.LANCZOS)

            # 追加普通放大候选图片。
            candidates.append(self.image_to_png_bytes(resized_image))

            # 追加蓝色笔画候选图片。
            candidates.append(self.extract_blue_strokes(resized_image))

        # 返回候选图片列表。
        return candidates

    # 定义蓝色笔画提取方法。
    def extract_blue_strokes(self, image):

        """
        提取验证码中的蓝色字符笔画。

        :param image: 验证码图片对象。
        :type image: Image.Image
        :return: 蓝色笔画二值化 PNG 字节流。
        :rtype: bytes
        """

        # 导入图片处理对象。
        from PIL import Image

        # 读取图片宽高。
        width, height = image.size

        # 创建白底图片。
        output_image = Image.new("RGB", (width, height), "white")

        # 遍历横向像素。
        for x in range(width):

            # 遍历纵向像素。
            for y in range(height):

                # 读取像素 RGB。
                red, green, blue = image.getpixel((x, y))

                # 判断像素是否属于蓝色笔画。
                if blue > 70 and blue > red + 25 and blue > green + 10:

                    # 写入黑色笔画像素。
                    output_image.putpixel((x, y), (0, 0, 0))

        # 返回 PNG 字节流。
        return self.image_to_png_bytes(output_image)

    # 定义图片转 PNG 字节方法。
    def image_to_png_bytes(self, image):

        """
        转换图片对象为 PNG 字节流。

        :param image: 图片对象。
        :type image: Image.Image
        :return: PNG 字节流。
        :rtype: bytes
        """

        # 创建内存字节流。
        buffer = BytesIO()

        # 保存图片为 PNG。
        image.save(buffer, format="PNG")

        # 返回 PNG 字节数据。
        return buffer.getvalue()

    # 定义算式验证码解析方法。
    def parse_math_captcha(self, raw_text):

        """
        解析算式验证码答案。

        :param raw_text: 原始验证码识别文本。
        :type raw_text: str
        :return: 算式答案或空字符串。
        :rtype: str
        """

        # 统一算式符号文本。
        normalized_text = self.normalize_math_text(raw_text)

        # 读取算式中的两个数字和运算符。
        match = re.search(r"(\d+)\s*([+\-*/])\s*(\d+)", normalized_text)

        # 未识别到算式时返回空字符串。
        if not match:

            # 返回空算式答案。
            return ""

        # 读取左侧数字。
        left_value = int(match.group(1))

        # 读取运算符。
        operator = match.group(2)

        # 读取右侧数字。
        right_value = int(match.group(3))

        # 处理加法算式。
        if operator == "+":

            # 返回加法结果。
            return str(left_value + right_value)

        # 处理减法算式。
        if operator == "-":

            # 返回减法结果。
            return str(left_value - right_value)

        # 处理乘法算式。
        if operator == "*":

            # 返回乘法结果。
            return str(left_value * right_value)

        # 处理除法算式。
        if operator == "/" and right_value != 0:

            # 返回整数除法结果。
            return str(left_value // right_value)

        # 返回空算式答案。
        return ""

    # 定义算式文本归一化方法。
    def normalize_math_text(self, raw_text):

        """
        归一化算式验证码识别文本。

        :param raw_text: 原始验证码识别文本。
        :type raw_text: str
        :return: 归一化算式文本。
        :rtype: str
        """

        # 转换原始文本为字符串。
        text = str(raw_text or "")

        # 移除空白字符。
        text = re.sub(r"\s+", "", text)

        # 替换常见乘法符号。
        text = text.replace("×", "*").replace("X", "*").replace("x", "*")

        # 替换常见除法符号。
        text = text.replace("÷", "/")

        # 替换常见减号误识别。
        text = text.replace("一", "-").replace("_", "-")

        # 替换常见加号误识别。
        text = re.sub(r"(?<=\d)[tT](?=\d)", "+", text)

        # 保留算式相关字符。
        text = "".join([char for char in text if char.isdigit() or char in "+-*/"])

        # 返回归一化文本。
        return text

    # 定义登录请求体构建方法。
    def build_login_payload(self, captcha_code, captcha_uuid):

        """
        构建登录请求体。

        :param captcha_code: 验证码答案。
        :type captcha_code: str
        :param captcha_uuid: 验证码会话编号。
        :type captcha_uuid: str
        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录 JSON 字段。
        return {
            "username": self.clean_login_name(),
            "password": self.clean_login_password(),
            "code": captcha_code,
            "uuid": captcha_uuid,
        }

    # 定义登录请求提交方法。
    def post_login(self, payload):

        """
        提交登录请求。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 编码 JSON 请求体。
        request_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 构建登录请求头。
        headers = self.build_ruoyi_json_headers()

        # 发送登录请求。
        return self.http.request("POST", self.login_api_url, headers=headers, data=request_body)

    # 定义 JSON GET 请求方法。
    def get_json(self, url):

        """
        发送 RuoYi JSON GET 请求。

        :param url: 请求地址。
        :type url: str
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建 JSON 请求头。
        headers = self.build_ruoyi_json_headers()

        # 发送 GET 请求。
        return self.http.request("GET", url, headers=headers)

    # 定义 RuoYi JSON 请求头构建方法。
    def build_ruoyi_json_headers(self):

        """
        构建 RuoYi 登录阶段 JSON 请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回 RuoYi 登录阶段请求头。
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": self.base_url,
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
            "isToken": "false",
            "repeatSubmit": "false",
        }

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断登录响应是否表示成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 返回登录成功状态。
        return int(login_result.get("code", 0)) == 200 and bool(login_result.get("token") or login_result.get("msg"))

    # 定义登录响应消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取登录响应消息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录响应消息。
        :rtype: str
        """

        # 返回响应消息或默认成功文本。
        return str(login_result.get("msg") or login_result)

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

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录 Cookie 与令牌。

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

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询黑龙江阿拉丁流向数据。

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
        query_result = self.query_hljald_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出黑龙江阿拉丁流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出结果。
        :rtype: str
        """

        # 使用分页查询结果生成本地 Excel 文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询黑龙江阿拉丁流向数据并生成 Excel。

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

        # 查询指定类型完整数据。
        query_result = self.query_hljald_data(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], query_result["columns"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{query_result['total']} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义黑龙江阿拉丁数据查询方法。
    def query_hljald_data(self, data_type, start_date, end_date):

        """
        查询黑龙江阿拉丁指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准化查询结果。
        :rtype: dict
        """

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 校验日期类数据的开始日期。
        if data_type in ["配送流向", "购进流向"] and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验日期类数据的结束日期。
        if data_type in ["配送流向", "购进流向"] and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

        # 初始化分页起始页码。
        page_number = 1

        # 初始化累计数据行。
        all_rows = []

        # 初始化总记录数。
        total_count = None

        # 循环读取分页数据。
        while True:

            # 构建当前页查询地址。
            query_url = self.build_query_url(data_type, page_number, self.page_size, start_date, end_date)

            # 打印分页查询日志。
            self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", f"pageNum={page_number}", "cyan"), self.ph.kv("pageSize", self.page_size, "cyan")))

            # 请求当前页数据。
            result = self.get_authorized_json(query_url)

            # 解析当前页响应。
            data = self.http.decode_json(result)

            # 校验当前页响应状态。
            self.validate_query_response(data, data_type)

            # 读取当前页数据行。
            page_rows = list(data.get("rows") or [])

            # 读取响应总数。
            total_count = int(data.get("total") or len(page_rows))

            # 追加当前页数据行。
            all_rows.extend(page_rows)

            # 打印当前页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "cyan")))

            # 判断是否已经读取完整。
            if len(all_rows) >= total_count or not page_rows:

                # 结束分页循环。
                break

            # 递增页码。
            page_number += 1

        # 返回标准化查询结果。
        return {"rows": all_rows, "total": total_count or len(all_rows), "columns": self.build_excel_columns(data_type, all_rows)}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 校验数据类型是否存在于接口映射。
        if data_type not in ["配送流向", "购进流向", "库存"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"黑龙江阿拉丁暂未接入数据类型：{data_type}")

    # 定义查询地址构建方法。
    def build_query_url(self, data_type, page_number, page_size, start_date, end_date):

        """
        构建分页查询地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param page_number: 页码。
        :type page_number: int
        :param page_size: 每页条数。
        :type page_size: int
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 分页查询地址。
        :rtype: str
        """

        # 读取当前数据类型的接口地址。
        base_query_url = self.resolve_query_url(data_type)

        # 构建基础分页参数。
        params = {"pageNum": page_number, "pageSize": page_size}

        # 写入采购日期参数。
        if data_type == "购进流向":

            # 写入采购开始日期。
            params["params[beginPurDate]"] = start_date

            # 写入采购结束日期。
            params["params[endPurDate]"] = end_date

        # 写入销售日期参数。
        if data_type == "配送流向":

            # 写入销售开始日期。
            params["params[beginSaleDate]"] = start_date

            # 写入销售结束日期。
            params["params[endSaleDate]"] = end_date

        # 返回完整查询地址。
        return f"{base_query_url}?{urlencode(params)}"

    # 定义查询接口地址解析方法。
    def resolve_query_url(self, data_type):

        """
        解析数据类型对应的查询接口地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询接口地址。
        :rtype: str
        """

        # 返回采购进项接口地址。
        if data_type == "购进流向":

            # 返回采购进项查询接口。
            return self.purchase_query_url

        # 返回销售流向接口地址。
        if data_type == "配送流向":

            # 返回销售流向查询接口。
            return self.sale_query_url

        # 返回库存接口地址。
        return self.stock_query_url

    # 定义授权 JSON GET 请求方法。
    def get_authorized_json(self, url):

        """
        发送带登录令牌的 JSON GET 请求。

        :param url: 请求地址。
        :type url: str
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建授权请求头。
        headers = self.build_authorized_json_headers()

        # 发送 GET 请求。
        return self.http.request("GET", url, headers=headers)

    # 定义授权 JSON 请求头构建方法。
    def build_authorized_json_headers(self):

        """
        构建带登录令牌的 JSON 请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回授权请求头。
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Authorization": f"Bearer {self.login_token}",
            "Connection": "keep-alive",
            "Referer": self.base_url + "/allflow/flow",
            "User-Agent": self.http.user_agent(),
        }

    # 定义查询响应校验方法。
    def validate_query_response(self, data, data_type):

        """
        校验查询接口响应状态。

        :param data: 查询响应数据。
        :type data: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 校验响应编码是否为成功。
        if int(data.get("code", 0)) != 200:

            # 抛出查询接口异常。
            raise RuntimeError(f"{self.company_name} {data_type}查询失败：{data.get('msg') or data}")

    # 定义 Excel 列映射构建方法。
    def build_excel_columns(self, data_type, rows):

        """
        构建黑龙江阿拉丁 Excel 列映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :return: Excel 列映射。
        :rtype: dict
        """

        # 读取预设列映射。
        predefined_columns = self.build_predefined_columns(data_type)

        # 返回预设列映射。
        if predefined_columns:

            # 返回固定列映射。
            return predefined_columns

        # 初始化动态列映射。
        dynamic_columns = {}

        # 遍历数据行生成动态列。
        for row in rows:

            # 遍历当前行字段。
            for field_name in row.keys():

                # 保存未出现过的字段名。
                dynamic_columns.setdefault(field_name, field_name)

        # 返回动态列映射。
        return dynamic_columns

    # 定义预设 Excel 列映射构建方法。
    def build_predefined_columns(self, data_type):

        """
        构建黑龙江阿拉丁预设 Excel 列映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 预设 Excel 列映射。
        :rtype: dict
        """

        # 返回采购进项列映射。
        if data_type == "购进流向":

            # 返回采购进项字段映射。
            return {
                "orderId": "单据号",
                "proEnterprise": "生产企业",
                "purDate": "采购日期",
                "inCompanyCode": "进货单位编码",
                "inCompanyName": "进货单位名称",
                "goodsCode": "商品编码",
                "goodsName": "商品名称",
                "goodsSpec": "商品规格",
                "unit": "单位",
                "batchNumber": "批号",
                "qty": "数量",
                "inPrice": "进货价格",
                "inAmount": "进货金额",
                "validDate": "有效期",
                "ownerName": "业主名称",
            }

        # 返回销售流向列映射。
        if data_type == "配送流向":

            # 返回销售流向字段映射。
            return {
                "saleDate": "日期",
                "proEnterprise": "生产企业",
                "companyCode": "单位编码",
                "companyName": "单位名称",
                "inCompanyCode": "进货单位编码",
                "inCompanyName": "进货单位名称",
                "goodsCode": "商品编码",
                "goodsName": "商品名称",
                "goodsSpec": "商品规格",
                "unit": "单位",
                "batchNumber": "批号",
                "qty": "数量",
                "salePrice": "销售价格",
                "saleAmount": "销售金额",
                "validDate": "有效期",
                "ownerName": "业主名称",
            }

        # 返回库存列映射。
        return {
            "invDate": "库存日期",
            "goodsCode": "商品编码",
            "goodsName": "商品名称",
            "proEnterprise": "生产企业",
            "goodsSpec": "商品规格",
            "unit": "单位",
            "batchNumber": "批号",
            "qty": "数量",
            "validDate": "有效期",
            "ownerName": "业主名称",
        }

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建黑龙江阿拉丁输出文件名。

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

    # 定义月份标签构建方法。
    def build_month_label(self, start_date):

        """
        构建月份文件标签。

        :param start_date: 查询开始日期。
        :type start_date: str
        :return: 月份标签。
        :rtype: str
        """

        # 导入日期解析模块。
        from datetime import datetime

        # 解析开始日期。
        date_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 返回 yy.m 标签。
        return f"{date_value.year % 100}.{date_value.month}"

    # 定义库存日期标签构建方法。
    def build_stock_date_label(self, end_date):

        """
        构建库存文件日期标签。

        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 库存日期标签。
        :rtype: str
        """

        # 导入日期处理模块。
        from datetime import datetime

        # 读取库存日期字符串。
        stock_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # 解析导出日期。
        date_value = datetime.strptime(stock_date, "%Y-%m-%d")

        # 返回 yy.m.d 标签。
        return f"{date_value.year % 100}.{date_value.month}.{date_value.day}"

    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, columns, output_path, sheet_name):

        """
        写入黑龙江阿拉丁查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param columns: Excel 列映射。
        :type columns: dict
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

        # 读取接口字段列表。
        field_names = list(columns.keys())

        # 写入中文表头行。
        worksheet.append([columns[field_name] for field_name in field_names])

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按列映射顺序组装一行数据。
            worksheet.append([row.get(field_name, "") for field_name in field_names])

        # 遍历所有导出列设置列宽。
        for column_index, header_name in enumerate(columns.values(), start=1):

            # 读取当前列字母。
            column_letter = get_column_letter(column_index)

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

            # 文件不存在时直接返回。
            return

        # 捕获删除文件时的占用异常。
        try:

            # 删除已有同名文件。
            os.remove(output_path)

        # 处理文件被占用导致的删除异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error
