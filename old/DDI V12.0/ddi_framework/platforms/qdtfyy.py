# -*- coding: utf-8 -*-
"""
青岛同方药业连锁有限公司 Forguncy 平台协议适配器。

本模块负责登录会话建立、Forguncy 元数据解析、查询命令请求、分页数据读取、行级补充数据读取和本地 Excel 文件生成。
"""

# 导入基础编码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入 URL 编码函数。
from urllib.parse import quote

# 导入日期时间模块。
from datetime import datetime, timedelta

# 导入 RSA 非对称填充配置。
from cryptography.hazmat.primitives.asymmetric import padding

# 导入 PEM 公钥加载函数。
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient


# 定义青岛同方平台查询模板。
QDTFYY_QUERY_DEFINITIONS = {
    "购进流向": {
        "页面名称": "总部入库流向",
        "表名": "总部入库",
        "视图名": "总部入库流向表格1",
        "列表位置": "总部入库流向",
        "查询命令": "d690296d16064c60bc1197d5da0bd127",
        "参数键": ["=M3", "=T3", "=B3"],
        "参数来源": "范围日期",
        "字段列表": ["日期", "商品编号", "商品名称", "规格", "生产厂家", "单位", "单价", "数量", "批号", "流水号", "入库单号", "供应商"],
        "列绑定": [
            ("日期", 2),
            ("商品编号", 6),
            ("商品名称", 10),
            ("规格", 20),
            ("生产厂家", 24),
            ("单位", 30),
            ("单价", 32),
            ("数量", 35),
            ("批号", 38),
            ("流水号", 41),
            ("入库单号", 46),
            ("供应商", 52),
        ],
        "总计列": ["数量"],
    },
    "配送流向": {
        "页面名称": "总部配送流向",
        "表名": "总部配送",
        "视图名": "总部配送流向表格1",
        "列表位置": "总部配送流向",
        "查询命令": "3cdfdcf0384d4cd6a842e784b5066418",
        "参数键": ["=M3", "=T3", "=B3"],
        "参数来源": "范围日期",
        "字段列表": ["门店编号", "门店名称", "区域", "商品编号", "商品名称", "规格", "生产厂家", "单位", "数量", "批号", "有效期", "流水号", "日期", "供应商"],
        "列绑定": [
            ("门店编号", 2),
            ("门店名称", 6),
            ("区域", 14),
            ("商品编号", 18),
            ("商品名称", 22),
            ("规格", 32),
            ("生产厂家", 36),
            ("单位", 44),
            ("数量", 46),
            ("批号", 49),
            ("有效期", 53),
            ("流水号", 57),
            ("日期", 64),
            ("供应商", 68),
        ],
        "总计列": ["数量"],
    },
    "纯销流向": {
        "页面名称": "门店销售流向",
        "表名": "门店销售",
        "视图名": "门店销售流向表格1",
        "列表位置": "门店销售流向",
        "查询命令": "792b495d71e948abbf948e2e913acfe9",
        "参数键": ["=M3", "=T3", "=B3"],
        "参数来源": "范围日期",
        "字段列表": ["门店编号", "门店名称", "区域", "商品编号", "商品名称", "规格", "生产厂家", "单位", "数量", "批号", "营业员", "日期", "供应商"],
        "列绑定": [
            ("门店编号", 2),
            ("门店名称", 6),
            ("区域", 16),
            ("商品编号", 22),
            ("商品名称", 26),
            ("规格", 36),
            ("生产厂家", 40),
            ("单位", 48),
            ("数量", 50),
            ("批号", 53),
            ("营业员", 57),
            ("日期", 60),
            ("供应商", 64),
        ],
        "总计列": ["数量"],
    },
    "总部库存": {
        "页面名称": "总部库存明细",
        "表名": "总部库存",
        "视图名": "总部库存明细表格1",
        "列表位置": "总部库存明细",
        "查询命令": "6c165995b303444f965630cec1f132a7",
        "参数键": ["=B8"],
        "参数来源": "页面默认",
        "字段列表": ["商品编号", "商品名称", "规格", "生产厂家", "单位", "数量", "批号", "有效期", "入库时间", "供应商"],
        "列绑定": [
            ("商品编号", 2),
            ("商品名称", 6),
            ("规格", 17),
            ("生产厂家", 21),
            ("单位", 29),
            ("数量", 31),
            ("批号", 34),
            ("有效期", 38),
            ("入库时间", 42),
            ("供应商", 46),
        ],
        "总计列": ["数量"],
    },
    "门店库存": {
        "页面名称": "门店库存明细",
        "表名": "门店库存",
        "视图名": "门店库存明细表格1",
        "列表位置": "门店库存明细",
        "查询命令": "7e14d9aeb884484ea4beeaa73dfd7925",
        "参数键": ["=B3"],
        "参数来源": "页面默认",
        "字段列表": ["门店编号", "门店名称", "区域", "商品编号", "商品名称", "规格", "生产厂家", "单位", "数量", "批号", "有效期", "供应商"],
        "列绑定": [
            ("门店编号", 2),
            ("门店名称", 6),
            ("区域", 16),
            ("商品编号", 22),
            ("商品名称", 26),
            ("规格", 36),
            ("生产厂家", 40),
            ("单位", 48),
            ("数量", 50),
            ("批号", 53),
            ("有效期", 57),
            ("供应商", 61),
        ],
        "总计列": ["数量"],
    },
}


