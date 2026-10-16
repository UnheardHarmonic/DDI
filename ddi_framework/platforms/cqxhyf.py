# -*- coding: utf-8 -*-
"""
重庆鑫斛药房连锁有限公司数据流向系统协议适配器。

本模块负责鑫斛数据流向系统的表单登录、HTML 表格分页查询、
购进双表头归并、原始字段保留和 Excel 文件生成。
"""

# 导入 HTML 实体处理模块。
import html as html_module

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入 HTML 解析器基类。
from html.parser import HTMLParser

# 导入 Cookie 容器。
from http.cookiejar import CookieJar

# 导入 URL 拼接函数。
from urllib.parse import urlencode

# 导入 URL 拼接函数。
from urllib.parse import urljoin

# 导入 HTTP 错误类型。
from urllib.error import HTTPError

# 导入 Cookie 处理器。
from urllib.request import HTTPCookieProcessor

# 导入 URL 请求对象。
from urllib.request import Request

# 导入 URL 打开器构建函数。
from urllib.request import build_opener

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义平台数据类型别名。
CQXHYF_DATA_TYPE_ALIASES = {
    "纯销": "纯销流向",
}


# 定义平台页面端点配置。
CQXHYF_ENDPOINT_DEFINITIONS = {
    "goodsin": {"页面名称": "入库", "路径": "goodsin", "查询类型": "日期区间"},
    "backinfo": {"页面名称": "退仓", "路径": "backinfo", "查询类型": "日期区间"},
    "sendinfo": {"页面名称": "配送", "路径": "sendinfo", "查询类型": "日期区间"},
    "stockinfo": {"页面名称": "库存", "路径": "stockinfo", "查询类型": "库存快照"},
    "saleinfo": {"页面名称": "销售", "路径": "saleinfo", "查询类型": "日期区间"},
}


# 定义平台数据类型查询配置。
CQXHYF_QUERY_DEFINITIONS = {
    "购进流向": {"端点列表": ["goodsin", "backinfo"], "日期字段": "购进日期", "日期模式": "日期区间"},
    "配送流向": {"端点列表": ["sendinfo"], "日期字段": "销售日期", "日期模式": "日期区间"},
    "库存": {"端点列表": ["stockinfo"], "日期字段": "库存日期", "日期模式": "库存快照"},
    "纯销流向": {"端点列表": ["saleinfo"], "日期字段": "销售日期", "日期模式": "日期区间"},
}


# 定义平台标准表头配置。
CQXHYF_STANDARD_HEADERS = {
    "购进流向": ["数据类型", "来源表单", "购进日期", "生效时间", "业务单号", "相关单位编码", "相关单位名称", "商品编码", "商品名称", "商品规格", "生产企业", "商品单位", "生成批号", "数量", "有效期至"],
    "配送流向": ["数据类型", "来源表单", "销售日期", "生效时间", "相关单位编码", "相关单位名称", "客户名称", "商品编码", "商品名称", "商品规格", "生产企业", "商品单位", "生成批号", "数量", "有效期至"],
    "库存": ["数据类型", "来源表单", "库存日期", "业务机构编码", "业务机构名称", "商品编码", "商品名称", "商品规格", "生产企业", "商品单位", "生成批号", "数量", "有效期至"],
    "纯销流向": ["数据类型", "来源表单", "销售日期", "销售门店", "买方名称", "区域", "商品编码", "商品名称", "商品规格", "生产企业", "商品单位", "数量"],
}


