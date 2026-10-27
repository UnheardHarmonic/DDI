# -*- coding: utf-8 -*-
"""
国药控股吉林流向平台协议适配器。

本模块负责国药控股吉林流向平台的协议登录、Cookie 保存和后续查询接口扩展。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期解析模块。
from datetime import datetime

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入通用逆向摘要函数。
from ddi_framework import md5_hex


# 定义国药控股吉林流向平台协议适配器。
class GyjlPlatform(BasePlatform):

    """
    国药控股吉林流向平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 国药控股吉林平台适配器实例。
    :rtype: GyjlPlatform
    """

    # 定义国药控股吉林适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化国药控股吉林平台适配器。

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
        self.login_page_url = account.get("登录页", "https://www.sinopharm-jilin.com/lxlogin.php")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", "https://www.sinopharm-jilin.com/lxlogin_action.php")

        # 保存查询接口地址。
        self.query_api_url = account.get("查询接口", "https://www.sinopharm-jilin.com/lxinfo_action.php")

        # 保存平台根地址。
        self.base_url = self.login_page_url.rsplit("/", 1)[0]

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 保存查询页面地址。
        self.query_page_url = account.get("查询页", f"{self.base_url}/lxinfo.php?code={self.clean_login_name()}&data=1")

    # 定义国药控股吉林登录方法。
    def login(self):

        """
        执行国药控股吉林协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("国药吉林登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 访问登录页以初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 打印正式登录请求日志。
        self.ph.info(self.ph.kv("提交正式登录请求", "/lxlogin_action.php", "cyan"))

        # 发送登录表单请求。
        result = self.post_login_form(payload)

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
        构建国药控股吉林登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 读取清洗后的登录账号。
        login_name = self.clean_login_name()

        # 读取清洗后的登录密码。
        login_password = self.clean_login_password()

        # 计算登录密码的大写 MD5 摘要。
        encrypted_password = md5_hex(login_password).upper()

        # 返回登录表单字段。
        return {"username": login_name, "password": encrypted_password}

    # 定义登录表单提交方法。
    def post_login_form(self, payload):

        """
        提交国药控股吉林登录表单。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建 AJAX 表单请求头。
        headers = self.build_login_headers()

        # 编码表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送登录请求。
        return self.http.request("POST", self.login_api_url, headers=headers, data=data)

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建国药控股吉林登录请求头。

        :return: 登录请求头。
        :rtype: dict
        """

        # 返回与网页登录一致的 AJAX 表单请求头。
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": self.base_url,
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
            "X-Requested-With": "XMLHttpRequest",
        }

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析国药控股吉林登录响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 登录响应数据。
        :rtype: dict
        """

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 处理错误账号密码返回的空响应。
        if not response_text:

            # 返回空响应登录结果。
            return {"success": False, "message": "用户名或密码错误"}

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
        判断国药控股吉林登录是否成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 读取响应业务标识。
        flag_value = str(login_result.get("FLAG3", ""))

        # 判断登录响应是否进入平台业务分支。
        return flag_value in ["0", "1"]

    # 定义登录响应消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取国药控股吉林登录响应消息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录响应消息。
        :rtype: str
        """

        # 返回显式响应消息。
        if login_result.get("message"):

            # 返回响应消息。
            return str(login_result.get("message"))

        # 返回平台业务状态。
        if login_result.get("FLAG3") is not None:

            # 返回登录业务标识。
            return f"FLAG3={login_result.get('FLAG3')}"

        # 返回原始响应摘要。
        return str(login_result)

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
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询国药控股吉林流向数据。

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
        query_result = self.query_gyjl_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出国药控股吉林流向数据。

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

        # 抛出导出接口未接入异常。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询国药控股吉林流向数据并生成 Excel。

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

        # 抛出查询落地接口未接入异常。
        query_result = self.query_gyjl_data(data_type, start_date, end_date)

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

    # 定义国药控股吉林数据查询方法。
    def query_gyjl_data(self, data_type, start_date, end_date):

        """
        查询国药控股吉林指定类型数据。

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

        # 构建查询请求体。
        payload = self.build_query_payload(data_type, start_date, end_date)

        # 打印查询请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}", "/lxinfo_action.php", "cyan"), self.ph.kv("opttype", payload["opttype"], "yellow"), self.ph.kv("owner", payload["owner"], "yellow")))

        # 发送查询表单请求。
        result = self.post_query_form(payload)

        # 解析查询响应。
        rows = self.decode_query_rows(result)

        # 推断 Excel 表头。
        headers = self.infer_headers(rows)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{len(rows)} 条", "green"), self.ph.kv("表头数", len(headers), "cyan")))

        # 返回标准查询结果。
        return {"rows": rows, "headers": headers}

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, start_date, end_date):

        """
        构建国药控股吉林查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询请求体。
        :rtype: dict
        """

        # 读取业务类型编码。
        option_type = self.build_query_option_type(data_type)

        # 构建基础查询表单字段。
        payload = {
            "usercode": self.clean_login_name(),
            "owner": self.clean_owner_code(),
            "opttype": option_type,
            "goodsid": "",
            "goodsname": "",
            "qBeginTime": "",
            "qEndTime": "",
            "datarange": "1",
        }

        # 写入流向类业务日期范围。
        if data_type in ["配送流向", "购进流向"]:

            # 设置查询开始日期。
            payload["qBeginTime"] = start_date

            # 设置查询结束日期。
            payload["qEndTime"] = end_date

        # 返回查询表单字段。
        return payload

    # 定义查询类型编码构建方法。
    def build_query_option_type(self, data_type):

        """
        构建国药控股吉林查询类型编码。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询类型编码。
        :rtype: str
        """

        # 定义内部数据类型与网页业务分类编码映射。
        option_type_map = {"配送流向": "1", "购进流向": "2", "库存": "3"}

        # 返回当前数据类型对应的业务分类编码。
        return option_type_map[data_type]

    # 定义查询表单提交方法。
    def post_query_form(self, payload):

        """
        提交国药控股吉林查询表单。

        :param payload: 查询请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建查询请求头。
        headers = self.build_query_headers()

        # 编码查询表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送查询请求。
        return self.http.request("POST", self.query_api_url, headers=headers, data=data, timeout=120)

    # 定义查询请求头构建方法。
    def build_query_headers(self):

        """
        构建国药控股吉林查询请求头。

        :return: 查询请求头。
        :rtype: dict
        """

        # 返回与网页查询一致的 AJAX 表单请求头。
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": self.base_url,
            "Referer": self.query_page_url,
            "User-Agent": self.http.user_agent(),
            "X-Requested-With": "XMLHttpRequest",
        }

    # 定义查询响应解析方法。
    def decode_query_rows(self, result):

        """
        解析国药控股吉林查询响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 查询结果数据行。
        :rtype: list[dict]
        """

        # 解码查询响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 处理空响应数据。
        if not response_text:

            # 返回空数据列表。
            return []

        # 解析 JSON 响应。
        response_data = json.loads(response_text)

        # 返回列表型响应数据。
        if isinstance(response_data, list):

            # 返回响应数据列表。
            return response_data

        # 返回字典中的数据列表。
        if isinstance(response_data, dict):

            # 读取常见数据字段。
            rows = response_data.get("data") or response_data.get("rows") or response_data.get("list") or []

            # 返回数据列表。
            return rows if isinstance(rows, list) else []

        # 返回空数据列表。
        return []

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验国药控股吉林数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 校验数据类型是否存在。
        if data_type not in ["配送流向", "购进流向", "库存"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前国药控股吉林暂未接入: {data_type}")

    # 定义货主编码清洗方法。
    def clean_owner_code(self):

        """
        读取清洗后的货主编码。

        :return: 货主编码。
        :rtype: str
        """

        # 返回去除两端空白后的货主编码。
        return str(self.account.get("货主编码", "2")).strip()

    # 定义表头推断方法。
    def infer_headers(self, rows):

        """
        根据查询结果推断 Excel 表头。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :return: Excel 表头列表。
        :rtype: list[str]
        """

        # 空数据返回空表头。
        if not rows:

            # 返回空列表。
            return []

        # 初始化表头列表。
        headers = []

        # 遍历全部数据行。
        for row in rows:

            # 跳过非字典数据行。
            if not isinstance(row, dict):

                # 继续处理下一行数据。
                continue

            # 遍历当前数据行字段。
            for key in row.keys():

                # 追加尚未出现的字段。
                if key not in headers:

                    # 保存字段名称。
                    headers.append(key)

        # 返回表头列表。
        return headers

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建国药控股吉林输出文件名。

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
        写入国药控股吉林查询结果到 Excel。

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