# 定义青岛同方药业连锁有限公司平台适配器。
class QdtfyyPlatform(BasePlatform):

    """
    青岛同方药业连锁有限公司 Forguncy 平台适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 青岛同方药业连锁有限公司平台适配器实例。
    :rtype: QdtfyyPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化青岛同方药业连锁有限公司 Forguncy 平台适配器。

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

        # 保存接口根地址。
        self.base_url = account.get("接口根地址", "http://erp.qingdaotfyy.com:8070/SRM").rstrip("/")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.base_url}/")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化 RSA 公钥标识。
        self.rsa_key_id = ""

        # 初始化 RSA 公钥文本。
        self.rsa_public_key = ""

        # 初始化登录状态。
        self.logged_in = False

        # 初始化登录结果。
        self.login_result = {}

    # 定义平台登录方法。
    def login(self):

        """
        执行青岛同方药业连锁有限公司平台登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("青岛同方药业连锁有限公司登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.join(self.ph.kv("访问登录页", self.login_page_url, "cyan"), self.ph.kv("账号", self.get_login_name(), "cyan")))

        # 请求登录页以建立会话 Cookie。
        self.http.get(self.login_page_url, referer=self.login_page_url)

        # 获取 RSA 公钥信息。
        rsa_info = self.fetch_rsa_public_key()

        # 构建登录请求体。
        payload = self.build_login_payload(rsa_info)

        # 提交登录请求。
        result = self.http.post_json(self.build_api_url("Account/Login"), payload, self.login_page_url)

        # 解析登录响应。
        response_data = self.http.decode_json(result)

        # 读取登录结果标记。
        login_result = bool(response_data.get("Result"))

        # 判断登录是否失败。
        if not login_result:

            # 读取失败消息。
            error_message = response_data.get("Message") or response_data

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{error_message}")

        # 保存登录结果。
        self.login_result = response_data

        # 标记登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("正式登录成功", "Forguncy RSA 登录通过", "green"), self.ph.kv("Cookie数", len(list(self.http.cookie_jar)), "cyan")))

        # 返回登录结果。
        return response_data

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存协议会话 Cookie。

        :param output_dir: Cookie 输出目录。
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

    # 定义平台导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出指定类型流向数据并生成 Excel。

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

        # 返回查询落地文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义平台查询方法。
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

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, start_date, end_date)

        # 返回协议查询结果。
        return self.fetch_protocol_rows(data_type, start_date, end_date)

    # 定义查询落地方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型数据并生成 Excel 文件。

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
        使用 Forguncy 协议查询数据行。

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

        # 构建请求载荷。
        payload = self.build_query_payload(query_definition, start_date, end_date)

        # 打印主表分页查询日志。
        self.ph.info(self.ph.join(self.ph.kv("提交协议查询", query_definition["页面名称"], "cyan"), self.ph.kv("端点", "/Home/GetTableDataWithOffset", "yellow")))

        # 提交主表分页查询请求。
        primary_result = self.http.post_json(self.build_api_url("Home/GetTableDataWithOffset"), payload, self.build_page_url(query_definition["页面名称"]))

        # 解析主表查询结果行。
        primary_rows = self.parse_query_result(data_type, primary_result.body)

        # 初始化行级补充结果。
        supplemental_rows = []

        # 判断当前查询是否需要行级补充数据。
        if query_definition.get("补充行数据", True):

            # 打印行级补充查询日志。
            self.ph.info(self.ph.join(self.ph.kv("提交行级补充查询", query_definition["页面名称"], "cyan"), self.ph.kv("端点", "/Home/GetTableRowData", "yellow")))

            try:

                # 提交行级补充查询请求。
                supplemental_result = self.http.post_json(self.build_api_url("Home/GetTableRowData"), payload, self.build_page_url(query_definition["页面名称"]))

                # 解析行级补充查询结果行。
                supplemental_rows = self.parse_query_result(data_type, supplemental_result.body)

            except Exception as error:

                # 记录行级补充查询异常。
                self.ph.warning(self.ph.join(self.ph.kv("行级补充查询失败", query_definition["页面名称"], "yellow"), self.ph.kv("原因", str(error), "yellow")))

        # 合并主表查询结果和行级补充结果。
        rows = self.merge_query_rows(query_definition, primary_rows, supplemental_rows)

        # 打印协议解析日志。
        self.ph.success(self.ph.join(self.ph.kv("协议查询完成", data_type, "green"), self.ph.kv("记录数", len(rows), "cyan")))

        # 返回查询结果行。
        return rows

    # 定义登录 RSA 公钥获取方法。
    def fetch_rsa_public_key(self):

        """
        获取登录 RSA 公钥。

        :return: RSA 信息字典。
        :rtype: dict
        """

        # 构建 RSA 接口地址。
        request_url = self.build_api_url("Account/GetRSAPublicKey")

        # 请求 RSA 接口。
        result = self.http.post_json(request_url, {}, self.login_page_url)

        # 解析 RSA 接口响应。
        response_data = self.http.decode_json(result)

        # 校验 RSA 信息结构。
        if not response_data.get("Result"):

            # 抛出 RSA 公钥缺失异常。
            raise RuntimeError(f"{self.company_name} 登录失败：RSA 公钥缺失")

        # 保存 RSA 标识。
        self.rsa_key_id = response_data["Result"].get("Id", "")

        # 保存 RSA 公钥文本。
        self.rsa_public_key = response_data["Result"].get("Value", "")

        # 返回 RSA 信息。
        return response_data["Result"]

    # 定义登录请求体构建方法。
    def build_login_payload(self, rsa_info):

        """
        构建 Forguncy 登录请求体。

        :param rsa_info: RSA 信息字典。
        :type rsa_info: dict
        :return: 登录请求体。
        :rtype: dict
        """

        # 加密登录密码。
        encrypted_password = self.encrypt_rsa_value(self.get_login_password(), rsa_info.get("Value", ""))

        # 返回登录请求体。
        return {
            "userName": self.get_login_name(),
            "password": encrypted_password,
            "rememberMe": False,
            "keyId": rsa_info.get("Id", ""),
            "deviceInfo": self.build_device_info(),
        }

    # 定义登录账号读取方法。
    def get_login_name(self):

        """
        读取平台登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回账号配置中的登录账号。
        return str(self.account.get("账号", "")).strip()

    # 定义登录密码读取方法。
    def get_login_password(self):

        """
        读取平台登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回账号配置中的登录密码。
        return str(self.account.get("密码", "")).strip()

    # 定义 RSA 加密方法。
    def encrypt_rsa_value(self, value, public_key_text):

        """
        使用平台 RSA 公钥加密登录字段。

        :param value: 明文字段值。
        :type value: str
        :param public_key_text: 平台返回的公钥文本。
        :type public_key_text: str
        :return: Base64 密文。
        :rtype: str
        """

        # 规范化公钥文本。
        key_text = self.normalize_public_key(public_key_text)

        # 加载 RSA 公钥对象。
        public_key = load_pem_public_key(key_text.encode("ascii"))

        # 执行 RSA PKCS#1 v1.5 加密。
        cipher_bytes = public_key.encrypt(str(value).encode("utf-8"), padding.PKCS1v15())

        # 返回 Base64 密文。
        return base64.b64encode(cipher_bytes).decode("ascii")

    # 定义公钥规范化方法。
    def normalize_public_key(self, public_key_text):

        """
        规范化平台返回的 RSA 公钥文本。

        :param public_key_text: 平台返回的公钥文本。
        :type public_key_text: str
        :return: PEM 格式公钥文本。
        :rtype: str
        """

        # 清理公钥文本两端空白。
        key_text = str(public_key_text).strip()

        # 判断公钥是否已经是 PEM 格式。
        if "BEGIN PUBLIC KEY" in key_text:

            # 返回已有 PEM 公钥。
            return key_text

        # 返回补齐边界后的 PEM 公钥。
        return f"-----BEGIN PUBLIC KEY-----\n{key_text}\n-----END PUBLIC KEY-----\n"

    # 定义浏览器设备信息构建方法。
    def build_device_info(self):

        """
        构建登录设备信息。

        :return: 设备信息字符串。
        :rtype: str
        """

        # 返回浏览器设备信息。
        return self.account.get("deviceInfo", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0")

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
        if data_type not in QDTFYY_QUERY_DEFINITIONS:

            # 抛出数据类型异常。
            raise ValueError(f"青岛同方药业连锁有限公司平台不支持数据类型：{data_type}")

        # 返回查询定义。
        return QDTFYY_QUERY_DEFINITIONS[data_type]

    # 定义页面地址构建方法。
    def build_page_url(self, page_name):

        """
        构建 Forguncy 页面地址。

        :param page_name: 页面名称。
        :type page_name: str
        :return: 页面地址。
        :rtype: str
        """

        # 返回统一业务首页地址。
        return f"{self.base_url}/Home/Index"

    # 定义元数据地址构建方法。
    def build_metadata_url(self, page_name):

        """
        构建 Forguncy 页面元数据地址。

        :param page_name: 页面名称。
        :type page_name: str
        :return: 元数据地址。
        :rtype: str
        """

        # 返回元数据地址。
        return f"{self.base_url}/Home/GetMetadata2?pageName={quote(page_name)}&isMobile=false&v=577094912"

    # 定义查询载荷构建方法。
    def build_query_payload(self, query_definition, start_date, end_date):

        """
        构建 Forguncy 分页查询载荷。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 协议查询载荷。
        :rtype: dict
        """

        # 读取列绑定信息。
        binding_infos = [{"TableName": query_definition["表名"], "ColumnName": column_name} for column_name, _ in query_definition["列绑定"]]

        # 读取总计绑定信息。
        total_row_binding_infos = []
        for column_name in query_definition.get("总计列", []):

            # 追加汇总列绑定。
            total_row_binding_infos.append({"TableName": query_definition["表名"], "ColumnName": column_name, "IsAggregated": True, "AggregateFunction": 2})

        # 读取查询参数字典。
        param_list = self.build_query_param_list(query_definition, start_date, end_date)

        # 返回分页查询载荷。
        return {
            "bindingInfos": binding_infos,
            "currentRowInfo": {
                "currentTable": query_definition["表名"],
                "viewname": query_definition["视图名"],
                "listviewLocation": query_definition["列表位置"],
            },
            "demandRowCount": 0,
            "currentDataLength": 0,
            "needRowVersion": True,
            "queryCommandInfo": {"id": query_definition["查询命令"], "paramList": param_list},
            "editorDataInfos": None,
            "sortCommandID": None,
            "orderByInfo": None,
            "offsetConditionInfo": {"targetPage": 1, "pageLimitRowCount": 0},
            "columnFilterQueries": [],
            "totalRowBindingInfos": total_row_binding_infos,
        }

    # 定义查询参数构建方法。
    def build_query_param_list(self, query_definition, start_date, end_date):

        """
        构建 Forguncy 查询命令参数。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询参数字典。
        :rtype: dict
        """

        # 初始化查询参数字典。
        param_list = {}

        # 写入日期范围参数。
        if query_definition["参数来源"] == "范围日期":

            # 写入开始日期序列值。
            param_list[query_definition["参数键"][0]] = self.to_oa_date_serial(start_date)

            # 写入结束日期序列值。
            param_list[query_definition["参数键"][1]] = self.to_oa_date_serial(end_date)

            # 写入检索关键字空值。
            param_list[query_definition["参数键"][2]] = None

        # 写入单日期参数。
        if query_definition["参数来源"] == "单日期":

            # 写入库存查询日期序列值。
            param_list[query_definition["参数键"][0]] = self.to_oa_date_serial(end_date or start_date)

        # 写入页面默认参数。
        if query_definition["参数来源"] == "页面默认":

            # 遍历默认参数键。
            for parameter_key in query_definition["参数键"]:

                # 写入默认空参数值。
                param_list[parameter_key] = None

        # 返回查询参数字典。
        return param_list

    # 定义协议查询结果解析方法。
    def parse_query_result(self, data_type, response_body):

        """
        解析 Forguncy 分页查询响应。

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
        raw_rows = self.extract_response_rows(response_data)

        # 初始化结果行列表。
        rows = []

        # 遍历原始数据行。
        for raw_row in raw_rows:

            # 追加标准字段行。
            rows.append(self.convert_raw_row(query_definition, raw_row))

        # 返回标准数据行。
        return rows

    # 定义响应数据提取方法。
    def extract_response_rows(self, response_data):

        """
        提取 Forguncy 响应中的原始数据行。

        :param response_data: JSON 响应数据。
        :type response_data: dict
        :return: 原始数据行列表。
        :rtype: list[dict]
        """

        # 初始化候选数据容器。
        containers = []

        # 判断响应顶层是否为字典。
        if isinstance(response_data, dict):

            # 追加顶层响应数据。
            containers.append(response_data)

        # 判断响应是否包含 Result 字段。
        if isinstance(response_data, dict) and isinstance(response_data.get("Result"), dict):

            # 追加 Result 子对象。
            containers.insert(0, response_data["Result"])

        # 遍历候选容器。
        for container in containers:

            # 读取 table 子对象。
            table_data = container.get("table")

            # 判断 table 子对象是否为字典。
            if isinstance(table_data, dict):

                # 遍历常见行数组字段。
                for key_name in ("Data", "Rows", "RowData"):

                    # 读取当前候选行数组。
                    rows = table_data.get(key_name)

                    # 判断候选行数组是否有效。
                    if isinstance(rows, list) and rows:

                        # 返回命中的原始数据行。
                        return rows

            # 遍历顶层常见行数组字段。
            for key_name in ("Data", "Rows", "RowData"):

                # 读取当前候选行数组。
                rows = container.get(key_name)

                # 判断候选行数组是否有效。
                if isinstance(rows, list) and rows:

                    # 返回命中的原始数据行。
                    return rows

        # 返回空行列表。
        return []

    # 定义查询结果合并方法。
    def merge_query_rows(self, query_definition, primary_rows, supplemental_rows):

        """
        合并主表查询结果和行级补充结果。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param primary_rows: 主表查询结果行。
        :type primary_rows: list[dict]
        :param supplemental_rows: 行级补充结果行。
        :type supplemental_rows: list[dict]
        :return: 合并后的结果行。
        :rtype: list[dict]
        """

        # 判断补充结果是否为空。
        if not supplemental_rows:

            # 直接返回主表结果。
            return primary_rows

        # 初始化合并结果。
        merged_rows = []

        # 初始化行签名索引。
        signature_index = {}

        # 遍历主表结果。
        for row_data in primary_rows:

            # 追加当前结果行。
            self.append_merged_row(query_definition, merged_rows, signature_index, row_data)

        # 遍历补充结果。
        for row_data in supplemental_rows:

            # 合并补充结果行。
            self.append_merged_row(query_definition, merged_rows, signature_index, row_data)

        # 返回合并结果。
        return merged_rows

    # 定义合并行追加方法。
    def append_merged_row(self, query_definition, merged_rows, signature_index, row_data):

        """
        按标准字段签名追加或合并数据行。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param merged_rows: 合并结果列表。
        :type merged_rows: list[dict]
        :param signature_index: 行签名索引。
        :type signature_index: dict
        :param row_data: 待处理数据行。
        :type row_data: dict
        :return: None。
        :rtype: None
        """

        # 读取当前数据行签名。
        signature = self.build_row_signature(query_definition, row_data)

        # 判断签名是否已存在。
        if signature in signature_index:

            # 读取已存在的目标行。
            target_row = merged_rows[signature_index[signature]]

            # 遍历补充字段。
            for field_name, field_value in row_data.items():

                # 判断目标行是否缺失当前字段。
                if field_name not in target_row or target_row.get(field_name) in ("", None):

                    # 写入补充字段值。
                    target_row[field_name] = field_value

            # 结束合并流程。
            return None

        # 记录当前签名位置。
        signature_index[signature] = len(merged_rows)

        # 追加当前数据行副本。
        merged_rows.append(dict(row_data))

        # 返回空结果。
        return None

    # 定义行签名构建方法。
    def build_row_signature(self, query_definition, row_data):

        """
        构建用于合并的行签名。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param row_data: 数据行。
        :type row_data: dict
        :return: 行签名元组。
        :rtype: tuple
        """

        # 初始化签名值列表。
        signature_values = []

        # 遍历标准字段顺序。
        for column_name in query_definition["字段列表"]:

            # 读取标准字段值。
            signature_values.append(self.normalize_cell_value(row_data.get(column_name, "")))

        # 返回不可变行签名。
        return tuple(signature_values)

    # 定义原始行转换方法。
    def convert_raw_row(self, query_definition, raw_row):

        """
        转换 Forguncy C0/C1 字段行为标准字段行。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param raw_row: 原始行数据。
        :type raw_row: dict
        :return: 标准字段行。
        :rtype: dict
        """

        # 初始化结果行。
        row_data = {}

        # 遍历标准字段顺序。
        for column_index, column_name in enumerate(query_definition["字段列表"]):

            # 读取原始字段值。
            raw_value = raw_row.get(f"C{column_index}", "")

            # 写入标准字段值。
            row_data[column_name] = self.normalize_cell_value(raw_value)

        # 追加原始查询字段。
        for raw_key, raw_value in raw_row.items():

            # 跳过已映射字段。
            if raw_key.startswith("C"):
                continue

            # 追加原始字段值。
            row_data[raw_key] = self.normalize_cell_value(raw_value)

        # 返回标准字段行。
        return row_data

    # 定义单元格值标准化方法。
    def normalize_cell_value(self, value):

        """
        标准化 Forguncy 单元格值。

        :param value: 原始单元格值。
        :type value: object
        :return: 标准化后的单元格值。
        :rtype: object
        """

        # 判断单元格值是否为空。
        if value is None:

            # 返回空字符串。
            return ""

        # 判断单元格值是否为文本。
        if isinstance(value, str):

            # 返回去除首尾空白后的文本。
            return value.strip()

        # 判断单元格值是否为 OADate 序列。
        if isinstance(value, (int, float)) and value > 30000:

            # 尝试转换为日期文本。
            try:

                # 读取 OA 日期基准。
                base_date = datetime(1899, 12, 30)

                # 计算真实日期。
                real_date = base_date + timedelta(days=float(value))

                # 返回日期文本。
                return real_date.strftime("%Y-%m-%d")

            except Exception:

                # 返回原始单元格值。
                return value

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

        # 初始化字段集合。
        headers = list(query_definition["字段列表"])

        # 遍历结果行补充原始字段。
        for row_data in rows:

            # 遍历当前行字段。
            for column_name in row_data.keys():

                # 判断字段是否已存在。
                if column_name not in headers:

                    # 追加动态字段。
                    headers.append(column_name)

        # 创建工作簿。
        workbook = Workbook()

        # 读取活动工作表。
        worksheet = workbook.active

        # 写入表头。
        worksheet.append(headers)

        # 遍历查询结果行。
        for row_data in rows:

            # 写入当前数据行。
            worksheet.append([row_data.get(column_name, "") for column_name in headers])

        # 删除旧目标文件。
        if os.path.exists(target_path):

            # 清理旧文件。
            os.remove(target_path)

        # 保存目标工作簿。
        workbook.save(target_path)

        # 关闭目标工作簿。
        workbook.close()

        # 返回空结果。
        return None

    # 定义标准输出文件名构建方法。
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

        # 返回基类统一命名。
        return super().build_output_file_name(data_type, start_date, end_date)

    # 定义 OA 日期序列转换方法。
    def to_oa_date_serial(self, date_text):

        """
        将日期文本转换为 OA 序列号。

        :param date_text: 日期文本。
        :type date_text: str | None
        :return: OA 日期序列号。
        :rtype: int | None
        """

        # 判断日期文本是否为空。
        if not date_text:

            # 返回空值。
            return None

        # 解析日期文本。
        date_obj = datetime.strptime(str(date_text), "%Y-%m-%d")

        # 计算 OA 序列号。
        return (date_obj - datetime(1899, 12, 30)).days

    # 定义请求地址构建方法。
    def build_api_url(self, route_path):

        """
        构建 API 请求地址。

        :param route_path: 路由路径。
        :type route_path: str
        :return: API 地址。
        :rtype: str
        """

        # 返回完整 API 请求地址。
        return f"{self.base_url}/{route_path.lstrip('/')}"
