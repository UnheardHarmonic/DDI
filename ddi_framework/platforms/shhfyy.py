# -*- coding: utf-8 -*-
"""
上海汇丰医药药材有限责任公司数据服务云平台协议适配器。

本模块负责数据服务云平台的登录、会话初始化、分页查询、结果落表和标准文件命名。
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统路径模块。
import os

# 导入日期时间模块。
from datetime import datetime

# 导入时间增量模块。
from datetime import timedelta

# 导入 URL 解析模块。
from urllib.parse import urlparse

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义上海汇丰医药药材有限责任公司平台查询定义。
SHHFYY_QUERY_DEFINITIONS = {

    # 定义购进流向查询配置。
    "购进流向": {
        "页面名称": "进货数据查询",
        "页面文件": "queryImp.jsp",
        "请求文件名": "/OnLineDevelopProFiles/DataFlowQuery/cjcx/queryImp",
        "请求接口": "/OnLineDevelopProFiles/DataFlowQuery/cjcx/com.wx.utils.publicMemer.JDBCComponent.dbPageQuery.biz.ext",
        "标准字段": [
            {"name": "日期", "source": "impdate", "kind": "date"},
            {"name": "配送公司", "source": "compname", "kind": "text"},
            {"name": "供应商编码", "source": "vendcode", "kind": "text"},
            {"name": "供应商名称", "source": "vendname", "kind": "text"},
            {"name": "进货门店编码", "source": "deptcode", "kind": "text"},
            {"name": "进货门店名称", "source": "deptname", "kind": "text"},
            {"name": "商品编码", "source": "goodscode", "kind": "text"},
            {"name": "商品名称", "source": "goodsname", "kind": "text"},
            {"name": "规格", "source": "goodsspec", "kind": "text"},
            {"name": "单位", "source": "goodsunit", "kind": "text"},
            {"name": "批准文号", "source": "authorize", "kind": "text"},
            {"name": "生产厂家", "source": "manufactory", "kind": "text"},
            {"name": "批号", "source": "lot", "kind": "text"},
            {"name": "有效期", "source": "validdate", "kind": "date"},
            {"name": "生产日期", "source": "procdate", "kind": "date"},
            {"name": "数量", "source": "qty", "kind": "text"},
            {"name": "单价", "source": "price", "kind": "text"},
            {"name": "类型", "source": "sheettype", "kind": "text"},
            {"name": "流水号", "source": "procid", "kind": "text"},
        ],
        "原始字段": [
            "authorize",
            "comp_goods",
            "compname",
            "deptcode",
            "deptname",
            "goodscode",
            "goodsname",
            "goodsspec",
            "goodsunit",
            "impdate",
            "lot",
            "manufactory",
            "price",
            "procdate",
            "procid",
            "qty",
            "rn",
            "sheettype",
            "validdate",
            "vendcode",
            "vendname",
        ],
        "日期模式": "range",
    },

    # 定义库存查询配置。
    "库存": {
        "页面名称": "库存数据查询",
        "页面文件": "queryStk.jsp",
        "请求文件名": "/OnLineDevelopProFiles/DataFlowQuery/cjcx/queryStk",
        "请求接口": "/OnLineDevelopProFiles/DataFlowQuery/cjcx/com.wx.utils.publicMemer.JDBCComponent.dbPageQuery.biz.ext",
        "标准字段": [
            {"name": "日期", "source": "stkdate", "kind": "date"},
            {"name": "配送公司", "source": "compname", "kind": "text"},
            {"name": "供应商编码", "source": "vendcode", "kind": "text"},
            {"name": "供应商名称", "source": "vendname", "kind": "text"},
            {"name": "商品编码", "source": "goodscode", "kind": "text"},
            {"name": "商品名称", "source": "goodsname", "kind": "text"},
            {"name": "规格", "source": "goodsspec", "kind": "text"},
            {"name": "单位", "source": "goodsunit", "kind": "text"},
            {"name": "批准文号", "source": "authorize", "kind": "text"},
            {"name": "生产厂家", "source": "manufactory", "kind": "text"},
            {"name": "批号", "source": "lot", "kind": "text"},
            {"name": "有效期", "source": "validdate", "kind": "date"},
            {"name": "生产日期", "source": "procdate", "kind": "date"},
            {"name": "数量", "source": "qty", "kind": "text"},
            {"name": "单价", "source": "price", "kind": "text"},
            {"name": "类型", "source": "sheettype", "kind": "text"},
            {"name": "流水号", "source": "procid", "kind": "text"},
        ],
        "原始字段": [
            "authorize",
            "comp_goods",
            "compname",
            "goodscode",
            "goodsname",
            "goodsspec",
            "goodsunit",
            "lot",
            "manufactory",
            "price",
            "procdate",
            "procid",
            "qty",
            "rn",
            "stkdate",
            "validdate",
            "vendcode",
            "vendname",
        ],
        "日期模式": "snapshot",
    },

    # 定义配送流向查询配置。
    "配送流向": {
        "页面名称": "配送销售查询",
        "页面文件": "querySale.jsp",
        "请求文件名": "/OnLineDevelopProFiles/DataFlowQuery/cjcx/querySale",
        "请求接口": "/OnLineDevelopProFiles/DataFlowQuery/cjcx/com.wx.utils.publicMemer.JDBCComponent.dbPageQuery.biz.ext",
        "标准字段": [
            {"name": "日期", "source": "outdate", "kind": "date"},
            {"name": "配送公司", "source": "compname", "kind": "text"},
            {"name": "供应商编码", "source": "vendcode", "kind": "text"},
            {"name": "供应商名称", "source": "vendname", "kind": "text"},
            {"name": "客户编码", "source": "custcode", "kind": "text"},
            {"name": "客户名称", "source": "custname", "kind": "text"},
            {"name": "客户地址", "source": "custaddr", "kind": "text"},
            {"name": "客户所属上级名称", "source": "ouname", "kind": "text"},
            {"name": "配送单号", "source": "sheetno", "kind": "text"},
            {"name": "商品编码", "source": "goodscode", "kind": "text"},
            {"name": "商品名称", "source": "goodsname", "kind": "text"},
            {"name": "规格", "source": "goodsspec", "kind": "text"},
            {"name": "单位", "source": "goodsunit", "kind": "text"},
            {"name": "批准文号", "source": "authorize", "kind": "text"},
            {"name": "生产厂家", "source": "manufactory", "kind": "text"},
            {"name": "批号", "source": "lot", "kind": "text"},
            {"name": "有效期", "source": "validdate", "kind": "date"},
            {"name": "生产日期", "source": "procdate", "kind": "date"},
            {"name": "数量", "source": "qty", "kind": "text"},
            {"name": "金额", "source": "custamt", "kind": "text"},
            {"name": "单价", "source": "price", "kind": "text"},
            {"name": "类型", "source": "sheettype", "kind": "text"},
            {"name": "流水号", "source": "procid", "kind": "text"},
        ],
        "原始字段": [
            "authorize",
            "comp_goods",
            "compname",
            "custaddr",
            "custamt",
            "custcode",
            "custid",
            "custname",
            "goodscode",
            "goodsname",
            "goodsspec",
            "goodsunit",
            "lot",
            "manufactory",
            "ouid",
            "ouname",
            "outdate",
            "price",
            "procdate",
            "procid",
            "qty",
            "rn",
            "sheetno",
            "sheettype",
            "validdate",
            "vendcode",
            "vendname",
        ],
        "日期模式": "range",
    },
}


# 定义上海汇丰医药药材有限责任公司平台适配器。
class ShhfyyPlatform(BasePlatform):

    """
    上海汇丰医药药材有限责任公司数据服务云平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 上海汇丰医药药材有限责任公司平台适配器实例。
    :rtype: ShhfyyPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化上海汇丰医药药材有限责任公司数据服务云平台适配器。

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
        self.login_page_url = account.get("登录页", "https://flow.dyyy.com.cn/wxquery/coframe/auth/login/login.jsp")

        # 保存站点根地址。
        self.site_root_url = account.get("接口根地址", "https://flow.dyyy.com.cn/wxquery").rstrip("/")

        # 保存站点原点地址。
        self.origin_url = self.build_origin(self.site_root_url)

        # 保存首页地址。
        self.index_page_url = account.get("首页", f"{self.site_root_url}/coframe/auth/skin1/index.jsp")

        # 保存登录接口地址。
        self.login_api_url = account.get(
            "登录接口",
            f"{self.site_root_url}/coframe/auth/login/org.gocom.components.coframe.auth.LoginManager.login.biz.ext",
        )

        # 保存菜单接口地址。
        self.menu_api_url = account.get(
            "菜单接口",
            f"{self.site_root_url}/coframe/auth/login/org.gocom.components.coframe.auth.LoginManager.getMenuData.biz.ext",
        )

        # 保存会话写入接口地址。
        self.write_session_api_url = account.get(
            "写会话接口",
            f"{self.site_root_url}/com.wx.utils.publicMemer.SysRoute.writeSession.biz.ext",
        )

        # 保存查询接口地址。
        self.query_api_url = account.get(
            "查询接口",
            f"{self.site_root_url}/OnLineDevelopProFiles/DataFlowQuery/cjcx/com.wx.utils.publicMemer.JDBCComponent.dbPageQuery.biz.ext",
        )

        # 保存默认分页大小。
        self.page_size = int(account.get("分页大小", 500))

        # 初始化协议请求客户端。
        self.http = ProtocolHttpClient(self.origin_url)

        # 初始化登录状态。
        self.logged_in = False

        # 初始化登录结果。
        self.login_result = {}

        # 初始化已写入会话的页面集合。
        self.session_written_pages = set()

    # 定义平台登录方法。
    def login(self):

        """
        执行上海汇丰医药药材有限责任公司协议登录。

        :return: 登录结果。
        :rtype: dict
        """

        # 打印登录阶段标题。
        self.ph.section("上海汇丰医药药材有限责任公司登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 打印登录页访问日志。
        self.ph.info(self.ph.join(self.ph.kv("访问登录页", self.login_page_url, "cyan"), self.ph.kv("账号", self.get_login_name(), "cyan")))

        # 访问登录页以建立会话 Cookie。
        self.http.get(self.login_page_url, referer=self.login_page_url)

        # 构建登录请求体。
        payload = self.build_login_payload()

        # 提交登录请求。
        result = self.http.post_json(self.login_api_url, payload, self.login_page_url)

        # 解析登录响应。
        login_result = self.decode_login_result(result)

        # 判断登录是否成功。
        if not self.is_login_success(login_result):

            # 提取登录失败消息。
            error_message = self.extract_login_message(login_result)

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：{error_message}")

        # 保存登录结果。
        self.login_result = login_result

        # 标记登录状态。
        self.logged_in = True

        # 打印登录成功日志。
        self.ph.success(self.ph.join(self.ph.kv("正式登录成功", self.extract_login_message(login_result), "green"), self.ph.kv("Cookie数", len(list(self.http.cookie_jar)), "cyan")))

        # 访问首页以完成会话初始化。
        self.http.get(self.index_page_url, referer=self.login_page_url)

        # 返回登录结果。
        return login_result


    # 定义登录请求体构建方法。
    def build_login_payload(self):

        """
        构建登录请求体。

        :return: 登录请求体。
        :rtype: dict
        """

        # 返回登录请求体。
        return {
            "userId": self.get_login_name(),
            "password": self.get_login_password(),
        }

    # 定义登录响应解析方法。
    def decode_login_result(self, result):

        """
        解析登录响应。

        :param result: HTTP 响应结果。
        :type result: object
        :return: 登录响应数据。
        :rtype: dict
        """

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 返回 JSON 响应数据。
        return json.loads(response_text)

    # 定义登录结果判断方法。
    def is_login_success(self, login_result):

        """
        判断登录是否成功。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 是否登录成功。
        :rtype: bool
        """

        # 读取成功标识。
        ret_code = login_result.get("retCode")

        # 判断成功标识是否为 1。
        return str(ret_code) == "1"

    # 定义登录消息提取方法。
    def extract_login_message(self, login_result):

        """
        提取登录结果说明。

        :param login_result: 登录响应数据。
        :type login_result: dict
        :return: 登录结果说明。
        :rtype: str
        """

        # 返回默认登录说明。
        return str(login_result.get("msg") or login_result.get("message") or "登录成功")

    # 定义登录账号读取方法。
    def get_login_name(self):

        """
        读取登录账号。

        :return: 登录账号。
        :rtype: str
        """

        # 返回账号配置中的账号。
        return str(self.account.get("账号", "")).strip()

    # 定义登录密码读取方法。
    def get_login_password(self):

        """
        读取登录密码。

        :return: 登录密码。
        :rtype: str
        """

        # 返回账号配置中的密码。
        return str(self.account.get("密码", "")).strip()

    # 定义员工编号读取方法。
    def get_employee_id(self):

        """
        读取员工编号。

        :return: 员工编号。
        :rtype: str
        """

        # 优先读取显式员工编号。
        employee_id = self.account.get("员工编号")

        # 回退读取 EmpId。
        if employee_id in (None, ""):
            employee_id = self.account.get("EmpId")

        # 返回字符串化员工编号。
        return str(employee_id or "").strip()


    # 定义平台查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定类型流向数据。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果。
        :rtype: list[dict]
        """

        # 打印数据类型查询分隔线。
        self.print_query_section(data_type, start_date, end_date)

        # 返回协议查询结果。
        return self.fetch_protocol_rows(data_type, start_date, end_date)

    # 定义查询落地方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定类型数据并生成 Excel 文件。

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

        # 读取协议查询结果。
        rows = self.fetch_protocol_rows(data_type, start_date, end_date)

        # 构建输出目录。
        save_dir = output_dir or "downloads"

        # 创建输出目录。
        os.makedirs(save_dir, exist_ok=True)

        # 构建目标文件名。
        target_name = self.build_output_file_name(data_type, start_date, end_date)

        # 拼接目标文件路径。
        target_path = os.path.join(save_dir, target_name)

        # 写入 Excel 文件。
        self.write_rows_to_excel(data_type, rows, target_path)

        # 应用统一 Excel 样式。
        apply_standard_excel_style(target_path)

        # 打印 Excel 生成日志。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel 已生成", self.ph.path(target_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan")))

        # 返回 Excel 文件路径。
        return target_path


    # 定义协议查询方法。
    def fetch_protocol_rows(self, data_type, start_date, end_date):

        """
        使用数据服务云平台查询数据行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询结果行列表。
        :rtype: list[dict]
        """

        # 判断当前会话是否已登录。
        if not self.logged_in:

            # 执行平台登录。
            self.login()

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 读取会话初始化页面地址。
        page_url = self.build_page_url(query_definition["页面文件"])

        # 初始化页面会话。
        self.initialize_page_session(query_definition, page_url)

        # 初始化结果行列表。
        all_rows = []

        # 初始化分页页码。
        page_index = 0

        # 初始化总记录数。
        total_count = None

        # 按页循环请求数据。
        while True:

            # 构建分页请求体。
            payload = self.build_query_payload(query_definition, start_date, end_date, page_index=page_index, page_size=self.page_size)

            # 打印分页请求日志。
            self.ph.info(self.ph.join(self.ph.kv("提交协议查询", query_definition["页面名称"], "cyan"), self.ph.kv("页码", page_index, "yellow"), self.ph.kv("页大小", self.page_size, "yellow")))

            # 提交分页查询请求。
            result = self.http.post_json(self.build_api_url(query_definition["请求接口"]), payload, page_url)

            # 解析分页响应。
            response_data = self.decode_query_result(result, data_type)

            # 读取当前页结果行。
            page_rows = response_data.get("resultList", [])

            # 读取总记录数。
            if total_count is None:

                # 解析总记录数。
                total_count = self.to_int(response_data.get("totalCount"))

            # 遍历当前页结果行。
            for raw_row in page_rows:

                # 追加标准化数据行。
                all_rows.append(self.convert_raw_row(query_definition, raw_row))

            # 打印分页结果日志。
            self.ph.success(self.ph.join(self.ph.kv("分页返回完成", query_definition["页面名称"], "green"), self.ph.kv("当前页行数", len(page_rows), "cyan"), self.ph.kv("累计行数", len(all_rows), "cyan")))

            # 判断是否已经到达总记录数。
            if total_count is not None and len(all_rows) >= total_count:

                # 结束分页循环。
                break

            # 判断当前页是否不足一页。
            if len(page_rows) < self.page_size:

                # 结束分页循环。
                break

            # 递增下一页页码。
            page_index += 1

        # 打印协议查询完成日志。
        self.ph.success(self.ph.join(self.ph.kv("协议查询完成", data_type, "green"), self.ph.kv("记录数", len(all_rows), "cyan")))

        # 返回查询结果。
        return all_rows

    # 定义页面会话初始化方法。
    def initialize_page_session(self, query_definition, page_url):

        """
        初始化查询页面会话。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param page_url: 查询页面地址。
        :type page_url: str
        :return: None。
        :rtype: None
        """

        # 判断当前页面是否已经初始化过。
        if page_url in self.session_written_pages:

            # 结束会话初始化。
            return None

        # 访问查询页面以建立页面上下文。
        self.http.get(page_url, referer=self.index_page_url)

        # 构建会话写入请求体。
        payload = {
            "LOGINBROWSER": self.http.user_agent(),
            "ADDAPID": "wxapp",
        }

        # 提交会话写入请求。
        self.http.post_json(self.write_session_api_url, payload, page_url)

        # 记录页面已初始化。
        self.session_written_pages.add(page_url)

        # 打印页面初始化日志。
        self.ph.info(self.ph.join(self.ph.kv("页面会话已初始化", query_definition["页面名称"], "cyan"), self.ph.kv("页面", page_url, "yellow")))

        # 返回空结果。
        return None

    # 定义查询定义解析方法。
    def resolve_query_definition(self, data_type):

        """
        解析数据类型查询定义。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询定义。
        :rtype: dict
        """

        # 判断数据类型是否存在查询定义。
        if data_type not in SHHFYY_QUERY_DEFINITIONS:

            # 抛出不支持的数据类型异常。
            raise ValueError(f"上海汇丰医药药材有限责任公司平台不支持数据类型：{data_type}")

        # 返回查询定义。
        return SHHFYY_QUERY_DEFINITIONS[data_type]

    # 定义页面地址构建方法。
    def build_page_url(self, page_file_name):

        """
        构建查询页面地址。

        :param page_file_name: 页面文件名。
        :type page_file_name: str
        :return: 页面地址。
        :rtype: str
        """

        # 拼接页面地址。
        return f"{self.site_root_url}/OnLineDevelopProFiles/DataFlowQuery/cjcx/{page_file_name}"

    # 定义 API 地址构建方法。
    def build_api_url(self, route_path):

        """
        构建 API 请求地址。

        :param route_path: 路由路径。
        :type route_path: str
        :return: API 地址。
        :rtype: str
        """

        # 返回完整接口地址。
        return f"{self.site_root_url}/{route_path.lstrip('/')}"

    # 定义请求体构建方法。
    def build_query_payload(self, query_definition, start_date, end_date, page_index=0, page_size=None):

        """
        构建分页查询请求体。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param page_index: 页码索引。
        :type page_index: int
        :param page_size: 分页大小。
        :type page_size: int | None
        :return: 查询请求体。
        :rtype: dict
        """

        # 读取分页大小。
        active_page_size = int(page_size or self.page_size)

        # 构建基础请求体。
        payload = {
            "fileName": query_definition["请求文件名"],
            "LibId": "grid1",
            "dbName": "",
            "page": {
                "begin": page_index * active_page_size,
                "length": active_page_size,
            },
            "pageIndex": page_index,
            "pageSize": active_page_size,
            "pageStartIndex": page_index,
            "reqMap": self.build_request_map(query_definition, start_date, end_date),
            "sortField": "",
            "sortOrder": "",
        }

        # 返回查询请求体。
        return payload

    # 定义请求参数构建方法。
    def build_request_map(self, query_definition, start_date, end_date):

        """
        构建查询参数映射。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 查询参数映射。
        :rtype: dict
        """

        # 初始化请求参数。
        req_map = {
            "EmpId": self.get_employee_id(),
            "artiname": "",
            "distname": "",
        }

        # 判断当前查询是否为库存类型。
        if query_definition["日期模式"] == "snapshot":

            # 写入库存快照日期。
            req_map["stkdate"] = self.format_query_datetime(self.resolve_snapshot_date(start_date, end_date))

            # 返回库存查询参数。
            return req_map

        # 规范化开始日期。
        normalized_start_date = self.normalize_date_text(start_date)

        # 规范化结束日期。
        normalized_end_date = self.normalize_date_text(end_date)

        # 判断开始日期是否缺失。
        if not normalized_start_date:

            # 使用默认日期作为开始日期。
            normalized_start_date = self.get_default_flow_date()

        # 判断结束日期是否缺失。
        if not normalized_end_date:

            # 使用开始日期作为结束日期。
            normalized_end_date = normalized_start_date

        # 写入开始日期。
        req_map["startdate"] = self.format_query_datetime(normalized_start_date)

        # 写入结束日期。
        req_map["enddate"] = self.format_query_datetime(normalized_end_date)

        # 返回流向查询参数。
        return req_map

    # 定义库存日期解析方法。
    def resolve_snapshot_date(self, start_date, end_date):

        """
        解析库存快照日期。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 库存快照日期。
        :rtype: str
        """

        # 优先使用结束日期。
        if end_date:
            return self.normalize_date_text(end_date)

        # 次优先使用开始日期。
        if start_date:
            return self.normalize_date_text(start_date)

        # 返回默认库存日期。
        return self.get_default_stock_date()

    # 定义流向默认日期方法。
    def get_default_flow_date(self):

        """
        读取流向查询默认日期。

        :return: 默认日期。
        :rtype: str
        """

        # 读取昨天日期。
        yesterday = datetime.now() - timedelta(days=1)

        # 返回昨天日期文本。
        return yesterday.strftime("%Y-%m-%d")

    # 定义库存默认日期方法。
    def get_default_stock_date(self):

        """
        读取库存查询默认日期。

        :return: 默认日期。
        :rtype: str
        """

        # 读取昨天日期。
        yesterday = datetime.now() - timedelta(days=1)

        # 返回昨天日期文本。
        return yesterday.strftime("%Y-%m-%d")

    # 定义日期文本规范化方法。
    def normalize_date_text(self, date_text):

        """
        规范化日期文本。

        :param date_text: 原始日期文本。
        :type date_text: str | None
        :return: 规范化日期文本。
        :rtype: str
        """

        # 判断日期文本是否为空。
        if not date_text:

            # 返回空字符串。
            return ""

        # 清理两端空白。
        text = str(date_text).strip()

        # 遍历可能的日期格式。
        for date_format in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):

            # 尝试解析日期。
            try:

                # 解析日期对象。
                date_obj = datetime.strptime(text, date_format)

                # 返回标准日期文本。
                return date_obj.strftime("%Y-%m-%d")

            # 继续尝试下一个格式。
            except ValueError:

                # 进入下一轮格式判断。
                continue

        # 返回原始文本。
        return text

    # 定义请求日期时间格式化方法。
    def format_query_datetime(self, date_text):

        """
        格式化查询时间字段。

        :param date_text: 日期文本。
        :type date_text: str | None
        :return: 带零时分秒的日期文本。
        :rtype: str
        """

        # 规范化日期文本。
        normalized_date = self.normalize_date_text(date_text)

        # 判断日期文本是否为空。
        if not normalized_date:

            # 返回空字符串。
            return ""

        # 返回标准时间文本。
        return f"{normalized_date} 00:00:00"

    # 定义查询响应解析方法。
    def decode_query_result(self, result, data_type):

        """
        解析查询响应。

        :param result: HTTP 响应结果。
        :type result: object
        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 查询响应数据。
        :rtype: dict
        """

        # 解码响应文本。
        response_text = result.body.decode("utf-8", errors="replace")

        # 解析 JSON 响应。
        response_data = json.loads(response_text)

        # 判断是否存在异常对象。
        if isinstance(response_data, dict) and response_data.get("exception"):

            # 读取异常消息。
            exception_message = response_data["exception"].get("message") or response_data["exception"]

            # 抛出协议查询异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询失败：{exception_message}")

        # 判断结果是否成功。
        if isinstance(response_data, dict) and str(response_data.get("sts")) not in ("1", "True", "true"):

            # 读取失败消息。
            error_message = response_data.get("msg") or response_data.get("message") or response_data

            # 抛出协议查询异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询失败：{error_message}")

        # 返回查询响应。
        return response_data

    # 定义整数转换方法。
    def to_int(self, value):

        """
        将值转换为整数。

        :param value: 原始值。
        :type value: object
        :return: 整数值或 None。
        :rtype: int | None
        """

        # 判断值是否为空。
        if value in (None, ""):

            # 返回空值。
            return None

        # 尝试转换整数。
        try:

            # 返回转换后的整数。
            return int(value)

        # 处理转换失败。
        except Exception:

            # 返回空值。
            return None

    # 定义原始行转换方法。
    def convert_raw_row(self, query_definition, raw_row):

        """
        转换查询原始行为标准字段行。

        :param query_definition: 查询定义。
        :type query_definition: dict
        :param raw_row: 原始行数据。
        :type raw_row: dict
        :return: 标准字段行。
        :rtype: dict
        """

        # 初始化标准化结果行。
        normalized_row = {}

        # 遍历标准字段定义。
        for field_spec in query_definition["标准字段"]:

            # 读取标准字段名称。
            field_name = field_spec["name"]

            # 读取原始字段名称。
            source_name = field_spec["source"]

            # 读取字段类型。
            field_kind = field_spec.get("kind", "text")

            # 读取原始字段值。
            source_value = raw_row.get(source_name, "")

            # 判断是否需要日期规范化。
            if field_kind == "date":

                # 写入日期字段值。
                normalized_row[field_name] = self.normalize_date_value(source_value)

            else:

                # 写入普通字段值。
                normalized_row[field_name] = self.normalize_text_value(source_value)

        # 遍历原始字段，保持接口字段完整。
        for key_name, key_value in raw_row.items():

            # 判断当前字段是否已存在。
            if key_name in normalized_row:

                # 跳过重复字段。
                continue

            # 写入原始字段值。
            normalized_row[key_name] = self.normalize_text_value(key_value)

        # 返回标准化结果行。
        return normalized_row

    # 定义文本值规范化方法。
    def normalize_text_value(self, value):

        """
        规范化普通文本值。

        :param value: 原始值。
        :type value: object
        :return: 规范化后的值。
        :rtype: object
        """

        # 判断值是否为空。
        if value is None:

            # 返回空字符串。
            return ""

        # 返回字符串化或原始数值。
        return value

    # 定义日期值规范化方法。
    def normalize_date_value(self, value):

        """
        规范化日期值。

        :param value: 原始值。
        :type value: object
        :return: 规范化后的日期值。
        :rtype: str
        """

        # 判断值是否为空。
        if value in (None, ""):

            # 返回空字符串。
            return ""

        # 转换为字符串。
        text = str(value).strip()

        # 遍历可识别日期格式。
        for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):

            # 尝试解析日期。
            try:

                # 返回标准日期文本。
                return datetime.strptime(text, date_format).strftime("%Y-%m-%d")

            # 继续尝试其它格式。
            except ValueError:

                # 进入下一轮判断。
                continue

        # 返回原始文本。
        return text

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, data_type, rows, target_path):

        """
        将查询结果写入 Excel 文件。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 查询结果行列表。
        :type rows: list[dict]
        :param target_path: 目标文件路径。
        :type target_path: str
        :return: None。
        :rtype: None
        """

        # 导入工作簿对象。
        from openpyxl import Workbook

        # 读取查询定义。
        query_definition = self.resolve_query_definition(data_type)

        # 初始化表头集合。
        headers = [field_spec["name"] for field_spec in query_definition["标准字段"]]

        # 遍历接口原始字段。
        for raw_field_name in query_definition["原始字段"]:

            # 判断字段是否已存在。
            if raw_field_name not in headers:

                # 追加原始字段。
                headers.append(raw_field_name)

        # 遍历结果行补充新字段。
        for row_data in rows:

            # 遍历当前行字段。
            for column_name in row_data.keys():

                # 判断字段是否已存在。
                if column_name not in headers:

                    # 追加新增字段。
                    headers.append(column_name)

        # 创建工作簿。
        workbook = Workbook()

        # 读取默认工作表。
        worksheet = workbook.active

        # 设置工作表名称。
        worksheet.title = data_type

        # 写入表头行。
        worksheet.append(headers)

        # 遍历查询结果行。
        for row_data in rows:

            # 写入当前结果行。
            worksheet.append([row_data.get(column_name, "") for column_name in headers])

        # 删除旧文件。
        if os.path.exists(target_path):

            # 移除旧文件。
            os.remove(target_path)

        # 保存工作簿。
        workbook.save(target_path)

        # 关闭工作簿。
        workbook.close()

        # 返回空值。
        return None

    # 定义输出日期解析方法。
    def resolve_output_query_date(self, data_type, start_date=None, end_date=None):

        """
        解析输出文件名使用的日期。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 输出文件名使用的日期。
        :rtype: str | None
        """

        # 判断当前数据类型是否为库存。
        if "库存" in data_type:

            # 返回导出当天日期。
            return datetime.now().strftime("%Y-%m-%d")

        # 返回流向类使用的开始日期。
        return self.normalize_date_text(start_date) or self.normalize_date_text(end_date)

