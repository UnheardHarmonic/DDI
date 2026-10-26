# -*- coding: utf-8 -*-
"""
成都聚仁堂 FineReport 数据报表系统协议适配器。

本模块负责成都聚仁堂医药连锁有限公司 FineDecision 登录、门户报表入口定位、
四报表参数提交、分页数据读取和本地 Excel 生成。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入随机数模块。
import random

# 导入正则表达式模块。
import re

# 导入时间模块。
import time

# 导入 URL 表单编码函数。
from urllib.parse import urlencode

# 导入 URL 引号编码函数。
from urllib.parse import quote

# 导入日期时间解析对象。
from datetime import datetime

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入 FineReport 平台公共骨架。
from ddi_framework.platforms.finereport_common import FineReportPlatformBase

# 导入 FineReport 表格解析器。
from ddi_framework.platforms.finereport_common import FineReportTableParser


# 定义聚仁堂 FineReport 数据类型与独立报表定义映射。
REPORT_DEFINITIONS = {
    "购进流向": {"pageName": "采购退货明细", "startParam": "开始生效日期", "endParam": "结束生效日期", "paperWidth": 759, "paperHeight": 728, "dateColumn": "生效时间"},
    "配送流向": {"pageName": "配送明细表", "startParam": "开始日期", "endParam": "结束日期", "paperWidth": 759, "paperHeight": 725, "dateColumn": "会计日"},
    "纯销流向": {"pageName": "销售明细表", "startParam": "销售开始日期", "endParam": "销售结束日期", "paperWidth": 759, "paperHeight": 725, "dateColumn": "会计日"},
    "库存": {"pageName": "库存明细表", "startParam": "", "endParam": "", "paperWidth": 759, "paperHeight": 849, "dateColumn": ""},
}


class JrtPlatform(FineReportPlatformBase):
    """
    成都聚仁堂 FineReport 数据报表系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 成都聚仁堂平台适配器实例。
    :rtype: JrtPlatform
    """

    def __init__(self, company_name, account, printer=None):
        """
        初始化成都聚仁堂平台适配器。

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
        super().__init__(company_name, account, printer=printer, api_root_default="http://183.221.78.70:18075", decision_path_default="/webroot/decision")

        # 初始化日志打印器。
        self.ph = printer or PrintHandler()

        # 保存参数最大查询天数。
        self.max_query_days = int(account.get("最大查询天数", 180))

        # 初始化报表入口缓存。
        self.report_entries = {}

    def login(self):
        """
        执行聚仁堂 FineDecision 协议登录。

        :return: 登录响应数据。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("聚仁堂登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.join(self.ph.kv("访问登录页", self.login_page_url, "cyan"), self.ph.kv("账号", self.clean_login_name(), "cyan")))

        # 访问登录页以建立站点 Cookie。
        login_page = self.http.get(self.login_page_url)

        # 解码登录页 HTML。
        login_html = login_page.body.decode("utf-8", errors="replace")

        # 提取 FineDecision 前端加密配置。
        cipher_config = self.extract_cipher_config(login_html)

        # 构建登录请求体。
        payload = self.build_login_payload(cipher_config)

        # 提交登录 JSON 请求。
        result = self.post_login_json(payload)

        # 解析登录响应。
        response_data = self.decode_json_response(result)

        # 校验登录响应数据。
        self.validate_login_response(response_data)

        # 保存登录访问令牌。
        self.access_token = str(response_data.get("data", {}).get("accessToken", ""))

        # 写入 FineDecision 登录 Cookie。
        self.apply_token_cookies(self.access_token)

        # 标记当前登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("用户", response_data.get("data", {}).get("username", ""), "cyan")))

        # 返回登录响应数据。
        return response_data

    def validate_data_type(self, data_type):
        """
        校验数据类型是否已接入。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否存在报表定义。
        if data_type not in REPORT_DEFINITIONS:

            # 抛出数据类型未接入异常。
            raise ValueError(f"成都聚仁堂平台暂不支持数据类型：{data_type}")

    def resolve_query_dates(self, start_date, end_date):
        """
        解析查询日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询开始日期与结束日期。
        :rtype: tuple[str, str]
        """

        # 读取当天日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 返回查询日期范围。
        return start_date or today_text, end_date or today_text

    def validate_query_range(self, start_date, end_date):
        """
        校验 FineReport 查询日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 解析开始日期。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断开始日期是否晚于结束日期。
        if start_value > end_value:

            # 抛出日期范围异常。
            raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{start_date} > {end_date}")

        # 判断查询跨度是否超过平台限制。
        if (end_value - start_value).days > self.max_query_days:

            # 抛出日期跨度异常。
            raise ValueError(f"{self.company_name} 单次查询范围不能超过 {self.max_query_days} 天")

    def print_query_section(self, data_type, start_date, end_date):
        """
        打印查询阶段标题。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印业务查询标题。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

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

        # 查询聚仁堂 FineReport 数据。
        query_result = self.query_jrt_data(data_type, start_date, end_date)

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

        # 查询聚仁堂 FineReport 数据。
        query_result = self.query_jrt_data(data_type, start_date, end_date)

        # 使用当前工作目录作为默认输出目录。
        output_dir = output_dir or os.getcwd()

        # 创建输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 构建输出文件路径。
        output_path = os.path.join(output_dir, file_name)

        # 构建表头二元组契约（显示列名与行键名一致）。
        header_pairs = [(header, header) for header in query_result["headers"]]

        # 写入 Excel 文件。
        self.write_rows_to_excel(query_result["rows"], header_pairs, output_path, data_type)

        # 打印 Excel 保存日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    def query_jrt_data(self, data_type, start_date, end_date):
        """
        查询聚仁堂 FineReport 指定类型数据。

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
            self.submit_report_parameters(data_type, report_context["session_id"], report_context["entry_url"], start_date, end_date)

        # 收集前端预览信息。
        self.collect_preview_info(report_context["entry_url"])

        # 读取并汇总全部分页数据。
        headers, rows = self.fetch_all_page_rows(report_context, data_type)

        # 校验查询结果日期范围。
        self.validate_result_date_range(data_type, rows, start_date, end_date)

        # 打印查询结果日志。
        self.ph.success(self.ph.join(self.ph.kv("报表解析完成", REPORT_DEFINITIONS[data_type]["pageName"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果。
        return {"headers": headers, "rows": rows, "start_date": start_date, "end_date": end_date}

    def parse_report_html(self, html_text):
        """
        解析聚仁堂 FineReport 冻结窗格报表 HTML。

        :param html_text: 报表 HTML 文本。
        :type html_text: str
        :return: 首行为表头的逻辑表格行集合。
        :rtype: list[list[str]]
        """

        # 解析冻结窗格并组装逻辑表格行。
        logical_rows = self.build_pane_table_rows(str(html_text or ""))

        # 判断冻结窗格解析是否产出逻辑行。
        if logical_rows:

            # 返回窗格合并后的逻辑表格行。
            return logical_rows

        # 无冻结窗格时回退整页解析。
        return super().parse_report_html(html_text)

    def build_pane_table_rows(self, html_text):
        """
        按 FineReport 冻结窗格结构组装逻辑表格行。

        :param html_text: 报表 HTML 文本。
        :type html_text: str
        :return: 首行为表头的逻辑表格行集合，无窗格结构时返回空列表。
        :rtype: list[list[str]]
        """

        # 初始化各窗格行集合容器。
        pane_rows = {}

        # 遍历四个冻结窗格并逐格解析。
        for pane_name in ("frozen-corner", "frozen-north", "frozen-west", "frozen-center"):

            # 截取当前窗格的 HTML 片段。
            pane_match = re.search(rf'id="{pane_name}"(.*?)(?=id="frozen-|$)', html_text, re.S)

            # 判断当前窗格是否存在。
            if not pane_match:

                # 记录空窗格行集合。
                pane_rows[pane_name] = []

                # 进入下一个窗格。
                continue

            # 创建窗格表格解析器。
            parser = FineReportTableParser()

            # 解析当前窗格 HTML 片段。
            parser.feed(pane_match.group(1))

            # 保存当前窗格行集合。
            pane_rows[pane_name] = parser.rows

        # 判断是否存在窗格结构且表头窗格有行。
        if not any(pane_rows.values()) or not pane_rows["frozen-north"]:

            # 无窗格结构时返回空列表交由调用方回退。
            return []

        # 读取表头窗格中字段数最多的一行作为逻辑表头。
        header_row = max(pane_rows["frozen-north"], key=len)

        # 读取左侧冻结列与中央数据列的行集合。
        west_rows = pane_rows["frozen-west"]

        # 读取中央数据行集合。
        center_rows = pane_rows["frozen-center"]

        # 初始化逻辑数据行集合。
        logical_rows = [header_row]

        # 遍历中央数据行并按行序拼接左侧冻结列。
        for row_index, center_row in enumerate(center_rows):

            # 读取当前行序对应的左侧冻结单元格。
            west_row = west_rows[row_index] if row_index < len(west_rows) else []

            # 拼接左侧冻结列与中央数据列。
            logical_rows.append(list(west_row) + list(center_row))

        # 返回逻辑表格行集合。
        return logical_rows

    def resolve_report_entry(self, data_type):
        """
        解析指定数据类型的报表入口路径。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表入口访问路径。
        :rtype: str
        """

        # 判断当前数据类型是否已缓存报表入口。
        if data_type in self.report_entries:

            # 返回已缓存的报表入口路径。
            return self.report_entries[data_type]

        # 读取账号中的页面配置。
        page_mapping = self.account.get("页面映射", {}).get(data_type, {})

        # 读取账号显式声明的入口编号。
        entry_token = str(page_mapping.get("入口ID", "")).strip()

        # 判断账号是否显式声明了入口编号。
        if entry_token:

            # 缓存并返回显式声明的报表入口。
            self.report_entries[data_type] = entry_token

            # 返回显式声明的报表入口。
            return entry_token

        # 按页面名称搜索门户报表入口。
        entry_token = self.search_report_entry(REPORT_DEFINITIONS[data_type]["pageName"])

        # 判断是否定位到目标报表入口。
        if not entry_token:

            # 抛出报表入口缺失异常。
            raise RuntimeError(f"{self.company_name} 未在门户定位到 {data_type} 的报表入口")

        # 缓存当前数据类型的报表入口。
        self.report_entries[data_type] = entry_token

        # 返回定位到的报表入口。
        return entry_token

    def search_report_entry(self, page_name):
        """
        按页面名称调用门户目录搜索接口定位报表入口。

        :param page_name: 报表页面名称。
        :type page_name: str
        :return: 报表入口编号，未定位到时返回空字符串。
        :rtype: str
        """

        # 构建门户目录搜索地址。
        url = f"{self.api_base_url}{self.decision_path}/v10/entry/list?keyword={quote(page_name)}"

        # 构建门户搜索请求头。
        headers = self.build_ajax_headers(f"{self.api_base_url}{self.decision_path}/")

        # 写入授权请求头。
        self.apply_authorization_header(headers)

        # 发送门户目录搜索请求。
        result = self.http.request("GET", url, headers=headers, timeout=60)

        # 解码搜索响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 解析搜索响应中的目标入口编号。
        entry_token = self.parse_entry_search_response(response_text, page_name)

        # 判断是否定位到目标报表入口。
        if entry_token:

            # 打印入口定位日志。
            self.ph.info(self.ph.join(self.ph.kv("报表入口", entry_token, "cyan"), self.ph.kv("页面名称", page_name, "cyan")))

        # 返回目标报表入口编号。
        return entry_token

    def parse_entry_search_response(self, response_text, page_name):
        """
        解析门户目录搜索响应中的目标报表入口编号。

        :param response_text: 门户目录搜索响应文本。
        :type response_text: str
        :param page_name: 报表页面名称。
        :type page_name: str
        :return: 报表入口编号，未命中时返回空字符串。
        :rtype: str
        """

        # 解析搜索响应 JSON 文本。
        response_data = json.loads(response_text)

        # 遍历搜索结果条目匹配目标页面名称。
        for item in response_data.get("data", []) or []:

            # 判断当前条目名称是否与目标页面名称一致。
            if str(item.get("text", "")).strip() == page_name:

                # 返回当前条目的入口编号。
                return str(item.get("id", "")).strip()

        # 未命中目标页面时返回空字符串。
        return ""

    def initialize_report_session(self, data_type):
        """
        初始化指定数据类型的报表会话。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 报表会话上下文。
        :rtype: dict
        """

        # 解析当前数据类型的报表入口路径。
        entry_token = self.resolve_report_entry(data_type)

        # 构建报表入口绝对地址。
        if entry_token.startswith(("http://", "https://")):

            # 绝对地址直接使用。
            entry_url = entry_token

        # 处理根相对入口路径。
        elif entry_token.startswith("/"):

            # 按平台根地址拼接入口地址。
            entry_url = f"{self.api_base_url}{entry_token}"

        # 处理裸入口编号。
        elif "/" not in entry_token:

            # 按入口访问端点拼接入口地址。
            entry_url = f"{self.api_base_url}{self.decision_path}/v10/entry/access/{entry_token}"

        # 处理其余相对入口路径。
        else:

            # 按决策系统根地址拼接入口地址。
            entry_url = f"{self.api_base_url}{self.decision_path}/{entry_token}"

        # 构建报表入口请求头。
        headers = self.build_html_headers(f"{self.api_base_url}{self.decision_path}")

        # 写入授权请求头。
        self.apply_authorization_header(headers)

        # 访问报表入口。
        result = self.http.request("GET", entry_url, headers=headers, timeout=120)

        # 解码报表入口 HTML。
        html_text = result.body.decode("utf-8", errors="replace")

        # 提取报表会话编号。
        session_id = self.extract_report_session_id(html_text)

        # 打印会话初始化日志。
        self.ph.info(self.ph.join(self.ph.kv("页面名称", REPORT_DEFINITIONS[data_type]["pageName"], "cyan"), self.ph.kv("报表会话", session_id, "cyan")))

        # 返回报表上下文。
        return {"session_id": session_id, "entry_url": entry_url, "report_config": REPORT_DEFINITIONS[data_type]}

    def extract_report_session_id(self, html_text):
        """
        从报表入口 HTML 中提取报表会话编号。

        :param html_text: 报表入口 HTML。
        :type html_text: str
        :return: 报表会话编号。
        :rtype: str
        """

        # 查找当前会话编号赋值。
        session_match = re.search(r"currentSessionID\s*=\s*'([^']+)'", html_text)

        # 判断当前会话编号是否存在。
        if session_match:

            # 返回当前会话编号。
            return session_match.group(1)

        # 查找 SessionMgr 注册调用。
        register_match = re.search(r"FR\.SessionMgr\.register\('([^']+)'", html_text)

        # 判断注册调用是否存在。
        if register_match:

            # 返回注册调用中的会话编号。
            return register_match.group(1)

        # 抛出会话编号缺失异常。
        raise RuntimeError(f"{self.company_name} 报表入口缺少 sessionID")

    def submit_report_parameters(self, data_type, session_id, entry_url, start_date, end_date):
        """
        提交指定数据类型的报表查询参数。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param session_id: 报表会话编号。
        :type session_id: str
        :param entry_url: 报表入口地址。
        :type entry_url: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 参数提交响应数据。
        :rtype: dict
        """

        # 构建参数提交地址。
        url = f"{self.api_base_url}{self.decision_path}/view/report?op=fr_dialog&cmd=parameters_d&sessionID={session_id}"

        # 读取当前数据类型的参数名称。
        report_config = REPORT_DEFINITIONS[data_type]

        # 构建参数字典。
        parameter_values = {report_config["startParam"]: start_date, report_config["endParam"]: end_date}

        # 构建表单请求体。
        data = urlencode({"__parameters__": json.dumps(parameter_values, ensure_ascii=False, separators=(",", ":")), "_": str(int(time.time() * 1000))}).encode("utf-8")

        # 构建表单请求头。
        headers = self.build_form_headers(entry_url, session_id=session_id)

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

        except ValueError:

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

        # 循环读取全部分页内容。
        while page_number <= total_pages:

            # 读取当前页内容响应。
            response_data = self.fetch_page_content(report_context, page_number)

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

            # 判断当前页是否无数据行以终止读取。
            if not page_rows:

                # 空页说明分页读取已到尽头。
                break

            # 页码递增到下一页。
            page_number += 1

        # 返回合并后的表头与数据行。
        return merged_headers, merged_rows

    def fetch_page_content(self, report_context, page_number):
        """
        读取指定页码的报表 HTML 内容。

        :param report_context: 报表会话上下文。
        :type report_context: dict
        :param page_number: 当前页码。
        :type page_number: int
        :return: 页面内容响应数据。
        :rtype: dict
        """

        # 读取当前数据类型的报表配置。
        report_config = report_context["report_config"]

        # 构建页面客户端标识并编码片段分隔符。
        client_id = quote(self.build_client_id(report_context["session_id"]), safe="")

        # 构建报表内容请求地址。
        url = (
            f"{self.api_base_url}{self.decision_path}/view/report?_={int(time.time() * 1000)}"
            f"&__boxModel__=true&op=page_content&sessionID={report_context['session_id']}&pn={page_number}&cid={client_id}&__webpage__=true"
            f"&__paperWidth__={report_config['paperWidth']}&__paperHeight__={report_config['paperHeight']}&__fit__=false"
        )

        # 构建 AJAX 请求头。
        headers = self.build_ajax_headers(report_context["entry_url"])

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

        # 返回会话号、毫秒时间戳与随机段拼接的客户端标识。
        return f"{session_id}#{int(time.time() * 1000)}#{random.randint(0, 0xFFFFFFFF):08x}"

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
                result_dates.append(datetime.strptime(date_text[:10], "%Y-%m-%d"))

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
