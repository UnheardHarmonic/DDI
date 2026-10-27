# -*- coding: utf-8 -*-
"""
镇江存仁堂医药连锁有限责任公司全亿健康 SRM 平台接入契约测试。

本模块验证存仁堂账号配置完整性、四类型网关方法映射、业务参数组装
与日期毫秒换算口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入 JSON 编解码模块。
import json

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入全亿健康 OA 平台适配器。
from ddi_framework.platforms.jshthy import JshthyPlatform
from ddi_framework.platforms.jshthy import SRM_GATEWAY_METHODS

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义存仁堂 SRM 平台接入契约测试套件。
class CunrentangPlatformTests(unittest.TestCase):

    """
    镇江存仁堂医药连锁有限责任公司全亿健康 SRM 平台接入契约测试。

    :return: 测试套件实例。
    :rtype: CunrentangPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "镇江存仁堂医药连锁有限责任公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["购进流向", "配送流向", "纯销流向", "库存"]

    # 定义类级网关方法映射引用（与浏览器抓包一致）。
    EXPECTED_METHODS = {
        "购进流向": "ykcloud.supinterface.oaSrmPurchase.queryPage",
        "配送流向": "ykcloud.supinterface.oaSrmDist.queryPage",
        "纯销流向": "ykcloud.supinterface.oaSrmSale.queryPage",
        "库存": "ykcloud.supinterface.oaSrmStock.queryPage",
    }

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 全亿健康 OA 平台适配器实例。
        :rtype: JshthyPlatform
        """

        # 读取账号配置并注入登录响应样例（离线模拟会话用户编号）。
        platform = JshthyPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())
        platform.login_result = {"userid": 111587}
        return platform

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证存仁堂账号声明平台归属、站点双地址与公司编码。

        :return: None。
        :rtype: None
        """

        # 读取存仁堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 jshthy。
        self.assertEqual(account["平台"], "jshthy")

        # 断言登录站点与数据网关地址与抓包一致。
        self.assertEqual(account["接口根地址"], "https://oa.myquanyi.com")
        self.assertEqual(account["数据网关地址"], "https://xb-test.myquanyi.com:8080/portal-prod/gateway-manager/xjl-job")

        # 断言公司编码与租户编号与抓包一致。
        self.assertEqual(account["公司编码"], "CR01")
        self.assertEqual(account["租户编号"], "18")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义网关方法映射验证。
    def test_gateway_methods_match_capture(self):

        """
        验证四类型网关方法与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言方法映射与约定一致。
        self.assertEqual(SRM_GATEWAY_METHODS, self.EXPECTED_METHODS)

    # 定义业务参数组装验证。
    def test_gateway_params_shape(self):

        """
        验证业务参数携带租户、公司编码与日期毫秒区间。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建购进流向业务参数。
        params = platform.build_gateway_params("购进流向", "2026-10-01", "2026-10-27", 2)

        # 断言租户、公司编码与分页域。
        self.assertEqual(params["tenant_num_id"], "18")
        self.assertEqual(params["cort_num_id"], "CR01")
        self.assertEqual(params["page_num"], 2)
        self.assertEqual(params["page_size"], 10)

        # 断言日期毫秒换算（北京时区当日零点）。
        self.assertEqual(params["rec_date_begin"], 1790812800000)

    # 定义库存快照无日期验证。
    def test_stock_snapshot_has_no_date(self):

        """
        验证库存业务参数不携带日期字段。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建库存业务参数。
        params = platform.build_gateway_params("库存", "2026-10-01", "2026-10-27", 1)

        # 断言无日期字段（快照口径）。
        self.assertNotIn("rec_date_begin", params)
        self.assertNotIn("ship_date_begin", params)
        self.assertNotIn("order_date_begin", params)

    # 定义会话凭证缺失验证。
    def test_missing_session_credential_is_rejected(self):

        """
        验证未配置 SRM 会话凭证时抛出明确异常。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言缺失凭证抛出异常。
        with self.assertRaises(RuntimeError):
            platform.query_srm_data("购进流向", "2026-10-01", "2026-10-27")

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


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