# 定义鑫斛数据流向 HTML 表格解析器。
class CqxhyfTableParser(HTMLParser):

    """
    解析鑫斛数据流向系统 HTML 页面中的表格和分页链接。

    :return: HTML 表格解析器实例。
    :rtype: CqxhyfTableParser
    """

    # 定义解析器初始化方法。
    def __init__(self):

        """
        初始化 HTML 表格解析状态。

        :return: None。
        :rtype: None
        """

        # 调用 HTML 解析器初始化逻辑。
        super().__init__(convert_charrefs=True)

        # 初始化页面表格集合。
        self.tables = []

        # 初始化当前表格。
        self.current_table = None

        # 初始化当前表格行。
        self.current_row = None

        # 初始化当前单元格文本片段。
        self.current_cell = None

        # 初始化表格嵌套深度。
        self.table_depth = 0

        # 初始化分页链接集合。
        self.page_links = []

    # 定义开始标签处理方法。
    def handle_starttag(self, tag, attrs):

        """
        处理 HTML 开始标签。

        :param tag: 标签名称。
        :type tag: str
        :param attrs: 标签属性列表。
        :type attrs: list[tuple[str, str | None]]
        :return: None。
        :rtype: None
        """

        # 读取标签属性映射。
        attr_map = dict(attrs)

        # 标准化标签名称。
        tag_name = tag.lower()

        # 判断当前标签是否为表格。
        if tag_name == "table":

            # 累加表格嵌套深度。
            self.table_depth += 1

            # 判断是否进入外层数据表格。
            if self.table_depth == 1:

                # 初始化当前表格容器。
                self.current_table = []

        # 判断当前标签是否为表格行。
        if tag_name == "tr" and self.table_depth:

            # 初始化当前表格行。
            self.current_row = []

        # 判断当前标签是否为表格单元格。
        if tag_name in ("td", "th") and self.current_row is not None:

            # 初始化当前单元格文本片段。
            self.current_cell = []

        # 判断当前标签是否为链接。
        if tag_name == "a":

            # 读取 LayUI data-open 跳转地址。
            data_open = attr_map.get("data-open") or ""

            # 读取普通链接跳转地址。
            href_value = attr_map.get("href") or ""

            # 保存可用分页跳转地址。
            self.page_links.append(data_open or href_value)

    # 定义文本处理方法。
    def handle_data(self, data):

        """
        处理 HTML 文本内容。

        :param data: 文本内容。
        :type data: str
        :return: None。
        :rtype: None
        """

        # 判断当前是否处于表格单元格内。
        if self.current_cell is None:

            # 结束非单元格文本处理。
            return None

        # 标准化文本片段。
        text = data.strip()

        # 判断文本片段是否为空。
        if not text:

            # 结束空文本处理。
            return None

        # 保存当前文本片段。
        self.current_cell.append(text)

        # 返回空结果。
        return None

    # 定义结束标签处理方法。
    def handle_endtag(self, tag):

        """
        处理 HTML 结束标签。

        :param tag: 标签名称。
        :type tag: str
        :return: None。
        :rtype: None
        """

        # 标准化标签名称。
        tag_name = tag.lower()

        # 判断当前标签是否为表格单元格结束。
        if tag_name in ("td", "th") and self.current_cell is not None:

            # 合并当前单元格文本。
            cell_text = "".join(self.current_cell).strip()

            # 追加当前单元格文本。
            self.current_row.append(cell_text)

            # 清空当前单元格状态。
            self.current_cell = None

        # 判断当前标签是否为表格行结束。
        if tag_name == "tr" and self.current_row is not None:

            # 判断当前行是否包含有效文本。
            if any(self.current_row):

                # 保存当前表格行。
                self.current_table.append(self.current_row)

            # 清空当前行状态。
            self.current_row = None

        # 判断当前标签是否为表格结束。
        if tag_name == "table" and self.table_depth:

            # 判断当前结束标签是否对应外层表格。
            if self.table_depth == 1 and self.current_table is not None:

                # 保存当前完整表格。
                self.tables.append(self.current_table)

                # 清空当前表格状态。
                self.current_table = None

            # 递减表格嵌套深度。
            self.table_depth -= 1


