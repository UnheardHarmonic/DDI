# -*- coding: utf-8 -*-
"""
漱玉平民 QQT SRM 供应商门户协议适配器。

本模块负责漱玉医药物流(山东)供应商门户（sybm.sypm.cn，ELS 框架）的协议登录、
四类型数据查询、分页汇聚和原始字段 Excel 落地。
登录链路为：无令牌公钥接口（getEncryptedKey，base64 DER 公钥+keyId 会话绑定）→
RSA PKCS1v15 加密密码 → 登录接口换取 JWT 令牌；
数据接口以 X-Access-Token 请求头承载会话，查询串携带分页与日期参数。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入随机数模块。
import random

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义门户站点地址常量。
SITE_BASE_URL = "https://sybm.sypm.cn"

# 定义 ELS 接口根路径常量。
API_ROOT_PATH = "/els"

# 定义公钥接口路径常量。
PUBLIC_KEY_API_PATH = "/account/noToken/getEncryptedKey"

# 定义登录接口路径常量。
LOGIN_API_PATH = "/account/login"

# 定义数据接口根路径常量。
DATA_API_ROOT = "/supplier/saleMaterialFlow"


# 定义漱玉平民 QQT SRM 供应商门户协议适配器。
class SypmPlatform(BasePlatform):

    """
    漱玉平民 QQT SRM 供应商门户协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 漱玉平台适配器实例。
    :rtype: SypmPlatform
    """

    # 定义平台支持的接入数据类型。
    SUPPORTED_TYPES = ["购进流向", "纯销流向", "配送流向", "库存"]

    # 定义流向类数据类型清单。
    FLOW_TYPES = ["购进流向", "纯销流向", "配送流向"]

    # 定义数据类型到查询端点路径的映射。
    DATA_PATHS = {
        "购进流向": DATA_API_ROOT + "/detailList",
        "纯销流向": DATA_API_ROOT + "/detailSaleList",
        "配送流向": DATA_API_ROOT + "/detailDeliveryList",
        "库存": DATA_API_ROOT + "/detailStockList",
    }

    # 定义分页大小。
    PAGE_SIZE = 500

    # 定义分页安全上限页数。
    MAX_PAGES = 200

    # 定义分页请求之间的基础间隔秒数下限。
    PAGE_INTERVAL_MIN = 1.0

    # 定义分页请求之间的基础间隔秒数上限。
    PAGE_INTERVAL_MAX = 2.0

    # 定义触发流向频控后的等待秒数。
    RATE_LIMIT_WAIT_SECONDS = 32

    # 定义流向频控最大等待重试次数。
    MAX_RATE_LIMIT_RETRIES = 6

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化漱玉平台适配器。

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

        # 保存门户站点地址。
        self.site_base_url = str(account.get("站点根地址", SITE_BASE_URL)).rstrip("/")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.site_base_url)

        # 初始化登录态标记。
        self.logged_in = False

        # 初始化访问令牌。
        self.access_token = ""

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验平台数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in self.SUPPORTED_TYPES:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"漱玉平台暂未接入: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 流向三类型按日期区间查询，库存为快照不要求日期。
        return data_type in self.FLOW_TYPES

    # 定义请求时间戳构建方法。
    def build_timestamp(self):

        """
        构建接口查询串的毫秒时间戳参数。

        :return: 秒级精度带毫秒小数的时间戳字符串。
        :rtype: str
        """

        # 按前端 new Date().getTime()/1e3 形态输出。
        return f"{time.time():.3f}"

    # 定义密码加密方法。
    def encrypt_password(self, public_key_b64, plain_password):

        """
        按平台前端同款 RSA PKCS1v15 加密密码。

        :param public_key_b64: 服务端下发的 Base64 DER 公钥。
        :type public_key_b64: str
        :param plain_password: 明文密码。
        :type plain_password: str
        :return: Base64 密文。
        :rtype: str
        """

        # 导入序列化工具。
        from cryptography.hazmat.primitives import serialization

        # 导入非对称填充方案。
        from cryptography.hazmat.primitives.asymmetric import padding

        # 解码 DER 公钥。
        public_key = serialization.load_der_public_key(base64.b64decode(public_key_b64))

        # 执行 RSA PKCS1v15 加密并输出 Base64 密文。
        cipher_bytes = public_key.encrypt(plain_password.encode("utf-8"), padding.PKCS1v15())

        # 返回 Base64 密文。
        return base64.b64encode(cipher_bytes).decode("utf-8")

    # 定义基础请求头构建方法。
    def build_base_headers(self):

        """
        构建门户基础请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回浏览器同构请求头。
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": self.site_base_url,
            "Referer": self.site_base_url + "/",
            "User-Agent": self.http.user_agent(),
        }

    # 定义平台登录方法。
    def login(self):

        """
        执行漱玉平民门户协议登录并保存访问令牌。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("漱玉登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 构建基础请求头。
        headers = self.build_base_headers()

        # 拉取会话绑定的 RSA 公钥与编号。
        key_result = self.http.request("GET", self.site_base_url + API_ROOT_PATH + PUBLIC_KEY_API_PATH + "?_t=" + self.build_timestamp(), headers=headers, timeout=60, allow_http_error=True)

        # 解析公钥响应。
        key_data = json.loads(key_result.body.decode("utf-8", errors="replace"))

        # 判断公钥获取是否成功。
        if not key_data.get("success") or not (key_data.get("result") or {}).get("key"):

            # 抛出公钥获取异常。
            raise RuntimeError(f"{self.company_name} 漱玉平台公钥获取失败：{key_data.get('message')}")

        # 读取公钥编号。
        key_id = str(key_data["result"].get("keyId") or "")

        # 读取 Base64 DER 公钥。
        public_key_b64 = str(key_data["result"].get("key"))

        # 构建登录负载（密码以 RSA 密文承载）。
        login_payload = {
            "elsAccount": self.clean_login_name(),
            "subAccount": str(self.account.get("子账号") or ""),
            "password": self.encrypt_password(public_key_b64, self.clean_login_password()),
            "keyId": key_id,
            "loginType": None,
        }

        # 提交登录请求。
        login_result = self.http.request("POST", self.site_base_url + API_ROOT_PATH + LOGIN_API_PATH + "?_t=" + self.build_timestamp(), headers=headers, data=json.dumps(login_payload).encode("utf-8"), timeout=60, allow_http_error=True)

        # 解析登录响应。
        login_data = json.loads(login_result.body.decode("utf-8", errors="replace"))

        # 判断登录是否成功。
        if not login_data.get("success") or not (login_data.get("result") or {}).get("token"):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 漱玉平台登录失败：{login_data.get('message')}")

        # 保存访问令牌。
        self.access_token = str(login_data["result"].get("token"))

        # 标记登录态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("登录成功", self.ph.kv("令牌前缀", self.access_token[:20], "cyan"), "green"))

        # 返回登录结果摘要。
        return {"message": "登录成功"}

    # 定义数据请求头构建方法。
    def build_data_headers(self):

        """
        构建数据查询请求头（会话以裸令牌头承载）。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回数据查询请求头。
        headers = self.build_base_headers()

        # 附加会话令牌头。
        headers["X-Access-Token"] = self.access_token

        # 返回请求头。
        return headers

    # 定义单页查询地址构建方法。
    def build_query_url(self, data_type, start_date, end_date, page_number):

        """
        构建单页查询完整地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 页码。
        :type page_number: int
        :return: 完整查询地址。
        :rtype: str
        """

        # 构建列表通用查询参数。
        query_params = {
            "column": "id",
            "order": "desc",
            "filter": "{}",
            "superQueryParams": "null",
            "superQueryMatchType": "null",
            "pageSize": str(self.PAGE_SIZE),
            "pageNo": str(page_number),
        }

        # 判断当前类型是否为流向类（查询串附加日期区间）。
        if data_type in self.FLOW_TYPES:

            # 写入开始日期（YYYYMMDD 紧凑格式）。
            query_params["startDate"] = str(start_date or "").replace("-", "")

            # 写入结束日期（YYYYMMDD 紧凑格式）。
            query_params["endDate"] = str(end_date or "").replace("-", "")

        # 拼接完整查询地址。
        return self.site_base_url + API_ROOT_PATH + self.DATA_PATHS[data_type] + "?_t=" + self.build_timestamp() + "&" + urlencode(query_params)

    # 定义单页查询方法。
    def query_one_page(self, data_type, start_date, end_date, page_number):

        """
        查询漱玉平台单页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 页码。
        :type page_number: int
        :return: 平台原始分页数据块。
        :rtype: dict
        """

        # 打印分页请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", self.DATA_PATHS[data_type], "cyan"), self.ph.kv("pageNo", page_number, "yellow"), self.ph.kv("pageSize", self.PAGE_SIZE, "cyan")))

        # 按频控重试上限循环提交查询。
        for retry_index in range(1, self.MAX_RATE_LIMIT_RETRIES + 1):

            # 提交查询请求。
            result = self.http.request("GET", self.build_query_url(data_type, start_date, end_date, page_number), headers=self.build_data_headers(), timeout=300, allow_http_error=True)

            # 解析查询响应。
            response_data = json.loads(result.body.decode("utf-8", errors="replace"))

            # 判断响应是否成功。
            if response_data.get("success"):

                # 返回业务数据块。
                return response_data.get("result") or {}

            # 读取平台拒绝消息。
            response_message = str(response_data.get("message") or "")

            # 判断是否命中流向频控（平台提示 30 秒后再试）。
            if "频繁" in response_message:

                # 打印频控等待日志。
                self.ph.warning(self.ph.kv(f"命中流向频控（第 {retry_index} 次）", f"等待 {self.RATE_LIMIT_WAIT_SECONDS} 秒后重试", "yellow"))

                # 按平台冷却窗口等待。
                time.sleep(self.RATE_LIMIT_WAIT_SECONDS)

                # 进入下一次重试。
                continue

            # 抛出查询响应异常并携带平台消息。
            raise RuntimeError(f"{data_type} 查询响应异常 message={response_message}")

        # 抛出频控重试耗尽异常。
        raise RuntimeError(f"{data_type} 查询频控重试耗尽（{self.MAX_RATE_LIMIT_RETRIES} 次）")

    # 定义数据查询方法。
    def query_data(self, data_type, start_date=None, end_date=None):

        """
        查询漱玉平台全量数据并汇聚原始字段。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果与表头。
        :rtype: dict
        """

        # 校验数据类型。
        self.validate_data_type(data_type)

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "-", "cyan"), self.ph.kv("结束日期", end_date or "-", "cyan")))

        # 查询第一页数据。
        first_block = self.query_one_page(data_type, start_date, end_date, 1)

        # 读取当前页数据行。
        first_rows = first_block.get("records") or []

        # 读取总记录数。
        total_count = int(first_block.get("total") or 0)

        # 初始化累计数据行。
        all_rows = list(first_rows)

        # 打印首页完成日志。
        self.ph.success(self.ph.join(self.ph.kv("首页解析完成", f"{len(first_rows)} 条", "green"), self.ph.kv("总数", total_count, "cyan")))

        # 计算总页数。
        total_pages = (total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE if total_count else 1

        # 遍历剩余页码。
        for page_number in range(2, min(total_pages, self.MAX_PAGES) + 1):

            # 判断累计行数是否已满足总数。
            if len(all_rows) >= total_count:

                # 结束分页遍历。
                break

            # 查询当前页数据。
            page_block = self.query_one_page(data_type, start_date, end_date, page_number)

            # 读取当前页数据行。
            current_rows = page_block.get("records") or []

            # 判断当前页是否已无数据。
            if not current_rows:

                # 结束分页遍历。
                break

            # 累加当前页数据行。
            all_rows.extend(current_rows)

            # 打印当前页完成日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(current_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "cyan")))

            # 分页请求之间保持拟人化间隔以规避流向频控。
            time.sleep(random.uniform(self.PAGE_INTERVAL_MIN, self.PAGE_INTERVAL_MAX))

        # 按首次出现顺序汇聚跨页字段并集。
        columns = {}

        # 遍历全量数据行。
        for row in all_rows:

            # 遍历当前行字段。
            for field_name in row.keys():

                # 按首次出现顺序记录原名字段。
                columns.setdefault(field_name, field_name)

        # 打印汇聚完成日志。
        self.ph.success(self.ph.kv(f"{data_type} 查询完成", f"{len(all_rows)} 条 | {len(columns)} 列"))

        # 返回查询结果与表头。
        return {"rows": all_rows, "headers": list(columns.keys())}

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询漱玉平台流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果数据行。
        :rtype: list[dict]
        """

        # 查询指定类型数据。
        query_result = self.query_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询漱玉平台数据并生成原始字段 Excel。

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

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 查询平台数据。
        query_result = self.query_data(data_type, start_date, end_date)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 构建列映射（原始字段名同时作为标题与取值字段）。
        columns = [(field, field) for field in query_result["headers"]]

        # 写入原始字段 Excel。
        self.write_rows_to_excel(query_result["rows"], columns, output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"))

        # 返回 Excel 文件路径。
        return output_path

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出漱玉平台数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出文件路径。
        :rtype: str
        """

        # 委托查询落地方法生成 Excel。
        return self.query_flow_to_excel(data_type, start_date, end_date, output_dir)
