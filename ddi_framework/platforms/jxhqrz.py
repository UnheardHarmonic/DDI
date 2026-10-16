# -*- coding: utf-8 -*-
"""
江西黄庆仁栈医药物流有限公司流向查询系统协议适配器。

本模块负责江西黄庆仁栈医药物流平台的登录、分页查询和本地 Excel 文件生成。
"""

# 导入哈希摘要模块。

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间戳模块。
import time

# 导入日期时间对象。
from datetime import datetime

# 导入 HTML 解析基类。
from html.parser import HTMLParser

# 导入 URL 编码函数。
from urllib.parse import urlencode

# 导入 URL 解析函数。
from urllib.parse import urlparse

# 导入协议请求客户端。
# 导入通用摘要函数。
from ddi_framework.reverse_utils import md5_hex

from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义登录页防伪令牌解析器。
class VerificationTokenParser(HTMLParser):

    """
    解析登录页中的 ASP.NET 防伪令牌。

    :return: 防伪令牌解析器实例。
    :rtype: VerificationTokenParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化防伪令牌解析器。

        :return: None。
        :rtype: None
        """

        # 调用父类 HTML 解析器初始化逻辑。
        super().__init__()

        # 初始化防伪令牌文本。
        self.token = ""

    # 定义开始标签处理方法。
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

        # 转换属性列表为字典。
        attr_map = dict(attrs)

        # 判断当前标签是否为防伪令牌输入框。
        if tag.lower() == "input" and attr_map.get("name") == "__RequestVerificationToken":

            # 保存防伪令牌值。
            self.token = attr_map.get("value", "") or ""


