# -*- coding: utf-8 -*-
"""
雨诺轻应用知流向协议适配器。

本模块负责雨诺轻应用的签名登录、菜单报表解析、同表类型拆分和本地 Excel 生成。
"""

# 导入 Base64 编解码模块。
import base64

# 导入日期时间处理模块。
from datetime import datetime

# 导入哈希摘要模块。
import hashlib

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间戳模块。
import time

# 导入三重 DES 兼容算法。
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES

# 导入密码算法后端。
from cryptography.hazmat.backends import default_backend

# 导入分组密码构造器。
from cryptography.hazmat.primitives.ciphers import Cipher

# 导入 ECB 分组模式。
from cryptography.hazmat.primitives.ciphers import modes

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议 HTTP 客户端。
from ddi_framework.http_client import ProtocolHttpClient

# 导入平台适配器基类。
from ddi_framework.platforms.base import BasePlatform

# 导入公共日志打印器。
from ddi_framework.print_handler import PrintHandler


# 定义接口原始类型到 DDI 数据类型的映射。
YNQY_TYPE_MAPPING = {"入库": "购进流向", "出库": "配送流向", "库存": "库存"}

# 定义 DDI 数据类型到接口原始类型的映射。
YNQY_REVERSE_TYPE_MAPPING = {value: key for key, value in YNQY_TYPE_MAPPING.items()}

# 定义标准字段及其原始字段候选项。
YNQY_STANDARD_FIELD_MAPPING = [
    ("标准数据类型", ["数据类型"]),
    ("标准原始类型", ["类型"]),
    ("标准业务日期", ["库单日期", "日期"]),
    ("标准商品编码", ["货号", "商品编码"]),
    ("标准商品名称", ["品名", "商品名称"]),
    ("标准商品规格", ["规格", "商品规格"]),
    ("标准生产企业", ["生产单位", "生产企业", "产地"]),
    ("标准批号", ["批号", "批次号"]),
    ("标准有效期", ["有效期"]),
    ("标准单位", ["单位"]),
    ("标准数量", []),
    ("标准供应商编码", ["供应商编码"]),
    ("标准客户编码", ["客户编码"]),
    ("标准往来单位名称", ["供应商及客户"]),
]


