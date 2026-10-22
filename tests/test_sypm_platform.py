# -*- coding: utf-8 -*-
"""
漱玉医药物流(山东)有限公司 QQT SRM 门户接入契约测试。

本模块验证漱玉账号配置完整性、四类型端点映射、日期区间口径、
查询参数形态与令牌承载方式，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入漱玉平台适配器。
from ddi_framework.platforms.sypm import SypmPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义漱玉接入契约测试套件。
class SypmPlatformTests(unittest.TestCase):

    """
    漱玉 QQT SRM 门户接入契约测试。

    :return: 测试套件实例。
    :rtype: SypmPlatformTests
    """

    # 定义类级账号配置引用。
    ACCOUNT_KEY = "漱玉医药物流(山东)有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["购进流向", "纯销流向", "配送流向", "库存"]

    # 定义类级数据端点映射引用。
    EXPECTED_PATHS = {
        "购进流向": "/supplier/saleMaterialFlow/detailList",
        "纯销流向": "/supplier/saleMaterialFlow/detailSaleList",
        "配送流向": "/supplier/saleMaterialFlow/detailDeliveryList",
        "库存": "/supplier/saleMaterialFlow/detailStockList",
    }

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建注入访问令牌的适配器实例。

        :return: 漱玉平台适配器实例。
        :rtype: SypmPlatform
        """

        # 读取漱玉账号配置并构建适配器。
        platform = SypmPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

        # 注入访问令牌模拟已登录状态。
        platform.access_token = "token-sample"

        # 返回适配器实例。
        return platform

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证漱玉账号声明包含平台归属、凭据字段与数据类型清单。

        :return: None。
        :rtype: None
        """

        # 读取漱玉账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为漱玉门户。
        self.assertEqual(account["平台"], "sypm")

        # 断言站点根地址指向漱玉域名。
        self.assertIn("sybm.sypm.cn", account["站点根地址"])

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义四类型端点覆盖验证。
    def test_data_paths_cover_all_types(self):

        """
        验证四类型查询端点与页面抓包地址一致。

        :return: None。
        :rtype: None
        """

        # 断言端点映射与约定一致。
        self.assertEqual(SypmPlatform.DATA_PATHS, self.EXPECTED_PATHS)

    # 定义日期区间口径验证。
    def test_date_range_requirements(self):

        """
        验证流向三类型要求日期区间且库存为快照免日期。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言流向三类型要求日期区间。
        for data_type in ["购进流向", "纯销流向", "配送流向"]:
            self.assertTrue(platform.requires_date_range(data_type), data_type)

        # 断言库存为快照不要求日期。
        self.assertFalse(platform.requires_date_range("库存"))

    # 定义查询地址参数形态验证。
    def test_query_url_matches_capture(self):

        """
        验证流向与库存查询地址的查询串与抓包一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建购进流向查询地址。
        purchase_url = platform.build_query_url("购进流向", "2026-10-01", "2026-10-22", 1)

        # 断言端点与紧凑日期与分页参数齐备。
        self.assertIn("/supplier/saleMaterialFlow/detailList?", purchase_url)
        self.assertIn("startDate=20261001", purchase_url)
        self.assertIn("endDate=20261022", purchase_url)
        self.assertIn("pageSize=500", purchase_url)
        self.assertIn("pageNo=1", purchase_url)
        self.assertIn("column=id", purchase_url)
        self.assertIn("order=desc", purchase_url)
        self.assertIn("filter=%7B%7D", purchase_url)

        # 构建库存查询地址。
        stock_url = platform.build_query_url("库存", None, None, 2)

        # 断言库存端点正确且不携带日期参数。
        self.assertIn("/supplier/saleMaterialFlow/detailStockList?", stock_url)
        self.assertNotIn("startDate", stock_url)
        self.assertNotIn("endDate", stock_url)
        self.assertIn("pageNo=2", stock_url)

    # 定义数据请求头形态验证。
    def test_data_headers_carry_token(self):

        """
        验证数据请求头以 X-Access-Token 承载会话。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建数据请求头。
        headers = platform.build_data_headers()

        # 断言令牌头为注入值。
        self.assertEqual(headers["X-Access-Token"], "token-sample")

        # 断言内容类型为 JSON。
        self.assertEqual(headers["Content-Type"], "application/json")

    # 定义未知数据类型拒绝验证。
    def test_unknown_type_rejected(self):

        """
        验证未接入数据类型抛出未接入异常。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言未知类型触发未接入异常。
        with self.assertRaises(NotImplementedError):
            platform.validate_data_type("报损流向")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
