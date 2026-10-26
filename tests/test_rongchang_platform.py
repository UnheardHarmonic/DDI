# -*- coding: utf-8 -*-
"""
福建省泉州市荣昌药业海翔药业云平台接入契约测试。

本模块验证荣昌账号配置完整性、海翔平台登录体字段形态、报表请求体形态
与页签映射口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入 JSON 编解码模块。
import json

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入海翔供应链平台适配器。
from ddi_framework.platforms.hx import HxPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义荣昌海翔平台接入契约测试套件。
class RongchangPlatformTests(unittest.TestCase):

    """
    福建省泉州市荣昌药业海翔药业云平台接入契约测试。

    :return: 测试套件实例。
    :rtype: RongchangPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "福建省泉州市荣昌药业有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["购进流向", "配送流向", "库存"]

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 海翔供应链平台适配器实例。
        :rtype: HxPlatform
        """

        # 读取账号配置并构建适配器。
        return HxPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证荣昌账号声明平台归属、站点地址与账套三要素。

        :return: None。
        :rtype: None
        """

        # 读取荣昌账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 hx。
        self.assertEqual(account["平台"], "hx")

        # 断言站点地址与抓包一致。
        self.assertEqual(account["接口根地址"], "https://rcyy.seaflysoft.com")

        # 断言账套三要素与抓包一致（门店版编码 16、账套编号 3 来自 pJson y_id）。
        self.assertEqual(account["账套版本编码"], "16")
        self.assertEqual(account["账套"], "福建荣昌药业")
        self.assertEqual(account["账套编号"], "3")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义登录体字段形态验证。
    def test_login_payload_shape(self):

        """
        验证登录体携带门店版编码、账套与登录机构要素。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建登录请求体。
        payload = platform.build_login_payload()

        # 断言门店版编码与账套要素。
        self.assertEqual(payload["verflag"], "16")
        self.assertEqual(payload["accountname"], "福建荣昌药业")
        self.assertEqual(payload["yid"], "3")
        self.assertEqual(payload["code"], "桂林华诺威")
        self.assertEqual(payload["password"], "gl12345678")

    # 定义报表请求体形态验证。
    def test_report_payload_shape(self):

        """
        验证分页请求体页签、报表名与业务参数形态。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建购进流向分页请求体。
        payload = platform.build_report_payload("购进流向", "2026-08-01", "2026-10-26", 2)

        # 断言页签与报表名与抓包一致。
        self.assertEqual(payload["tabID"], "1")
        self.assertEqual(payload["reportName"], "rp_supplierflow_dz")
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["rows"], 50)

        # 解析业务参数断言日期与账套编号。
        report_params = json.loads(payload["parJson"])
        self.assertEqual(report_params["begindate"], "2026-08-01")
        self.assertEqual(report_params["enddate"], "2026-10-26")
        self.assertEqual(report_params["y_id"], 3)

        # 断言门店版部署剔除 supplyid 字段（荣昌站点带该字段返回空响应）。
        self.assertNotIn("supplyid", report_params)

        # 断言蜂鸟默认配置仍携带 supplyid（企业版行为零漂移）。
        fengniao_payload = HxPlatform("福建蜂鸟医药有限公司", ACCOUNTS["福建蜂鸟医药有限公司"], printer=PrintHandler()).build_report_params("2026-08-01", "2026-10-26")
        self.assertIn("supplyid", fengniao_payload)

    # 定义页签映射验证。
    def test_tab_id_mapping(self):

        """
        验证荣昌门店版页签顺序（采购1/库存2/销售3）与蜂鸟默认顺序各自成立。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言荣昌页签编号（销售明细=配送流向为 3、库存明细为 2）。
        self.assertEqual(platform.build_tab_id("购进流向"), "1")
        self.assertEqual(platform.build_tab_id("配送流向"), "3")
        self.assertEqual(platform.build_tab_id("库存"), "2")

        # 断言蜂鸟默认页签编号零漂移。
        fengniao = HxPlatform("福建蜂鸟医药有限公司", ACCOUNTS["福建蜂鸟医药有限公司"], printer=PrintHandler())
        self.assertEqual(fengniao.build_tab_id("配送流向"), "2")
        self.assertEqual(fengniao.build_tab_id("库存"), "3")

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
            platform.validate_data_type("纯销流向")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
