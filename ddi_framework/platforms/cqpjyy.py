# -*- coding: utf-8 -*-
"""
重庆普健医药有限公司普健数据协同平台协议适配器。

本模块负责普健数据协同平台的账号登录、AccessToken 鉴权、
采购报表、销售报表、库存报表分页查询、标准字段前置、原始字段保留和 Excel 文件生成。
"""

# 导入哈希摘要模块。

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime


# 导入 URL 错误类型。
from urllib.error import HTTPError


# 导入 URL 请求对象。
from urllib.request import Request


# 导入 Excel 统一样式函数。
# 导入通用摘要函数。
from ddi_framework.reverse_utils import md5_hex

from ddi_framework import apply_standard_excel_style
# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义普健平台接口根路径。
CQPJYY_API_PREFIX = "/pjyy-deepexi-datanalysis-center"


# 定义普健接口英文原始字段到中文显示标题的映射。
CQPJYY_RAW_HEADER_ALIASES = {
    "busEmployeeName": "业务员",
    "makeNo": "批号",
    "customerCode": "客户编码",
    "validDateStr": "有效期至",
    "supplierCode": "供应商编码",
    "batchId": "批次号",
    "orderTimeStr": "日期",
    "categoryName": "产品分类",
    "productName": "商品名称",
    "customerAddr": "客户地址",
    "billTypeCodeName": "单据类型",
    "price": "销售价",
    "customerTaxNo": "客户税号",
    "unitPrice": "单价",
    "supplierName": "供应商名称",
    "amount": "数量",
    "orderNo": "单据编号",
    "unitName": "单位",
    "productSpecs": "商品规格",
    "factoryName": "生产企业",
    "saleArea": "销售地区",
    "customerName": "客户名称",
    "saleEmployeeName": "开票员",
    "customerTypeName": "往来单位类型",
    "productCode": "商品编码",
    "inTimeStr": "入库日期",
    "available": "可用数量",
    "purPrice": "进价",
    "money": "金额",
    "createAtStr": "创建时间",
}


# 定义普健平台查询配置。
CQPJYY_QUERY_DEFINITIONS = {
    "购进流向": {
        "endpoint": "/purchasePush/pageBySupplier",
        "column_endpoint": "/common/getBusColumn/1",
        "page_name": "采购报表",
        "date_field": "采购日期",
        "standard_fields": [
            ("采购日期", ["orderTimeStr", "validDateStr", "createAtStr", "inTimeStr"]),
            ("单据类型", ["billTypeCodeName", "billTypeName", "categoryName"]),
            ("单据编号", ["orderNo", "makeNo"]),
            ("供应商编码", ["supplierCode"]),
            ("供应商名称", ["supplierName"]),
            ("商品编码", ["productCode"]),
            ("商品名称", ["productName"]),
            ("商品规格", ["productSpecs"]),
            ("生产企业", ["factoryName"]),
            ("批号", ["makeNo", "batchId"]),
            ("有效期至", ["validDateStr"]),
            ("单位", ["unitName"]),
            ("数量", ["amount", "available"]),
            ("单价", ["unitPrice", "purPrice", "price"]),
            ("金额", ["money", "price"]),
        ],
        "empty_headers": ["采购日期", "单据类型", "单据编号", "供应商编码", "供应商名称", "商品编码", "商品名称", "商品规格", "生产企业", "批号", "有效期至", "单位", "数量", "单价", "金额"],
    },
    "配送流向": {
        "endpoint": "/sales/pageBySupplier",
        "column_endpoint": "/common/getBusColumn/2",
        "page_name": "销售报表",
        "date_field": "销售日期",
        "standard_fields": [
            ("销售日期", ["orderTimeStr", "validDateStr"]),
            ("单据编号", ["orderNo"]),
            ("客户编码", ["customerCode"]),
            ("客户名称", ["customerName"]),
            ("客户地址", ["customerAddr"]),
            ("客户类型", ["customerTypeName"]),
            ("区域", ["saleArea"]),
            ("商品编码", ["productCode"]),
            ("商品名称", ["productName"]),
            ("商品规格", ["productSpecs"]),
            ("生产企业", ["factoryName"]),
            ("批号", ["makeNo", "batchId"]),
            ("有效期至", ["validDateStr"]),
            ("单位", ["unitName"]),
            ("数量", ["amount"]),
            ("单价", ["unitPrice", "price"]),
            ("金额", ["money", "price"]),
            ("供应商编码", ["supplierCode"]),
            ("供应商名称", ["supplierName"]),
            ("业务员", ["busEmployeeName", "saleEmployeeName"]),
        ],
        "empty_headers": ["销售日期", "单据编号", "客户编码", "客户名称", "客户地址", "客户类型", "区域", "商品编码", "商品名称", "商品规格", "生产企业", "批号", "有效期至", "单位", "数量", "单价", "金额", "供应商编码", "供应商名称", "业务员"],
    },
    "库存": {
        "endpoint": "/store/page",
        "column_endpoint": "/common/getBusColumn/3",
        "page_name": "库存报表",
        "date_field": None,
        "standard_fields": [
            ("库存日期", ["库存日期"]),
            ("商品编码", ["productCode"]),
            ("商品名称", ["productName"]),
            ("商品规格", ["productSpecs"]),
            ("生产企业", ["factoryName"]),
            ("供应商编码", ["supplierCode"]),
            ("供应商名称", ["supplierName"]),
            ("批号", ["makeNo", "batchId"]),
            ("入库日期", ["inTimeStr"]),
            ("有效期至", ["validDateStr"]),
            ("单位", ["unitName"]),
            ("库存数量", ["available"]),
            ("采购单价", ["purPrice"]),
            ("库存金额", ["money"]),
        ],
        "empty_headers": ["库存日期", "商品编码", "商品名称", "商品规格", "生产企业", "供应商编码", "供应商名称", "批号", "入库日期", "有效期至", "单位", "库存数量", "采购单价", "库存金额"],
    },
}


