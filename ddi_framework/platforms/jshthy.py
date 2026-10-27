# -*- coding: utf-8 -*-
"""
江苏恒泰华洋全亿健康 OA 平台协议适配器。

本模块负责江苏恒泰华洋医药有限公司在全亿健康 OA 系统中的 RSA 登录会话建立。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入日期时间对象。
from datetime import datetime, timezone

# 导入 RSA 非对称填充配置。
from cryptography.hazmat.primitives.asymmetric import padding

# 导入 PEM 公钥加载函数。
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义 RSA 密文标记默认值。
DEFAULT_RSA_FLAG = "``RSA``"

# 定义数据类型与 SRM 网关方法映射。
SRM_GATEWAY_METHODS = {
    "购进流向": "ykcloud.supinterface.oaSrmPurchase.queryPage",
    "配送流向": "ykcloud.supinterface.oaSrmDist.queryPage",
    "纯销流向": "ykcloud.supinterface.oaSrmSale.queryPage",
    "库存": "ykcloud.supinterface.oaSrmStock.queryPage",
}

# 定义数据类型与查询日期参数前缀映射（库存为快照无日期）。
SRM_DATE_PARAM_PREFIX = {
    "购进流向": "rec_date",
    "配送流向": "ship_date",
    "纯销流向": "order_date",
    "库存": "",
}


class JshthyPlatform(BasePlatform):
    """
    江苏恒泰华洋全亿健康 OA 平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 江苏恒泰华洋平台适配器实例。
    :rtype: JshthyPlatform
    """

    def __init__(self, company_name, account, printer=None):
        """
        初始化江苏恒泰华洋全亿健康 OA 平台适配器。

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
        self.api_base_url = account.get("接口根地址", "http://oa.myquanyi.com").rstrip("/")

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", f"{self.api_base_url}/wui/index.html#/login?type=2")

        # 保存登录表单配置接口。
        self.login_form_api_url = account.get("登录表单接口", f"{self.api_base_url}/api/hrm/login/getLoginForm")

        # 保存 RSA 参数接口。
        self.rsa_info_api_url = account.get("RSA参数接口", f"{self.api_base_url}/rsa/weaver.rsa.GetRsaInfo")

        # 保存登录校验接口。
        self.login_api_url = account.get("登录接口", f"{self.api_base_url}/api/hrm/login/checkLogin")

        # 保存登录语言编号。
        self.lang_id = str(account.get("语言编号", "7"))

        # 保存登录类型编号。
        self.login_type = str(account.get("登录类型", "2"))

        # 保存 SRM 数据网关地址。
        self.srm_gateway_url = account.get("数据网关地址", "https://xb-test.myquanyi.com:8080/portal-prod/gateway-manager/xjl-job")

        # 保存 SRM 应用编号。
        self.srm_app_key = str(account.get("应用编号", "18000"))

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 初始化登录表单配置。
        self.login_form = {}

        # 初始化 RSA 参数。
        self.rsa_info = {}

        # 初始化登录响应。
        self.login_result = {}

        # 初始化登录状态。
        self.logged_in = False

    def login(self):
        """
        执行江苏恒泰华洋全亿健康 OA 平台登录。

        :return: 登录响应数据。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("全亿健康 SRM 登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印首页初始化日志。
        self.ph.info(self.ph.join(self.ph.kv("访问登录页", self.login_page_url, "cyan"), self.ph.kv("账号", self.clean_login_name(), "cyan")))

        # 请求登录页以建立服务器会话 Cookie。
        self.http.get(self.login_page_url)

        # 获取登录表单配置。
        self.login_form = self.fetch_login_form()

        # 获取 RSA 加密参数。
        self.rsa_info = self.fetch_rsa_info()

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 提交表单登录请求。
        result = self.http.post_form(self.login_api_url, payload, self.login_page_url)

        # 解析登录响应。
        response_data = self.http.decode_json(result)

        # 保存登录响应。
        self.login_result = response_data

        # 判断登录响应是否成功。
        if str(response_data.get("loginstatus", "")).lower() != "true":

            # 读取平台登录失败消息。
            error_message = response_data.get("msg") or response_data.get("message") or response_data

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{error_message}")

        # 标记登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("用户ID", response_data.get("userid", ""), "cyan")))

        # 返回登录响应数据。
        return response_data

    def fetch_login_form(self):
        """
        获取登录表单配置。

        :return: 登录表单配置响应。
        :rtype: dict
        """

        # 构建登录表单请求体。
        payload = {"loginid": self.clean_login_name(), "langid": self.lang_id}

        # 请求登录表单配置接口。
        result = self.http.post_json(self.login_form_api_url, payload, self.login_page_url)

        # 解析登录表单响应。
        response_data = self.http.decode_json(result)

        # 读取登录加密开关。
        open_rsa = response_data.get("loginSetting", {}).get("openRSA", "")

        # 打印登录表单解析日志。
        self.ph.info(self.ph.join(self.ph.kv("登录表单", "已获取", "green"), self.ph.kv("RSA", open_rsa, "cyan")))

        # 返回登录表单配置。
        return response_data

    def fetch_rsa_info(self):
        """
        获取 RSA 加密参数。

        :return: RSA 参数响应。
        :rtype: dict
        """

        # 拼接 RSA 参数接口时间戳。
        rsa_url = f"{self.rsa_info_api_url}?ts={int(time.time() * 1000)}"

        # 请求 RSA 参数接口。
        result = self.http.get(rsa_url, referer=self.login_page_url)

        # 解析 RSA 参数响应。
        response_data = self.http.decode_json(result)

        # 校验 RSA 公钥字段。
        if not response_data.get("rsa_pub"):

            # 抛出 RSA 公钥缺失异常。
            raise RuntimeError(f"江苏恒泰华洋 RSA 参数缺少公钥：{response_data}")

        # 打印 RSA 参数解析日志。
        self.ph.info(self.ph.join(self.ph.kv("RSA参数", "已获取", "green"), self.ph.kv("标记", response_data.get("rsa_flag", DEFAULT_RSA_FLAG), "cyan")))

        # 返回 RSA 参数。
        return response_data

    def build_login_payload(self):
        """
        构建 RSA 加密后的登录请求体。

        :return: 登录表单字段。
        :rtype: dict
        """

        # 读取登录表单设置。
        login_setting = self.login_form.get("loginSetting", {})

        # 读取验证码键值。
        validate_code_key = login_setting.get("validateCodeKey", "")

        # 加密登录账号。
        encrypted_login_name = self.encrypt_rsa_value(self.clean_login_name())

        # 加密登录密码。
        encrypted_password = self.encrypt_rsa_value(self.clean_login_password())

        # 返回登录表单字段。
        return {"islanguid": self.lang_id, "loginid": encrypted_login_name, "userpassword": encrypted_password, "dynamicPassword": "", "tokenAuthKey": "", "validatecode": "", "validateCodeKey": validate_code_key, "logintype": self.login_type, "messages": "", "isie": "false", "appid": "", "service": "", "isRememberPassword": "false"}

    def encrypt_rsa_value(self, value):
        """
        使用平台 RSA 公钥加密登录字段。

        :param value: 明文字段值。
        :type value: str
        :return: 追加 RSA 标记后的 Base64 密文。
        :rtype: str
        """

        # 读取 RSA 公钥文本。
        public_key_text = self.normalize_public_key(self.rsa_info.get("rsa_pub", ""))

        # 加载 RSA 公钥对象。
        public_key = load_pem_public_key(public_key_text.encode("ascii"))

        # 读取 RSA 随机码。
        rsa_code = self.rsa_info.get("rsa_code") or ""

        # 读取 RSA 密文标记。
        rsa_flag = self.rsa_info.get("rsa_flag") or DEFAULT_RSA_FLAG

        # 初始化密文片段列表。
        encrypted_parts = []

        # 遍历前端约定的 240 字符分段。
        for chunk_start in range(0, len(str(value)), 240):

            # 读取当前明文片段。
            plain_chunk = str(value)[chunk_start:chunk_start + 240]

            # 拼接平台 RSA 随机码。
            plain_text = f"{plain_chunk}{rsa_code}"

            # 执行 RSA PKCS#1 v1.5 加密。
            cipher_bytes = public_key.encrypt(plain_text.encode("utf-8"), padding.PKCS1v15())

            # 追加 Base64 密文和平台 RSA 标记。
            encrypted_parts.append(f"{base64.b64encode(cipher_bytes).decode('ascii')}{rsa_flag}")

        # 返回完整密文。
        return "".join(encrypted_parts)

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


    def clean_login_password(self):
        """
        读取并清洗登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回原始密码字符串。
        return str(self.account.get("密码", ""))

    def validate_data_type(self, data_type):
        """
        校验数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否存在网关方法映射。
        if data_type not in SRM_GATEWAY_METHODS:

            # 抛出数据类型未接入异常。
            raise ValueError(f"全亿健康 SRM 平台暂未接入数据类型：{data_type}")

    def resolve_srm_session(self):
        """
        读取 SRM 网关会话凭证。

        :return: 会话凭证文本。
        :rtype: str
        """

        # 读取账号配置中的会话凭证。
        return str(self.account.get("SRM会话凭证", "")).strip()

    def build_gateway_url(self, data_type, params, page_number):
        """
        构建 SRM 网关查询地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param params: 网关业务参数。
        :type params: dict
        :param page_number: 当前页码。
        :type page_number: int
        :return: 网关查询地址。
        :rtype: str
        """

        # 导入 URL 编码函数。
        from urllib.parse import quote

        # 拼接业务参数 JSON 的 URL 编码文本。
        encoded_params = quote(json.dumps(params, ensure_ascii=False, separators=(",", ":")), safe="")

        # 返回拼接后的网关查询地址。
        return f"{self.srm_gateway_url}?method={SRM_GATEWAY_METHODS[data_type]}&app_key={self.srm_app_key}&params={encoded_params}"

    def build_gateway_params(self, data_type, start_date, end_date, page_number):
        """
        构建 SRM 网关业务参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_number: 当前页码。
        :type page_number: int
        :return: 网关业务参数。
        :rtype: dict
        """

        # 读取公司编码。
        company_code = str(self.account.get("公司编码", "")).strip()

        # 构建公共业务参数。
        params = {"tenant_num_id": str(self.account.get("租户编号", "18")), "data_sign": 0, "user_id": str(self.login_result.get("userid", "")), "cort_num_id": company_code, "item_num_id": "", "page_num": page_number, "page_size": int(self.account.get("分页大小", 10))}

        # 读取当前类型的日期参数前缀。
        date_prefix = SRM_DATE_PARAM_PREFIX.get(data_type, "")

        # 判断当前类型是否携带日期区间。
        if date_prefix:

            # 写入开始与结束毫秒时间戳。
            params[f"{date_prefix}_begin"] = self.to_epoch_millis(start_date)
            params[f"{date_prefix}_end"] = self.to_epoch_millis(end_date)

        # 返回业务参数。
        return params

    def to_epoch_millis(self, date_text):
        """
        将北京时区日期文本换算为毫秒时间戳。

        :param date_text: 日期文本。
        :type date_text: str
        :return: 毫秒时间戳。
        :rtype: int
        """

        # 按站点前端口径以 UTC 零点解析日期并返回毫秒时间戳。
        return int(datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

    def query_flow(self, data_type, start_date=None, end_date=None):
        """
        查询指定类型业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行。
        :rtype: list[dict]
        """

        # 查询 SRM 网关指定类型完整数据。
        query_result = self.query_srm_data(data_type, start_date, end_date)

        # 返回查询结果行。
        return query_result["rows"]

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

        # 查询 SRM 网关指定类型完整数据。
        query_result = self.query_srm_data(data_type, start_date, end_date)

        # 使用当前工作目录作为默认输出目录。
        output_dir = output_dir or os.getcwd()

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 构建输出文件路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    def query_srm_data(self, data_type, start_date, end_date):
        """
        查询 SRM 网关指定类型全部分页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 查询结果、表头和日期范围。
        :rtype: dict
        """

        # 导入 JSON 编解码模块。
        import json

        # 校验数据类型。
        self.validate_data_type(data_type)

        # 确保当前会话已经登录。
        self.ensure_login()

        # 缺省日期回退为当天。
        start_date = start_date or datetime.now().strftime("%Y-%m-%d")
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 读取 SRM 会话凭证。
        session_credential = self.resolve_srm_session()

        # 判断会话凭证是否已配置。
        if not session_credential:

            # 抛出会话凭证缺失异常。
            raise RuntimeError(f"{self.company_name} 缺少 SRM会话凭证 配置（门户登录后的 Authorization 值，待与平台方核对获取方式）")

        # 初始化合并数据行集合。
        merged_rows = []

        # 初始化合并表头集合。
        merged_headers = []

        # 初始化总页数。
        total_pages = 1

        # 初始化当前页码。
        page_number = 1

        # 循环读取全部分页。
        while page_number <= total_pages:

            # 构建当前页业务参数。
            params = self.build_gateway_params(data_type, start_date, end_date, page_number)

            # 构建当前页查询地址。
            url = self.build_gateway_url(data_type, params, page_number)

            # 构建请求头。
            headers = {"Authorization": session_credential, "Referer": self.srm_gateway_url.rsplit("/gateway-manager", 1)[0] + "/"}

            # 发送网关查询请求。
            result = self.http.request("GET", url, headers=headers, timeout=180, allow_http_error=True)

            # 解析网关响应。
            response_data = self.http.decode_json(result)

            # 读取数据块字段。
            data_block = response_data.get("data")

            # 判断数据块是否为列表形态。
            rows = data_block if isinstance(data_block, list) else []

            # 合并当前页数据行。
            merged_rows.extend(row for row in rows if isinstance(row, dict))

            # 按行序合并动态表头。
            merged_headers = self.merge_srm_headers(merged_headers, rows)

            # 打印分页读取日志。
            self.ph.info(self.ph.join(self.ph.kv("当前页", page_number, "cyan"), self.ph.kv("本页记录", len(rows), "cyan"), self.ph.kv("累计记录", len(merged_rows), "cyan")))

            # 判断当前页是否不足一页以终止读取。
            if len(rows) < int(self.account.get("分页大小", 10)):

                # 结束分页循环。
                break

            # 页码递增。
            page_number += 1

        # 返回查询结果。
        return {"headers": merged_headers, "rows": merged_rows, "start_date": start_date, "end_date": end_date}

    def merge_srm_headers(self, merged_headers, rows):
        """
        按行序合并动态表头。

        :param merged_headers: 已合并表头。
        :type merged_headers: list[str]
        :param rows: 当前页数据行。
        :type rows: list[dict]
        :return: 合并后的表头。
        :rtype: list[str]
        """

        # 初始化当前合并表头副本。
        current_headers = list(merged_headers)

        # 遍历当前页数据行。
        for row in rows:

            # 遍历当前行字段名称。
            for header_name in row.keys():

                # 判断字段名称是否已存在。
                if header_name in current_headers:

                    # 进入下一字段。
                    continue

                # 追加新字段。
                current_headers.append(header_name)

        # 返回合并后的表头。
        return current_headers

    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        写入查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param headers: 表头列表。
        :type headers: list[str]
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
        worksheet.append(headers)

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按表头顺序组装一行数据。
            worksheet.append([row.get(header_name, "") if isinstance(row, dict) else "" for header_name in headers])

        # 遍历所有导出列设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

            # 读取当前列字母。
            column_letter = get_column_letter(column_index)

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