# 定义江西黄庆仁栈平台适配器。
class JxhqrzPlatform(BasePlatform):

    """
    江西黄庆仁栈医药物流平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 江西黄庆仁栈平台适配器实例。
    :rtype: JxhqrzPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化江西黄庆仁栈平台适配器。

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
        self.login_page_url = account.get("登录页", "http://m.jxncyy.com/HHWLSaleFlowWeb/Login/Index")

        # 保存站点根地址。
        self.base_url = self.build_origin(self.login_page_url)

        # 保存应用根地址。
        self.app_base_url = account.get("应用根地址", "http://m.jxncyy.com/HHWLSaleFlowWeb").rstrip("/")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", f"{self.app_base_url}/Login/CheckLogin")

        # 保存登录后首页地址。
        self.home_page_url = account.get("首页", f"{self.app_base_url}/Home/Index")

        # 保存分页大小。
        self.page_size = int(account.get("分页大小", 100))

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态。
        self.logged_in = False

        # 初始化登录响应。
        self.login_result = {}

    # 定义平台登录方法。
    def login(self):

        """
        执行江西黄庆仁栈平台登录。

        :return: 登录响应数据。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("江西黄庆仁栈登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 请求登录页以初始化 Cookie。
        login_page_result = self.http.get(self.login_page_url)

        # 打印登录页访问结果。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 解析登录页防伪令牌。
        verification_token = self.extract_verification_token(login_page_result)

        # 构建登录请求体。
        payload = self.build_login_payload(verification_token)

        # 打印登录账号日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("密码加密", "MD5", "yellow")))

        # 打印正式登录请求日志。
        self.ph.info("提交正式登录请求: /Login/CheckLogin")

        # 提交登录表单。
        login_result = self.post_login_form(payload)

        # 解析登录响应。
        login_data = self.decode_json_response(login_result)

        # 校验登录响应状态。
        if not self.is_login_success(login_data):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{login_data.get('info') or login_data}")

        # 保存登录响应。
        self.login_result = login_data

        # 标记当前会话已登录。
        self.logged_in = True

        # 加载登录后首页。
        self.load_home_page()

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("正式登录成功", "登录成功", "green"))

        # 返回登录响应数据。
        return login_data

    # 定义登录页防伪令牌解析方法。
    def extract_verification_token(self, login_page_result):

        """
        提取登录页中的防伪令牌。

        :param login_page_result: 登录页响应。
        :type login_page_result: HttpResult
        :return: 防伪令牌文本。
        :rtype: str
        """

        # 解码登录页 HTML。
        html_text = self.decode_response_text(login_page_result)

        # 初始化 HTML 令牌解析器。
        parser = VerificationTokenParser()

        # 解析登录页 HTML。
        parser.feed(html_text)

        # 返回解析到的令牌文本。
        return parser.token

    # 定义登录请求体构建方法。
    def build_login_payload(self, verification_token):

        """
        构建登录表单请求体。

        :param verification_token: 防伪令牌文本。
        :type verification_token: str
        :return: 登录表单字段。
        :rtype: dict
        """

        # 初始化登录表单字段。
        payload = {"username": self.clean_login_name(), "password": self.build_password_hash(), "verifycode": ""}

        # 判断登录页是否提供防伪令牌。
        if verification_token:

            # 写入防伪令牌字段。
            payload["__RequestVerificationToken"] = verification_token

        # 返回登录表单字段。
        return payload

    # 定义登录密码摘要构建方法。
    def build_password_hash(self):

        """
        构建前端一致的登录密码 MD5 摘要。

        :return: 登录密码 MD5 十六进制摘要。
        :rtype: str
        """

        # 读取清洗后的登录密码。
        password_text = self.clean_login_password()

        # 返回密码 MD5 摘要。
        return md5_hex(password_text)



    # 定义登录后首页加载方法。
    def load_home_page(self):

        """
        加载登录成功后的系统首页。

        :return: 首页响应。
        :rtype: HttpResult
        """

        # 请求首页以初始化菜单会话。
        return self.http.get(self.home_page_url, referer=self.login_page_url)


    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询江西黄庆仁栈业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果数据行。
        :rtype: list[dict]
        """

        # 查询指定业务数据。
        query_result = self.query_jxhqrz_data(data_type, start_date, end_date)

        # 返回查询结果行。
        return query_result["rows"]


    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询江西黄庆仁栈业务数据并生成 Excel。

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
        query_result = self.query_jxhqrz_data(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建输出文件路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan")))

        # 返回输出文件路径。
        return output_path

    # 定义业务数据查询方法。
    def query_jxhqrz_data(self, data_type, start_date, end_date):

        """
        查询江西黄庆仁栈指定类型业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果与表头。
        :rtype: dict
        """

        # 校验数据类型是否已经接入。
        self.validate_data_type(data_type)

        # 校验流向类查询开始日期。
        if data_type in ["购进流向", "配送流向"] and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验流向类查询结束日期。
        if data_type in ["购进流向", "配送流向"] and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 查询全部分页数据。
        rows = self.query_all_pages(data_type, start_date, end_date)

        # 构建输出表头。
        headers = self.build_headers(data_type, rows)

        # 打印查询解析日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{len(rows)} 条", "green"), self.ph.kv("表头数", len(headers), "cyan")))

        # 返回查询数据与表头。
        return {"rows": rows, "headers": headers}

    # 定义全部分页查询方法。
    def query_all_pages(self, data_type, start_date, end_date):

        """
        查询指定数据类型的全部分页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 全部分页数据行。
        :rtype: list[dict]
        """

        # 初始化分页页码。
        page_number = 1

        # 初始化累计数据行。
        all_rows = []

        # 初始化总页数。
        total_pages = 1

        # 循环读取全部分页。
        while page_number <= total_pages:

            # 查询当前页数据。
            page_data = self.query_page(data_type, start_date, end_date, page_number)

            # 读取当前页数据行。
            current_rows = page_data["rows"]

            # 累加当前页数据行。
            all_rows.extend(current_rows)

            # 更新总页数。
            total_pages = max(1, int(page_data.get("total_pages") or 1))

            # 打印分页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(current_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总页数", total_pages, "yellow")))

            # 判断当前页是否已经没有数据。
            if not current_rows:

                # 结束分页查询。
                break

            # 递增分页页码。
            page_number += 1

        # 返回累计数据行。
        return all_rows

    # 定义单页查询方法。
    def query_page(self, data_type, start_date, end_date, page_number):

        """
        查询指定数据类型的单页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 分页页码。
        :type page_number: int
        :return: 单页响应摘要。
        :rtype: dict
        """

        # 构建分页请求地址。
        request_url = self.build_page_request_url(data_type, start_date, end_date, page_number)

        # 构建分页请求头。
        headers = self.build_ajax_get_headers()

        # 打印分页请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", self.build_query_path(data_type), "cyan"), self.ph.kv("page", page_number, "yellow"), self.ph.kv("rows", self.page_size, "yellow")))

        # 发送分页查询请求。
        result = self.http.request("GET", request_url, headers=headers, timeout=90)

        # 解析分页响应。
        response_data = self.decode_json_response(result)

        # 校验分页响应状态。
        if int(response_data.get("code", 0)) != 200:

            # 抛出分页查询失败异常。
            raise RuntimeError(f"{self.company_name} {data_type}分页查询失败：{response_data.get('info') or response_data}")

        # 读取分页数据对象。
        data_block = response_data.get("data") or {}

        # 读取分页数据行。
        rows = data_block.get("rows") or []

        # 返回单页响应摘要。
        return {"rows": rows, "records": data_block.get("records", len(rows)), "total_pages": data_block.get("total", 1)}

    # 定义分页请求地址构建方法。
    def build_page_request_url(self, data_type, start_date, end_date, page_number):

        """
        构建分页查询请求地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 分页页码。
        :type page_number: int
        :return: 分页查询请求地址。
        :rtype: str
        """

        # 构建业务查询条件。
        query_json = self.build_query_json(data_type, start_date, end_date)

        # 构建分页参数。
        pagination = {"rows": self.page_size, "page": page_number, "sidx": "Id", "sort": "ASC", "records": 0, "total": 0}

        # 构建 URL 查询参数。
        query_params = {"queryJson": json.dumps(query_json, ensure_ascii=False, separators=(",", ":")), "pagination": json.dumps(pagination, ensure_ascii=False, separators=(",", ":")), "_": str(int(time.time() * 1000))}

        # 返回完整分页查询地址。
        return f"{self.build_query_api_url(data_type)}?{urlencode(query_params)}"

    # 定义业务查询条件构建方法。
    def build_query_json(self, data_type, start_date, end_date):

        """
        构建业务查询条件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 业务查询条件。
        :rtype: dict
        """

        # 判断当前查询是否为库存。
        if data_type == "库存":

            # 返回库存空查询条件。
            return {}

        # 返回流向类查询条件。
        return {"Kind": "", "SupplierName": "", "Name": "", "AgentName": "", "BatchCode": "", "StartTime": f"{start_date} 00:00:00", "EndTime": f"{end_date} 23:59:59"}

    # 定义表单请求方法。
    def post_form(self, url, payload, referer):

        """
        提交 AJAX 表单请求。

        :param url: 请求地址。
        :type url: str
        :param payload: 表单字段。
        :type payload: dict
        :param referer: 来源页面地址。
        :type referer: str
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建表单请求体。
        body = urlencode(payload).encode("utf-8")

        # 构建表单请求头。
        headers = self.build_form_headers(referer)

        # 发送表单请求。
        return self.http.request("POST", url, headers=headers, data=body, timeout=120)

    # 定义登录表单提交方法。
    def post_login_form(self, payload):

        """
        提交登录表单并对慢响应进行重试。

        :param payload: 登录表单字段。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 初始化最后一次异常。
        last_error = None

        # 遍历登录提交尝试次数。
        for attempt_index in range(2):

            # 捕获登录提交异常。
            try:

                # 提交登录表单。
                return self.post_form(self.login_api_url, payload, self.login_page_url)

            # 处理登录提交异常。
            except RuntimeError as error:

                # 保存最后一次异常。
                last_error = error

                # 判断是否仍可重试。
                if attempt_index == 0:

                    # 打印登录重试日志。
                    self.ph.warning(f"登录接口响应异常，重新访问登录页后重试: {error}")

                    # 重新访问登录页刷新会话。
                    login_page_result = self.http.get(self.login_page_url)

                    # 重新提取防伪令牌。
                    verification_token = self.extract_verification_token(login_page_result)

                    # 更新登录表单字段。
                    payload = self.build_login_payload(verification_token)

                    # 进入下一次登录提交。
                    continue

                # 继续抛出最后一次异常。
                raise

        # 抛出登录提交失败异常。
        raise RuntimeError(f"{self.company_name} 登录请求失败：{last_error}")

    # 定义表单请求头构建方法。
    def build_form_headers(self, referer):

        """
        构建登录表单请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 登录表单请求头。
        :rtype: dict
        """

        # 返回登录表单请求头。
        return {"Accept": "application/json, text/javascript, */*; q=0.01", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": self.base_url, "Referer": referer, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    # 定义 AJAX GET 请求头构建方法。
    def build_ajax_get_headers(self):

        """
        构建分页查询请求头。

        :return: 分页查询请求头。
        :rtype: dict
        """

        # 返回分页查询请求头。
        return {"Accept": "application/json, text/javascript, */*; q=0.01", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Account": self.clean_login_name(), "Connection": "keep-alive", "Referer": self.home_page_url, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    # 定义 JSON 响应解析方法。
    def decode_json_response(self, result):

        """
        解析 JSON 响应体。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 解码响应体文本。
        response_text = self.decode_response_text(result).strip()

        # 判断响应体是否为空。
        if not response_text:

            # 返回空响应对象。
            return {}

        # 返回 JSON 解析结果。
        return json.loads(response_text)

    # 定义响应文本解码方法。
    def decode_response_text(self, result):

        """
        解码 HTTP 响应体文本。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 响应体文本。
        :rtype: str
        """

        # 读取响应头字符集声明。
        content_type = result.headers.get("Content-Type", "")

        # 判断响应头是否声明 GBK 字符集。
        if "gb" in content_type.lower():

            # 按 GB18030 解码响应体。
            return result.body.decode("gb18030", errors="replace")

        # 按 UTF-8 解码响应体。
        return result.body.decode("utf-8", errors="replace")

    # 定义登录成功判断方法。
    def is_login_success(self, login_data):

        """
        判断登录响应是否成功。

        :param login_data: 登录响应数据。
        :type login_data: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 返回登录响应状态判断结果。
        return int(login_data.get("code", 0)) == 200


    # 定义查询阶段标题打印方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印查询阶段标题。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 判断当前查询是否为库存。
        if data_type == "库存":

            # 打印库存查询标题。
            self.ph.section(f"{data_type}查询", "库存接口不传递起止日期")

            # 结束标题打印。
            return

        # 打印流向查询标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

    # 定义查询接口路径构建方法。
    def build_query_path(self, data_type):

        """
        构建查询接口路径。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询接口路径。
        :rtype: str
        """

        # 定义数据类型与接口路径映射。
        mapping = {"购进流向": "/TH_FlowDirection/PurchaseDetail/GetPageList", "配送流向": "/TH_FlowDirection/SalesDetail1/GetPageList", "库存": "/TH_FlowDirection/StockDetail/GetPageList"}

        # 返回当前数据类型接口路径。
        return mapping[data_type]

    # 定义查询接口地址构建方法。
    def build_query_api_url(self, data_type):

        """
        构建查询接口地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询接口地址。
        :rtype: str
        """

        # 定义配置键与默认接口映射。
        mapping = {"购进流向": self.account.get("购进流向接口", f"{self.app_base_url}/TH_FlowDirection/PurchaseDetail/GetPageList"), "配送流向": self.account.get("配送流向接口", f"{self.app_base_url}/TH_FlowDirection/SalesDetail1/GetPageList"), "库存": self.account.get("库存接口", f"{self.app_base_url}/TH_FlowDirection/StockDetail/GetPageList")}

        # 返回当前数据类型接口地址。
        return mapping[data_type]

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已经接入。
        if data_type not in ["购进流向", "配送流向", "库存"]:

            # 抛出数据类型未接入异常。
            raise ValueError(f"江西黄庆仁栈暂未接入数据类型：{data_type}")

    # 定义输出表头构建方法。
    def build_headers(self, data_type, rows):

        """
        构建输出表头配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :return: 表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 读取基础表头配置。
        headers = list(self.build_base_headers(data_type))

        # 读取已配置字段集合。
        configured_fields = {field_name for _, field_name in headers}

        # 遍历数据行补齐动态字段。
        for row in rows:

            # 遍历当前行字段。
            for field_name in row.keys():

                # 判断当前字段是否已经配置。
                if field_name in configured_fields:

                    # 进入下一个字段。
                    continue

                # 追加动态字段表头。
                headers.append((field_name, field_name))

                # 记录动态字段已经配置。
                configured_fields.add(field_name)

        # 返回完整表头配置。
        return headers

    # 定义基础表头构建方法。
    def build_base_headers(self, data_type):

        """
        构建基础输出表头配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 基础表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 定义购进流向表头。
        purchase_headers = [("采购主单ID", "BillId"), ("采购明细ID", "BillDetailId"), ("采购类型ID", "KindId"), ("采购类型", "Kind"), ("业务日期", "BusinessDate"), ("入库日期", "StockInDate"), ("供应商ID", "SuppierId"), ("供应商名称", "SuppierName"), ("采购员ID", "PurchaserId"), ("采购员名称", "PurchaserName"), ("商品编码", "Code"), ("商品名称", "Name"), ("通用名", "CommName"), ("规格", "Spec"), ("单位", "Unit"), ("包装规格", "PackageSpec"), ("厂家ID", "ManufacturerId"), ("生产厂家", "Manufacturer"), ("批号", "BatchNo"), ("批次", "BatchCode"), ("生产日期", "MakeDate"), ("有效期", "ExpiredDate"), ("保管账ID", "KeepAccountId"), ("保管账", "KeepAccountName"), ("单价", "Price"), ("数量", "Amount"), ("金额", "Money"), ("代理商ID", "AgentId"), ("代理商名称", "AgentName"), ("更新时间", "UpdateTime"), ("上传时间", "UploadTime")]

        # 定义配送流向表头。
        sales_headers = [("业务日期", "BusinessDate"), ("出库日期", "StockOutDate"), ("客户ID", "CustomerId"), ("客户名称", "CustomerName"), ("客户类型ID", "CustomerKindId"), ("客户类型", "CustomerKind"), ("销售员ID", "SalesId"), ("销售员名称", "SalesName"), ("销售部门ID", "SalesDeptId"), ("销售部门", "SalesDept"), ("采购员ID", "PurchaserId"), ("采购员名称", "PurchaserName"), ("商品编码", "Code"), ("商品名称", "Name"), ("通用名", "CommName"), ("规格", "Spec"), ("单位", "Unit"), ("厂家ID", "ManufacturerId"), ("生产厂家", "Manufacturer"), ("批号", "BatchNo"), ("批次", "BatchCode"), ("生产日期", "MakeDate"), ("有效期", "ExpiredDate"), ("保管账ID", "KeepAccountId"), ("保管账", "KeepAccountName"), ("单价", "Price"), ("退货数量", "ReturnAmount"), ("库存数量", "StockAmount"), ("数量", "Amount"), ("金额", "Money"), ("城市ID", "CityId"), ("城市", "CityName"), ("区县ID", "DistrictId"), ("区县", "DistrictName"), ("客户地址", "CustomerAddress"), ("代理商ID", "AgentId"), ("代理商名称", "AgentName"), ("发票代码", "InvoiceCode"), ("发票号码", "InvoiceNo"), ("发票日期", "InvoiceDate"), ("差异数量", "DiffAmount"), ("差异金额", "DiffMoney"), ("批准文号", "approvedocno"), ("更新时间", "UpdateTime"), ("上传时间", "UploadTime")]

        # 定义库存表头。
        stock_headers = [("商品ID", "Code"), ("商品名称", "Name"), ("通用名", "CommName"), ("规格", "Spec"), ("单位", "Unit"), ("生产厂家", "Manufacturer"), ("采购员ID", "PurchaserId"), ("采购员名称", "PurchaserName"), ("批号", "BatchNo"), ("批次", "BatchCode"), ("批次日期", "BatchNoDate"), ("生产日期", "MakeDate"), ("有效期", "ExpiredDate"), ("数量", "Amount"), ("可用数量", "AmountUsable"), ("不可用数量", "AmountUnusable"), ("单价", "Price"), ("金额", "Money"), ("采购部门ID", "PurchaseDeptId"), ("采购部门", "PurchaserDeptName"), ("代理商ID", "AgentId"), ("代理商名称", "AgentName"), ("库存天数", "StockDays"), ("更新时间", "UpdateTime"), ("上传时间", "UploadTime")]

        # 定义数据类型与表头映射。
        mapping = {"购进流向": purchase_headers, "配送流向": sales_headers, "库存": stock_headers}

        # 返回当前数据类型表头。
        return mapping[data_type]