# 定义重庆普健医药有限公司平台适配器。
class CqpjyyPlatform(BasePlatform):

    """
    重庆普健医药有限公司普健数据协同平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台适配器实例。
    :rtype: CqpjyyPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化普健数据协同平台协议适配器。

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
        self.site_root_url = account.get("登录页", "https://data.pujian.com/").rstrip("/")

        # 保存接口根地址。
        self.api_root_url = account.get("接口根地址", f"{self.site_root_url}{CQPJYY_API_PREFIX}").rstrip("/")

        # 保存登录接口路径。
        self.login_endpoint = account.get("登录接口路径", "/login/loginAccount")

        # 保存刷新令牌接口路径。
        self.refresh_endpoint = account.get("刷新令牌接口路径", "/login/refreshToken")

        # 保存登录账号。
        self.username = account.get("账号", "")

        # 保存登录密码。
        self.password = account.get("密码", "")

        # 保存系统类型编码。
        self.system_type = int(account.get("系统类型", 2))

        # 保存分页大小。
        self.page_size = int(account.get("分页大小", 200))

        # 初始化协议请求客户端并托管平台会话。
        self.http = ProtocolHttpClient(self.site_root_url)

        # 引用协议客户端管理的 Cookie 容器。
        self.cookie_jar = self.http.cookie_jar

        # 引用协议客户端管理的请求打开器。
        self.opener = self.http.opener

        # 初始化访问令牌。
        self.access_token = ""

        # 初始化刷新令牌。
        self.refresh_token = ""

        # 初始化登录状态。
        self.logged_in = False

        # 初始化平台页面表头缓存。
        self.remote_columns = {}

    # 定义平台登录方法。
    def login(self):

        """
        登录普健数据协同平台。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("普健数据协同平台登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 提交登录请求。
        response_data = self.post_json(self.login_endpoint, payload, token_required=False)

        # 校验登录业务状态。
        if str(response_data.get("code")) != "200":

            # 抛出登录失败异常。
            raise RuntimeError(f"普健数据协同平台登录失败：{response_data.get('msg') or response_data}")

        # 读取登录返回数据。
        login_data = response_data.get("data") if isinstance(response_data.get("data"), dict) else {}

        # 保存访问令牌。
        self.access_token = login_data.get("accessToken", "")

        # 保存刷新令牌。
        self.refresh_token = login_data.get("refreshToken", "")

        # 校验访问令牌是否存在。
        if not self.access_token:

            # 抛出令牌缺失异常。
            raise RuntimeError(f"普健数据协同平台登录未返回 AccessToken：{response_data}")

        # 标记当前会话已登录。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录成功", self.username, "green"), self.ph.kv("鉴权", "AccessToken", "cyan")))

        # 返回登录摘要。
        return {"success": True, "account": self.username, "token_type": "AccessToken"}

    # 定义会话信息保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录会话摘要。

        :param output_dir: 会话信息输出目录。
        :type output_dir: str
        :return: 会话信息文件路径。
        :rtype: str
        """

        # 创建会话信息输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建会话信息文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 组装会话信息内容。
        cookie_data = {"api_root": self.api_root_url, "site_root": self.site_root_url, "access_token_present": bool(self.access_token), "refresh_token_present": bool(self.refresh_token)}

        # 打开会话信息文件。
        with open(cookie_path, "w", encoding="utf-8") as file_obj:

            # 写入会话信息内容。
            json.dump(cookie_data, file_obj, ensure_ascii=False, indent=2)

        # 打印会话信息保存日志。
        self.ph.success(self.ph.kv("会话信息已保存", self.ph.path(cookie_path), "green"))

        # 返回会话信息文件路径。
        return cookie_path

    # 定义平台查询方法。
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


    # 定义查询落地 Excel 方法。
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

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 拼接输出文件路径。
        output_path = os.path.join(save_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(data_type, rows, output_path)

        # 应用统一 Excel 样式。
        apply_standard_excel_style(output_path)

        # 打印 Excel 生成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path


    # 定义协议分页查询方法。
    def fetch_protocol_rows(self, data_type, start_date, end_date):

        """
        通过普健报表接口分页读取业务数据。

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

        # 缓存平台页面表头。
        self.cache_remote_columns(data_type, query_definition)

        # 初始化页码。
        page_number = 1

        # 初始化结果行容器。
        result_rows = []

        # 初始化接口总数。
        total_count = None

        # 持续分页直到接口没有更多数据。
        while True:

            # 构建当前页请求体。
            payload = self.build_query_payload(data_type, page_number, start_date, end_date)

            # 请求当前页数据。
            response_data = self.post_json(query_definition["endpoint"], payload)

            # 解析当前页数据和总数。
            page_rows, parsed_total = self.extract_rows_and_total(response_data)

            # 更新接口总数。
            total_count = parsed_total if parsed_total is not None else total_count

            # 转换当前页数据结构。
            transformed_rows = [self.transform_row(data_type, row_data) for row_data in page_rows]

            # 追加当前页数据。
            result_rows.extend(transformed_rows)

            # 判断当前页是否为空。
            if not page_rows:

                # 结束分页循环。
                break

            # 判断是否已达到接口总数。
            if total_count is not None and len(result_rows) >= int(total_count):

                # 结束分页循环。
                break

            # 判断当前页数量是否小于分页大小。
            if len(page_rows) < self.page_size:

                # 结束分页循环。
                break

            # 增加页码。
            page_number += 1

        # 校验业务日期范围。
        self.validate_date_range(data_type, result_rows, start_date, end_date)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type}查询完成", f"{len(result_rows)} 条", "green"), self.ph.kv("接口总数", "" if total_count is None else str(total_count), "cyan")))

        # 返回结果行列表。
        return result_rows


    # 定义查询定义解析方法。
    def resolve_query_definition(self, data_type):

        """
        解析数据类型对应的查询定义。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询定义。
        :rtype: dict
        """

        # 判断数据类型是否存在配置。
        if data_type not in CQPJYY_QUERY_DEFINITIONS:

            # 抛出未支持数据类型异常。
            raise NotImplementedError(f"普健数据协同平台暂未接入{data_type}")

        # 返回查询定义。
        return CQPJYY_QUERY_DEFINITIONS[data_type]

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建前端一致的账号密码登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 计算前端 js-md5 一致的密码摘要。
        password_digest = md5_hex(self.password)

        # 返回登录请求体。
        return {"account": self.username, "pwd": password_digest, "systemType": self.system_type, "loginType": "ACCOUNT"}

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, page_number, start_date, end_date):

        """
        构建报表分页查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param page_number: 页码。
        :type page_number: int
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询请求体。
        :rtype: dict
        """

        # 判断当前数据类型是否为购进流向。
        if data_type == "购进流向":

            # 返回采购报表请求体。
            return {"customerKeyWords": None, "productKeyWords": None, "keyWords": None, "billTypeCode": None, "pageSize": self.page_size, "page": page_number, "startEffectTimeAt": self.normalize_date_text(start_date), "endEffectTimeAt": self.normalize_date_text(end_date or start_date)}

        # 判断当前数据类型是否为配送流向。
        if data_type == "配送流向":

            # 返回销售报表请求体。
            return {"pageSize": self.page_size, "page": page_number, "queryVal": None, "makeNo": None, "customerVal": None, "startDate": self.normalize_date_text(start_date), "endDate": self.normalize_date_text(end_date or start_date)}

        # 返回库存报表请求体。
        return {"makeNo": None, "customerVal": None, "queryVal": None, "pageSize": self.page_size, "page": page_number, "startDate": None, "endDate": None}

    # 定义平台页面表头缓存方法。
    def cache_remote_columns(self, data_type, query_definition):

        """
        缓存平台页面字段配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_definition: 查询定义。
        :type query_definition: dict
        :return: None。
        :rtype: None
        """

        # 判断当前数据类型是否已有表头缓存。
        if data_type in self.remote_columns:

            # 返回空结果。
            return None

        # 捕获页面字段接口异常。
        try:

            # 请求页面字段配置接口。
            response_data = self.get_json(query_definition["column_endpoint"])

            # 读取字段配置数据。
            column_data = response_data.get("data") if isinstance(response_data.get("data"), list) else []

            # 写入页面表头缓存。
            self.remote_columns[data_type] = column_data

        # 处理页面字段接口异常。
        except Exception as error:

            # 写入空页面表头缓存。
            self.remote_columns[data_type] = []

            # 打印表头接口警告。
            self.ph.warning(f"{data_type}页面表头接口读取失败：{error}")

        # 返回空结果。
        return None

    # 定义接口数据解析方法。
    def extract_rows_and_total(self, response_data):

        """
        从接口响应中解析数据行与总数。

        :param response_data: 接口响应数据。
        :type response_data: dict
        :return: 数据行列表与总数。
        :rtype: tuple[list[dict], int | None]
        """

        # 读取数据节点。
        data = response_data.get("data")

        # 判断数据节点是否为分页字典。
        if isinstance(data, dict):

            # 读取分页行列表。
            rows = data.get("list") or []

            # 读取分页总数。
            total = data.get("total")

            # 返回分页行与总数。
            return rows if isinstance(rows, list) else [], total

        # 返回空列表与空总数。
        return [], None

    # 定义数据行转换方法。
    def transform_row(self, data_type, row_data):

        """
        将接口原始行转换为标准字段前置的输出行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param row_data: 接口原始行。
        :type row_data: dict
        :return: 输出行。
        :rtype: dict
        """

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 展平接口原始行。
        flat_row = self.flatten_row(row_data)

        # 初始化输出行。
        output_row = {}

        # 判断当前数据类型是否为库存。
        if data_type == "库存":

            # 写入库存日期字段。
            flat_row["库存日期"] = datetime.now().strftime("%Y-%m-%d")

        # 遍历标准字段定义。
        for header_name, source_keys in query_definition["standard_fields"]:

            # 写入标准字段值。
            output_row[header_name] = self.first_available_value(flat_row, source_keys)

        # 遍历原始展平字段。
        for field_name, field_value in flat_row.items():

            # 转换接口字段为中文显示标题。
            display_name = self.translate_header_name(data_type, field_name)

            # 初始化当前字段显示标题。
            unique_display_name = display_name

            # 为与标准字段重名的原始字段保留独立中文列。
            if unique_display_name in output_row:

                # 追加接口字段后缀并避免同名覆盖。
                unique_display_name = f"{display_name}（接口）"

                # 继续追加序号直到列名唯一。
                suffix_index = 2

                while unique_display_name in output_row:

                    # 构建带序号的中文列名。
                    unique_display_name = f"{display_name}（接口{suffix_index}）"

                    # 增加列名序号。
                    suffix_index += 1

            # 写入中文显示标题及其原始值。
            output_row[unique_display_name] = field_value

        # 返回输出行。
        return output_row

    # 定义接口字段显示标题转换方法。
    def translate_header_name(self, data_type, field_name):

        """
        将普健接口字段名转换为中文显示标题。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param field_name: 接口字段名或页面表头。
        :type field_name: str
        :return: 中文显示标题或原字段名。
        :rtype: str
        """

        # 标准化字段标题文本。
        normalized_name = str(field_name).strip()

        # 返回接口字段对应的中文标题。
        return CQPJYY_RAW_HEADER_ALIASES.get(normalized_name, normalized_name)

    # 定义首个可用字段读取方法。
    def first_available_value(self, row_data, source_keys):

        """
        从候选字段中读取首个有效值。

        :param row_data: 展平后的原始行。
        :type row_data: dict
        :param source_keys: 候选字段列表。
        :type source_keys: list[str]
        :return: 字段值。
        :rtype: object
        """

        # 遍历候选字段。
        for source_key in source_keys:

            # 判断候选字段是否存在且不为空。
            if row_data.get(source_key) not in (None, ""):

                # 返回当前候选字段值。
                return row_data.get(source_key)

        # 返回空文本。
        return ""

    # 定义字典展平方法。
    def flatten_row(self, value, prefix=""):

        """
        展平嵌套字典和列表字段。

        :param value: 原始值。
        :type value: dict | list | str | int | float | None
        :param prefix: 字段前缀。
        :type prefix: str
        :return: 展平后的字段字典。
        :rtype: dict
        """

        # 初始化展平结果。
        result = {}

        # 判断当前值是否为字典。
        if isinstance(value, dict):

            # 遍历字典字段。
            for key, child_value in value.items():

                # 构建子字段名称。
                child_key = f"{prefix}.{key}" if prefix else str(key)

                # 合并子字段展平结果。
                result.update(self.flatten_row(child_value, child_key))

            # 返回字典展平结果。
            return result

        # 判断当前值是否为列表。
        if isinstance(value, list):

            # 将列表按 JSON 文本保留。
            result[prefix] = json.dumps(value, ensure_ascii=False)

            # 返回列表字段结果。
            return result

        # 写入普通字段值。
        result[prefix] = "" if value is None else value

        # 返回普通字段结果。
        return result

    # 定义日期范围校验方法。
    def validate_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向业务日期是否落在查询区间内。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 判断当前数据类型是否不需要日期校验。
        if not query_definition.get("date_field"):

            # 返回空结果。
            return None

        # 判断结果行是否为空。
        if not rows:

            # 打印空结果提示。
            self.ph.warning(f"{data_type} 本次查询无数据，已保留标准表头和页面表头")

            # 返回空结果。
            return None

        # 读取业务日期字段名称。
        date_field = query_definition["date_field"]

        # 提取业务日期列表。
        row_dates = [str(row.get(date_field, ""))[:10] for row in rows if str(row.get(date_field, ""))[:10]]

        # 判断业务日期列表是否为空。
        if not row_dates:

            # 打印日期字段缺失提示。
            self.ph.warning(f"{data_type} 未解析到可校验的业务日期字段：{date_field}")

            # 返回空结果。
            return None

        # 计算最小业务日期。
        min_date = min(row_dates)

        # 计算最大业务日期。
        max_date = max(row_dates)

        # 判断业务日期是否早于开始日期。
        if start_date and min_date < start_date:

            # 抛出日期范围异常。
            raise RuntimeError(f"{data_type} 业务日期超出查询范围：{min_date} - {max_date}")

        # 判断业务日期是否晚于结束日期。
        if end_date and max_date > end_date:

            # 抛出日期范围异常。
            raise RuntimeError(f"{data_type} 业务日期超出查询范围：{min_date} - {max_date}")

        # 打印日期范围校验日志。
        self.ph.success(self.ph.join(self.ph.kv("日期范围", f"{min_date} - {max_date}", "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回空结果。
        return None

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, data_type, rows, target_path):

        """
        将查询结果写入 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param target_path: 目标文件路径。
        :type target_path: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 导入列号转换函数。
        from openpyxl.utils import get_column_letter

        # 构建 Excel 表头。
        headers = self.build_excel_headers(data_type, rows)

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type[:31]

        # 写入表头行。
        worksheet.append(headers)

        # 遍历查询结果行。
        for row_data in rows:

            # 按表头顺序写入当前行。
            worksheet.append([row_data.get(header, "") for header in headers])

        # 遍历表头设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

            # 计算当前列最大显示宽度。
            width = max([len(str(header_name))] + [len(str(row_data.get(header_name, ""))) for row_data in rows[:200]])

            # 设置当前列宽。
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(width + 2, 12), 45)

        # 判断目标文件是否已经存在。
        if os.path.exists(target_path):

            # 删除旧目标文件。
            os.remove(target_path)

        # 保存 Excel 文件。
        workbook.save(target_path)

        # 关闭 Excel 工作簿。
        workbook.close()

        # 返回空结果。
        return None

    # 定义 Excel 表头构建方法。
    def build_excel_headers(self, data_type, rows):

        """
        构建标准字段前置的 Excel 表头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :return: 表头列表。
        :rtype: list[str]
        """

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 初始化标准表头。
        headers = [header_name for header_name, _ in query_definition["standard_fields"]]

        # 初始化已存在表头集合。
        existing_headers = set(headers)

        # 遍历平台页面表头并统一转换为中文标题。
        for raw_header_name in self.extract_remote_header_names(data_type):

            # 转换当前页面字段标题。
            header_name = self.translate_header_name(data_type, raw_header_name)

            # 判断页面表头是否已经存在。
            if header_name in existing_headers:

                # 继续处理下一个表头。
                continue

            # 追加中文页面表头。
            headers.append(header_name)

            # 标记表头已经存在。
            existing_headers.add(header_name)

        # 遍历查询结果行中的动态中文字段。
        for row_data in rows:

            # 遍历当前行字段。
            for field_name in row_data.keys():

                # 转换当前字段标题。
                header_name = self.translate_header_name(data_type, field_name)

                # 判断字段是否已经存在。
                if header_name in existing_headers:

                    # 继续处理下一个字段。
                    continue

                # 追加动态字段。
                headers.append(header_name)

                # 标记字段已存在。
                existing_headers.add(header_name)

        # 返回表头列表。
        return headers

    # 定义页面表头名称提取方法。
    def extract_remote_header_names(self, data_type):

        """
        从平台页面字段配置中提取表头名称。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 页面表头名称列表。
        :rtype: list[str]
        """

        # 读取页面字段配置。
        column_rows = self.remote_columns.get(data_type, [])

        # 初始化页面表头名称列表。
        header_names = []

        # 遍历页面字段配置。
        for column_row in column_rows:

            # 判断字段配置是否为字典。
            if not isinstance(column_row, dict):

                # 继续处理下一项。
                continue

            # 读取页面字段名称。
            header_name = column_row.get("label") or column_row.get("columnName") or column_row.get("name") or column_row.get("title")

            # 判断页面字段名称是否为空。
            if not header_name:

                # 继续处理下一项。
                continue

            # 追加页面字段名称。
            header_names.append(str(header_name))

        # 返回页面表头名称列表。
        return header_names

    # 定义 JSON GET 请求方法。
    def get_json(self, endpoint):

        """
        发起 JSON GET 请求并解析响应。

        :param endpoint: 接口路径。
        :type endpoint: str
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 拼接完整接口地址。
        request_url = self.build_api_url(endpoint)

        # 构建请求头。
        headers = self.build_headers(token_required=True)

        # 构建 GET 请求对象。
        request = Request(request_url, headers=headers, method="GET")

        # 发送请求并解析 JSON。
        return self.open_json_request(request)

    # 定义 JSON POST 请求方法。
    def post_json(self, endpoint, payload, token_required=True):

        """
        发起 JSON POST 请求并解析响应。

        :param endpoint: 接口路径。
        :type endpoint: str
        :param payload: 请求体。
        :type payload: dict
        :param token_required: 是否携带登录令牌。
        :type token_required: bool
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 拼接完整接口地址。
        request_url = self.build_api_url(endpoint)

        # 序列化请求体。
        request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        # 构建请求头。
        headers = self.build_headers(token_required=token_required)

        # 构建 POST 请求对象。
        request = Request(request_url, data=request_body, headers=headers, method="POST")

        # 发送请求并解析 JSON。
        return self.open_json_request(request)

    # 定义请求发送方法。
    def open_json_request(self, request):

        """
        发送 urllib 请求并按 JSON 解析响应。

        :param request: urllib 请求对象。
        :type request: urllib.request.Request
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 捕获 HTTP 错误响应。
        try:

            # 发送协议请求。
            response = self.opener.open(request, timeout=30)

            # 读取响应文本。
            response_text = response.read().decode("utf-8", errors="replace")

        # 处理 HTTP 错误响应。
        except HTTPError as error:

            # 读取错误响应文本。
            response_text = error.read().decode("utf-8", errors="replace")

            # 抛出 HTTP 异常。
            raise RuntimeError(f"HTTP请求失败：{error.code} {error.reason} {response_text[:300]}") from error

        # 解析 JSON 响应。
        response_data = json.loads(response_text)

        # 判断业务状态是否为成功或登录态过期。
        if str(response_data.get("code")) == "401" and self.refresh_token:

            # 刷新访问令牌。
            self.refresh_access_token()

            # 覆盖请求头中的访问令牌。
            request.headers["Accesstoken"] = self.access_token

            # 重新发送原请求。
            response = self.opener.open(request, timeout=30)

            # 读取重试响应文本。
            response_text = response.read().decode("utf-8", errors="replace")

            # 解析重试 JSON 响应。
            response_data = json.loads(response_text)

        # 校验业务状态码。
        if str(response_data.get("code")) not in ("200", "0"):

            # 抛出业务异常。
            raise RuntimeError(f"普健数据协同平台接口返回异常：{response_data.get('msg') or response_data}")

        # 返回接口响应。
        return response_data

    # 定义访问令牌刷新方法。
    def refresh_access_token(self):

        """
        通过刷新令牌更新访问令牌。

        :return: None。
        :rtype: None
        """

        # 拼接刷新令牌接口地址。
        request_url = self.build_api_url(self.refresh_endpoint)

        # 序列化空请求体。
        request_body = json.dumps({}, ensure_ascii=False).encode("utf-8")

        # 构建刷新令牌请求头。
        headers = self.build_headers(token_required=False)

        # 写入刷新令牌请求头。
        headers["refreshToken"] = self.refresh_token

        # 构建刷新令牌请求对象。
        request = Request(request_url, data=request_body, headers=headers, method="POST")

        # 发送刷新令牌请求。
        response = self.opener.open(request, timeout=30)

        # 读取响应文本。
        response_text = response.read().decode("utf-8", errors="replace")

        # 解析响应 JSON。
        response_data = json.loads(response_text)

        # 校验刷新状态。
        if str(response_data.get("code")) != "200":

            # 抛出刷新失败异常。
            raise RuntimeError(f"普健数据协同平台刷新令牌失败：{response_data.get('msg') or response_data}")

        # 读取刷新响应数据。
        token_data = response_data.get("data") if isinstance(response_data.get("data"), dict) else {}

        # 更新访问令牌。
        self.access_token = token_data.get("accessToken", self.access_token)

        # 更新刷新令牌。
        self.refresh_token = token_data.get("refreshToken", self.refresh_token)

        # 返回空结果。
        return None

    # 定义请求头构建方法。
    def build_headers(self, token_required=True):

        """
        构建普健数据协同平台请求头。

        :param token_required: 是否携带登录令牌。
        :type token_required: bool
        :return: 请求头字典。
        :rtype: dict
        """

        # 初始化基础请求头。
        headers = {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Content-Type": "application/json;charset=UTF-8", "Origin": self.site_root_url, "Referer": f"{self.site_root_url}/", "User-Agent": self.user_agent(), "deviceType": "10"}

        # 判断是否需要访问令牌。
        if token_required:

            # 写入访问令牌请求头。
            headers["AccessToken"] = self.access_token

        # 返回请求头。
        return headers

    # 定义接口地址构建方法。
    def build_api_url(self, endpoint):

        """
        构建完整接口地址。

        :param endpoint: 接口路径。
        :type endpoint: str
        :return: 完整接口地址。
        :rtype: str
        """

        # 判断接口路径是否已经是完整地址。
        if endpoint.startswith("http://") or endpoint.startswith("https://"):

            # 返回完整地址。
            return endpoint

        # 返回根地址与接口路径拼接结果。
        return f"{self.api_root_url}/{endpoint.lstrip('/')}"

    # 定义日期文本规范化方法。
    def normalize_date_text(self, date_text):

        """
        规范化日期文本。

        :param date_text: 日期文本。
        :type date_text: str | None
        :return: 标准日期文本。
        :rtype: str
        """

        # 判断日期是否为空。
        if not date_text:

            # 返回当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 截取日期部分。
        return str(date_text)[:10]


    # 定义用户代理构建方法。
    def user_agent(self):

        """
        返回协议请求使用的浏览器 User-Agent。

        :return: User-Agent 文本。
        :rtype: str
        """

        # 返回稳定的桌面浏览器 User-Agent。
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
