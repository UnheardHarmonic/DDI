# -*- coding: utf-8 -*-
"""
凉山佳能达医药贸易有限责任公司流向卡管理系统协议适配器。

本模块通过 ASP.NET 表单会话、图片验证码和 LXK HTML 分页页面读取购进流向、配送流向及库存明细，并将标准字段和全部页面原始字段写入 Excel。

:return: 流向卡管理系统协议适配器。
:rtype: None
"""

# 导入 HTML 解析基类。
from html.parser import HTMLParser

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入日期时间类。
from datetime import datetime

# 导入 URL 参数编码函数。
from urllib.parse import urlencode

# 导入 Excel 工作簿类。
from openpyxl import Workbook

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入 Excel 标准样式函数。
from ddi_framework import apply_standard_excel_style

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient


# 定义用户映射的数据类型与页面类别。
DATA_TYPE_CONFIG = {
    "购进流向": "入库",
    "配送流向": "出库",
    "库存": "库存",
}

# 定义页面原始字段到标准字段的映射。
STANDARD_FIELD_MAP = {
    "购进流向": [("入库日期", "日期"), ("往来单位", "往来单位"), ("商品编号", "商品编号"), ("商品名称", "商品名称"), ("商品规格", "商品规格"), ("单位", "单位"), ("数量", "数量"), ("含税价", "含税价"), ("含税金额", "含税金额"), ("批号", "批号"), ("生产厂家", "生产厂家")],
    "配送流向": [("出库日期", "日期"), ("往来单位", "往来单位"), ("商品编号", "商品编号"), ("商品名称", "商品名称"), ("商品规格", "商品规格"), ("单位", "单位"), ("数量", "数量"), ("含税价", "含税价"), ("含税金额", "含税金额"), ("批号", "批号"), ("生产厂家", "生产厂家")],
    "库存": [("库存日期", "日期"), ("往来单位", "往来单位"), ("商品编号", "商品编号"), ("商品名称", "商品名称"), ("商品规格", "商品规格"), ("单位", "单位"), ("库存数量", "数量"), ("含税价", "含税价"), ("含税金额", "含税金额"), ("批号", "批号"), ("生产厂家", "生产厂家")],
}


# 定义流向卡 HTML 表格解析器。
class LxkHtmlTableParser(HTMLParser):

    """
    提取页面内全部普通 HTML 表格。

    :return: HTML 表格解析器实例。
    :rtype: LxkHtmlTableParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化表格、行和单元格状态。

        :return: None。
        :rtype: None
        """

        # 调用 HTML 解析器初始化逻辑。
        super().__init__()

        # 初始化全部已完成表格。
        self.tables = []

        # 初始化当前表格。
        self.current_table = None

        # 初始化当前行。
        self.current_row = None

        # 初始化当前单元格文字片段。
        self.current_cell = None

    # 定义开始标签处理方法。
    def handle_starttag(self, tag, attrs):

        """
        记录表格、行和单元格开始位置。

        :param tag: 当前 HTML 标签名称。
        :type tag: str
        :param attrs: 当前 HTML 标签属性。
        :type attrs: list[tuple[str, str | None]]
        :return: None。
        :rtype: None
        """

        # 判断当前标签是否为表格。
        if tag.lower() == "table":

            # 初始化当前表格记录集合。
            self.current_table = []

        # 判断当前标签是否为表格行。
        if tag.lower() == "tr" and self.current_table is not None:

            # 初始化当前表格行。
            self.current_row = []

        # 判断当前标签是否为表头或单元格。
        if tag.lower() in {"th", "td"} and self.current_row is not None:

            # 初始化当前单元格文字集合。
            self.current_cell = []

    # 定义文本处理方法。
    def handle_data(self, data):

        """
        收集当前单元格的文本片段。

        :param data: 当前 HTML 文本。
        :type data: str
        :return: None。
        :rtype: None
        """

        # 判断当前正在读取单元格。
        if self.current_cell is not None:

            # 追加当前文本片段。
            self.current_cell.append(data)

    # 定义结束标签处理方法。
    def handle_endtag(self, tag):

        """
        完成单元格、行和表格的数据归集。

        :param tag: 当前 HTML 标签名称。
        :type tag: str
        :return: None。
        :rtype: None
        """

        # 判断当前标签是否结束单元格。
        if tag.lower() in {"th", "td"} and self.current_cell is not None and self.current_row is not None:

            # 合并并写入当前单元格文本。
            self.current_row.append("".join(self.current_cell).strip())

            # 清空当前单元格状态。
            self.current_cell = None

        # 判断当前标签是否结束表格行。
        if tag.lower() == "tr" and self.current_row is not None and self.current_table is not None:

            # 保存含有单元格的当前行。
            if self.current_row:

                # 追加当前行到表格记录集合。
                self.current_table.append(self.current_row)

            # 清空当前行状态。
            self.current_row = None

        # 判断当前标签是否结束表格。
        if tag.lower() == "table" and self.current_table is not None:

            # 保存当前表格。
            self.tables.append(self.current_table)

            # 清空当前表格状态。
            self.current_table = None


