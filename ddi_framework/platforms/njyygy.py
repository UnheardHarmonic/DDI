# -*- coding: utf-8 -*-
"""
南京医药国药 DDI 数据直连系统协议适配器。

本模块负责南京医药国药有限公司供应商门户（DDI数据直连系统，ddi.njyygy.com
前端 + ddi-api.njyygy.com 接口）的协议登录、五类型数据查询、分页汇聚和
原始字段 Excel 落地。
登录链路为：JSON 表单提交手机号与明文密码（无验证码）换取 Bearer 令牌。
数据链路为：按类型端点 POST JSON 分页负载（三流向带日期区间、两库存快照），
响应为 data.list 数据行与 data.total 总条数，按空页与总账双口径翻页汇聚。
"""

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入随机数模块。
import random

# 导入 JSON 编解码模块。
import json

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义平台接口根地址常量。
API_BASE_URL = "https://ddi-api.njyygy.com"

# 定义前端站点地址常量。
WEB_BASE_URL = "https://ddi.njyygy.com"

# 定义登录接口路径常量。
LOGIN_API_PATH = "/api/v1/user/login"


# 定义南京医药国药 DDI 数据直连系统协议适配器。
class NjyygyPlatform(BasePlatform):

    """
    南京医药国药 DDI 数据直连系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 南京医药国药平台适配器实例。
    :rtype: NjyygyPlatform
    """

    # 定义平台支持的接入数据类型。
    SUPPORTED_TYPES = ["配送流向", "购进流向", "纯销流向", "门店库存", "仓库库存"]

    # 定义按日期区间查询的流向类数据类型清单。
    FLOW_TYPES = ["配送流向", "购进流向", "纯销流向"]

    # 定义数据类型到查询端点路径的映射。
    DATA_PATHS = {
        "配送流向": "/api/v1/supplier-data/delivery-out",
        "购进流向": "/api/v1/supplier-data/purchase-in",
        "纯销流向": "/api/v1/supplier-data/retail-out",
        "门店库存": "/api/v1/supplier-data/store-stock",
        "仓库库存": "/api/v1/supplier-data/warehouse-stock",
    }

    # 定义单页行数（平台 500 拒绝、100 实测通过）。
    PAGE_SIZE = 100

    # 定义分页安全上限页数。
    MAX_PAGES = 500

    # 定义数据请求超时秒数。
    QUERY_TIMEOUT = 120

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化南京医药国药平台适配器。

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

        # 保存接口根地址。
        self.api_base_url = str(account.get("站点根地址", API_BASE_URL)).rstrip("/")

        # 保存前端站点地址（引用页同源）。
        self.web_base_url = str(account.get("前端地址", WEB_BASE_URL)).rstrip("/")

        # 保存登录接口地址。
        self.login_api_url = str(account.get("登录接口", self.api_base_url + LOGIN_API_PATH))

        # 初始化带 Cookie 管理的协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 初始化登录状态标记。
        self.logged_in = False

        # 初始化访问令牌。
        self.access_token = ""

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验平台数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否在支持清单内。
        if data_type not in self.SUPPORTED_TYPES:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"南京医药国药平台暂未接入: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 仅流向类按日期区间查询，两类库存按当前快照查询。
        return data_type in self.FLOW_TYPES

    # 定义公共请求头构建方法。
    def build_json_headers(self):

        """
        构建 JSON 接口请求头（同源引用页口径）。

        :return: 请求头字典。
        :rtype: dict
        """

        # 组装请求头字典。
        return {
            "User-Agent": self.http.user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": self.web_base_url,
            "Referer": self.web_base_url + "/",
        }

    # 定义认证请求头构建方法。
    def build_auth_headers(self):

        """
        构建携带访问令牌的认证请求头。

        :return: 认证请求头字典。
        :rtype: dict
        """

        # 复制 JSON 请求头。
        headers = self.build_json_headers()

        # 写入 Bearer 访问令牌。
        headers["Authorization"] = f"Bearer {self.access_token}"

        # 返回认证请求头。
        return headers

    # 定义登录表单构建方法。
    def build_login_payload(self):

        """
        构建登录请求体（平台明文 JSON 口径）。

        :return: 登录请求体。
        :rtype: dict
        """

        # 返回手机号、明文密码与空验证码三字段。
        return {"phone": self.clean_login_name(), "password": self.clean_login_password(), "captcha": ""}

    # 定义登录响应校验方法。
    def validate_login_response(self, response_data):

        """
        校验登录响应并提取访问令牌。

        :param response_data: 登录响应字典。
        :type response_data: dict
        :return: None。
        :rtype: None
        """

        # 读取业务数据块。
        data_block = response_data.get("data") or {}

        # 判断登录成功（外层 0000 且内层 success 携带令牌）。
        if str(response_data.get("code")) == "0000" and data_block.get("success") is True and data_block.get("token"):

            # 保存访问令牌。
            self.access_token = str(data_block["token"])

            # 置位登录状态标记。
            self.logged_in = True

            # 结束校验。
            return

        # 读取内层失败信息。
        fail_count = data_block.get("failCount")
        fail_remain = data_block.get("failRemainCount")

        # 抛出登录失败异常并携带剩余尝试次数。
        raise RuntimeError(f"{self.company_name} 南京医药国药登录失败：{data_block.get('message') or response_data}（已错 {fail_count} 次，锁号前剩余 {fail_remain} 次尝试）")

    # 定义平台登录方法。
    def login(self):

        """
        执行南京医药国药平台协议登录。

        :return: 登录结果字典。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("南京医药国药登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录配置日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("密码长度", len(self.clean_login_password()), "cyan"), self.ph.kv("密码指纹", self.mask_secret(self.clean_login_password()), "yellow")))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 发送登录请求。
        result = self.http.request("POST", self.login_api_url, headers=self.build_json_headers(), data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), timeout=60, allow_http_error=True)

        # 解析登录响应。
        response_data = json.loads(result.body.decode("utf-8", "replace"))

        # 校验登录响应并保存令牌。
        self.validate_login_response(response_data)

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("正式登录成功", self.clean_login_name(), "green"))

        # 返回登录结果。
        return {"token": self.access_token}

    # 定义登录态保障方法。
    def ensure_login(self):

        """
        确保当前会话已建立有效登录态。

        :return: None。
        :rtype: None
        """

        # 判断当前尚未登录。
        if not self.logged_in:

            # 执行平台登录流程。
            self.login()

    # 定义登录态重置方法。
    def reset_login(self):

        """
        重置登录态以供认证失效后重建会话。

        :return: None。
        :rtype: None
        """

        # 清空访问令牌。
        self.access_token = ""

        # 置位未登录标记。
        self.logged_in = False

    # 定义敏感文本掩码方法。
    def mask_secret(self, secret_text):

        """
        构建密码掩码文本。

        :param secret_text: 原始密码。
        :type secret_text: str
        :return: 密码掩码文本。
        :rtype: str
        """

        # 返回空密码标记。
        if not secret_text:

            # 返回空标记文本。
            return "<空>"

        # 返回短密码掩码。
        if len(secret_text) <= 2:

            # 返回等长星号掩码。
            return "*" * len(secret_text)

        # 返回首尾可见的密码掩码。
        return f"{secret_text[0]}***{secret_text[-1]}"

    # 定义查询负载构建方法。
    def build_query_payload(self, data_type, start_date, end_date, page_number):

        """
        构建指定类型的查询负载。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 页码。
        :type page_number: int
        :return: 查询负载字典。
        :rtype: dict
        """

        # 组装分页公共字段。
        payload = {"pageNum": page_number, "pageSize": self.PAGE_SIZE}

        # 流向类追加日期区间。
        if data_type in self.FLOW_TYPES:

            # 写入开始日期。
            payload["startTime"] = start_date

            # 写入结束日期。
            payload["endTime"] = end_date

        # 返回查询负载。
        return payload

    # 定义单页响应解析方法。
    def parse_one_page_sample(self, response_data):

        """
        解析单页响应字典为数据行、总条数与表头。

        :param response_data: 查询响应字典。
        :type response_data: dict
        :return: 数据行、总条数与表头元组。
        :rtype: tuple[list[dict], int | None, list[str]]
        """

        # 读取业务数据块。
        data_block = response_data.get("data") or {}

        # 读取当前页数据行。
        data_rows = data_block.get("list") or []

        # 读取总条数。
        total_count = data_block.get("total")

        # 按首次出现顺序汇聚表头。
        headers = []

        # 遍历数据行。
        for row in data_rows:

            # 遍历行字段。
            for field_name in row.keys():

                # 按首次出现顺序记录字段。
                if field_name not in headers:

                    # 记录新字段。
                    headers.append(field_name)

        # 返回数据行、总条数与表头。
        return data_rows, int(total_count) if total_count is not None else None, headers

    # 定义单页查询方法。
    def query_one_page(self, data_type, start_date, end_date, page_number, allow_relogin=True):

        """
        查询指定类型与页码的数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 页码。
        :type page_number: int
        :param allow_relogin: 认证失效时是否允许重建会话重试一次。
        :type allow_relogin: bool
        :return: 数据行、总条数与表头元组。
        :rtype: tuple[list[dict], int | None, list[str]]
        """

        # 构建查询负载。
        payload = self.build_query_payload(data_type, start_date, end_date, page_number)

        # 发送查询请求。
        result = self.http.request("POST", f"{self.api_base_url}{self.DATA_PATHS[data_type]}", headers=self.build_auth_headers(), data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), timeout=self.QUERY_TIMEOUT, allow_http_error=True)

        # 解析查询响应。
        response_data = json.loads(result.body.decode("utf-8", "replace"))

        # 判断响应为会话失效。
        if str(response_data.get("code")) == "3001":

            # 判断允许重建会话。
            if allow_relogin:

                # 打印会话失效日志。
                self.ph.warning("访问令牌已失效，重建登录后重试当前页")

                # 重置登录态并重新登录。
                self.reset_login()

                # 执行重新登录。
                self.ensure_login()

                # 递归重试当前页且不再二次重建。
                return self.query_one_page(data_type, start_date, end_date, page_number, allow_relogin=False)

            # 抛出会话失效异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询会话失效")

        # 校验业务响应码。
        if str(response_data.get("code")) != "0000":

            # 抛出查询响应异常并携带平台消息。
            raise RuntimeError(f"{data_type} 查询响应异常 code={response_data.get('code')} message={response_data.get('message') or response_data}")

        # 解析单页响应。
        data_rows, total_count, headers = self.parse_one_page_sample(response_data)

        # 返回数据行、总条数与表头。
        return data_rows, total_count, headers

    # 定义多页汇聚查询方法。
    def query_pages(self, data_type, start_date, end_date):

        """
        按总账与空页终止口径汇聚指定类型的全量数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 表头与全量数据行元组。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化累计数据行。
        all_rows = []

        # 初始化表头容器。
        headers = []

        # 遍历分页页码。
        for page_number in range(1, self.MAX_PAGES + 1):

            # 查询当前页。
            page_rows, total_count, page_headers = self.query_one_page(data_type, start_date, end_date, page_number)

            # 记录首个非空表头。
            if page_headers and not headers:

                # 保存表头。
                headers = page_headers

            # 空页即终点。
            if not page_rows:

                # 结束翻页遍历。
                break

            # 累加当前页数据行。
            all_rows.extend(page_rows)

            # 打印当前页完成日志。
            self.ph.success(self.ph.join(self.ph.kv(f"{data_type} 当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总条数", total_count if total_count is not None else "-", "cyan")))

            # 判断累计行数已覆盖总条数。
            if total_count is not None and len(all_rows) >= total_count:

                # 结束翻页遍历。
                break

            # 分页请求之间保持轻量随机间隔。
            time.sleep(random.uniform(0.3, 0.8))

        # 返回表头与全量数据行。
        return headers, all_rows

    # 定义数据查询方法。
    def query_data(self, data_type, start_date=None, end_date=None):

        """
        查询南京医药国药平台指定类型全量数据。

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
        self.print_query_section(data_type, start_date, end_date)

        # 判断当前类型为流向类。
        if data_type in self.FLOW_TYPES:

            # 校验查询开始日期。
            if not start_date:

                # 抛出查询开始日期缺失异常。
                raise ValueError(f"查询{data_type}必须提供 start_date")

            # 校验查询结束日期。
            if not end_date:

                # 抛出查询结束日期缺失异常。
                raise ValueError(f"查询{data_type}必须提供 end_date")

        # 汇聚全量数据行。
        headers, all_rows = self.query_pages(data_type, start_date, end_date)

        # 打印汇聚完成日志。
        self.ph.success(self.ph.kv(f"{data_type} 查询完成", f"{len(all_rows)} 条 | {len(headers)} 列"))

        # 返回查询结果与表头。
        return {"rows": all_rows, "headers": headers}

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询南京医药国药平台流向数据。

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
        查询南京医药国药平台数据并生成原始字段 Excel。

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
        导出南京医药国药平台数据。

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
