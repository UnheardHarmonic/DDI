# -*- coding: utf-8 -*-
"""
福建省博爱医药连锁有限公司 HReport 平台接入契约测试。

本模块验证博爱账号配置完整性、Spring Security 登录体 MD5 形态、
无验证码字段口径与驼峰日期查询模板，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入 HReport 平台适配器。
from ddi_framework.platforms.hreport import HreportPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义博爱 HReport 接入契约测试套件。
class BoaiPlatformTests(unittest.TestCase):

    """
    福建省博爱医药连锁有限公司 HReport 平台接入契约测试。

    :return: 测试套件实例。
    :rtype: BoaiPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "福建省博爱医药连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "库存"]

    # 定义类级报表功能编号引用（站点 qryParamList 实测校准）。
    EXPECTED_FUNC_IDS = {"购进流向": "37", "配送流向": "45", "库存": "44"}

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: HReport 平台适配器实例。
        :rtype: HreportPlatform
        """

        # 读取账号配置并构建适配器。
        return HreportPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证博爱账号声明平台归属、站点地址与类型清单。

        :return: None。
        :rtype: None
        """

        # 读取博爱账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 hreport。
        self.assertEqual(account["平台"], "hreport")

        # 断言登录接口与抓包一致。
        self.assertEqual(account["登录接口"], "http://182.44.76.78:13333/hreport-manager/j_spring_security_check")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言报表功能编号与站点实测一致。
        self.assertEqual(account["报表功能编号"], self.EXPECTED_FUNC_IDS)

        # 断言未配置验证码字段（博爱登录页无验证码框）。
        self.assertFalse(account.get("登录验证码字段", ""))

    # 定义登录体形态验证。
    def test_login_payload_is_md5_spring_security(self):

        """
        验证登录体为 j_username 与 MD5 密文密码且不含验证码字段。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建登录请求体。
        payload = platform.build_login_payload()

        # 断言账号与 MD5 密文密码（抓包 j_password 同为 32 位小写摘要形态）。
        self.assertEqual(payload["j_username"], "0088")
        self.assertEqual(payload["j_password"], "9ce086727c3752234c7e702b2f4d3f19")
        self.assertNotEqual(payload["j_password"], "Qwer!123")

        # 断言登录体仅有账号与密码两个字段。
        self.assertEqual(sorted(payload.keys()), ["j_password", "j_username"])

    # 定义查询模板驼峰日期验证。
    def test_query_template_uses_camel_date(self):

        """
        验证流向模板日期参数为站点实测的驼峰形态 beginDate/endDate。

        :return: None。
        :rtype: None
        """

        # 读取博爱账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言配送模板日期参数名与渲染。
        delivery_template = account["查询字段模板"]["配送流向"]
        self.assertEqual(delivery_template["beginDate"], "{start_date}")
        self.assertEqual(delivery_template["endDate"], "{end_date}")

        # 断言购进模板日期参数名与渲染。
        purchase_template = account["查询字段模板"]["购进流向"]
        self.assertEqual(purchase_template["beginDate"], "{start_date}")
        self.assertEqual(purchase_template["endDate"], "{end_date}")

        # 断言库存模板无日期参数（快照口径）。
        stock_template = account["查询字段模板"]["库存"]
        self.assertNotIn("beginDate", stock_template)
        self.assertNotIn("begindate", stock_template)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