# 定义凉山佳能达流向卡管理系统适配器。
class LsjndPlatform(BasePlatform):

    """
    凉山佳能达流向卡管理系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 流向卡管理系统协议适配器实例。
    :rtype: LsjndPlatform
    """

    # 定义平台初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化 ASP.NET 会话、验证码和查询配置。

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

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 读取流向卡管理系统根地址。
        self.base_url = str(account.get("接口根地址", "http://www.lsjnd.com.cn:6501")).rstrip("/")

        # 读取登录页地址。
        self.login_page_url = f"{self.base_url}/Account/Login"

        # 读取验证码接口地址。
        self.captcha_url = f"{self.base_url}/Common/GetVerfyCode"

        # 读取登录接口地址。
        self.login_api_url = f"{self.base_url}/Account/UserLogin"

        # 读取流向卡页面接口地址。
        self.query_url = f"{self.base_url}/LXK/Index"

        # 读取当前商业的流向卡名称。
        self.lxk_name = str(account.get("流向卡名称", "")).strip()

        # 读取稳定的分页大小。
        self.page_size = int(account.get("分页大小", 100))

        # 读取验证码固定长度。
        self.captcha_length = int(account.get("验证码长度", 5))

        # 读取验证码最大重试次数。
        self.captcha_max_retries = int(account.get("验证码重试次数", 6))

        # 读取查询限流重试次数。
        self.rate_limit_retries = int(account.get("限流重试次数", 3))

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化图片验证码识别器。
        self.captcha_solver = CaptchaSolver()

        # 初始化登录状态标识。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        执行图片验证码和防伪令牌登录。

        :return: 脱敏登录结果。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("流向卡管理系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 校验流向卡名称已配置。
        if not self.lxk_name:

            # 抛出流向卡名称缺失异常。
            raise RuntimeError(f"{self.company_name} 未配置流向卡名称")

        # 初始化最后一次登录失败原因。
        last_error = ""

        # 按配置次数执行验证码登录。
        for retry_index in range(self.captcha_max_retries):

            # 捕获单次验证码请求、识别和提交异常。
            try:

                # 读取当前会话的登录页和防伪令牌。
                csrf_token = self.fetch_login_page_token()

                # 获取当前会话的验证码图片。
                image_bytes = self.fetch_captcha_image()

                # 识别当前验证码文本。
                captcha_code = self.solve_captcha_code(image_bytes)

                # 提交登录表单并解析响应。
                login_data = self.submit_login(csrf_token, captcha_code)

            # 保存单次验证码处理异常并进入下一次尝试。
            except Exception as error:

                # 保存异常文本。
                last_error = str(error)

                # 打印当前验证码处理异常。
                self.ph.warning(self.ph.kv("验证码处理异常", f"第 {retry_index + 1}/{self.captcha_max_retries} 次：{last_error}", "yellow"))

                # 等待验证码刷新间隔。
                if retry_index < self.captcha_max_retries - 1:

                    # 等待服务器验证码刷新。
                    time.sleep(1.2)

                # 进入下一次验证码尝试。
                continue

            # 判断当前登录是否成功。
            if str(login_data.get("code", "")) == "200":

                # 标记当前会话已登录。
                self.logged_in = True

                # 打印登录成功摘要。
                self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("Cookie", "已建立", "cyan")))

                # 返回脱敏登录结果。
                return {"登录状态": "成功", "会话状态": "已建立"}

            # 保存当前登录失败说明。
            last_error = str(login_data.get("message", "平台未返回登录成功"))

            # 打印当前验证码重试摘要。
            self.ph.warning(self.ph.kv("验证码登录未通过", f"第 {retry_index + 1}/{self.captcha_max_retries} 次：{last_error}", "yellow"))

            # 等待验证码刷新间隔。
            if retry_index < self.captcha_max_retries - 1:

                # 等待服务器验证码刷新。
                time.sleep(1.2)

        # 抛出最终登录失败异常。
        raise RuntimeError(f"{self.company_name} 登录失败：{last_error}")

    # 定义登录页防伪令牌读取方法。
    def fetch_login_page_token(self):

        """
        读取登录页内的 ASP.NET 防伪令牌。

        :return: 防伪令牌文本。
        :rtype: str
        """

        # 请求登录页面以建立 Cookie 会话。
        result = self.request_with_rate_limit("GET", self.login_page_url, self.http.browser_headers(self.base_url))

        # 解码登录页面 HTML。
        html_text = result.body.decode("utf-8", errors="replace")

        # 提取页面隐藏防伪字段。
        token_match = re.search(r'name="Page_XSRF_TOKEN"\s+type="hidden"\s+value="([^"]+)"', html_text)

        # 校验页面已返回防伪字段。
        if token_match is None:

            # 抛出防伪令牌缺失异常。
            raise RuntimeError(f"{self.company_name} 登录页未返回 Page_XSRF_TOKEN")

        # 返回当前页面防伪令牌。
        return token_match.group(1)

    # 定义验证码图片读取方法。
    def fetch_captcha_image(self):

        """
        获取当前会话的图片验证码。

        :return: 验证码图片字节。
        :rtype: bytes
        """

        # 构建带防缓存参数的验证码地址。
        request_url = f"{self.captcha_url}?r={time.time()}"

        # 构建验证码图片请求头。
        headers = {"Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Referer": self.login_page_url, "User-Agent": self.http.user_agent()}

        # 请求验证码图片。
        result = self.request_with_rate_limit("GET", request_url, headers)

        # 校验验证码图片不为空。
        if not result.body:

            # 抛出验证码图片为空异常。
            raise RuntimeError(f"{self.company_name} 验证码图片为空")

        # 返回验证码图片字节。
        return result.body

    # 定义验证码识别方法。
    def solve_captcha_code(self, image_bytes):

        """
        识别并校验当前图片验证码。

        :param image_bytes: 验证码图片字节。
        :type image_bytes: bytes
        :return: 验证码文本。
        :rtype: str
        """

        # 调用公共 OCR 识别普通验证码。
        captcha_code = self.captcha_solver.solve_text_image(image_bytes, min_length=self.captcha_length)

        # 清理非字母数字字符。
        captcha_code = "".join(character for character in str(captcha_code) if character.isalnum())

        # 校验验证码文本长度。
        if len(captcha_code) != self.captcha_length:

            # 抛出验证码长度不符异常。
            raise RuntimeError(f"验证码识别长度异常：{len(captcha_code)}")

        # 返回识别后的验证码文本。
        return captcha_code

    # 定义登录表单提交方法。
    def submit_login(self, csrf_token, captcha_code):

        """
        按页面 AJAX 协议提交登录表单。

        :param csrf_token: 页面防伪令牌。
        :type csrf_token: str
        :param captcha_code: 图片验证码答案。
        :type captcha_code: str
        :return: 登录响应对象。
        :rtype: dict
        """

        # 构建登录表单请求头。
        headers = self.http.ajax_form_headers(self.login_page_url)

        # 写入页面要求的防伪请求头。
        headers["Header_XSRF_TOKEN"] = csrf_token

        # 构建登录表单字段。
        payload = {"Name": str(self.account.get("账号", "")), "Pwd": str(self.account.get("密码", "")), "VerfyCode": captcha_code}

        # 编码表单请求体。
        request_data = urlencode(payload).encode("utf-8")

        # 提交登录表单。
        result = self.request_with_rate_limit("POST", self.login_api_url, headers, data=request_data)

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 尝试解析登录 JSON 响应。
        try:

            # 返回登录 JSON 响应对象。
            return json.loads(response_text)

        # 处理非 JSON 登录响应。
        except json.JSONDecodeError as error:

            # 抛出登录协议异常。
            raise RuntimeError(f"{self.company_name} 登录响应不是 JSON：{response_text[:200]}") from error

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的全部页面原始记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 查询并返回完整数据结果。
        result = self.query_lxk_data(data_type, start_date, end_date)

        # 返回页面原始记录。
        return result["rows"]

    # 定义登录 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前协议会话 Cookie。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存当前 Cookie 会话。
        self.http.save_cookie_file(cookie_path)

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询页面 HTML 明细并生成标准 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 查询当前数据类型完整数据。
        result = self.query_lxk_data(data_type, start_date, end_date)

        # 解析 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建项目统一命名的 Excel 文件名。
        file_name = self.build_output_file_name(data_type, result["start_date"], result["end_date"])

        # 拼接 Excel 输出文件路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入标准字段和完整原始字段。
        self.write_excel(result["rows"], result["headers"], data_type, output_path)

        # 打印 Excel 落地摘要。
        self.ph.success(self.ph.join(self.ph.kv("Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义统一导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        使用 HTML 查询结果生成本地 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 调用统一查询并落地流程。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义完整 HTML 分页查询方法。
    def query_lxk_data(self, data_type, start_date, end_date):

        """
        分页读取 LXK 页面并保留全部表头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 表头、记录和真实查询日期范围。
        :rtype: dict
        """

        # 校验数据类型已配置。
        if data_type not in DATA_TYPE_CONFIG:

            # 抛出不支持数据类型异常。
            raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

        # 确保当前会话已经登录。
        if not self.logged_in:

            # 执行登录流程。
            self.login()

        # 解析真实请求日期范围。
        resolved_start_date, resolved_end_date = self.resolve_dates(start_date, end_date)

        # 打印数据类型查询分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", resolved_start_date, "cyan"), self.ph.kv("结束日期", resolved_end_date, "cyan")))

        # 初始化原始字段列表。
        headers = []

        # 初始化所有页面原始记录。
        rows = []

        # 初始化当前页码。
        page_index = 1

        # 初始化服务端总记录数。
        expected_count = None

        # 逐页读取页面明细。
        while True:

            # 请求当前 HTML 分页页面。
            page_headers, page_rows, page_total = self.fetch_query_page(data_type, resolved_start_date, resolved_end_date, page_index)

            # 合并当前页面原始字段顺序。
            headers = self.merge_headers(headers, page_headers, page_rows)

            # 合并当前页原始记录。
            rows.extend(page_rows)

            # 更新服务端总记录数。
            expected_count = page_total if page_total is not None else expected_count

            # 打印当前分页查询进度。
            self.ph.info(self.ph.join(self.ph.kv("分页", page_index, "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan"), self.ph.kv("累计", len(rows), "cyan")))

            # 判断当前分页已经结束。
            if not page_rows or (expected_count is not None and len(rows) >= expected_count) or len(page_rows) < self.page_size:

                # 结束分页读取。
                break

            # 递增当前页码。
            page_index += 1

            # 等待下一页避免触发站点访问频率限制。
            time.sleep(1.2)

        # 校验业务日期落在真实请求范围内。
        self.validate_date_range(data_type, rows, resolved_start_date, resolved_end_date)

        # 返回完整查询结果。
        return {"headers": headers, "rows": rows, "start_date": resolved_start_date, "end_date": resolved_end_date}

    # 定义单页 HTML 查询方法。
    def fetch_query_page(self, data_type, start_date, end_date, page_index):

        """
        请求并解析指定页码的 LXK HTML 表格。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_index: 当前页码。
        :type page_index: int
        :return: 页面表头、页面记录和服务端总记录数。
        :rtype: tuple[list[str], list[dict], int | None]
        """

        # 构建当前页查询参数。
        query_params = {"lxkName": self.lxk_name, "dtFrom": start_date, "dtTo": end_date, "leibie": DATA_TYPE_CONFIG[data_type], "key": "", "CurrentPage": int(page_index), "PageSize": self.page_size}

        # 编码当前页完整查询地址。
        request_url = f"{self.query_url}?{urlencode(query_params)}"

        # 请求当前页 HTML 响应。
        result = self.request_with_rate_limit("GET", request_url, self.http.browser_headers(self.login_page_url))

        # 解码当前页 HTML 文本。
        html_text = result.body.decode("utf-8", errors="replace")

        # 校验当前会话未跳回登录页。
        if 'id="txtName"' in html_text:

            # 清空失效登录状态。
            self.logged_in = False

            # 抛出会话失效异常。
            raise RuntimeError(f"{self.company_name} 查询会话已失效")

        # 解析当前页表头和记录。
        headers, rows = self.parse_detail_table(html_text)

        # 解析页面展示的总记录数。
        total_count = self.parse_total_count(html_text)

        # 返回当前页解析结果。
        return headers, rows, total_count

    # 定义页面明细表解析方法。
    def parse_detail_table(self, html_text):

        """
        从页面表格中定位含日期和商品名称的业务明细表。

        :param html_text: 页面 HTML 文本。
        :type html_text: str
        :return: 页面原始表头和记录。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化 HTML 表格解析器。
        parser = LxkHtmlTableParser()

        # 执行 HTML 表格解析。
        parser.feed(html_text)

        # 遍历页面全部表格定位业务明细表。
        for table in parser.tables:

            # 跳过没有表头的空表格。
            if not table:

                # 继续读取下一个表格。
                continue

            # 读取当前表格首行。
            candidate_headers = table[0]

            # 判断当前表格是否为业务明细表。
            if "日期" not in candidate_headers or "商品名称" not in candidate_headers:

                # 继续读取下一个表格。
                continue

            # 初始化当前表格原始记录。
            rows = []

            # 遍历当前表格数据行。
            for values in table[1:]:

                # 补齐当前行缺少的表头位置。
                padded_values = values + [""] * max(0, len(candidate_headers) - len(values))

                # 按表头顺序构建当前原始记录。
                row = {header: padded_values[index] for index, header in enumerate(candidate_headers)}

                # 追加当前原始记录。
                rows.append(row)

            # 返回业务明细表头和记录。
            return candidate_headers, rows

        # 返回页面无数据时的空表头和空记录。
        return [], []

    # 定义总记录数解析方法。
    def parse_total_count(self, html_text):

        """
        解析页面分页提示中的总记录数。

        :param html_text: 页面 HTML 文本。
        :type html_text: str
        :return: 服务端总记录数。
        :rtype: int | None
        """

        # 匹配分页提示中的总记录数。
        total_match = re.search(r"共\s*(\d+)\s*条记录", html_text)

        # 判断页面未展示总记录数。
        if total_match is None:

            # 返回未知总记录数。
            return None

        # 返回页面展示的总记录数。
        return int(total_match.group(1))

    # 定义原始字段合并方法。
    def merge_headers(self, headers, page_headers, page_rows):

        """
        按页面列顺序合并后续页新增原始字段。

        :param headers: 已收集原始字段。
        :type headers: list[str]
        :param page_headers: 当前页原始字段。
        :type page_headers: list[str]
        :param page_rows: 当前页原始记录。
        :type page_rows: list[dict]
        :return: 合并后的原始字段。
        :rtype: list[str]
        """

        # 复制已收集的原始字段。
        merged_headers = list(headers)

        # 遍历页面表头字段。
        for header in page_headers:

            # 判断当前字段尚未出现。
            if header not in merged_headers:

                # 追加当前页面字段。
                merged_headers.append(header)

        # 遍历当前页记录。
        for row in page_rows:

            # 遍历当前记录字段。
            for header in row:

                # 判断当前字段尚未出现。
                if header not in merged_headers:

                    # 追加当前记录字段。
                    merged_headers.append(header)

        # 返回合并后的字段列表。
        return merged_headers

    # 定义日期范围解析方法。
    def resolve_dates(self, start_date, end_date):

        """
        解析并校验页面实际使用的日期参数。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 生成默认当天日期。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 解析实际开始日期。
        resolved_start_date = str(start_date or today_text)

        # 解析实际结束日期。
        resolved_end_date = str(end_date or resolved_start_date)

        # 解析开始日期对象。
        start_value = datetime.strptime(resolved_start_date, "%Y-%m-%d")

        # 解析结束日期对象。
        end_value = datetime.strptime(resolved_end_date, "%Y-%m-%d")

        # 校验开始日期不晚于结束日期。
        if start_value > end_value:

            # 抛出无效日期范围异常。
            raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{resolved_start_date} > {resolved_end_date}")

        # 返回已验证日期范围。
        return resolved_start_date, resolved_end_date

    # 定义业务日期范围校验方法。
    def validate_date_range(self, data_type, rows, start_date, end_date):

        """
        校验页面日期列未超出请求范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 提取可解析的页面业务日期。
        business_dates = [str(row.get("日期", ""))[:10] for row in rows if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("日期", ""))[:10])]

        # 判断页面不含可解析业务日期。
        if not business_dates:

            # 结束空结果或无日期字段校验。
            return

        # 判断页面最早日期超出范围。
        if min(business_dates) < start_date:

            # 抛出业务日期过早异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期早于请求开始日期：{min(business_dates)} < {start_date}")

        # 判断页面最晚日期超出范围。
        if max(business_dates) > end_date:

            # 抛出业务日期过晚异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期晚于请求结束日期：{max(business_dates)} > {end_date}")

    # 定义库存输出日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        保证库存文件名使用导出当天日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 输出命名使用的日期。
        :rtype: str | None
        """

        # 判断当前数据类型为库存。
        if data_type == "库存":

            # 返回导出当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向查询开始日期。
        return start_date or end_date

    # 定义 Excel 写入方法。
    def write_excel(self, rows, headers, data_type, output_path):

        """
        写入标准字段前置且完整保留页面原始字段的 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 页面原始字段列表。
        :type headers: list[str]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param output_path: Excel 输出路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 获取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type

        # 读取当前类型标准字段定义。
        standard_fields = STANDARD_FIELD_MAP[data_type]

        # 构建标准字段标题列表。
        standard_titles = [title for title, _ in standard_fields]

        # 写入标准字段及完整页面原始字段表头。
        worksheet.append(standard_titles + headers)

        # 遍历全部页面原始记录。
        for row in rows:

            # 构建标准字段数据。
            standard_values = [row.get(source_name, "") for _, source_name in standard_fields]

            # 构建完整页面原始字段数据。
            raw_values = [row.get(header, "") for header in headers]

            # 写入当前数据行。
            worksheet.append(standard_values + raw_values)

        # 保存 Excel 工作簿。
        workbook.save(output_path)

        # 关闭 Excel 工作簿。
        workbook.close()

        # 应用项目统一 Excel 样式。
        apply_standard_excel_style(output_path)

    # 定义限流重试请求方法。
    def request_with_rate_limit(self, method, url, headers, data=None):

        """
        请求平台接口并在 429 响应时受控重试。

        :param method: HTTP 请求方法。
        :type method: str
        :param url: 请求地址。
        :type url: str
        :param headers: 请求头。
        :type headers: dict
        :param data: 请求体字节。
        :type data: bytes | None
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 初始化最后一次请求异常。
        last_error = None

        # 按配置次数执行限流重试。
        for retry_index in range(self.rate_limit_retries):

            # 尝试执行当前 HTTP 请求。
            try:

                # 返回当前请求响应。
                return self.http.request(method, url, headers=headers, data=data, timeout=60)

            # 处理协议请求异常。
            except RuntimeError as error:

                # 保存当前请求异常。
                last_error = error

                # 判断当前异常不是访问频率限制。
                if "HTTP 429" not in str(error) or retry_index >= self.rate_limit_retries - 1:

                    # 重新抛出当前请求异常。
                    raise

                # 打印访问频率限制重试摘要。
                self.ph.warning(self.ph.kv("访问频率限制", f"等待后重试第 {retry_index + 1} 次", "yellow"))

                # 等待限流窗口恢复。
                time.sleep(3.0)

        # 抛出理论上不可到达的最后异常。
        raise RuntimeError(str(last_error))
