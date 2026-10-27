# -*- coding: utf-8 -*-
"""
四川聚之家医药有限公司聚创供应商系统协议适配器。

本模块负责聚创供应商系统的账号登录、主体选择、流向卡分页查询、
原始字段保留、标准字段前置和 Excel 文件生成。
"""

# 导入 Base64 编码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入 Cookie 容器。
from http.cookiejar import CookieJar

# 导入 URL 错误类型。
from urllib.error import HTTPError

# 导入 URL 请求构建工具。
from urllib.request import HTTPCookieProcessor

# 导入 URL 请求构建工具。
from urllib.request import Request

# 导入 URL 请求打开器构建工具。
from urllib.request import build_opener

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义聚创供应商系统查询配置。
SCJZJ_QUERY_DEFINITIONS = {
    "购进流向": {
        "endpoint": "/api/supplier/flow-card/purchase/list",
        "date_field": "storageTime",
        "date_label": "入库日期",
        "standard_fields": [
            ("入库日期", "storageTime"),
            ("业务日期", "date"),
            ("配送公司", "enterprise"),
            ("商品编码", "goodsErpCode"),
            ("商品名称", "name"),
            ("商品规格", "specification"),
            ("单位", "unit"),
            ("生产厂家", "produce"),
            ("批号", "batchNum"),
            ("生产日期", "produceDate"),
            ("有效期", "validDate"),
            ("数量", "goodsNum"),
            ("单价", "price"),
            ("金额", "amount"),
            ("采购单号", "purchaseOrderNumber"),
            ("流向卡ID", "flowCardId"),
            ("渠道名称", "channel.name"),
        ],
    },
    "配送流向": {
        "endpoint": "/api/supplier/flow-card/sales/list",
        "date_field": "deliveryTime",
        "date_label": "出库日期",
        "standard_fields": [
            ("出库日期", "deliveryTime"),
            ("业务日期", "date"),
            ("销售单位名称", "enterprise"),
            ("客户名称", "displayUserName"),
            ("客户原始名称", "slaveUserName"),
            ("客户类别", "userType"),
            ("客户省份", "province"),
            ("客户城市", "city"),
            ("商品编码", "goodsErpCode"),
            ("商品名称", "name"),
            ("商品规格", "specification"),
            ("单位", "unit"),
            ("生产厂家", "produce"),
            ("批号", "batchNum"),
            ("生产日期", "produceDate"),
            ("有效期", "validDate"),
            ("数量", "goodsNum"),
            ("单价", "price"),
            ("金额", "amount"),
            ("销售单号", "salesOrderNumber"),
            ("配送单号", "salesDeliveryNumber"),
            ("流向卡ID", "flowCardId"),
            ("渠道名称", "channel.name"),
        ],
    },
    "库存": {
        "endpoint": "/api/supplier/flow-card/stock/list",
        "date_field": None,
        "date_label": "库存日期",
        "standard_fields": [
            ("商品编码", "goodsErpCode"),
            ("商品名称", "name"),
            ("商品规格", "specification"),
            ("单位", "unit"),
            ("生产厂家", "produce"),
            ("批号", "batchNum"),
            ("生产日期", "produceDate"),
            ("有效期", "validDate"),
            ("库存数量", "stockNum"),
            ("近效数量", "nearExpiryAmount"),
            ("滞销数量", "unsalableAmount"),
            ("配送公司", "enterprise"),
            ("部门管理员", "departmentAdminName"),
            ("流向卡ID", "flowCardId"),
            ("渠道名称", "channel.name"),
        ],
    },
}


