# -*- coding: utf-8 -*-
"""
佛山市百姓堂药业连锁有限公司米伦厂商合作平台接入契约测试。

本模块验证百姓堂账号配置完整性、登录体形态、过滤串构造与
空清单业务码口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入米伦厂商合作平台适配器。
from ddi_framework.platforms.milun import MilunPlatform
from ddi_framework.platforms.milun import BILL_TYPE_FILTERS

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义百姓堂米伦平台接入契约测试套件。
class MilunPlatformTests(unittest.TestCase):

    """
    佛山市百姓堂药业连锁有限公司米伦厂商合作平台接入契约测试。

    :return: 测试套件实例。
    :rtype: MilunPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "佛山市百姓堂药业连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["购进流向", "纯销流向"]

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 米伦平台适配器实例。
        :rtype: MilunPlatform
        """

        # 读取账号配置并构建适配器。
        return MilunPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证百姓堂账号声明平台归属、站点地址与类型清单。

        :return: None。
        :rtype: None
        """

        # 读取百姓堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 milun。
        self.assertEqual(account["平台"], "milun")

        # 断言站点地址与抓包一致。
        self.assertEqual(account["接口根地址"], "http://bxtyylsyf.hicp.net:1686")

        # 断言数据类型清单与映射约定一致（配送/库存材料留空未接入）。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义登录体形态验证。
    def test_login_payload_is_plain_form(self):

        """
        验证登录体为明文账号密码两字段。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言清洗后账号与台账一致（真实口令值只存 gitignored 本机配置，不入测试）。
        self.assertEqual(platform.clean_login_name(), "13423692449")
        self.assertEqual(platform.clean_login_password(), str(ACCOUNTS[self.ACCOUNT_KEY]["密码"]))
        self.assertTrue(platform.clean_login_password())

    # 定义单据类型过滤映射验证。
    def test_bill_type_filters_match_capture(self):

        """
        验证过滤串单据类型清单与抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言购进过滤清单与抓包一致。
        self.assertEqual(BILL_TYPE_FILTERS["购进流向"], "('采购退货单','采购入库单')")

        # 断言纯销过滤清单与抓包一致。
        self.assertEqual(BILL_TYPE_FILTERS["纯销流向"], "('零售销售单')")

    # 定义过滤串构造验证。
    def test_filter_text_construction(self):

        """
        验证过滤串按记账日期区间与单据类型清单拼接。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建购进过滤串。
        filter_text = platform.build_filter_text("购进流向", "2026-10-01", "2026-10-26")

        # 断言过滤串与抓包形态一致。
        self.assertEqual(filter_text, "[记账日期] >= '2026-10-01' And [记账日期] <= '2026-10-26' And [单据类型] in ('采购退货单','采购入库单')")

    # 定义空清单业务码验证。
    def test_empty_list_semantics(self):

        """
        验证嵌套数据块解析与空数据块口径。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言空数据块解析为空行集合。
        self.assertEqual(platform.parse_nested_rows(""), [])

        # 构造嵌套 JSON 字符串样例。
        nested = '[{"SYS_ID": "1", "记账日期": "2026-10-25", "数量": "1.0000"}]'

        # 解析嵌套数据块。
        rows = platform.parse_nested_rows(nested)

        # 断言数据行解析结果。
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["记账日期"], "2026-10-25")

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
            platform.validate_data_type("配送流向")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
