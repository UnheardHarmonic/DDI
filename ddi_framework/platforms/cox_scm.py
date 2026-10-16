# -*- coding: utf-8 -*-
"""
能手软件 SCM 查询平台协议适配器。

本模块通过 COX OA 登录、动态数据源读取和报表分页接口查询入库、出库及库存数据，并将标准字段与接口原始字段写入本地 Excel。

:return: 模块提供能手软件 SCM 查询平台适配器。
:rtype: None
"""

# 导入 JSON 编解码模块。
import json

# 导入 SHA-256 摘要算法。
import hashlib

# 导入操作系统路径模块。
import os

# 导入毫秒时间戳模块。
import time

# 导入 XML 数据集解析模块。
import xml.etree.ElementTree as ElementTree

# 导入日期时间模块。
from datetime import datetime

# 导入 Excel 工作簿类。
from openpyxl import Workbook

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入 Excel 标准样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义数据类型与页面数据源名称、日期字段的映射。
DATA_TYPE_CONFIG = {
    "配送流向": {"source_name": "出库查询", "date_column": "ckdate", "query_column": "ckpx.ckdate"},
    "购进流向": {"source_name": "入库查询", "date_column": "rkdate", "query_column": "rkpx.rkdate"},
    "库存": {"source_name": "库存查询", "date_column": "", "query_column": ""},
}

# 定义各数据类型的标准字段映射。
STANDARD_FIELD_MAP = {
    "配送流向": [("单据编号", "ckid"), ("出库日期", "ckdate"), ("出库方式", "ckfs"), ("商品编号", "pxid"), ("货号", "pxno"), ("品名", "pxname"), ("剂型", "jxname"), ("规格", "pxgg"), ("单位", "unit"), ("数量", "qty"), ("生产厂家", "sccjname"), ("供应商", "vendorname"), ("门店", "posname")],
    "购进流向": [("单据编号", "rkid"), ("入库日期", "rkdate"), ("入库方式", "rkfs"), ("商品编号", "pxid"), ("货号", "pxno"), ("品名", "pxname"), ("剂型", "jxname"), ("规格", "pxgg"), ("单位", "unit"), ("数量", "qty"), ("生产厂家", "sccjname"), ("供应商", "vendorname"), ("门店", "posname")],
    "库存": [("商品编号", "pxid"), ("货号", "pxno"), ("品名", "pxname"), ("剂型", "jxname"), ("规格", "pxgg"), ("单位", "unit"), ("库存数量", "qty"), ("成本价", "costprice"), ("成本金额", "costje"), ("生产厂家", "sccjname"), ("供应商", "vendorname"), ("门店", "posname")],
}


