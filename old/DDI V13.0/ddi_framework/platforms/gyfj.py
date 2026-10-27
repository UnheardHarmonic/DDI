# -*- coding: utf-8 -*-
"""
国药控股福建流向平台协议适配器。

本模块负责国药控股福建流向平台的协议登录、Cookie 保存和后续查询接口扩展。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期解析模块。
from datetime import datetime

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入通用逆向摘要函数。
from ddi_framework import md5_hex


# 定义国药控股福建流向平台协议适配器。
class GyfjPlatform(BasePlatform):

    """
    国药控股福建流向平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 国药控股福建平台适配器实例。
    :rtype: GyfjPlatform
    """

    # 定义国药控股福建适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化国药控股福建平台适配器。

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

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", "http://spfj.sinopharm-fj.com:8001/api/login")

        # 保存平台根地址。
        self.base_url = self.login_api_url.split("/api/", 1)[0]

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", self.base_url)

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 保存查询接口地址。
        self.query_api_url = account.get("查询接口", urljoin(self.base_url, "/api/query"))

    # 定义国药控股福建登录方法。
    def login(self):

        """
        执行国药控股福建协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("国药福建登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 访问登录页以初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 打印正式登录请求日志。
        self.ph.info(self.ph.join(self.ph.kv("提交正式登录请求", "/api/login", "cyan"), self.ph.kv("货主", self.account.get("货主名称"), "yellow")))

        # 发送登录表单请求。
        result = self.http.post_form(self.login_api_url, payload, self.login_page_url)

        # 解析登录接口响应。
        login_result = self.decode_login_result(result)

        # 校验登录结果。
        if not self.is_login_success(login_result):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{self.extract_login_message(login_result)}")

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"))

        # 返回登录结果。
        return login_result

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建国药控股福建登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 读取清洗后的登录账号。
        login_name = self.clean_login_name()

        # 读取清洗后的登录密码。
        login_password = self.clean_login_password()

        # 读取货主编码。
        owner_code = self.clean_owner_code()

        # 返回登录表单字段。
        return {
            "user": login_name,
            "pwd": md5_hex(login_password),
            "own": owner_code,
        }

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析国药控股福建登录响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 登录响应数据。
        :rtype: dict
        """

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 尝试解析 JSON 响应。
        try:

            # 返回 JSON 响应数据。
            return json.loads(response_text)

        # 处理非 JSON 响应。
        except json.JSONDecodeError:

            # 返回原始响应文本。
            return {"type": "", "msg": response_text}

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断登录响应是否表示成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 读取响应类型。
        result_type = str(login_result.get("type", ""))

        # 判断响应类型是否为成功编码。
        return result_type == "1"

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
        return str(login_result.get("msg") or login_result.get("message") or login_result)

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

    # 定义货主编码清洗方法。
    def clean_owner_code(self):

        """
        读取清洗后的货主编码。

        :return: 货主编码。
        :rtype: str
        """

        # 返回去除两端空白后的货主编码。
        return str(self.account.get("货主编码", "")).strip()

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录 Cookie。

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
        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询国药控股福建流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 查询指定类型数据。
        query_result = self.query_gyfj_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["data"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出国药控股福建流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出结果。
        :rtype: dict
        """

        # 执行查询并生成 Excel 文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询国药控股福建流向数据并生成 Excel。

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

        # 查询指定类型完整响应。
        query_result = self.query_gyfj_data(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["data"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{query_result['count']} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义国药控股福建数据查询方法。
    def query_gyfj_data(self, data_type, start_date, end_date):

        """
        查询国药控股福建指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 查询结果、表头和总数。
        :rtype: dict
        """

        # 校验查询开始日期。
        if not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验查询结束日期。
        if not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 构建查询请求体。
        payload = self.build_query_payload(data_type, start_date, end_date)

        # 打印查询请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}", "/api/query", "cyan"), self.ph.kv("ptype", payload["ptype"], "yellow")))

        # 发送查询表单请求。
        result = self.http.post_form(self.query_api_url, payload, self.login_page_url)

        # 解析查询响应。
        response_data = self.decode_query_result(result)

        # 提取标准查询结果。
        query_result = self.normalize_query_result(data_type, response_data)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{query_result['count']} 条", "green"), self.ph.kv("表头数", len(query_result["headers"]), "cyan")))

        # 返回标准查询结果。
        return query_result

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, start_date, end_date):

        """
        构建国药控股福建查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 查询请求体。
        :rtype: dict
        """

        # 返回查询表单字段。
        return {
            "pstartdate": start_date,
            "penddate": end_date,
            "ptype": self.build_query_ptype(data_type),
            "pgoodsname": "",
        }

    # 定义查询类型编码构建方法。
    def build_query_ptype(self, data_type):

        """
        构建国药控股福建查询类型编码。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询类型编码。
        :rtype: str
        """

        # 定义内部数据类型与网页查询类型编码映射。
        ptype_map = {
            "购进流向": "Purchase",
            "配送流向": "Sales",
            "库存": "Stocks",
            "报损流向": "Others",
        }

        # 返回数据类型对应的查询类型编码。
        return ptype_map[data_type]

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验国药控股福建数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 校验数据类型是否存在。
        if data_type not in ["购进流向", "配送流向", "库存", "报损流向"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前国药控股福建暂未接入: {data_type}")

    # 定义查询响应解析方法。
    def decode_query_result(self, result):

        """
        解析国药控股福建查询响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 查询响应数据。
        :rtype: dict
        """

        # 解码查询响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 返回 JSON 响应数据。
        return json.loads(response_text)

    # 定义查询响应标准化方法。
    def normalize_query_result(self, data_type, response_data):

        """
        标准化国药控股福建查询响应。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param response_data: 查询响应数据。
        :type response_data: dict
        :return: 标准查询结果。
        :rtype: dict
        """

        # 读取顶层数据字段。
        top_data = response_data.get("data")

        # 判断响应是否为顶层列表结构。
        if isinstance(top_data, list):

            # 读取顶层数据行。
            rows = top_data

            # 读取顶层表头。
            headers = response_data.get("headers") or self.infer_headers(rows)

            # 读取顶层总数。
            count_value = response_data.get("count", len(rows))

        # 判断响应是否为嵌套字典结构。
        elif isinstance(top_data, dict):

            # 读取嵌套数据行。
            rows = top_data.get("data") or []

            # 读取嵌套表头。
            headers = top_data.get("headers") or response_data.get("headers") or self.infer_headers(rows)

            # 读取嵌套总数。
            count_value = top_data.get("count", response_data.get("count", len(rows)))

        # 处理无 data 字段的响应结构。
        else:

            # 读取响应数据行。
            rows = response_data.get("rows") or []

            # 读取响应表头。
            headers = response_data.get("headers") or self.infer_headers(rows)

            # 读取响应总数。
            count_value = response_data.get("count", len(rows))

        # 校验查询数据结构。
        if not isinstance(rows, list):

            # 抛出查询结构异常。
            raise RuntimeError(f"{data_type}查询失败：响应 data 字段不是列表")

        # 按真实数据字段修正导出表头。
        headers = self.normalize_export_headers(rows, headers)

        # 返回标准查询结果。
        return {
            "data": rows,
            "headers": headers,
            "count": int(count_value or len(rows)),
        }

    # 定义导出表头标准化方法。
    def normalize_export_headers(self, rows, headers):

        """
        根据真实数据行修正国药控股福建导出表头。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param headers: 接口返回表头列表。
        :type headers: list[str]
        :return: 修正后的导出表头列表。
        :rtype: list[str]
        """

        # 判断查询结果是否为空。
        if not rows:

            # 返回接口表头列表。
            return headers

        # 判断查询结果首行是否为字典。
        if not isinstance(rows[0], dict):

            # 返回接口表头列表。
            return headers

        # 根据真实数据行推断字段列表。
        inferred_headers = self.infer_headers(rows)

        # 判断真实数据字段列表是否为空。
        if not inferred_headers:

            # 返回接口表头列表。
            return headers

        # 返回真实数据字段列表。
        return inferred_headers

    # 定义表头推断方法。
    def infer_headers(self, rows):

        """
        根据数据行推断 Excel 表头。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :return: 表头列表。
        :rtype: list[str]
        """

        # 空数据返回空表头。
        if not rows:

            # 返回空列表。
            return []

        # 初始化表头结果列表。
        headers = []

        # 遍历查询结果数据行。
        for row in rows:

            # 跳过非字典数据行。
            if not isinstance(row, dict):

                # 继续处理下一行。
                continue

            # 遍历当前数据行字段名称。
            for header_name in row.keys():

                # 判断字段名称是否已经记录。
                if header_name in headers:

                    # 继续处理下一字段。
                    continue

                # 追加当前字段名称。
                headers.append(header_name)

        # 返回完整字段顺序。
        return headers

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建国药控股福建输出文件名。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
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
        :type end_date: str
        :return: 库存日期标签。
        :rtype: str
        """

        # 读取导出当天日期。
        date_value = datetime.now()

        # 返回 yy.m.d 标签。
        return f"{date_value.year % 100}.{date_value.month}.{date_value.day}"

    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        写入国药控股福建查询结果到 Excel。

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

            # 按接口表头顺序组装一行数据。
            worksheet.append([row.get(header, "") for header in headers])

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

        # 关闭导出工作簿。
        workbook.close()

        # 应用统一 Excel 输出样式。
        apply_standard_excel_style(output_path)

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
