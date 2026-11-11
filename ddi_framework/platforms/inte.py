# -*- coding: utf-8 -*-
"""
英特集团流向查询平台协议适配器。

本模块负责英特集团流向查询平台（若依 RuoYi 框架）的算术验证码登录、
流向明细与库存查询、原始字段 Excel 落地。
"""

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入随机数模块。
import random

# 导入 JSON 编解码模块。
import json

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入协议请求客户端。
from ddi_framework import ProtocolHttpClient

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入正式原始 Excel 写入函数。
from ddi_framework.raw_fields import write_formal_raw_excel


# 定义数据类型与协议端点及筛选能力映射。
DATA_TYPE_CONFIG = {
    "配送流向": {"端点": "/system/itMedicinegotoInoutroom/list", "时间类型": "0", "开始字段": "params[keepStartTime]", "结束字段": "params[keepEndTime]", "日期列": "keepdate"},
    "库存": {"端点": "/system/itMedicinegotoStorege/list", "时间类型": "", "开始字段": "", "结束字段": "", "日期列": ""},
}

# 定义登录单次会话最大验证码拉取次数。
MAX_CAPTCHA_ROUNDS = 20

# 定义登录连续错误答案上限（防账号锁定）。
MAX_WRONG_ANSWERS = 3


# 定义英特集团流向查询平台适配器。
class IntePlatform(BasePlatform):

    """
    英特集团流向查询平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 英特集团流向查询平台适配器实例。
    :rtype: IntePlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化站点地址、协议客户端与验证码识别引擎。

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

        # 读取平台 HTTP 服务根地址。
        self.base_url = str(account.get("接口根地址", "")).rstrip("/")

        # 读取查询请求超时时间。
        self.query_timeout_seconds = int(account.get("查询超时秒", 300))

        # 初始化带 Cookie 管理的协议客户端。
        self.http = ProtocolHttpClient(self.base_url)

        # 初始化登录状态标识。
        self.logged_in = False

        # 延迟初始化验证码识别引擎。
        self.captcha_engine = None

    # 定义平台登录方法。
    def login(self):

        """
        完成算术验证码识别与登录表单提交建立会话。

        :return: 不含凭据的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("英特流向平台登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 访问登录页初始化 JSP 会话 Cookie。
        self.http.get(self.build_url("/login"), referer=self.base_url + "/")

        # 初始化验证码识别引擎。
        self.captcha_engine = self.build_captcha_engine()

        # 初始化连续错误答案计数。
        wrong_answers = 0

        # 循环拉取验证码识别并提交登录。
        for round_index in range(1, MAX_CAPTCHA_ROUNDS + 1):

            # 拉取会话绑定的算术验证码图片。
            image_body = self.fetch_captcha_image()

            # 识别算式文本。
            text = self.read_captcha_text(image_body)

            # 解析算式并计算答案。
            answer = self.parse_math_expression(text)

            # 判断解析失败直接换图重试。
            if answer is None:

                # 打印换图重试日志。
                self.ph.info(self.ph.kv(f"验证码第 {round_index} 次不解析", f"识别文本 {text[:16]!r}", "yellow"))

                # 进入下一次拉取。
                continue

            # 提交登录表单。
            response_data = self.submit_login(answer)

            # 判断登录成功。
            if response_data.get("code") == 0:

                # 标记当前协议会话已登录。
                self.logged_in = True

                # 打印不含敏感值的登录成功日志。
                self.ph.success(self.ph.join(self.ph.kv("登录状态", "成功", "green"), self.ph.kv("验证码轮次", round_index, "cyan"), self.ph.kv("错误答案", wrong_answers, "cyan")))

                # 返回不含敏感字段的登录结果。
                return {"登录状态": "成功", "验证码轮次": round_index}

            # 累加连续错误答案计数。
            wrong_answers += 1

            # 打印验证码错误日志。
            self.ph.warning(self.ph.kv(f"验证码第 {round_index} 次识别错误", f"提交答案 {answer}", "yellow"))

            # 判断达到错误答案上限。
            if wrong_answers >= MAX_WRONG_ANSWERS:

                # 抛出防锁定的登录失败异常。
                raise RuntimeError(f"{self.company_name} 登录失败：验证码连续错误 {wrong_answers} 次，为防账号锁定已停止尝试")

        # 抛出验证码轮次耗尽异常。
        raise RuntimeError(f"{self.company_name} 登录失败：验证码 {MAX_CAPTCHA_ROUNDS} 轮内未能成功登录")

    # 定义验证码识别引擎构建方法。
    def build_captcha_engine(self):

        """
        构建算术验证码识别引擎。

        :return: 识别引擎实例。
        :rtype: object
        """

        # 导入 RapidOCR 识别引擎。
        from rapidocr_onnxruntime import RapidOCR

        # 返回识别引擎实例。
        return RapidOCR()

    # 定义验证码图片拉取方法。
    def fetch_captcha_image(self):

        """
        拉取会话绑定的算术验证码图片。

        :return: 验证码图片字节。
        :rtype: bytes
        """

        # 拼接验证码接口地址（随机数防缓存）。
        captcha_url = self.build_url(f"/captcha/captchaImage?type=math&s={random.random()}")

        # 发起验证码图片请求。
        result = self.http.request("GET", captcha_url, headers={"Referer": self.build_url("/login")}, timeout=30)

        # 返回图片字节。
        return result.body

    # 定义验证码文本识别方法。
    def read_captcha_text(self, image_body):

        """
        识别验证码图片中的算式文本。

        :param image_body: 验证码图片字节。
        :type image_body: bytes
        :return: 识别文本。
        :rtype: str
        """

        # 执行识别并拼接全部文本片段。
        result, _ = self.captcha_engine(image_body)

        # 返回拼接文本。
        return "".join(item[1] for item in result) if result else ""

    # 定义算式解析方法。
    def parse_math_expression(self, text):

        """
        从识别文本解析算式并计算答案。

        :param text: 识别文本。
        :type text: str
        :return: 算式答案，解析失败返回 None。
        :rtype: int | None
        """

        # 锚定开头匹配首个单目算式（识别文本以算式起始，中段杂讯直接判不解析）。
        match = re.match(r"\s*(\d+)\s*([+\-*xX×~≈])\s*(\d+)", str(text))

        # 判断解析失败。
        if not match:

            # 返回解析失败。
            return None

        # 读取左操作数。
        left_value = int(match.group(1))

        # 读取归一化算符。
        operator = match.group(2)

        # 读取右操作数。
        right_value = int(match.group(3))

        # 按归一化算符计算答案。
        if operator == "+" or operator == "≈":

            # 加法。
            return left_value + right_value

        # 判断减法或波浪号误读。
        if operator == "-" or operator == "~":

            # 减法（允许负数答案）。
            return left_value - right_value

        # 其余按乘法计算。
        return left_value * right_value

    # 定义登录表单提交方法。
    def submit_login(self, answer):

        """
        提交登录表单并返回响应对象。

        :param answer: 验证码答案。
        :type answer: int
        :return: 登录响应 JSON 对象。
        :rtype: dict
        """

        # 构建浏览器同款登录请求头。
        headers = {"Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest", "Origin": self.base_url, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": self.build_url("/login")}

        # 构建登录表单文本。
        payload = f"username={self.account.get('账号', '')}&password={self.account.get('密码', '')}&validateCode={answer}&rememberMe=false"

        # 提交登录表单。
        result = self.http.request("POST", self.build_url("/login"), headers=headers, data=payload.encode("utf-8"), timeout=30, allow_http_error=True)

        # 解析响应 JSON。
        return json.loads(result.body.decode("utf-8", "replace"))

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

        # 请求当前类型的全量记录。
        rows = self.fetch_all_rows(data_type, start_date, end_date)

        # 校验流向记录的业务日期处于请求范围。
        self.validate_result_date_range(data_type, rows, start_date, end_date)

        # 返回原始记录列表。
        return rows

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成原始字段 Excel。

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

        # 请求当前类型的全量记录。
        rows = self.fetch_all_rows(data_type, start_date, end_date)

        # 校验流向记录的业务日期处于请求范围。
        self.validate_result_date_range(data_type, rows, start_date, end_date)

        # 解析当前查询的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(data_type, start_date, end_date)

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, resolved_start_date, resolved_end_date)

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 装配字段定义（按首行键序保留服务端全部原始字段）。
        headers = self.resolve_headers(rows)

        # 写入原始字段 Excel。
        self.write_rows_to_excel(rows, headers, output_path, data_type)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义全量记录请求方法。
    def fetch_all_rows(self, data_type, start_date, end_date):

        """
        请求协议端点并返回服务端全量记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 读取当前类型的协议配置。
        config = self.resolve_config(data_type)

        # 确保当前 HTTP 会话已经登录。
        self.ensure_login()

        # 打印数据类型查询分隔线。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(data_type, start_date, end_date)

        # 打印查询阶段分隔线。
        self.ph.section(f"{data_type}查询", self.ph.join(self.ph.kv("开始日期", resolved_start_date, "cyan"), self.ph.kv("结束日期", resolved_end_date, "cyan")))

        # 构建查询表单字段集合。
        fields = [f"pageNumber=1", f"pageSize=500"]

        # 判断当前端点需要时间类型与日期区间。
        if config["时间类型"]:

            # 写入时间类型选项。
            fields.append(f"timeType={config['时间类型']}")

            # 写入开始日期字段。
            fields.append(f"{config['开始字段']}={resolved_start_date}")

            # 写入结束日期字段。
            fields.append(f"{config['结束字段']}={resolved_end_date}")

        # 构建查询请求头。
        headers = {"Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest", "Origin": self.base_url, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": self.build_url(self.resolve_page_path(data_type))}

        # 提交查询请求（服务端忽略分页参数单次返回全量）。
        result = self.http.request("POST", self.build_url(config["端点"]), headers=headers, data="&".join(fields).encode("utf-8"), timeout=self.query_timeout_seconds, allow_http_error=True)

        # 解析响应 JSON。
        response_data = json.loads(result.body.decode("utf-8", "replace"))

        # 读取记录集合。
        rows = response_data.get("rows", [])

        # 校验记录集合为数组。
        if not isinstance(rows, list):

            # 抛出响应结构异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询响应 rows 字段不是数组")

        # 打印协议查询完成摘要。
        self.ph.success(self.ph.join(self.ph.kv("查询端点", config["端点"], "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("服务端总数", response_data.get("total", "-"), "cyan")))

        # 返回原始记录列表。
        return rows

    # 定义协议配置解析方法。
    def resolve_config(self, data_type):

        """
        读取数据类型的协议配置。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 协议配置字典。
        :rtype: dict
        """

        # 判断数据类型已配置协议端点。
        if data_type in DATA_TYPE_CONFIG:

            # 返回协议配置字典。
            return DATA_TYPE_CONFIG[data_type]

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}（该平台仅提供单一流向数据集与库存）")

    # 定义页面路径解析方法。
    def resolve_page_path(self, data_type):

        """
        读取当前数据类型对应的查询页面路径（作 Referer）。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 页面路径。
        :rtype: str
        """

        # 判断当前类型为流向查询。
        if data_type == "配送流向":

            # 返回流向查询页面路径。
            return "/system/itMedicinegotoInoutroom"

        # 其余返回库存查询页面路径。
        return "/system/itMedicinegotoStorege"

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型存在于平台协议映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 调用协议配置解析完成校验。
        self.resolve_config(data_type)

    # 定义查询日期解析方法。
    def resolve_query_dates(self, data_type, start_date, end_date):

        """
        解析流向或库存查询使用的日期范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 解析后的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 读取当天日期文本。
        today_text = self.resolve_today_text()

        # 判断当前类型为库存快照。
        if data_type == "库存":

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

    # 定义当天日期解析方法。
    def resolve_today_text(self):

        """
        生成当前导出日期文本。

        :return: 当天日期文本。
        :rtype: str
        """

        # 导入日期时间模块。
        from datetime import datetime

        # 返回当天日期文本。
        return datetime.now().strftime("%Y-%m-%d")

    # 定义结果日期范围校验方法。
    def validate_result_date_range(self, data_type, rows, start_date, end_date):

        """
        校验流向记录日期未超出提交的查询范围。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: None。
        :rtype: None
        """

        # 判断当前查询未提供日期范围。
        if not start_date or not end_date:

            # 结束无日期范围的校验。
            return

        # 读取当前类型的业务日期列。
        date_column = self.resolve_config(data_type)["日期列"]

        # 判断当前类型无日期列（库存快照）。
        if not date_column:

            # 结束库存日期范围校验。
            return

        # 导入日期解析函数。
        from datetime import datetime

        # 解析请求开始日期对象。
        start_value = datetime.strptime(str(start_date), "%Y-%m-%d").date()

        # 解析请求结束日期对象。
        end_value = datetime.strptime(str(end_date), "%Y-%m-%d").date()

        # 遍历返回的原始记录。
        for row in rows:

            # 读取当前记录的业务日期文本。
            date_text = str(row.get(date_column, "")).strip()

            # 跳过空日期字段记录。
            if not date_text:

                # 继续校验下一条记录。
                continue

            # 解析日期文本前十位。
            record_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()

            # 判断记录日期是否处于请求范围。
            if start_value <= record_date <= end_value:

                # 继续校验下一条记录。
                continue

            # 抛出业务日期越界异常。
            raise RuntimeError(f"{self.company_name} {data_type} 返回日期超出查询范围：{date_text}")

    # 定义字段元数据解析方法。
    def resolve_headers(self, rows):

        """
        按首行键序解析全部原始字段定义。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :return: 字段标题列表。
        :rtype: list[str]
        """

        # 判断无记录时返回空字段。
        if not rows:

            # 返回空字段列表。
            return []

        # 按行序合并动态字段。
        merged = []

        # 遍历记录。
        for row in rows:

            # 遍历字段名。
            for key in row.keys():

                # 判断字段未收录。
                if key not in merged:

                    # 追加字段名。
                    merged.append(key)

        # 返回字段列表。
        return merged

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        按字段标题与顺序写入原始字段 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 字段标题列表。
        :type headers: list[str]
        :param output_path: Excel 输出文件路径。
        :type output_path: str
        :param sheet_name: 工作表名称。
        :type sheet_name: str
        :return: None。
        :rtype: None
        """

        # 装配字段定义列表。
        field_headers = [{"key": title, "title": title} for title in headers]

        # 展平嵌套结构（dict/list 序列化为 JSON 文本，保证单元格可写）。
        flat_rows = [{key: (json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value) for key, value in row.items()} for row in rows]

        # 写入原始字段。
        write_formal_raw_excel(output_path, field_headers, flat_rows, sheet_name=sheet_name)

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)

    # 定义完整 URL 构建方法。
    def build_url(self, path):

        """
        将相对路径转换为平台完整 URL。

        :param path: 相对路径。
        :type path: str
        :return: 完整接口地址。
        :rtype: str
        """

        # 拼接根地址与路径。
        return f"{self.base_url}{path}"
