# -*- coding: utf-8 -*-
"""
安徽华人健康医药股份有限公司捷助数据中心协议适配器。

本模块负责捷助数据中心的验证码登录、令牌保存、分页查询和本地 Excel 生成。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入随机等待模块。
import random

# 导入验证码重试等待模块。
import time

# 导入日期时间对象。
from datetime import datetime, timedelta

# 导入 URL 解析函数。
from urllib.parse import urlparse

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入验证码识别器。
from ddi_framework import CaptchaSolver

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义捷助数据中心字段标题映射。
FIELD_TITLE_MAPPING = {
    "currDate": "销售日期",
    "rq": "日期",
    "djbh": "单据编号",
    "salesCode": "销售方代码",
    "salesName": "销售方名称",
    "ssdw": "所属单位",
    "purchaseCode": "采购方代码",
    "purchaseName": "买方名称",
    "companyCode": "公司代码",
    "companyName": "公司名称",
    "goodsId": "产品代码",
    "goodsCode": "商品编码",
    "newGoodsCode": "新商品编码",
    "spbh": "商品编码",
    "goodsName": "产品名称",
    "goodsSpec": "产品规格",
    "manufacturer": "生产厂家",
    "lotNo": "产品批号",
    "packUnits": "单位",
    "qty": "交易数量",
    "unitPrice": "销售单价",
    "xycb": "协议成本",
    "amount": "金额",
    "sxq": "失效期",
    "position": "货位",
    "salesType": "销售类型",
    "centerErpCode": "中心ERP编码",
    "id": "ID",
    "remark": "备注",
    "createTime": "创建时间",
    "updateTime": "更新时间",
}


# 定义安徽华人健康捷助数据中心协议适配器。
class HrjkPlatform(BasePlatform):

    """
    安徽华人健康医药股份有限公司捷助数据中心协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 安徽华人健康平台适配器实例。
    :rtype: HrjkPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化安徽华人健康捷助数据中心适配器。

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

        # 保存登录页地址。
        self.login_page_url = account.get("登录页", "http://idc.fastjz.com:2022/jzapi/")

        # 保存接口根地址。
        self.api_base_url = account.get("接口根地址", "http://idc.fastjz.com:2022/jzapi").rstrip("/")

        # 保存站点源地址。
        self.origin_url = self.build_origin(self.api_base_url)

        # 保存验证码接口地址。
        self.captcha_api_url = account.get("验证码接口", f"{self.api_base_url}/init/verificationCode")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", f"{self.api_base_url}/login")

        # 保存查询接口地址。
        self.query_api_url = account.get("查询接口", f"{self.api_base_url}/sys/query/getFrameValue")

        # 保存页面配置接口地址。
        self.frame_api_url = account.get("页面配置接口", f"{self.api_base_url}/sys/query/getFrame")

        # 保存分页大小。
        self.page_size = int(account.get("分页大小", 100))

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.api_base_url)

        # 初始化验证码识别器。
        self.captcha_solver = CaptchaSolver()

        # 初始化登录令牌。
        self.login_token = ""

        # 初始化登录响应。
        self.login_result = {}

        # 初始化登录状态。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        执行捷助数据中心协议登录。

        :return: 登录响应数据。
        :rtype: dict
        """

        # 执行带验证码重试的登录流程。
        return self.login_with_captcha_retry()

    # 定义带验证码重试的登录方法。
    def login_with_captcha_retry(self, max_retries=8):

        """
        使用图片验证码重试机制执行登录。

        :param max_retries: 最大验证码刷新次数。
        :type max_retries: int
        :return: 登录响应数据。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("捷助数据中心登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.join(self.ph.kv("商业", self.company_name, "cyan"), self.ph.kv("访问登录页", self.login_page_url, "cyan")))

        # 访问登录页初始化站点上下文。
        self.http.get(self.login_page_url)

        # 初始化最后一次登录错误。
        last_error = None

        # 循环获取验证码并提交登录。
        for retry_index in range(max_retries):

            # 打印验证码尝试日志。
            self.ph.info(self.ph.join(self.ph.kv("商业", self.company_name, "cyan"), self.ph.kv("图片验证码尝试", f"第 {retry_index + 1}/{max_retries} 次", "cyan")))

            # 捕获当前验证码登录异常。
            try:

                # 获取验证码上下文。
                captcha_context = self.get_captcha_context()

                # 识别验证码文本。
                captcha_code = self.solve_captcha_code(captcha_context["image_bytes"])

                # 打印验证码识别日志。
                self.ph.info(self.ph.join(self.ph.kv("商业", self.company_name, "cyan"), self.ph.kv("图片验证码识别完成", f"长度={len(captcha_code)}", "cyan")))

                # 构建登录请求体。
                payload = self.build_login_payload(captcha_context["uuid"], captcha_code)

                # 打印登录账号日志。
                self.ph.info(self.ph.join(self.ph.kv("登录账号", self.clean_login_name(), "cyan"), self.ph.kv("密码长度", len(self.clean_login_password()), "cyan")))

                # 打印正式登录请求日志。
                self.ph.info("提交正式登录请求: /login")

                # 提交登录请求。
                result = self.post_json(self.login_api_url, payload, with_token=False)

                # 解析登录响应。
                login_result = self.decode_json_response(result)

                # 判断登录是否成功。
                if self.is_success_response(login_result):

                    # 保存登录响应。
                    self.login_result = login_result

                    # 保存登录令牌。
                    self.login_token = str(login_result.get("data") or "")

                    # 校验登录令牌。
                    if not self.login_token:

                        # 抛出令牌缺失异常。
                        raise RuntimeError(f"{self.company_name} 登录响应缺少 accessToken")

                    # 保存登录状态。
                    self.logged_in = True

                    # 打印登录成功日志。
                    self.ph.success(self.ph.join(self.ph.kv("正式登录成功", login_result.get("message", "登录成功"), "green"), self.ph.kv("Token", self.login_token[:8], "cyan")))

                    # 返回登录响应。
                    return login_result

                # 保存登录失败响应。
                last_error = login_result

                # 打印验证码或登录失败日志。
                self.ph.warning(self.ph.join(self.ph.kv("商业", self.company_name, "cyan"), "登录校验未通过，准备刷新验证码"))

            # 处理验证码识别或登录提交异常。
            except Exception as error:

                # 保存当前异常。
                last_error = error

                # 打印验证码处理失败日志。
                self.ph.warning(self.ph.join(self.ph.kv("商业", self.company_name, "cyan"), "图片验证码识别或登录校验未通过，准备刷新验证码"))

            # 判断是否已经达到最后一次重试。
            if retry_index >= max_retries - 1:

                # 跳出验证码重试循环。
                break

            # 计算验证码失败后的等待秒数。
            delay_seconds = 1.0 + random.random() * 1.0

            # 打印验证码等待日志。
            self.ph.wait(self.ph.kv("验证码失败后等待，预计", f"{delay_seconds:.1f} 秒", "cyan"))

            # 失败后延迟等待。
            time.sleep(delay_seconds)

        # 抛出验证码登录失败异常。
        raise RuntimeError(f"{self.company_name} 图片验证码登录失败：{last_error}")

    # 定义验证码上下文获取方法。
    def get_captcha_context(self):

        """
        获取登录验证码图片与验证码会话编号。

        :return: 验证码上下文字典。
        :rtype: dict
        """

        # 打印验证码请求日志。
        self.ph.info("请求图片验证码: /init/verificationCode")

        # 请求验证码接口。
        result = self.post_json(self.captcha_api_url, {}, with_token=False)

        # 解析验证码响应。
        response_data = self.decode_json_response(result)

        # 校验验证码接口状态。
        if not self.is_success_response(response_data):

            # 抛出验证码接口异常。
            raise RuntimeError(f"验证码接口返回失败：{response_data}")

        # 读取验证码业务数据。
        data = response_data.get("data") or {}

        # 读取验证码图片文本。
        image_text = data.get("img") or ""

        # 读取验证码会话编号。
        uuid_value = data.get("uuid") or ""

        # 校验验证码图片。
        if not image_text:

            # 抛出验证码图片缺失异常。
            raise RuntimeError(f"验证码接口未返回图片：{response_data}")

        # 校验验证码会话编号。
        if not uuid_value:

            # 抛出验证码会话编号缺失异常。
            raise RuntimeError(f"验证码接口未返回 uuid：{response_data}")

        # 解码验证码图片字节。
        image_bytes = base64.b64decode(str(image_text).split("base64,", 1)[-1])

        # 返回验证码上下文。
        return {"uuid": uuid_value, "image_bytes": image_bytes}

    # 定义验证码识别方法。
    def solve_captcha_code(self, image_bytes):

        """
        识别图片验证码文本。

        :param image_bytes: 验证码图片字节。
        :type image_bytes: bytes
        :return: 验证码文本。
        :rtype: str
        """

        # 按字母数字范围识别验证码。
        raw_text = self.captcha_solver.solve_raw_text_image_with_ranges(image_bytes, "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

        # 清洗验证码文本。
        captcha_code = "".join([char for char in str(raw_text or "") if char.isalnum()])

        # 校验验证码长度。
        if len(captcha_code) < 4:

            # 使用通用文本识别作为备用。
            captcha_code = self.captcha_solver.solve_text_image(image_bytes, min_length=4)

        # 校验最终验证码文本。
        if not captcha_code:

            # 抛出验证码识别失败异常。
            raise RuntimeError("图片验证码识别为空")

        # 返回验证码文本。
        return captcha_code

    # 定义登录请求体构建方法。
    def build_login_payload(self, uuid_value, captcha_code):

        """
        构建登录请求体。

        :param uuid_value: 验证码会话编号。
        :type uuid_value: str
        :param captcha_code: 验证码文本。
        :type captcha_code: str
        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录字段。
        return {"userName": self.clean_login_name(), "password": self.clean_login_password(), "verificationCode": captcha_code, "uuid": uuid_value}



    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录 Cookie 与访问令牌。

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

        # 保存登录令牌文件。
        self.save_token_file(output_dir)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义令牌保存方法。
    def save_token_file(self, output_dir):

        """
        保存当前登录访问令牌。

        :param output_dir: 输出目录。
        :type output_dir: str
        :return: 令牌文件路径。
        :rtype: str
        """

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建令牌文件路径。
        token_path = os.path.join(output_dir, f"{self.company_name}_token.json")

        # 构建令牌文件数据。
        token_data = {"accessToken": self.login_token, "login_result": self.login_result}

        # 写入令牌文件。
        with open(token_path, "w", encoding="utf-8") as file_obj:

            # 序列化令牌文件。
            json.dump(token_data, file_obj, ensure_ascii=False, indent=2)

        # 打印令牌保存日志。
        self.ph.success(self.ph.kv("登录令牌已保存", self.ph.path(token_path), "green"))

        # 返回令牌文件路径。
        return token_path

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询捷助数据中心业务数据。

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
        query_result = self.query_hrjk_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]


    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询捷助数据中心业务数据并生成 Excel。

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
        query_result = self.query_hrjk_data(data_type, start_date, end_date)

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

    # 定义业务数据查询方法。
    def query_hrjk_data(self, data_type, start_date, end_date):

        """
        查询捷助数据中心指定类型数据。

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

        # 校验流向类查询开始日期。
        if data_type in ["购进流向", "配送流向"] and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验流向类查询结束日期。
        if data_type in ["购进流向", "配送流向"] and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 确保当前会话已经登录。
        self.ensure_login()

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 初始化查询结果行。
        all_rows = []

        # 读取前端页面配置。
        frame_data = self.fetch_query_frame(data_type)

        # 构建初始化查询请求体。
        initial_payload = self.build_initial_query_payload(data_type, start_date, end_date)

        # 打印初始化查询请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}初始化查询", self.resolve_query_name(data_type), "cyan")))

        # 发送初始化查询请求。
        initial_result = self.post_json(self.query_api_url, initial_payload, with_token=True)

        # 解析初始化查询响应。
        initial_response_data = self.decode_json_response(initial_result)

        # 校验初始化查询响应状态。
        if not self.is_success_response(initial_response_data):

            # 抛出初始化查询失败异常。
            raise RuntimeError(f"{self.company_name} {data_type}查询失败：{initial_response_data.get('message') or initial_response_data}")

        # 读取初始化响应表格对象。
        initial_table_data = self.extract_table_data(initial_response_data)

        # 读取初始化响应数据行。
        initial_rows = self.extract_rows(initial_table_data)

        # 合并初始化响应数据行。
        all_rows.extend(initial_rows)

        # 读取分页总记录数。
        total_count = self.resolve_total_count(initial_table_data, None)

        # 解析后续分页大小。
        active_page_size = self.resolve_active_page_size(frame_data, initial_rows)

        # 打印初始化响应解析日志。
        self.ph.success(self.ph.join(self.ph.kv("初始化查询完成", f"{len(initial_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count if total_count is not None else "未知", "cyan")))

        # 初始化后续分页页码。
        page_index = 2

        # 循环读取剩余分页。
        while total_count is None or len(all_rows) < total_count:

            # 构建当前分页请求体。
            payload = self.build_query_payload(data_type, start_date, end_date, page_index, active_page_size)

            # 打印当前分页请求日志。
            self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", f"currentPage={page_index}", "cyan"), self.ph.kv("pageSize", active_page_size, "cyan")))

            # 发送当前分页查询请求。
            result = self.post_json(self.query_api_url, payload, with_token=True)

            # 解析当前分页响应。
            response_data = self.decode_json_response(result)

            # 校验当前分页响应状态。
            if not self.is_success_response(response_data):

                # 抛出查询失败异常。
                raise RuntimeError(f"{self.company_name} {data_type}查询失败：{response_data.get('message') or response_data}")

            # 读取当前业务表格对象。
            table_data = self.extract_table_data(response_data)

            # 读取当前页数据行。
            current_rows = self.extract_rows(table_data)

            # 合并当前页数据行。
            all_rows.extend(current_rows)

            # 打印当前页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(current_rows)} 条", "green"), self.ph.kv("累计", f"{len(all_rows)} 条", "cyan"), self.ph.kv("总数", total_count if total_count is not None else "未知", "cyan")))

            # 判断当前页是否已经没有数据。
            if not current_rows:

                # 结束分页循环。
                break

            # 判断当前页是否已经不足一页。
            if len(current_rows) < active_page_size:

                # 结束分页循环。
                break

            # 递增页码。
            page_index += 1

        # 合并页面配置字段与原始数据字段。
        headers = self.build_output_headers(data_type, frame_data, initial_table_data, all_rows)

        # 返回查询数据与表头。
        return {"rows": all_rows, "headers": headers}


    # 定义查询阶段标题打印方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印查询阶段标题。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 判断是否为库存查询。
        if data_type == "库存":

            # 读取库存查询日期。
            stock_date = self.resolve_stock_query_date(end_date)

            # 打印库存查询标题。
            self.ph.section(f"{data_type}查询", self.ph.kv("查询日期", stock_date, "cyan"))

            # 结束标题打印。
            return

        # 打印流向查询标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

    # 定义查询请求体构建方法。
    def fetch_query_frame(self, data_type):

        """
        读取查询页面字段配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 页面配置响应数据。
        :rtype: dict
        """

        # 读取当前数据类型查询名称。
        query_name = self.resolve_query_name(data_type)

        # 构建页面配置接口地址。
        frame_url = f"{self.frame_api_url}/{query_name}"

        # 打印页面配置请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"读取{data_type}字段配置", query_name, "cyan")))

        # 请求页面配置接口。
        result = self.post_json(frame_url, {}, with_token=True)

        # 解析页面配置响应。
        response_data = self.decode_json_response(result)

        # 校验页面配置响应状态。
        if not self.is_success_response(response_data):

            # 抛出页面配置读取失败异常。
            raise RuntimeError(f"{self.company_name} {data_type}字段配置读取失败：{response_data.get('message') or response_data}")

        # 返回页面配置响应数据。
        return response_data

    # 定义初始化查询请求体构建方法。
    def build_initial_query_payload(self, data_type, start_date, end_date):

        """
        构建不带分页字段的初始化查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 初始化查询请求体。
        :rtype: dict
        """

        # 构建查询参数。
        query_param = self.build_query_param(data_type, start_date, end_date)

        # 返回初始化查询请求体。
        return {"queryName": self.resolve_query_name(data_type), "queryParam": query_param, "function": "query"}

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, start_date, end_date, page_index, page_size=None):

        """
        构建业务查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_index: 当前页码。
        :type page_index: int
        :param page_size: 当前分页大小。
        :type page_size: int | None
        :return: 业务查询请求体。
        :rtype: dict
        """

        # 构建查询参数。
        query_param = self.build_query_param(data_type, start_date, end_date)

        # 读取当前分页大小。
        current_page_size = int(page_size or self.page_size)

        # 构建分页查询请求体。
        return {"queryName": self.resolve_query_name(data_type), "queryParam": query_param, "function": "query", "currentPage": page_index, "subQuery": "cx1", "orderby": "", "sort": "", "pageSize": current_page_size}

    # 定义查询参数构建方法。
    def build_query_param(self, data_type, start_date, end_date):

        """
        构建业务查询参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 业务查询参数。
        :rtype: dict
        """

        # 处理购进流向查询参数。
        if data_type == "购进流向":

            # 返回购进流向查询参数。
            return {"startDate": start_date, "endDate": end_date, "userId": "", "orgId": "", "name": "", "goodsName": ""}

        # 处理配送流向查询参数。
        if data_type == "配送流向":

            # 返回配送流向查询参数。
            return {"startDate": start_date, "endDate": end_date, "userId": "", "goodsName": ""}

        # 返回库存查询参数。
        return {"userId": "", "orgId": "", "name": "", "goodsName": "", "startDate": self.resolve_stock_query_date(end_date)}

    # 定义数据类型对应查询名称读取方法。
    def resolve_query_name(self, data_type):

        """
        读取数据类型对应的捷助查询名称。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 捷助查询名称。
        :rtype: str
        """

        # 定义数据类型与查询名称映射。
        mapping = {"购进流向": "flowPurchaseSelect", "配送流向": "flowSalesSelect", "库存": "flowStockSelect"}

        # 返回当前数据类型对应查询名称。
        return mapping[data_type]

    # 定义库存查询日期解析方法。
    def resolve_stock_query_date(self, end_date):

        """
        解析库存查询业务日期。

        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 库存查询日期。
        :rtype: str
        """

        # 计算平台默认库存查询日期。
        stock_date = datetime.now() - timedelta(days=1)

        # 返回平台默认库存查询日期文本。
        return stock_date.strftime("%Y-%m-%d")

    # 定义表格对象提取方法。
    def extract_table_data(self, response_data):

        """
        提取查询响应中的表格数据对象。

        :param response_data: 查询响应数据。
        :type response_data: dict
        :return: 表格数据对象。
        :rtype: dict
        """

        # 读取响应业务数据列表。
        data_list = response_data.get("data") or []

        # 校验业务数据列表。
        if not data_list or not isinstance(data_list[0], dict):

            # 返回空表格对象。
            return {}

        # 返回主表格对象。
        return data_list[0].get("cx1") or {}

    # 定义表格行提取方法。
    def extract_rows(self, table_data):

        """
        提取表格数据行。

        :param table_data: 表格数据对象。
        :type table_data: dict
        :return: 数据行列表。
        :rtype: list[dict]
        """

        # 读取表格行数据。
        rows = table_data.get("rows") or []

        # 返回字典数据行列表。
        return [row for row in rows if isinstance(row, dict)]

    # 定义表头提取方法。
    def extract_headers(self, table_data, data_type):

        """
        提取表格输出表头。

        :param table_data: 表格数据对象。
        :type table_data: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 读取响应表头字段定义。
        raw_headers = table_data.get("tempObject") or []

        # 初始化表头配置。
        headers = self.extract_headers_from_column_definitions(raw_headers, include_hidden=True)

        # 返回表头配置或默认表头。
        return headers or self.build_default_headers(data_type)

    # 定义输出表头构建方法。
    def build_output_headers(self, data_type, frame_data, table_data, rows):

        """
        合并页面配置字段、响应字段和原始数据字段。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param frame_data: 页面配置响应数据。
        :type frame_data: dict
        :param table_data: 查询响应表格对象。
        :type table_data: dict
        :param rows: 查询结果行集合。
        :type rows: list[dict]
        :return: 输出表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 读取页面配置字段定义。
        frame_columns = self.extract_frame_columns(frame_data)

        # 基于可见页面字段构建表头。
        headers = self.extract_headers_from_column_definitions(frame_columns, include_hidden=False)

        # 合并响应字段定义。
        headers = self.merge_headers(headers, self.extract_headers(table_data, data_type))

        # 合并原始数据行中的全部字段。
        headers = self.merge_headers(headers, self.extract_headers_from_rows(rows))

        # 返回合并后的表头配置。
        return headers or self.build_default_headers(data_type)

    # 定义页面字段集合提取方法。
    def extract_frame_columns(self, frame_data):

        """
        提取页面配置中的表格字段集合。

        :param frame_data: 页面配置响应数据。
        :type frame_data: dict
        :return: 表格字段定义集合。
        :rtype: list[dict]
        """

        # 读取页面配置业务数据。
        frame_body = frame_data.get("data") or {}

        # 兼容列表形式的页面配置业务数据。
        if isinstance(frame_body, list) and frame_body:

            # 读取列表中的首个页面配置对象。
            frame_body = frame_body[0]

        # 校验页面配置业务数据结构。
        if not isinstance(frame_body, dict):

            # 返回空字段集合。
            return []

        # 读取查询配置集合。
        query_items = frame_body.get("querys") or frame_body.get("queries") or []

        # 兼容单对象形式的查询配置。
        if isinstance(query_items, dict):

            # 转换单对象查询配置为列表。
            query_items = [query_items]

        # 校验查询配置集合结构。
        if not query_items or not isinstance(query_items[0], dict):

            # 返回空字段集合。
            return []

        # 读取主表格字段定义。
        columns = query_items[0].get("columns") or query_items[0].get("cols") or []

        # 返回字典型字段定义集合。
        return [item for item in columns if isinstance(item, dict)]

    # 定义字段定义表头提取方法。
    def extract_headers_from_column_definitions(self, raw_headers, include_hidden=True):

        """
        将接口字段定义转换为输出表头配置。

        :param raw_headers: 接口字段定义集合。
        :type raw_headers: list[dict]
        :param include_hidden: 是否包含隐藏字段。
        :type include_hidden: bool
        :return: 输出表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 初始化表头配置。
        headers = []

        # 遍历前端表头字段定义。
        for item in raw_headers:

            # 跳过非字典字段定义。
            if not isinstance(item, dict):

                # 进入下一项字段定义。
                continue

            # 判断隐藏字段是否参与输出。
            if not include_hidden and self.is_hidden_column(item):

                # 进入下一项字段定义。
                continue

            # 读取字段名称。
            field_name = self.extract_column_field_name(item)

            # 跳过空字段名称。
            if not field_name:

                # 进入下一项字段定义。
                continue

            # 读取字段中文标题。
            header_name = self.extract_column_header_name(item, field_name)

            # 保存字段表头配置。
            headers = self.merge_headers(headers, [(header_name, field_name)])

        # 返回表头配置。
        return headers

    # 定义原始数据字段表头提取方法。
    def extract_headers_from_rows(self, rows):

        """
        从原始数据行中提取全部字段。

        :param rows: 原始数据行集合。
        :type rows: list[dict]
        :return: 输出表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 初始化表头配置。
        headers = []

        # 遍历原始数据行。
        for row in rows:

            # 跳过非字典数据行。
            if not isinstance(row, dict):

                # 进入下一条数据行。
                continue

            # 遍历当前数据行字段。
            for field_name in row.keys():

                # 读取字段文本。
                field_key = str(field_name or "").strip()

                # 跳过空字段文本。
                if not field_key:

                    # 进入下一项字段。
                    continue

                # 读取字段中文标题。
                header_name = FIELD_TITLE_MAPPING.get(field_key, field_key)

                # 合并当前字段表头。
                headers = self.merge_headers(headers, [(header_name, field_key)])

        # 返回原始字段表头。
        return headers

    # 定义表头合并方法。
    def merge_headers(self, base_headers, append_headers):

        """
        按字段名去重合并表头配置。

        :param base_headers: 基础表头配置。
        :type base_headers: list[tuple[str, str]]
        :param append_headers: 待追加表头配置。
        :type append_headers: list[tuple[str, str]]
        :return: 合并后的表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 复制基础表头配置。
        headers = list(base_headers or [])

        # 读取已存在字段集合。
        existing_fields = {field_name for _, field_name in headers}

        # 遍历待追加表头配置。
        for header_name, field_name in append_headers or []:

            # 跳过已存在字段。
            if field_name in existing_fields:

                # 进入下一项表头。
                continue

            # 添加当前字段名到去重集合。
            existing_fields.add(field_name)

            # 追加当前表头配置。
            headers.append((header_name, field_name))

        # 返回合并后的表头配置。
        return headers

    # 定义字段名称提取方法。
    def extract_column_field_name(self, item):

        """
        从字段定义中读取字段名。

        :param item: 字段定义对象。
        :type item: dict
        :return: 字段名。
        :rtype: str
        """

        # 按常见字段名属性读取字段名。
        field_name = item.get("name") or item.get("field") or item.get("prop") or item.get("dataIndex") or item.get("key")

        # 返回清洗后的字段名。
        return str(field_name or "").strip()

    # 定义字段标题提取方法。
    def extract_column_header_name(self, item, field_name):

        """
        从字段定义中读取字段标题。

        :param item: 字段定义对象。
        :type item: dict
        :param field_name: 字段名。
        :type field_name: str
        :return: 字段标题。
        :rtype: str
        """

        # 按常见标题属性读取字段标题。
        header_name = item.get("title") or item.get("label") or item.get("text") or item.get("displayName") or FIELD_TITLE_MAPPING.get(field_name)

        # 返回清洗后的字段标题。
        return str(header_name or field_name).strip()

    # 定义隐藏字段判断方法。
    def is_hidden_column(self, item):

        """
        判断字段定义是否为隐藏字段。

        :param item: 字段定义对象。
        :type item: dict
        :return: 是否隐藏。
        :rtype: bool
        """

        # 读取显隐标记字段。
        visible_value = item.get("visible")

        # 判断布尔显隐标记是否隐藏。
        if visible_value is False:

            # 返回隐藏判断结果。
            return True

        # 判断数字显隐标记是否隐藏。
        if visible_value == 0:

            # 返回隐藏判断结果。
            return True

        # 判断文本显隐标记是否隐藏。
        if str(visible_value).lower() in ["false", "0"]:

            # 返回隐藏判断结果。
            return True

        # 读取隐藏标记字段。
        hidden_value = item.get("hidden")

        # 判断布尔隐藏标记是否隐藏。
        if hidden_value is True:

            # 返回隐藏判断结果。
            return True

        # 判断数字隐藏标记是否隐藏。
        if hidden_value == 1:

            # 返回隐藏判断结果。
            return True

        # 判断文本隐藏标记是否隐藏。
        if str(hidden_value).lower() in ["true", "1"]:

            # 返回隐藏判断结果。
            return True

        # 返回非隐藏判断结果。
        return False

    # 定义活跃分页大小解析方法。
    def resolve_active_page_size(self, frame_data, initial_rows):

        """
        解析初始化查询之后的分页大小。

        :param frame_data: 页面配置响应数据。
        :type frame_data: dict
        :param initial_rows: 初始化查询返回行集合。
        :type initial_rows: list[dict]
        :return: 分页大小。
        :rtype: int
        """

        # 读取页面配置业务数据。
        frame_body = frame_data.get("data") or {}

        # 兼容列表形式的页面配置业务数据。
        if isinstance(frame_body, list) and frame_body:

            # 读取列表中的首个页面配置对象。
            frame_body = frame_body[0]

        # 校验页面配置业务数据结构。
        if isinstance(frame_body, dict):

            # 读取查询配置集合。
            query_items = frame_body.get("querys") or frame_body.get("queries") or []

            # 兼容单对象形式的查询配置。
            if isinstance(query_items, dict):

                # 转换单对象查询配置为列表。
                query_items = [query_items]

            # 判断查询配置是否存在分页大小。
            if query_items and isinstance(query_items[0], dict) and query_items[0].get("pageSize"):

                # 返回页面配置中的分页大小。
                return int(query_items[0].get("pageSize"))

        # 判断初始化结果是否可推断分页大小。
        if initial_rows:

            # 使用初始化结果行数作为后续分页大小。
            return len(initial_rows)

        # 返回账号配置分页大小。
        return self.page_size

    # 定义总记录数解析方法。
    def resolve_total_count(self, table_data, current_total):

        """
        解析分页总记录数。

        :param table_data: 表格数据对象。
        :type table_data: dict
        :param current_total: 已解析的总记录数。
        :type current_total: int | None
        :return: 总记录数。
        :rtype: int | None
        """

        # 返回已存在的总记录数。
        if current_total is not None:

            # 返回当前总记录数。
            return current_total

        # 读取总记录数字段。
        total_count = table_data.get("total")

        # 返回数字型总记录数。
        if total_count not in [None, ""]:

            # 返回整型总记录数。
            return int(float(total_count))

        # 返回未知总记录数。
        return None

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验捷助数据中心数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in ["购进流向", "配送流向", "库存"]:

            # 抛出数据类型未接入异常。
            raise ValueError(f"安徽华人健康暂未接入数据类型：{data_type}")

    # 定义默认表头构建方法。
    def build_default_headers(self, data_type):

        """
        构建默认输出表头配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 表头配置。
        :rtype: list[tuple[str, str]]
        """

        # 定义流向类默认表头。
        flow_headers = [("日期", "currDate"), ("单据编号", "djbh"), ("销售方代码", "salesCode"), ("销售方名称", "salesName"), ("采购方代码", "purchaseCode"), ("采购方名称", "purchaseName"), ("商品编码", "goodsCode"), ("商品名称", "goodsName"), ("商品规格", "goodsSpec"), ("生产厂家", "manufacturer"), ("批号", "lotNo"), ("单位", "packUnits"), ("数量", "qty"), ("销售单价", "unitPrice"), ("金额", "amount")]

        # 判断当前类型是否为库存。
        if data_type == "库存":

            # 返回库存默认表头。
            return [("日期", "rq"), ("公司代码", "companyCode"), ("公司名称", "companyName"), ("商品编码", "spbh"), ("商品名称", "goodsName"), ("商品规格", "goodsSpec"), ("生产厂家", "manufacturer"), ("批号", "lotNo"), ("单位", "packUnits"), ("数量", "qty"), ("协议成本", "xycb"), ("失效期", "sxq"), ("货位", "position")]

        # 返回流向默认表头。
        return flow_headers

    # 定义 JSON POST 请求方法。
    def post_json(self, url, payload, with_token=False):

        """
        提交 JSON 请求。

        :param url: 请求地址。
        :type url: str
        :param payload: 请求体字段。
        :type payload: dict
        :param with_token: 是否携带登录令牌。
        :type with_token: bool
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 序列化 JSON 请求体。
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 构建 JSON 请求头。
        headers = self.build_json_headers(with_token=with_token)

        # 发送 POST 请求。
        return self.http.request("POST", url, headers=headers, data=body, timeout=90)

    # 定义 JSON 请求头构建方法。
    def build_json_headers(self, with_token=False):

        """
        构建 JSON 请求头。

        :param with_token: 是否携带登录令牌。
        :type with_token: bool
        :return: JSON 请求头。
        :rtype: dict
        """

        # 构建基础 JSON 请求头。
        headers = {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6", "Connection": "keep-alive", "Content-Type": "application/json;charset=UTF-8", "Origin": self.origin_url, "Referer": self.login_page_url, "User-Agent": self.http.user_agent()}

        # 判断是否需要携带登录令牌。
        if with_token and self.login_token:

            # 写入平台访问令牌请求头。
            headers["accessToken"] = self.login_token

        # 返回 JSON 请求头。
        return headers

    # 定义 JSON 响应解析方法。
    def decode_json_response(self, result):

        """
        解析 JSON 响应体。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: JSON 响应数据。
        :rtype: dict
        """

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 处理空响应。
        if not response_text:

            # 返回空响应结构。
            return {}

        # 返回 JSON 响应数据。
        return json.loads(response_text)

    # 定义响应成功判断方法。
    def is_success_response(self, response_data):

        """
        判断接口响应是否成功。

        :param response_data: 接口响应数据。
        :type response_data: dict
        :return: 是否成功。
        :rtype: bool
        """

        # 返回接口状态判断结果。
        return str(response_data.get("code")) == "00"




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


