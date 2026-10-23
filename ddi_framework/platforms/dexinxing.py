# -*- coding: utf-8 -*-
"""
华润德信行流向查询平台协议适配器。

本模块负责华润江苏医药有限公司德信行分公司流向查询平台（kscx.crcjs.cn，
ThinkPHP 服务端渲染）的图形验证码登录、五类型数据查询、HTML 表格解析、
分页汇聚和原始字段 Excel 落地。
登录链路为：登录页建立会话 → 图形验证码识别 → checkLogin 明文表单提交 →
跳转提示页判定成败。
数据链路为：按类型端点 POST 表单（三流向带日期区间、两库存快照无日期）→
解析响应 HTML 数据表 → 按 共N条 总账与空页终止口径翻页汇聚。
平台响应缓慢，全部数据请求采用 300 秒长超时。
"""

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入随机数模块。
import random

# 导入操作系统路径模块。
import os

# 导入 URL 编码函数。
from urllib.parse import urlencode

# 导入 HTML 解析模块。
from bs4 import BeautifulSoup

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义平台站点根地址常量。
BASE_URL = "http://kscx.crcjs.cn"

# 定义登录页地址常量。
LOGIN_PAGE_URL = "http://kscx.crcjs.cn/Admin/Public/login"

# 定义验证码接口路径常量。
CAPTCHA_API_PATH = "/admin/public/verify/"

# 定义登录提交接口路径常量。
LOGIN_API_PATH = "/admin/public/checkLogin/"

# 定义验证码字符集常量（字母数字全集）。
CAPTCHA_CHARSET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# 定义主框架页路径常量（数据查询引用页）。
MAIN_FRAME_PATH = "/admin/index"


