# -*- coding: utf-8 -*-
"""
厦门片仔癀宏仁供应商流向平台协议适配器。

本模块负责厦门片仔癀宏仁供应商流向平台的协议登录、验证码识别、Cookie 保存和后续业务接口扩展。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入随机数模块。
import random

# 导入时间模块。
import time

# 导入日期时间解析对象。
from datetime import datetime

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

# 导入通用逆向加密函数。
from ddi_framework import aes_cbc_pkcs7_base64


# 定义厦门片仔癀宏仁供应商流向平台协议适配器。
class PzhhrPlatform(BasePlatform):

    """
    厦门片仔癀宏仁供应商流向平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 厦门片仔癀宏仁平台适配器实例。
    :rtype: PzhhrPlatform
    """

    # 定义厦门片仔癀宏仁适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化厦门片仔癀宏仁平台适配器。

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
        self.login_page_url = account.get("登录页", "https://zlcx.hrpzh.com/drugqc/home/login?type=flowLogin")

        # 保存平台根地址。
        self.base_url = self.login_page_url.split("/drugqc/", 1)[0]

        # 保存业务上下文地址。
        self.context_url = urljoin(self.base_url, "/drugqc/home")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", urljoin(self.context_url + "/", "flowLogin"))

        # 保存验证码接口地址。
        self.captcha_api_url = account.get("验证码接口", urljoin(self.context_url + "/", "captcha.jpg"))

        # 保存登录成功后的首页地址。
        self.index_url = account.get("首页", urljoin(self.context_url + "/", "index?type=flow"))

        # 保存供应商流向分页查询接口地址。
        self.distribution_query_url = account.get("供应商流向接口", urljoin(self.context_url + "/", "flow/bmsBfsFlowQueryV/listData"))

        # 保存进货明细分页查询接口地址。
        self.purchase_query_url = account.get("进货明细接口", urljoin(self.context_url + "/", "flow/bmsSnsSuDtlV/listData"))

        # 保存库存明细分页查询接口地址。
        self.stock_query_url = account.get("库存明细接口", urljoin(self.context_url + "/", "flow/bmsSnsQtylstV/listData"))

        # 保存默认分页大小。
        self.page_size = int(account.get("分页大小", 100))

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化验证码处理器。
        self.captcha_solver = CaptchaSolver()

    # 定义厦门片仔癀宏仁登录方法。
    def login(self):

        """
        执行厦门片仔癀宏仁协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("片仔癀宏仁登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 请求登录页并初始化 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 执行带验证码重试的登录流程。
        return self.login_with_captcha_retry()

    # 定义带验证码重试的登录方法。
    def login_with_captcha_retry(self, max_retries=6):

        """
        使用验证码重试机制执行登录。

        :param max_retries: 最大验证码刷新次数。
        :type max_retries: int
        :return: 登录结果。
        :rtype: dict
        """

        # 初始化最后一次失败原因。
        last_error = ""

        # 循环获取验证码并提交登录。
        for retry_index in range(max_retries):

            # 打印验证码尝试日志。
            self.ph.info(self.ph.kv("图片验证码尝试", f"第 {retry_index + 1}/{max_retries} 次", "cyan"))

            # 记录当前尝试的异常。
            try:

                # 获取验证码图片字节。
                captcha_bytes = self.get_captcha_image()

                # 识别验证码文本。
                captcha_text = self.solve_captcha_text(captcha_bytes)

                # 打印验证码识别完成日志。
                self.ph.info(self.ph.kv("图片验证码识别完成", f"长度={len(captcha_text)}", "cyan"))

                # 构建登录请求体。
                payload = self.build_login_payload(captcha_text)

                # 打印正式登录请求日志。
                self.ph.info(self.ph.join(self.ph.kv("提交正式登录请求", "/drugqc/home/flowLogin", "cyan"), self.ph.kv("公司", self.account.get("公司名称"), "yellow")))

                # 发送登录表单请求。
                result = self.http.post_form(self.login_api_url, payload, self.login_page_url)

                # 解析登录响应。
                login_result = self.decode_login_result(result)

                # 判断登录是否成功。
                if self.is_login_success(login_result):

                    # 打印登录成功日志。
                    self.ph.success(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"))

                    # 返回登录结果。
                    return login_result

                # 记录登录失败原因。
                last_error = self.extract_login_message(login_result)

                # 打印验证码或登录失败日志。
                self.ph.warning("登录校验未通过，准备刷新验证码")

            # 处理验证码识别或登录提交异常。
            except Exception as error:

                # 记录当前异常原因。
                last_error = str(error)

                # 打印验证码处理失败日志。
                self.ph.warning("图片验证码识别未通过，准备刷新验证码")

            # 最后一轮失败后跳过等待。
            if retry_index >= max_retries - 1:

                # 进入下一步失败处理。
                continue

            # 计算失败后的等待秒数。
            delay_seconds = random.uniform(2.2, 4.4)

            # 打印等待日志。
            self.ph.wait(self.ph.kv("验证码失败后等待，预计", f"{delay_seconds:.1f} 秒", "cyan"))

            # 等待后再刷新验证码。
            time.sleep(delay_seconds)

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 登录失败：{last_error}")

    # 定义验证码图片获取方法。
    def get_captcha_image(self):

        """
        获取登录验证码图片。

        :return: 验证码图片字节流。
        :rtype: bytes
        """

        # 构建带时间戳的验证码地址。
        captcha_url = f"{self.captcha_api_url}?t={int(time.time() * 1000)}"

        # 打印验证码请求日志。
        self.ph.info("请求图片验证码: /drugqc/home/captcha.jpg")

        # 请求验证码图片。
        result = self.http.get(captcha_url, referer=self.login_page_url)

        # 返回验证码图片字节。
        return result.body

    # 定义验证码文本识别方法。
    def solve_captcha_text(self, captcha_bytes):

        """
        识别登录验证码文本。

        :param captcha_bytes: 验证码图片字节流。
        :type captcha_bytes: bytes
        :return: 验证码文本。
        :rtype: str
        """

        # 执行普通图片验证码识别。
        captcha_text = self.captcha_solver.solve_text_image(captcha_bytes, min_length=4)

        # 清洗验证码数字文本。
        cleaned_text = "".join([char for char in captcha_text if char.isdigit()])

        # 校验验证码文本是否为空。
        if len(cleaned_text) < 4:

            # 抛出验证码识别异常。
            raise RuntimeError("图片验证码识别为空")

        # 返回清洗后的验证码文本。
        return cleaned_text

    # 定义登录请求体构建方法。
    def build_login_payload(self, captcha_text):

        """
        构建厦门片仔癀宏仁登录请求体。

        :param captcha_text: 验证码文本。
        :type captcha_text: str
        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录表单字段。
        return {
            "username": self.encrypt_login_field(self.clean_login_name()),
            "password": self.encrypt_login_field(self.clean_login_password()),
            "entryid": self.clean_entry_id(),
            "captcha": captcha_text,
        }

    # 定义登录字段加密方法。
    def encrypt_login_field(self, plain_text):

        """
        加密登录表单字段。

        :param plain_text: 登录字段明文。
        :type plain_text: str
        :return: 登录字段密文。
        :rtype: str
        """

        # 返回 AES-CBC-PKCS7-Base64 密文。
        return aes_cbc_pkcs7_base64(plain_text, "hrdrugqcForToKey", "hrdrugqcForTo_Iv")

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析厦门片仔癀宏仁登录响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 登录响应数据。
        :rtype: dict
        """

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 返回 JSON 响应数据。
        return json.loads(response_text)

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断登录响应是否表示成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 返回登录成功标记。
        return bool(login_result.get("success"))

    # 定义登录响应消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取登录响应消息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录响应消息。
        :rtype: str
        """

        # 返回响应消息或默认成功文本。
        return str(login_result.get("msg") or login_result.get("message") or login_result)

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

    # 定义公司编码清洗方法。
    def clean_entry_id(self):

        """
        读取清洗后的公司编码。

        :return: 公司编码。
        :rtype: str
        """

        # 返回去除两端空白后的公司编码。
        return str(self.account.get("公司编码", "")).strip()

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

    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询厦门片仔癀宏仁流向数据。

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
        query_result = self.query_pzhhr_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["data"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出厦门片仔癀宏仁流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: 导出目录。
        :type output_dir: str | None
        :return: 导出结果。
        :rtype: str
        """

        # 使用分页查询结果生成本地 Excel 文件。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询厦门片仔癀宏仁流向数据并生成 Excel。

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

        # 查询指定类型完整响应。
        query_result = self.query_pzhhr_data(data_type, start_date, end_date)

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["data"], query_result["columns"], output_path, data_type)

        # 打印 Excel 保存日志。
        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{query_result['count']} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义片仔癀宏仁数据查询方法。
    def query_pzhhr_data(self, data_type, start_date, end_date):

        """
        查询片仔癀宏仁指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准化查询结果。
        :rtype: dict
        """

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 校验日期类数据的开始日期。
        if data_type != "库存" and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验日期类数据的结束日期。
        if data_type != "库存" and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "无", "cyan"), self.ph.kv("结束日期", end_date or "无", "cyan")))

        # 读取分页查询接口地址。
        query_url = self.build_query_url(data_type)

        # 读取查询页面来源地址。
        referer = self.build_query_referer(data_type)

        # 初始化分页页码。
        page_no = 1

        # 初始化查询结果容器。
        rows = []

        # 初始化总记录数。
        total_count = None

        # 循环请求全部分页数据。
        while True:

            # 构建当前页查询表单。
            payload = self.build_query_payload(data_type, start_date, end_date, page_no)

            # 打印当前页查询日志。
            self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", f"page={page_no}", "cyan"), self.ph.kv("size", self.page_size, "yellow")))

            # 发送分页查询表单请求。
            result = self.http.post_form(query_url, payload, referer)

            # 解析分页查询响应。
            response_data = self.decode_query_result(result)

            # 读取当前页记录列表。
            page_rows = response_data.get("records") or []

            # 校验当前页记录结构。
            if not isinstance(page_rows, list):

                # 抛出响应结构异常。
                raise RuntimeError(f"{data_type}查询失败：records 字段不是列表")

            # 追加当前页记录。
            rows.extend(page_rows)

            # 读取服务端总记录数。
            total_count = int(response_data.get("total") or len(rows))

            # 读取服务端总页数。
            total_pages = int(response_data.get("pages") or self.calculate_total_pages(total_count))

            # 打印当前页解析日志。
            self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(page_rows)} 条", "green"), self.ph.kv("累计", f"{len(rows)} 条", "cyan"), self.ph.kv("总数", f"{total_count} 条", "yellow")))

            # 判断是否已经请求到最后一页。
            if page_no >= total_pages or len(rows) >= total_count:

                # 结束分页循环。
                break

            # 递增下一页页码。
            page_no += 1

            # 执行分页间隔等待。
            time.sleep(random.uniform(0.2, 0.6))

        # 构建 Excel 列映射。
        columns = self.build_excel_columns(data_type, rows)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{len(rows)} 条", "green"), self.ph.kv("页数", f"{page_no} 页", "cyan")))

        # 返回标准化查询结果。
        return {"data": rows, "columns": columns, "count": total_count if total_count is not None else len(rows)}

    # 定义查询接口地址构建方法。
    def build_query_url(self, data_type):

        """
        构建片仔癀宏仁分页查询接口地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 分页查询接口地址。
        :rtype: str
        """

        # 返回配送流向查询接口。
        if data_type == "配送流向":

            # 返回供应商流向接口地址。
            return self.distribution_query_url

        # 返回购进流向查询接口。
        if data_type == "购进流向":

            # 返回进货明细接口地址。
            return self.purchase_query_url

        # 返回库存查询接口。
        if data_type == "库存":

            # 返回库存明细接口地址。
            return self.stock_query_url

        # 抛出未接入类型异常。
        raise NotImplementedError(f"当前片仔癀宏仁暂未接入: {data_type}")

    # 定义查询来源页构建方法。
    def build_query_referer(self, data_type):

        """
        构建片仔癀宏仁查询页面来源地址。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询页面来源地址。
        :rtype: str
        """

        # 返回配送流向页面地址。
        if data_type == "配送流向":

            # 返回供应商流向页面地址。
            return urljoin(self.context_url + "/", "flow/bmsBfsFlowQueryV")

        # 返回购进流向页面地址。
        if data_type == "购进流向":

            # 返回进货明细页面地址。
            return urljoin(self.context_url + "/", "flow/bmsSnsSuDtlV")

        # 返回库存页面地址。
        if data_type == "库存":

            # 返回库存明细页面地址。
            return urljoin(self.context_url + "/", "flow/bmsSnsQtylstV")

        # 抛出未接入类型异常。
        raise NotImplementedError(f"当前片仔癀宏仁暂未接入: {data_type}")

    # 定义查询表单构建方法。
    def build_query_payload(self, data_type, start_date, end_date, page_no):

        """
        构建片仔癀宏仁分页查询表单。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_no: 当前页码。
        :type page_no: int
        :return: 分页查询表单。
        :rtype: dict
        """

        # 构建通用分页字段。
        payload = {"pageSize": self.page_size, "pageNo": page_no, "size": self.page_size, "current": page_no}

        # 写入配送流向筛选字段。
        if data_type == "配送流向":

            # 返回配送流向分页表单。
            return dict(payload, beginCreateTime=start_date, endCreateTime=end_date, customname="", goodsname="")

        # 写入购进流向筛选字段。
        if data_type == "购进流向":

            # 返回购进流向分页表单。
            return dict(payload, beginCreateTime=start_date, endCreateTime=end_date, goodsname="")

        # 写入库存筛选字段。
        if data_type == "库存":

            # 返回库存分页表单。
            return dict(payload, goodsname="", goodsid="", ascs="goodsname")

        # 抛出未接入类型异常。
        raise NotImplementedError(f"当前片仔癀宏仁暂未接入: {data_type}")

    # 定义查询响应解析方法。
    def decode_query_result(self, result):

        """
        解析片仔癀宏仁分页查询响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 分页查询响应数据。
        :rtype: dict
        """

        # 解码分页查询响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 返回 JSON 响应数据。
        return json.loads(response_text)

    # 定义总页数计算方法。
    def calculate_total_pages(self, total_count):

        """
        根据总记录数计算总页数。

        :param total_count: 总记录数。
        :type total_count: int
        :return: 总页数。
        :rtype: int
        """

        # 空记录时返回一页。
        if total_count <= 0:

            # 返回一页。
            return 1

        # 返回向上取整后的页数。
        return (total_count + self.page_size - 1) // self.page_size

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验片仔癀宏仁数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 定义当前平台已接入的数据类型。
        supported_types = ["配送流向", "购进流向", "库存"]

        # 校验数据类型是否存在于已接入列表。
        if data_type not in supported_types:

            # 抛出未接入类型异常。
            raise NotImplementedError(f"当前片仔癀宏仁暂未接入: {data_type}")

    # 定义 Excel 列映射构建方法。
    def build_excel_columns(self, data_type, rows):

        """
        构建片仔癀宏仁 Excel 列映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :return: Excel 列映射。
        :rtype: dict
        """

        # 读取指定类型预设列映射。
        columns = self.build_predefined_columns(data_type)

        # 遍历查询结果补充未预设字段。
        for row in rows:

            # 遍历当前数据行字段。
            for field_name in row.keys():

                # 补充未预设字段。
                columns.setdefault(field_name, field_name)

        # 返回完整列映射。
        return columns

    # 定义预设列映射构建方法。
    def build_predefined_columns(self, data_type):

        """
        构建片仔癀宏仁预设 Excel 列映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 预设 Excel 列映射。
        :rtype: dict
        """

        # 返回配送流向列映射。
        if data_type == "配送流向":

            # 返回供应商流向主要字段。
            return {"keptate": "业务日期", "customname": "客户名称", "goodsname": "通用名", "goodsstype": "规格", "goodsunit": "单位", "goodsqty": "数量", "batchid": "批号", "lotno": "批号编码", "proddate": "生产日期", "invaliddate": "有效期至", "factoryname": "生产厂家", "supplyname": "供应商", "transopname": "配送客户"}

        # 返回购进流向列映射。
        if data_type == "购进流向":

            # 返回进货明细主要字段。
            return {"keptate": "业务日期", "credate": "创建日期", "billtype": "单据类型", "goodsname": "通用名", "goodsstype": "规格", "goodsunit": "单位", "goodsqty": "数量", "batchid": "批号", "lotno": "批号编码", "proddate": "生产日期", "invaliddate": "有效期至", "factoryname": "生产厂家", "supplyname": "供应商"}

        # 返回库存列映射。
        if data_type == "库存":

            # 返回库存明细主要字段。
            return {"goodsname": "通用名", "currencyname": "商品名", "goodsstype": "规格", "goodsunit": "单位", "goodsqty": "库存数量", "batchid": "批号", "lotno": "批号编码", "proddate": "生产日期", "invaliddate": "有效期至", "factoryname": "生产厂家", "supplyname": "供应商", "companyname": "公司名称", "unitprice": "单价"}

        # 抛出未接入类型异常。
        raise NotImplementedError(f"当前片仔癀宏仁暂未接入: {data_type}")

    # 定义输出文件名构建方法。
    def build_output_file_name(self, data_type, start_date, end_date):

        """
        构建片仔癀宏仁输出文件名。

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

        # 读取库存日期字符串。
        stock_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # 解析导出日期。
        date_value = datetime.strptime(stock_date, "%Y-%m-%d")

        # 返回 yy.m.d 标签。
        return f"{date_value.year % 100}.{date_value.month}.{date_value.day}"

    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, columns, output_path, sheet_name):

        """
        写入片仔癀宏仁查询结果到 Excel。

        :param rows: 查询结果数据行。
        :type rows: list[dict]
        :param columns: Excel 列映射。
        :type columns: dict
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
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = sheet_name[:31]

        # 读取接口字段列表。
        field_names = list(columns.keys())

        # 写入中文表头行。
        worksheet.append([columns[field_name] for field_name in field_names])

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按列映射顺序组装一行数据。
            worksheet.append([row.get(field_name, "") for field_name in field_names])

        # 遍历所有导出列设置列宽。
        for column_index, header_name in enumerate(columns.values(), start=1):

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
