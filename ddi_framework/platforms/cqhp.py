# -*- coding: utf-8 -*-
"""
重庆医药流向系统协议适配器。

本模块负责重庆和平药房供应商体系（重庆医药流向系统）的协议登录、
验证码双状态自动处理、五类型数据查询、分页汇聚和原始字段 Excel 落地。
BladeX SSO（blade/doLogin，密码 DES-ECB 加密 key=test1234）+
JWT Bearer 数据接口（/server/*HpTarget/page 系列分页查询）。
按董事长给定凭据实测，服务端在验证码层通过后于凭据层拒绝
（疑似账号连败锁定或密码变更），待凭据修正后全量通道即可生效。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入时间模块。
import time

# 导入随机数模块。
import random

# 导入表单编码函数。
from urllib.parse import urlencode

# 导入操作系统路径模块。
import os

# 导入时间模块。
import time

# 导入随机数模块。
import random

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义平台 SSO 站点地址常量。
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
    重庆医药流向系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 重庆和平平台适配器实例。
    :rtype: CqhpPlatform
    """

    # 定义平台支持的接入数据类型。
    SUPPORTED_TYPES = ["纯销流向", "配送流向", "购进流向", "库存", "报损流向"]

    # 定义流向类数据类型清单。
    FLOW_TYPES = ["纯销流向", "配送流向", "购进流向", "报损流向"]

    # 定义数据类型到查询端点路径的映射。
    DATA_PATHS = {
        "纯销流向": "/server/retailHpTarget/page",
        "配送流向": "/server/headOfficeSalesHpTarget/page",
        "购进流向": "/server/headquartersWarehousingHpTarget/page",
        "库存": "/server/factInventoryflowHp/page",
        "报损流向": "/server/factIncomestatementPf/pageFactIncomestatementPf",
    }

    # 定义分页大小。
    PAGE_SIZE = 100

    # 定义分页安全上限页数。
    MAX_PAGES = 500

    # 定义登录验证码最大识别尝试次数。
    MAX_LOGIN_ATTEMPTS = 8

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

        # 保存认证平台站点地址。
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
        校验平台数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in self.SUPPORTED_TYPES:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"重庆和平平台暂未接入: {data_type}")

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

        # 按 PKCS5/7 规范填充明文。
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
        for attempt_index in range(1, self.MAX_LOGIN_ATTEMPTS + 1):

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
                captcha_result = self.http.request("GET", self.captcha_api_url, headers=self.build_page_headers(), timeout=30)

                # 解析验证码响应。
                captcha_data = (json.loads(captcha_result.body.decode("utf-8", errors="replace")).get("data") or {})

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

    # 定义构建查询过滤模型方法。
    def build_data_filter(self, data_type, start_date, end_date):

        """
        构建数据查询的过滤模型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 过滤模型字典。
        :rtype: dict
        """

        # 判断当前类型是否为纯销流向（门店零售）。
        if data_type == "纯销流向":

            # 返回纯销过滤模型。
            return {"flag": 0, "outboundStartDate": start_date or "", "outboundEndDate": end_date or "", "returnMoney": None, "returnSales": None, "userId": self.data_user_id}

        # 判断当前类型是否为配送流向（总部销售）。
        if data_type == "配送流向":

            # 返回配送过滤模型。
            return {"outboundStartDate": start_date or "", "outboundEndDate": end_date or "", "flag": 0, "returnMoney": 0, "returnSales": 0, "userId": self.data_user_id}

        # 判断当前类型是否为购进流向。
        if data_type == "购进流向":

            # 返回购进过滤模型。
            return {"goodsId": "", "tradeMark": "", "agentName": "", "commodity": "", "inStcDateBegin": start_date or "", "inStcDateEnd": end_date or "", "userId": self.data_user_id}

        # 判断当前类型是否为报损流向。
        if data_type == "报损流向":

            # 返回报损过滤模型。
            return {"type": "报损", "startTime": start_date or "", "endDate": end_date or "", "userId": self.data_user_id}

        # 库存类型返回空过滤模型（快照查询无日期条件）。
        return {"userId": self.data_user_id}

    # 定义单页查询方法。
    def query_one_page(self, data_type, filter_model, page_number):

        """
        查询重庆医药流向系统单页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param filter_model: 过滤模型字典。
        :type filter_model: dict
        :param page_number: 页码。
        :type page_number: int
        :return: 平台原始分页响应。
        :rtype: dict
        """

        # 构建查询参数（查询串承载分页）。
        page_params = {"currentPage": str(page_number), "pageSize": str(self.PAGE_SIZE)}

        # 构建查询请求体。
        body = json.dumps(filter_model, ensure_ascii=False).encode("utf-8")

        # 构建 AJAX 请求头。
        headers = self.build_data_headers()

        # 打印分页请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", self.DATA_PATHS[data_type], "cyan"), self.ph.kv("currentPage", page_number, "yellow"), self.ph.kv("pageSize", self.PAGE_SIZE, "cyan")))

        # 拼接完整 URL（查询串承载分页参数）。
        url = self.data_base_url + self.DATA_PATHS[data_type] + "?" + urlencode(page_params)

        # 提交查询请求。
        result = self.http.request("POST", url, headers=headers, data=body, timeout=300, allow_http_error=True)

        # 解析查询响应。
        response_data = json.loads(result.body.decode("utf-8", errors="replace"))

        # 返回原始响应。
        return response_data

    # 定义数据查询方法。
    def query_data(self, data_type, start_date=None, end_date=None):

        """
        查询重庆医药流向系统全量数据并汇聚原始字段。

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

        # 构建过滤模型。
        filter_model = self.build_data_filter(data_type, start_date, end_date)

        # 查询第一页数据。
        first_page = self.query_one_page(data_type, filter_model, 1)

        # 读取业务数据块。
        data_block = first_page.get("data") or {}

        # 读取当前页数据行。
        first_rows = data_block.get("records") or []

        # 读取总记录数。
        total_count = int(data_block.get("total") or 0)

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
            page_response = self.query_one_page(data_type, filter_model, page_number)

            # 读取业务数据块。
            page_block = page_response.get("data") or {}

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

            # 分页请求之间保持轻量间隔。
            time.sleep(random.uniform(0.05, 0.15))

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
        查询重庆医药流向系统流向数据。

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
        查询重庆医药流向系统数据并生成原始字段 Excel。

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

        # 构建列映射（原名兜底）。
        columns = {field: field for field in query_result["headers"]}

        # 写入原始字段 Excel。
        self.write_rows_to_excel(query_result["rows"], output_path, columns, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"))

        # 返回 Excel 文件路径。
        return output_path

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出重庆医药流向系统数据。

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

    # 定义数据查询请求头构建方法。
    def build_data_headers(self):

        """
        构建数据查询请求头。

        :return: 请求头字典。
        :rtype: dict
        """

        # 返回数据查询请求头。
        return {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.access_token}",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": self.data_base_url,
            "Referer": self.data_base_url + "/",
            "User-Agent": self.http.user_agent(),
        }

