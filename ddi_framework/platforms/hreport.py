# -*- coding: utf-8 -*-
"""
深圳市南北医药供应商查询系统协议适配器。

本模块负责深圳市南北医药供应商查询系统的协议登录、Cookie 保存和后续查询接口扩展。
"""

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入表单编码函数。
from urllib.parse import urlencode



# 导入请求构造对象。
from urllib.request import Request



# 导入协议请求客户端。
from ddi_framework import HttpResult

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入通用逆向摘要函数。
from ddi_framework import md5_hex


# 定义禁止自动重定向处理器。


# 定义HReport 供应商查询系统协议适配器。
class HreportPlatform(BasePlatform):

    """
    HReport 供应商查询系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: HReport 平台适配器实例。
    :rtype: HreportPlatform
    """

    # 定义HReport 适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化HReport 平台适配器。

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
        self.login_page_url = account.get("登录页", "http://121.15.7.106:7006/hreport-manager/login")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", "http://121.15.7.106:7006/hreport-manager/j_spring_security_check")

        # 保存登录成功跳转路径。
        self.success_location = account.get("登录成功路径", "/hreport-manager/login/loginCheck")

        # 保存登录失败跳转路径。
        self.failure_location = account.get("登录失败路径", "/hreport-manager/login?error=1")

        # 保存登录成功首页地址。
        self.home_page_url = account.get("首页", "http://121.15.7.106:7006/hreport-manager/login/loginCheck")

        # 保存报表页面地址。
        self.report_page_url = account.get("报表页", "http://121.15.7.106:7006/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp")

        # 保存报表参数接口地址。
        self.param_api_url = account.get("报表参数接口", "http://121.15.7.106:7006/hreport-manager/vendorReportMgr/qryParamList")

        # 保存查询接口地址。
        self.query_api_url = account.get("查询接口", "http://121.15.7.106:7006/hreport-manager/vendorReportMgr/qryReportMeanInfo")

        # 保存平台根地址。
        self.base_url = self.login_page_url.split("/hreport-manager/", 1)[0]

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.base_url)

    # 定义HReport登录方法。
    def login(self):

        """
        执行HReport协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("HReport登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.kv("访问登录页", self.login_page_url, "cyan"))

        # 访问登录页以初始化站点 Cookie。
        self.http.get(self.login_page_url)

        # 打印登录页访问完成日志。
        self.ph.success(self.ph.kv("登录页访问完成，当前 Cookie 数", len(list(self.http.cookie_jar)), "green"))

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 打印正式登录请求日志。
        self.ph.info(self.ph.kv("提交正式登录请求", "/hreport-manager/j_spring_security_check", "cyan"))

        # 提交不自动重定向的登录表单。
        result = self.post_login_form_without_redirect(payload)

        # 解析登录响应。
        login_result = self.decode_login_result(result)

        # 校验登录结果。
        if not self.is_login_success(login_result):

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 正式登录失败：{self.extract_login_message(login_result)}")

        # 打印登录成功日志。
        self.ph.success(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"))

        # 初始化登录成功后的系统首页会话。
        self.load_home_page()

        # 返回登录结果。
        return login_result

    # 定义登录成功首页加载方法。
    def load_home_page(self):

        """
        加载登录成功后的系统首页。

        :return: 首页响应结果。
        :rtype: HttpResult
        """

        # 访问首页以完成 Spring Security 登录后的会话初始化。
        result = self.http.get(self.home_page_url, referer=self.login_page_url)

        # 返回首页响应结果。
        return result

    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建HReport登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 读取清洗后的登录账号。
        login_name = self.clean_login_name()

        # 读取清洗后的登录密码。
        login_password = self.clean_login_password()

        # 计算登录密码的 MD5 摘要。
        encrypted_password = md5_hex(login_password)

        # 初始化 Spring Security 登录表单字段。
        payload = {"j_username": login_name, "j_password": encrypted_password}

        # 读取账号配置中的验证码字段名。
        captcha_field_name = str(self.account.get("登录验证码字段", "")).strip()

        # 判断当前站点是否要求提交验证码字段。
        if captcha_field_name:

            # 读取账号配置中的验证码固定值。
            captcha_value = str(self.account.get("登录验证码固定值", "")).strip() or "abcd"

            # 写入登录验证码字段。
            payload[captcha_field_name] = captcha_value

        # 返回 Spring Security 登录表单字段。
        return payload

    # 定义登录表单提交方法。
    def post_login_form_without_redirect(self, payload):

        """
        提交不跟随重定向的HReport登录表单。

        :param payload: 登录请求体。
        :type payload: dict
        :return: HTTP 响应结果。
        :rtype: HttpResult
        """

        # 构建登录请求头。
        headers = self.build_login_headers()

        # 编码表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 以禁止跟随重定向方式提交登录并保留原始响应。
        return self.http.request("POST", self.login_api_url, headers, data=data, timeout=30, allow_http_error=True, follow_redirects=False)

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建HReport登录请求头。

        :return: 登录请求头。
        :rtype: dict
        """

        # 返回浏览器表单登录请求头。
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.base_url,
            "Referer": self.login_page_url,
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.http.user_agent(),
        }

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析HReport登录响应。

        :param result: HTTP 响应结果。
        :type result: HttpResult
        :return: 登录响应数据。
        :rtype: dict
        """

        # 读取登录响应跳转地址。
        location = result.headers.get("Location", "")

        # 返回登录响应摘要。
        return {"status_code": result.status_code, "location": location, "message": self.build_login_message(result.status_code, location)}

    # 定义登录响应消息构建方法。
    def build_login_message(self, status_code, location):

        """
        构建HReport登录响应消息。

        :param status_code: HTTP 状态码。
        :type status_code: int
        :param location: 响应跳转地址。
        :type location: str
        :return: 登录响应消息。
        :rtype: str
        """

        # 判断响应是否跳转到登录成功确认页。
        if status_code == 302 and self.success_location in location:

            # 返回登录成功消息。
            return "登录成功"

        # 判断响应是否跳转到登录失败页。
        if status_code == 302 and self.failure_location in location:

            # 返回登录失败消息。
            return "用户名或密码错误"

        # 返回无法识别的跳转状态。
        return f"HTTP {status_code} | Location={location}"

    # 定义登录成功判断方法。
    def is_login_success(self, login_result):

        """
        判断HReport登录是否成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 读取响应状态码。
        status_code = int(login_result.get("status_code", 0))

        # 读取响应跳转地址。
        location = str(login_result.get("location", ""))

        # 判断是否跳转到登录成功确认页。
        return status_code == 302 and self.success_location in location

    # 定义登录响应消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取HReport登录响应消息。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录响应消息。
        :rtype: str
        """

        # 返回登录响应消息。
        return str(login_result.get("message", login_result))

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


    # 定义流向查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询HReport流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 查询指定类型数据。
        query_result = self.query_hreport_data(data_type, start_date, end_date)

        # 返回查询结果数据行。
        return query_result["rows"]

    # 定义流向导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        导出HReport流向数据。

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

        # 判断当前商业是否使用平台导出接口。
        if self.should_use_platform_export():

            # 使用平台原始导出接口生成 Excel 文件。
            return self.export_report_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

        # 使用查询接口结果生成本地 Excel 文件。
        return self.query_report_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义平台导出策略判断方法。
    def should_use_platform_export(self):

        """
        判断当前商业是否使用平台原始导出接口。

        :return: 是否使用平台原始导出接口。
        :rtype: bool
        """

        # 返回账号配置中的平台导出策略。
        return bool(self.account.get("使用平台导出", True))

    # 定义查询结果 Excel 落地方法。
    def query_report_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询HReport流向数据并写入本地 Excel。

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

        # 查询平台报表数据。
        query_result = self.query_hreport_data(data_type, start_date, end_date)

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 写入查询结果 Excel。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"))

        # 返回 Excel 文件路径。
        return output_path

    # 定义查询落地 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询HReport流向数据并生成 Excel。

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

        # 判断当前商业是否使用平台导出接口。
        if self.should_use_platform_export():

            # 使用平台原始导出接口生成 Excel 文件。
            return self.export_report_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

        # 使用查询接口结果生成本地 Excel 文件。
        return self.query_report_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义平台 Excel 导出方法。
    def export_report_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        调用HReport 平台原始导出接口并生成本地 Excel。

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

        # 校验数据类型是否已接入。
        self.validate_data_type(data_type)

        # 校验流向类查询开始日期。
        if self.requires_date_range(data_type) and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"导出{data_type}必须提供 start_date")

        # 校验流向类查询结束日期。
        if self.requires_date_range(data_type) and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"导出{data_type}必须提供 end_date")

        # 使用调用方指定目录或默认下载目录。
        output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # 使用调用方指定目录或默认下载目录。
        os.makedirs(output_dir, exist_ok=True)

        # 初始化报表页面上下文。
        self.load_report_page()

        # 加载报表参数与表头配置。
        report_config = self.load_report_config(data_type)

        # 构建平台导出请求体。
        payload = self.build_export_payload(data_type, start_date, end_date)

        # 构建临时 xls 文件路径。
        xls_path = os.path.join(output_dir, self.build_output_file_name(data_type, start_date, end_date).replace(".xlsx", ".xls"))

        # 构建 Excel 文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 构建 Excel 输出路径。
        output_path = os.path.join(output_dir, file_name)

        # 打印平台导出请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"导出{data_type}", "/vendorReportMgr/exportReportExcel", "cyan"), self.ph.kv("funcId", report_config["func_id"], "yellow")))

        # 请求平台原始 Excel。
        result = self.post_export_form(payload, report_config["func_id"])

        # 保存平台原始 Excel。
        self.save_binary_file(result.body, xls_path)

        # 转换为标准 xlsx 文件。
        converted_path = self.convert_xls_to_xlsx(xls_path, output_path)

        # 判断是否完成 xlsx 转换。
        if converted_path == output_path and os.path.exists(xls_path):

            # 删除临时 xls 文件。
            os.remove(xls_path)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(converted_path), "green"))

        # 返回 Excel 文件路径。
        return converted_path

    # 定义平台导出请求体构建方法。
    def build_export_payload(self, data_type, start_date, end_date):

        """
        构建HReport 平台导出请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 导出请求体。
        :rtype: dict
        """

        # 构建基础导出字段。
        payload = {"userid": "", "warecode": ""}

        # 补充购进流向特有字段。
        if data_type == "购进流向":

            # 写入采购员筛选字段。
            payload["buyer"] = ""

            # 写入单据号筛选字段。
            payload["billcode"] = ""

        # 补充流向类日期字段。
        if self.requires_date_range(data_type):

            # 写入开始日期。
            payload["beginDate"] = start_date

            # 写入结束日期。
            payload["endDate"] = end_date

        # 返回导出请求体。
        return payload

    # 定义平台导出表单提交方法。
    def post_export_form(self, payload, func_id):

        """
        提交HReport 平台导出表单。

        :param payload: 导出请求体。
        :type payload: dict
        :param func_id: 报表功能编号。
        :type func_id: str
        :return: 导出响应。
        :rtype: HttpResult
        """

        # 构建导出接口地址。
        export_url = f"{self.base_url}/hreport-manager/vendorReportMgr/exportReportExcel?funcId={func_id}"

        # 构建表单请求头。
        headers = self.build_export_headers()

        # 编码表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送导出请求。
        return self.http.request("POST", export_url, headers=headers, data=data, timeout=300)

    # 定义导出请求头构建方法。
    def build_export_headers(self):

        """
        构建HReport 平台导出请求头。

        :return: 导出请求头。
        :rtype: dict
        """

        # 返回浏览器表单导出请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded", "Origin": self.base_url, "Referer": self.home_page_url, "Upgrade-Insecure-Requests": "1", "User-Agent": self.http.user_agent()}

    # 定义二进制文件保存方法。
    def save_binary_file(self, content, output_path):

        """
        保存二进制响应到本地文件。

        :param content: 二进制文件内容。
        :type content: bytes
        :param output_path: 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 创建输出目录。
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 删除已有同名文件。
        self.remove_existing_file(output_path)

        # 写入二进制文件。
        with open(output_path, "wb") as file_obj:

            # 写入响应内容。
            file_obj.write(content)

    # 定义 xls 转 xlsx 方法。
    def convert_xls_to_xlsx(self, xls_path, xlsx_path):

        """
        将平台返回的 xls 文件转换为 xlsx 文件。

        :param xls_path: 原始 xls 文件路径。
        :type xls_path: str
        :param xlsx_path: 目标 xlsx 文件路径。
        :type xlsx_path: str
        :return: 可用 Excel 文件路径。
        :rtype: str
        """

        # 删除已有目标文件。
        self.remove_existing_file(xlsx_path)

        # 初始化工作簿引用。
        workbook = None

        # 初始化 Excel 应用引用。
        excel_app = None

        # 捕获 Excel COM 转换异常。
        try:

            # 导入 COM 客户端。
            import win32com.client

            # 启动 Excel 应用。
            excel_app = win32com.client.DispatchEx("Excel.Application")

            # 设置 Excel 后台运行。
            excel_app.Visible = False

            # 禁用弹窗提示。
            excel_app.DisplayAlerts = False

            # 打开原始 xls 文件。
            workbook = excel_app.Workbooks.Open(os.path.abspath(xls_path))

            # 另存为 xlsx 文件。
            workbook.SaveAs(os.path.abspath(xlsx_path), FileFormat=51)

            # 返回 xlsx 文件路径。
            return xlsx_path

        # 处理转换失败场景。
        except Exception as error:

            # 打印转换失败提示。
            self.ph.warning(f"xls 转 xlsx 失败，保留平台原始文件: {error}")

            # 返回原始 xls 文件路径。
            return xls_path

        # 清理 Excel COM 进程资源。
        finally:

            # 判断工作簿是否已经打开。
            if workbook is not None:

                # 捕获工作簿关闭异常。
                try:

                    # 关闭工作簿对象。
                    workbook.Close(False)

                # 忽略工作簿关闭阶段异常。
                except Exception:

                    # 保持导出转换结果不受关闭阶段影响。
                    pass

            # 判断 Excel 应用是否已经启动。
            if excel_app is not None:

                # 捕获 Excel 应用退出异常。
                try:

                    # 退出 Excel 应用。
                    excel_app.Quit()

                # 忽略 Excel 应用退出阶段异常。
                except Exception:

                    # 保持导出转换结果不受退出阶段影响。
                    pass

    # 定义HReport数据查询方法。
    def query_hreport_data(self, data_type, start_date, end_date):

        """
        查询HReport指定类型数据。

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
        if self.requires_date_range(data_type) and not start_date:

            # 抛出查询开始日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 start_date")

        # 校验流向类查询结束日期。
        if self.requires_date_range(data_type) and not end_date:

            # 抛出查询结束日期缺失异常。
            raise ValueError(f"查询{data_type}必须提供 end_date")

        # 打印查询阶段标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date or "", "cyan"), self.ph.kv("结束日期", end_date or "", "cyan")))

        # 初始化报表页面上下文。
        self.load_report_page()

        # 加载报表参数与表头配置。
        report_config = self.load_report_config(data_type)

        # 查询全部分页数据。
        rows = self.query_all_pages(data_type, start_date, end_date, report_config)

        # 校验配置的流向日期字段位于请求范围内。
        self.validate_business_date_range(data_type, rows, start_date, end_date)

        # 打印查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("查询解析完成", f"{len(rows)} 条", "green"), self.ph.kv("表头数", len(report_config["headers"]), "cyan")))

        # 返回标准查询结果。
        return {"rows": rows, "headers": report_config["headers"]}

    # 定义业务日期范围校验方法。
    def validate_business_date_range(self, data_type, rows, start_date, end_date):

        """
        校验配置的流向业务日期未超出请求范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询原始记录。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 读取当前数据类型配置的业务日期字段。
        date_field = str(self.account.get("业务日期字段", {}).get(data_type, "")).strip()

        # 判断当前类型不要求日期范围校验。
        if not date_field or not start_date or not end_date:

            # 结束无日期字段的查询校验。
            return

        # 提取符合日期格式的业务日期文本。
        business_dates = [str(row.get(date_field, ""))[:10] for row in rows if str(row.get(date_field, ""))[:10].count("-") == 2]

        # 判断当前结果没有可校验日期。
        if not business_dates:

            # 结束空结果日期校验。
            return

        # 判断最早业务日期早于请求开始日期。
        if min(business_dates) < start_date:

            # 抛出最早业务日期超范围异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期早于请求开始日期：{min(business_dates)} < {start_date}")

        # 判断最晚业务日期晚于请求结束日期。
        if max(business_dates) > end_date:

            # 抛出最晚业务日期超范围异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期晚于请求结束日期：{max(business_dates)} > {end_date}")

    # 定义全部分页查询方法。
    def query_all_pages(self, data_type, start_date, end_date, report_config):

        """
        查询HReport全部分页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param report_config: 报表配置。
        :type report_config: dict
        :return: 查询数据行。
        :rtype: list[dict]
        """

        # 构建第一页查询请求体。
        payload = self.build_query_payload(data_type, start_date, end_date, report_config["func_id"])

        # 查询第一页数据。
        first_page_result = self.query_one_page(data_type, payload, report_config["headers"], 1)

        # 初始化累计数据行。
        all_rows = list(first_page_result["rows"])

        # 读取总页数。
        total_pages = first_page_result["total_pages"]

        # 遍历剩余页码。
        for page_number in range(2, total_pages + 1):

            # 构建当前页查询请求体。
            page_payload = dict(payload)

            # 写入当前页码。
            page_payload["pageStart"] = str(page_number)

            # 查询当前页数据。
            page_result = self.query_one_page(data_type, page_payload, report_config["headers"], page_number)

            # 累加当前页数据行。
            all_rows.extend(page_result["rows"])

        # 返回全部数据行。
        return all_rows

    # 定义单页查询方法。
    def query_one_page(self, data_type, payload, headers, page_number):

        """
        查询HReport单页数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param payload: 查询请求体。
        :type payload: dict
        :param headers: 表头列表。
        :type headers: list[str]
        :param page_number: 当前页码。
        :type page_number: int
        :return: 单页查询结果。
        :rtype: dict
        """

        # 打印查询请求日志。
        self.ph.info(self.ph.join(self.ph.kv(f"请求{data_type}分页", "/vendorReportMgr/qryReportMeanInfo", "cyan"), self.ph.kv("pageStart", page_number, "yellow"), self.ph.kv("funcId", payload["funcId"], "yellow")))

        # 发送查询表单请求。
        result = self.post_query_form(payload)

        # 解析查询响应。
        rows = self.decode_query_rows(result, headers)

        # 解析查询总页数。
        total_pages = self.extract_total_pages(result)

        # 打印当前页完成日志。
        self.ph.success(self.ph.join(self.ph.kv("当前页解析完成", f"{len(rows)} 条", "green"), self.ph.kv("总页数", total_pages, "cyan")))

        # 返回单页查询结果。
        return {"rows": rows, "total_pages": total_pages}

    # 定义报表页面加载方法。
    def load_report_page(self):

        """
        加载HReport报表页面。

        :return: 报表页面响应。
        :rtype: HttpResult
        """

        # 构建 AJAX 页面加载请求头。
        headers = self.build_ajax_headers()

        # 发送报表页面加载请求。
        return self.http.request("GET", self.report_page_url, headers=headers, timeout=60)

    # 定义报表配置加载方法。
    def load_report_config(self, data_type):

        """
        加载HReport报表参数与表头配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表配置。
        :rtype: dict
        """

        # 读取数据类型对应的 funcId。
        func_id = self.build_func_id(data_type)

        # 构建报表参数接口地址。
        param_url = f"{self.param_api_url}?funcId={func_id}"

        # 构建 AJAX 请求头。
        headers = self.build_ajax_headers()

        # 打印报表参数加载日志。
        self.ph.info(self.ph.join(self.ph.kv("加载报表参数", "/vendorReportMgr/qryParamList", "cyan"), self.ph.kv("funcId", func_id, "yellow")))

        # 初始化最后一次解析异常。
        last_error = None

        # 循环请求报表参数并处理偶发非 JSON 响应。
        for attempt_index in range(2):

            # 发送报表参数请求。
            result = self.http.request("POST", param_url, headers=headers, data=b"", timeout=120)

            # 捕获报表参数解析异常。
            try:

                # 解析报表参数响应。
                report_config = self.http.decode_json(result)

                # 解析报表表头列表。
                headers = self.decode_report_headers(report_config)

                # 返回标准报表配置。
                return {"func_id": func_id, "headers": headers, "raw": report_config}

            # 处理平台偶发返回页面文本的场景。
            except Exception as error:

                # 保存最后一次解析异常。
                last_error = error

                # 解码响应摘要用于日志定位。
                response_preview = result.body.decode("utf-8", errors="replace").strip()[:160]

                # 判断是否仍有重试机会。
                if attempt_index == 0:

                    # 打印报表参数重试日志。
                    self.ph.warning(f"报表参数响应不是 JSON，重新加载页面后重试: {response_preview}")

                    # 重新加载登录成功首页。
                    self.load_home_page()

                    # 重新加载报表页面上下文。
                    self.load_report_page()

                    # 进入下一次报表参数请求。
                    continue

                # 抛出带响应摘要的报表参数异常。
                raise RuntimeError(f"{self.company_name} 报表参数解析失败：{last_error}；响应摘要：{response_preview}") from error

        # 抛出未取得报表参数的异常。
        raise RuntimeError(f"{self.company_name} 报表参数加载失败：{last_error}")

    # 定义报表表头解析方法。
    def decode_report_headers(self, report_config):

        """
        解析HReport报表表头。

        :param report_config: 报表配置响应。
        :type report_config: dict
        :return: 表头列表。
        :rtype: list[str]
        """

        # 读取表头文本。
        header_text = str(report_config.get("reportHeader", "")).strip()

        # 校验表头文本是否存在。
        if not header_text:

            # 抛出表头缺失异常。
            raise RuntimeError(f"{self.company_name} 报表表头为空：{report_config}")

        # 返回逗号切分后的表头列表。
        return [header.strip() for header in header_text.split(",") if header.strip()]

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, start_date, end_date, func_id):

        """
        构建HReport查询请求体。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param func_id: 报表功能编号。
        :type func_id: str
        :return: 查询请求体。
        :rtype: dict
        """

        # 读取账号配置中的查询字段模板。
        template_payload = self.account.get("查询字段模板", {}).get(data_type)

        # 判断是否存在当前数据类型的查询字段模板。
        if template_payload:

            # 返回字段模板渲染后的查询请求体。
            return self.render_query_payload_template(template_payload, start_date, end_date, func_id)

        # 构建基础查询表单字段。
        payload = {"userid": "", "warecode": "", "funcId": func_id}

        # 补充购进流向特有字段。
        if data_type == "购进流向":

            # 写入采购员筛选字段。
            payload["buyer"] = ""

            # 写入单据号筛选字段。
            payload["billcode"] = ""

        # 补充流向类日期字段。
        if self.requires_date_range(data_type):

            # 写入开始日期。
            payload["beginDate"] = start_date

            # 写入结束日期。
            payload["endDate"] = end_date

        # 返回查询请求体。
        return payload

    # 定义查询字段模板渲染方法。
    def render_query_payload_template(self, template_payload, start_date, end_date, func_id):

        """
        渲染账号配置中的查询字段模板。

        :param template_payload: 查询字段模板。
        :type template_payload: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param func_id: 报表功能编号。
        :type func_id: str
        :return: 查询请求体。
        :rtype: dict
        """

        # 初始化渲染上下文。
        render_context = {"start_date": start_date or "", "end_date": end_date or "", "func_id": func_id}

        # 初始化查询请求体。
        payload = {}

        # 遍历模板字段。
        for field_name, field_value in template_payload.items():

            # 渲染当前字段值。
            payload[field_name] = str(field_value).format(**render_context)

        # 返回查询请求体。
        return payload

    # 定义查询表单提交方法。
    def post_query_form(self, payload):

        """
        提交HReport查询表单。

        :param payload: 查询请求体。
        :type payload: dict
        :return: 查询响应。
        :rtype: HttpResult
        """

        # 构建 AJAX 表单请求头。
        headers = self.build_ajax_form_headers()

        # 编码表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 发送查询请求。
        return self.http.request("POST", self.query_api_url, headers=headers, data=data, timeout=300)

    # 定义查询响应解析方法。
    def decode_query_rows(self, result, headers):

        """
        解析HReport局部表格响应。

        :param result: 查询响应。
        :type result: HttpResult
        :param headers: 表头列表。
        :type headers: list[str]
        :return: 查询数据行。
        :rtype: list[dict]
        """

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 解析表格单元格行。
        raw_rows = self.parse_table_rows(response_text)

        # 初始化结果行列表。
        rows = []

        # 遍历原始行数据。
        for raw_row in raw_rows:

            # 跳过空行。
            if not raw_row:

                # 进入下一行。
                continue

            # 按表头组装字典行。
            rows.append({header: raw_row[index] if index < len(raw_row) else "" for index, header in enumerate(headers)})

        # 返回结果行列表。
        return rows

    # 定义总页数提取方法。
    def extract_total_pages(self, result):

        """
        从HReport分页摘要中提取总页数。

        :param result: 查询响应。
        :type result: HttpResult
        :return: 总页数。
        :rtype: int
        """

        # 导入 HTML 解析器。
        from bs4 import BeautifulSoup

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 使用 HTML 解析响应。
        soup = BeautifulSoup(response_text, "html.parser")

        # 查找分页摘要容器。
        summary_node = soup.find(id="reportMgrQueryInfoAjaxPageSummary")

        # 处理分页摘要缺失。
        if summary_node is None:

            # 返回默认单页。
            return 1

        # 查找总页数字段。
        page_total_node = summary_node.find("span", class_="page_total")

        # 处理总页数字段缺失。
        if page_total_node is None:

            # 返回默认单页。
            return 1

        # 读取总页数文本。
        page_total_text = page_total_node.get_text(strip=True)

        # 尝试转换总页数。
        try:

            # 返回有效总页数。
            return max(1, int(page_total_text))

        # 处理无法解析的总页数。
        except ValueError:

            # 返回默认单页。
            return 1

    # 定义局部表格行解析方法。
    def parse_table_rows(self, response_text):

        """
        解析HReport返回的 tbody 局部 HTML。

        :param response_text: 局部 HTML 响应文本。
        :type response_text: str
        :return: 原始行列表。
        :rtype: list[list[str]]
        """

        # 导入 HTML 解析器。
        from bs4 import BeautifulSoup

        # 使用 table 容器包裹局部 tr 片段。
        soup = BeautifulSoup(f"<table>{response_text}</table>", "html.parser")

        # 初始化原始行列表。
        rows = []

        # 遍历所有表格行。
        for table_row in soup.find_all("tr"):

            # 读取当前行所有单元格。
            cells = table_row.find_all("td")

            # 跳过没有单元格的占位行。
            if not cells:

                # 进入下一行。
                continue

            # 解析当前行单元格文本。
            row_values = [self.extract_cell_value(cell) for cell in cells]

            # 判断当前行为无数据占位提示。
            if len(row_values) == 1 and row_values[0] in {"暂无信息记录", "暂无数据", "无数据"}:

                # 跳过当前无数据占位行。
                continue

            # 追加当前原始行。
            rows.append(row_values)

        # 返回原始行列表。
        return rows

    # 定义单元格值提取方法。
    def extract_cell_value(self, cell):

        """
        提取HReport表格单元格值。

        :param cell: HTML 单元格节点。
        :type cell: bs4.element.Tag
        :return: 单元格文本。
        :rtype: str
        """

        # 优先读取 title 属性中的完整值。
        title_value = cell.get("title")

        # 判断 title 值是否存在。
        if title_value is not None:

            # 返回清洗后的 title 值。
            return str(title_value).strip()

        # 返回清洗后的单元格可见文本。
        return cell.get_text(" ", strip=True)

    # 定义 AJAX 基础请求头构建方法。
    def build_ajax_headers(self):

        """
        构建HReport AJAX 请求头。

        :return: AJAX 请求头。
        :rtype: dict
        """

        # 返回 AJAX 基础请求头。
        return {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Origin": self.base_url, "Referer": self.home_page_url, "User-Agent": self.http.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    # 定义 AJAX 表单请求头构建方法。
    def build_ajax_form_headers(self):

        """
        构建HReport AJAX 表单请求头。

        :return: AJAX 表单请求头。
        :rtype: dict
        """

        # 构建基础 AJAX 请求头。
        headers = self.build_ajax_headers()

        # 写入表单请求内容类型。
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        # 返回 AJAX 表单请求头。
        return headers

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验HReport数据类型。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已接入。
        if data_type not in ["配送流向", "购进流向", "库存", "纯销流向"]:

            # 抛出数据类型未接入异常。
            raise NotImplementedError(f"当前HReport暂未接入: {data_type}")

    # 定义日期区间要求判断方法。
    def requires_date_range(self, data_type):

        """
        判断当前数据类型是否要求传入日期区间。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 是否要求日期区间。
        :rtype: bool
        """

        # 返回流向类数据的日期区间要求。
        return data_type in ["配送流向", "购进流向", "纯销流向"]

    # 定义报表功能编号构建方法。
    def build_func_id(self, data_type):

        """
        构建HReport报表功能编号。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表功能编号。
        :rtype: str
        """

        # 读取账号配置中的报表功能编号映射。
        mapping = self.account.get("报表功能编号") or {"购进流向": "40", "配送流向": "10006", "库存": "10008"}

        # 返回当前数据类型对应的功能编号。
        return mapping[data_type]


    # 定义库存导出命名日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        解析 HReport 文件命名使用的业务日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 输出命名使用的日期。
        :rtype: str | None
        """

        # 判断当前类型是否为库存。
        if data_type == "库存":

            # 返回库存导出当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向查询开始日期。
        return start_date or end_date



    # 定义通用 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        写入HReport查询结果到 Excel。

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
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = sheet_name[:31]

        # 读取当前数据类型配置的标准字段映射。
        standard_fields = self.account.get("标准字段映射", {}).get(sheet_name, [])

        # 构建标准字段标题列表。
        standard_titles = [title for title, _ in standard_fields]

        # 写入表头行。
        worksheet.append(standard_titles + headers)

        # 遍历查询结果并写入数据行。
        for row in rows:

            # 按表头顺序组装一行数据。
            worksheet.append([row.get(source_field, "") if isinstance(row, dict) else "" for _, source_field in standard_fields] + [row.get(header, "") if isinstance(row, dict) else "" for header in headers])

        # 遍历所有导出列设置列宽。
        for column_index, header_name in enumerate(standard_titles + headers, start=1):

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

        # 删除已有输出文件。
        os.remove(output_path)
