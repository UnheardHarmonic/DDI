# -*- coding: utf-8 -*-
"""
国大药房流向数据平台协议适配器。

本模块负责国药控股国大药房体系供应商门户（国大药房流向数据平台）的协议登录、
图形验证码识别、流向与库存数据查询、分页汇聚和原始字段 Excel 落地。
当前接入商业：国药控股国大药房广西连锁有限公司。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入动态字段收集器。
from ddi_framework import DynamicFieldCollector

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义国大药房流向数据平台协议适配器。
class GuodaPlatform(BasePlatform):

    """
    国大药房流向数据平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 国大药房平台适配器实例。
    :rtype: GuodaPlatform
    """

    # 定义平台支持的接入数据类型。
    SUPPORTED_TYPES = ["配送流向", "购进流向", "库存"]

    # 定义流向类数据类型清单。
    FLOW_TYPES = ["配送流向", "购进流向"]

    # 定义数据类型到查询端点路径的映射。
    DATA_PATHS = {
        "配送流向": "/BIMData/BIMSecondDirectionNoDBList",
        "购进流向": "/BIMData/BIMPurchaseList",
        "库存": "/BIMData/BIMStockInfoList",
    }

    # 定义平台固定分页大小（服务端对超过 100 的页大小返回空集）。
    PAGE_SIZE = "100"

    # 定义分页安全上限页数。
    MAX_PAGES = 500

    # 定义登录验证码最大识别尝试次数。
    MAX_LOGIN_ATTEMPTS = 8

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化国大药房平台适配器。

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

        # 保存平台站点地址。
        self.base_url = str(account.get("站点地址", "https://gdedi.sinopharmgroup.net")).rstrip("/")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", self.base_url + "/")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", self.base_url + "/EDI/CheckLogin")

        # 保存验证码接口地址。
        self.captcha_api_url = account.get("验证码接口", self.base_url + "/EDI/CheckCode?ID=1")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化验证码识别器。
        self.captcha_solver = CaptchaSolver()

        # 初始化登录态标记。
        self.logged_in = False

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验国大药房平台数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in self.SUPPORTED_TYPES:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前国大药房平台暂未接入: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 返回流向类数据的日期区间要求。
        return data_type in self.FLOW_TYPES

    # 定义平台登录方法。
    def login(self):

        """
        执行国大药房平台协议登录。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("国大药房登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页初始化站点会话 Cookie。
        self.http.request("GET", self.login_page_url, headers=self.build_page_headers(), timeout=30)

        # 循环识别验证码并提交登录。
        for attempt_index in range(1, self.MAX_LOGIN_ATTEMPTS + 1):

            # 拉取会话绑定的图形验证码。
            captcha_result = self.http.request("GET", self.captcha_api_url, headers=self.build_image_headers(), timeout=30)

            # 识别验证码文本（优先数字字符集，失败回退通用识别）。
            captcha_code = self.captcha_solver.solve_raw_text_image_with_ranges(captcha_result.body, "0123456789") or self.captcha_solver.solve_text_image(captcha_result.body, min_length=4)

            # 判断识别结果是否为有效四位数字。
            if not captcha_code or len(captcha_code) != 4:

                # 记录识别失败并换码重试。
                self.ph.warning(self.ph.kv(f"验证码识别未通过（第 {attempt_index} 次）", f"识别值 {captcha_code!r}", "yellow"))

                # 进入下一次验证码尝试。
                continue

            # 构建登录请求体。
            payload = {"dataJson": json.dumps({"FilterModel": {"USER_CODE": self.clean_login_name(), "PASSWORD": self.clean_login_password(), "ValidateCode": captcha_code}}, ensure_ascii=False)}

            # 提交登录表单。
            result = self.http.request("POST", self.login_api_url, headers=self.build_ajax_headers(), data=urlencode(payload).encode("utf-8"), timeout=30, allow_http_error=True)

            # 解析登录响应。
            data = self.http.decode_json(result)

            # 判断登录成功（300 表示跳转登录成功）。
            if str(data.get("ResultCode")) == "300":

                # 跟随登录成功跳转完成会话升级。
                redirect_path = str(data.get("Result") or "/")

                # 补全相对跳转地址。
                if redirect_path.startswith("/"):

                    # 拼接站点根地址。
                    redirect_path = self.base_url + redirect_path

                # 访问登录成功首页。
                self.http.request("GET", redirect_path, headers=self.build_page_headers(), timeout=30)

                # 标记登录态并记录 Cookie 数量。
                self.logged_in = True

                # 打印登录成功日志。
                self.ph.success(self.ph.join(self.ph.kv("登录成功", f"第 {attempt_index} 次验证码通过", "green"), self.ph.kv("Cookie 数", len(list(self.http.cookie_jar)), "cyan")))

                # 返回登录结果摘要。
                return {"message": "登录成功", "attempts": attempt_index}

            # 记录未通过原因并换码重试。
            self.ph.warning(self.ph.kv(f"登录未通过（第 {attempt_index} 次）", str(data.get("Message") or f"ResultCode={data.get('ResultCode')}"), "yellow"))

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 国大药房平台登录失败：验证码识别或凭据连续 {self.MAX_LOGIN_ATTEMPTS} 次未通过")

    # 定义查询过滤器构建方法。
    def build_data_filter(self, data_type, start_date, end_date):

        """
        构建数据查询的过滤模型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 过滤模型字典。
        :rtype: dict
        """

        # 判断当前类型是否为流向类。
        if self.requires_date_range(data_type):

            # 返回带日期区间的过滤模型。
            return {"BEGINDATE": start_date, "ENDDATE": end_date}

        # 返回库存类的空过滤模型。
        return {}

    # 定义单页查询方法。
    def query_one_page(self, data_type, filter_model, page_number):

        """
        查询国大药房平台单页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param filter_model: 过滤模型字典。
        :type filter_model: dict
        :param page_number: 页码。
        :type page_number: int
        :return: 平台原始分页响应。
        :rtype: dict
        """

        # 构建分页请求体。
        payload = {"dataJson": json.dumps({"FilterModel": filter_model}, ensure_ascii=False), "page": str(page_number), "rows": self.PAGE_SIZE}

        # 打印分页请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", self.DATA_PATHS[data_type], "cyan"), self.ph.kv("page", page_number, "yellow"), self.ph.kv("rows", self.PAGE_SIZE, "cyan")))

        # 提交分页查询请求（宽区间大结果集服务端响应较慢，超时放宽至 300 秒）。
        result = self.http.request("POST", self.base_url + self.DATA_PATHS[data_type], headers=self.build_ajax_headers(), data=urlencode(payload).encode("utf-8"), timeout=300)

        # 返回解析后的分页响应。
        return self.http.decode_json(result)

    # 定义数据查询方法。
    def query_data(self, data_type, start_date=None, end_date=None):

        """
        查询国大药房平台全量数据并汇聚原始字段。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果与表头（表头为 (展示标题, 字段名) 元组列表）。
        :rtype: dict
        """

        # 校验数据类型。
        self.validate_data_type(data_type)

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 构建过滤模型。
        filter_model = self.build_data_filter(data_type, start_date, end_date)

        # 查询第一页数据。
        first_page = self.query_one_page(data_type, filter_model, 1)

        # 初始化页面响应集合。
        page_responses = [{"page": 1, "rows": first_page.get("rows") or []}]

        # 读取平台返回的记录总数。
        total_count = int(first_page.get("total") or 0)

        # 初始化累计数据行。
        all_rows = list(page_responses[0]["rows"])

        # 遍历剩余页码直到取满总数。
        for page_number in range(2, self.MAX_PAGES + 1):

            # 判断累计行数是否已满足总数。
            if total_count and len(all_rows) >= total_count:

                # 结束分页遍历。
                break

            # 查询当前页数据。
            page_response = self.query_one_page(data_type, filter_model, page_number)

            # 读取当前页数据行。
            current_rows = page_response.get("rows") or []

            # 判断当前页是否已无数据。
            if not current_rows:

                # 结束分页遍历。
                break

            # 累加当前页数据行。
            all_rows.extend(current_rows)

            # 记录页面响应用于字段汇聚。
            page_responses.append({"page": page_number, "rows": current_rows})

            # 打印当前页完成日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(current_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "cyan")))

        # 按首次出现顺序汇聚跨页字段并集并对齐全量数据行。
        field_table = DynamicFieldCollector().collect(page_responses)

        # 输出跨页新增字段提示。
        for change in field_table.changes:

            # 打印动态字段变化日志。
            self.ph.warning(self.ph.kv(f"第 {change['page']} 页出现新增字段", "、".join(change["added"]), "yellow"))

        # 打印汇聚完成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} 查询完成", f"{len(field_table.rows)} 条", "green"), self.ph.kv("字段数", len(field_table.columns), "cyan")))

        # 返回查询结果与表头（元组为基类写表契约：展示标题 + 字段名）。
        return {"rows": field_table.rows, "headers": [(column["title"], column["key"]) for column in field_table.columns]}

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询国大药房平台流向数据。

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
        查询国大药房平台数据并生成原始字段 Excel。

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

        # 写入原始字段 Excel。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"))

        # 返回 Excel 文件路径。
        return output_path

    # 定义页面请求头构建方法。
    def build_page_headers(self):

        """
        构建页面访问请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回浏览器页面请求头。
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "User-Agent": self.http.user_agent(),
        }

    # 定义验证码请求头构建方法。
    def build_image_headers(self):

        """
        构建验证码图片请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回验证码图片请求头。
        return {
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
        }

    # 定义异步请求头构建方法。
    def build_ajax_headers(self):

        """
        构建异步表单请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回异步表单请求头。
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": self.base_url,
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
            "X-Requested-With": "XMLHttpRequest",
        }