# 定义雨诺轻应用平台适配器。
class YnqyPlatform(BasePlatform):

    """
    雨诺轻应用知流向协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台适配器实例。
    :rtype: YnqyPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化雨诺轻应用协议会话和账号配置。

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

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 保存接口根地址。
        self.api_root_url = str(account.get("接口根地址", "http://58.144.199.103:8063/")).rstrip("/")

        # 保存前端页面根地址。
        self.site_root_url = str(account.get("登录页", "http://58.144.199.103:8064/")).rstrip("/")

        # 保存企业号。
        self.ent_id = str(account.get("企业号", "001"))

        # 保存签名企业编码。
        self.sign_corp_id = str(account.get("签名企业编码", "null"))

        # 保存登录账号。
        self.user_code = str(account.get("账号", ""))

        # 保存登录密码。
        self.password = str(account.get("密码", ""))

        # 保存报表名称匹配词。
        self.report_name = str(account.get("报表名称", "总部进销存"))

        # 保存报表标识兜底值。
        self.report_guid = str(account.get("报表标识", ""))

        # 保存单个协议请求的最大尝试次数。
        self.request_attempts = max(1, int(account.get("请求重试次数", 3)))

        # 初始化会话令牌。
        self.dc_token = ""

        # 初始化登录返回用户名。
        self.login_username = ""

        # 初始化报表表头元数据。
        self.format_info = []

        # 初始化当前查询行缓存。
        self._report_cache = {}

        # 初始化协议 HTTP 客户端。
        self.http_client = ProtocolHttpClient(self.api_root_url)

    # 定义平台登录方法。
    def login(self):

        """
        执行雨诺轻应用的配置读取和账号登录。

        :return: 登录响应数据。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("雨诺轻应用登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 请求中间层配置数据。
        facade_result = self._post_json("YDSW/GetFacadeInfo", {})

        # 校验中间层配置是否成功。
        self._ensure_success(facade_result, "中间层配置读取")

        # 读取中间层地址。
        facade_url = str(facade_result.get("FacadeUrl", ""))

        # 读取数据库编号。
        db_number = str(facade_result.get("DBNumber", ""))

        # 校验中间层必要字段。
        if not facade_url or not db_number:

            # 抛出中间层配置缺失异常。
            raise RuntimeError("雨诺轻应用中间层配置缺少 FacadeUrl 或 DBNumber")

        # 构建登录请求数据。
        login_payload = {"EntId": self.ent_id, "UserCode": self.user_code, "Password": self._encrypt_password(self.password), "FacadeUrl": facade_url, "DbNumber": db_number}

        # 请求账号登录接口。
        login_result = self._post_json("YDSW/loginin", login_payload)

        # 校验账号登录是否成功。
        self._ensure_success(login_result, "账号登录")

        # 保存会话令牌。
        self.dc_token = str(login_result.get("dctoken", ""))

        # 保存登录返回用户名。
        self.login_username = str(login_result.get("username", ""))

        # 校验会话令牌是否存在。
        if not self.dc_token:

            # 抛出会话令牌缺失异常。
            raise RuntimeError("雨诺轻应用登录成功但未返回 dctoken")

        # 记录登录结果摘要。
        self.ph.success(self.ph.join(self.ph.kv("登录账号", login_result.get("usercode", self.user_code), "cyan"), self.ph.kv("会话令牌", "已获取", "green")))

        # 返回登录响应数据。
        return login_result

    # 定义会话摘要保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前会话的非敏感摘要信息。

        :param output_dir: 会话信息输出目录。
        :type output_dir: str
        :return: 会话摘要文件路径。
        :rtype: str
        """

        # 创建会话摘要输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建会话摘要文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 组装会话摘要数据。
        cookie_data = {"api_root": self.api_root_url, "ent_id": self.ent_id, "user_code": self.user_code, "dctoken_present": bool(self.dc_token)}

        # 打开会话摘要文件。
        with open(cookie_path, "w", encoding="utf-8") as file_obj:

            # 写入会话摘要数据。
            json.dump(cookie_data, file_obj, ensure_ascii=False, indent=2)

        # 返回会话摘要文件路径。
        return cookie_path

    # 定义数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定 DDI 类型的原始字段完整数据。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准字段与原始字段合并后的数据行。
        :rtype: list[dict]
        """

        # 打印当前数据类型查询分隔线。
        self._print_query_section(data_type, start_date, end_date)

        # 查询同表全部原始数据。
        raw_rows = self._query_report_rows(start_date, end_date)

        # 筛选当前数据类型对应的原始类型数据。
        filtered_rows = self._filter_rows(data_type, raw_rows)

        # 校验筛选结果的业务日期范围。
        self._validate_date_range(data_type, filtered_rows, start_date, end_date)

        # 返回标准字段与原始字段合并后的数据行。
        return [self._build_output_row(data_type, raw_row) for raw_row in filtered_rows]

    # 定义导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定 DDI 类型并生成 Excel 文件。

        :param data_type: DDI 数据类型名称。
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

        # 复用查询落地 Excel 方法。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定 DDI 类型并将同表结果落地为独立 Excel。

        :param data_type: DDI 数据类型名称。
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

        # 查询指定数据类型的完整输出行。
        rows = self.query_flow(data_type, start_date=start_date, end_date=end_date)

        # 读取目标输出目录。
        save_dir = output_dir or "downloads"

        # 创建目标输出目录。
        os.makedirs(save_dir, exist_ok=True)

        # 构建标准输出文件名称。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 拼接 Excel 输出文件路径。
        output_path = os.path.join(save_dir, file_name)

        # 写入当前数据类型 Excel 文件。
        self._write_excel(data_type, rows, output_path)

        # 应用统一 Excel 样式。
        apply_standard_excel_style(output_path)

        # 记录 Excel 生成结果。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 输出文件路径。
        return output_path

    # 定义查询分隔线打印方法。
    def _print_query_section(self, data_type, start_date, end_date):

        """
        打印指定数据类型的查询阶段分隔线。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 输出包含日期范围的数据查询分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

    # 定义报表数据查询方法。
    def _query_report_rows(self, start_date, end_date):

        """
        按日期范围请求同表原始数据并缓存报表表头。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 接口返回的原始数据行。
        :rtype: list[dict]
        """

        # 确保当前协议会话已经登录。
        self._ensure_logged_in()

        # 构建日期范围缓存键。
        cache_key = f"{start_date or ''}|{end_date or ''}"

        # 判断当前日期范围是否已有缓存。
        if cache_key in self._report_cache:

            # 返回已缓存的原始数据行。
            return list(self._report_cache[cache_key])

        # 调用首页接口读取账号实际授权的报表标识。
        home_result = self._post_json("YDSW/HomePage", {"EntId": self.ent_id, "UserCode": self.user_code})

        # 校验首页接口是否成功。
        self._ensure_success(home_result, "菜单报表读取")

        # 从菜单数据中解析当前报表标识。
        report_guid = self._resolve_report_guid(home_result.get("data", []))

        # 校验当前账号是否拥有目标报表。
        if not report_guid:

            # 抛出目标报表缺失异常。
            raise RuntimeError(f"雨诺轻应用未找到报表：{self.report_name}")

        # 构建报表查询请求数据。
        report_payload = {"EntId": self.ent_id, "UserCode": self.user_code, "ReportGuid": report_guid, "PM": "", "BeginDate": start_date or "", "EndDate": end_date or "", "LSH": ""}

        # 请求报表数据接口。
        report_result = self._post_json("YDSW/ReportPage", report_payload)

        # 校验报表接口是否成功。
        self._ensure_success(report_result, "进销存报表查询")

        # 保存接口返回的表头元数据。
        self.format_info = list(report_result.get("FORMATINFO") or [])

        # 读取接口返回的数据集合。
        raw_rows = list(report_result.get("data") or [])

        # 缓存当前日期范围的数据集合。
        self._report_cache[cache_key] = list(raw_rows)

        # 统计接口返回的原始类型分布。
        type_summary = self._summarize_raw_types(raw_rows)

        # 记录报表查询结果摘要。
        self.ph.info(self.ph.join(self.ph.kv("报表标识", report_guid, "cyan"), self.ph.kv("同表总记录数", f"{len(raw_rows)} 条", "cyan"), self.ph.kv("类型分布", type_summary, "yellow")))

        # 返回接口原始数据行。
        return raw_rows

    # 定义菜单报表标识解析方法。
    def _resolve_report_guid(self, menu_groups):

        """
        从首页菜单配置中解析账号实际授权的报表标识。

        :param menu_groups: 首页菜单分组列表。
        :type menu_groups: list[dict]
        :return: 报表标识。
        :rtype: str
        """

        # 遍历首页菜单分组。
        for menu_group in menu_groups:

            # 遍历分组内报表明细。
            for report_item in menu_group.get("ReportDetail") or []:

                # 读取当前报表名称。
                report_name = str(report_item.get("NAME", ""))

                # 判断当前报表名称是否匹配配置名称。
                if report_name == self.report_name:

                    # 返回当前账号授权的报表标识。
                    return str(report_item.get("GUID", ""))

        # 返回配置中的报表标识兜底值。
        return self.report_guid

    # 定义数据类型筛选方法。
    def _filter_rows(self, data_type, raw_rows):

        """
        按用户指定映射筛选同表中的原始业务类型。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param raw_rows: 同表原始数据行。
        :type raw_rows: list[dict]
        :return: 当前数据类型对应的原始数据行。
        :rtype: list[dict]
        """

        # 校验当前数据类型是否支持。
        if data_type not in YNQY_REVERSE_TYPE_MAPPING:

            # 抛出不支持的数据类型异常。
            raise ValueError(f"雨诺轻应用不支持数据类型：{data_type}")

        # 读取目标原始类型名称。
        raw_type = YNQY_REVERSE_TYPE_MAPPING[data_type]

        # 初始化当前数据类型结果行集合。
        filtered_rows = []

        # 遍历同表原始数据行。
        for raw_row in raw_rows:

            # 读取并标准化当前行类型。
            current_type = self._normalize_text(raw_row.get("类型"))

            # 判断当前行是否属于目标原始类型。
            if current_type == raw_type:

                # 追加当前原始数据行。
                filtered_rows.append(dict(raw_row))

        # 记录当前类型拆分结果。
        self.ph.info(self.ph.join(self.ph.kv("原始类型", raw_type, "cyan"), self.ph.kv("拆分记录数", f"{len(filtered_rows)} 条", "green")))

        # 返回筛选后的原始数据行。
        return filtered_rows

    # 定义输出行构建方法。
    def _build_output_row(self, data_type, raw_row):

        """
        构建标准字段前置且保留全部原始字段的输出行。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param raw_row: 接口原始数据行。
        :type raw_row: dict
        :return: 输出数据行。
        :rtype: dict
        """

        # 初始化标准字段输出行。
        output_row = {}

        # 遍历标准字段映射配置。
        for output_field, raw_fields in YNQY_STANDARD_FIELD_MAPPING:

            # 判断当前字段是否为标准数据类型。
            if output_field == "标准数据类型":

                # 写入当前 DDI 数据类型。
                output_row[output_field] = data_type

                # 跳过当前字段的原始候选读取。
                continue

            # 判断当前字段是否为标准原始类型。
            if output_field == "标准原始类型":

                # 写入当前接口原始类型。
                output_row[output_field] = self._normalize_text(raw_row.get("类型"))

                # 跳过当前字段的原始候选读取。
                continue

            # 判断当前字段是否为标准数量。
            if output_field == "标准数量":

                # 写入当前数据类型对应的数量字段。
                output_row[output_field] = self._resolve_quantity(data_type, raw_row)

                # 跳过当前字段的原始候选读取。
                continue

            # 写入当前标准字段的首个非空原始值。
            output_row[output_field] = self._first_value(raw_row, raw_fields)

        # 遍历接口原始字段。
        for field_name, field_value in raw_row.items():

            # 写入全部接口原始字段。
            output_row[str(field_name)] = field_value

        # 返回标准字段与原始字段合并后的输出行。
        return output_row

    # 定义 Excel 写入方法。
    def _write_excel(self, data_type, rows, output_path):

        """
        写入标准字段前置并保留原始字段的 Excel 文件。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param rows: 输出数据行。
        :type rows: list[dict]
        :param output_path: Excel 输出路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿构造器。
        from openpyxl import Workbook

        # 导入 Excel 列标转换函数。
        from openpyxl.utils import get_column_letter

        # 构建当前 Excel 表头。
        headers = self._build_excel_headers(rows)

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type[:31]

        # 写入表头行。
        worksheet.append(headers)

        # 遍历当前输出数据行。
        for row_data in rows:

            # 按表头顺序写入当前数据行。
            worksheet.append([row_data.get(header, "") for header in headers])

        # 遍历表头设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

            # 计算当前列显示宽度。
            width = max([len(str(header_name))] + [len(str(row_data.get(header_name, ""))) for row_data in rows[:200]])

            # 设置当前列宽。
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(width + 2, 12), 45)

        # 判断目标文件是否已存在。
        if os.path.exists(output_path):

            # 删除旧目标文件。
            os.remove(output_path)

        # 保存 Excel 工作簿。
        workbook.save(output_path)

        # 关闭 Excel 工作簿。
        workbook.close()

    # 定义 Excel 表头构建方法。
    def _build_excel_headers(self, rows):

        """
        构建标准字段前置且包含全部接口原始字段的 Excel 表头。

        :param rows: 输出数据行。
        :type rows: list[dict]
        :return: Excel 表头列表。
        :rtype: list[str]
        """

        # 初始化标准字段表头。
        headers = [field_name for field_name, _ in YNQY_STANDARD_FIELD_MAPPING]

        # 初始化已存在表头集合。
        existing_headers = set(headers)

        # 遍历接口返回的表头元数据。
        for field_meta in self.format_info:

            # 读取接口表头名称。
            field_name = str(field_meta.get("TITLE", ""))

            # 判断当前接口表头是否有效且未存在。
            if field_name and field_name not in existing_headers:

                # 追加当前接口表头。
                headers.append(field_name)

                # 标记当前接口表头已存在。
                existing_headers.add(field_name)

        # 遍历所有输出数据行。
        for row_data in rows:

            # 遍历当前数据行字段。
            for field_name in row_data:

                # 判断当前字段是否尚未写入表头。
                if field_name not in existing_headers:

                    # 追加当前动态字段表头。
                    headers.append(field_name)

                    # 标记当前动态字段已存在。
                    existing_headers.add(field_name)

        # 返回完整 Excel 表头。
        return headers

    # 定义日期范围校验方法。
    def _validate_date_range(self, data_type, raw_rows, start_date, end_date):

        """
        校验拆分后数据行的库单日期是否落在请求范围内。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param raw_rows: 筛选后的原始数据行。
        :type raw_rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 初始化可解析日期集合。
        date_values = []

        # 遍历筛选后的原始数据行。
        for raw_row in raw_rows:

            # 读取当前行库单日期。
            date_text = self._normalize_text(raw_row.get("库单日期"))

            # 判断当前行日期是否为空。
            if not date_text:

                # 跳过当前空日期行。
                continue

            # 截取当前行日期前十位。
            date_text = date_text[:10]

            # 尝试解析当前行日期。
            try:

                # 写入可解析日期对象。
                date_values.append(datetime.strptime(date_text, "%Y-%m-%d").date())

            # 忽略无法解析的日期文本。
            except ValueError:

                # 进入下一条原始数据行。
                continue

        # 判断当前类型是否无可解析日期。
        if not date_values:

            # 记录当前类型无日期数据。
            self.ph.warning(self.ph.kv(f"{data_type}业务日期", "无可解析日期", "yellow"))

            # 结束当前日期校验。
            return

        # 读取数据最小业务日期。
        min_date = min(date_values)

        # 读取数据最大业务日期。
        max_date = max(date_values)

        # 解析请求开始日期。
        start_value = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None

        # 解析请求结束日期。
        end_value = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # 校验数据最小日期是否早于请求开始日期。
        if start_value and min_date < start_value:

            # 抛出查询日期范围异常。
            raise RuntimeError(f"{data_type}返回日期早于查询开始日期：{min_date} < {start_value}")

        # 校验数据最大日期是否晚于请求结束日期。
        if "库存" in data_type:

            # 记录库存快照的实际业务日期范围。
            self.ph.info(self.ph.join(self.ph.kv("库存快照日期最小值", min_date, "cyan"), self.ph.kv("库存快照日期最大值", max_date, "cyan")))

            # 结束库存快照日期校验。
            return

        # 校验数据最大日期是否晚于请求结束日期。
        if end_value and max_date > end_value:

            # 抛出查询日期范围异常。
            raise RuntimeError(f"{data_type}返回日期晚于查询结束日期：{max_date} > {end_value}")

        # 记录业务日期范围校验结果。
        self.ph.success(self.ph.join(self.ph.kv("业务日期最小值", min_date, "cyan"), self.ph.kv("业务日期最大值", max_date, "cyan")))

    # 定义登录状态校验方法。
    def _ensure_logged_in(self):

        """
        确保当前协议会话已经获得有效登录令牌。

        :return: None。
        :rtype: None
        """

        # 判断当前会话令牌是否为空。
        if not self.dc_token:

            # 执行账号登录流程。
            self.login()

    # 定义 JSON 请求方法。
    def _post_json(self, path, payload):

        """
        按前端签名规则发送雨诺轻应用 JSON 请求。

        :param path: 接口相对路径。
        :type path: str
        :param payload: 业务请求数据。
        :type payload: dict
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 构建当前请求的动态签名字段。
        signed_payload = self._build_sign_payload()

        # 追加当前业务请求字段。
        signed_payload.update(payload)

        # 追加当前会话令牌字段。
        signed_payload["DcToken"] = str(payload.get("DcToken", self.dc_token))

        # 初始化最后一次超时异常。
        last_timeout_error = None

        # 遍历当前请求的最大尝试次数。
        for attempt_index in range(1, self.request_attempts + 1):

            # 尝试发送当前 JSON POST 请求。
            try:

                # 发送 JSON POST 请求。
                result = self.http_client.post_json(self._build_url(path), signed_payload, self.site_root_url)

                # 解析并返回 JSON 响应数据。
                return self.http_client.decode_json(result)

            # 捕获网络超时异常。
            except TimeoutError as error:

                # 保存当前超时异常。
                last_timeout_error = error

                # 判断当前是否仍可进行重试。
                if attempt_index < self.request_attempts:

                    # 记录当前协议请求超时重试信息。
                    self.ph.warning(self.ph.join(self.ph.kv("协议请求超时", path, "yellow"), self.ph.kv("重试次数", f"{attempt_index}/{self.request_attempts - 1}", "cyan")))

                    # 等待短暂间隔后重试请求。
                    time.sleep(1)

        # 重新抛出最后一次超时异常。
        raise last_timeout_error

    # 定义动态签名构建方法。
    def _build_sign_payload(self):

        """
        按网页前端算法构建 TOKEN、RTIME 和 RSIGN。

        :return: 动态签名字段。
        :rtype: dict
        """

        # 构建前端签名原始企业文本。
        sign_source = f"CORPID={self.sign_corp_id}|@ModuleNo=undefined"

        # 构建前端替换规则编码的令牌正文。
        token_body = self._encode_frontend_base64(sign_source.encode("utf-8"))

        # 构建带协议前缀的会话令牌。
        token = f"@@{token_body}"

        # 构建 UTC 毫秒时间戳。
        rtime = f"UTC{int(time.time() * 1000)}"

        # 构建签名原始文本。
        sign_text = f"RTIME{rtime}TOKEN{token}"

        # 计算前端 MD5 原始字节摘要。
        sign_digest = hashlib.md5(sign_text.encode("utf-8")).digest()

        # 构建前端替换规则编码的签名值。
        rsign = self._encode_frontend_base64(sign_digest)

        # 返回动态签名字段。
        return {"TOKEN": token, "RTIME": rtime, "RSIGN": rsign}

    # 定义密码加密方法。
    def _encrypt_password(self, password):

        """
        按网页前端 DES-ECB-AnsiX923 规则加密登录密码。

        :param password: 明文登录密码。
        :type password: str
        :return: 十六进制密文。
        :rtype: str
        """

        # 将明文密码编码为字节数据。
        password_bytes = str(password).encode("utf-8")

        # 计算 AnsiX923 补齐长度。
        padding_length = 8 - len(password_bytes) % 8

        # 构建 AnsiX923 补齐后的密码字节。
        padded_password = password_bytes + (b"\x00" * (padding_length - 1)) + bytes([padding_length])

        # 构建与单 DES 等价的三重 DES 密钥。
        des_key = b"romensjm" * 3

        # 构建 ECB 加密器。
        cipher = Cipher(TripleDES(des_key), modes.ECB(), backend=default_backend())

        # 执行密码字节加密。
        encrypted_password = cipher.encryptor().update(padded_password)

        # 返回小写十六进制密文。
        return encrypted_password.hex()

    # 定义前端 Base64 编码方法。
    def _encode_frontend_base64(self, value):

        """
        按前端替换规则编码 Base64 文本。

        :param value: 需要编码的字节数据。
        :type value: bytes
        :return: 前端规则编码文本。
        :rtype: str
        """

        # 执行标准 Base64 编码。
        encoded_value = base64.b64encode(value).decode("ascii")

        # 按网页前端规则替换特殊字符。
        return encoded_value.replace("+", "_").replace("=", "-").replace("/", "|")

    # 定义成功响应校验方法。
    def _ensure_success(self, response_data, stage_name):

        """
        校验接口响应状态并在失败时抛出阶段化异常。

        :param response_data: 接口响应数据。
        :type response_data: dict
        :param stage_name: 当前协议阶段名称。
        :type stage_name: str
        :return: None。
        :rtype: None
        """

        # 读取接口响应状态码。
        response_code = str(response_data.get("code", ""))

        # 判断接口响应是否成功。
        if response_code == "200":

            # 结束当前成功校验。
            return

        # 读取接口响应提示文本。
        response_message = response_data.get("message") or response_data.get("msg") or "未知错误"

        # 抛出当前协议阶段异常。
        raise RuntimeError(f"雨诺轻应用{stage_name}失败：{response_message}")

    # 定义 URL 构建方法。
    def _build_url(self, path):

        """
        根据接口根地址构建完整请求地址。

        :param path: 接口相对路径。
        :type path: str
        :return: 完整接口地址。
        :rtype: str
        """

        # 返回拼接后的完整接口地址。
        return f"{self.api_root_url}/{str(path).lstrip('/')}"

    # 定义原始类型统计方法。
    def _summarize_raw_types(self, raw_rows):

        """
        统计同表原始类型的行数分布。

        :param raw_rows: 同表原始数据行。
        :type raw_rows: list[dict]
        :return: 原始类型分布文本。
        :rtype: str
        """

        # 初始化原始类型统计字典。
        summary = {}

        # 遍历同表原始数据行。
        for raw_row in raw_rows:

            # 读取并标准化当前行类型。
            raw_type = self._normalize_text(raw_row.get("类型")) or "空类型"

            # 累加当前原始类型记录数。
            summary[raw_type] = summary.get(raw_type, 0) + 1

        # 返回排序后的类型统计文本。
        return ", ".join(f"{raw_type}:{count}" for raw_type, count in sorted(summary.items()))

    # 定义首个有效字段读取方法。
    def _first_value(self, row_data, field_names):

        """
        从候选字段中读取首个非空原始值。

        :param row_data: 原始数据行。
        :type row_data: dict
        :param field_names: 候选字段名称列表。
        :type field_names: list[str]
        :return: 首个非空字段值。
        :rtype: object
        """

        # 遍历候选原始字段名称。
        for field_name in field_names:

            # 读取当前候选字段值。
            field_value = row_data.get(field_name, "")

            # 判断当前候选字段值是否有效。
            if self._normalize_text(field_value):

                # 返回当前有效字段值。
                return field_value

        # 返回空字段兜底值。
        return ""

    # 定义标准数量解析方法。
    def _resolve_quantity(self, data_type, raw_row):

        """
        根据 DDI 数据类型读取语义一致的原始数量字段。

        :param data_type: DDI 数据类型名称。
        :type data_type: str
        :param raw_row: 接口原始数据行。
        :type raw_row: dict
        :return: 标准数量字段值。
        :rtype: object
        """

        # 定义各 DDI 数据类型的数量字段优先级。
        quantity_fields = {"购进流向": ["入库数量"], "配送流向": ["销售数量"], "库存": ["库存数"]}

        # 读取当前数据类型的数量字段候选项。
        candidate_fields = quantity_fields.get(data_type, [])

        # 返回当前数据类型的首个有效数量字段值。
        return self._first_value(raw_row, candidate_fields)

    # 定义文本标准化方法。
    def _normalize_text(self, value):

        """
        统一清理类型和日期判断使用的文本空白字符。

        :param value: 原始字段值。
        :type value: object
        :return: 清理后的文本。
        :rtype: str
        """

        # 返回清理全角空格、换行和首尾空白后的文本。
        return str(value or "").replace("\u3000", " ").replace("\r", " ").replace("\n", " ").strip()
