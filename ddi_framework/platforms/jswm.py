# -*- coding: utf-8 -*-
"""
江苏卫民数据智能管理系统协议适配器。

本模块负责江苏卫民供应商自助系统的协议登录、菜单解析、FineReport 报表参数提交、分页读取和本地 Excel 生成。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入日期时间解析对象。
from datetime import datetime

# 导入 URL 表单编码函数。
from urllib.parse import urlencode

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入 FineReport 平台公共骨架。
from ddi_framework.platforms.finereport_common import FineReportPlatformBase


# 定义卫民 FineReport 数据类型与页面配置映射。
REPORT_DEFINITIONS = {
    "购进流向": {
        "pageName": "商品采购流向",
        "reportlet": "sp/yhpurin.cpt",
        "paperWidth": 865,
        "paperHeight": 658,
        "parameters": ["BDATE", "EDATE", "BILLCODE", "BATCHNO", "GOODSCODE", "GOODSNAME", "BUSINESSNAME", "MANUFACTURER"],
        "dateColumn": "日期",
    },
    "配送流向": {
        "pageName": "商品销售流向(明细)",
        "reportlet": "sp/yhjoinout.cpt",
        "paperWidth": 800,
        "paperHeight": 658,
        "parameters": ["BDATE", "EDATE", "BILLCODE", "GOODSCODE", "GOODSNAME", "ZJM", "BATCHNO", "BUSINESSNAME", "MANUFACTURER"],
        "dateColumn": "日期",
    },
    "库存": {
        "pageName": "商品库存查询",
        "reportlet": "sp/yhbalance.cpt",
        "paperWidth": 800,
        "paperHeight": 700,
        "parameters": ["GOODSCODE", "GOODSNAME", "SEARCH", "SPLOGOGRAM", "MANUFACTURER"],
        "dateColumn": "",
    },
}


class JswmPlatform(FineReportPlatformBase):
    """
    江苏卫民数据智能管理系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 江苏卫民平台适配器实例。
    :rtype: JswmPlatform
    """

    def __init__(self, company_name, account, printer=None):
        """
        初始化江苏卫民平台适配器。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param account: 商业账号配置。
        :type account: dict
        :param printer: 日志打印器。
        :type printer: PrintHandler | None
        :return: None。
        :rtype: None
        """

        # 调用 FineReport 公共骨架初始化逻辑。
        super().__init__(company_name, account, printer=printer)

        # 初始化日志打印器。
        self.ph = printer or PrintHandler()

        # 保存系统首页地址。
        self.home_page_url = account.get("首页", f"{self.api_base_url}/trunk/platform/jsp/v2.jsp")

        # 保存菜单接口地址。
        self.menu_api_url = account.get("菜单接口", f"{self.api_base_url}/AjaxAction/getMenuTree.do")

        # 初始化菜单树缓存。
        self.menu_tree = []

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型是否已配置卫民报表。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否存在报表定义。
        if data_type not in REPORT_DEFINITIONS:

            # 抛出数据类型未接入异常。
            raise ValueError(f"江苏卫民平台暂不支持数据类型：{data_type}")

    def login(self):

        """
        执行江苏卫民供应商自助系统协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("江苏卫民登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.join(self.ph.kv("访问登录页", self.login_page_url, "cyan"), self.ph.kv("账号", self.clean_login_name(), "cyan")))

        # 访问登录页以建立站点 Cookie。
        self.http.get(self.login_page_url, referer=self.api_base_url)

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 构建登录请求头。
        headers = self.build_form_headers(self.login_page_url)

        # 编码表单请求体。
        data = urlencode(payload).encode("utf-8")

        # 提交正式登录请求。
        result = self.http.request("POST", self.login_api_url, headers=headers, data=data, timeout=60)

        # 解码登录响应文本。
        response_text = result.body.decode("utf-8", errors="replace").strip()

        # 校验登录响应文本。
        self.validate_login_result(response_text)

        # 访问首页以完成登录态初始化。
        self.http.get(self.home_page_url, referer=self.login_page_url)

        # 加载当前账号可见菜单。
        self.menu_tree = self.load_menu_tree()

        # 标记当前登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("菜单节点", len(self.flatten_menu_nodes(self.menu_tree)), "cyan")))

        # 返回登录结果。
        return {"status": "success", "response": response_text}

    def build_login_payload(self):
        """
        构建江苏卫民系统登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 返回标准登录表单字段。
        return {"UserName": self.clean_login_name(), "UserPass": self.clean_login_password(), "UserVc": ""}

    def validate_login_result(self, response_text):
        """
        校验江苏卫民系统登录响应文本。

        :param response_text: 登录响应文本。
        :type response_text: str
        :return: None。
        :rtype: None
        """

        # 判断登录响应是否为成功标记。
        if response_text == "ok":

            # 登录成功时直接返回。
            return

        # 定义常见登录失败码与错误消息映射。
        error_mapping = {
            "notin": "账号不存在",
            "isnot": "账号和密码不匹配",
            "isdel": "账号已离职",
            "stop": "账号已停用",
            "errorcode": "验证码错误",
            "issupplier": "供应商账号无权登录该系统",
            "iscustomer": "客户账号无权登录该系统",
        }

        # 读取失败响应对应的错误消息。
        error_message = error_mapping.get(response_text, response_text or "未知错误")

        # 抛出登录失败异常。
        raise RuntimeError(f"{self.company_name} 登录失败：{error_message}")

    def load_menu_tree(self):
        """
        读取当前账号可见的菜单树。

        :return: 菜单树列表。
        :rtype: list[dict]
        """

        # 构建菜单请求头。
        headers = self.build_ajax_headers(self.home_page_url)

        # 发送菜单读取请求。
        result = self.http.request("GET", self.menu_api_url, headers=headers, timeout=60)

        # 解析菜单响应数据。
        menu_tree = self.decode_json_response(result)

        # 返回菜单树列表。
        return list(menu_tree or [])

    def flatten_menu_nodes(self, nodes):
        """
        将菜单树展开为线性节点列表。

        :param nodes: 菜单节点列表。
        :type nodes: list[dict]
        :return: 展开后的节点列表。
        :rtype: list[dict]
        """

        # 初始化展开后的节点集合。
        flat_nodes = []

        # 遍历当前层级菜单节点。
        for node in nodes or []:

            # 保存当前菜单节点。
            flat_nodes.append(node)

            # 递归展开当前节点的子节点。
            flat_nodes.extend(self.flatten_menu_nodes(node.get("children", [])))

        # 返回展开后的节点列表。
        return flat_nodes

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

        # 查询江苏卫民 FineReport 数据。
        query_result = self.query_jswm_data(data_type, start_date, end_date)

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

        # 查询江苏卫民 FineReport 数据。
        query_result = self.query_jswm_data(data_type, start_date, end_date)

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

    def query_jswm_data(self, data_type, start_date, end_date):
        """
        查询江苏卫民 FineReport 指定类型数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果、表头和日期范围。
        :rtype: dict
        """

        # 校验数据类型。
        self.validate_data_type(data_type)

        # 确保当前会话已经登录。
        self.ensure_login()

        # 解析查询日期范围。
        start_date, end_date = self.resolve_query_dates(start_date, end_date)

        # 判断当前数据类型是否需要校验日期跨度。
        if data_type != "库存":

            # 校验查询日期跨度。
            self.validate_query_range(start_date, end_date)

        # 打印查询阶段标题。
        self.print_query_section(data_type, start_date, end_date)

        # 初始化报表会话。
        report_context = self.initialize_report_session(data_type)

        # 判断当前数据类型是否需要提交日期参数。
        if data_type != "库存":

            # 提交报表参数。
            self.submit_report_parameters(data_type, report_context["session_id"], report_context["report_url"], start_date, end_date)

        # 收集前端预览信息。
        self.collect_preview_info(report_context["report_url"])

        # 读取并汇总全部分页数据。
        headers, rows = self.fetch_all_page_rows(report_context, data_type)

        # 校验查询结果日期范围。
        self.validate_result_date_range(data_type, rows, start_date, end_date)

        # 打印查询结果日志。
        self.ph.success(self.ph.join(self.ph.kv("报表页签解析完成", REPORT_DEFINITIONS[data_type]["pageName"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果。
        return {"headers": headers, "rows": rows, "start_date": start_date, "end_date": end_date}

    def initialize_report_session(self, data_type):
        """
        初始化指定数据类型的报表会话。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表会话上下文。
        :rtype: dict
        """

        # 解析当前数据类型的报表配置。
        report_config = self.resolve_report_config(data_type)

        # 构建报表入口地址。
        report_url = self.build_report_url(report_config["startprogram"])

        # 构建报表入口请求头。
        headers = self.build_html_headers(self.home_page_url)

        # 访问报表入口。
        result = self.http.request("GET", report_url, headers=headers, timeout=120)

        # 解码报表入口 HTML。
        html_text = result.body.decode("utf-8", errors="replace")

        # 提取报表会话编号。
        session_id = self.extract_report_session_id(html_text)

        # 打印会话初始化日志。
        self.ph.info(self.ph.join(self.ph.kv("页面名称", report_config["pageName"], "cyan"), self.ph.kv("报表会话", session_id, "cyan"), self.ph.kv("报表入口", report_config["startprogram"], "cyan")))

        # 返回报表上下文。
        return {"session_id": session_id, "report_url": report_url, "report_config": report_config}

    def resolve_report_config(self, data_type):
        """
        解析指定数据类型的报表配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表配置字典。
        :rtype: dict
        """

        # 读取默认报表配置。
        default_config = REPORT_DEFINITIONS[data_type]

        # 读取账号中的页面配置。
        page_mapping = self.account.get("页面映射", {}).get(data_type, {})

        # 读取目标页面名称。
        page_name = page_mapping.get("页面名称", default_config["pageName"])

        # 初始化报表启动路径。
        startprogram = page_mapping.get("startprogram", "")

        # 遍历菜单树中的全部节点。
        for node in self.flatten_menu_nodes(self.menu_tree):

            # 判断当前菜单节点名称是否匹配页面名称。
            if str(node.get("name", "")).strip() != page_name:

                # 当前节点不是目标页面时进入下一项。
                continue

            # 读取菜单节点中的报表启动路径。
            startprogram = node.get("startprogram", "") or startprogram

            # 找到目标页面后结束循环。
            break

        # 判断报表启动路径是否仍然为空。
        if not startprogram:

            # 读取账号中的报表模板路径。
            reportlet = page_mapping.get("reportlet", default_config["reportlet"])

            # 构建报表启动路径。
            startprogram = f"ReportServer?reportlet={reportlet}"

        # 判断报表启动路径是否仍然为空。
        if not startprogram:

            # 抛出报表入口缺失异常。
            raise RuntimeError(f"{self.company_name} 未找到 {data_type} 的报表入口")

        # 返回报表配置。
        return {
            "pageName": page_name,
            "startprogram": startprogram,
            "paperWidth": int(page_mapping.get("纸张宽度", default_config["paperWidth"])),
            "paperHeight": int(page_mapping.get("纸张高度", default_config["paperHeight"])),
            "parameters": list(page_mapping.get("参数字段", default_config["parameters"])),
            "dateColumn": page_mapping.get("日期字段", default_config["dateColumn"]),
        }

    def build_report_url(self, startprogram):
        """
        根据菜单启动路径构建报表访问地址。

        :param startprogram: 菜单启动路径。
        :type startprogram: str
        :return: 报表访问地址。
        :rtype: str
        """

        # 判断当前启动路径是否已经是绝对地址。
        if str(startprogram).startswith(("http://", "https://")):

            # 绝对地址直接返回。
            return str(startprogram)

        # 返回基于平台根地址拼接后的报表访问地址。
        return urljoin(f"{self.api_base_url}/", str(startprogram).lstrip("/"))

    def submit_report_parameters(self, data_type, session_id, report_url, start_date, end_date):
        """
        提交指定数据类型的报表查询参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param session_id: 报表会话编号。
        :type session_id: str
        :param report_url: 报表访问地址。
        :type report_url: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 参数提交响应数据。
        :rtype: dict
        """

        # 构建参数提交地址。
        url = f"{self.api_base_url}{self.decision_path}/view/report?op=fr_dialog&cmd=parameters_d&sessionID={session_id}"

        # 构建参数字典。
        parameter_values = self.build_parameter_values(data_type, start_date, end_date)

        # 构建表单请求体。
        data = urlencode({"__parameters__": json.dumps(parameter_values, ensure_ascii=False, separators=(",", ":")), "_": str(int(time.time() * 1000))}).encode("utf-8")

        # 构建表单请求头。
        headers = self.build_form_headers(report_url, session_id=session_id)

        # 发送参数提交请求。
        result = self.http.request("POST", url, headers=headers, data=data, timeout=120)

        # 解析参数提交响应。
        response_data = self.decode_json_response(result)

        # 校验参数提交结果。
        if str(response_data.get("status", "")).lower() != "success":

            # 抛出参数提交异常。
            raise RuntimeError(f"{self.company_name} {data_type} 报表参数提交失败：{response_data}")

        # 打印参数提交日志。
        self.ph.info(self.ph.join(self.ph.kv("报表参数", "提交成功", "green"), self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

        # 返回参数提交响应。
        return response_data

    def build_parameter_values(self, data_type, start_date, end_date):
        """
        构建指定数据类型的报表参数字典。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 参数字典。
        :rtype: dict
        """

        # 读取当前数据类型的报表配置。
        report_config = self.resolve_report_config(data_type)

        # 初始化参数字典。
        parameter_values = {}

        # 遍历当前数据类型的参数字段。
        for field_name in report_config["parameters"]:

            # 判断当前字段是否为开始日期。
            if field_name == "BDATE":

                # 写入查询开始日期。
                parameter_values[field_name] = start_date

                # 进入下一个参数字段。
                continue

            # 判断当前字段是否为结束日期。
            if field_name == "EDATE":

                # 写入查询结束日期。
                parameter_values[field_name] = end_date

                # 进入下一个参数字段。
                continue

            # 写入空字符串参数值。
            parameter_values[field_name] = ""

        # 返回参数字典。
        return parameter_values

    def collect_preview_info(self, report_url):
        """
        提交 FineReport 前端预览信息埋点。

        :param report_url: 报表访问地址。
        :type report_url: str
        :return: dict | None。
        :rtype: dict | None
        """

        # 构建预览信息采集地址。
        url = f"{self.api_base_url}{self.decision_path}/preview/info/collect"

        # 构建预览信息请求体。
        data = urlencode({"webInfo": json.dumps({"webResolution": "1920*1080", "fullScreen": 0}, ensure_ascii=False, separators=(",", ":"))}).encode("utf-8")

        # 构建预览信息请求头。
        headers = self.build_form_headers(report_url)

        try:

            # 发送预览信息采集请求。
            result = self.http.request("POST", url, headers=headers, data=data, timeout=60)

        except RuntimeError:

            # 预览埋点失败时直接返回空值。
            return None

        try:

            # 返回 JSON 响应数据。
            return self.decode_json_response(result)

        except json.JSONDecodeError:

            # JSON 解析失败时返回空值。
            return None

    def fetch_all_page_rows(self, report_context, data_type):
        """
        读取指定数据类型的全部分页数据。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 表头与数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化当前页码。
        page_number = 1

        # 初始化总页数。
        total_pages = 1

        # 初始化合并后表头。
        merged_headers = []

        # 初始化合并后数据行。
        merged_rows = []

        # 构建页面客户端标识。
        client_id = self.build_client_id(report_context["session_id"])

        # 循环读取全部分页内容。
        while page_number <= total_pages:

            # 读取当前页内容响应。
            response_data = self.fetch_page_content(report_context, page_number, client_id)

            # 解析当前页总页数。
            current_total_pages = self.extract_total_pages(response_data.get("html", ""))

            # 判断当前页是否返回了有效总页数。
            if current_total_pages:

                # 更新总页数。
                total_pages = current_total_pages

            # 解析当前页表格行。
            table_rows = self.parse_report_html(response_data.get("html", ""))

            # 构建当前页表头与数据行。
            page_headers, page_rows = self.build_rows_from_table(table_rows)

            # 合并当前页数据。
            merged_headers, merged_rows = self.merge_page_rows(merged_headers, merged_rows, page_headers, page_rows)

            # 打印分页读取日志。
            self.ph.info(self.ph.join(self.ph.kv("当前页", f"{page_number}/{total_pages}", "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan"), self.ph.kv("累计记录", len(merged_rows), "cyan")))

            # 页码递增到下一页。
            page_number += 1

        # 返回合并后的表头与数据行。
        return merged_headers, merged_rows

    def fetch_page_content(self, report_context, page_number, client_id):
        """
        读取指定页码的报表 HTML 内容。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :param page_number: 当前页码。
        :type page_number: int
        :param client_id: 前端客户端标识。
        :type client_id: str
        :return: 页面内容响应数据。
        :rtype: dict
        """

        # 读取报表配置。
        report_config = report_context["report_config"]

        # 构建报表内容请求地址。
        url = (
            f"{self.api_base_url}{self.decision_path}/view/report?_={int(time.time() * 1000)}"
            f"&__boxModel__=true&op=page_content&sessionID={report_context['session_id']}"
            f"&pn={page_number}&cid={client_id}&__webpage__=true"
            f"&_paperWidth={report_config['paperWidth']}&_paperHeight={report_config['paperHeight']}&__fit__=false"
        )

        # 构建 AJAX 请求头。
        headers = self.build_ajax_headers(report_context["report_url"])

        # 发送报表内容请求。
        result = self.http.request("GET", url, headers=headers, timeout=180)

        # 返回 JSON 响应数据。
        return self.decode_json_response(result)

    def build_client_id(self, session_id):
        """
        构建 FineReport 页面内容请求使用的客户端标识。

        :param session_id: 报表会话编号。
        :type session_id: str
        :return: 客户端标识。
        :rtype: str
        """

        # 返回基于会话号拼接的固定客户端标识。
        return f"ddi-{session_id}"

    def extract_total_pages(self, html_text):
        """
        从页面 HTML 中提取总页数。

        :param html_text: 页面 HTML 文本。
        :type html_text: str
        :return: 总页数。
        :rtype: int
        """

        # 查找总页数字段。
        matched = re.search(r"reportTotalPage=(\d+)", str(html_text or ""))

        # 判断总页数字段是否存在。
        if not matched:

            # 不存在时返回默认单页值。
            return 1

        # 返回解析后的总页数。
        return int(matched.group(1))

    def merge_page_rows(self, merged_headers, merged_rows, page_headers, page_rows):
        """
        合并分页返回的表头与数据行。

        :param merged_headers: 已合并表头。
        :type merged_headers: list[str]
        :param merged_rows: 已合并数据行。
        :type merged_rows: list[dict]
        :param page_headers: 当前页表头。
        :type page_headers: list[str]
        :param page_rows: 当前页数据行。
        :type page_rows: list[dict]
        :return: 合并后的表头与数据行。
        :rtype: tuple[list[str], list[dict]]
        """

        # 初始化当前合并表头副本。
        current_headers = list(merged_headers)

        # 遍历当前页表头。
        for header_name in page_headers:

            # 判断当前字段是否已存在于合并表头。
            if header_name in current_headers:

                # 已存在时进入下一项表头。
                continue

            # 将新字段追加到合并表头末尾。
            current_headers.append(header_name)

        # 初始化合并后数据行集合。
        normalized_rows = []

        # 遍历历史数据行。
        for row in merged_rows:

            # 按最新合并表头重建历史数据行。
            normalized_rows.append({header_name: row.get(header_name, "") for header_name in current_headers})

        # 遍历当前页数据行。
        for row in page_rows:

            # 按最新合并表头重建当前页数据行。
            normalized_rows.append({header_name: row.get(header_name, "") for header_name in current_headers})

        # 返回合并后的表头与数据行。
        return current_headers, normalized_rows

    def validate_result_date_range(self, data_type, rows, start_date, end_date):
        """
        校验流向结果中的业务日期范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 判断当前数据类型是否为库存。
        if data_type == "库存":

            # 库存快照无需校验业务日期范围。
            return

        # 判断结果行是否为空。
        if not rows:

            # 空结果直接返回。
            return

        # 读取日期字段名称。
        date_column = REPORT_DEFINITIONS[data_type]["dateColumn"]

        # 判断日期字段名称是否为空。
        if not date_column:

            # 日期字段缺失时直接返回。
            return

        # 初始化结果日期集合。
        result_dates = []

        # 遍历全部结果行。
        for row in rows:

            # 读取当前行日期文本。
            date_text = str(row.get(date_column, "")).strip()

            # 判断当前行日期文本是否为空。
            if not date_text:

                # 空日期直接进入下一行。
                continue

            try:

                # 解析当前行日期。
                result_dates.append(datetime.strptime(date_text, "%Y-%m-%d"))

            except ValueError:

                # 非标准日期文本时直接进入下一行。
                continue

        # 判断结果日期集合是否为空。
        if not result_dates:

            # 没有可校验日期时直接返回。
            return

        # 解析开始日期。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 读取结果中的最小日期。
        min_date = min(result_dates)

        # 读取结果中的最大日期。
        max_date = max(result_dates)

        # 判断结果日期是否超出查询范围。
        if min_date < start_value or max_date > end_value:

            # 抛出结果日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 结果日期超出查询范围：{min_date:%Y-%m-%d} ~ {max_date:%Y-%m-%d}")

        # 打印结果日期范围校验日志。
        self.ph.info(self.ph.join(self.ph.kv("结果日期最小值", min_date.strftime("%Y-%m-%d"), "cyan"), self.ph.kv("结果日期最大值", max_date.strftime("%Y-%m-%d"), "cyan")))
