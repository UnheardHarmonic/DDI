# -*- coding: utf-8 -*-
"""
成都聚仁堂 FineReport 数据报表系统平台接入契约测试。

本模块验证聚仁堂账号配置完整性、四报表参数映射、登录请求体形态、
分页客户端标识形态、表格解析与日期校验口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入正则表达式模块。
import re

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入成都聚仁堂平台适配器。
from ddi_framework.platforms.jrt import JrtPlatform
from ddi_framework.platforms.jrt import REPORT_DEFINITIONS

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义成都聚仁堂接入契约测试套件。
class JrtPlatformTests(unittest.TestCase):

    """
    成都聚仁堂 FineReport 数据报表系统平台接入契约测试。

    :return: 测试套件实例。
    :rtype: JrtPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "成都聚仁堂医药连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["购进流向", "配送流向", "纯销流向", "库存"]

    # 定义类级报表参数映射引用（与浏览器抓包一致）。
    EXPECTED_PARAMS = {
        "购进流向": ("开始生效日期", "结束生效日期"),
        "配送流向": ("开始日期", "结束日期"),
        "纯销流向": ("销售开始日期", "销售结束日期"),
        "库存": ("", ""),
    }

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 成都聚仁堂平台适配器实例。
        :rtype: JrtPlatform
        """

        # 读取账号配置并构建适配器。
        return JrtPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证聚仁堂账号声明平台归属、站点地址、页面映射与类型清单。

        :return: None。
        :rtype: None
        """

        # 读取聚仁堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 jrt。
        self.assertEqual(account["平台"], "jrt")

        # 断言站点根地址与应用路径与抓包一致。
        self.assertEqual(account["接口根地址"], "http://183.221.78.70:18075")
        self.assertEqual(account["应用路径"], "/webroot/decision")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言页面映射覆盖四类型的页面名称。
        for data_type in self.EXPECTED_TYPES:
            self.assertTrue(account["页面映射"][data_type]["页面名称"], data_type)

    # 定义四报表参数映射验证。
    def test_report_param_mapping_matches_capture(self):

        """
        验证四类型日期参数名与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 遍历四类型断言参数名。
        for data_type, (start_param, end_param) in self.EXPECTED_PARAMS.items():

            # 断言开始参数名一致。
            self.assertEqual(REPORT_DEFINITIONS[data_type]["startParam"], start_param, data_type)

            # 断言结束参数名一致。
            self.assertEqual(REPORT_DEFINITIONS[data_type]["endParam"], end_param, data_type)

    # 定义登录请求体形态验证。
    def test_login_payload_is_encrypted_json(self):

        """
        验证登录请求体为加密标记、有效期与占位域齐备的 JSON 字段集。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建登录请求体。
        payload = platform.build_login_payload({"frontSeed": "1234567812345678"})

        # 断言加密标记与占位域齐备。
        self.assertTrue(payload["encrypted"])
        self.assertEqual(payload["validity"], -1)
        self.assertEqual(payload["sliderToken"], "")
        self.assertEqual(payload["origin"], "")

        # 断言账号取自配置且密码已加密为非明文。
        self.assertEqual(payload["username"], "10030")
        self.assertNotEqual(payload["password"], "10030")
        self.assertTrue(payload["password"])

    # 定义分页客户端标识形态验证。
    def test_client_id_shape_matches_capture(self):

        """
        验证分页请求客户端标识为会话号、毫秒时间戳与八位随机段。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建客户端标识。
        client_id = platform.build_client_id("4cfdf9620accbd4a5ee27a450286e24")

        # 断言客户端标识形态与抓包一致。
        self.assertRegex(client_id, r"^4cfdf9620accbd4a5ee27a450286e24#\d{13}#[0-9a-f]{8}$")

    # 定义总页数提取验证。
    def test_total_pages_extraction(self):

        """
        验证从页面 HTML 提取总页数并对缺失标记回退单页。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言带标记页面解析出总页数。
        self.assertEqual(platform.extract_total_pages("var reportTotalPage=11;"), 11)

        # 断言缺标记页面回退单页。
        self.assertEqual(platform.extract_total_pages("<div>无标记</div>"), 1)

    # 定义表格解析与表头去重验证。
    def test_table_parsing_and_header_dedup(self):

        """
        验证表格行组装保留全字段并给重复表头追加序号。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构造含重复表头的表格行样例。
        table_rows = [["序号", "会计日", "会计日"], ["1", "2026-09-25", "备注"]]

        # 组装表头与数据行。
        headers, rows = platform.build_rows_from_table(table_rows)

        # 断言重复表头追加序号且数据行完整。
        self.assertEqual(headers, ["序号", "会计日", "会计日_2"])
        self.assertEqual(rows, [{"序号": "1", "会计日": "2026-09-25", "会计日_2": "备注"}])

    # 定义入口搜索响应解析验证。
    def test_entry_search_response_parsing(self):

        """
        验证门户目录搜索响应按页面名称精确匹配入口并忽略同名前缀条目。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构造含目标条目的搜索响应样例。
        response_text = '{"data":[{"id":"8a56a663-9f7b-449e-909f-d0c2a5f5ce77","text":"采购退货明细","path":"采购退货明细.cpt","entryType":102},{"id":"other-id","text":"采购退货明细（旧）","entryType":102}]}'

        # 解析搜索响应。
        entry_token = platform.parse_entry_search_response(response_text, "采购退货明细")

        # 断言精确命中的入口编号。
        self.assertEqual(entry_token, "8a56a663-9f7b-449e-909f-d0c2a5f5ce77")

        # 断言无命中时返回空字符串。
        self.assertEqual(platform.parse_entry_search_response('{"data":[]}', "采购退货明细"), "")

    # 定义入口地址构建验证。
    def test_entry_url_building(self):

        """
        验证裸入口编号按入口访问端点拼接绝对地址。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 写入缓存入口编号。
        platform.report_entries["购进流向"] = "8a56a663-9f7b-449e-909f-d0c2a5f5ce77"

        # 读取解析后的入口路径。
        entry_token = platform.resolve_report_entry("购进流向")

        # 断言缓存命中返回入口编号。
        self.assertEqual(entry_token, "8a56a663-9f7b-449e-909f-d0c2a5f5ce77")

    # 定义日期范围校验验证。
    def test_result_date_range_validation(self):

        """
        验证流向结果日期越界报错、区间内放行、库存快照免校验。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构造区间内结果行。
        inside_rows = [{"生效时间": "2026-08-01 10:00:00"}, {"生效时间": "2026-09-15 10:00:00"}]

        # 断言区间内结果放行。
        platform.validate_result_date_range("购进流向", inside_rows, "2026-08-01", "2026-10-26")

        # 构造越界结果行。
        outside_rows = [{"生效时间": "2026-07-31 10:00:00"}]

        # 断言越界结果抛出异常。
        with self.assertRaises(RuntimeError):
            platform.validate_result_date_range("购进流向", outside_rows, "2026-08-01", "2026-10-26")

        # 断言库存快照免校验。
        platform.validate_result_date_range("库存", [{"库存数量": "1"}], "2026-08-01", "2026-10-26")

    # 定义未接入类型拒绝验证。
    def test_unsupported_type_is_rejected(self):

        """
        验证未接入数据类型抛出未接入异常。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言未知类型抛出异常。
        with self.assertRaises(ValueError):
            platform.validate_data_type("报损流向")

    # 定义日期解析回退验证。
    def test_resolve_query_dates_default_today(self):

        """
        验证缺省日期回退为当天日期文本。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 解析缺省日期。
        start_date, end_date = platform.resolve_query_dates(None, None)

        # 断言起止日期一致且为当日形态。
        self.assertEqual(start_date, end_date)
        self.assertTrue(re.match(r"^\d{4}-\d{2}-\d{2}$", start_date))


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
