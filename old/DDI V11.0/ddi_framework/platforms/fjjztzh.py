# -*- coding: utf-8 -*-
"""
福建九州通中化流向查询系统协议适配器。

本模块负责福建九州通中化流向查询系统的协议登录、登录响应解析和 Cookie 保存。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入日期时间解析对象。
from datetime import datetime

# 导入 URL 解析函数。
from urllib.parse import urlencode, urlparse

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义福建九州通中化流向查询系统协议适配器。
class FjjztzhPlatform(BasePlatform):

    """
    福建九州通中化流向查询系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 福建九州通中化平台适配器实例。
    :rtype: FjjztzhPlatform
    """

    # 定义福建九州通中化适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化福建九州通中化平台适配器。

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
        self.login_page_url = account.get("登录页", "http://112.5.108.165:8088/zh/")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", "http://112.5.108.165:8088/zh/sysuser/validate")

        # 保存采购明细查询接口地址。
        self.purchase_query_url = account.get("采购明细接口", "http://112.5.108.165:8088/zh/buybillidx/search")

        # 保存销售明细查询接口地址。
        self.sale_query_url = account.get("销售明细接口", "http://112.5.108.165:8088/zh/salebillidx/search")

        # 保存当前库存查询接口地址。
        self.stock_query_url = account.get("当前库存接口", "http://112.5.108.165:8088/zh/storehouse/search")

        # 保存平台根地址。
        self.base_url = self.build_origin(self.login_page_url)

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录响应。
        self.login_result = {}

        # 保存默认分页大小。
        self.page_size = int(account.get("分页大小", 100))

    # 定义福建九州通中化登录方法。
    def login(self):

        """
        执行福建九州通中化协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("福建九州通中化登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 访问登录页以初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 打印正式登录请求日志。
        self.ph.info(self.ph.kv("提交正式登录请求", "/zh/sysuser/validate", "cyan"))

        # 提交登录请求。
        result = self.post_login_form(payload)

        # 解析登录响应。
        login_result = self.decode_login_result(result)

        # 校验登录结果。
        if not self.is_login_success(login_result):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{self.extract_login_message(login_result)}")

        # 保存登录响应。
        self.login_result = login_result

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"))

        # 返回登录结果。
        return login_result

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建福建九州通中化登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 返回平台登录表单字段。
        return {"userName": self.clean_login_name(), "userPwd": self.clean_login_password()}

    # 定义登录表单提交方法。
    def post_login_form(self, payload):

        """
        提交福建九州通中化登录表单。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 使用通用 AJAX 表单请求提交登录。
        return self.http.post_form(self.login_api_url, payload, self.login_page_url)

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析福建九州通中化登录响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 登录响应数据。
        :rtype: dict
        """

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 处理空响应内容。
        if not response_text:

            # 返回空响应登录结果。
            return {"flag": False, "msg": "登录接口返回空响应"}

        # 尝试解析 JSON 响应。
        try:

            # 返回 JSON 响应数据。
            return json.loads(response_text)

        # 处理非 JSON 响应。
        except json.JSONDecodeError:

            # 返回原始响应文本。
            return {"flag": False, "msg": response_text}

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断福建九州通中化登录是否成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 读取响应业务状态。
        flag_value = login_result.get("flag")

        # 读取响应编码。
        code_value = str(login_result.get("code", ""))

        # 判断布尔状态或业务编码是否表示成功。
        return bool(flag_value) or code_value in ["0", "1", "200"]

    # 定义登录响应消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取福建九州通中化登录响应消息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录响应消息。
        :rtype: str
        """

        # 返回接口消息或原始响应摘要。
        return str(login_result.get("msg") or login_result.get("message") or login_result)

    # 定义登录账号清洗方法。
    def clean_login_name(self):

        """
        读取并清洗登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回去除两端空白后的登录账号。
        return str(self.account.get("账号", "")).strip()

    # 定义登录密码清洗方法。
    def clean_login_password(self):

        """
        读取并清洗登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回去除两端空白后的登录密码。
        return str(self.account.get("密码", "")).strip()

    # 定义 Cookie 保存方法。
    def save_cookie(self, cookie_dir):

        """
        保存福建九州通中化登录 Cookie。

        :param cookie_dir: Cookie 输出目录。
        :type cookie_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(cookie_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(cookie_dir, f"{self.company_name}_cookie.json")

        # 写入 Cookie 文件。
        self.http.save_cookie_file(cookie_path)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 查询指定数据类型结果。
        query_result = self.query_fjjztzh_data(data_type, start_date, end_date)

        # 返回查询结果行。
        return query_result["rows"]

    # 定义导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出指定类型流向数据。

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

        # 使用查询落地流程生成 Excel。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型流向数据并生成 Excel。

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

        # 查询指定数据类型结果。
        query_result = self.query_fjjztzh_data(data_type, start_date, end_date)

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

    # 定义福建九州通中化数据查询方法。
    def query_fjjztzh_data(self, data_type, start_date, end_date):

        """
        查询福建九州通中化指定类型数据。

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

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

        # 查询全部分页原始数据。
        raw_rows = self.query_all_pages(data_type, start_date, end_date)

        # 读取当前数据类型表头。
        headers = self.build_headers(data_type)

        # 转换为中文字段结果行。
        rows = [self.convert_row(data_type, row) for row in raw_rows]

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{len(rows)} 条", "green"), self.ph.kv("表头数", len(headers), "cyan")))

        # 返回标准查询结果。
        return {"rows": rows, "headers": headers}

    # 定义全部分页查询方法。
    def query_all_pages(self, data_type, start_date, end_date):

        """
        查询福建九州通中化全部分页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始数据行列表。
        :rtype: list[dict]
        """

        # 初始化当前页码。
        page_number = 1

        # 初始化累计数据行。
        all_rows = []

        # 初始化总记录数。
        total_count = None

        # 循环查询分页数据。
        while total_count is None or len(all_rows) < total_count:

            # 查询当前分页数据。
            page_result = self.query_one_page(data_type, start_date, end_date, page_number)

            # 读取当前页数据行。
            page_rows = page_result["rows"]

            # 读取总记录数。
            total_count = page_result["total"]

            # 累加当前页数据行。
            all_rows.extend(page_rows)

            # 打印分页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "yellow")))

            # 判断是否没有后续分页。
            if not page_rows:

                # 结束分页查询。
                break

            # 递增页码。
            page_number += 1

        # 返回累计数据行。
        return all_rows

    # 定义单页查询方法。
    def query_one_page(self, data_type, start_date, end_date, page_number):

        """
        查询福建九州通中化单页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 当前页码。
        :type page_number: int
        :return: 单页查询结果。
        :rtype: dict
        """

        # 构建查询接口地址。
        query_url = self.build_query_url(data_type, start_date, end_date, page_number)

        # 构建 AJAX 请求头。
        headers = self.build_query_headers(data_type)

        # 打印分页查询日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", self.extract_path(query_url), "cyan"), self.ph.kv("page", page_number, "yellow"), self.ph.kv("rows", self.page_size, "yellow")))

        # 发送查询请求。
        result = self.http.request("GET", query_url, headers=headers)

        # 解析查询响应。
        query_result = self.decode_query_result(result)

        # 返回分页查询结果。
        return query_result

    # 定义查询 URL 构建方法。
    def build_query_url(self, data_type, start_date, end_date, page_number):

        """
        构建福建九州通中化查询 URL。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 当前页码。
        :type page_number: int
        :return: 查询 URL。
        :rtype: str
        """

        # 读取数据类型对应的接口地址。
        query_api_url = self.build_query_api_url(data_type)

        # 构建基础查询参数。
        params = {"condition": "", "rows": self.page_size, "page": page_number, "_": int(time.time() * 1000)}

        # 判断是否为流向类查询。
        if data_type in ["配送流向", "购进流向"]:

            # 写入开始日期。
            params["sdate"] = start_date

            # 写入结束日期。
            params["edate"] = end_date

        # 返回完整查询 URL。
        return f"{query_api_url}?{urlencode(params)}"

    # 定义查询接口地址构建方法。
    def build_query_api_url(self, data_type):

        """
        构建福建九州通中化查询接口地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询接口地址。
        :rtype: str
        """

        # 配置数据类型与查询接口映射。
        mapping = {"购进流向": self.purchase_query_url, "配送流向": self.sale_query_url, "库存": self.stock_query_url}

        # 返回当前数据类型查询接口地址。
        return mapping[data_type]

    # 定义查询请求头构建方法。
    def build_query_headers(self, data_type):

        """
        构建福建九州通中化查询请求头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询请求头。
        :rtype: dict
        """

        # 读取当前数据类型页面地址。
        referer = self.build_referer_url(data_type)

        # 构建 AJAX 请求头。
        headers = self.http.ajax_form_headers(referer)

        # 设置 JSON 响应接收类型。
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"

        # 返回查询请求头。
        return headers

    # 定义来源页面地址构建方法。
    def build_referer_url(self, data_type):

        """
        构建福建九州通中化业务来源页面地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 来源页面地址。
        :rtype: str
        """

        # 配置数据类型与业务页面路径映射。
        mapping = {"购进流向": "/zh/buybillidx", "配送流向": "/zh/salebillidx", "库存": "/zh/storehouse"}

        # 返回业务页面地址。
        return f"{self.base_url}{mapping[data_type]}"

    # 定义查询响应解析方法。
    def decode_query_result(self, result):

        """
        解析福建九州通中化查询响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 查询响应数据。
        :rtype: dict
        """

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 解析 JSON 响应。
        response_data = json.loads(response_text)

        # 读取响应行列表。
        rows = response_data.get("rows") or []

        # 读取响应总数。
        total = int(response_data.get("total") or 0)

        # 返回标准分页结果。
        return {"rows": rows, "total": total}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验福建九州通中化数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in ["配送流向", "购进流向", "库存"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前福建九州通中化暂未接入: {data_type}")

    # 定义表头构建方法。
    def build_headers(self, data_type):

        """
        构建福建九州通中化输出表头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 输出表头列表。
        :rtype: list[str]
        """

        # 判断是否为库存数据。
        if data_type == "库存":

            # 返回库存输出表头。
            return ["商品编号", "商品名称", "规格", "生产厂家", "批号", "效期", "数量", "单位", "单价", "金额", "批准文号", "生产日期", "库位编号", "库位名称"]

        # 判断是否为购进流向。
        if data_type == "购进流向":

            # 返回购进输出表头。
            return ["单据日期", "类型", "供应商", "商品编号", "商品名称", "商品规格", "生产厂家", "单位", "数量", "含税单价", "含税金额", "批号", "生产日期", "有效期", "批准文号", "业务员", "单据编号"]

        # 返回配送输出表头。
        return ["单据日期", "类型", "客户名称", "商品编号", "商品名称", "商品规格", "生产厂家", "单位", "数量", "含税单价", "含税金额", "批号", "生产日期", "有效期", "批准文号", "业务员", "单据编号"]

    # 定义数据行转换方法。
    def convert_row(self, data_type, row):

        """
        转换福建九州通中化原始行到中文输出行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param row: 原始数据行。
        :type row: dict
        :return: 中文字段数据行。
        :rtype: dict
        """

        # 判断是否为库存数据。
        if data_type == "库存":

            # 返回库存中文字段行。
            return self.convert_stock_row(row)

        # 返回流向中文字段行。
        return self.convert_flow_row(data_type, row)

    # 定义流向数据行转换方法。
    def convert_flow_row(self, data_type, row):

        """
        转换福建九州通中化流向原始行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param row: 原始数据行。
        :type row: dict
        :return: 中文字段流向行。
        :rtype: dict
        """

        # 根据数据类型读取往来单位表头。
        company_header = "供应商" if data_type == "购进流向" else "客户名称"

        # 返回流向中文字段行。
        return {"单据日期": row.get("billdate", ""), "类型": row.get("billtype", ""), company_header: row.get("companyname", ""), "商品编号": row.get("productbh", ""), "商品名称": row.get("productname", ""), "商品规格": row.get("productstandard", ""), "生产厂家": row.get("makearea", ""), "单位": row.get("unitname", ""), "数量": row.get("quantity", ""), "含税单价": row.get("taxprice", ""), "含税金额": row.get("taxtotal", ""), "批号": row.get("batchno", ""), "生产日期": row.get("makedate", ""), "有效期": row.get("validdate", ""), "批准文号": row.get("permitcode", ""), "业务员": row.get("personname", ""), "单据编号": row.get("billnumber", "")}

    # 定义库存数据行转换方法。
    def convert_stock_row(self, row):

        """
        转换福建九州通中化库存原始行。

        :param row: 原始数据行。
        :type row: dict
        :return: 中文字段库存行。
        :rtype: dict
        """

        # 返回库存中文字段行。
        return {"商品编号": row.get("productbh", ""), "商品名称": row.get("productname", ""), "规格": row.get("productstandard", ""), "生产厂家": row.get("makearea", ""), "批号": row.get("batchno", ""), "效期": row.get("validdate", ""), "数量": row.get("quantity", ""), "单位": row.get("unitname", ""), "单价": row.get("costprice", ""), "金额": row.get("costtotal", ""), "批准文号": row.get("permitcode", ""), "生产日期": row.get("makedate", ""), "库位编号": row.get("storagesbh", ""), "库位名称": row.get("storagesname", "")}

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建福建九州通中化输出文件名。

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

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        写入福建九州通中化查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param headers: 表头列表。
        :type headers: list[str]
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
        worksheet.append(headers)

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按表头顺序组装一行数据。
            worksheet.append([row.get(header, "") if isinstance(row, dict) else "" for header in headers])

        # 遍历所有导出列设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

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

        # 判断目标文件是否存在。
        if not os.path.exists(output_path):

            # 无需删除不存在的文件。
            return

        # 捕获文件删除异常。
        try:

            # 删除已有目标文件。
            os.remove(output_path)

        # 处理文件被占用导致的删除异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

    # 定义请求路径提取方法。
    def extract_path(self, url):

        """
        提取 URL 的路径与查询摘要。

        :param url: 原始 URL。
        :type url: str
        :return: URL 路径。
        :rtype: str
        """

        # 解析 URL 结构。
        parsed_url = urlparse(url)

        # 返回 URL 路径。
        return parsed_url.path

    # 定义站点根地址构建方法。
    def build_origin(self, url):

        """
        构建 URL 的站点根地址。

        :param url: 原始 URL。
        :type url: str
        :return: 站点根地址。
        :rtype: str
        """

        # 解析 URL 结构。
        parsed_url = urlparse(url)

        # 返回协议与主机组合。
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
