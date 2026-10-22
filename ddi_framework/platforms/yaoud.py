# -*- coding: utf-8 -*-
"""
药德供应商流向平台协议适配器。

本模块负责药德平台（Salus 商户体系）的协议登录、五类型 BI 报表查询、
分页汇聚和原始字段 Excel 落地。
完整认证链路为三段：AJ 滑块验证码（code/create 取图、code/check 校验、
secretKey AES-ECB pointJson 密文）→ OAuth2 密码授权换令牌
（auth/oauth2/token，Basic merchant 客户端凭证、密码 AES-CFB 加密、
CLIENT-TOM 商户端标记头）→ BI 报表令牌直连
（bi/report/query/{reportId}/list，Bearer 令牌加租户头，
extendParams.supFlowId 承载商业作用域）。
一个商户账号可授权多家商业，各商业以独立供应商流向编号查询同一套报表。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入随机数模块。
import random

# 导入时间模块。
import time

# 导入 UUID 生成模块。
import uuid

# 导入 URL 编码函数。
from urllib.parse import urlencode

# 导入日期与时间跨度类型。
from datetime import date, datetime, timedelta

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入 AES-ECB 加密器。
from ddi_framework.captcha_solver import AesEcbEncryptor


# 定义药德平台网关根地址常量。
API_BASE_URL = "https://api-salus.yaoud.cn"

# 定义药德平台登录页地址常量。
LOGIN_PAGE_URL = "https://web.yaoud.cn/login"

# 定义 OAuth2 令牌接口路径常量。
OAUTH_TOKEN_API_PATH = "/auth/oauth2/token"

# 定义滑块取图接口路径常量。
CAPTCHA_CREATE_API_PATH = "/code/create"

# 定义滑块校验接口路径常量。
CAPTCHA_CHECK_API_PATH = "/code/check"

# 定义 BI 报表查询接口路径模板常量。
BI_REPORT_QUERY_PATH_TEMPLATE = "/bi/report/query/{report_id}/list"

# 定义授权商业列表接口路径常量。
FLOW_INFO_LIST_API_PATH = "/bi/supplierFlowAuthorizedAccount/listFlowInfoByAccount"

# 定义 OAuth 客户端明文凭证常量（前端 window.btoa 同源口径）。
OAUTH_BASIC_PLAIN_CREDENTIALS = "merchant:dwkqwpsxfzwssqfiksxd"

# 定义登录密码 AES-CFB 加密密钥常量（前端登录加密同款，密钥兼作初始向量）。
PASSWORD_AES_KEY = "PITWDjRNQCQ4xUev"

# 定义滑块验证码类型常量。
SLIDE_CAPTCHA_TYPE = "blockPuzzle"

# 定义商户端标记请求头取值常量（前端拦截器 CLIENT-TOM 固定取值）。
CLIENT_TOM_HEADER_VALUE = "Y"


# 定义药德供应商流向平台协议适配器。
class YaoudPlatform(BasePlatform):

    """
    药德供应商流向平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 药德平台适配器实例。
    :rtype: YaoudPlatform
    """

    # 定义平台支持的接入数据类型。
    SUPPORTED_TYPES = ["配送流向", "购进流向", "纯销流向", "库存", "报损流向"]

    # 定义按日期区间查询的流向类数据类型清单。
    FLOW_TYPES = ["配送流向", "购进流向", "纯销流向", "报损流向"]

    # 定义数据类型到 BI 报表编号的映射。
    REPORT_IDS = {
        "配送流向": "253",
        "购进流向": "252",
        "纯销流向": "251",
        "库存": "247",
        "报损流向": "254",
    }

    # 定义流向类数据类型的日期条件字段映射。
    DATE_CONDITION_FIELDS = {
        "购进流向": "入库日期|范围查询",
        "配送流向": "配送日期|范围查询",
        "纯销流向": "销售日期|范围查询",
    }

    # 定义库存快照日期条件字段常量。
    INVENTORY_CONDITION_FIELD = "inventoryTime"

    # 定义分页大小。
    PAGE_SIZE = 1000

    # 定义分页安全上限页数。
    MAX_PAGES = 200

    # 定义滑块验证码最大尝试轮数。
    MAX_LOGIN_ATTEMPTS = 6

    # 定义库存快照空数据回溯天数。
    INVENTORY_WALKBACK_DAYS = 7

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化药德平台适配器。

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

        # 保存平台网关根地址。
        self.api_base_url = str(account.get("站点根地址", API_BASE_URL)).rstrip("/")

        # 保存登录页地址。
        self.login_page_url = str(account.get("登录页", LOGIN_PAGE_URL))

        # 保存商业作用域的供应商流向编号。
        self.supplier_flow_id = str(account.get("供应商流向编号", "")).strip()

        # 初始化带 Cookie 管理的协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 初始化滑块验证码识别器。
        self.captcha_solver = CaptchaSolver()

        # 生成滑块客户端唯一标识。
        self.slider_client_uid = f"slider-{uuid.uuid4()}"

        # 初始化登录状态标记。
        self.logged_in = False

        # 初始化 OAuth2 访问令牌。
        self.access_token = ""

        # 初始化商户租户编号。
        self.tenant_id = ""

        # 计算 OAuth 客户端 Basic 凭证。
        self.oauth_basic_credentials = "Basic " + base64.b64encode(OAUTH_BASIC_PLAIN_CREDENTIALS.encode("utf-8")).decode("ascii")

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
            raise NotImplementedError(f"药德平台暂未接入: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 仅流向类按日期区间查询，库存按快照单日回溯、报损按全量拉取。
        return data_type in ("配送流向", "购进流向", "纯销流向")

    # 定义登录密码加密方法。
    def encrypt_password(self, plain_password):

        """
        按平台前端同款 AES-CFB 无填充口径加密登录密码。

        :param plain_password: 明文密码。
        :type plain_password: str
        :return: Base64 密文。
        :rtype: str
        """

        # 导入密码学对称加密模块。
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        # 编码十六字节密钥（密钥兼作初始向量）。
        key_bytes = PASSWORD_AES_KEY.encode("utf-8")

        # 构建 AES-CFB-128 无填充加密器。
        encryptor = Cipher(algorithms.AES(key_bytes), modes.CFB(key_bytes)).encryptor()

        # 按 Latin-1 口径编码明文并执行加密。
        cipher_bytes = encryptor.update(plain_password.encode("latin-1"))

        # 返回 Base64 密文。
        return base64.b64encode(cipher_bytes).decode("ascii")

    # 定义公共请求头构建方法。
    def build_common_headers(self):

        """
        构建全平台统一的浏览器指纹请求头。

        :return: 公共请求头字典。
        :rtype: dict
        """

        # 组装公共请求头字典。
        return {
            "User-Agent": self.http.user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": "https://web.yaoud.cn",
            "Referer": "https://web.yaoud.cn/",
            "CLIENT-TOM": CLIENT_TOM_HEADER_VALUE,
        }

    # 定义认证请求头构建方法。
    def build_auth_headers(self):

        """
        构建携带访问令牌与租户标识的认证请求头。

        :return: 认证请求头字典。
        :rtype: dict
        """

        # 复制公共请求头。
        headers = self.build_common_headers()

        # 写入 Bearer 访问令牌。
        headers["Authorization"] = f"Bearer {self.access_token}"

        # 写入商户租户编号。
        headers["TENANT-ID"] = self.tenant_id or "1"

        # 写入 JSON 内容类型声明。
        headers["Content-Type"] = "application/json"

        # 返回认证请求头。
        return headers

    # 定义滑块点位文本构建方法。
    def build_point_json(self, move_distance):

        """
        构建滑块点位 JSON 文本。

        :param move_distance: 滑块横向移动距离。
        :type move_distance: float
        :return: 紧凑点位 JSON 文本。
        :rtype: str
        """

        # 转换横向距离为浏览器数字格式。
        x_value = int(move_distance) if float(move_distance).is_integer() else move_distance

        # 返回紧凑 JSON 文本。
        return json.dumps({"x": x_value, "y": 5}, ensure_ascii=False, separators=(",", ":"))

    # 定义滑块校验参数与登录密文构建方法。
    def build_slide_check_request(self, captcha_payload, move_distance):

        """
        依据取图上下文与距离候选构建校验请求体和登录二次密文。

        :param captcha_payload: 取图上下文。
        :type captcha_payload: dict
        :param move_distance: 滑块横向移动距离。
        :type move_distance: float
        :return: 校验查询串与登录二次校验密文元组。
        :rtype: tuple[str, str]
        """

        # 构建点位 JSON 文本。
        point_json = self.build_point_json(move_distance)

        # 按取图返回的 secretKey 加密点位。
        encrypted_point = AesEcbEncryptor.encrypt_to_base64(point_json, captcha_payload["secretKey"])

        # 拼接登录二次校验明文。
        verification_plain = f"{captcha_payload['token']}---{point_json}"

        # 加密登录二次校验密文。
        captcha_verification = AesEcbEncryptor.encrypt_to_base64(verification_plain, captcha_payload["secretKey"])

        # 构建校验查询串。
        check_query = urlencode({
            "captchaType": SLIDE_CAPTCHA_TYPE,
            "pointJson": encrypted_point,
            "token": captcha_payload["token"],
            "clientUid": self.slider_client_uid,
            "ts": int(time.time() * 1000),
        })

        # 返回校验查询串与登录密文。
        return check_query, captcha_verification

    # 定义滑块取图方法。
    def fetch_captcha_payload(self):

        """
        请求滑块取图接口并解析验证码上下文。

        :return: 取图上下文。
        :rtype: dict
        """

        # 构建取图查询串。
        query_string = urlencode({"captchaType": SLIDE_CAPTCHA_TYPE, "clientUid": self.slider_client_uid, "ts": int(time.time() * 1000)})

        # 发送取图请求。
        result = self.http.request("GET", f"{self.api_base_url}{CAPTCHA_CREATE_API_PATH}?{query_string}", headers=self.build_common_headers())

        # 解析取图响应。
        response_data = self.http.decode_json(result)

        # 读取业务数据层。
        data_block = response_data.get("data") or {}

        # 校验业务响应码。
        if str(data_block.get("repCode")) != "0000":

            # 抛出取图失败异常。
            raise RuntimeError(f"{self.company_name} 滑块取图失败：{json.dumps(response_data, ensure_ascii=False)[:200]}")

        # 读取验证码业务数据。
        rep_data = data_block.get("repData") or {}

        # 返回解算所需的验证码上下文。
        return {
            "token": rep_data["token"],
            "secretKey": rep_data["secretKey"],
            "originalImage": base64.b64decode(rep_data["originalImageBase64"]),
            "jigsawImage": base64.b64decode(rep_data["jigsawImageBase64"]),
        }

    # 定义滑块校验提交方法。
    def submit_slide_check(self, check_query):

        """
        提交滑块校验请求并返回业务响应码。

        :param check_query: 校验查询串。
        :type check_query: str
        :return: 校验响应字典。
        :rtype: dict
        """

        # 发送校验请求（平台口径为参数入查询串、空 JSON 体）。
        result = self.http.request("POST", f"{self.api_base_url}{CAPTCHA_CHECK_API_PATH}?{check_query}", headers=self.build_common_headers(), data=json.dumps({}).encode("utf-8"))

        # 解析校验响应。
        return self.http.decode_json(result)

    # 定义 OAuth2 令牌请求方法。
    def request_access_token(self, captcha_verification):

        """
        提交 OAuth2 密码授权请求换取访问令牌。

        :param captcha_verification: 滑块二次校验密文。
        :type captcha_verification: str
        :return: 令牌响应字典。
        :rtype: dict
        """

        # 加密登录密码。
        encrypted_password = self.encrypt_password(self.clean_login_password())

        # 构建令牌查询串。
        query_string = urlencode({
            "username": self.clean_login_name(),
            "randomStr": SLIDE_CAPTCHA_TYPE,
            "code": captcha_verification,
            "grant_type": "password",
            "scope": "server",
        })

        # 构建令牌请求头。
        headers = self.build_common_headers()

        # 写入客户端 Basic 凭证与表单类型声明。
        headers["Authorization"] = self.oauth_basic_credentials

        # 写入表单内容类型。
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        # 发送令牌请求。
        result = self.http.request("POST", f"{self.api_base_url}{OAUTH_TOKEN_API_PATH}?{query_string}", headers=headers, data=urlencode({"password": encrypted_password}).encode("utf-8"))

        # 解析令牌响应。
        return self.http.decode_json(result)

    # 定义滑块验证码校验主方法。
    def solve_slide_captcha(self, max_retries=6):

        """
        完成药德滑块验证码取图、解算与校验。

        :param max_retries: 最大验证码刷新轮数。
        :type max_retries: int
        :return: 正式登录所需的二次校验密文。
        :rtype: str
        """

        # 初始化最后一次失败原因。
        last_error = ""

        # 循环刷新验证码并尝试校验。
        for retry_index in range(max_retries):

            # 打印验证码尝试日志。
            self.ph.info(self.ph.kv("滑块验证码尝试", f"第 {retry_index + 1}/{max_retries} 轮", "cyan"))

            # 循环内取图并逐候选校验。
            try:

                # 获取验证码上下文。
                captcha_payload = self.fetch_captcha_payload()

                # 识别滑块横向移动距离候选。
                move_distances = self.captcha_solver.solve_slide_distance_candidates(captcha_payload["originalImage"], captcha_payload["jigsawImage"])

                # 打印滑块距离日志。
                self.ph.info(self.ph.kv("滑块距离识别完成", ", ".join([f"x={move_distance}" for move_distance in move_distances]), "cyan"))

                # 遍历滑块距离候选值。
                for distance_candidate in move_distances:

                    # 构建校验查询串与登录密文。
                    check_query, captcha_verification = self.build_slide_check_request(captcha_payload, distance_candidate)

                    # 提交滑块校验。
                    check_result = self.submit_slide_check(check_query)

                    # 读取校验业务码。
                    check_block = check_result.get("data") or {}

                    # 校验通过时返回登录密文。
                    if str(check_block.get("repCode")) == "0000":

                        # 打印校验成功日志。
                        self.ph.success("滑块验证码校验通过")

                        # 返回登录二次校验密文。
                        return captcha_verification

                    # 记录失败原因。
                    last_error = str((check_block.get("repMsg")) or check_result)

                    # 打印候选未通过日志。
                    self.ph.warning(self.ph.kv("滑块候选未通过", f"x={distance_candidate}", "yellow"))

            # 捕获本轮识别与校验异常。
            except Exception as error:

                # 记录当前轮异常。
                last_error = str(error)

                # 打印异常日志。
                self.ph.warning("滑块验证码识别未通过，准备刷新验证码")

            # 末轮失败后跳过等待。
            if retry_index >= max_retries - 1:

                # 跳过末轮等待。
                continue

            # 计算失败后的随机等待秒数。
            delay_seconds = random.uniform(2.2, 4.4)

            # 执行随机等待。
            time.sleep(delay_seconds)

        # 抛出滑块校验失败异常。
        raise RuntimeError(f"{self.company_name} 滑块验证码校验失败：{last_error}")

    # 定义授权商业清单记录方法。
    def log_authorized_flows(self):

        """
        读取并打印当前账号的授权商业清单。

        :return: None。
        :rtype: None
        """

        # 登录后的商业清单读取失败不阻断主流程。
        try:

            # 请求授权商业列表接口。
            result = self.http.request("POST", f"{self.api_base_url}{FLOW_INFO_LIST_API_PATH}", headers=self.build_auth_headers(), data=json.dumps({"account": self.clean_login_name(), "entName": ""}).encode("utf-8"))

            # 解析商业列表响应。
            response_data = self.http.decode_json(result)

            # 读取商业条目列表。
            flow_items = response_data.get("data") or []

            # 遍历商业条目打印授权窗口。
            for flow_item in flow_items:

                # 打印单条商业授权信息。
                self.ph.info(self.ph.join(self.ph.kv("授权商业", str(flow_item.get("enterpriseName") or ""), "cyan"), self.ph.kv("流向编号", str(flow_item.get("id") or ""), "cyan"), self.ph.kv("授权窗口", str(flow_item.get("selectTimeRange") or ""), "cyan")))

        # 捕获商业清单读取异常。
        except Exception as error:

            # 打印清单读取失败警告。
            self.ph.warning(self.ph.kv("授权商业清单读取失败", str(error)[:80], "yellow"))

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

    # 定义平台登录方法。
    def login(self):

        """
        执行药德平台协议登录。

        :return: 登录结果字典。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("药德登录", self.ph.join(self.ph.kv("商业", self.company_name, "cyan"), self.ph.kv("流向编号", self.supplier_flow_id or "-", "cyan")))

        # 打印登录配置日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("密码长度", len(self.clean_login_password()), "cyan"), self.ph.kv("密码指纹", self.mask_secret(self.clean_login_password()), "yellow")))

        # 获取滑块二次校验密文。
        captcha_verification = self.solve_slide_captcha(self.MAX_LOGIN_ATTEMPTS)

        # 提交正式令牌请求。
        token_result = self.request_access_token(captcha_verification)

        # 读取访问令牌。
        access_token = str(token_result.get("access_token") or token_result.get("accessToken") or "")

        # 校验令牌获取结果。
        if not access_token:

            # 抛出正式登录失败异常。
            raise RuntimeError(f"{self.company_name} 药德正式登录失败：{token_result.get('msg') or token_result}")

        # 保存访问令牌。
        self.access_token = access_token

        # 保存商户租户编号。
        self.tenant_id = str(token_result.get("tenantId") or "1")

        # 置位登录状态标记。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("正式登录成功", self.clean_login_name(), "green"), self.ph.kv("租户编号", self.tenant_id, "cyan")))

        # 记录授权商业清单。
        self.log_authorized_flows()

        # 返回登录结果。
        return {"access_token": self.access_token, "tenantId": self.tenant_id}

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
        重置登录态以供认证失败后重建会话。

        :return: None。
        :rtype: None
        """

        # 清空访问令牌。
        self.access_token = ""

        # 置位未登录标记。
        self.logged_in = False

    # 定义流向类查询条件构建方法。
    def build_conditions(self, data_type, start_date, end_date):

        """
        构建指定数据类型的查询条件列表。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询条件列表。
        :rtype: list[dict]
        """

        # 判断当前类型为流向类。
        if data_type in self.DATE_CONDITION_FIELDS:

            # 返回日期区间条件。
            return [{"field": self.DATE_CONDITION_FIELDS[data_type], "rule": "between", "val": [start_date, end_date]}]

        # 报损报表未暴露日期条件，按全量拉取。
        return []

    # 定义库存快照查询条件构建方法。
    def build_inventory_conditions(self, snapshot_date):

        """
        构建库存快照单日查询条件列表。

        :param snapshot_date: 快照日期。
        :type snapshot_date: str
        :return: 查询条件列表。
        :rtype: list[dict]
        """

        # 返回库存报表的单日等于条件组。
        return [
            {"field": self.INVENTORY_CONDITION_FIELD, "rule": "eq", "val": snapshot_date},
            {"field": f"范围查询|{self.INVENTORY_CONDITION_FIELD}", "rule": "eq", "val": snapshot_date},
        ]

    # 定义查询负载构建方法。
    def build_query_payload(self, data_type, conditions, page_number):

        """
        构建 BI 报表查询负载。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param conditions: 查询条件列表。
        :type conditions: list[dict]
        :param page_number: 页码。
        :type page_number: int
        :return: 查询负载字典。
        :rtype: dict
        """

        # 组装查询负载字典。
        return {
            "current": page_number,
            "size": self.PAGE_SIZE,
            "reportId": self.REPORT_IDS[data_type],
            "conditions": conditions,
            "extendParams": {"supFlowId": self.supplier_flow_id},
            "reportSource": 1,
        }

    # 定义单页查询方法。
    def query_one_page(self, data_type, conditions, page_number, allow_relogin=True):

        """
        查询指定类型与页码的数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param conditions: 查询条件列表。
        :type conditions: list[dict]
        :param page_number: 页码。
        :type page_number: int
        :param allow_relogin: 认证失败时是否允许重建会话重试一次。
        :type allow_relogin: bool
        :return: 当前页数据行。
        :rtype: list[dict]
        """

        # 构建查询负载。
        payload = self.build_query_payload(data_type, conditions, page_number)

        # 发送报表查询请求（允许读取 HTTP 错误正文以识别认证失效）。
        result = self.http.request("POST", f"{self.api_base_url}{BI_REPORT_QUERY_PATH_TEMPLATE.format(report_id=self.REPORT_IDS[data_type])}", headers=self.build_auth_headers(), data=json.dumps(payload).encode("utf-8"), timeout=300, allow_http_error=True)

        # 判断响应为网关认证失效。
        if result.status_code in (401, 403):

            # 判断允许重建会话。
            if allow_relogin:

                # 打印认证失效日志。
                self.ph.warning("访问令牌已失效，重建会话后重试当前页")

                # 重置登录态并重新登录。
                self.reset_login()

                # 执行重新登录。
                self.ensure_login()

                # 递归重试当前页且不再二次重建。
                return self.query_one_page(data_type, conditions, page_number, allow_relogin=False)

            # 抛出认证失效异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询认证失效：HTTP {result.status}")

        # 解析查询响应。
        response_data = self.http.decode_json(result)

        # 校验业务响应码。
        if response_data.get("code") != 0:

            # 抛出查询响应异常并携带平台消息。
            raise RuntimeError(f"{data_type} 查询响应异常 code={response_data.get('code')} msg={response_data.get('msg') or response_data}")

        # 读取业务数据块。
        data_block = response_data.get("data") or {}

        # 返回当前页数据行。
        return data_block.get("records") or []

    # 定义多页汇聚查询方法。
    def query_pages(self, data_type, conditions):

        """
        按空页终止口径汇聚指定类型的全量数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param conditions: 查询条件列表。
        :type conditions: list[dict]
        :return: 全量数据行。
        :rtype: list[dict]
        """

        # 初始化累计数据行。
        all_rows = []

        # 遍历分页页码。
        for page_number in range(1, self.MAX_PAGES + 1):

            # 查询当前页数据行。
            current_rows = self.query_one_page(data_type, conditions, page_number)

            # 判断当前页已无数据。
            if not current_rows:

                # 结束分页遍历。
                break

            # 累加当前页数据行。
            all_rows.extend(current_rows)

            # 打印当前页完成日志。
            self.ph.success(self.ph.join(self.ph.kv(f"{data_type} 当前页解析完成", f"{len(current_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan")))

            # 分页请求之间保持轻量随机间隔。
            time.sleep(random.uniform(0.2, 0.5))

        # 返回全量数据行。
        return all_rows

    # 定义库存快照回溯日期解析方法。
    def resolve_inventory_snapshot_base(self, end_date):

        """
        解析库存快照回溯的起始日期。

        :param end_date: 任务结束日期。
        :type end_date: str | None
        :return: 快照回溯起始日期。
        :rtype: str
        """

        # 判断任务已提供结束日期。
        if end_date:

            # 返回任务结束日期。
            return end_date

        # 返回当前日期作为快照基点。
        return date.today().strftime("%Y-%m-%d")

    # 定义数据查询方法。
    def query_data(self, data_type, start_date=None, end_date=None):

        """
        查询药德平台指定类型全量数据并汇聚原始字段。

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

        # 初始化快照日期记录。
        snapshot_date = ""

        # 判断当前类型为库存快照。
        if data_type == "库存":

            # 解析快照回溯基点日期。
            base_date_text = self.resolve_inventory_snapshot_base(end_date)

            # 转换基点日期对象。
            base_date_value = datetime.strptime(base_date_text, "%Y-%m-%d").date()

            # 遍历回溯天数窗口。
            for offset in range(self.INVENTORY_WALKBACK_DAYS):

                # 计算当前回溯日期。
                candidate_date = (base_date_value - timedelta(days=offset)).strftime("%Y-%m-%d")

                # 查询当前快照日期的全量数据行。
                all_rows = self.query_pages(data_type, self.build_inventory_conditions(candidate_date))

                # 判断当前快照日期已有数据。
                if all_rows:

                    # 记录生效快照日期。
                    snapshot_date = candidate_date

                    # 打印快照命中日志。
                    self.ph.success(self.ph.kv(f"{data_type} 快照命中日期", candidate_date, "green"))

                    # 结束回溯遍历。
                    break

                # 打印空快照回溯日志。
                self.ph.warning(self.ph.kv(f"{data_type} 快照无数据，回溯", candidate_date, "yellow"))

            # 判断回溯窗口全部为空。
            else:

                # 初始化空数据行。
                all_rows = []

                # 打印回溯耗尽警告。
                self.ph.warning(self.ph.kv(f"{data_type} 快照回溯{self.INVENTORY_WALKBACK_DAYS}天均无数据", base_date_text, "yellow"))

        # 判断当前类型为流向类。
        elif data_type in self.DATE_CONDITION_FIELDS:

            # 校验查询开始日期。
            if not start_date:

                # 抛出查询开始日期缺失异常。
                raise ValueError(f"查询{data_type}必须提供 start_date")

            # 校验查询结束日期。
            if not end_date:

                # 抛出查询结束日期缺失异常。
                raise ValueError(f"查询{data_type}必须提供 end_date")

            # 查询日期区间全量数据行。
            all_rows = self.query_pages(data_type, self.build_conditions(data_type, start_date, end_date))

        # 其余类型按全量口径拉取。
        else:

            # 查询全量数据行。
            all_rows = self.query_pages(data_type, [])

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
        return {"rows": all_rows, "headers": list(columns.keys()), "snapshot_date": snapshot_date}

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询药德平台流向数据。

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
        查询药德平台数据并生成原始字段 Excel。

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
        导出药德平台数据。

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
