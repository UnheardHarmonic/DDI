# -*- coding: utf-8 -*-
"""
江苏恒泰华洋全亿健康 OA 平台协议适配器。

本模块负责江苏恒泰华洋医药有限公司在全亿健康 OA 系统中的 RSA 登录会话建立。
"""

# 导入 Base64 编解码模块。
import base64

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

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
        self.ph.section("江苏恒泰华洋登录", self.ph.kv("商业", self.company_name, "cyan"))

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
            raise RuntimeError(f"江苏恒泰华洋登录失败：{error_message}")

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


    def query_flow(self, data_type, start_date=None, end_date=None):
        """
        查询指定类型业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 抛出数据接口待接入异常。
        raise NotImplementedError(f"江苏恒泰华洋暂未接入{data_type}查询接口")

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
        :return: 导出结果。
        :rtype: dict
        """

        # 抛出数据接口待接入异常。
        raise NotImplementedError(f"江苏恒泰华洋暂未接入{data_type}导出接口")

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

        # 抛出数据接口待接入异常。
        raise NotImplementedError(f"江苏恒泰华洋暂未接入{data_type}Excel生成接口")
