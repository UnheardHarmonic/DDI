# -*- coding: utf-8 -*-
"""
重庆医药流向系统协议适配器。

本模块负责重庆和平药房供应商体系（重庆医药流向系统）的协议登录与登录态验证。
登录协议已全量实证：BladeX SSO（blade/doLogin，密码 DES-ECB 加密 key=test1234，
验证码为失败后启用的双状态机制——首轮无码、失败后经 Captcha-Key/Captcha-Code 请求头
携带图形验证码，图形码经 ddddocr 识别）。
按董事长给定凭据实测，服务端在验证码层通过后于凭据层拒绝（疑似账号连败锁定或密码变更），
故本模块数据查询暂不开放，待凭据验证通过后按五类型端点映射开启。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入操作系统路径模块。
import os

# 导入类型标注对象。
from typing import Any, Dict, Optional

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义平台站点地址常量。
SSO_BASE_URL = "https://cqp-sxy-sso.cq-p.com.cn"

# 定义数据平台站点地址常量。
DATA_BASE_URL = "https://new-data-flow.cq-p.com.cn:8080"

# 定义登录接口路径常量。
LOGIN_API_PATH = "/api/cqp-sxy-sso-server/blade/doLogin"

# 定义验证码接口路径常量。
CAPTCHA_API_PATH = "/api/blade-auth/oauth/captcha"

# 定义密码加密密钥常量（前端 cryptoKey）。
DES_KEY = b"test1234"


# 定义重庆医药流向系统协议适配器。
class CqhpPlatform(BasePlatform):

    """
    重庆医药流向系统协议适配器（仅登录）。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 重庆和平平台适配器实例。
    :rtype: CqhpPlatform
    """

    # 定义数据类型到查询端点的映射（凭据验证通过后开放）。
    DATA_PATHS = {
        "纯销流向": "/server/retailHpTarget/page",
        "配送流向": "/server/headOfficeSalesHpTarget/page",
        "购进流向": "/server/headquartersWarehousingHpTarget/page",
        "库存": "/server/factInventoryflowHp/page",
        "报损流向": "/server/factIncomestatementPf/pageFactIncomestatementPf",
    }

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化重庆和平平台适配器。

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

        # 保存平台站点地址。
        self.sso_base_url = str(account.get("认证站点地址", SSO_BASE_URL)).rstrip("/")

        # 保存数据平台站点地址。
        self.data_base_url = str(account.get("数据站点地址", DATA_BASE_URL)).rstrip("/")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", self.sso_base_url + LOGIN_API_PATH)

        # 保存验证码接口地址。
        self.captcha_api_url = account.get("验证码接口", self.sso_base_url + CAPTCHA_API_PATH)

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", self.sso_base_url + "/#/login")

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.sso_base_url)

        # 初始化验证码识别器。
        self.captcha_solver = CaptchaSolver()

        # 初始化登录态标记。
        self.logged_in = False

        # 初始化访问令牌。
        self.access_token = ""

        # 初始化数据平台用户编号。
        self.data_user_id = ""

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验平台数据类型（凭据验证通过前数据类型均未开放）。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 按凭据阻塞现状抛出未接入异常。
        raise NotImplementedError(f"重庆和平平台数据查询暂未开放（待凭据验证通过后开启）: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 五类型端点均按日期区间查询，统一返回True。
        return True

    # 定义密码加密方法。
    def encrypt_password(self, plain_password):

        """
        按平台前端同款 DES-ECB-PKCS5 加密密码。

        :param plain_password: 明文密码。
        :type plain_password: str
        :return: Base64 密文。
        :rtype: str
        """

        # 导入密码学对称加密模块。
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        # 导入填充模块。
        from cryptography.hazmat.primitives.padding import PKCS7

        # 屏蔽三重DES别名弃用警告。
        import warnings

        # 过滤弃用警告。
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # 按_PKCS5/7 规范填充明文。
        padder = PKCS7(64).padder()

        # 执行填充。
        padded = padder.update(plain_password.encode("utf-8")) + padder.finalize()

        # 构建单倍 DES 的 ECB 加密器（8 字节密钥等价单倍 DES）。
        encryptor = Cipher(algorithms.TripleDES(DES_KEY), modes.ECB()).encryptor()

        # 加密并输出 Base64 密文。
        return base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode("utf-8")

    # 定义平台登录方法。
    def login(self):

        """
        执行重庆医药流向系统协议登录（验证码双状态自动处理）。

        首轮以无验证码形态提交（平台首次登录不要求验证码）；
        服务端拒绝后自动拉取图形验证码识别并携带 Captcha-Key/Captcha-Code
        请求头重试，覆盖失败后需要验证码的第二状态。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("重庆和平登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 初始化最后一次错误信息。
        last_message = ""

        # 循环验证码重试（首轮无验证码，后续带识别验证码）。
        for attempt_index in range(1, 9):

            # 构建基础登录参数（首轮无验证码，验证码字段留空）。
            login_params = {
                "tenantId": str(self.account.get("租户ID") or self.clean_login_name()),
                "username": self.clean_login_name(),
                "password": self.encrypt_password(self.clean_login_password()),
                "grant_type": "password",
                "scope": "all",
                "type": "account",
                "code": "",
                "key": "",
                "idmsyscode": "",
            }

            # 初始化登录请求头。
            login_headers = {"Tenant-Id": login_params["tenantId"]}

            # 判断是否进入验证码状态（首轮之后的重试均携带验证码）。
            if attempt_index > 1:

                # 拉取会话绑定的图形验证码。
                status_code, captcha_text = self.http.request("GET", self.captcha_api_url, headers=self.build_page_headers(), timeout=30)

                # 解析验证码响应。
                captcha_data = (json.loads(captcha_text).get("data") or {})

                # 读取验证码键值。
                captcha_key = str(captcha_data.get("key") or "")

                # 读取 Base64 图像数据并剥离数据头。
                image_b64 = str(captcha_data.get("image") or "").split(",")[-1]

                # 补齐 Base64 填充。
                image_b64 += "=" * (-len(image_b64) % 4)

                # 解码图像字节流。
                image_bytes = base64.b64decode(image_b64)

                # 优先数字字母字符集识别，失败回退通用识别。
                captcha_code = (self.captcha_solver.solve_raw_text_image_with_ranges(image_bytes, "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") or self.captcha_solver.solve_text_image(image_bytes, min_length=4))

                # 判断识别结果是否有效。
                if not captcha_code or len(captcha_code) < 4:

                    # 记录识别失败并换码重试。
                    self.ph.warning(self.ph.kv(f"验证码识别未通过（第 {attempt_index} 次）", f"识别值 {captcha_code!r}", "yellow"))

                    # 进入下一次尝试。
                    continue

                # 写入验证码参数。
                login_params["code"] = captcha_code

                # 写入验证码键。
                login_params["key"] = captcha_key

                # 追加验证码请求头（平台以请求头承载验证码）。
                login_headers["Captcha-Key"] = captcha_key

                # 追加验证码值请求头。
                login_headers["Captcha-Code"] = captcha_code

            # 拼接查询串承载登录参数（平台以查询串传参、POST 空体）。
            query_string = urlencode(login_params)

            # 提交登录请求。
            result = self.http.request("POST", self.login_api_url + "?" + query_string, headers=login_headers, data=b"", timeout=60, allow_http_error=True)

            # 读取状态码与响应文本。
            status_code = result.status_code

            # 解码响应体。
            result_text = result.body.decode("utf-8", errors="replace")

            # 解析登录响应。
            data = json.loads(result_text)

            # 判断登录成功（平台约定 code=0）。
            if int(data.get("code", -1)) == 0:

                # 读取业务数据块。
                login_data = data.get("data") or {}

                # 提取访问令牌。
                self.access_token = str(login_data.get("access_token") or "")

                # 提取数据平台用户编号。
                self.data_user_id = str(login_data.get("user_id") or login_data.get("userId") or "")

                # 标记登录态。
                self.logged_in = True

                # 打印登录成功日志。
                self.ph.success(self.ph.join(self.ph.kv("登录成功", f"第 {attempt_index} 次尝试", "green"), self.ph.kv("令牌前缀", self.access_token[:20], "cyan")))

                # 返回登录结果摘要。
                return {"message": "登录成功", "attempts": attempt_index}

            # 读取平台拒绝消息。
            last_message = str(data.get("msg") or f"code={data.get('code')}")

            # 判断消息是否为凭据层拒绝（验证码层已通过的判定依据）。
            if "验证码" not in last_message:

                # 凭据层拒绝时终止重试（换验证码无法解决凭据问题）。
                self.ph.warning(self.ph.kv("凭据层拒绝", last_message, "yellow"))

                # 跳出重试循环。
                break

            # 记录验证码层失败并重试。
            self.ph.warning(self.ph.kv(f"验证码层未通过（第 {attempt_index} 次）", last_message, "yellow"))

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 重庆和平平台登录失败：{last_message}")

    # 定义流向查询方法（待凭据验证后开放）。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询流向数据（未开放）。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 无返回。
        :rtype: list[dict]
        """

        # 校验数据类型并抛出未开放异常。
        self.validate_data_type(data_type)

    # 定义流向导出方法（待凭据验证后开放）。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出流向数据（未开放）。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 无返回。
        :rtype: str
        """

        # 校验数据类型并抛出未开放异常。
        self.validate_data_type(data_type)

    # 定义页面请求头构建方法。
    def build_page_headers(self):

        """
        构建页面访问请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回浏览器页面请求头。
        return {
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "Referer": self.login_page_url,
            "User-Agent": self.http.user_agent(),
        }