# 定义能手软件 SCM 查询平台适配器。
class CoxScmPlatform(BasePlatform):

    """
    能手软件 SCM 查询平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 能手软件 SCM 查询平台适配器实例。
    :rtype: CoxScmPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化 COX OA 登录与 SCM 报表查询会话。

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

        # 读取 COX OA 服务根地址。
        self.login_base_url = str(account.get("登录接口根地址", "")).rstrip("/")

        # 读取报表服务根地址。
        self.report_base_url = str(account.get("报表接口根地址", "")).rstrip("/")

        # 读取平台系统名称。
        self.system_name = str(account.get("系统名称", "SCMSCCJ"))

        # 读取商业编号。
        self.customer_number = str(account.get("商业编号", ""))

        # 读取登录租户编号。
        self.tenant = str(account.get("租户", "0"))

        # 读取 COX OA 登录密码签名密钥。
        self.password_secret = str(account.get("登录密码密钥", "5B42C292068EAE007520F17A6E9FDD9B"))

        # 读取平台分页大小。
        self.page_size = int(account.get("分页大小", 500))

        # 初始化登录服务协议客户端。
        self.login_http = ProtocolHttpClient(self.login_base_url)

        # 初始化报表服务协议客户端。
        self.report_http = ProtocolHttpClient(self.report_base_url)

        # 初始化登录令牌。
        self.access_token = ""

    # 定义平台登录方法。
    def login(self):

        """
        提交 COX OA 登录请求并保存访问令牌。

        :return: 不含敏感字段的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("能手软件 SCM 登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 构建服务端要求的登录请求地址。
        login_url = f"{self.login_base_url}/api/coxoa/login?tenant={self.tenant}&gsno={self.customer_number}"

        # 生成本次登录请求的毫秒时间戳。
        request_timestamp = str(int(time.time() * 1000))

        # 构建前端传输格式的动态密码签名。
        password_value = self.encode_login_password(request_timestamp)

        # 构建登录接口要求的对象请求体。
        payload = {"userno": str(self.account.get("账号", "")), "pwd": password_value, "req": request_timestamp}

        # 捕获登录服务返回的 HTTP 失败响应。
        try:

            # 提交带系统标识的登录请求。
            response_data = self.request_json(self.login_http, login_url, payload, include_token=False)

        # 处理登录服务拒绝当前密码的响应。
        except RuntimeError as error:

            # 保存不含凭据的异常说明。
            error_text = str(error)

            # 判断 COX OA 登录服务是否以 HTTP 500 拒绝当前登录请求。
            if "HTTP 500" in error_text and "/api/coxoa/login" in error_text:

                # 抛出可直接定位账号维护动作的业务异常。
                raise RuntimeError(f"{self.company_name} 登录失败：COX OA 登录接口拒绝当前登录请求；本次服务端响应为密码不正确，请在账号抽屉核对并更新有效账号密码后重试。") from error

            # 保留其他协议失败的原始异常。
            raise

        # 从登录响应中提取访问令牌。
        self.access_token = self.find_token(response_data)

        # 校验登录响应包含可用令牌。
        if not self.access_token:

            # 抛出未获取到访问令牌异常。
            raise RuntimeError(f"{self.company_name} 登录响应未返回访问令牌")

        # 打印登录成功摘要。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("令牌", "已获取", "cyan")))

        # 返回脱敏登录结果。
        return {"登录状态": "成功", "令牌状态": "已获取"}

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存登录服务会话 Cookie。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存登录服务 Cookie。
        self.login_http.save_cookie_file(cookie_path)

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义原始数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型的全部原始业务记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 查询当前数据类型的完整报表数据。
        result = self.query_cox_report(data_type, start_date, end_date)

        # 返回未裁剪的原始记录。
        return result["rows"]

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型并生成标准字段加原始字段 Excel。

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

        # 查询当前数据类型的完整报表数据。
        result = self.query_cox_report(data_type, start_date, end_date)

        # 解析 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, result["start_date"], result["end_date"])

        # 拼接 Excel 输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入标准字段和全部原始字段。
        self.write_excel(result["rows"], result["headers"], data_type, output_path)

        # 打印 Excel 落地摘要。
        self.ph.success(self.ph.join(self.ph.kv("Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(result["headers"]), "cyan")))

        # 返回 Excel 输出路径。
        return output_path


    # 定义报表查询主流程。
    def query_cox_report(self, data_type, start_date, end_date):

        """
        读取动态数据源并分页查询指定业务报表。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始字段、原始记录及查询日期范围。
        :rtype: dict
        """

        # 校验数据类型已经配置。
        if data_type not in DATA_TYPE_CONFIG:

            # 抛出未接入数据类型异常。
            raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

        # 确保当前会话已完成登录。
        if not self.access_token:

            # 执行平台登录。
            self.login()

        # 解析查询日期范围。
        resolved_start_date, resolved_end_date = self.resolve_dates(data_type, start_date, end_date)

        # 打印数据类型查询分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", resolved_start_date, "cyan"), self.ph.kv("结束日期", resolved_end_date, "cyan")))

        # 读取当前页面的数据源和报表定义。
        source_data, report_data = self.resolve_report_definition(data_type)

        # 初始化原始记录列表。
        rows = []

        # 初始化原始字段列表。
        headers = []

        # 初始化第一页页码。
        page_index = 1

        # 初始化服务端总数。
        total_count = None

        # 持续读取全部报表分页数据。
        while total_count is None or len(rows) < total_count:

            # 构建当前页报表请求体。
            payload = self.build_report_payload(source_data, report_data, data_type, resolved_start_date, resolved_end_date, page_index)

            # 提交当前页报表查询请求。
            response_data = self.request_json(self.report_http, f"{self.report_base_url}/api/bizQuery/rptquery", payload, include_token=True)

            # 提取当前页原始记录。
            page_rows = self.find_rows(response_data)

            # 合并当前页字段顺序。
            headers = self.merge_headers(headers, page_rows)

            # 合并当前页记录。
            rows.extend(page_rows)

            # 解析服务端总记录数。
            total_count = self.find_total_count(response_data, total_count)

            # 打印当前页进度。
            self.ph.info(self.ph.join(self.ph.kv("分页", page_index, "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan"), self.ph.kv("累计", len(rows), "cyan")))

            # 判断当前页已无数据。
            if not page_rows:

                # 结束分页读取。
                break

            # 判断当前页已读取到服务端总记录数。
            if total_count is not None and len(rows) >= total_count:

                # 结束分页读取。
                break

            # 增加下一页页码。
            page_index += 1

        # 校验流向数据日期范围。
        self.validate_date_range(data_type, rows, resolved_start_date, resolved_end_date)

        # 返回完整查询结果。
        return {"headers": headers, "rows": rows, "start_date": resolved_start_date, "end_date": resolved_end_date}

    # 定义密码传输编码方法。
    def encode_login_password(self, request_timestamp):

        """
        按 COX OA 请求格式计算动态登录密码签名。

        :param request_timestamp: 本次登录请求的毫秒时间戳。
        :type request_timestamp: str

        :return: 服务端要求的 SHA-256 密码签名。
        :rtype: str
        """

        # 读取账号配置中的密码文本。
        password_text = str(self.account.get("密码", ""))

        # 拼接密码、请求时间戳和平台签名密钥。
        signature_source = f"{password_text}{request_timestamp}{self.password_secret}"

        # 返回小写十六进制 SHA-256 密码签名。
        return hashlib.sha256(signature_source.encode("utf-8")).hexdigest()

    # 定义动态报表定义读取方法。
    def resolve_report_definition(self, data_type):

        """
        读取页面数据源和报表定义。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 数据源定义和报表定义。
        :rtype: tuple[dict, dict]
        """

        # 读取当前数据类型配置。
        config = DATA_TYPE_CONFIG[data_type]

        # 构建数据源定义查询请求体。
        payload = {"dsId": "", "dsname": config["source_name"], "sysName": self.system_name, "apptype": self.system_name, "khNo": self.customer_number}

        # 提交数据源定义查询请求。
        response_data = self.request_json(self.report_http, f"{self.report_base_url}/api/DataSource/Get", payload, include_token=True)

        # 提取数据源定义对象。
        source_data = self.find_named_dict(response_data, "bs_datasource")

        # 提取报表定义对象。
        report_data = self.find_named_dict(response_data, "bs_reportconfig")

        # 校验数据源定义存在。
        if not source_data:

            # 抛出数据源定义缺失异常。
            raise RuntimeError(f"{self.company_name} {data_type} 未返回 bs_datasource 定义")

        # 返回动态数据源和可选报表定义。
        return source_data, report_data

    # 定义报表查询请求体构建方法。
    def build_report_payload(self, source_data, report_data, data_type, start_date, end_date, page_index):

        """
        构建业务报表分页查询请求体。

        :param source_data: 数据源定义。
        :type source_data: dict
        :param report_data: 报表定义。
        :type report_data: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_index: 当前页码。
        :type page_index: int
        :return: 报表分页查询请求体。
        :rtype: dict
        """

        # 读取当前数据类型配置。
        config = DATA_TYPE_CONFIG[data_type]

        # 初始化日期筛选参数列表。
        query_params = []

        # 判断当前数据类型需要日期过滤。
        if config["query_column"]:

            # 写入服务端日期范围筛选参数。
            query_params.append({"paramname": "", "paramtype": "日期范围", "colname": config["query_column"], "paramvlu": start_date, "paramvlu2": end_date})

        # 返回当前页报表查询请求体。
        return {"bs_datasource": source_data, "bs_reportconfig": report_data, "filter": "", "page": page_index, "page_size": self.page_size, "queryParam": query_params, "sort": ""}

    # 定义 JSON 请求发送方法。
    def request_json(self, client, url, payload, include_token):

        """
        发送带系统标识和可选访问令牌的 JSON 请求。

        :param client: 协议请求客户端。
        :type client: ProtocolHttpClient
        :param url: 请求地址。
        :type url: str
        :param payload: JSON 请求体。
        :type payload: dict | list
        :param include_token: 是否携带访问令牌。
        :type include_token: bool
        :return: JSON 响应对象。
        :rtype: dict | list
        """

        # 判断当前请求是否为 COX OA 登录请求。
        if not include_token and "/api/coxoa/login" in url:

            # 构建与 COX OA 前端一致的最小登录请求头。
            headers = {"Content-Type": "application/json", "Accept": "application/json", "apptype": self.system_name, "sysname": self.system_name, "Mver": "1.0", "User-Agent": client.user_agent()}

        # 为已登录的报表请求保留公共 JSON 会话头。
        else:

            # 构建服务端要求的会话请求头。
            headers = client.json_headers(self.login_base_url or self.report_base_url)

            # 写入应用类型请求头。
            headers["apptype"] = self.system_name

            # 写入系统名称请求头。
            headers["sysname"] = self.system_name

            # 写入客户端版本请求头。
            headers["Mver"] = "1.0"

        # 判断当前请求需要访问令牌。
        if include_token:

            # 写入 Bearer 访问令牌请求头。
            headers["Authorization"] = f"Bearer {self.access_token}"

        # 编码 JSON 请求体。
        request_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 判断报表查询需要保留服务端错误响应正文。
        allow_http_error = include_token and "/api/bizQuery/rptquery" in url

        # 发送 JSON 请求。
        response = client.request("POST", url, headers=headers, data=request_body, timeout=180, allow_http_error=allow_http_error)

        # 解码响应 JSON 文本。
        response_text = response.body.decode("utf-8", errors="replace")

        # 判断服务端返回 HTTP 失败状态。
        if response.status_code >= 400:

            # 提取 XML DataSet 错误响应中的服务端提示。
            dataset_message = self.extract_dataset_message(response_text)

            # 判断报表服务是否绑定到了其他商业环境。
            if "该JWT是属于公司" in dataset_message and "当前配置是公司" in dataset_message:

                # 抛出可定位平台服务端配置的业务异常。
                raise RuntimeError(f"{self.company_name} 报表查询失败：登录令牌所属商业与报表服务当前环境不一致。{dataset_message} 请联系能手软件将 {self.customer_number} 绑定到对应的报表查询环境后重试。")

            # 抛出保留服务端业务提示的协议异常。
            raise RuntimeError(f"{self.company_name} 协议请求失败：HTTP {response.status_code}，{dataset_message or response_text[:300]}")

        # 尝试解析 JSON 响应。
        try:

            # 返回 JSON 响应对象。
            return json.loads(response_text)

        # 捕获非 JSON 异常响应。
        except json.JSONDecodeError as error:

            # 解析 COX 服务返回的 XML DataSet 正常响应。
            dataset_data = self.parse_dataset_response(response_text)

            # 判断当前响应已成功转换为结构化数据。
            if dataset_data:

                # 返回转换后的 XML DataSet 内容。
                return dataset_data

            # 提取 XML DataSet 错误响应中的服务端提示。
            dataset_message = self.extract_dataset_message(response_text)

            # 判断报表服务是否绑定到了其他商业环境。
            if "该JWT是属于公司" in dataset_message and "当前配置是公司" in dataset_message:

                # 抛出可定位平台服务端配置的业务异常。
                raise RuntimeError(f"{self.company_name} 报表查询失败：登录令牌所属商业与报表服务当前环境不一致。{dataset_message} 请联系能手软件将 KH03311 绑定到对应的报表查询环境后重试。") from error

            # 抛出包含脱敏摘要的协议异常。
            raise RuntimeError(f"{self.company_name} 协议响应不是 JSON：HTTP {response.status_code}，{response_text[:300]}") from error

    # 定义 XML DataSet 正常响应解析方法。
    def parse_dataset_response(self, response_text):

        """
        将 COX 服务返回的 XML DataSet 转换为平台查询数据结构。

        :param response_text: 协议响应文本。
        :type response_text: str
        :return: 按数据表名称分组的结构化响应。
        :rtype: dict
        """

        # 尝试解析 XML DataSet 响应正文。
        try:

            # 构建 XML 根节点。
            root = ElementTree.fromstring(response_text)

        # 忽略非 XML 响应文本。
        except ElementTree.ParseError:

            # 返回空响应结构。
            return {}

        # 查找承载实际行数据的 diffgram 节点。
        diffgram = next((element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "diffgram"), None)

        # 判断响应未包含实际行数据节点。
        if diffgram is None:

            # 返回空响应结构。
            return {}

        # 读取 diffgram 中承载数据表的 DataSet 节点。
        dataset = next((element for element in list(diffgram) if element.tag.rsplit("}", 1)[-1] == "NewDataSet"), None)

        # 判断响应未包含实际数据表集合。
        if dataset is None:

            # 返回空响应结构。
            return {}

        # 初始化按表名收集的记录集合。
        table_rows = {}

        # 遍历 DataSet 中的实际数据表记录。
        for element in list(dataset):

            # 读取当前记录的字段节点。
            children = list(element)

            # 判断当前记录包含字段节点。
            if children:

                # 读取当前 XML 数据表名称。
                table_name = element.tag.rsplit("}", 1)[-1]

                # 构建当前记录的字段字典。
                record = {child.tag.rsplit("}", 1)[-1]: (child.text or "") for child in children}

                # 追加当前记录至对应数据表。
                table_rows.setdefault(table_name, []).append(record)

        # 初始化转换后的结构化响应。
        response_data = {}

        # 遍历各数据表记录集合。
        for table_name, records in table_rows.items():

            # 判断当前表为单条数据源定义。
            if table_name == "bs_datasource" and len(records) == 1:

                # 保留数据源定义的字典结构。
                response_data[table_name] = records[0]

            # 保留其他数据表的完整记录列表。
            else:

                # 保存当前数据表记录列表。
                response_data[table_name] = records

        # 返回 XML DataSet 转换结果。
        return response_data

    # 定义 XML DataSet 错误信息提取方法。
    def extract_dataset_message(self, response_text):

        """
        从 XML DataSet 响应中提取服务端业务提示。

        :param response_text: 协议响应文本。
        :type response_text: str
        :return: 服务端业务提示文本。
        :rtype: str
        """

        # 尝试解析 XML DataSet 响应正文。
        try:

            # 构建 XML 根节点。
            root = ElementTree.fromstring(response_text)

        # 忽略非 XML 响应文本。
        except ElementTree.ParseError:

            # 返回空提示文本。
            return ""

        # 遍历 XML 节点查找业务提示字段。
        for element in root.iter():

            # 判断当前节点为服务端提示字段。
            if element.tag.rsplit("}", 1)[-1] == "message" and element.text:

                # 返回首条非空服务端提示。
                return element.text.strip()

        # 返回未发现提示文本的结果。
        return ""

    # 定义令牌递归提取方法。
    def find_token(self, value):

        """
        从登录响应中递归提取访问令牌。

        :param value: 登录响应节点。
        :type value: dict | list | object
        :return: 访问令牌文本。
        :rtype: str
        """

        # 判断当前节点为字典。
        if isinstance(value, dict):

            # 遍历常见令牌字段名称。
            for key in ("access_token", "accessToken", "accesstoken", "token", "Token"):

                # 判断当前字段为非空字符串。
                if isinstance(value.get(key), str) and value.get(key):

                    # 返回当前令牌文本。
                    return value[key]

            # 遍历当前字典的子节点。
            for child_value in value.values():

                # 递归提取子节点令牌。
                token = self.find_token(child_value)

                # 判断子节点包含令牌。
                if token:

                    # 返回子节点令牌。
                    return token

        # 判断当前节点为列表。
        if isinstance(value, list):

            # 遍历当前列表的子节点。
            for child_value in value:

                # 递归提取子节点令牌。
                token = self.find_token(child_value)

                # 判断子节点包含令牌。
                if token:

                    # 返回子节点令牌。
                    return token

        # 返回未找到令牌结果。
        return ""

    # 定义命名字典提取方法。
    def find_named_dict(self, value, name):

        """
        从响应对象中递归提取指定名称的字典节点。

        :param value: 响应节点。
        :type value: dict | list | object
        :param name: 目标字段名称。
        :type name: str
        :return: 指定名称的字典节点。
        :rtype: dict
        """

        # 判断当前节点为字典。
        if isinstance(value, dict):

            # 判断目标字段为字典。
            if isinstance(value.get(name), dict):

                # 返回目标字段字典。
                return value[name]

            # 遍历当前字典子节点。
            for child_value in value.values():

                # 递归查找目标字典。
                result = self.find_named_dict(child_value, name)

                # 判断已找到目标字典。
                if result:

                    # 返回目标字典。
                    return result

        # 判断当前节点为列表。
        if isinstance(value, list):

            # 遍历列表子节点。
            for child_value in value:

                # 递归查找目标字典。
                result = self.find_named_dict(child_value, name)

                # 判断已找到目标字典。
                if result:

                    # 返回目标字典。
                    return result

        # 返回空字典。
        return {}

    # 定义记录列表提取方法。
    def find_rows(self, value):

        """
        从报表响应中提取最可能的原始明细记录列表。

        :param value: 报表响应对象。
        :type value: dict | list | object
        :return: 原始明细记录列表。
        :rtype: list[dict]
        """

        # 判断响应本身为字典列表。
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):

            # 返回当前字典列表。
            return value

        # 判断响应为字典。
        if isinstance(value, dict):

            # 遍历常见明细记录字段名称。
            for key in ("rows", "data", "list", "pageData", "result"):

                # 读取当前候选字段。
                candidate = value.get(key)

                # 判断候选字段为字典列表。
                if isinstance(candidate, list) and all(isinstance(item, dict) for item in candidate):

                    # 返回候选明细记录列表。
                    return candidate

            # 遍历当前字典的业务数据子节点。
            for key, child_value in value.items():

                # 判断当前节点属于报表元数据表。
                if key in {"output", "bs_datasource", "bs_reportconfig", "b_tableformatmx", "sequence", "schema"}:

                    # 跳过非业务明细节点。
                    continue

                # 递归提取子节点记录列表。
                rows = self.find_rows(child_value)

                # 判断子节点包含记录。
                if rows:

                    # 返回子节点记录列表。
                    return rows

        # 返回空记录列表。
        return []

    # 定义总记录数提取方法。
    def find_total_count(self, value, default_value):

        """
        从报表响应中递归提取总记录数。

        :param value: 报表响应节点。
        :type value: dict | list | object
        :param default_value: 默认总记录数。
        :type default_value: int | None
        :return: 服务端总记录数。
        :rtype: int | None
        """

        # 判断当前节点为字典。
        if isinstance(value, dict):

            # 遍历常见总数字段名称。
            for key in ("total", "totalCount", "recordCount", "count"):

                # 读取当前总数字段值。
                candidate = value.get(key)

                # 判断当前值为非布尔整数。
                if isinstance(candidate, int) and not isinstance(candidate, bool):

                    # 返回当前总记录数。
                    return candidate

            # 遍历当前字典子节点。
            for child_value in value.values():

                # 递归提取子节点总记录数。
                total_count = self.find_total_count(child_value, None)

                # 判断子节点包含总记录数。
                if total_count is not None:

                    # 返回子节点总记录数。
                    return total_count

        # 返回默认总记录数。
        return default_value

    # 定义字段合并方法。
    def merge_headers(self, headers, rows):

        """
        按接口出现顺序合并原始字段名称。

        :param headers: 已知字段名称列表。
        :type headers: list[str]
        :param rows: 当前页原始记录。
        :type rows: list[dict]
        :return: 合并后的原始字段名称列表。
        :rtype: list[str]
        """

        # 遍历当前页原始记录。
        for row in rows:

            # 遍历当前记录字段名称。
            for key in row.keys():

                # 判断字段尚未出现。
                if key not in headers:

                    # 追加当前原始字段名称。
                    headers.append(key)

        # 返回合并后的字段名称列表。
        return headers

    # 定义日期范围解析方法。
    def resolve_dates(self, data_type, start_date, end_date):

        """
        解析流向日期范围或库存导出日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 生成当天日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 判断当前数据类型为库存快照。
        if data_type == "库存":

            # 返回库存导出当天日期。
            return today_text, today_text

        # 解析流向开始日期。
        resolved_start_date = str(start_date or today_text)

        # 解析流向结束日期。
        resolved_end_date = str(end_date or resolved_start_date)

        # 校验日期范围顺序。
        if datetime.strptime(resolved_start_date, "%Y-%m-%d") > datetime.strptime(resolved_end_date, "%Y-%m-%d"):

            # 抛出无效日期范围异常。
            raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{resolved_start_date} > {resolved_end_date}")

        # 返回流向日期范围。
        return resolved_start_date, resolved_end_date

    # 定义流向业务日期校验方法。
    def validate_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向记录日期不超出请求范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param start_date: 请求开始日期。
        :type start_date: str
        :param end_date: 请求结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 读取当前数据类型业务日期字段。
        date_column = DATA_TYPE_CONFIG[data_type]["date_column"]

        # 判断当前数据类型不需要日期校验。
        if not date_column:

            # 结束库存快照日期校验。
            return

        # 初始化有效业务日期列表。
        business_dates = []

        # 遍历原始记录。
        for row in rows:

            # 读取当前记录日期文本。
            value = str(row.get(date_column, ""))[:10]

            # 判断当前日期文本长度有效。
            if len(value) == 10:

                # 追加当前业务日期文本。
                business_dates.append(value)

        # 判断当前不存在有效业务日期。
        if not business_dates:

            # 结束空结果日期校验。
            return

        # 判断最小业务日期早于请求开始日期。
        if min(business_dates) < start_date:

            # 抛出业务日期超范围异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期早于请求开始日期：{min(business_dates)} < {start_date}")

        # 判断最大业务日期晚于请求结束日期。
        if max(business_dates) > end_date:

            # 抛出业务日期超范围异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期晚于请求结束日期：{max(business_dates)} > {end_date}")

    # 定义 Excel 写入方法。
    def write_excel(self, rows, headers, data_type, output_path):

        """
        写入标准字段前置且完整保留原始字段的 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 原始字段名称列表。
        :type headers: list[str]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param output_path: Excel 输出路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 获取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type

        # 读取当前数据类型标准字段映射。
        standard_fields = STANDARD_FIELD_MAP[data_type]

        # 构建标准字段标题列表。
        standard_titles = [title for title, _ in standard_fields]

        # 构建未重复的原始字段标题列表。
        raw_headers = [header for header in headers if header not in {field for _, field in standard_fields}]

        # 写入表头行。
        worksheet.append(standard_titles + raw_headers)

        # 遍历原始记录。
        for row in rows:

            # 构建标准字段数据行。
            standard_values = [row.get(field, "") for _, field in standard_fields]

            # 构建原始字段数据行。
            raw_values = [row.get(field, "") for field in raw_headers]

            # 写入当前数据行。
            worksheet.append(standard_values + raw_values)

        # 应用项目标准 Excel 样式。
        apply_standard_excel_style(worksheet)

        # 保存 Excel 工作簿。
        workbook.save(output_path)
