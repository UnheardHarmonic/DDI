# -*- coding: utf-8 -*-
"""
ABACUS 供应链系统协议适配器。

本模块通过统一 JSON RPC 接口完成登录、总部库存、门店库存、门店销售、配送和收货明细查询，并按商业配置定义的页面字段标题和顺序写入本地 Excel。

:return: 模块提供 ABACUS 供应链系统平台适配器。
:rtype: None
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入 Excel 工作簿类。
from openpyxl import Workbook

# 导入平台基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义数据类型与 JSON RPC 方法、页面来源及日期字段的协议映射。
DATA_TYPE_CONFIG = {
    "总部库存": {"method": "warequery", "referer": "/scm/inventoryList", "date_field": ""},
    "门店库存": {"method": "storequery", "referer": "/scm/storeInventoryList", "date_field": ""},
    "纯销流向": {"method": "salequery", "referer": "/scm/saleList", "date_field": "actdat"},
    "配送流向": {"method": "stkotquery", "referer": "/scm/distribution", "date_field": "actdat"},
    "购进流向": {"method": "stkinquery", "referer": "/scm/receiving", "date_field": "actdat"},
}

# 定义 ABACUS 供应链系统平台适配器。
class AbacusPlatform(BasePlatform):

    """
    ABACUS 供应链系统平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: ABACUS 供应链系统平台适配器实例。
    :rtype: AbacusPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化 JSON RPC 会话、查询配置和日志对象。

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

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 读取平台接口根地址。
        self.base_url = str(account.get("接口根地址", account.get("登录页", ""))).rstrip("/")

        # 读取登录页面地址。
        self.login_page_url = str(account.get("登录页", f"{self.base_url}/scm/login"))

        # 读取统一 JSON RPC 接口地址。
        self.api_url = str(account.get("查询接口", f"{self.base_url}/scmapi/api"))

        # 读取查询请求超时时间。
        self.query_timeout_seconds = int(account.get("查询超时秒", 180))

        # 初始化带 Cookie 管理的协议客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态标识。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        提交 ABACUS JSON RPC 登录请求并建立协议会话。

        :return: 不含凭据的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("ABACUS 供应链系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 构建服务端要求的登录请求体。
        payload = {"method": "login", "data": {"prvid": str(self.account.get("账号", "")), "pwd": str(self.account.get("密码", ""))}}

        # 提交 JSON RPC 登录请求。
        response_data = self.request_rpc(payload, self.login_page_url)

        # 校验登录响应表示成功。
        self.validate_response("登录", response_data)

        # 标记当前协议会话已登录。
        self.logged_in = True

        # 打印不含敏感值的登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("Cookie", len(list(self.http.cookie_jar)), "cyan")))

        # 返回不含敏感字段的登录结果。
        return {"登录状态": "成功", "Cookie数量": len(list(self.http.cookie_jar))}

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前协议会话 Cookie 供公共任务服务记录。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 输出文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 保存当前协议会话 Cookie。
        self.http.save_cookie_file(cookie_path)

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义原始数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的全部原始业务记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 查询当前数据类型的全部分页数据。
        query_result = self.query_abacus_data(data_type, start_date, end_date)

        # 返回未裁剪的原始记录列表。
        return query_result["rows"]

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成页面字段顺序 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 查询当前数据类型的全部分页数据。
        query_result = self.query_abacus_data(data_type, start_date, end_date)

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, query_result["start_date"], query_result["end_date"])

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 写入页面字段工作表和隐藏接口原始字段工作表。
        self.write_rows_to_excel(query_result["rows"], query_result["headers"], data_type, output_path)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(query_result['rows'])} 条", "cyan"), self.ph.kv("字段数", len(query_result["headers"]), "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义平台导出方法。
    def export_flow(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        使用协议查询结果生成本地 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 调用查询并落地 Excel 的统一流程。
        return self.query_flow_to_excel(data_type, start_date=start_date, end_date=end_date, output_dir=output_dir)

    # 定义协议主查询方法。
    def query_abacus_data(self, data_type, start_date, end_date):

        """
        建立登录态、提交 JSON RPC 筛选条件并读取全部分页记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始字段、原始记录及实际日期范围。
        :rtype: dict
        """

        # 校验数据类型已配置协议方法。
        self.validate_data_type(data_type)

        # 确保当前 HTTP 会话已经登录。
        self.ensure_login()

        # 解析当前查询的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(data_type, start_date, end_date)

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, resolved_start_date, resolved_end_date)

        # 请求并合并当前数据类型的所有分页记录。
        headers, rows = self.fetch_all_pages(data_type, resolved_start_date, resolved_end_date)

        # 校验流向记录的业务日期处于请求范围。
        self.validate_result_date_range(data_type, rows, resolved_start_date, resolved_end_date)

        # 打印协议查询完成摘要。
        self.ph.success(self.ph.join(self.ph.kv("查询方法", DATA_TYPE_CONFIG[data_type]["method"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回查询结果数据结构。
        return {"headers": headers, "rows": rows, "start_date": resolved_start_date, "end_date": resolved_end_date}

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型存在于平台协议映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 判断数据类型是否已配置协议方法。
        if data_type in DATA_TYPE_CONFIG:

            # 结束有效数据类型校验。
            return

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}")

    # 定义登录态确保方法。
    def ensure_login(self):

        """
        确保当前协议客户端已经建立有效登录态。

        :return: None。
        :rtype: None
        """

        # 判断当前会话已经完成登录。
        if self.logged_in:

            # 结束重复登录处理。
            return

        # 执行平台登录流程。
        self.login()

    # 定义查询日期解析方法。
    def resolve_query_dates(self, data_type, start_date, end_date):

        """
        解析库存快照或流向明细使用的日期范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 解析后的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 生成当前导出日期文本。
        today_text = datetime.now().strftime("%Y-%m-%d")

        # 判断当前数据类型是否为库存快照。
        if not DATA_TYPE_CONFIG[data_type]["date_field"]:

            # 返回库存文件命名使用的当天日期。
            return today_text, today_text

        # 解析流向查询开始日期。
        resolved_start_date = str(start_date or today_text)

        # 解析流向查询结束日期。
        resolved_end_date = str(end_date or resolved_start_date)

        # 校验流向日期范围顺序。
        self.validate_query_range(resolved_start_date, resolved_end_date)

        # 返回流向查询日期范围。
        return resolved_start_date, resolved_end_date

    # 定义日期范围校验方法。
    def validate_query_range(self, start_date, end_date):

        """
        校验开始日期不晚于结束日期。

        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 解析开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d")

        # 解析结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d")

        # 判断日期范围顺序是否正确。
        if start_value <= end_value:

            # 结束有效日期范围校验。
            return

        # 抛出无效日期范围异常。
        raise ValueError(f"{self.company_name} 查询开始日期不能晚于结束日期：{start_date} > {end_date}")

    # 定义查询阶段日志方法。
    def print_query_section(self, data_type, start_date, end_date):

        """
        打印当前数据类型的标准查询日志分隔线。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 打印包含日期范围的查询阶段分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", start_date, "cyan"), self.ph.kv("结束日期", end_date, "cyan")))

    # 定义全部分页读取方法。
    def fetch_all_pages(self, data_type, start_date, end_date):

        """
        分页请求 JSON RPC 接口并合并服务端原始记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: 原始字段定义和全部原始记录。
        :rtype: tuple[list[dict], list[dict]]
        """

        # 初始化有序原始字段定义列表。
        headers = []

        # 初始化全部原始记录列表。
        rows = []

        # 初始化当前请求页码。
        page_index = 1

        # 初始化服务端返回的总页数。
        total_pages = 1

        # 持续请求直到读取完服务端全部页码。
        while page_index <= total_pages:

            # 构建当前页 JSON RPC 查询请求体。
            payload = self.build_query_payload(data_type, start_date, end_date, page_index)

            # 请求当前页 JSON RPC 数据。
            response_data = self.fetch_page(data_type, payload)

            # 读取当前页服务端数据对象。
            data_block = response_data.get("data", {}) if isinstance(response_data, dict) else {}

            # 读取当前页记录列表。
            page_rows = data_block.get("pageData", []) if isinstance(data_block, dict) else []

            # 校验当前页记录列表为数组。
            if not isinstance(page_rows, list):

                # 抛出无效数据结构异常。
                raise RuntimeError(f"{self.company_name} {data_type} 查询返回的 pageData 字段不是数组")

            # 合并本页新增原始字段定义。
            headers = self.merge_headers(headers, page_rows)

            # 合并当前页原始记录。
            rows.extend(row for row in page_rows if isinstance(row, dict))

            # 读取服务端总页数。
            total_pages = self.resolve_page_count(data_block, total_pages)

            # 打印当前页读取进度。
            self.ph.info(self.ph.join(self.ph.kv("分页", f"{page_index}/{total_pages}", "cyan"), self.ph.kv("本页记录", len(page_rows), "cyan"), self.ph.kv("累计", len(rows), "cyan")))

            # 判断当前页未返回记录。
            if not page_rows:

                # 结束分页读取循环。
                break

            # 增加下一页页码。
            page_index += 1

        # 返回字段定义和全部原始记录。
        return headers, rows

    # 定义单页数据请求方法。
    def fetch_page(self, data_type, payload):

        """
        请求并校验单页 JSON RPC 业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param payload: JSON RPC 查询请求体。
        :type payload: dict
        :return: 服务端 JSON 响应对象。
        :rtype: dict
        """

        # 读取当前数据类型页面来源配置。
        referer_path = DATA_TYPE_CONFIG[data_type]["referer"]

        # 拼接当前数据类型来源页面地址。
        referer_url = f"{self.base_url}{referer_path}"

        # 提交带平台超时配置的 JSON RPC 查询请求。
        response_data = self.request_rpc(payload, referer_url)

        # 校验接口未返回失败状态。
        self.validate_response(data_type, response_data)

        # 返回当前页响应对象。
        return response_data

    # 定义查询请求体构建方法。
    def build_query_payload(self, data_type, start_date, end_date, page_index):

        """
        构建 ABACUS 页面提交的完整 JSON RPC 筛选条件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :param page_index: 当前分页页码。
        :type page_index: int
        :return: JSON RPC 查询请求体。
        :rtype: dict
        """

        # 构建页面公共筛选字段。
        query_data = {"prvid": str(self.account.get("账号", "")), "gdsid": "", "pageIndex": int(page_index)}

        # 判断当前数据类型需要提交业务日期范围。
        if DATA_TYPE_CONFIG[data_type]["date_field"]:

            # 写入去除连接符的开始日期。
            query_data["bdate"] = start_date.replace("-", "")

            # 写入去除连接符的结束日期。
            query_data["edate"] = end_date.replace("-", "")

        # 返回当前数据类型对应的 JSON RPC 请求体。
        return {"method": DATA_TYPE_CONFIG[data_type]["method"], "data": query_data}

    # 定义 JSON RPC 请求方法。
    def request_rpc(self, payload, referer_url):

        """
        使用配置超时发送 JSON RPC 请求并解析响应。

        :param payload: JSON RPC 请求体。
        :type payload: dict
        :param referer_url: 浏览器来源页面地址。
        :type referer_url: str
        :return: 服务端 JSON 响应对象。
        :rtype: dict
        """

        # 构建 JSON 请求头。
        headers = self.http.json_headers(referer_url)

        # 编码 JSON RPC 请求体。
        request_data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # 发送带平台超时配置的请求。
        result = self.http.request("POST", self.api_url, headers=headers, data=request_data, timeout=self.query_timeout_seconds)

        # 返回解析后的 JSON 响应对象。
        return self.http.decode_json(result)

    # 定义响应校验方法。
    def validate_response(self, stage_name, response_data):

        """
        校验 JSON RPC 响应为成功状态且包含预期对象。

        :param stage_name: 登录或数据类型阶段名称。
        :type stage_name: str
        :param response_data: JSON 响应对象。
        :type response_data: dict
        :return: None。
        :rtype: None
        """

        # 判断响应对象是否为字典。
        if not isinstance(response_data, dict):

            # 抛出无效响应结构异常。
            raise RuntimeError(f"{self.company_name} {stage_name} 未返回 JSON 对象")

        # 读取服务端成功状态文本。
        success_text = str(response_data.get("success", "")).strip().lower()

        # 判断服务端是否明确返回成功状态。
        if success_text in {"true", "1", "success"}:

            # 结束成功响应校验。
            return

        # 读取服务端失败说明文本。
        message_text = str(response_data.get("msg", response_data.get("message", "平台返回失败状态"))).strip()

        # 抛出不含凭据的协议失败异常。
        raise RuntimeError(f"{self.company_name} {stage_name} 失败：{message_text or '平台返回失败状态'}")

    # 定义总页数解析方法。
    def resolve_page_count(self, data_block, fallback):

        """
        从服务端数据对象读取可用总页数。

        :param data_block: 服务端数据对象。
        :type data_block: dict
        :param fallback: 已解析的总页数。
        :type fallback: int
        :return: 当前总页数。
        :rtype: int
        """

        # 读取服务端总页数字段。
        raw_page_count = data_block.get("pageCount", fallback) if isinstance(data_block, dict) else fallback

        try:

            # 返回至少为一页的总页数。
            return max(1, int(raw_page_count))

        except (TypeError, ValueError):

            # 返回已解析的总页数。
            return fallback

    # 定义原始字段合并方法。
    def merge_headers(self, headers, rows):

        """
        按服务端返回顺序合并分页中出现的原始字段。

        :param headers: 已收集的原始字段定义。
        :type headers: list[dict]
        :param rows: 当前页原始记录。
        :type rows: list[dict]
        :return: 合并后的原始字段定义。
        :rtype: list[dict]
        """

        # 建立已收集字段键集合。
        known_keys = {str(field.get("key", "")) for field in headers}

        # 遍历当前页每条原始记录。
        for row in rows:

            # 跳过非字典类型的记录。
            if not isinstance(row, dict):

                # 继续读取下一条原始记录。
                continue

            # 遍历记录中的原始字段键。
            for field_key in row.keys():

                # 转换当前字段键为文本。
                key_text = str(field_key)

                # 判断当前字段已经收集。
                if key_text in known_keys:

                    # 继续读取下一项原始字段。
                    continue

                # 保存当前接口字段定义。
                headers.append({"key": key_text, "title": key_text})

                # 记录当前字段已收集。
                known_keys.add(key_text)

        # 返回合并后的字段定义。
        return headers

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向记录日期未超出提交的查询范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str
        :param end_date: 查询结束日期。
        :type end_date: str
        :return: None。
        :rtype: None
        """

        # 读取当前数据类型的业务日期字段。
        date_field = DATA_TYPE_CONFIG[data_type]["date_field"]

        # 判断当前数据类型不包含业务日期字段。
        if not date_field:

            # 结束库存日期范围校验。
            return

        # 解析请求开始日期对象。
        start_value = datetime.strptime(start_date, "%Y-%m-%d").date()

        # 解析请求结束日期对象。
        end_value = datetime.strptime(end_date, "%Y-%m-%d").date()

        # 遍历返回的原始记录。
        for row in rows:

            # 读取当前记录的业务日期文本。
            date_text = str(row.get(date_field, "")).strip()

            # 跳过空日期字段记录。
            if not date_text:

                # 继续校验下一条记录。
                continue

            # 解析 YYYYMMDD 格式的业务日期。
            record_date = datetime.strptime(date_text[:8], "%Y%m%d").date()

            # 判断记录日期是否处于请求范围。
            if start_value <= record_date <= end_value:

                # 继续校验下一条记录。
                continue

            # 抛出业务日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期超出查询范围：{date_text}")

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, data_type, output_path):

        """
        将商业页面定义的字段标题和顺序写入 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 原始字段定义列表。
        :type headers: list[dict]
        :param data_type: 数据类型名称。
        :type data_type: str
        :param output_path: Excel 输出文件路径。
        :type output_path: str
        :return: None。
        :rtype: None
        """

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认活动工作表。
        worksheet = workbook.active

        # 设置工作表名称为当前数据类型。
        worksheet.title = data_type

        # 读取当前商业页面字段配置。
        page_columns = self.resolve_page_columns(data_type)

        # 写入页面原始表头。
        worksheet.append([column["title"] for column in page_columns])

        # 遍历全部原始记录。
        for row_index, row in enumerate(rows, start=1):

            # 构建当前记录的页面字段值。
            page_values = self.resolve_page_row_values(row, row_index, page_columns)

            # 写入当前记录页面字段值。
            worksheet.append(page_values)

        # 写入隐藏的接口原始字段工作表。
        self.write_raw_response_sheet(workbook, headers, rows)

        # 保存未样式化 Excel 工作簿。
        workbook.save(output_path)

        # 关闭 Excel 工作簿。
        workbook.close()

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)

    # 定义商业页面字段配置读取方法。
    def resolve_page_columns(self, data_type):

        """
        读取并校验商业专属的页面字段标题与顺序。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 页面字段定义列表。
        :rtype: list[dict]
        """

        # 读取商业专属页面字段映射。
        page_column_mapping = self.account.get("页面原始列", {})

        # 读取当前数据类型页面字段定义。
        configured_columns = page_column_mapping.get(data_type, []) if isinstance(page_column_mapping, dict) else []

        # 判断当前数据类型未配置页面字段定义。
        if not isinstance(configured_columns, list) or not configured_columns:

            # 抛出禁止回退到公共字段映射的异常。
            raise RuntimeError(f"{self.company_name} {data_type} 未配置页面原始列，不能使用公共字段标题或顺序")

        # 初始化已使用页面标题集合。
        used_titles = set()

        # 初始化已校验页面字段定义列表。
        page_columns = []

        # 遍历当前商业配置的页面字段定义。
        for column in configured_columns:

            # 判断字段定义是否为字典。
            if not isinstance(column, dict):

                # 抛出字段定义结构异常。
                raise RuntimeError(f"{self.company_name} {data_type} 页面原始列定义无效")

            # 读取页面显示标题。
            title_text = str(column.get("标题", "")).strip()

            # 读取接口字段键。
            field_key = str(column.get("字段", "")).strip()

            # 判断标题或字段键为空。
            if not title_text or not field_key:

                # 抛出字段标题或字段键缺失异常。
                raise RuntimeError(f"{self.company_name} {data_type} 页面原始列缺少标题或字段")

            # 判断页面标题重复。
            if title_text in used_titles:

                # 抛出页面标题重复异常。
                raise RuntimeError(f"{self.company_name} {data_type} 页面原始列标题重复：{title_text}")

            # 记录当前页面标题。
            used_titles.add(title_text)

            # 保存当前页面字段定义。
            page_columns.append({"title": title_text, "key": field_key})

        # 返回已校验页面字段定义。
        return page_columns

    # 定义页面记录值解析方法。
    def resolve_page_row_values(self, row, row_index, page_columns):

        """
        按页面字段定义生成单条 Excel 记录值。

        :param row: 服务端原始记录。
        :type row: dict
        :param row_index: 当前记录在页面中的行号。
        :type row_index: int
        :param page_columns: 页面字段定义列表。
        :type page_columns: list[dict]
        :return: 页面字段值列表。
        :rtype: list
        """

        # 初始化当前记录页面字段值列表。
        page_values = []

        # 遍历当前页面字段定义。
        for column in page_columns:

            # 读取当前页面字段键。
            field_key = column["key"]

            # 判断当前字段为页面行号。
            if field_key == "__row_number__":

                # 写入从一开始的页面行号。
                page_values.append(row_index)

                # 继续处理下一页面字段。
                continue

            # 写入当前接口字段值。
            page_values.append(row.get(field_key, ""))

        # 返回当前记录页面字段值。
        return page_values

    # 定义接口原始字段工作表写入方法。
    def write_raw_response_sheet(self, workbook, headers, rows):

        """
        在隐藏工作表保留接口返回的全部原始字段。

        :param workbook: 待写入的 Excel 工作簿。
        :type workbook: openpyxl.Workbook
        :param headers: 接口字段定义列表。
        :type headers: list[dict]
        :param rows: 接口原始记录列表。
        :type rows: list[dict]
        :return: None。
        :rtype: None
        """

        # 提取接口字段键列表。
        field_keys = [str(field.get("key", "")).strip() for field in headers if str(field.get("key", "")).strip()]

        # 判断当前响应不包含接口字段。
        if not field_keys:

            # 结束原始字段工作表写入。
            return

        # 创建接口原始字段工作表。
        raw_worksheet = workbook.create_sheet("接口原始字段")

        # 写入接口字段原始键名。
        raw_worksheet.append(field_keys)

        # 遍历接口原始记录。
        for row in rows:

            # 按接口字段返回顺序写入原始记录。
            raw_worksheet.append([row.get(field_key, "") for field_key in field_keys])

        # 隐藏接口原始字段工作表。
        raw_worksheet.sheet_state = "hidden"