# 定义华润德信行流向查询平台协议适配器。
class DexinxingPlatform(BasePlatform):

    """
    华润德信行流向查询平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 华润德信行平台适配器实例。
    :rtype: DexinxingPlatform
    """

    # 定义平台支持的接入数据类型。
    SUPPORTED_TYPES = ["配送流向", "购进流向", "纯销流向", "大仓库存", "门店库存"]

    # 定义按日期区间查询的流向类数据类型清单。
    FLOW_TYPES = ["配送流向", "购进流向", "纯销流向"]

    # 定义数据类型到查询端点路径的映射。
    TYPE_ENDPOINTS = {
        "配送流向": "/lssales/index.html",
        "购进流向": "/lssupplys/index.html",
        "纯销流向": "/shopsales/index.html",
        "大仓库存": "/lsstore/index.html",
        "门店库存": "/shopstore/index.html",
    }

    # 定义单页行数。
    PAGE_SIZE = 100

    # 定义分页安全上限页数。
    MAX_PAGES = 500

    # 定义登录验证码最大识别尝试次数。
    MAX_LOGIN_ATTEMPTS = 8

    # 定义数据请求超时秒数（慢平台长超时）。
    QUERY_TIMEOUT = 300

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化华润德信行平台适配器。

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

        # 保存平台站点根地址。
        self.base_url = str(account.get("站点根地址", BASE_URL)).rstrip("/")

        # 保存登录页地址。
        self.login_page_url = str(account.get("登录页", LOGIN_PAGE_URL))

        # 初始化带 Cookie 管理的协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化验证码识别器。
        self.captcha_solver = CaptchaSolver()

        # 初始化登录状态标记。
        self.logged_in = False

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验平台数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否在支持清单内。
        if data_type not in self.SUPPORTED_TYPES:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"华润德信行平台暂未接入: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 仅流向类按日期区间查询，两类库存按当前快照查询。
        return data_type in self.FLOW_TYPES

    # 定义公共请求头构建方法。
    def build_web_headers(self, referer):

        """
        构建页面交互请求头。

        :param referer: 引用页地址。
        :type referer: str
        :return: 请求头字典。
        :rtype: dict
        """

        # 组装页面请求头字典。
        return {
            "User-Agent": self.http.user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer,
        }

    # 定义验证码图片获取方法。
    def fetch_captcha_image(self):

        """
        请求会话绑定的图形验证码图片。

        :return: 验证码图片字节。
        :rtype: bytes
        """

        # 发送验证码图片请求。
        result = self.http.request("GET", f"{self.base_url}{CAPTCHA_API_PATH}", headers=self.build_web_headers(self.login_page_url), timeout=120)

        # 返回图片字节。
        return result.body

    # 定义验证码文本识别方法。
    def solve_captcha_code(self, image_bytes):

        """
        识别登录图形验证码。

        :param image_bytes: 验证码图片字节。
        :type image_bytes: bytes
        :return: 验证码文本。
        :rtype: str
        """

        # 按字母数字字符集识别验证码。
        raw_text = self.captcha_solver.solve_raw_text_image_with_ranges(image_bytes, CAPTCHA_CHARSET)

        # 清理非字母数字字符。
        captcha_code = re.sub(r"[^0-9A-Za-z]", "", raw_text or "")

        # 返回验证码文本。
        return captcha_code

    # 定义登录表单提交方法。
    def submit_login(self, captcha_code):

        """
        提交账号密码与验证码明文表单。

        :param captcha_code: 验证码文本。
        :type captcha_code: str
        :return: 登录响应 HTML 文本。
        :rtype: str
        """

        # 构建登录表单（平台明文口径）。
        payload = {"account": self.clean_login_name(), "password": self.clean_login_password(), "verify": captcha_code}

        # 编码请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送登录提交请求。
        result = self.http.request("POST", f"{self.base_url}{LOGIN_API_PATH}", headers=self.build_web_headers(self.login_page_url), data=data, timeout=120, allow_http_error=True)

        # 返回响应文本。
        return result.body.decode("utf-8", "replace")

    # 定义登录结果判定方法。
    def is_login_success(self, response_text):

        """
        按跳转提示页判定登录是否成功。

        :param response_text: 登录响应 HTML 文本。
        :type response_text: str
        :return: 登录是否成功。
        :rtype: bool
        """

        # 跳转提示页包含登录成功字样即为成功。
        return "登录成功" in response_text

    # 定义错误消息提取方法。
    def extract_error_message(self, response_text):

        """
        从跳转提示页提取错误消息文本。

        :param response_text: 登录响应 HTML 文本。
        :type response_text: str
        :return: 错误消息文本。
        :rtype: str
        """

        # 解析 HTML 并提取可见文本。
        soup = BeautifulSoup(response_text, "html.parser")

        # 返回压缩后的纯文本。
        return " ".join(soup.get_text(strip=True).split())[:80]

    # 定义平台登录方法。
    def login(self):

        """
        执行华润德信行平台协议登录。

        :return: 登录结果字典。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("德信行登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录配置日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("密码长度", len(self.clean_login_password()), "cyan"), self.ph.kv("密码指纹", self.mask_secret(self.clean_login_password()), "yellow")))

        # 访问登录页建立会话。
        self.http.request("GET", self.login_page_url, headers=self.build_web_headers(self.login_page_url), timeout=120)

        # 初始化最后一次失败原因。
        last_error = ""

        # 循环识别验证码并提交登录。
        for attempt_index in range(self.MAX_LOGIN_ATTEMPTS):

            # 打印验证码尝试日志。
            self.ph.info(self.ph.kv("验证码识别尝试", f"第 {attempt_index + 1}/{self.MAX_LOGIN_ATTEMPTS} 次", "cyan"))

            # 拉取会话绑定验证码并识别。
            captcha_code = self.solve_captcha_code(self.fetch_captcha_image())

            # 打印识别值日志。
            self.ph.info(self.ph.kv("验证码识别值", repr(captcha_code), "cyan"))

            # 提交登录表单。
            response_text = self.submit_login(captcha_code)

            # 判定登录成功。
            if self.is_login_success(response_text):

                # 置位登录状态标记。
                self.logged_in = True

                # 打印登录成功日志。
                self.ph.success(self.ph.kv("正式登录成功", self.clean_login_name(), "green"))

                # 返回登录结果。
                return {"登录": "成功"}

            # 记录失败原因。
            last_error = self.extract_error_message(response_text)

            # 打印失败日志。
            self.ph.warning(self.ph.kv("登录未通过（第 {0} 次）".format(attempt_index + 1), last_error, "yellow"))

            # 末轮失败后跳过等待。
            if attempt_index >= self.MAX_LOGIN_ATTEMPTS - 1:

                # 跳过末轮等待。
                continue

            # 随机等待后重试。
            time.sleep(random.uniform(1.0, 2.0))

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 德信行登录失败：{last_error}")

    # 定义登录态保障方法。
    def ensure_login(self):

        """
        确保当前会话已建立有效登录态。

        :return: None。
        :rtype: None
        """

        # 判断当前尚未登录。
        if not self.logged_in:

            # 执行平台登录流程。
            self.login()

    # 定义登录态重置方法。
    def reset_login(self):

        """
        重置登录态以供认证失效后重建会话。

        :return: None。
        :rtype: None
        """

        # 置位未登录标记。
        self.logged_in = False

    # 定义敏感文本掩码方法。
    def mask_secret(self, secret_text):

        """
        构建密码掩码文本。

        :param secret_text: 原始密码。
        :type secret_text: str
        :return: 密码掩码文本。
        :rtype: str
        """

        # 返回空密码标记。
        if not secret_text:

            # 返回空标记文本。
            return "<空>"

        # 返回短密码掩码。
        if len(secret_text) <= 2:

            # 返回等长星号掩码。
            return "*" * len(secret_text)

        # 返回首尾可见的密码掩码。
        return f"{secret_text[0]}***{secret_text[-1]}"

    # 定义查询负载构建方法。
    def build_query_payload(self, data_type, start_date, end_date, page_number):

        """
        构建指定类型的查询表单负载。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 页码。
        :type page_number: int
        :return: 查询表单负载。
        :rtype: dict
        """

        # 组装公共筛选字段（三项均留空表示不限商品）。
        payload = {"goodsid": "", "goodsname": "", "currencyname": "", "pageNum": str(page_number), "numberPage": str(self.PAGE_SIZE)}

        # 流向类追加日期区间。
        if data_type in self.FLOW_TYPES:

            # 写入起止日期。
            payload["begindate"] = start_date

            # 写入结束日期。
            payload["enddate"] = end_date

        # 返回查询负载。
        return payload

    # 定义总条数解析方法。
    def parse_total_count(self, response_text):

        """
        从响应页解析 共N条 形式的总条数。

        :param response_text: 响应 HTML 文本。
        :type response_text: str
        :return: 总条数或空值。
        :rtype: int | None
        """

        # 按共N条模式检索。
        matched = re.search(r"共\s*(\d+)\s*条", response_text)

        # 返回整数总条数或空值。
        return int(matched.group(1)) if matched else None

    # 定义数据表解析方法。
    def parse_table_rows(self, response_text):

        """
        解析响应页数据表为表头与数据行。

        :param response_text: 响应 HTML 文本。
        :type response_text: str
        :return: 表头清单与数据行字典列表元组。
        :rtype: tuple[list[str], list[dict]]
        """

        # 解析 HTML 文档。
        soup = BeautifulSoup(response_text, "html.parser")

        # 收集全部表格。
        tables = soup.find_all("table")

        # 无表格时返回空结果。
        if not tables:

            # 返回空表头与空数据行。
            return [], []

        # 取行数最多的表格作为数据表。
        table = max(tables, key=lambda item: len(item.find_all("tr")))

        # 读取全部行。
        rows = table.find_all("tr")

        # 无有效行时返回空结果。
        if len(rows) < 2:

            # 返回空表头与空数据行。
            return [], []

        # 读取表头单元格文本。
        header_cells = [cell.get_text(strip=True) for cell in rows[0].find_all(["th", "td"])]

        # 过滤空表头列（勾选框列）。
        kept_indexes = [index for index, name in enumerate(header_cells) if name]

        # 保留有效表头。
        headers = [header_cells[index] for index in kept_indexes]

        # 初始化数据行容器。
        data_rows = []

        # 遍历数据行。
        for row in rows[1:]:

            # 读取单元格文本。
            cells = [cell.get_text(strip=True) for cell in row.find_all("td")]

            # 跳过空行。
            if not cells:

                # 进入下一行。
                continue

            # 按保留列组装数据字典。
            data_rows.append({header_cells[index]: cells[index] if index < len(cells) else "" for index in kept_indexes})

        # 返回表头与数据行。
        return headers, data_rows

    # 定义响应是否为登录页判定方法。
    def is_login_page_response(self, response_text):

        """
        判定响应是否为登录页或会话失效跳转页。

        :param response_text: 响应 HTML 文本。
        :type response_text: str
        :return: 是否为登录页响应。
        :rtype: bool
        """

        # 按登录表单特征判定会话失效。
        return "checkLogin" in response_text or ("验证码" in response_text and "登录" in response_text)

    # 定义单页查询方法。
    def query_one_page(self, data_type, start_date, end_date, page_number, allow_relogin=True):

        """
        查询指定类型与页码的数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 页码。
        :type page_number: int
        :param allow_relogin: 认证失效时是否允许重建会话重试一次。
        :type allow_relogin: bool
        :return: 表头、数据行与总条数元组。
        :rtype: tuple[list[str], list[dict], int | None]
        """

        # 构建查询负载。
        payload = self.build_query_payload(data_type, start_date, end_date, page_number)

        # 编码请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送查询请求（慢平台长超时）。
        result = self.http.request("POST", f"{self.base_url}{self.TYPE_ENDPOINTS[data_type]}", headers=self.build_web_headers(f"{self.base_url}{MAIN_FRAME_PATH}"), data=data, timeout=self.QUERY_TIMEOUT, allow_http_error=True)

        # 解码响应文本。
        response_text = result.body.decode("utf-8", "replace")

        # 判定会话失效。
        if self.is_login_page_response(response_text):

            # 判断允许重建会话。
            if allow_relogin:

                # 打印会话失效日志。
                self.ph.warning("会话已失效，重建登录后重试当前页")

                # 重置登录态并重新登录。
                self.reset_login()

                # 执行重新登录。
                self.ensure_login()

                # 递归重试当前页且不再二次重建。
                return self.query_one_page(data_type, start_date, end_date, page_number, allow_relogin=False)

            # 抛出会话失效异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询会话失效")

        # 解析总条数。
        total_count = self.parse_total_count(response_text)

        # 解析表头与数据行。
        headers, data_rows = self.parse_table_rows(response_text)

        # 返回解析结果。
        return headers, data_rows, total_count

    # 定义多页汇聚查询方法。
    def query_pages(self, data_type, start_date, end_date):

        """
        按总账与空页终止口径汇聚指定类型的全量数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 表头与全量数据行元组。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化累计数据行。
        all_rows = []

        # 初始化表头容器。
        headers = []

        # 初始化总条数容器。
        total_count = None

        # 遍历分页页码。
        for page_number in range(1, self.MAX_PAGES + 1):

            # 查询当前页。
            page_headers, page_rows, total_count = self.query_one_page(data_type, start_date, end_date, page_number)

            # 记录首个非空表头。
            if page_headers and not headers:

                # 保存表头。
                headers = page_headers

            # 空页即终点。
            if not page_rows:

                # 结束翻页遍历。
                break

            # 累加当前页数据行。
            all_rows.extend(page_rows)

            # 打印当前页完成日志。
            self.ph.success(self.ph.join(self.ph.kv(f"{data_type} 当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总条数", total_count if total_count is not None else "-", "cyan")))

            # 判断累计行数已覆盖总条数。
            if total_count is not None and len(all_rows) >= total_count:

                # 结束翻页遍历。
                break

            # 分页请求之间保持轻量随机间隔。
            time.sleep(random.uniform(0.5, 1.5))

        # 返回表头与全量数据行。
        return headers, all_rows

    # 定义数据查询方法。
    def query_data(self, data_type, start_date=None, end_date=None):

        """
        查询华润德信行平台指定类型全量数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果与表头。
        :rtype: dict
        """

        # 校验数据类型。
        self.validate_data_type(data_type)

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 判断当前类型为流向类。
        if data_type in self.FLOW_TYPES:

            # 校验查询开始日期。
            if not start_date:

                # 抛出查询开始日期缺失异常。
                raise ValueError(f"查询{data_type}必须提供 start_date")

            # 校验查询结束日期。
            if not end_date:

                # 抛出查询结束日期缺失异常。
                raise ValueError(f"查询{data_type}必须提供 end_date")

        # 汇聚全量数据行。
        headers, all_rows = self.query_pages(data_type, start_date, end_date)

        # 打印汇聚完成日志。
        self.ph.success(self.ph.kv(f"{data_type} 查询完成", f"{len(all_rows)} 条 | {len(headers)} 列"))

        # 返回查询结果与表头。
        return {"rows": all_rows, "headers": headers}

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询华润德信行平台流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果数据行。
        :rtype: list[dict]
        """

        # 查询指定类型数据。
        query_result = self.query_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询华润德信行平台数据并生成原始字段 Excel。

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

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 查询平台数据。
        query_result = self.query_data(data_type, start_date, end_date)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 构建列映射（原始字段名同时作为标题与取值字段）。
        columns = [(field, field) for field in query_result["headers"]]

        # 写入原始字段 Excel。
        self.write_rows_to_excel(query_result["rows"], columns, output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"))

        # 返回 Excel 文件路径。
        return output_path

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出华润德信行平台数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出文件路径。
        :rtype: str
        """

        # 委托查询落地方法生成 Excel。
        return self.query_flow_to_excel(data_type, start_date, end_date, output_dir)
