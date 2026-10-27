# -*- coding: utf-8 -*-
"""
九州通流向平台协议适配器。
"""

# 导入 Base64 编解码模块。
import base64

# 导入随机数模块。
import random

# 导入时间模块。
import time

# 导入操作系统接口模块。
import os

# 导入 JSON 编解码模块。
import json

# 导入日期解析模块。
from datetime import datetime

# 导入 UUID 生成模块。
import uuid

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入验证码处理器。
from ddi_framework import CaptchaSolver

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义九州通流向平台协议适配器。
class JztPlatform(BasePlatform):
    """
    九州通流向平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :return: 九州通平台适配器实例。
    :rtype: JztPlatform
    """

    # 定义九州通适配器初始化方法。
    def __init__(self, company_name, account, printer=None):
        """
        初始化九州通平台适配器。

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
        self.login_page_url = account.get("登录页", "https://flow.jztit.com/user/login.html")

        # 保存平台根地址。
        self.base_url = self.login_page_url.split("/user/", 1)[0]

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化验证码处理器。
        self.captcha_solver = CaptchaSolver()

        # 生成滑块客户端标识。
        self.slider_client_uid = f"slider-{uuid.uuid4()}"

        # 保存查询接口路径。
        self.query_api_path = account.get("查询接口", "/_yvanui/query")

        # 保存日志接口路径。
        self.execute_api_path = account.get("日志接口", "/_yvanui/execute")

        # 保存导出接口路径。
        self.export_api_path = account.get("导出接口", "/api/flowquery/export")

    # 定义九州通登录方法。
    def login(self):
        """
        执行九州通协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("九州通登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 请求登录页并初始化 Cookie。
        self.http.get(self.login_page_url)

        # 打印 Cookie 初始化日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 打印登录配置检查日志。
        self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("密码长度", len(self.clean_login_password()), "cyan"), self.ph.kv("密码指纹", self.mask_secret(self.clean_login_password()), "yellow")))

        # 提交账号密码前置校验。
        check_result = self.check_account()

        # 校验账号密码前置校验结果。
        if not check_result.get("success"):
            raise RuntimeError(f"{self.company_name} 账号密码前置校验失败：{check_result.get('msg') or check_result}")

        # 打印账号校验成功日志。
        self.ph.success("账号密码前置校验通过")

        # 获取滑块验证码二次校验密文。
        captcha_verification = self.solve_slide_captcha()

        # 提交正式登录请求。
        login_result = self.submit_login(captcha_verification)

        # 校验正式登录结果。
        if not login_result.get("success"):
            raise RuntimeError(f"{self.company_name} 正式登录失败：{login_result.get('msg') or login_result}")

        # 打印正式登录成功日志。
        self.ph.success(f"正式登录成功: {login_result.get('msg', '登录成功')}")

        # 返回登录结果。
        return login_result

    # 定义账号密码前置校验方法。
    def check_account(self):
        """
        提交账号密码前置校验。

        :return: 前置校验接口响应数据。
        :rtype: dict
        """

        # 构建前置校验表单。
        payload = {"loginName": self.clean_login_name(), "loginPwd": self.clean_login_password(), "rememberMe": "false", "type": "user"}

        # 打印前置校验日志。
        self.ph.info("提交账号密码前置校验: /user/login/check")

        # 发送前置校验请求。
        result = self.http.post_form(urljoin(self.base_url, "/user/login/check"), payload, self.login_page_url)

        # 返回 JSON 响应数据。
        return self.http.decode_json(result)

    # 定义滑块验证码校验方法。
    def solve_slide_captcha(self, max_retries=8):
        """
        完成九州通滑块验证码校验。

        :param max_retries: 最大验证码刷新次数。
        :type max_retries: int
        :return: 正式登录接口所需的验证码密文。
        :rtype: str
        """

        # 初始化最后一次失败原因。
        last_error = ""

        # 循环刷新验证码并尝试校验。
        for retry_index in range(max_retries):
            try:
                # 打印验证码尝试日志。
                self.ph.info(self.ph.kv("滑块验证码尝试", f"第 {retry_index + 1}/{max_retries} 次", "cyan"))

                # 获取验证码上下文。
                captcha_payload = self.get_slide_captcha()

                # 识别滑块横向移动距离候选。
                move_distances = self.captcha_solver.solve_slide_distance_candidates(captcha_payload["originalImage"], captcha_payload["jigsawImage"])

                # 打印滑块距离日志。
                self.ph.info(self.ph.kv("滑块距离识别完成", ", ".join([f"x={move_distance}" for move_distance in move_distances]), "cyan"))

                # 构建滑块距离候选列表。
                distance_candidates = self.build_slide_distance_candidates(move_distances)

                # 遍历滑块距离候选值。
                for distance_candidate in distance_candidates:

                    # 构建验证码校验请求体与登录参数。
                    check_payload, captcha_verification = self.captcha_solver.build_anji_slide_payload(captcha_payload, distance_candidate, self.slider_client_uid)

                    # 打印验证码校验日志。
                    self.ph.info(self.ph.kv("提交滑块验证码校验", f"x={distance_candidate}", "cyan"))

                    # 发送验证码校验请求。
                    result = self.http.post_json(urljoin(self.base_url, "/captcha/check"), check_payload, self.login_page_url)

                    # 解析验证码校验响应。
                    check_result = self.http.decode_json(result)

                    # 返回校验成功的登录参数。
                    if check_result.get("repCode") == "0000":

                        # 打印验证码成功日志。
                        self.ph.success("滑块验证码校验通过")

                        # 返回登录验证码密文。
                        return captcha_verification

                    # 记录失败原因。
                    last_error = str(check_result.get("repMsg") or check_result)

                    # 打印候选距离失败日志。
                    self.ph.warning(self.ph.kv("滑块候选未通过", f"x={distance_candidate}", "yellow"))

                # 打印验证码失败日志。
                self.ph.warning("滑块验证码校验未通过，准备刷新验证码")

            except Exception as error:
                # 记录当前验证码处理异常。
                last_error = str(error)

                # 打印验证码异常日志。
                self.ph.warning("滑块验证码识别未通过，准备刷新验证码")

            # 最后一轮失败后跳过等待。
            if retry_index >= max_retries - 1:
                continue

            # 计算失败后的验证码刷新等待秒数。
            delay_seconds = random.uniform(2.2, 4.4)

            # 打印等待日志。
            self.ph.wait(self.ph.kv("验证码失败后等待，预计", f"{delay_seconds:.1f} 秒", "cyan"))

            # 失败后延迟等待，避免连续请求验证码服务。
            time.sleep(delay_seconds)

        # 抛出验证码失败异常。
        raise RuntimeError(f"{self.company_name} 滑块验证码校验失败：{last_error}")

    # 定义滑块候选距离构建方法。
    def build_slide_distance_candidates(self, move_distances):
        """
        构建滑块验证码候选距离列表。

        :param move_distances: 识别得到的基础横向距离列表。
        :type move_distances: list[float] | float
        :return: 候选横向距离列表。
        :rtype: list[float]
        """

        # 定义候选距离的轻微偏移量。
        offsets = [0, -1, 1, -2, 2, -4, 4, -6, 6, -8, 8]

        # 初始化候选距离列表。
        candidates = []

        # 兼容单个基础距离输入。
        base_distances = move_distances if isinstance(move_distances, list) else [move_distances]

        # 遍历基础距离生成候选。
        for move_distance in base_distances:

            # 遍历偏移量生成候选距离。
            for offset in offsets:

                # 计算候选距离。
                candidate = round(float(move_distance) + float(offset), 1)

                # 跳过越界候选距离。
                if candidate < 0 or candidate > 310:

                    # 进入下一个候选距离。
                    continue

                # 跳过重复候选距离。
                if candidate in candidates:

                    # 进入下一个候选距离。
                    continue

                # 保存候选距离。
                candidates.append(candidate)

        # 返回候选距离列表。
        return candidates

    # 定义滑块验证码获取方法。
    def get_slide_captcha(self):
        """
        获取九州通滑块验证码图片。

        :return: 验证码上下文。
        :rtype: dict
        """

        # 构建验证码图片请求体。
        payload = {"captchaType": "blockPuzzle", "clientUid": self.slider_client_uid, "ts": int(__import__("time").time() * 1000)}

        # 打印验证码获取日志。
        self.ph.info("请求滑块验证码: /captcha/get")

        # 发送验证码图片请求。
        result = self.http.post_json(urljoin(self.base_url, "/captcha/get"), payload, self.login_page_url)

        # 解析验证码图片响应。
        data = self.http.decode_json(result)

        # 校验验证码图片响应编码。
        if data.get("repCode") != "0000":
            raise RuntimeError(f"{self.company_name} 获取滑块验证码失败：{data.get('repMsg') or data}")

        # 读取验证码业务数据。
        rep_data = data.get("repData") or {}

        # 解码背景图片。
        original_image = base64.b64decode(rep_data["originalImageBase64"])

        # 解码拼图图片。
        jigsaw_image = base64.b64decode(rep_data["jigsawImageBase64"])

        # 返回验证码上下文。
        return {"token": rep_data["token"], "secretKey": rep_data["secretKey"], "originalImage": original_image, "jigsawImage": jigsaw_image}

    # 定义正式登录提交方法。
    def submit_login(self, captcha_verification):
        """
        提交九州通正式登录请求。

        :param captcha_verification: 滑块验证码二次校验密文。
        :type captcha_verification: str
        :return: 正式登录接口响应数据。
        :rtype: dict
        """

        # 构建正式登录表单。
        payload = {"loginName": self.clean_login_name(), "loginPwd": self.clean_login_password(), "rememberMe": "false", "type": "user", "captchaVerification": captcha_verification}

        # 打印正式登录日志。
        self.ph.info("提交正式登录请求: /user/login")

        # 发送正式登录请求。
        result = self.http.post_form(urljoin(self.base_url, "/user/login"), payload, self.login_page_url)

        # 返回 JSON 响应数据。
        return self.http.decode_json(result)

    # 定义登录账号清洗方法。
    def clean_login_name(self):
        """
        读取清洗后的登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回去除两端空白后的账号。
        return str(self.account["账号"]).strip()

    # 定义登录密码清洗方法。
    def clean_login_password(self):
        """
        读取清洗后的登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回去除两端空白后的密码。
        return str(self.account["密码"]).strip()

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
            return "<空>"

        # 返回短密码掩码。
        if len(secret_text) <= 2:
            return "*" * len(secret_text)

        # 返回首尾可见的密码掩码。
        return f"{secret_text[0]}***{secret_text[-1]}"

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):
        """
        保存当前登录 Cookie。

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

        # 打印 Cookie 保存日志。
        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):
        """
        导出九州通流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出结果。
        :rtype: dict
        """

        # 校验当前数据类型是否为已接入的配送流向。
        if data_type != "配送流向":
            raise NotImplementedError(f"当前仅接入配送流向，暂未接入: {data_type}")

        # 校验查询开始日期。
        if not start_date:
            raise ValueError("导出配送流向必须提供 start_date")

        # 校验查询结束日期。
        if not end_date:
            raise ValueError("导出配送流向必须提供 end_date")

        # 构建导出文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建导出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建导出路径。
        output_path = os.path.join(output_dir, file_name)

        # 执行配送流向导出。
        return self.export_distribution_flow(start_date, end_date, output_path)

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):
        """
        查询九州通流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果列表。
        :rtype: list[dict]
        """

        # 校验查询开始日期。
        if not start_date:
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验查询结束日期。
        if not end_date:
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 执行指定数据类型查询。
        return self.query_jzt_data(data_type, start_date, end_date)

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):
        """
        查询九州通流向数据并生成 Excel。

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

        # 校验查询开始日期。
        if not start_date:
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验查询结束日期。
        if not end_date:
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 查询指定数据类型全量数据。
        rows = self.query_jzt_data(data_type, start_date, end_date)

        # 合并标准字段与接口原始字段。
        columns = self.build_complete_jzt_columns(data_type, rows)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(rows, output_path, columns, data_type)

        # 打印 Excel 保存日志。
        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义九州通通用分页查询方法。
    def query_jzt_data(self, data_type, start_date, end_date, page_size=100):
        """
        查询九州通指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_size: 每页查询条数。
        :type page_size: int
        :return: 查询结果列表。
        :rtype: list[dict]
        """

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 写入查询日志。
        self.write_flow_log("8", self.build_jzt_log_text(data_type, "查询", start_date, end_date))

        # 初始化查询结果列表。
        all_rows = []

        # 初始化分页偏移量。
        offset = 0

        # 初始化总记录数。
        total_count = None

        # 循环分页查询。
        while True:

            # 构建查询请求体。
            payload = self.build_jzt_query_payload(data_type, start_date, end_date, page_size, offset)

            # 打印当前分页查询日志。
            self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", f"offset={offset}", "cyan"), self.ph.kv("limit", page_size, "cyan")))

            # 发送查询请求。
            result = self.http.post_json(urljoin(self.base_url, self.query_api_path), payload, self.login_page_url)

            # 解析查询响应。
            response_data = self.http.decode_json(result)

            # 校验查询响应。
            if not response_data.get("success"):
                raise RuntimeError(f"{data_type}查询失败：{response_data.get('msg') or response_data}")

            # 读取响应业务数据。
            data_block = response_data.get("data") or {}

            # 读取当前页数据。
            page_rows = data_block.get("data") or []

            # 读取总记录数。
            total_count = data_block.get("totalCount", total_count)

            # 追加当前页数据。
            all_rows.extend(page_rows)

            # 打印分页查询结果。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "cyan")))

            # 判断是否已经查完。
            if total_count is not None and len(all_rows) >= int(total_count):
                break

            # 判断当前页是否为空。
            if not page_rows:
                break

            # 增加分页偏移。
            offset += page_size

            # 分页请求之间保持轻量间隔。
            time.sleep(random.uniform(0.05, 0.15))

        # 验证接口返回记录的业务日期范围。
        self.validate_jzt_date_range(data_type, all_rows, start_date, end_date)

        # 返回全量查询结果。
        return all_rows

    # 定义九州通业务日期范围校验方法。
    def validate_jzt_date_range(self, data_type, rows, start_date, end_date):
        """
        验证九州通查询记录的业务日期与请求范围一致。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 接口返回的原始记录。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 定义各数据类型的业务日期字段。
        date_fields = {
            "配送流向": "FSELLDATE",
            "购进流向": "FBUYDATE",
            "库存": "FSTORAGEDATE",
            "报损流向": "FSELLDATE",
        }

        # 读取当前数据类型的业务日期字段。
        date_field = date_fields[data_type]

        # 初始化业务日期列表。
        business_dates = []

        # 遍历接口返回的全部原始记录。
        for row in rows:

            # 跳过非字典类型的异常记录。
            if not isinstance(row, dict):

                # 继续读取下一条原始记录。
                continue

            # 解析当前记录的业务日期。
            business_date = self.parse_jzt_business_date(row.get(date_field))

            # 跳过未提供或无法解析业务日期的记录。
            if business_date is None:

                # 继续读取下一条原始记录。
                continue

            # 保存当前记录的业务日期。
            business_dates.append(business_date)

        # 跳过没有业务日期的空结果或异常结果。
        if not business_dates:

            # 打印未发现业务日期的提示。
            self.ph.info(self.ph.kv(f"{data_type}业务日期验证", "无可校验业务日期", "cyan"))

            # 结束当前校验流程。
            return

        # 读取当前结果最早业务日期。
        actual_start_date = min(business_dates)

        # 读取当前结果最晚业务日期。
        actual_end_date = max(business_dates)

        # 解析请求开始日期。
        requested_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        # 解析请求结束日期。
        requested_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # 判断当前数据类型是否为库存快照。
        if data_type == "库存":

            # 构建库存快照日期展示文本。
            snapshot_label = f"{actual_start_date:%Y-%m-%d} 至 {actual_end_date:%Y-%m-%d}"

            # 判断平台快照是否晚于请求结束日期。
            if actual_end_date > requested_end_date:

                # 记录平台当前快照并允许库存结果继续导出。
                self.ph.warning(self.ph.join(self.ph.kv("库存使用平台当前快照", snapshot_label, "yellow"), self.ph.kv("请求结束日期", end_date, "cyan")))

            else:

                # 记录落在请求范围内的库存快照。
                self.ph.success(self.ph.join(self.ph.kv("库存快照日期验证通过", snapshot_label, "green"), self.ph.kv("请求结束日期", end_date, "cyan")))

            # 结束库存快照校验流程。
            return

        # 校验流向业务日期未早于请求开始日期。
        if actual_start_date < requested_start_date:

            # 抛出业务日期早于请求范围异常。
            raise RuntimeError(f"{data_type}查询返回业务日期早于请求开始日期：{actual_start_date:%Y-%m-%d} < {start_date}")

        # 校验流向业务日期未晚于请求结束日期。
        if actual_end_date > requested_end_date:

            # 抛出业务日期晚于请求范围异常。
            raise RuntimeError(f"{data_type}查询返回业务日期晚于请求结束日期：{actual_end_date:%Y-%m-%d} > {end_date}")

        # 打印流向业务日期验证结果。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type}业务日期验证通过", f"{actual_start_date:%Y-%m-%d} 至 {actual_end_date:%Y-%m-%d}", "green"), self.ph.kv("请求范围", f"{start_date} 至 {end_date}", "cyan")))

    # 定义九州通业务日期解析方法。
    def parse_jzt_business_date(self, raw_value):
        """
        解析九州通接口返回的业务日期值。

        :param raw_value: 接口返回的原始日期值。
        :type raw_value: object
        :return: 解析后的业务日期。
        :rtype: datetime.date | None
        """

        # 跳过空日期值。
        if raw_value is None or raw_value == "":

            # 返回空日期结果。
            return None

        # 直接处理日期时间对象。
        if isinstance(raw_value, datetime):

            # 返回日期时间对象的日期部分。
            return raw_value.date()

        # 标准化字符串日期分隔符。
        raw_text = str(raw_value).strip().replace("/", "-")

        # 截取标准日期部分。
        date_text = raw_text[:10]

        try:

            # 按标准日期格式解析业务日期。
            return datetime.strptime(date_text, "%Y-%m-%d").date()

        except ValueError:

            # 返回无法解析的日期标记。
            return None

    # 定义九州通完整 Excel 列映射构建方法。
    def build_complete_jzt_columns(self, data_type, rows):
        """
        构建按当前商业接口返回顺序排列的完整 Excel 列映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 接口返回的原始记录。
        :type rows: list[dict]
        :return: 完整 Excel 列映射。
        :rtype: dict
        """

        # 读取当前数据类型的商业字段标题映射。
        configured_columns = self.build_jzt_columns(data_type)

        # 初始化当前响应实际字段顺序。
        columns = {}

        # 遍历接口返回的每条原始记录。
        for row in rows:

            # 跳过非字典类型的异常记录。
            if not isinstance(row, dict):

                # 继续读取下一条原始记录。
                continue

            # 遍历当前记录的全部原始字段。
            for field_name in row.keys():

                # 跳过已经按接口顺序记录的字段。
                if field_name in columns:

                    # 继续读取下一个原始字段。
                    continue

                # 按配置中文标题或接口原始键写入当前字段。
                columns[field_name] = configured_columns.get(field_name, field_name)

        # 保留空结果场景可用的协议字段参考。
        if not columns:

            # 使用当前数据类型的已知字段生成空结果表头。
            columns = dict(configured_columns)

        # 返回完整字段映射。
        return columns

    # 定义库存输出日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):
        """
        解析九州通标准输出文件名使用的业务日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准输出文件名使用的业务日期。
        :rtype: str | None
        """

        # 判断当前数据类型是否为库存类。
        if "库存" in data_type:

            # 返回导出当天日期作为库存命名日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向类查询开始日期。
        return start_date or end_date

    # 定义九州通数据类型校验方法。
    def validate_data_type(self, data_type):
        """
        校验九州通数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 校验数据类型是否存在。
        if data_type not in ["配送流向", "购进流向", "库存", "报损流向"]:
            raise NotImplementedError(f"当前九州通暂未接入: {data_type}")

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):
        """
        构建流向文件输出名称。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 输出文件名称。
        :rtype: str
        """

        # 委托平台基类统一处理日期范围文件命名。
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
        :type end_date: str
        :return: 库存日期标签。
        :rtype: str
        """

        # 读取导出当天日期。
        date_value = datetime.now()

        # 返回 yy.m.d 标签。
        return f"{date_value.year % 100}.{date_value.month}.{date_value.day}"

    # 定义配送流向分页查询方法。
    def query_distribution_flow(self, start_date, end_date, page_size=100):
        """
        查询配送流向数据。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_size: 每页查询条数。
        :type page_size: int
        :return: 查询结果列表。
        :rtype: list[dict]
        """

        # 打印查询阶段标题。
        self.ph.section("配送流向查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 写入查询日志。
        self.write_flow_log("8", self.build_distribution_log_text("查询", start_date, end_date))

        # 初始化查询结果列表。
        all_rows = []

        # 初始化分页偏移量。
        offset = 0

        # 初始化总记录数。
        total_count = None

        # 循环分页查询。
        while True:

            # 构建查询请求体。
            payload = self.build_distribution_query_payload(start_date, end_date, page_size, offset)

            # 打印当前分页查询日志。
            self.ph.info(self.ph.join(self.ph.kv("请求配送流向分页", f"offset={offset}", "cyan"), self.ph.kv("limit", page_size, "cyan")))

            # 发送查询请求。
            result = self.http.post_json(urljoin(self.base_url, self.query_api_path), payload, self.login_page_url)

            # 解析查询响应。
            response_data = self.http.decode_json(result)

            # 校验查询响应。
            if not response_data.get("success"):
                raise RuntimeError(f"配送流向查询失败：{response_data.get('msg') or response_data}")

            # 读取响应业务数据。
            data_block = response_data.get("data") or {}

            # 读取当前页数据。
            page_rows = data_block.get("data") or []

            # 读取总记录数。
            total_count = data_block.get("totalCount", total_count)

            # 追加当前页数据。
            all_rows.extend(page_rows)

            # 打印分页查询结果。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count, "cyan")))

            # 判断是否已经查完。
            if total_count is not None and len(all_rows) >= int(total_count):
                break

            # 判断当前页是否为空。
            if not page_rows:
                break

            # 增加分页偏移。
            offset += page_size

            # 分页请求之间保持轻量间隔。
            time.sleep(random.uniform(0.05, 0.15))

        # 返回全量查询结果。
        return all_rows

    # 定义配送流向接口导出方法。
    def export_distribution_flow(self, start_date, end_date, output_path):
        """
        导出配送流向 Excel 文件。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param output_path: 输出文件路径。
        :type output_path: str
        :return: 输出文件路径。
        :rtype: str
        """

        # 打印导出阶段标题。
        self.ph.section("配送流向导出", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 构建导出表单。
        payload = self.build_distribution_export_payload(start_date, end_date)

        # 打印导出请求日志。
        self.ph.info(f"提交配送流向导出请求: {self.export_api_path}")

        # 发送导出请求。
        result = self.http.post_form(urljoin(self.base_url, self.export_api_path), payload, self.login_page_url)

        # 校验导出响应是否为空。
        if not result.body:
            raise RuntimeError("配送流向导出失败：响应内容为空")

        # 创建输出目录。
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 删除已有同名文件。
        self.remove_existing_file(output_path)

        # 写入 Excel 二进制文件。
        try:

            # 打开导出文件写入句柄。
            with open(output_path, "wb") as file_obj:

                # 写入接口返回的二进制内容。
                file_obj.write(result.body)

        # 处理文件被占用导致的写入异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

        # 打印导出保存日志。
        self.ph.success(self.ph.join(self.ph.kv("配送流向文件已保存", output_path, "green"), self.ph.kv("文件大小", f"{len(result.body)} bytes", "cyan")))

        # 写入导出日志。
        self.write_flow_log("12", self.build_distribution_log_text("流向导出", start_date, end_date))

        # 返回输出路径。
        return output_path

    # 定义配送流向查询请求体构建方法。
    def build_distribution_query_payload(self, start_date, end_date, limit, offset):
        """
        构建配送流向查询请求体。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param limit: 每页条数。
        :type limit: int
        :param offset: 分页偏移。
        :type offset: int
        :return: 查询请求体。
        :rtype: dict
        """

        # 返回查询请求体。
        return {
            "db": "db",
            "filterModel": {},
            "sortModel": [],
            "limit": limit,
            "limitOffset": offset,
            "needCount": True,
            "params": self.build_distribution_params(start_date, end_date),
            "sqlId": "/flowquery/flowquery@query",
        }

    # 定义九州通通用查询请求体构建方法。
    def build_jzt_query_payload(self, data_type, start_date, end_date, limit, offset):
        """
        构建九州通指定类型查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param limit: 每页条数。
        :type limit: int
        :param offset: 分页偏移。
        :type offset: int
        :return: 查询请求体。
        :rtype: dict
        """

        # 返回查询请求体。
        return {
            "db": "db",
            "filterModel": {},
            "sortModel": [],
            "limit": limit,
            "limitOffset": offset,
            "needCount": True,
            "params": self.build_jzt_params(data_type, start_date, end_date),
            "sqlId": self.build_jzt_sql_id(data_type),
        }

    # 定义九州通查询 SQL 标识构建方法。
    def build_jzt_sql_id(self, data_type):
        """
        构建九州通指定类型 SQL 标识。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: SQL 标识。
        :rtype: str
        """

        # 定义数据类型和 SQL 标识映射。
        sql_ids = {
            "配送流向": "/flowquery/flowquery@query",
            "购进流向": "/groupbuyquery/Groupbuyquery@query",
            "库存": "/inventoryquery/inventoryquery@query",
            "报损流向": "/lossquery/lossquery@query",
        }

        # 返回指定类型 SQL 标识。
        return sql_ids[data_type]

    # 定义九州通通用查询参数构建方法。
    def build_jzt_params(self, data_type, start_date, end_date):
        """
        构建九州通指定类型查询参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 查询参数。
        :rtype: dict
        """

        # 读取机构范围。
        org_codes = self.account.get("机构") or []

        # 校验机构范围。
        if not org_codes:
            raise ValueError(f"{self.company_name} 未配置机构范围，请抓取全选后的 org 数组并写入 account_config.py 的 机构 字段")

        # 返回配送流向查询参数。
        if data_type == "配送流向":
            return {
                "appUserName": self.account["账号"],
                "org": org_codes,
                "productName": "",
                "batchnumber": "",
                "factory": "",
                "customerName": "",
                "area": "",
                "startDate": start_date,
                "endDate": end_date,
                "daterange": "",
            }

        # 返回购进和报损查询参数。
        if data_type in ["购进流向", "报损流向"]:
            return {
                "startDate": start_date,
                "endDate": end_date,
                "appUserName": self.account["账号"],
                "q1": "",
                "q2": "",
                "org": org_codes,
            }

        # 返回库存查询参数。
        if data_type == "库存":
            return {
                "appUserName": self.account["账号"],
                "org": org_codes,
                "productName": "",
                "isZero": "",
                "factory": "",
            }

        # 抛出未接入类型异常。
        raise NotImplementedError(f"当前九州通暂未接入: {data_type}")

    # 定义配送流向导出表单构建方法。
    def build_distribution_export_payload(self, start_date, end_date):
        """
        构建配送流向导出表单。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 导出表单字段。
        :rtype: dict
        """

        # 构建导出查询参数。
        params = self.build_distribution_params(start_date, end_date)

        # 构建导出列映射。
        columns = self.build_distribution_export_columns()

        # 返回表单字段。
        return {
            "params": json.dumps(params, ensure_ascii=False, separators=(",", ":")),
            "colums": json.dumps(columns, ensure_ascii=False, separators=(",", ":")),
        }

    # 定义配送流向查询参数构建方法。
    def build_distribution_params(self, start_date, end_date):
        """
        构建配送流向查询参数。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 查询参数。
        :rtype: dict
        """

        # 返回查询参数。
        if not self.account.get("机构"):
            raise ValueError(f"{self.company_name} 未配置机构范围，请抓取全选后的 org 数组并写入 account_config.py 的 机构 字段")

        # 返回查询参数。
        return {
            "appUserName": self.account["账号"],
            "org": self.account.get("机构") or [],
            "productName": "",
            "batchnumber": "",
            "factory": "",
            "customerName": "",
            "area": "",
            "startDate": start_date,
            "endDate": end_date,
            "daterange": "",
        }

    # 定义配送流向列映射构建方法。
    def build_distribution_export_columns(self):
        """
        构建配送流向导出列映射。

        :return: 导出列映射。
        :rtype: dict
        """

        # 返回导出列映射。
        return {
            "FSELLDATE": "日期",
            "FORDERNUMBER": "单据编号",
            "FBRANCHORGNAME": "公司名称",
            "FCUSTOMERCODE": "销往单位编码",
            "FCUSTOMERNAME": "销往单位",
            "FPRODUCTCODE": "药品编码",
            "FPRODUCTNAME": "药品名称",
            "IONAME": "库存组织",
            "FSPECIFICATION": "规格",
            "FQUANTITY": "数量",
            "FPRICE": "单价",
            "FBATCHNUMBER": "批号",
            "FBILLER": "开票员",
            "FFACTORY": "生产厂家",
            "FACTORY_SHORT": "生产厂家简称",
            "FUNIT": "包装",
            "FAREA": "区域",
            "FDZSW": "网上订单类型",
            "FDEPARTMENT": "所属部门",
            "FBUYER": "采购员",
            "FVALIDITY": "商品有效期",
            "FBUSINESS_LICENSE_NO": "营业执照号",
            "SUPPLIER_NOTES": "厂家业务员信息",
        }

    # 定义九州通通用列映射构建方法。
    def build_jzt_columns(self, data_type):
        """
        构建九州通指定类型 Excel 列映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: Excel 列映射。
        :rtype: dict
        """

        # 返回配送流向列映射。
        if data_type == "配送流向":
            return self.build_distribution_export_columns()

        # 返回购进流向列映射。
        if data_type == "购进流向":
            return {
                "FBUYDATE": "日期",
                "FORDERNUMBER": "单据编号",
                "FBRANCHORGNAME": "公司名称",
                "FPRODUCTCODE": "药品编码",
                "FPRODUCTNAME": "药品名称",
                "FSPECIFICATION": "规格",
                "FQUANTITY": "数量",
                "FUNIT": "单位",
                "FPRICE": "单价",
                "FBATCHNUMBER": "批号",
                "FFACTORY": "生产厂家",
                "FCUSTOMERCODE": "供应商编码",
                "FCUSTOMERNAME": "供应商名称",
            }

        # 返回库存列映射。
        if data_type == "库存":
            return {
                "FSTORAGEDATE": "日期",
                "FBRANCHORGNAME": "公司名称",
                "IONAME": "库存组织",
                "FSTORENAME": "仓库信息",
                "FPRODUCTCODE": "药品编码",
                "FPRODUCTNAME": "药品名称",
                "FSPECIFICATION": "药品规格",
                "FQUANTITY": "数量",
                "FBIGQUANTITY": "件数",
                "FUNIT": "包装单位",
                "FPRICE": "价格",
                "FBATCHNUMBER": "批号",
                "FFACTORY": "生产厂家",
                "FACTORY_SHORT": "生产厂家简称",
                "FPACKAGE": "包装数量",
                "FBIRTHDATE": "生产日期",
                "FVALIDITY": "有效期",
                "ZHGRQ": "最后购进日期",
                "KXTS": "可销天数",
                "ZKTS": "在库天数",
                "RXJSSL": "日均销售数量",
            }

        # 返回报损流向列映射。
        if data_type == "报损流向":
            return {
                "FSELLDATE": "日期",
                "FORDERNUMBER": "单据编号",
                "FBRANCHORGNAME": "公司名称",
                "FPRODUCTCODE": "药品编码",
                "FPRODUCTNAME": "药品名称",
                "FSPECIFICATION": "规格",
                "FQUANTITY": "数量",
                "FUNIT": "单位",
                "FPRICE": "单价",
                "FBATCHNUMBER": "批号",
                "FFACTORY": "生产厂家",
                "FACTORY_SHORT": "生产厂家简称",
            }

        # 抛出未接入类型异常。
        raise NotImplementedError(f"当前九州通暂未接入: {data_type}")

    # 定义配送流向 Excel 写入方法。
    def write_distribution_rows_to_excel(self, rows, output_path):
        """
        写入配送流向查询结果到 Excel。

        :param rows: 查询结果列表。
        :type rows: list[dict]
        :param output_path: 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿对象。
        self.write_rows_to_excel(rows, output_path, self.build_distribution_export_columns(), "配送流向")

    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, output_path, columns, sheet_name):
        """
        写入查询结果到 Excel。

        :param rows: 查询结果列表。
        :type rows: list[dict]
        :param output_path: 输出文件路径。
        :type output_path: str
        :param columns: Excel 列映射。
        :type columns: dict
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
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = sheet_name[:31]

        # 写入表头行。
        worksheet.append(list(columns.values()))

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按列映射顺序组装一行数据。
            worksheet.append([row.get(field_name, "") for field_name in columns.keys()])

        # 遍历所有导出列设置列宽。
        for column_index, header_name in enumerate(columns.values(), start=1):

            # 读取当前列字母。
            column_letter = get_column_letter(column_index)

            # 设置当前列宽。
            worksheet.column_dimensions[column_letter].width = max(12, min(28, len(str(header_name)) + 8))

        # 冻结表头行。
        worksheet.freeze_panes = "A2"

        # 启用自动筛选。
        worksheet.auto_filter.ref = worksheet.dimensions

        # 创建隐藏字段元数据工作表。
        metadata_sheet = workbook.create_sheet("字段元数据")

        # 写入字段元数据表头。
        metadata_sheet.append(["正式标题", "原始键", "字段来源", "首次出现顺序", "动态字段"])

        # 读取当前数据类型已知字段键集合。
        try:

            # 获取商业配置字段映射键。
            static_keys = set(self.build_jzt_columns(sheet_name).keys())

        # 处理未声明字段映射的数据类型。
        except (NotImplementedError, KeyError):

            # 使用空集合表示没有已知字段。
            static_keys = set()

        # 遍历正式输出字段写入元数据。
        for ordinal, (field_key, title) in enumerate(columns.items(), start=1):

            # 判断当前字段是否为静态映射之外的动态字段。
            is_dynamic = field_key not in static_keys

            # 写入字段元数据行。
            metadata_sheet.append([title, field_key, "配置映射" if not is_dynamic else "接口返回", ordinal, "是" if is_dynamic else "否"])

        # 隐藏字段元数据页避免影响明细阅读。
        metadata_sheet.sheet_state = "hidden"

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

        # 判断同名文件是否存在。
        if not os.path.exists(output_path):

            # 文件不存在时直接返回。
            return

        # 捕获删除文件时的占用异常。
        try:

            # 删除已有同名文件。
            os.remove(output_path)

        # 处理文件被占用导致的删除异常。
        except PermissionError as error:

            # 抛出带业务路径的文件占用异常。
            raise PermissionError(f"无法覆盖文件，请先关闭已打开的 Excel 文件：{output_path}") from error

    # 定义配送流向日志文本构建方法。
    def build_distribution_log_text(self, action_name, start_date, end_date):
        """
        构建配送流向日志文本。

        :param action_name: 操作名称。
        :type action_name: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 日志文本。
        :rtype: str
        """

        # 返回与网页一致的日志文本。
        return f"{action_name}:日期从【{start_date}】至【{end_date}】药品名称【】批号【】生产厂家【】销往单位【】销往区域【】"

    # 定义九州通通用日志文本构建方法。
    def build_jzt_log_text(self, data_type, action_name, start_date, end_date):
        """
        构建九州通操作日志文本。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param action_name: 操作名称。
        :type action_name: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 操作日志文本。
        :rtype: str
        """

        # 返回配送流向日志文本。
        if data_type == "配送流向":
            return self.build_distribution_log_text(action_name, start_date, end_date)

        # 返回库存日志文本。
        if data_type == "库存":
            return f"{data_type}{action_name}:药品名称【】生产厂家【】"

        # 返回通用日期类日志文本。
        return f"{data_type}{action_name}:日期从【{start_date}】至【{end_date}】药品名称【】批号【】"

    # 定义操作日志写入方法。
    def write_flow_log(self, log_type, log_text):
        """
        写入九州通操作日志。

        :param log_type: 日志类型。
        :type log_type: str
        :param log_text: 日志文本。
        :type log_text: str
        :return: None。
        :rtype: None
        """

        # 构建日志请求体。
        payload = {
            "db": "db",
            "sqlId": "/log/log@insert",
            "params": {
                "fbranchorgcode": self.account.get("日志机构编码") or self.account.get("分支机构编码") or "",
                "foperatercode": self.account["账号"],
                "foperatername": self.account.get("操作员名称") or self.company_name,
                "flogtype": log_type,
                "flogtext": log_text,
            },
        }

        try:

            # 打印操作日志写入请求。
            self.ph.info(self.ph.join(self.ph.kv("写入操作日志", f"type={log_type}", "cyan"), self.ph.kv("接口", self.execute_api_path, "cyan")))

            # 发送操作日志请求。
            result = self.http.post_json(urljoin(self.base_url, self.execute_api_path), payload, self.login_page_url)

            # 解析操作日志响应。
            response_data = self.http.decode_json(result)

            # 判断日志写入是否成功。
            if response_data.get("success"):

                # 打印操作日志写入成功信息。
                self.ph.success(self.ph.kv("操作日志写入完成", "affectRows=1", "green"))

            else:

                # 打印操作日志未确认信息。
                self.ph.warning("操作日志写入未确认，不影响后续数据请求")

        # 处理操作日志接口异常。
        except Exception:

            # 日志接口失败不阻断业务查询。
            self.ph.warning("操作日志写入异常，不影响后续数据请求")
