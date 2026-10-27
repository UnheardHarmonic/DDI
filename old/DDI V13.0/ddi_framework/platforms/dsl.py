# -*- coding: utf-8 -*-
"""
大参林供应商服务平台协议适配器。

本模块负责大参林供应商服务平台的协议登录、授权编号参数维护、分页查询和本地 Excel 生成。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入日期时间对象。
from datetime import datetime

# 导入 URL 编码与解析函数。
from urllib.parse import urlencode, urlparse

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义大参林供应商服务平台协议适配器。
class DslPlatform(BasePlatform):

    """
    大参林供应商服务平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 大参林平台适配器实例。
    :rtype: DslPlatform
    """

    # 定义大参林适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化大参林平台适配器。

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

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", "https://srm.dslyy.com/user/login?redirect=%2F")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", "https://srm.dslyy.com/els/supply/account/supplier-login/login")

        # 保存采购查询接口地址。
        self.purchase_query_url = account.get("采购查询接口", "https://srm.dslyy.com/els/flow/supplier/orderList")

        # 保存仓库库存查询接口地址。
        self.warehouse_stock_query_url = account.get("仓库库存查询接口", "https://srm.dslyy.com/els/flow/supplier/whStockList")

        # 保存配送查询接口地址。
        self.dist_query_url = account.get("配送查询接口", "https://srm.dslyy.com/els/flow/supplier/tsfList")

        # 保存门店库存查询接口地址。
        self.store_stock_query_url = account.get("门店库存查询接口", "https://srm.dslyy.com/els/flow/supplier/storeStockList")

        # 保存销售查询接口地址。
        self.store_sale_query_url = account.get("销售查询接口", "https://srm.dslyy.com/els/flow/supplier/storeSaleList")

        # 保存平台根地址。
        self.base_url = self.build_origin(self.login_page_url)

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录响应。
        self.login_result = {}

        # 初始化登录令牌。
        self.login_token = ""

        # 初始化登录用户信息。
        self.user_info = {}

        # 保存默认分页大小。
        self.page_size = int(account.get("分页大小", 1000))

        # 保存平台允许的最大分页大小。
        self.max_page_size = 1000

    # 定义大参林登录方法。
    def login(self):

        """
        执行大参林协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("大参林登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 访问登录页以初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 打印正式登录请求日志。
        self.ph.info("提交正式登录请求: /els/supply/account/supplier-login/login")

        # 提交登录请求。
        result = self.post_login(payload)

        # 解析登录响应。
        login_result = self.decode_json_response(result)

        # 校验登录结果。
        if not self.is_login_success(login_result):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{self.extract_response_message(login_result)}")

        # 保存登录响应。
        self.login_result = login_result

        # 保存登录令牌。
        self.login_token = self.extract_login_token(login_result)

        # 保存登录用户信息。
        self.user_info = self.extract_user_info(login_result)

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("正式登录成功", self.extract_response_message(login_result), "green"), self.ph.kv("供应商", self.get_supplier_name(), "cyan")))

        # 返回登录响应。
        return login_result

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建大参林登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录 JSON 字段。
        return {"elsAccount": self.get_supplier_code(), "subAccount": self.clean_login_name(), "password": self.clean_login_password()}

    # 定义登录提交方法。
    def post_login(self, payload):

        """
        提交大参林登录请求。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 序列化登录请求体。
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 构建登录请求头。
        headers = self.build_login_headers()

        # 拼接带时间戳的登录接口地址。
        request_url = f"{self.login_api_url}?{urlencode({'_t': int(time.time() * 1000)})}"

        # 发送登录请求。
        return self.http.request("POST", request_url, headers=headers, data=body)

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建登录接口请求头。

        :return: 登录请求头。
        :rtype: dict
        """

        # 返回浏览器 JSON 登录请求头。
        return {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6", "Connection": "keep-alive", "Content-Type": "application/json;charset=UTF-8", "Origin": self.base_url, "Referer": self.login_page_url, "User-Agent": self.http.user_agent()}

    # 定义 JSON 响应解析方法。
    def decode_json_response(self, result):

        """
        解析 JSON 响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 处理空响应。
        if not response_text:

            # 返回空响应错误结构。
            return {"code": 0, "message": "接口返回空响应"}

        # 返回 JSON 响应数据。
        return json.loads(response_text)

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断登录响应是否成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 读取响应成功标记。
        success_value = bool(login_result.get("success"))

        # 读取响应编码。
        code_value = str(login_result.get("code", ""))

        # 返回登录成功判断结果。
        return success_value and code_value == "200"

    # 定义响应消息提取方法。
    def extract_response_message(self, response_data):

        """
        提取接口响应消息。

        :param response_data: 接口响应数据。
        :type response_data: dict
        :return: 接口响应消息。
        :rtype: str
        """

        # 返回接口消息或原始响应摘要。
        return str(response_data.get("message") or response_data.get("msg") or response_data)

    # 定义登录令牌提取方法。
    def extract_login_token(self, login_result):

        """
        提取登录认证令牌。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录认证令牌。
        :rtype: str
        """

        # 读取响应业务数据。
        data_value = login_result.get("result") or {}

        # 返回登录令牌。
        return str(data_value.get("token") or "")

    # 定义登录用户信息提取方法。
    def extract_user_info(self, login_result):

        """
        提取登录用户信息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录用户信息。
        :rtype: dict
        """

        # 读取响应业务数据。
        data_value = login_result.get("result") or {}

        # 返回登录用户信息。
        return data_value.get("userInfo") or {}

    # 定义登录账号清洗方法。
    def clean_login_name(self):

        """
        读取并清洗登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回去除两端空白后的登录账号。
        return str(self.account.get("账号", "")).strip()

    # 定义登录密码清洗方法。
    def clean_login_password(self):

        """
        读取并清洗登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回去除两端空白后的登录密码。
        return str(self.account.get("密码", "")).strip()

    # 定义供应商编码读取方法。
    def get_supplier_code(self):

        """
        读取供应商编码。

        :return: 供应商编码。
        :rtype: str
        """

        # 返回账号配置中的供应商编码。
        return str(self.account.get("供应商编码", "")).strip()

    # 定义供应商名称读取方法。
    def get_supplier_name(self):

        """
        读取供应商名称。

        :return: 供应商名称。
        :rtype: str
        """

        # 返回登录响应中的供应商名称。
        return str(self.user_info.get("supplierName") or self.account.get("供应商名称") or "").strip()

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录 Cookie 与认证令牌。

        :param output_dir: 输出目录。
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

        # 保存认证令牌文件。
        self.save_token_file(output_dir)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义令牌保存方法。
    def save_token_file(self, output_dir):

        """
        保存登录令牌到本地文件。

        :param output_dir: 输出目录。
        :type output_dir: str
        :return: 令牌文件路径。
        :rtype: str
        """

        # 构建令牌文件路径。
        token_path = os.path.join(output_dir, f"{self.company_name}_token.json")

        # 构建令牌文件内容。
        token_data = {"token": self.login_token, "user_info": self.user_info, "login_result": self.login_result}

        # 写入令牌文件。
        with open(token_path, "w", encoding="utf-8") as file_obj:

            # 序列化令牌文件内容。
            json.dump(token_data, file_obj, ensure_ascii=False, indent=2)

        # 打印令牌保存日志。
        self.ph.success(self.ph.kv("登录令牌已保存", self.ph.path(token_path), "green"))

        # 返回令牌文件路径。
        return token_path

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询大参林业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 查询指定类型完整数据。
        query_result = self.query_dsl_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出大参林业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 输出目录。
        :type output_dir: str | None
        :return: 导出文件路径。
        :rtype: str
        """

        # 使用分页查询结果生成本地 Excel 文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询大参林业务数据并生成 Excel。

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

        # 查询指定业务数据。
        query_result = self.query_dsl_data(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义大参林数据查询方法。
    def query_dsl_data(self, data_type, start_date, end_date):

        """
        查询大参林指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果与表头。
        :rtype: dict
        """

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 校验开始日期。
        if not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验结束日期。
        if not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

        # 初始化当前页码。
        current_page = 1

        # 初始化累计数据行。
        all_rows = []

        # 初始化总记录数。
        total_count = None

        # 按页循环请求业务数据。
        while True:

            # 构建当前页查询参数。
            params = self.build_query_params(data_type, start_date, end_date, current_page)

            # 打印分页请求日志。
            self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", f"pageNo={current_page}", "cyan"), self.ph.kv("pageSize", params["pageSize"], "yellow")))

            # 发送当前页查询请求。
            result = self.get_query_page(data_type, params)

            # 解析当前页查询响应。
            page_result = self.decode_query_page(result)

            # 读取当前页数据行。
            page_rows = page_result["rows"]

            # 保存总记录数。
            total_count = page_result["total"]

            # 追加当前页数据行。
            all_rows.extend(page_rows)

            # 打印当前页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "yellow")))

            # 判断是否已经完成全部分页。
            if len(all_rows) >= int(total_count or 0) or not page_rows:

                # 结束分页循环。
                break

            # 递增页码。
            current_page += 1

        # 返回查询数据与表头。
        return {"rows": all_rows, "headers": self.build_headers(data_type)}

    # 定义登录状态校验方法。
    def ensure_login(self):

        """
        确保当前适配器已经完成登录。

        :return: None。
        :rtype: None
        """

        # 判断登录令牌是否已经存在。
        if self.login_token:

            # 登录令牌存在时直接返回。
            return

        # 执行登录流程。
        self.login()

    # 定义查询参数构建方法。
    def build_query_params(self, data_type, start_date, end_date, page_number):

        """
        构建分页查询参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_number: 当前页码。
        :type page_number: int
        :return: 查询参数。
        :rtype: dict
        """

        # 构建通用分页参数。
        params = {"itemName": "", "item": "", "applyId": self.get_apply_id(data_type), "roleType": "NOT_MANAGER", "supplierName": self.get_supplier_name(), "supplierCode": self.get_supplier_code(), "supplier": self.get_supplier_code(), "isRuquired": "true", "toSubAccount": self.clean_login_name(), "pageSize": self.get_page_size(), "pageNo": page_number, "filter": "{}", "column": "id", "order": "desc"}

        # 判断库存类查询是否使用单日库存日期。
        if data_type in ["仓库库存", "门店库存"]:

            # 写入库存查询日期作为开始日期。
            params["startTime"] = end_date

            # 写入库存查询日期作为结束日期。
            params["endTime"] = end_date

        # 处理流向类查询日期范围。
        else:

            # 写入查询开始日期。
            params["startTime"] = start_date

            # 写入查询结束日期。
            params["endTime"] = end_date

        # 判断是否为仓库库存查询。
        if data_type in ["仓库库存", "门店库存"]:

            # 写入厂家过滤字段。
            params["factory"] = ""

        # 判断是否为纯销流向查询。
        if data_type == "纯销流向":

            # 写入销售状态过滤字段。
            params["state"] = ""

            # 写入门店名称过滤字段。
            params["storeName"] = ""

        # 返回查询参数。
        return params

    # 定义分页大小读取方法。
    def get_page_size(self):

        """
        读取平台分页大小。

        :return: 分页大小。
        :rtype: int
        """

        # 返回不超过平台上限的分页大小。
        return min(int(self.page_size), self.max_page_size)

    # 定义授权编号读取方法。
    def get_apply_id(self, data_type):

        """
        读取数据类型对应的授权编号。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 授权编号。
        :rtype: str
        """

        # 定义数据类型与授权编号映射。
        mapping = self.account.get("授权编号") or {}

        # 返回当前数据类型授权编号。
        return str(mapping[data_type])

    # 定义单页查询方法。
    def get_query_page(self, data_type, params):

        """
        请求单页业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param params: 查询参数。
        :type params: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建查询地址。
        query_url = f"{self.build_query_api_url(data_type)}?{urlencode(params)}"

        # 构建查询请求头。
        headers = self.build_query_headers(data_type)

        # 发送查询请求。
        return self.http.request("GET", query_url, headers=headers, timeout=90)

    # 定义查询接口地址构建方法。
    def build_query_api_url(self, data_type):

        """
        构建数据类型对应的查询接口地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询接口地址。
        :rtype: str
        """

        # 定义数据类型与接口地址映射。
        mapping = {"购进流向": self.purchase_query_url, "仓库库存": self.warehouse_stock_query_url, "配送流向": self.dist_query_url, "门店库存": self.store_stock_query_url, "纯销流向": self.store_sale_query_url}

        # 返回当前数据类型查询接口。
        return mapping[data_type]

    # 定义查询请求头构建方法。
    def build_query_headers(self, data_type):

        """
        构建业务查询请求头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询请求头。
        :rtype: dict
        """

        # 返回携带认证令牌的浏览器请求头。
        return {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6", "Connection": "keep-alive", "Origin": self.base_url, "Referer": self.build_referer_url(data_type), "User-Agent": self.http.user_agent(), "X-Access-Token": self.login_token}

    # 定义查询来源页面构建方法。
    def build_referer_url(self, data_type):

        """
        构建数据类型对应的来源页面地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 来源页面地址。
        :rtype: str
        """

        # 定义数据类型与来源页面路径映射。
        mapping = {"购进流向": "/sale/newFlow/purchaseSeach", "仓库库存": "/sale/newFlow/warehouseInventoryQuery", "配送流向": "/sale/newFlow/allocation", "门店库存": "/sale/newFlow/storeInventoryQuery", "纯销流向": "/sale/newFlow/salesQuery"}

        # 返回完整来源页面地址。
        return f"{self.base_url}{mapping[data_type]}"

    # 定义查询响应解析方法。
    def decode_query_page(self, result):

        """
        解析分页查询响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 标准分页结果。
        :rtype: dict
        """

        # 解析响应 JSON。
        response_data = self.decode_json_response(result)

        # 校验查询响应业务状态。
        if str(response_data.get("code", "")) != "200":

            # 抛出业务响应异常。
            raise RuntimeError(f"查询接口返回异常：{response_data}")

        # 读取分页数据对象。
        data_value = response_data.get("result") or {}

        # 读取当前页记录。
        rows = data_value.get("records") or []

        # 读取总记录数。
        total = int(data_value.get("total") or 0)

        # 返回标准分页结果。
        return {"rows": rows, "total": total}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验大参林数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in ["购进流向", "仓库库存", "配送流向", "门店库存", "纯销流向"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前大参林暂未接入: {data_type}")

    # 定义表头构建方法。
    def build_headers(self, data_type):

        """
        构建输出表头配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 判断是否为购进流向。
        if data_type == "购进流向":

            # 返回购进流向表头配置。
            return [("供应商名称", "supplierName"), ("商品编码", "item"), ("业务日期", "serviceDate"), ("公司名称", "companyName"), ("采购公司", "puchaseName"), ("批准文号", "approvalNumber"), ("效期", "effectEndDate"), ("目的国家", "toCountry"), ("批号", "lot"), ("目的仓库", "toLocName"), ("商品规格", "udaValueDesc"), ("商品名称", "itemName"), ("单位", "uom"), ("目的省份", "toState"), ("目的仓库编码", "toLoc"), ("供应商编码", "supplier"), ("数量", "qty")]

        # 判断是否为仓库库存。
        if data_type == "仓库库存":

            # 返回仓库库存表头配置。
            return self.build_stock_headers(False)

        # 判断是否为配送流向。
        if data_type == "配送流向":

            # 返回配送流向表头配置。
            return [("业务日期", "serviceDate"), ("公司名称", "companyName"), ("区域", "regionName"), ("来源公司", "lyCompanyName"), ("目的公司", "toLocCompanyName"), ("目的仓库简称", "toLocNameSec"), ("批号", "lot"), ("单位", "uom"), ("目的省份", "toState"), ("目的仓库编码", "toLoc"), ("片区", "areaName"), ("来源仓库", "fromLocName"), ("商品编码", "item"), ("来源省份", "fromState"), ("来源国家", "fromCountry"), ("来源仓库编码", "fromLoc"), ("单据类型", "docType"), ("商品名称", "itemDesc"), ("来源公司编码", "fromLocCompany"), ("批准文号", "approvalNumber"), ("目的公司编码", "toLocCompany"), ("效期", "effectEndDate"), ("目的国家", "toCountry"), ("目的仓库", "toLocName"), ("商品规格", "udaValueDesc"), ("配送类型", "tsfType"), ("来源公司名称", "fromLocCompanyName"), ("来源仓库简称", "fromLocNameSec"), ("数量", "qty")]

        # 判断是否为门店库存。
        if data_type == "门店库存":

            # 返回门店库存表头配置。
            return self.build_stock_headers(True)

        # 返回纯销流向表头配置。
        return [("订单号", "ord"), ("国家", "country"), ("厂家", "factory"), ("商品编码", "item"), ("销售日期", "serviceDate"), ("公司名称", "companyName"), ("区域", "regionName"), ("门店名称", "locName"), ("门店编码", "store"), ("来源公司", "lyCompanyName"), ("批准文号", "approvalNumber"), ("效期", "effectEndDate"), ("批号", "lot"), ("商品规格", "udaValueDesc"), ("商品名称", "itemName"), ("单位", "uom"), ("医生名称", "doctorName"), ("片区", "areaName"), ("适应症", "indiction"), ("数量", "qty"), ("门店简称", "storeName"), ("省份", "state"), ("门店全称", "storeFullName"), ("客户", "customer")]

    # 定义库存表头构建方法。
    def build_stock_headers(self, include_region):

        """
        构建库存类型输出表头配置。

        :param include_region: 是否包含区域字段。
        :type include_region: bool
        :return: 表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 构建库存基础表头。
        headers = [("国家", "country"), ("厂家", "factory"), ("商品编码", "item"), ("库存日期", "serviceDate"), ("公司名称", "companyName")]

        # 判断是否写入区域字段。
        if include_region:

            # 写入区域字段。
            headers.append(("区域", "regionName"))

        # 扩展库存通用表头。
        headers.extend([("来源公司", "lyCompanyName"), ("生产日期", "productDate"), ("批号", "lot"), ("商品规格", "udaValueDesc"), ("仓库简称", "invLocNameSec"), ("商品名称", "itemName"), ("单位", "uom"), ("批准文号", "approvedNumber"), ("片区", "areaName"), ("效期", "endEffectDate"), ("仓库名称", "invLocName"), ("数量", "qty"), ("省份", "state"), ("仓库编码", "invLoc")])

        # 返回库存表头配置。
        return headers

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

    # 定义流向月份标签构建方法。
    def build_month_label(self, start_date):

        """
        构建流向文件月份标签。

        :param start_date: 查询开始日期。
        :type start_date: str
        :return: 月份标签。
        :rtype: str
        """

        # 解析开始日期。
        date_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 返回 yy.m月 标签。
        return f"{date_value.year % 100}.{date_value.month}月"

    # 定义库存日期标签构建方法。
    def build_stock_date_label(self, end_date):

        """
        构建库存文件日期标签。

        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 库存日期标签。
        :rtype: str
        """

        # 读取导出当天日期。
        date_text = datetime.now().strftime("%Y-%m-%d")

        # 解析导出日期。
        date_value = datetime.strptime(date_text, "%Y-%m-%d")

        # 返回 yy.m.d 标签。
        return f"{date_value.year % 100}.{date_value.month}.{date_value.day}"

    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        写入查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param headers: 表头配置。
        :type headers: list[tuple[str, str]]
        :param output_path: 输出文件路径。
        :type output_path: str
        :param sheet_name: 工作表名称。
        :type sheet_name: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 导入列宽工具函数。
        from openpyxl.utils import get_column_letter

        # 创建 Excel 工作簿。
        workbook = Workbook(write_only=False)

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = sheet_name[:31]

        # 写入表头行。
        worksheet.append([header_name for header_name, _ in headers])

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按表头顺序组装一行数据。
            worksheet.append([row.get(field_name, "") if isinstance(row, dict) else "" for _, field_name in headers])

        # 遍历所有导出列设置列宽。
        for column_index, header_item in enumerate(headers, start=1):

            # 读取当前列字母。
            column_letter = get_column_letter(column_index)

            # 读取当前表头名称。
            header_name = header_item[0]

            # 设置当前列宽。
            worksheet.column_dimensions[column_letter].width = max(12, min(34, len(str(header_name)) + 10))

        # 冻结表头行。
        worksheet.freeze_panes = "A2"

        # 启用自动筛选。
        worksheet.auto_filter.ref = worksheet.dimensions

        # 创建输出目录。
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 删除已有同名文件。
        self.remove_existing_file(output_path)

        # 保存 Excel 文件。
        try:

            # 将工作簿保存到目标路径。
            workbook.save(output_path)

        # 处理文件被占用导致的保存异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

    # 定义同名文件删除方法。
    def remove_existing_file(self, output_path):

        """
        删除已有同名输出文件。

        :param output_path: 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 判断目标文件是否存在。
        if not os.path.exists(output_path):

            # 无需删除不存在的文件。
            return

        # 捕获文件删除异常。
        try:

            # 删除已有目标文件。
            os.remove(output_path)

        # 处理文件被占用导致的删除异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

    # 定义站点根地址构建方法。
    def build_origin(self, url):

        """
        构建 URL 的站点根地址。

        :param url: 原始 URL。
        :type url: str
        :return: 站点根地址。
        :rtype: str
        """

        # 解析 URL 结构。
        parsed_url = urlparse(url)

        # 返回协议与主机组合。
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