# 定义四川聚之家医药有限公司平台适配器。
class ScjzjPlatform(BasePlatform):

    """
    四川聚之家医药有限公司聚创供应商系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台适配器实例。
    :rtype: ScjzjPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化聚创供应商系统协议适配器。

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

        # 保存页面根地址。
        self.site_root_url = account.get("登录页", "https://srm.tyaow.com/login").split("/login")[0].rstrip("/")

        # 保存接口根地址。
        self.api_root_url = account.get("接口根地址", "https://prod-srm-api.tyaow.com").rstrip("/")

        # 保存登录账号。
        self.username = account.get("账号", "")

        # 保存登录密码。
        self.password = account.get("密码", "")

        # 保存目标登录主体名称。
        self.target_supplier_name = account.get("登录主体", "广东健元药业有限公司")

        # 保存配置中的登录主体 ID。
        self.configured_supplier_id = account.get("登录主体ID")

        # 保存配置中的流向卡 ID。
        self.configured_flow_card_id = account.get("流向卡ID")

        # 保存分页大小。
        self.page_size = int(account.get("分页大小", 500))

        # 初始化 Cookie 容器。
        self.cookie_jar = CookieJar()

        # 初始化协议请求打开器。
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

        # 初始化登录令牌。
        self.token = ""

        # 初始化登录状态。
        self.logged_in = False

        # 初始化登录主体信息。
        self.supplier_info = {}

        # 初始化流向卡信息。
        self.flow_card_info = {}

    # 定义平台登录方法。
    def login(self):

        """
        登录聚创供应商系统并选择目标主体。

        :return: 登录结果。
        :rtype: dict
        """

        # 查询账号可用的登录主体列表。
        supplier_list = self.query_login_suppliers()

        # 解析目标登录主体信息。
        self.supplier_info = self.resolve_supplier_info(supplier_list)

        # 读取登录主体 ID。
        supplier_id = self.supplier_info.get("supplierId")

        # 生成前端一致的密码密文。
        encrypted_password = self.encode_password(self.password)

        # 构建登录请求体。
        payload = {"provider": "password", "phone": self.username, "pass_word": encrypted_password, "supplier_id": supplier_id}

        # 请求登录接口。
        response_data = self.post_json("/api/supplier/login_in", payload, token_required=False, referer=f"{self.site_root_url}/login")

        # 读取登录返回数据。
        login_data = response_data.get("data") if isinstance(response_data.get("data"), dict) else {}

        # 读取登录令牌。
        self.token = login_data.get("token", "")

        # 校验登录令牌是否存在。
        if not self.token:

            # 抛出登录令牌缺失异常。
            raise RuntimeError(f"聚创供应商系统登录失败：{response_data.get('msg') or response_data}")

        # 标记当前会话已登录。
        self.logged_in = True

        # 解析当前账号可用流向卡。
        self.flow_card_info = self.resolve_flow_card_info()

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("聚创供应商系统登录成功", self.target_supplier_name, "green"), self.ph.kv("流向卡", self.flow_card_info.get("code", ""), "cyan")))

        # 返回登录摘要信息。
        return {"success": True, "supplier": self.supplier_info, "flow_card": self.flow_card_info}

    # 定义会话信息保存方法。
    def save_cookie(self, output_dir):

        """
        保存聚创供应商系统当前登录会话信息。

        :param output_dir: 会话信息输出目录。
        :type output_dir: str
        :return: 会话信息文件路径。
        :rtype: str
        """

        # 创建会话信息输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建会话信息文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 组装当前会话信息。
        cookie_data = {"token": self.token, "authorization": f"Bearer {self.token}", "supplier": self.supplier_info, "flow_card": self.flow_card_info, "api_root": self.api_root_url, "site_root": self.site_root_url}

        # 写入会话信息文件。
        with open(cookie_path, "w", encoding="utf-8") as cookie_file:

            # 序列化会话信息。
            json.dump(cookie_data, cookie_file, ensure_ascii=False, indent=2)

        # 打印会话信息保存日志。
        self.ph.success(self.ph.kv("会话信息已保存", self.ph.path(cookie_path), "green"))

        # 返回会话信息文件路径。
        return cookie_path

    # 定义数据查询方法。
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

    # 定义业务导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出指定类型业务数据。

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

        # 复用查询落地 Excel 逻辑。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地方法。
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

    # 定义协议分页查询方法。
    def fetch_protocol_rows(self, data_type, start_date, end_date):

        """
        通过聚创供应商系统接口分页读取业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准字段与原始字段合并后的数据行。
        :rtype: list[dict]
        """

        # 确保当前会话已登录。
        self.ensure_logged_in()

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 读取流向卡 ID。
        flow_card_id = self.resolve_flow_card_id()

        # 初始化页码。
        page_number = 1

        # 初始化结果行容器。
        result_rows = []

        # 初始化总记录数。
        total_count = None

        # 持续分页直到接口没有更多数据。
        while True:

            # 构建当前页请求体。
            payload = self.build_query_payload(query_definition, flow_card_id, page_number, start_date, end_date)

            # 请求当前页数据。
            response_data = self.post_json(query_definition["endpoint"], payload)

            # 解析当前页数据和总数。
            page_rows, parsed_total = self.extract_rows_and_total(response_data)

            # 更新接口返回总数。
            total_count = parsed_total if parsed_total is not None else total_count

            # 转换当前页数据结构。
            transformed_rows = [self.transform_row(data_type, row_data) for row_data in page_rows]

            # 追加当前页数据。
            result_rows.extend(transformed_rows)

            # 判断当前页是否已经为空。
            if not page_rows:

                # 结束分页循环。
                break

            # 判断是否已经达到接口返回总数。
            if total_count is not None and len(result_rows) >= total_count:

                # 结束分页循环。
                break

            # 判断当前页数量是否小于分页大小。
            if len(page_rows) < self.page_size:

                # 结束分页循环。
                break

            # 增加页码。
            page_number += 1

        # 打印查询结果日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type}查询完成", f"{len(result_rows)} 条", "green"), self.ph.kv("接口总数", "" if total_count is None else str(total_count), "cyan")))

        # 返回结果行列表。
        return result_rows

    # 定义登录状态保障方法。
    def ensure_logged_in(self):

        """
        确保当前对象已经完成登录。

        :return: None。
        :rtype: None
        """

        # 判断当前是否已经登录。
        if not self.logged_in:

            # 执行登录流程。
            self.login()

        # 返回空结果。
        return None

    # 定义登录主体查询方法。
    def query_login_suppliers(self):

        """
        查询账号对应的登录主体列表。

        :return: 登录主体列表。
        :rtype: list[dict]
        """

        # 构建主体查询请求体。
        payload = {"provider": "mobile", "phone": self.username}

        # 请求主体查询接口。
        response_data = self.post_json("/api/supplier/query", payload, token_required=False, referer=f"{self.site_root_url}/login")

        # 读取主体列表。
        supplier_list = response_data.get("data") if isinstance(response_data.get("data"), list) else []

        # 校验主体列表是否存在。
        if not supplier_list:

            # 抛出主体缺失异常。
            raise RuntimeError(f"聚创供应商系统未返回登录主体：{response_data}")

        # 返回主体列表。
        return supplier_list

    # 定义登录主体解析方法。
    def resolve_supplier_info(self, supplier_list):

        """
        从登录主体列表中解析目标主体。

        :param supplier_list: 登录主体列表。
        :type supplier_list: list[dict]
        :return: 目标登录主体信息。
        :rtype: dict
        """

        # 遍历接口返回的主体记录。
        for item in supplier_list:

            # 读取内层主体对象。
            supplier = item.get("supplier") if isinstance(item.get("supplier"), dict) else {}

            # 读取主体名称。
            supplier_name = supplier.get("name", "")

            # 判断主体名称是否命中配置。
            if supplier_name == self.target_supplier_name:

                # 返回命中的主体记录。
                return item

        # 判断配置中是否存在主体 ID。
        if self.configured_supplier_id:

            # 遍历接口返回的主体记录。
            for item in supplier_list:

                # 判断主体 ID 是否命中配置。
                if str(item.get("supplierId")) == str(self.configured_supplier_id):

                    # 返回命中的主体记录。
                    return item

        # 抛出主体未命中异常。
        raise RuntimeError(f"未找到登录主体：{self.target_supplier_name}")

    # 定义流向卡解析方法。
    def resolve_flow_card_info(self):

        """
        查询并解析当前主体可用的流向卡。

        :return: 流向卡信息。
        :rtype: dict
        """

        # 构建流向卡列表请求体。
        payload = {"page": 1, "pageSize": 20, "__filter": {}, "__sort": {}}

        # 请求流向卡列表接口。
        response_data = self.post_json("/api/supplier/flow-card/list", payload)

        # 解析列表数据和总数。
        page_rows, _ = self.extract_rows_and_total(response_data)

        # 判断是否配置了流向卡 ID。
        if self.configured_flow_card_id:

            # 遍历接口返回的流向卡。
            for item in page_rows:

                # 判断当前流向卡是否命中配置 ID。
                if str(item.get("id")) == str(self.configured_flow_card_id):

                    # 返回命中的流向卡。
                    return item

        # 校验接口是否返回流向卡。
        if not page_rows:

            # 抛出流向卡缺失异常。
            raise RuntimeError(f"聚创供应商系统未返回流向卡：{response_data}")

        # 返回首个流向卡。
        return page_rows[0]

    # 定义流向卡 ID 解析方法。
    def resolve_flow_card_id(self):

        """
        解析业务查询使用的流向卡 ID。

        :return: 流向卡 ID。
        :rtype: int
        """

        # 优先读取登录后解析的流向卡 ID。
        flow_card_id = self.flow_card_info.get("id")

        # 使用配置中的流向卡 ID 兜底。
        flow_card_id = flow_card_id or self.configured_flow_card_id

        # 校验流向卡 ID 是否存在。
        if not flow_card_id:

            # 抛出流向卡 ID 缺失异常。
            raise RuntimeError("聚创供应商系统缺少流向卡 ID")

        # 返回整数型流向卡 ID。
        return int(flow_card_id)

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
        if data_type not in SCJZJ_QUERY_DEFINITIONS:

            # 抛出未支持数据类型异常。
            raise NotImplementedError(f"聚创供应商系统暂未接入{data_type}")

        # 返回查询定义。
        return SCJZJ_QUERY_DEFINITIONS[data_type]

    # 定义查询请求体构建方法。
    def build_query_payload(self, query_definition, flow_card_id, page_number, start_date, end_date):

        """
        构建分页查询请求体。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param flow_card_id: 流向卡 ID。
        :type flow_card_id: int
        :param page_number: 页码。
        :type page_number: int
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询请求体。
        :rtype: dict
        """

        # 初始化筛选条件。
        filter_data = {"flowCardId": flow_card_id}

        # 读取查询日期字段。
        date_field = query_definition.get("date_field")

        # 判断当前查询是否需要日期范围。
        if date_field:

            # 格式化开始时间。
            begin_time = self.format_begin_time(start_date)

            # 格式化结束时间。
            finish_time = self.format_finish_time(end_date or start_date)

            # 写入接口要求的日期范围表达式。
            filter_data[date_field] = ["between", [begin_time, finish_time]]

        # 返回分页查询请求体。
        return {"page": page_number, "pageSize": self.page_size, "__filter": filter_data, "__sort": {}}

    # 定义接口数据解析方法。
    def extract_rows_and_total(self, response_data):

        """
        从接口响应中解析数据行与总数。

        :param response_data: 接口响应数据。
        :type response_data: dict
        :return: 数据行列表与总数。
        :rtype: tuple[list[dict], int | None]
        """

        # 读取响应数据节点。
        data = response_data.get("data")

        # 判断数据节点是否为分页字典。
        if isinstance(data, dict):

            # 读取分页行列表。
            rows = data.get("list") or data.get("data") or []

            # 读取分页总数。
            total = data.get("total") or data.get("count") or data.get("totalCount")

            # 返回分页行和总数。
            return rows if isinstance(rows, list) else [], total

        # 判断数据节点是否为列表。
        if isinstance(data, list):

            # 返回列表数据和列表长度。
            return data, len(data)

        # 返回空列表和空总数。
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

        # 遍历标准字段定义。
        for header_name, source_key in query_definition["standard_fields"]:

            # 写入标准字段值。
            output_row[header_name] = flat_row.get(source_key, "")

        # 遍历原始展平字段。
        for field_name, field_value in flat_row.items():

            # 判断当前字段是否已经作为标准字段写入。
            if field_name not in output_row:

                # 写入原始字段。
                output_row[field_name] = field_value

        # 返回输出行。
        return output_row

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

        # 构建输出表头。
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

        # 遍历表头列设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

            # 计算当前列最大文本长度。
            width = max([len(str(header_name))] + [len(str(row_data.get(header_name, ""))) for row_data in rows[:200]])

            # 设置当前列宽。
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(width + 2, 12), 45)

        # 删除已存在的目标文件。
        if os.path.exists(target_path):

            # 移除旧文件。
            os.remove(target_path)

        # 保存工作簿。
        workbook.save(target_path)

        # 关闭工作簿。
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

        # 初始化表头列表。
        headers = [header_name for header_name, _ in query_definition["standard_fields"]]

        # 遍历全部结果行。
        for row_data in rows:

            # 遍历当前行字段。
            for field_name in row_data.keys():

                # 判断字段是否已经存在。
                if field_name not in headers:

                    # 追加原始字段。
                    headers.append(field_name)

        # 返回表头列表。
        return headers

    # 定义 JSON POST 请求方法。
    def post_json(self, endpoint, payload, token_required=True, referer=None):

        """
        发起 JSON POST 请求并解析响应。

        :param endpoint: 接口路径。
        :type endpoint: str
        :param payload: 请求体。
        :type payload: dict
        :param token_required: 是否携带登录令牌。
        :type token_required: bool
        :param referer: 来源页面地址。
        :type referer: str | None
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 拼接完整接口地址。
        request_url = self.build_api_url(endpoint)

        # 序列化请求体。
        request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        # 构建请求头。
        headers = self.build_headers(token_required=token_required, referer=referer)

        # 构建请求对象。
        request = Request(request_url, data=request_body, headers=headers, method="POST")

        # 捕获接口错误响应。
        try:

            # 发送 HTTP 请求。
            with self.opener.open(request, timeout=30) as response:

                # 读取响应文本。
                response_text = response.read().decode("utf-8", errors="replace")

        # 处理 HTTP 错误响应。
        except HTTPError as error:

            # 读取错误响应文本。
            response_text = error.read().decode("utf-8", errors="replace")

        # 解析 JSON 响应。
        response_data = json.loads(response_text)

        # 校验业务状态码。
        if response_data.get("code") not in (0, None):

            # 抛出业务异常。
            raise RuntimeError(f"聚创供应商系统接口返回异常：{response_data.get('msg') or response_data}")

        # 返回接口响应。
        return response_data

    # 定义请求头构建方法。
    def build_headers(self, token_required=True, referer=None):

        """
        构建聚创供应商系统请求头。

        :param token_required: 是否携带登录令牌。
        :type token_required: bool
        :param referer: 来源页面地址。
        :type referer: str | None
        :return: 请求头字典。
        :rtype: dict
        """

        # 初始化基础请求头。
        headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json;charset=UTF-8", "Origin": self.site_root_url, "Referer": referer or f"{self.site_root_url}/", "User-Agent": "Mozilla/5.0"}

        # 判断是否需要登录令牌。
        if token_required:

            # 写入 Bearer 令牌。
            headers["Authorization"] = f"Bearer {self.token}"

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

    # 定义密码编码方法。
    def encode_password(self, password):

        """
        按前端规则生成登录密码字段。

        :param password: 明文密码。
        :type password: str
        :return: Base64 编码后的密码。
        :rtype: str
        """

        # 将密码转换为 UTF-8 字节。
        password_bytes = str(password).encode("utf-8")

        # 返回 Base64 编码文本。
        return base64.b64encode(password_bytes).decode("ascii")

    # 定义开始时间格式化方法。
    def format_begin_time(self, date_text):

        """
        格式化接口查询开始时间。

        :param date_text: 日期文本。
        :type date_text: str | None
        :return: 开始时间文本。
        :rtype: str
        """

        # 规范化日期文本。
        normalized_date = self.normalize_date_text(date_text)

        # 返回开始时间。
        return f"{normalized_date} 00:00:00"

    # 定义结束时间格式化方法。
    def format_finish_time(self, date_text):

        """
        格式化接口查询结束时间。

        :param date_text: 日期文本。
        :type date_text: str | None
        :return: 结束时间文本。
        :rtype: str
        """

        # 规范化日期文本。
        normalized_date = self.normalize_date_text(date_text)

        # 返回结束时间。
        return f"{normalized_date} 23:59:59"

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

    # 定义输出日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        解析标准输出文件名使用的日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 输出文件名使用的日期。
        :rtype: str | None
        """

        # 判断当前数据类型是否为库存。
        if "库存" in data_type:

            # 返回导出当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向类使用的查询开始日期。
        return self.normalize_date_text(start_date) or self.normalize_date_text(end_date)
