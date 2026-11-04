# -*- coding: utf-8 -*-
"""
天济大药房连锁有限公司协同平台接入契约测试。

本模块验证天济账号配置完整性、四类型报表编号映射、报表表格解析口径
（原始表头保序与汇总行剔除）、检索日期口径与未接入类型拒绝，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入天济协同平台适配器。
from ddi_framework.platforms.tianji import INVENTORY_SHEET_NAMES
from ddi_framework.platforms.tianji import REPORT_DATA_TYPE_IDS
from ddi_framework.platforms.tianji import TianjiPlatform
from ddi_framework.platforms.tianji import TianjiReportTableParser
from ddi_framework.platforms.tianji import strip_total_rows

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义报表数据响应样例（结构对齐真实响应，末行携带汇总行）。
REPORT_TABLE_HTML = """
<div id="div_reportview_table_2c5f37a39ce548518c5f1f62b6e7623a">
<table id="reportview_table_2c5f37" data-pagination="false">
<thead><tr>
<th data-field="DATES" data-title="日期">日期</th>
<th data-field="ORGNAME" data-title="门店名称">门店名称</th>
<th data-field="GOODSCODE" data-title="商品编号">商品编号</th>
<th data-field="NUM" data-title="配送数量">配送数量</th>
</tr></thead>
<tbody>
<tr><td>2026-10-09</td><td>天济大药房1068分店</td><td>10011238</td><td>2</td></tr>
<tr><td>2026-10-30</td><td>天济大药房1003分店</td><td>10011238</td><td>5</td></tr>
<tr><td>合计</td><td></td><td></td><td>7</td></tr>
</tbody>
</table>
</div>
"""


# 定义天济协同平台接入契约测试套件。
class TianjiPlatformTests(unittest.TestCase):

    """
    天济大药房连锁有限公司协同平台接入契约测试。

    :return: 测试套件实例。
    :rtype: TianjiPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "天济大药房连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "库存"]

    # 定义类级报表编号映射引用（与浏览器抓包一致）。
    EXPECTED_REPORT_IDS = {
        "配送流向": ["0O0LO3T0QP5"],
        "购进流向": ["0O0LOGUHNU9"],
        "纯销流向": ["0O0LOTGZ6TX"],
        "库存": ["0THNNBTDD11", "0O0LP22MLRT"],
    }

    # 定义类级库存工作表名称映射引用。
    EXPECTED_SHEET_NAMES = {"0THNNBTDD11": "门店库存", "0O0LP22MLRT": "实时库存"}

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 天济协同平台适配器实例。
        :rtype: TianjiPlatform
        """

        # 构建平台适配器实例（离线不触发登录）。
        return TianjiPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证天济账号声明平台归属、站点地址与工作区编号。

        :return: None。
        :rtype: None
        """

        # 读取天济账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 tianji。
        self.assertEqual(account["平台"], "tianji")

        # 断言站点地址与抓包一致。
        self.assertEqual(account["接口根地址"], "http://gys.tianjiyy.com:9090")
        self.assertEqual(account["登录页"], "http://gys.tianjiyy.com:9090/Account/Login")

        # 断言工作区编号为襄阳天济。
        self.assertEqual(account["工作区编号"], "0O0LNH1Y131")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言配送流向页面映射与董事长给定一致。
        self.assertEqual(account["页面映射"]["配送流向"], {"页面名称": "配送-天济", "报表编号": "0O0LO3T0QP5"})

        # 断言库存页面映射合并双报表。
        self.assertEqual(account["页面映射"]["库存"]["报表编号"], ["0THNNBTDD11", "0O0LP22MLRT"])

    # 定义报表编号映射验证。
    def test_report_ids_match_capture(self):

        """
        验证四类型报表编号映射与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言报表编号映射与约定一致。
        self.assertEqual(REPORT_DATA_TYPE_IDS, self.EXPECTED_REPORT_IDS)

        # 断言库存工作表名称映射与约定一致。
        self.assertEqual(INVENTORY_SHEET_NAMES, self.EXPECTED_SHEET_NAMES)

    # 定义报表表格解析验证。
    def test_report_table_parser_keeps_raw_headers(self):

        """
        验证表格解析保留原始表头顺序并剔除汇总行。

        :return: None。
        :rtype: None
        """

        # 解析报表数据响应样例。
        parser = TianjiReportTableParser()

        # 喂入样例文本。
        parser.feed(REPORT_TABLE_HTML)

        # 断言表头标题与列顺序保持原始形态。
        self.assertEqual([header["title"] for header in parser.headers], ["日期", "门店名称", "商品编号", "配送数量"])

        # 断言表头字段名与接口一致。
        self.assertEqual([header["field"] for header in parser.headers], ["DATES", "ORGNAME", "GOODSCODE", "NUM"])

        # 断言解析器如实保留全部行（含汇总行）。
        self.assertEqual(len(parser.rows), 3)

        # 断言汇总行剔除后仅剩数据行且保序。
        self.assertEqual(strip_total_rows(parser.rows), [["2026-10-09", "天济大药房1068分店", "10011238", "2"], ["2026-10-30", "天济大药房1003分店", "10011238", "5"]])

    # 定义行字典转换验证。
    def test_build_row_dicts_adds_inventory_source(self):

        """
        验证库存双报表行字典附加报表名称键。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 解析报表数据响应样例。
        parser = TianjiReportTableParser()

        # 喂入样例文本。
        parser.feed(REPORT_TABLE_HTML)

        # 构建剔除汇总行后的表格结构。
        table = {"headers": parser.headers, "rows": strip_total_rows(parser.rows)}

        # 转换门店库存行字典。
        row_dicts = platform.build_row_dicts(table, "0THNNBTDD11")

        # 断言数据行全部携带报表名称键。
        self.assertTrue(all(row["报表名称"] == "门店库存" for row in row_dicts))

        # 断言字段取值按原始列对位。
        self.assertEqual(row_dicts[0]["DATES"], "2026-10-09")

    # 定义流向日期解析验证。
    def test_flow_dates_are_required_and_passed_through(self):

        """
        验证流向类日期必填且按原样透传（平台数据两端含）。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言缺失日期抛出异常。
        with self.assertRaises(ValueError):

            # 缺失起止日期触发异常。
            platform.resolve_query_dates("配送流向", None, None)

        # 断言起止日期按原样透传。
        self.assertEqual(platform.resolve_query_dates("配送流向", "2026-10-01", "2026-10-31"), ("2026-10-01", "2026-10-31"))

    # 定义库存快照日期解析验证。
    def test_inventory_dates_use_defaults(self):

        """
        验证库存类缺省日期回退平台默认口径。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 解析库存类缺省日期。
        resolved_start, resolved_end = platform.resolve_query_dates("库存", None, None)

        # 断言缺省开始日期为当月一号形态。
        self.assertRegex(resolved_start, r"^\d{4}-\d{2}-01$")

        # 断言缺省结束日期为当天形态。
        self.assertRegex(resolved_end, r"^\d{4}-\d{2}-\d{2}$")

    # 定义业务日期越界拒绝验证。
    def test_flow_date_out_of_range_is_rejected(self):

        """
        验证流向业务日期越出请求区间时抛出异常。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建包含越界日期的表格结构。
        table = {"headers": [{"title": "日期", "field": "DATES"}], "rows": [["2026-11-15"], ["2026-10-05"]]}

        # 断言越界数据触发异常。
        with self.assertRaises(RuntimeError):

            # 执行日期范围校验。
            platform.validate_report_dates("配送流向", table, "2026-10-01", "2026-10-31")

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

            # 未知类型触发异常。
            platform.validate_data_type("报损流向")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
