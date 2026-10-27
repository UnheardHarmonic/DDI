# -*- coding: utf-8 -*-
"""
安徽新聚源医药科技有限公司活字格直连平台协议适配器。

本模块负责活字格账号校验、查询命令参数构建、分页数据读取和本地 Excel 文件生成。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间解析对象。
from datetime import datetime

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入下载命名工具。
from ddi_framework import DownloadWatcher

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient


# 定义安徽新聚源数据类型查询模板。
XJY_QUERY_DEFINITIONS = {
    "购进流向": {
        "页面名称": "入库查询",
        "路径": "%E6%9F%A5%E8%AF%A2%E5%85%A5%E5%BA%93%E6%98%8E%E7%BB%86",
        "表名": "erp_rkmx",
        "视图名": "查询入库明细表格1",
        "列表位置": "查询入库明细|表格1",
        "查询命令": "05724ad7099643e2912eaf079d68acec",
        "字段列表": ["单据编号", "日期", "客商名称", "排序", "商品编号", "品名", "规格", "厂家", "包装单位", "数量", "含税单价", "税率", "含税金额", "批号", "有效期至", "直连标记", "客商编号", "单据类型", "入库单号"],
        "空条件键": ["=AA4", "=AL4", "=J6", "=U6", "=AF6"],
    },
    "配送流向": {
        "页面名称": "出库查询",
        "路径": "%E6%9F%A5%E8%AF%A2%E5%87%BA%E5%BA%93%E6%98%8E%E7%BB%86",
        "表名": "erp_ckmx",
        "视图名": "查询出库明细表格1",
        "列表位置": "查询出库明细|表格1",
        "查询命令": "9f8f2d32adf4446dbd87852e399ff31a",
        "字段列表": ["单据编号", "日期", "客商名称", "排序", "商品编号", "品名", "规格", "厂家", "包装单位", "数量", "含税单价", "税率", "含税金额", "批号", "有效期至", "供货商", "直连标记", "客商编号"],
        "空条件键": ["=J6", "=AA4", "=AL4", "=AF6", "=U6"],
    },
    "库存": {
        "页面名称": "库存查询",
        "路径": "%E6%9F%A5%E8%AF%A2%E5%BA%93%E5%AD%98%E6%98%8E%E7%BB%86",
        "表名": "erp_kcmx",
        "视图名": "查询库存明细表格1",
        "列表位置": "查询库存明细|表格1",
        "查询命令": "839e37c692c347598ddd89701d96bfd7",
        "字段列表": ["入库日期", "供货商", "商品编号", "品名", "规格", "厂家", "包装单位", "数量", "计价", "税率", "批号", "有效期至", "直连标记"],
        "空条件键": ["=AA4", "=AL4", "=U6", "=J6"],
    },
}


# 定义安徽新聚源活字格平台适配器。
class XjyPlatform(BasePlatform):

    """
    安徽新聚源活字格直连平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 安徽新聚源活字格平台适配器实例。
    :rtype: XjyPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化安徽新聚源活字格平台协议适配器。

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

        # 保存平台登录页地址。
        self.login_page_url = account.get("登录页", "http://120.193.90.144:10006/directdata/")

        # 保存平台根地址。
        self.base_url = account.get("接口根地址", "http://120.193.90.144:10006")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态。
        self.logged_in = False

        # 初始化登录结果。
        self.login_result = {}

    # 定义平台登录方法。
    def login(self):

        """
        执行安徽新聚源活字格平台协议登录校验。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("安徽新聚源登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 初始化活字格会话 Cookie。
        self.http.get(self.login_page_url, referer=self.base_url)

        # 读取登录账号。
        login_name = self.clean_login_name()

        # 读取登录密码。
        login_password = self.clean_login_password()

        # 打印账号校验日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", login_name, "cyan"), self.ph.kv("密码长度", len(login_password), "yellow")))

        # 查询平台保存的账号密码。
        password_rows = self.query_odata_rows(f"ksoa_right?$select=登录密码&$filter=直连标记 eq '{login_name}'")

        # 校验账号是否存在。
        if not password_rows:

            # 抛出账号缺失异常。
            raise RuntimeError(f"{self.company_name} 登录失败：账号不存在")

        # 读取平台密码。
        platform_password = str(password_rows[0].get("登录密码", ""))

        # 校验密码是否匹配。
        if platform_password != login_password:

            # 抛出密码错误异常。
            raise RuntimeError(f"{self.company_name} 登录失败：密码不匹配")

        # 查询密码修改状态。
        change_rows = self.query_odata_rows(f"ksoa_right?$select=是否修改&$filter=直连标记 eq '{login_name}'")

        # 读取密码修改状态。
        change_status = change_rows[0].get("是否修改", "") if change_rows else ""

        # 保存登录结果。
        self.login_result = {"登录状态": "成功", "密码状态": change_status, "Cookie数量": len(list(self.http.cookie_jar))}

        # 标记登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("正式登录成功", "活字格协议校验通过", "green"), self.ph.kv("Cookie数", len(list(self.http.cookie_jar)), "cyan")))

        # 返回登录结果。
        return self.login_result

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存协议会话 Cookie。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存 Cookie 文件。
        self.http.save_cookie_file(cookie_path)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义平台导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出安徽新聚源平台数据。

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

        # 返回本地生成的 Excel 文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义平台查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询安徽新聚源平台数据。

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

        # 返回协议查询结果。
        return self.fetch_protocol_rows(data_type, start_date, end_date)

    # 定义查询落地方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询安徽新聚源平台数据并生成 Excel。

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

        # 读取协议查询结果。
        rows = self.fetch_protocol_rows(data_type, start_date, end_date)

        # 构建输出目录。
        save_dir = output_dir or "downloads"

        # 创建输出目录。
        os.makedirs(save_dir, exist_ok=True)

        # 构建目标文件名。
        target_name = self.build_output_file_name(data_type, start_date, end_date)

        # 拼接目标文件路径。
        target_path = os.path.join(save_dir, target_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(data_type, rows, target_path)

        # 打印 Excel 生成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(target_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 文件路径。
        return target_path

    # 定义数据类型分隔线打印方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印数据类型查询分隔线。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 打印标准阶段分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

        # 返回空结果。
        return None

    # 定义协议查询方法。
    def fetch_protocol_rows(self, data_type, start_date, end_date):

        """
        使用活字格协议查询数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 判断当前会话是否已登录。
        if not self.logged_in:

            # 执行平台登录。
            self.login()

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 构建业务页面地址。
        page_url = self.build_page_url(query_definition)

        # 打印协议查询日志。
        self.ph.info(self.ph.join(self.ph.kv("提交协议查询", query_definition["页面名称"], "cyan"), self.ph.kv("端点", "/Home/GetTableDataWithOffset", "yellow")))

        # 构建协议查询载荷。
        payload = self.build_query_payload(query_definition, start_date, end_date)

        # 提交协议查询请求。
        result = self.http.post_json(urljoin(self.base_url + "/", "directdata/Home/GetTableDataWithOffset"), payload, page_url)

        # 解析协议查询结果行。
        rows = self.parse_query_result(data_type, result.body)

        # 打印协议解析日志。
        self.ph.success(self.ph.join(self.ph.kv("协议查询完成", data_type, "green"), self.ph.kv("记录数", len(rows), "cyan")))

        # 返回查询结果行。
        return rows

    # 定义 OData 查询方法。
    def query_odata_rows(self, odata_string):

        """
        查询活字格 OData 公式数据。

        :param odata_string: OData 查询字符串。
        :type odata_string: str
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 构建 OData 请求地址。
        request_url = urljoin(self.base_url + "/", "directdata/Home/GetTableDataODataFormula")

        # 提交 OData JSON 请求。
        result = self.http.post_json(request_url, {"ODataString": odata_string}, self.login_page_url)

        # 解析 OData 响应文本。
        response_data = self.http.decode_json(result)

        # 判断 OData 是否存在错误信息。
        if response_data.get("ErrorMessage"):

            # 抛出 OData 查询异常。
            raise RuntimeError(f"{self.company_name} OData 查询失败：{response_data.get('ErrorMessage')}")

        # 返回 OData 数据行。
        return response_data.get("Data", [])

    # 定义协议查询载荷构建方法。
    def build_query_payload(self, query_definition, start_date, end_date):

        """
        构建活字格分页查询载荷。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 协议查询载荷。
        :rtype: dict
        """

        # 构建字段绑定列表。
        binding_infos = [{"TableName": query_definition["表名"], "ColumnName": column_name} for column_name in query_definition["字段列表"]]

        # 构建查询参数字典。
        param_list = self.build_query_param_list(query_definition, start_date, end_date)

        # 返回分页查询载荷。
        return {
            "bindingInfos": binding_infos,
            "currentRowInfo": {"currentTable": query_definition["表名"], "viewname": query_definition["视图名"], "listviewLocation": query_definition["列表位置"]},
            "demandRowCount": 0,
            "currentDataLength": 0,
            "needRowVersion": True,
            "queryCommandInfo": {"id": query_definition["查询命令"], "paramList": param_list},
            "editorDataInfos": None,
            "sortCommandID": None,
            "orderByInfo": None,
            "offsetConditionInfo": {"targetPage": 1, "pageLimitRowCount": 0},
            "columnFilterQueries": None,
            "totalRowBindingInfos": [],
        }

    # 定义查询参数构建方法。
    def build_query_param_list(self, query_definition, start_date, end_date):

        """
        构建活字格查询命令参数字典。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询命令参数字典。
        :rtype: dict
        """

        # 初始化查询参数字典。
        param_list = {}

        # 写入开始日期参数。
        param_list['=TEXT(J4,"yyyy-mm-dd")'] = self.format_page_date(start_date)

        # 写入结束日期参数。
        param_list['=TEXT(Q4,"yyyy-mm-dd")'] = self.format_page_date(end_date)

        # 写入页面空筛选条件。
        for condition_key in query_definition["空条件键"]:

            # 设置当前空筛选条件。
            param_list[condition_key] = None

        # 写入当前账号参数。
        param_list['=IF(ISBLANK(usercode),"error",usercode)'] = self.clean_login_name()

        # 返回查询参数字典。
        return param_list

    # 定义协议查询结果解析方法。
    def parse_query_result(self, data_type, response_body):

        """
        解析活字格分页查询响应。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param response_body: HTTP 响应体字节。
        :type response_body: bytes
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 判断响应体是否为空。
        if not response_body:

            # 返回空行列表。
            return []

        # 解码响应体文本。
        response_text = response_body.decode("utf-8", errors="replace")

        # 解析 JSON 响应体。
        response_data = json.loads(response_text)

        # 读取原始数据行。
        raw_rows = response_data.get("table", {}).get("Data", [])

        # 初始化结果行列表。
        rows = []

        # 遍历原始数据行。
        for raw_row in raw_rows:

            # 追加标准字段行。
            rows.append(self.convert_raw_row(query_definition, raw_row))

        # 返回标准数据行。
        return rows

    # 定义原始行转换方法。
    def convert_raw_row(self, query_definition, raw_row):

        """
        转换活字格 C0/C1 字段行为中文字段行。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param raw_row: 原始行数据。
        :type raw_row: dict
        :return: 中文字段行。
        :rtype: dict
        """

        # 初始化结果行。
        row_data = {}

        # 遍历字段列表。
        for column_index, column_name in enumerate(query_definition["字段列表"]):

            # 读取原始字段值。
            raw_value = raw_row.get(f"C{column_index}", "")

            # 写入中文字段值。
            row_data[column_name] = self.normalize_cell_value(raw_value)

        # 返回中文字段行。
        return row_data

    # 定义单元格值标准化方法。
    def normalize_cell_value(self, value):

        """
        标准化活字格单元格值。

        :param value: 原始单元格值。
        :type value: object
        :return: 标准化后的单元格值。
        :rtype: object
        """

        # 判断单元格值是否为文本。
        if isinstance(value, str):

            # 返回去除首尾空白后的文本。
            return value.strip()

        # 返回原始单元格值。
        return value

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, data_type, rows, target_path):

        """
        将查询结果写入 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行列表。
        :type rows: list[dict]
        :param target_path: 目标文件路径。
        :type target_path: str
        :return: None。
        :rtype: None
        """

        # 导入工作簿对象。
        from openpyxl import Workbook

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 创建工作簿。
        workbook = Workbook()

        # 读取活动工作表。
        worksheet = workbook.active

        # 写入表头。
        worksheet.append(query_definition["字段列表"])

        # 遍历查询结果行。
        for row_data in rows:

            # 写入当前数据行。
            worksheet.append([row_data.get(column_name, "") for column_name in query_definition["字段列表"]])

        # 删除旧目标文件。
        self.remove_existing_file(target_path)

        # 保存目标工作簿。
        workbook.save(target_path)

        # 关闭目标工作簿。
        workbook.close()

        # 返回空结果。
        return None

    # 定义查询定义解析方法。
    def resolve_query_definition(self, data_type):

        """
        解析数据类型查询定义。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询定义。
        :rtype: dict
        """

        # 判断数据类型是否存在查询定义。
        if data_type not in XJY_QUERY_DEFINITIONS:

            # 抛出数据类型异常。
            raise ValueError(f"安徽新聚源平台不支持数据类型：{data_type}")

        # 返回查询定义。
        return XJY_QUERY_DEFINITIONS[data_type]

    # 定义页面地址构建方法。
    def build_page_url(self, query_definition):

        """
        构建活字格业务页面地址。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :return: 业务页面地址。
        :rtype: str
        """

        # 读取页面路径。
        page_path = query_definition["路径"]

        # 返回拼接后的业务页面地址。
        return urljoin(self.login_page_url, page_path.lstrip("/"))

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建输出文件名。

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

    # 定义页面日期格式化方法。
    def format_page_date(self, date_value):

        """
        格式化页面日期。

        :param date_value: 日期文本。
        :type date_value: str | None
        :return: 页面日期文本。
        :rtype: str
        """

        # 解析日期对象。
        date_obj = self.parse_date(date_value)

        # 返回页面日期格式。
        return f"{date_obj.year}-{date_obj.month:02d}-{date_obj.day:02d}"

    # 定义日期解析方法。
    def parse_date(self, date_value):

        """
        解析日期文本。

        :param date_value: 日期文本。
        :type date_value: str | None
        :return: 日期对象。
        :rtype: datetime
        """

        # 判断日期文本是否为空。
        if not date_value:

            # 返回当前日期。
            return datetime.now()

        # 遍历支持的日期格式。
        for date_format in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):

            # 捕获日期解析异常。
            try:

                # 返回解析后的日期。
                return datetime.strptime(str(date_value).strip(), date_format)

            # 处理日期解析异常。
            except ValueError:

                # 继续尝试下一种格式。
                continue

        # 抛出日期格式异常。
        raise ValueError(f"日期格式不支持：{date_value}")

    # 定义文件删除方法。
    def remove_existing_file(self, file_path):

        """
        删除已存在的目标文件。

        :param file_path: 文件路径。
        :type file_path: str
        :return: None。
        :rtype: None
        """

        # 判断目标文件是否存在。
        if os.path.exists(file_path):

            # 删除目标文件。
            os.remove(file_path)

        # 返回空结果。
        return None

    # 定义登录名读取方法。
    def clean_login_name(self):

        """
        读取登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回去除空白后的账号。
        return str(self.account.get("账号", "")).strip()

    # 定义登录密码读取方法。
    def clean_login_password(self):

        """
        读取登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回原始密码文本。
        return str(self.account.get("密码", ""))
