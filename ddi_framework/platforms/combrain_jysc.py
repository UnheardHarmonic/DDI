# -*- coding: utf-8 -*-
"""
康博士 ABrain 流向查询系统协议适配器。

本模块负责康博士后台管理系统的 AES-CBC 请求封装、账号登录、分页查询、
原始字段保留、标准字段前置和 Excel 文件生成。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统接口模块。
import os

# 导入日期时间模块。
from datetime import datetime


# 导入 URL 表单编码工具。
from urllib.parse import urlencode

from urllib.request import Request

# 导入工作簿创建对象。
from openpyxl import Workbook

# 导入统一 Excel 样式函数。
from ddi_framework import apply_standard_excel_style
# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入 AES-CBC-PKCS7-Base64 加密函数。
from ddi_framework import aes_cbc_pkcs7_base64

# 导入 MD5 摘要函数。
from ddi_framework import md5_hex


# 定义康博士平台支持的数据类型。
COMBRAIN_JYSC_SUPPORTED_DATA_TYPES = {"配送流向", "购进流向", "库存"}


# 定义康博士平台固定 AES 密钥。
COMBRAIN_JYSC_AES_KEY = "64498178c5490c7c"


# 定义康博士平台查询配置。
COMBRAIN_JYSC_QUERY_DEFINITIONS = {
    "配送流向": {
        "window_id": "lx_salelogxd",
        "sql_id": "lx_salelog",
        "grid_name": "grid_client",
        "date_start_key": "CT1",
        "date_end_key": "CT2",
        "fields": [
            ("销售单号", "SALELOG_NO"),
            ("销售时间", "CT"),
            ("客户编号", "CVID"),
            ("客户名称", "CVNAME"),
            ("商品编号", "IT_ID"),
            ("商品名称", "ITNAME"),
            ("规格", "SPEC"),
            ("生产厂商", "MADEIN"),
            ("单位", "UNIT"),
            ("批号", "BATCH_NO"),
            ("销售数量", "SALE_AMT"),
            ("含税单价", "SALE_PRICE"),
            ("销售金额", "SALE_MNY"),
            ("供应商名称", "UPCVNAME"),
            ("批准文号", "PASS_NO"),
            ("生产日期", "MADE_TIME"),
            ("有效期至", "AVAIL_TIME"),
            ("开票员", "CREAT_USER"),
        ],
    },
    "购进流向": {
        "window_id": "lx_pulog_n",
        "sql_id": "lx_pulog",
        "grid_name": "grid_client",
        "date_start_key": "CT1",
        "date_end_key": "CT2",
        "fields": [
            ("采购单号", "PURECORD_NO"),
            ("采购时间", "CT"),
            ("供应商编号", "CVID"),
            ("供应商名称", "CVNAME"),
            ("商品编号", "IT_ID"),
            ("商品名称", "ITNAME"),
            ("规格", "SPEC"),
            ("生产厂商", "MADEIN"),
            ("单位", "UNIT"),
            ("批号", "BATCH_NO"),
            ("采购数量", "PUR_AMT"),
            ("含税单价", "ITAX_PRICE"),
            ("采购金额", "ITAX_MNY"),
            ("批准文号", "PASS_NO"),
            ("生产日期", "MADE_TIME"),
            ("有效期至", "AVAIL_TIME"),
        ],
    },
    "库存": {
        "window_id": "lx_stock_n",
        "sql_id": "lx_stock",
        "grid_name": "grid_stock",
        "fields": [
            ("入库时间", "CT"),
            ("商品编号", "IT_ID"),
            ("商品名称", "ITNAME"),
            ("规格", "SPEC"),
            ("生产厂商", "MADEIN"),
            ("单位", "UNIT"),
            ("库存数量", "ALL_AMT"),
            ("批号", "BATCH_NO"),
            ("生产日期", "MADE_TIME"),
            ("有效期至", "AVAIL_TIME"),
            ("供应商编号", "供应商编号"),
            ("批准文号", "PASS_NO"),
        ],
    },
}


class CombrainJyscPlatform(BasePlatform):

    """
    康博士 ABrain 流向查询系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台适配器实例。
    :rtype: CombrainJyscPlatform
    """

    def __init__(self, company_name, account, printer=None):

        """
        初始化康博士 ABrain 协议适配器。

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

        # 初始化日志打印器。
        self.ph = printer or PrintHandler()

        # 保存站点根地址。
        self.site_root_url = account.get("站点根地址", "http://47.99.244.155:8189/intelsys_service_abrain").rstrip("/")

        # 保存登录账号。
        self.username = account.get("账号", "")

        # 保存登录密码。
        self.password = account.get("密码", "")

        # 保存登录数据源编码。
        self.group_id = account.get("数据源编码", "user")

        # 保存登录数据源显示名称。
        self.group_name = account.get("数据源", "YYB")

        # 保存分页大小。
        self.page_size = int(account.get("分页大小", 500))

        # 初始化协议请求客户端并托管平台会话。
        self.http = ProtocolHttpClient(self.site_root_url)

        # 引用协议客户端管理的 Cookie 容器。
        self.cookie_jar = self.http.cookie_jar

        # 引用协议客户端管理的请求打开器。
        self.opener = self.http.opener

        # 初始化登录用户信息。
        self.user_data = {}

        # 初始化登录状态。
        self.logged_in = False

    def login(self):

        """
        登录康博士 ABrain 流向查询系统。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("康博士 ABrain 登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 构建首次登录请求体。
        payload = {
            "user_id": self.username,
            "passWord": self.password,
            "group_id": self.group_id,
            "checkFlag": "",
            "terminall": "A",
        }

        # 发送首次登录请求。
        response_data = self.post_api("/login", payload, user_data=None, referer="home")

        # 判断账号是否处于在线状态。
        if response_data.get("code") == "001":

            # 构建强制登录请求体。
            payload["checkFlag"] = "confirm"

            # 发送强制登录请求。
            response_data = self.post_api("/login", payload, user_data=None, referer="home")

        # 校验登录是否成功。
        if response_data.get("code") != "00":

            # 抛出登录失败异常。
            raise RuntimeError(f"康博士 ABrain 登录失败：{response_data.get('msg') or response_data}")

        # 保存登录用户信息。
        self.user_data = response_data.get("data") if isinstance(response_data.get("data"), dict) else {}

        # 标记当前会话已登录。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("康博士 ABrain 登录成功", self.user_data.get("COMPANY_NAME", self.company_name), "green"), self.ph.kv("账号", self.username, "cyan"), self.ph.kv("数据源", self.group_name, "cyan")))

        # 返回登录摘要。
        return {"success": True, "data": self.user_data}

    def save_cookie(self, output_dir):

        """
        保存康博士 ABrain 当前会话信息。

        :param output_dir: 会话信息输出目录。
        :type output_dir: str
        :return: 会话信息文件路径。
        :rtype: str
        """

        # 创建会话信息输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建会话信息文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 组装会话信息。
        cookie_data = {"user": self.user_data, "site_root_url": self.site_root_url}

        # 写入会话信息文件。
        with open(cookie_path, "w", encoding="utf-8") as file_obj:
            json.dump(cookie_data, file_obj, ensure_ascii=False, indent=2)

        # 打印会话保存日志。
        self.ph.success(self.ph.kv("会话信息已保存", self.ph.path(cookie_path), "green"))

        # 返回会话信息文件路径。
        return cookie_path

    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, start_date, end_date)

        # 返回协议分页查询结果。
        return self.fetch_protocol_rows(data_type, start_date, end_date)


    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型业务数据并生成 Excel。

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

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, start_date, end_date)

        # 查询协议数据行。
        rows = self.fetch_protocol_rows(data_type, start_date, end_date)

        # 读取输出目录。
        save_dir = output_dir or "downloads"

        # 创建输出目录。
        os.makedirs(save_dir, exist_ok=True)

        # 构建目标文件名。
        target_name = self.build_output_file_name(data_type, start_date, end_date)

        # 拼接目标文件路径。
        target_path = os.path.join(save_dir, target_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(data_type, rows, target_path)

        # 应用统一 Excel 样式。
        apply_standard_excel_style(target_path)

        # 打印 Excel 生成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(target_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 文件路径。
        return target_path

    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        解析标准输出文件名使用的业务日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准输出文件名使用的业务日期。
        :rtype: str | None
        """

        # 判断当前数据类型是否为库存类。
        if data_type == "库存":

            # 返回库存类使用的运行当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向类使用的查询开始日期。
        return start_date or end_date


    def ensure_logged_in(self):

        """
        确保当前协议会话已经登录。

        :return: None。
        :rtype: None
        """

        # 判断当前会话是否已经登录。
        if not self.logged_in:

            # 执行平台登录。
            self.login()

    def fetch_protocol_rows(self, data_type, start_date, end_date):

        """
        通过康博士 ABrain 协议分页读取业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准字段与原始字段合并后的数据行。
        :rtype: list[dict]
        """

        # 确保当前会话已经登录。
        self.ensure_logged_in()

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 初始化当前页码。
        page_num = 1

        # 初始化结果行容器。
        result_rows = []

        # 循环读取分页数据。
        while True:

            # 构建分页请求体。
            request_payload = self.build_query_payload(query_definition, start_date, end_date, page_num)

            # 发送分页查询请求。
            response_data = self.post_api("/exe", request_payload, user_data=self.user_data, referer=f"parser/{query_definition['window_id']}")

            # 校验分页查询是否成功。
            if response_data.get("code") != "00":

                # 抛出查询失败异常。
                raise RuntimeError(f"{data_type}查询失败：{response_data.get('msg') or response_data}")

            # 读取响应数据主体。
            response_body = response_data.get("data") if isinstance(response_data.get("data"), dict) else {}

            # 读取当前页原始行。
            page_rows = response_body.get("rkey") if isinstance(response_body.get("rkey"), list) else []

            # 读取分页信息。
            page_info = response_body.get("optionPage") if isinstance(response_body.get("optionPage"), dict) else {}

            # 转换并追加当前页数据。
            for row_index, row in enumerate(page_rows, start=1):
                result_rows.append(self.convert_row(data_type, query_definition, row, start_date, end_date, page_num, row_index))

            # 打印分页读取日志。
            self.ph.info(self.ph.join(self.ph.kv("分页读取", data_type, "cyan"), self.ph.kv("页码", page_num, "cyan"), self.ph.kv("本页", f"{len(page_rows)} 条", "cyan"), self.ph.kv("累计", f"{len(result_rows)} 条", "green")))

            # 读取总页数。
            total_pages = int(page_info.get("pages") or page_num)

            # 判断是否已经读取到最后一页。
            if page_num >= total_pages:

                # 结束分页循环。
                break

            # 递增页码。
            page_num += 1

        # 返回全部结果行。
        return result_rows

    def build_query_payload(self, query_definition, start_date, end_date, page_num):

        """
        构建康博士 ABrain 查询请求体。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_num: 当前页码。
        :type page_num: int
        :return: 查询请求体。
        :rtype: dict
        """

        # 初始化页面查询参数。
        sql_param = {"ITEMINFO": ""}

        # 判断当前查询是否需要开始日期。
        if query_definition.get("date_start_key"):

            # 写入开始日期参数。
            sql_param[query_definition["date_start_key"]] = self.format_query_datetime(start_date, "00:00:00")

        # 判断当前查询是否需要结束日期。
        if query_definition.get("date_end_key"):

            # 写入结束日期参数。
            sql_param[query_definition["date_end_key"]] = self.format_query_datetime(end_date, "23:59:59")

        # 构建 SQL 查询列表。
        sql_list = [{
            "sql_id": query_definition["sql_id"],
            "sql_param": sql_param,
            "result_key": "rkey",
            "page_param": {"pageNum": page_num, "pageSize": self.page_size},
            "sql_type": "select_list",
            "ds_id": self.group_id,
        }]

        # 返回接口请求体。
        return {"P_WINDOW_ID": query_definition["window_id"], "_sys_sql_list_key": sql_list}

    def format_query_datetime(self, value, time_text):

        """
        格式化康博士 ABrain 查询日期时间参数。

        :param value: 日期文本。
        :type value: str | None
        :param time_text: 默认时间文本。
        :type time_text: str
        :return: 日期时间文本。
        :rtype: str
        """

        # 判断日期是否为空。
        if not value:

            # 返回空文本。
            return ""

        # 截取日期部分。
        date_text = str(value)[:10]

        # 返回带时间的日期文本。
        return f"{date_text} {time_text}"

    def convert_row(self, data_type, query_definition, source_row, start_date, end_date, page_num, row_index):

        """
        转换康博士 ABrain 响应行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_definition: 查询定义。
        :type query_definition: dict
        :param source_row: 接口原始行。
        :type source_row: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_num: 当前页码。
        :type page_num: int
        :param row_index: 页内行号。
        :type row_index: int
        :return: 转换后的数据行。
        :rtype: dict
        """

        # 初始化输出行。
        output_row = {}

        # 前置页面标准列。
        for header_name, field_name in query_definition["fields"]:
            output_row[header_name] = source_row.get(field_name, "")

        # 写入请求开始日期。
        output_row["请求开始日期"] = start_date or ""

        # 写入请求结束日期。
        output_row["请求结束日期"] = end_date or ""

        # 写入数据类型。
        output_row["数据类型"] = data_type

        # 写入协议页码。
        output_row["协议页码"] = page_num

        # 写入页内行号。
        output_row["页内行号"] = row_index

        # 追加接口返回的全部原始字段。
        for field_name, field_value in source_row.items():
            if field_name not in output_row:
                output_row[field_name] = field_value

        # 返回转换后的数据行。
        return output_row

    def write_rows_to_excel(self, data_type, rows, target_path):

        """
        写入查询结果到 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param target_path: Excel 输出路径。
        :type target_path: str
        :return: None。
        :rtype: None
        """

        # 创建工作簿对象。
        workbook = Workbook()

        # 读取活动工作表。
        worksheet = workbook.active

        # 设置工作表标题。
        worksheet.title = data_type

        # 构建表头列表。
        headers = self.build_headers(data_type, rows)

        # 写入表头。
        worksheet.append(headers)

        # 写入数据行。
        for row in rows:
            worksheet.append([row.get(header, "") for header in headers])

        # 保存工作簿。
        workbook.save(target_path)

    def build_headers(self, data_type, rows):

        """
        构建 Excel 表头列表。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :return: Excel 表头列表。
        :rtype: list[str]
        """

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 初始化表头列表。
        headers = [header_name for header_name, _field_name in query_definition["fields"]]

        # 追加元数据表头。
        headers.extend(["请求开始日期", "请求结束日期", "数据类型", "协议页码", "页内行号"])

        # 遍历所有数据行。
        for row in rows:

            # 追加未收录的原始字段。
            for field_name in row.keys():
                if field_name not in headers:
                    headers.append(field_name)

        # 返回表头列表。
        return headers

    def resolve_query_definition(self, data_type):

        """
        读取数据类型对应的查询定义。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询定义。
        :rtype: dict
        """

        # 校验数据类型是否支持。
        if data_type not in COMBRAIN_JYSC_SUPPORTED_DATA_TYPES:

            # 抛出不支持的数据类型异常。
            raise ValueError(f"康博士 ABrain 不支持数据类型：{data_type}")

        # 返回查询定义。
        return COMBRAIN_JYSC_QUERY_DEFINITIONS[data_type]

    def post_api(self, endpoint, payload, user_data=None, referer="home"):

        """
        发送康博士 ABrain 协议 POST 请求。

        :param endpoint: 接口路径。
        :type endpoint: str
        :param payload: 内层业务请求体。
        :type payload: dict
        :param user_data: 登录用户信息。
        :type user_data: dict | None
        :param referer: Referer 相对路径。
        :type referer: str
        :return: JSON 响应体。
        :rtype: dict
        """

        # 拼接完整接口地址。
        request_url = f"{self.site_root_url}{endpoint}"

        # 构建加密表单体。
        request_body = self.build_wrapped_form(payload, user_data=user_data)

        # 构建请求头。
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": self.site_root_url.rsplit("/", 1)[0],
            "Referer": f"{self.site_root_url}/{referer}",
        }

        # 构建 POST 请求对象。
        request = Request(request_url, data=request_body.encode("utf-8"), headers=headers, method="POST")

        # 发送请求并读取响应。
        with self.opener.open(request, timeout=60) as response:
            response_text = response.read().decode("utf-8", errors="replace")

        # 返回 JSON 响应体。
        return json.loads(response_text)

    def build_wrapped_form(self, payload, user_data=None):

        """
        构建康博士 ABrain 加密表单体。

        :param payload: 内层业务请求体。
        :type payload: dict
        :param user_data: 登录用户信息。
        :type user_data: dict | None
        :return: URL 编码表单体。
        :rtype: str
        """

        # 序列化内层业务请求体。
        plain_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        # 计算签名与 AES 初始向量。
        sign_text = md5_hex(plain_text)[:16]

        # 加密内层业务请求体。
        cipher_text = aes_cbc_pkcs7_base64(plain_text, COMBRAIN_JYSC_AES_KEY, sign_text)

        # 替换 Base64 加号占位符。
        cipher_text = cipher_text.replace("+", "<<%2B>>")

        # 读取当前会话 ID。
        session_id = "" if user_data is None else user_data.get("sessionId", "")

        # 读取当前数据库用户。
        db_user = "" if user_data is None else user_data.get("dbUser", "")

        # 返回 URL 编码表单体。
        return urlencode({"json": cipher_text, "sign": sign_text, "sessionId": session_id or "null", "dbUser": db_user or "null"})
