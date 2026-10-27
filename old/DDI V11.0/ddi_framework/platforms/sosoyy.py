# -*- coding: utf-8 -*-
"""
搜搜电商流向明细协议适配器。

本模块通过 ASP.NET MVC 登录会话和 JSON 分页接口查询销售、库存、采购及配送明细，并保留服务端返回的全部原始字段。

:return: 模块提供搜搜电商流向明细平台适配器。
:rtype: None
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入 Excel 工作簿类。
from openpyxl import Workbook

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义数据类型与接口、日期字段的协议映射。
DATA_TYPE_CONFIG = {
    "纯销流向": {"endpoint": "/FlowDetails/QuerySalesDetails", "date_field": "saleDate", "begin_field": "saleDateBegin", "end_field": "saleDateEnd"},
    "库存": {"endpoint": "/FlowDetails/QueryStockDetails", "date_field": "", "begin_field": "", "end_field": ""},
    "购进流向": {"endpoint": "/FlowDetails/QueryPurchaseDetails", "date_field": "purchaseDate", "begin_field": "purchaseDateBegin", "end_field": "purchaseDateEnd"},
    "配送流向": {"endpoint": "/FlowDetails/QueryDeliveryDetails", "date_field": "deliveryDate", "begin_field": "deliveryDateBegin", "end_field": "deliveryDateEnd"},
}

# 定义各数据类型的标准字段与服务端原始字段映射。
STANDARD_FIELD_MAP = {
    "纯销流向": [("日期", "saleDate"), ("门店编号", "storeNumber"), ("门店名称", "storeName"), ("商品ID", "drugsBase_Number"), ("品名", "drugsBase_DrugName"), ("标准品名", "drugsBase_DrugName_Standard"), ("规格", "drugsBase_Specification"), ("生产厂家", "drugsBase_Manufacturer"), ("单位", "goods_Unit"), ("批号", "batchNumber"), ("数量", "salesVolume")],
    "库存": [("门店编号", "storeNumber"), ("门店名称", "storeName"), ("商品ID", "drugsBase_Number"), ("品名", "drugsBase_DrugName"), ("标准品名", "drugsBase_DrugName_Standard"), ("规格", "drugsBase_Specification"), ("生产厂家", "drugsBase_Manufacturer"), ("单位", "goods_Unit"), ("批号", "batchNumber"), ("库存数量", "stockQty"), ("总部库存", "headquartersStock")],
    "购进流向": [("日期", "purchaseDate"), ("配送供应商", "distributionSupplier"), ("采购方", "purchaser"), ("商品ID", "drugsBase_Number"), ("品名", "drugsBase_DrugName"), ("标准品名", "drugsBase_DrugName_Standard"), ("规格", "drugsBase_Specification"), ("生产厂家", "drugsBase_Manufacturer"), ("单位", "goods_Unit"), ("批号", "batchNumber"), ("数量", "purchaseQty")],
    "配送流向": [("日期", "deliveryDate"), ("门店编号", "storeNumber"), ("门店名称", "storeName"), ("配送供应商", "distributionSupplier"), ("商品ID", "drugsBase_Number"), ("品名", "drugsBase_DrugName"), ("标准品名", "drugsBase_DrugName_Standard"), ("规格", "drugsBase_Specification"), ("生产厂家", "drugsBase_Manufacturer"), ("单位", "goods_Unit"), ("批号", "batchNumber"), ("数量", "deliveryQty")],
}


# 定义搜搜电商流向明细平台适配器。
class SosoyyPlatform(BasePlatform):

    """
    搜搜电商流向明细平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 搜搜电商流向明细平台适配器实例。
    :rtype: SosoyyPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化搜搜电商会话、查询配置和日志对象。

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

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 读取平台接口根地址。
        self.base_url = str(account.get("接口根地址", account.get("登录页", ""))).rstrip("/")

        # 读取登录页面地址。
        self.login_page_url = str(account.get("登录页", f"{self.base_url}/Account/Index"))

        # 读取登录接口地址。
        self.login_api_url = str(account.get("登录接口", f"{self.base_url}/Account"))

        # 读取可选登录预热页面地址。
        self.login_warmup_url = str(account.get("登录预热页", "")).strip()

        # 读取单页最大记录数。
        self.page_size = int(account.get("分页大小", 500))

        # 读取查询请求超时时间。
        self.query_timeout_seconds = int(account.get("查询超时秒", 180))

        # 初始化带 Cookie 管理的协议客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态标识。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        提交 ASP.NET MVC 表单登录请求并建立 Cookie 会话。

        :return: 不含凭据的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("搜搜电商流向系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 执行账号配置指定的可选预热请求。
        self.warm_up_login_session()

        # 构建页面实际提交的表单字段。
        payload = self.build_login_payload()

        # 捕获登录站点的 HTTP 失败响应。
        try:

            # 提交登录表单建立服务器会话。
            result = self.http.post_form(self.login_api_url, payload, referer=self.login_page_url)

        # 处理登录站点重定向至自身错误页的响应。
        except RuntimeError as error:

            # 保存不含凭据的异常说明。
            error_text = str(error)

            # 判断当前租户站点是否已进入错误页循环。
            if "HTTP 302" in error_text and "/Error/Index" in error_text:

                # 抛出可直接定位租户入口故障的业务异常。
                raise RuntimeError(f"{self.company_name} 登录站点不可用：租户入口持续重定向至 /Error/Index，请联系平台恢复租户或在账号抽屉更新可用入口地址。") from error

            # 保留其他协议失败的原始异常。
            raise

        # 解析服务端 JSON 登录响应。
        response_data = self.decode_login_response(result)

        # 校验响应表示登录成功。
        self.validate_login_response(response_data)

        # 标记当前协议会话已登录。
        self.logged_in = True

        # 打印不含敏感值的登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("Cookie", len(list(self.http.cookie_jar)), "cyan")))

        # 返回不含敏感字段的登录结果。
        return {"登录状态": "成功", "Cookie数量": len(list(self.http.cookie_jar))}

    # 定义可选登录预热方法。
    def warm_up_login_session(self):

        """
        在账号配置提供预热地址时访问该地址以初始化站点会话。

        :return: None。
        :rtype: None
        """

        # 判断账号未配置预热页面。
        if not self.login_warmup_url:

            # 结束无预热配置的处理。
            return

        # 拼接相对预热页面的完整地址。
        warmup_url = self.build_url(self.login_warmup_url)

        # 访问预热页面初始化服务端会话状态。
        self.http.get(warmup_url, referer=self.base_url)

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建页面 Account 登录接口需要的固定字段。

        :return: 登录表单字段。
        :rtype: dict
        """

        # 返回抓包确认的表单字段及账号配置凭据。
        return {"mobile": str(self.account.get("账号", "")), "password": str(self.account.get("密码", "")), "SMSVerification": "", "AuthorizationCode": "", "status": "", "onekey": "", "g": ""}

    # 定义登录响应解析方法。
    def decode_login_response(self, result):

        """
        解析 Account 接口返回的对象或对象数组。

        :param result: HTTP 响应结果。
        :type result: ddi_framework.http_client.HttpResult
        :return: 规范化登录响应对象。
        :rtype: dict
        """

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 解析登录响应 JSON 内容。
        response_data = json.loads(response_text)

        # 判断响应是否为对象数组。
        if isinstance(response_data, list):

            # 返回数组首项作为登录响应对象。
            return response_data[0] if response_data else {}

        # 返回对象类型的登录响应。
        return response_data if isinstance(response_data, dict) else {}

    # 定义登录响应校验方法。
    def validate_login_response(self, response_data):

        """
        校验登录响应中未出现错误状态。

        :param response_data: 规范化登录响应对象。
        :type response_data: dict
        :return: None。
        :rtype: None
        """

        # 读取登录响应状态文本。
        state_text = str(response_data.get("state", response_data.get("status", ""))).strip().lower()

        # 读取登录响应说明文本。
        message_text = str(response_data.get("content", response_data.get("message", response_data.get("msg", "")))).strip()

        # 判断响应是否为明确失败状态。
        if state_text in {"error", "false", "failed", "fail"}:

            # 抛出不含凭据的登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{message_text or '平台返回失败状态'}")

        # 判断响应说明文本是否包含密码错误提示。
        if "密码" in message_text or "账号不存在" in message_text:

            # 抛出不含凭据的登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{message_text}")

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录会话 Cookie 供公共任务服务记录。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 输出文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存当前协议会话 Cookie。
        self.http.save_cookie_file(cookie_path)

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义原始数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的全部原始业务记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 查询当前数据类型的全部分页数据。
        query_result = self.query_sosoyy_data(data_type, start_date, end_date)

        # 返回未裁剪的原始记录列表。
        return query_result["rows"]

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成标准字段加原始字段 Excel。

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

        # 查询当前数据类型的全部分页数据。
        query_result = self.query_sosoyy_data(data_type, start_date, end_date)

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入标准字段和服务端全部原始字段。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], data_type, output_path)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义平台导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        使用协议查询结果生成本地 Excel 文件。

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

        # 调用查询并落地 Excel 的统一流程。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义协议主查询方法。
    def query_sosoyy_data(self, data_type, start_date, end_date):

        """
        建立登录态、提交 JSON 筛选条件并读取全部分页记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始字段、原始记录及实际日期范围。
        :rtype: dict
        """

        # 校验数据类型已配置协议端点。
        self.validate_data_type(data_type)

        # 确保当前 HTTP 会话已经登录。
        self.ensure_login()

        # 解析当前查询的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(data_type, start_date, end_date)

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, resolved_start_date, resolved_end_date)

        # 请求并合并当前数据类型的所有分页记录。
        headers, rows = self.fetch_all_pages(data_type, resolved_start_date, resolved_end_date)

        # 校验流向记录的业务日期处于请求范围。
        self.validate_result_date_range(data_type, rows, resolved_start_date, resolved_end_date)

        # 打印协议查询完成摘要。
        self.ph.success(self.ph.join(self.ph.kv("查询接口", DATA_TYPE_CONFIG[data_type]["endpoint"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果数据结构。
        return {"headers": headers, "rows": rows, "start_date": resolved_start_date, "end_date": resolved_end_date}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型存在于平台接口映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已配置协议端点。
        if data_type in DATA_TYPE_CONFIG:

            # 结束有效数据类型校验。
            return

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

    # 定义登录态确保方法。
    def ensure_login(self):

        """
        确保当前协议客户端已经建立有效登录态。

        :return: None。
        :rtype: None
        """

        # 判断当前会话已经完成登录。
        if self.logged_in:

            # 结束重复登录处理。
            return

        # 执行平台登录流程。
        self.login()

    # 定义查询日期解析方法。
    def resolve_query_dates(self, data_type, start_date, end_date):

        """
        解析库存快照或流向明细使用的日期范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 解析后的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 生成当前导出日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 判断当前数据类型是否为库存。
        if data_type == "库存":

            # 返回库存文件命名使用的当天日期。
            return today_text, today_text

        # 解析流向查询开始日期。
        resolved_start_date = str(start_date or today_text)

        # 解析流向查询结束日期。
        resolved_end_date = str(end_date or resolved_start_date)

        # 校验流向日期范围顺序。
        self.validate_query_range(resolved_start_date, resolved_end_date)

        # 返回流向查询日期范围。
        return resolved_start_date, resolved_end_date

    # 定义日期范围校验方法。
    def validate_query_range(self, start_date, end_date):

        """
        校验开始日期不晚于结束日期。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 解析开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断日期范围顺序是否正确。
        if start_value <= end_value:

            # 结束有效日期范围校验。
            return

        # 抛出无效日期范围异常。
        raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{start_date} > {end_date}")

    # 定义查询阶段日志方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印当前数据类型的标准查询日志分隔线。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印包含日期范围的查询阶段分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

    # 定义全部分页读取方法。
    def fetch_all_pages(self, data_type, start_date, end_date):

        """
        分页请求 JSON 接口并合并服务端原始记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 原始字段定义和全部原始记录。
        :rtype: tuple[list[dict], list[dict]]
        """

        # 初始化首个响应返回的字段定义。
        headers = []

        # 初始化所有分页原始记录。
        rows = []

        # 初始化预期总记录数。
        expected_count = None

        # 初始化当前请求页码。
        page_index = 1

        # 持续请求直到读取完服务端全部记录。
        while True:

            # 构建当前页 JSON 筛选请求体。
            payload = self.build_query_payload(data_type, start_date, end_date, page_index)

            # 请求当前页 JSON 数据。
            response_data = self.fetch_page(data_type, payload)

            # 读取当前页服务端数据对象。
            data_block = response_data.get("data", {}) if isinstance(response_data, dict) else {}

            # 读取当前页记录列表。
            page_rows = data_block.get("list", []) if isinstance(data_block, dict) else []

            # 校验当前页记录列表为数组。
            if not isinstance(page_rows, list):

                # 抛出无效数据结构异常。
                raise RuntimeError(f"{self.company_name} {data_type} 查询返回的 list 字段不是数组")

            # 判断当前页是否首次提供字段定义。
            if not headers:

                # 解析首个响应中的字段定义。
                headers = self.resolve_headers(data_block, page_rows)

            # 合并当前页原始记录。
            rows.extend(row for row in page_rows if isinstance(row, dict))

            # 读取服务端总记录数。
            expected_count = self.resolve_record_count(data_block, expected_count)

            # 打印当前页读取进度。
            self.ph.info(self.ph.join(self.ph.kv("分页", f"{page_index}", "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan"), self.ph.kv("累计", len(rows), "cyan")))

            # 判断累计记录已达到服务端总数。
            has_reached_expected_count = expected_count is not None and len(rows) >= expected_count

            # 判断未提供总记录数时当前页不足分页大小。
            is_last_unknown_page = expected_count is None and len(page_rows) < self.page_size

            # 判断当前分页已经完成。
            if not page_rows or is_last_unknown_page or has_reached_expected_count:

                # 结束分页读取循环。
                break

            # 增加下一页页码。
            page_index += 1

        # 返回字段定义和全部原始记录。
        return headers, rows

    # 定义单页数据请求方法。
    def fetch_page(self, data_type, payload):

        """
        请求并校验单页 JSON 业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param payload: JSON 查询请求体。
        :type payload: dict
        :return: 服务端 JSON 响应对象。
        :rtype: dict
        """

        # 读取当前数据类型端点配置。
        data_config = DATA_TYPE_CONFIG[data_type]

        # 拼接当前数据类型完整接口地址。
        endpoint_url = self.build_url(data_config["endpoint"])

        # 构建 JSON 查询请求头。
        headers = self.http.json_headers(f"{self.base_url}/FlowDetails/Index.htm")

        # 编码 JSON 查询请求体。
        request_data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 提交带平台超时配置的 JSON 查询请求。
        result = self.http.request("POST", endpoint_url, headers=headers, data=request_data, timeout=self.query_timeout_seconds)

        # 解析接口 JSON 响应。
        response_data = self.http.decode_json(result)

        # 校验接口未返回失败状态。
        self.validate_query_response(data_type, response_data)

        # 返回当前页响应对象。
        return response_data

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, start_date, end_date, page_index):

        """
        构建流向管理页面提交的完整 JSON 筛选条件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_index: 当前分页页码。
        :type page_index: int
        :return: JSON 查询请求体。
        :rtype: dict
        """

        # 初始化页面统一使用的空筛选条件。
        payload = {"isAccurateQueryDrugsBaseNumber": False, "storeName": "", "purchaser": "", "goods": "", "salesVolumeMin": None, "salesVolumeMax": None, "deliveryDateBegin": None, "deliveryDateEnd": None, "deliveryQtyMin": None, "deliveryQtyMax": None, "purchaseDateBegin": None, "purchaseDateEnd": None, "purchaseQtyMin": None, "purchaseQtyMax": None, "saleDateBegin": None, "saleDateEnd": None, "stockQtyMin": None, "stockQtyMax": None, "pageIndex": int(page_index), "pageSize": self.page_size}

        # 读取当前数据类型的日期字段配置。
        data_config = DATA_TYPE_CONFIG[data_type]

        # 判断当前数据类型是否需要日期条件。
        if data_config["begin_field"]:

            # 写入当前数据类型的开始日期。
            payload[data_config["begin_field"]] = start_date

            # 写入当前数据类型的结束日期。
            payload[data_config["end_field"]] = end_date

        # 返回完整查询请求体。
        return payload

    # 定义查询响应校验方法。
    def validate_query_response(self, data_type, response_data):

        """
        校验业务接口响应为成功状态且包含数据对象。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param response_data: JSON 响应对象。
        :type response_data: dict
        :return: None。
        :rtype: None
        """

        # 判断响应对象是否为字典。
        if not isinstance(response_data, dict):

            # 抛出无效响应结构异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询未返回 JSON 对象")

        # 判断服务端是否明确返回失败。
        if response_data.get("isSuccess") is False:

            # 读取服务端失败说明。
            message_text = str(response_data.get("info", response_data.get("message", "平台返回失败状态")))

            # 抛出查询失败异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询失败：{message_text}")

        # 判断响应是否包含数据对象。
        if isinstance(response_data.get("data"), dict):

            # 结束有效响应校验。
            return

        # 抛出数据对象缺失异常。
        raise RuntimeError(f"{self.company_name} {data_type} 查询未返回 data 对象")

    # 定义字段元数据解析方法。
    def resolve_headers(self, data_block, rows):

        """
        从 fields 元数据或首行键顺序解析完整原始字段定义。

        :param data_block: 服务端数据对象。
        :type data_block: dict
        :param rows: 当前页原始记录。
        :type rows: list[dict]
        :return: 原始字段定义列表。
        :rtype: list[dict]
        """

        # 读取服务端字段元数据。
        fields = data_block.get("fields", []) if isinstance(data_block, dict) else []

        # 初始化有序字段定义列表。
        headers = []

        # 遍历服务端字段元数据。
        for field in fields if isinstance(fields, list) else []:

            # 读取当前元数据的原始字段键。
            field_key = str(field.get("dataIndex", "")).strip() if isinstance(field, dict) else ""

            # 跳过缺少原始字段键的元数据。
            if not field_key:

                # 继续读取下一项字段元数据。
                continue

            # 读取当前字段的页面标题。
            field_title = str(field.get("title", field_key)).strip() if isinstance(field, dict) else field_key

            # 保存当前字段定义。
            headers.append({"key": field_key, "title": field_title or field_key})

        # 判断服务端未提供可用字段元数据。
        if not headers and rows:

            # 按首行原始键顺序补齐字段定义。
            headers = [{"key": str(key), "title": str(key)} for key in rows[0].keys()]

        # 返回完整原始字段定义。
        return headers

    # 定义总记录数解析方法。
    def resolve_record_count(self, data_block, fallback):

        """
        从服务端数据对象读取可用总记录数。

        :param data_block: 服务端数据对象。
        :type data_block: dict
        :param fallback: 已解析的总记录数。
        :type fallback: int | None
        :return: 当前总记录数。
        :rtype: int | None
        """

        # 读取服务端总记录数字段。
        raw_count = data_block.get("recordCount", fallback) if isinstance(data_block, dict) else fallback

        # 尝试转换服务端总记录数。
        try:

            # 返回转换后的非负记录数。
            return max(0, int(raw_count))

        # 处理空值或非数字记录数。
        except (TypeError, ValueError):

            # 返回已有总记录数。
            return fallback

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向记录日期未超出提交的查询范围。

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

        # 读取当前数据类型的业务日期字段。
        date_field = DATA_TYPE_CONFIG[data_type]["date_field"]

        # 判断当前数据类型不包含业务日期字段。
        if not date_field:

            # 结束库存日期范围校验。
            return

        # 解析请求开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d").date()

        # 解析请求结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d").date()

        # 遍历返回的原始记录。
        for row in rows:

            # 读取当前记录的业务日期文本。
            date_text = str(row.get(date_field, "")).strip()

            # 跳过空日期字段记录。
            if not date_text:

                # 继续校验下一条记录。
                continue

            # 解析日期文本前十位。
            record_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()

            # 判断记录日期是否处于请求范围。
            if start_value <= record_date <= end_value:

                # 继续校验下一条记录。
                continue

            # 抛出业务日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期超出查询范围：{date_text}")

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, data_type, output_path):

        """
        将标准字段前置并追加全部原始字段写入 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 原始字段定义列表。
        :type headers: list[dict]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param output_path: Excel 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认活动工作表。
        worksheet = workbook.active

        # 设置工作表名称为当前数据类型。
        worksheet.title = data_type

        # 读取标准字段映射。
        standard_mapping = STANDARD_FIELD_MAP[data_type]

        # 构建标准字段标题列表。
        standard_headers = [item[0] for item in standard_mapping]

        # 构建原始字段标题列表。
        raw_headers = self.build_raw_excel_headers(headers)

        # 写入标准字段和原始字段表头。
        worksheet.append(standard_headers + raw_headers)

        # 遍历全部原始记录。
        for row in rows:

            # 构建当前记录的标准字段值。
            standard_values = [row.get(field_key, "") for _, field_key in standard_mapping]

            # 构建当前记录的原始字段值。
            raw_values = [row.get(str(field.get("key", "")), "") for field in headers]

            # 写入当前记录全部字段值。
            worksheet.append(standard_values + raw_values)

        # 保存未样式化 Excel 工作簿。
        workbook.save(output_path)

        # 关闭 Excel 工作簿。
        workbook.close()

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)

    # 定义原始 Excel 表头构建方法。
    def build_raw_excel_headers(self, headers):

        """
        以页面字段标题构建不重复的原始 Excel 列名。

        :param headers: 原始字段定义列表。
        :type headers: list[dict]
        :return: 不重复的原始 Excel 表头列表。
        :rtype: list[str]
        """

        # 初始化已使用表头集合。
        used_headers = set()

        # 初始化原始 Excel 表头列表。
        excel_headers = []

        # 遍历服务端原始字段定义。
        for field in headers:

            # 读取页面字段标题。
            title_text = str(field.get("title", field.get("key", ""))).strip()

            # 构建默认原始字段表头。
            header_text = f"原始_{title_text or field.get('key', '')}"

            # 初始化重复字段序号。
            duplicate_index = 2

            # 处理重复的页面字段标题。
            while header_text in used_headers:

                # 拼接带序号的原始字段表头。
                header_text = f"原始_{title_text}_{duplicate_index}"

                # 增加重复字段序号。
                duplicate_index += 1

            # 记录当前已使用原始字段表头。
            used_headers.add(header_text)

            # 保存当前原始字段表头。
            excel_headers.append(header_text)

        # 返回全部原始 Excel 表头。
        return excel_headers

    # 定义完整 URL 构建方法。
    def build_url(self, path):

        """
        将相对接口路径转换为平台完整 URL。

        :param path: 相对或完整接口地址。
        :type path: str
        :return: 完整接口地址。
        :rtype: str
        """

        # 转换路径为标准文本。
        path_text = str(path).strip()

        # 判断当前路径已经为完整 URL。
        if path_text.startswith("http://") or path_text.startswith("https://"):

            # 返回原始完整 URL。
            return path_text

        # 返回接口根地址拼接后的完整 URL。
        return f"{self.base_url}/{path_text.lstrip('/')}"