# 定义重庆鑫斛平台适配器。
class CqxhyfPlatform(BasePlatform):

    """
    重庆鑫斛药房连锁有限公司数据流向系统协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台适配器实例。
    :rtype: CqxhyfPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化鑫斛数据流向系统协议适配器。

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

        # 保存站点根地址。
        self.base_url = account.get("接口根地址", "http://xcx.azmks.com").rstrip("/")

        # 保存登录页面地址。
        self.login_page_url = account.get("登录页", f"{self.base_url}/index/dataflow/login.html?spm=")

        # 保存登录接口地址。
        self.login_api_url = account.get("登录接口", self.login_page_url)

        # 保存数据页根路径。
        self.dataflow_base_path = account.get("数据页根路径", "/index/dataflow")

        # 保存登录账号。
        self.username = account.get("账号", "")

        # 保存登录密码。
        self.password = account.get("密码", "")

        # 保存库存查询类型。
        self.stock_type = str(account.get("库存类型编码", "1"))

        # 保存最大分页页数。
        self.max_pages = int(account.get("最大分页页数", 500))

        # 初始化 Cookie 容器。
        self.cookie_jar = CookieJar()

        # 初始化协议请求打开器。
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

        # 初始化登录状态。
        self.logged_in = False

    # 定义平台登录方法。
    def login(self):

        """
        登录鑫斛数据流向系统。

        :return: 登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("鑫斛数据流向系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页以初始化服务端会话 Cookie。
        self.open_text(self.login_page_url, self.build_page_headers(self.login_page_url))

        # 构建登录表单数据。
        payload = {"username": self.username, "password": self.password}

        # 提交登录表单。
        response_text = self.post_form(self.login_api_url, payload, self.build_login_headers())

        # 解析登录响应。
        response_data = self.parse_json_response(response_text)

        # 判断平台登录状态。
        if str(response_data.get("code")) != "1":

            # 抛出登录失败异常。
            raise RuntimeError(f"鑫斛数据流向系统登录失败：{response_data.get('msg') or response_text[:200]}")

        # 标记当前会话已登录。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("登录成功", self.username, "green"), self.ph.kv("Cookie", f"{len(list(self.cookie_jar))} 个", "cyan")))

        # 返回登录摘要。
        return {"success": True, "cookie_count": len(list(self.cookie_jar))}

    # 定义 Cookie 保存方法。
    def save_cookie(self, output_dir):

        """
        保存当前登录 Cookie。

        :param output_dir: Cookie 文件输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 创建 Cookie 输出目录。
        os.makedirs(output_dir, exist_ok=True)

        # 构建 Cookie 文件路径。
        cookie_path = os.path.join(output_dir, f"{self.company_name}_cookie.json")

        # 提取当前 Cookie 值。
        cookie_values = {cookie.name: cookie.value for cookie in self.cookie_jar}

        # 构建 Cookie 文件内容。
        cookie_data = {"base_url": self.base_url, "login_page_url": self.login_page_url, "cookies": cookie_values}

        # 写入 Cookie JSON 文件。
        with open(cookie_path, "w", encoding="utf-8") as file_obj:

            # 序列化 Cookie 内容。
            json.dump(cookie_data, file_obj, ensure_ascii=False, indent=2)

        # 打印 Cookie 保存日志。
        self.ph.success(self.ph.kv("登录 Cookie 已保存", self.ph.path(cookie_path), "green"))

        # 返回 Cookie 文件路径。
        return cookie_path

    # 定义平台查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, start_date, end_date)

        # 返回协议分页查询结果。
        return self.fetch_protocol_rows(data_type, start_date, end_date)


    # 定义查询落地 Excel 方法。
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

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, start_date, end_date)

        # 查询协议数据行。
        rows = self.fetch_protocol_rows(data_type, start_date, end_date)

        # 读取输出目录。
        save_dir = output_dir or "downloads"

        # 创建输出目录。
        os.makedirs(save_dir, exist_ok=True)

        # 构建输出文件名。
        file_name = self.build_output_file_name(data_type, start_date, end_date)

        # 拼接输出文件路径。
        output_path = os.path.join(save_dir, file_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(data_type, rows, output_path)

        # 应用统一 Excel 样式。
        apply_standard_excel_style(output_path)

        # 打印 Excel 生成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 文件路径。
        return output_path

    # 定义标准输出命名日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        解析标准输出文件名使用的业务日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 标准输出文件名使用的业务日期。
        :rtype: str | None
        """

        # 解析规范数据类型。
        canonical_data_type = self.resolve_data_type(data_type)

        # 判断当前数据类型是否为库存。
        if canonical_data_type == "库存":

            # 返回库存文件命名使用的导出当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向类使用的查询开始日期。
        return start_date or end_date


    # 定义协议分页查询方法。
    def fetch_protocol_rows(self, data_type, start_date, end_date):

        """
        通过 HTML 表格页面分页读取业务数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 确保当前会话已经登录。
        self.ensure_logged_in()

        # 解析规范数据类型。
        canonical_data_type = self.resolve_data_type(data_type)

        # 读取查询定义。
        query_definition = CQXHYF_QUERY_DEFINITIONS[canonical_data_type]

        # 初始化结果行容器。
        result_rows = []

        # 遍历当前数据类型涉及的页面端点。
        for endpoint_name in query_definition["端点列表"]:

            # 查询当前页面端点全部分页。
            endpoint_rows = self.fetch_endpoint_rows(canonical_data_type, endpoint_name, start_date, end_date)

            # 合并当前端点结果行。
            result_rows.extend(endpoint_rows)

        # 校验日期范围。
        self.validate_date_range(canonical_data_type, query_definition, result_rows, start_date, end_date)

        # 返回查询结果行。
        return result_rows

    # 定义单端点分页查询方法。
    def fetch_endpoint_rows(self, canonical_data_type, endpoint_name, start_date, end_date):

        """
        查询单个 HTML 表格端点的全部分页。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param endpoint_name: 页面端点名称。
        :type endpoint_name: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 当前端点的标准化数据行。
        :rtype: list[dict]
        """

        # 读取端点定义。
        endpoint_definition = CQXHYF_ENDPOINT_DEFINITIONS[endpoint_name]

        # 构建首个分页地址。
        next_url = self.build_endpoint_url(endpoint_definition, start_date, end_date)

        # 初始化已访问地址集合。
        visited_urls = set()

        # 初始化分页页码。
        page_index = 0

        # 初始化端点结果容器。
        endpoint_rows = []

        # 循环读取页面分页。
        while next_url:

            # 判断当前页码是否超过安全上限。
            if page_index >= self.max_pages:

                # 抛出分页保护异常。
                raise RuntimeError(f"{endpoint_definition['页面名称']}分页超过安全上限：{self.max_pages}")

            # 判断分页地址是否已经访问过。
            if next_url in visited_urls:

                # 结束重复分页循环。
                break

            # 记录当前分页地址。
            visited_urls.add(next_url)

            # 累加分页页码。
            page_index += 1

            # 拉取当前分页 HTML。
            html_text = self.open_text(next_url, self.build_page_headers(next_url))

            # 解析当前分页表格和下一页地址。
            table_headers, table_rows, next_href = self.parse_table_page(html_text)

            # 转换当前分页表格行。
            converted_rows = [self.convert_table_row(canonical_data_type, endpoint_definition, table_headers, table_row) for table_row in table_rows]

            # 合并当前分页数据。
            endpoint_rows.extend(converted_rows)

            # 打印分页查询日志。
            self.ph.info(self.ph.join(self.ph.kv("页面", endpoint_definition["页面名称"], "cyan"), self.ph.kv("页码", page_index, "cyan"), self.ph.kv("本页", f"{len(table_rows)} 条", "cyan"), self.ph.kv("累计", f"{len(endpoint_rows)} 条", "green")))

            # 判断当前分页是否没有数据。
            if not table_rows:

                # 结束分页循环。
                break

            # 构建下一页完整地址。
            next_url = urljoin(self.base_url, next_href) if next_href else ""

        # 返回当前端点结果行。
        return endpoint_rows

    # 定义数据类型解析方法。
    def resolve_data_type(self, data_type):

        """
        解析平台支持的规范数据类型。

        :param data_type: 输入数据类型。
        :type data_type: str
        :return: 规范数据类型。
        :rtype: str
        """

        # 读取数据类型别名。
        canonical_data_type = CQXHYF_DATA_TYPE_ALIASES.get(data_type, data_type)

        # 校验数据类型是否已配置。
        if canonical_data_type not in CQXHYF_QUERY_DEFINITIONS:

            # 抛出不支持的数据类型异常。
            raise KeyError(f"鑫斛数据流向系统暂不支持数据类型：{data_type}")

        # 返回规范数据类型。
        return canonical_data_type


    # 定义首个端点地址构建方法。
    def build_endpoint_url(self, endpoint_definition, start_date, end_date):

        """
        构建页面端点首个分页地址。

        :param endpoint_definition: 页面端点定义。
        :type endpoint_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 完整页面地址。
        :rtype: str
        """

        # 初始化查询参数。
        params = {"goods_sn": ""}

        # 判断当前端点是否为库存快照。
        if endpoint_definition["查询类型"] == "库存快照":

            # 写入库存类型参数。
            params["type"] = self.stock_type

        # 处理日期区间端点。
        else:

            # 写入开始日期参数。
            params["start_time"] = start_date or ""

            # 写入结束日期参数。
            params["end_time"] = end_date or ""

        # 构建页面路径。
        endpoint_path = f"{self.dataflow_base_path}/{endpoint_definition['路径']}"

        # 拼接完整页面地址。
        return f"{self.base_url}{endpoint_path}?{urlencode(params)}"

    # 定义表格页面解析方法。
    def parse_table_page(self, html_text):

        """
        解析 HTML 页面中的数据表格和下一页链接。

        :param html_text: 页面 HTML 文本。
        :type html_text: str
        :return: 表头、数据行和下一页地址。
        :rtype: tuple[list[str], list[list[str]], str]
        """

        # 初始化表格解析器。
        parser = CqxhyfTableParser()

        # 解析 HTML 文本。
        parser.feed(html_text)

        # 选择候选数据表格。
        table_rows = self.select_data_table(parser.tables)

        # 判断页面是否没有数据表格。
        if not table_rows:

            # 返回空表格结果。
            return [], [], ""

        # 读取表头行。
        headers = self.normalize_headers(table_rows[0])

        # 读取数据行集合。
        rows = [row for row in table_rows[1:] if any(row)]

        # 解析下一页地址。
        next_href = self.resolve_next_href(parser.page_links)

        # 返回页面解析结果。
        return headers, rows, next_href

    # 定义数据表格选择方法。
    def select_data_table(self, tables):

        """
        从页面表格集合中选择明细数据表。

        :param tables: 页面表格集合。
        :type tables: list[list[list[str]]]
        :return: 明细表格行集合。
        :rtype: list[list[str]]
        """

        # 判断页面表格集合是否为空。
        if not tables:

            # 返回空表格。
            return []

        # 返回行数与列数乘积最大的表格。
        return max(tables, key=lambda table_rows: len(table_rows) * max([len(row) for row in table_rows] or [0]))

    # 定义表头标准化方法。
    def normalize_headers(self, raw_headers):

        """
        标准化表格表头。

        :param raw_headers: 原始表头列表。
        :type raw_headers: list[str]
        :return: 去重后的表头列表。
        :rtype: list[str]
        """

        # 初始化表头计数映射。
        header_counts = {}

        # 初始化标准化表头列表。
        headers = []

        # 遍历原始表头。
        for header in raw_headers:

            # 清理表头文本。
            header_text = str(header).strip() or "空字段"

            # 累加当前表头出现次数。
            header_counts[header_text] = header_counts.get(header_text, 0) + 1

            # 判断当前表头是否首次出现。
            if header_counts[header_text] == 1:

                # 追加原始表头名称。
                headers.append(header_text)

            # 处理重复表头名称。
            else:

                # 追加带序号的表头名称。
                headers.append(f"{header_text}_{header_counts[header_text]}")

        # 返回标准化表头列表。
        return headers

    # 定义下一页地址解析方法。
    def resolve_next_href(self, page_links):

        """
        从页面链接集合中解析下一页地址。

        :param page_links: 页面链接集合。
        :type page_links: list[str]
        :return: 下一页相对地址。
        :rtype: str
        """

        # 遍历页面链接。
        for page_link in reversed(page_links):

            # 解码 HTML 实体。
            href_text = html_module.unescape(page_link or "")

            # 判断链接是否不是分页地址。
            if "page=" not in href_text:

                # 继续检查前一个链接。
                continue

            # 判断链接是否为无效脚本。
            if "javascript:" in href_text:

                # 继续检查前一个链接。
                continue

            # 返回下一页地址。
            return href_text

        # 返回空地址。
        return ""

    # 定义表格行转换方法。
    def convert_table_row(self, canonical_data_type, endpoint_definition, headers, table_row):

        """
        将页面表格行转换为标准输出行。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param endpoint_definition: 页面端点定义。
        :type endpoint_definition: dict
        :param headers: 表头列表。
        :type headers: list[str]
        :param table_row: 表格行。
        :type table_row: list[str]
        :return: 标准输出行。
        :rtype: dict
        """

        # 构建原始字段映射。
        raw_row = {header: table_row[index] if index < len(table_row) else "" for index, header in enumerate(headers)}

        # 读取来源表单名称。
        source_label = endpoint_definition["页面名称"]

        # 根据数据类型构建标准字段。
        if canonical_data_type == "购进流向":

            # 返回购进流向标准化行。
            return self.convert_purchase_row(canonical_data_type, source_label, raw_row)

        # 根据数据类型构建配送字段。
        if canonical_data_type == "配送流向":

            # 返回配送流向标准化行。
            return self.convert_delivery_row(canonical_data_type, source_label, raw_row)

        # 根据数据类型构建库存字段。
        if canonical_data_type == "库存":

            # 返回库存标准化行。
            return self.convert_stock_row(canonical_data_type, source_label, raw_row)

        # 返回纯销标准化行。
        return self.convert_retail_row(canonical_data_type, source_label, raw_row)

    # 定义购进流向行转换方法。
    def convert_purchase_row(self, canonical_data_type, source_label, raw_row):

        """
        转换入库和退仓页面行到统一购进流向表头。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param source_label: 来源表单名称。
        :type source_label: str
        :param raw_row: 原始表格行。
        :type raw_row: dict
        :return: 购进流向标准行。
        :rtype: dict
        """

        # 初始化标准输出行。
        output_row = {"数据类型": canonical_data_type, "来源表单": source_label}

        # 写入购进日期字段。
        output_row["购进日期"] = raw_row.get("生效时间", "")

        # 写入生效时间字段。
        output_row["生效时间"] = raw_row.get("生效时间", "")

        # 写入业务单号字段。
        output_row["业务单号"] = raw_row.get("入库单编号", "")

        # 写入相关单位编码字段。
        output_row["相关单位编码"] = raw_row.get("相关单位编码", "")

        # 写入相关单位名称字段。
        output_row["相关单位名称"] = raw_row.get("往来单位名称") or raw_row.get("相关单位名称", "")

        # 写入通用商品字段。
        self.fill_common_product_fields(output_row, raw_row)

        # 追加原始字段。
        self.append_raw_fields(output_row, source_label, raw_row)

        # 返回标准输出行。
        return output_row

    # 定义配送流向行转换方法。
    def convert_delivery_row(self, canonical_data_type, source_label, raw_row):

        """
        转换配送页面行到配送流向标准表头。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param source_label: 来源表单名称。
        :type source_label: str
        :param raw_row: 原始表格行。
        :type raw_row: dict
        :return: 配送流向标准行。
        :rtype: dict
        """

        # 初始化标准输出行。
        output_row = {"数据类型": canonical_data_type, "来源表单": source_label}

        # 写入销售日期字段。
        output_row["销售日期"] = raw_row.get("生效时间", "")

        # 写入生效时间字段。
        output_row["生效时间"] = raw_row.get("生效时间", "")

        # 写入相关单位编码字段。
        output_row["相关单位编码"] = raw_row.get("相关单位编码", "")

        # 写入相关单位名称字段。
        output_row["相关单位名称"] = raw_row.get("相关单位名称", "")

        # 写入客户名称字段。
        output_row["客户名称"] = raw_row.get("相关单位名称", "")

        # 写入通用商品字段。
        self.fill_common_product_fields(output_row, raw_row)

        # 追加原始字段。
        self.append_raw_fields(output_row, source_label, raw_row)

        # 返回标准输出行。
        return output_row

    # 定义库存行转换方法。
    def convert_stock_row(self, canonical_data_type, source_label, raw_row):

        """
        转换库存页面行到库存标准表头。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param source_label: 来源表单名称。
        :type source_label: str
        :param raw_row: 原始表格行。
        :type raw_row: dict
        :return: 库存标准行。
        :rtype: dict
        """

        # 初始化标准输出行。
        output_row = {"数据类型": canonical_data_type, "来源表单": source_label}

        # 写入库存日期字段。
        output_row["库存日期"] = datetime.now().strftime("%Y-%m-%d")

        # 写入业务机构编码字段。
        output_row["业务机构编码"] = raw_row.get("业务机构编码", "")

        # 写入业务机构名称字段。
        output_row["业务机构名称"] = raw_row.get("业务机构名称", "")

        # 写入通用商品字段。
        self.fill_common_product_fields(output_row, raw_row)

        # 追加原始字段。
        self.append_raw_fields(output_row, source_label, raw_row)

        # 返回标准输出行。
        return output_row

    # 定义纯销流向行转换方法。
    def convert_retail_row(self, canonical_data_type, source_label, raw_row):

        """
        转换销售页面行到纯销流向标准表头。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param source_label: 来源表单名称。
        :type source_label: str
        :param raw_row: 原始表格行。
        :type raw_row: dict
        :return: 纯销流向标准行。
        :rtype: dict
        """

        # 初始化标准输出行。
        output_row = {"数据类型": canonical_data_type, "来源表单": source_label}

        # 写入销售日期字段。
        output_row["销售日期"] = raw_row.get("销售日期", "")

        # 写入销售门店字段。
        output_row["销售门店"] = raw_row.get("销售门店", "")

        # 写入买方名称字段。
        output_row["买方名称"] = raw_row.get("销售门店", "")

        # 写入区域字段。
        output_row["区域"] = raw_row.get("区域", "")

        # 写入通用商品字段。
        self.fill_common_product_fields(output_row, raw_row)

        # 追加原始字段。
        self.append_raw_fields(output_row, source_label, raw_row)

        # 返回标准输出行。
        return output_row

    # 定义通用商品字段填充方法。
    def fill_common_product_fields(self, output_row, raw_row):

        """
        填充商品、批号、数量和效期字段。

        :param output_row: 标准输出行。
        :type output_row: dict
        :param raw_row: 原始表格行。
        :type raw_row: dict
        :return: None。
        :rtype: None
        """

        # 写入商品编码字段。
        output_row["商品编码"] = raw_row.get("商品编码", "")

        # 写入商品名称字段。
        output_row["商品名称"] = raw_row.get("商品名称", "")

        # 写入商品规格字段。
        output_row["商品规格"] = raw_row.get("商品规格", "")

        # 写入生产企业字段。
        output_row["生产企业"] = raw_row.get("生产企业", "")

        # 写入商品单位字段。
        output_row["商品单位"] = raw_row.get("商品单位", "")

        # 写入生成批号字段。
        output_row["生成批号"] = raw_row.get("生成批号", "")

        # 写入数量字段。
        output_row["数量"] = raw_row.get("数量", "")

        # 写入有效期至字段。
        output_row["有效期至"] = raw_row.get("有效期至", "")

        # 返回空结果。
        return None

    # 定义原始字段追加方法。
    def append_raw_fields(self, output_row, source_label, raw_row):

        """
        将页面原始字段追加到标准字段之后。

        :param output_row: 标准输出行。
        :type output_row: dict
        :param source_label: 来源表单名称。
        :type source_label: str
        :param raw_row: 原始表格行。
        :type raw_row: dict
        :return: None。
        :rtype: None
        """

        # 遍历页面原始字段。
        for field_name, field_value in raw_row.items():

            # 构建原始字段输出名称。
            raw_field_name = f"原始{source_label}_{field_name}"

            # 写入原始字段值。
            output_row[raw_field_name] = field_value

        # 返回空结果。
        return None

    # 定义日期范围校验方法。
    def validate_date_range(self, canonical_data_type, query_definition, rows, start_date, end_date):

        """
        校验流向业务日期是否落在查询区间内。

        :param canonical_data_type: 规范数据类型。
        :type canonical_data_type: str
        :param query_definition: 查询定义。
        :type query_definition: dict
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 判断库存快照是否无需区间校验。
        if query_definition.get("日期模式") == "库存快照":

            # 返回空结果。
            return None

        # 判断结果行是否为空。
        if not rows:

            # 返回空结果。
            return None

        # 读取业务日期字段。
        date_field = query_definition["日期字段"]

        # 提取业务日期列表。
        row_dates = [str(row.get(date_field, ""))[:10] for row in rows if str(row.get(date_field, ""))[:10]]

        # 判断业务日期列表是否为空。
        if not row_dates:

            # 打印日期字段缺失提示。
            self.ph.warning(f"{canonical_data_type} 未解析到可校验的业务日期字段：{date_field}")

            # 返回空结果。
            return None

        # 计算最小业务日期。
        min_date = min(row_dates)

        # 计算最大业务日期。
        max_date = max(row_dates)

        # 判断业务日期是否早于开始日期。
        if start_date and min_date < start_date:

            # 抛出日期范围异常。
            raise RuntimeError(f"{canonical_data_type} 业务日期超出查询范围：{min_date} - {max_date}")

        # 判断业务日期是否晚于结束日期。
        if end_date and max_date > end_date:

            # 抛出日期范围异常。
            raise RuntimeError(f"{canonical_data_type} 业务日期超出查询范围：{min_date} - {max_date}")

        # 打印日期范围校验日志。
        self.ph.success(self.ph.join(self.ph.kv("日期范围", f"{min_date} - {max_date}", "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回空结果。
        return None

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, data_type, rows, target_path):

        """
        将查询结果写入 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :param target_path: 目标文件路径。
        :type target_path: str
        :return: None。
        :rtype: None
        """

        # 导入 Excel 工作簿对象。
        from openpyxl import Workbook

        # 导入列号转换函数。
        from openpyxl.utils import get_column_letter

        # 构建 Excel 表头。
        headers = self.build_excel_headers(data_type, rows)

        # 创建 Excel 工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type[:31]

        # 写入表头行。
        worksheet.append(headers)

        # 遍历查询结果行。
        for row_data in rows:

            # 按表头顺序写入当前行。
            worksheet.append([row_data.get(header, "") for header in headers])

        # 遍历表头设置列宽。
        for column_index, header_name in enumerate(headers, start=1):

            # 计算当前列最大显示宽度。
            width = max([len(str(header_name))] + [len(str(row_data.get(header_name, ""))) for row_data in rows[:200]])

            # 设置当前列宽。
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(width + 2, 12), 45)

        # 判断目标文件是否已经存在。
        if os.path.exists(target_path):

            # 删除旧目标文件。
            os.remove(target_path)

        # 保存 Excel 文件。
        workbook.save(target_path)

        # 返回空结果。
        return None

    # 定义 Excel 表头构建方法。
    def build_excel_headers(self, data_type, rows):

        """
        构建 Excel 输出表头。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行。
        :type rows: list[dict]
        :return: Excel 表头列表。
        :rtype: list[str]
        """

        # 解析规范数据类型。
        canonical_data_type = self.resolve_data_type(data_type)

        # 初始化标准表头。
        headers = list(CQXHYF_STANDARD_HEADERS[canonical_data_type])

        # 初始化已存在表头集合。
        existing_headers = set(headers)

        # 遍历查询结果行。
        for row_data in rows:

            # 遍历当前行字段。
            for field_name in row_data.keys():

                # 判断字段是否已经存在。
                if field_name in existing_headers:

                    # 继续处理下一个字段。
                    continue

                # 追加动态字段。
                headers.append(field_name)

                # 标记字段已存在。
                existing_headers.add(field_name)

        # 返回表头列表。
        return headers

    # 定义页面请求头构建方法。
    def build_page_headers(self, referer):

        """
        构建 HTML 页面请求头。

        :param referer: 来源页面地址。
        :type referer: str
        :return: 页面请求头。
        :rtype: dict
        """

        # 返回页面请求头。
        return {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Referer": referer, "User-Agent": self.user_agent()}

    # 定义登录请求头构建方法。
    def build_login_headers(self):

        """
        构建登录表单请求头。

        :return: 登录请求头。
        :rtype: dict
        """

        # 返回登录请求头。
        return {"Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": self.base_url, "Referer": self.login_page_url, "User-Agent": self.user_agent(), "X-Requested-With": "XMLHttpRequest"}

    # 定义用户代理构建方法。
    def user_agent(self):

        """
        返回协议请求使用的浏览器 User-Agent。

        :return: User-Agent 文本。
        :rtype: str
        """

        # 返回稳定的桌面浏览器 User-Agent。
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"

    # 定义表单 POST 方法。
    def post_form(self, url, payload, headers):

        """
        发送表单 POST 请求并返回响应文本。

        :param url: 请求地址。
        :type url: str
        :param payload: 表单字段。
        :type payload: dict
        :param headers: 请求头。
        :type headers: dict
        :return: 响应文本。
        :rtype: str
        """

        # 编码表单请求体。
        request_body = urlencode(payload).encode("utf-8")

        # 构建 POST 请求对象。
        request = Request(url, data=request_body, headers=headers, method="POST")

        # 返回响应文本。
        return self.open_request_text(request)

    # 定义 GET 请求方法。
    def open_text(self, url, headers):

        """
        发送 GET 请求并返回响应文本。

        :param url: 请求地址。
        :type url: str
        :param headers: 请求头。
        :type headers: dict
        :return: 响应文本。
        :rtype: str
        """

        # 构建 GET 请求对象。
        request = Request(url, headers=headers, method="GET")

        # 返回响应文本。
        return self.open_request_text(request)

    # 定义请求发送方法。
    def open_request_text(self, request):

        """
        发送 urllib 请求并按 UTF-8 解码响应。

        :param request: urllib 请求对象。
        :type request: urllib.request.Request
        :return: 响应文本。
        :rtype: str
        """

        # 捕获 HTTP 层异常以保留响应摘要。
        try:

            # 发送协议请求。
            response = self.opener.open(request, timeout=60)

            # 读取响应字节。
            response_bytes = response.read()

        # 处理 HTTP 错误响应。
        except HTTPError as error:

            # 读取错误响应体。
            error_text = error.read().decode("utf-8", errors="replace")

            # 抛出包含状态码的异常。
            raise RuntimeError(f"HTTP请求失败：{error.code} {error.reason} {error_text[:300]}") from error

        # 返回 UTF-8 响应文本。
        return response_bytes.decode("utf-8", errors="replace")

    # 定义 JSON 响应解析方法。
    def parse_json_response(self, response_text):

        """
        解析平台 JSON 响应文本。

        :param response_text: JSON 响应文本。
        :type response_text: str
        :return: JSON 对象。
        :rtype: dict
        """

        # 捕获 JSON 解析异常。
        try:

            # 返回 JSON 解析结果。
            return json.loads(response_text)

        # 处理 JSON 解析失败。
        except json.JSONDecodeError as error:

            # 抛出响应格式异常。
            raise RuntimeError(f"平台响应不是 JSON：{response_text[:300]}") from error
