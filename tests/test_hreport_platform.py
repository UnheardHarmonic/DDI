# -*- coding: utf-8 -*-
"""
HReport 家族平台配置与类型门契约测试。

本模块验证万鑫/健南门/日月七天三家 hreport 系商业的配置形态、
类型门覆盖（含报损流向扩展）与日期区间口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入 HReport 平台适配器。
from ddi_framework.platforms.hreport import HreportPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义 HReport 家族配置契约测试套件。
class HreportPlatformConfigTests(unittest.TestCase):

    """
    HReport 家族平台配置契约测试。

    :return: 测试套件实例。
    :rtype: HreportPlatformConfigTests
    """

    # 定义类级北京日月七天账号键引用。
    ACCOUNT_KEY = "北京日月七天药房有限公司"

    # 定义平台适配器构建方法。
    def build_platform(self, company_name=None):

        """
        构建平台适配器实例。

        :param company_name: 商业公司名称，缺省为日月七天。
        :type company_name: str | None
        :return: HReport 平台适配器实例。
        :rtype: HreportPlatform
        """

        # 读取账号配置并构建适配器。
        key = company_name or self.ACCOUNT_KEY
        return HreportPlatform(key, ACCOUNTS[key], printer=PrintHandler())

    # 定义日月七天账号声明完整性验证。
    def test_riyueqitian_account_declaration_is_complete(self):

        """
        验证日月七天账号声明部署端点、五类型功能编号与字段模板。

        :return: None。
        :rtype: None
        """

        # 读取日月七天账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 hreport。
        self.assertEqual(account["平台"], "hreport")

        # 断言站点部署地址。
        self.assertIn("140.143.145.232:8080", account["登录接口"])

        # 断言五类型功能编号映射与抓包一致。
        self.assertEqual(account["报表功能编号"], {"购进流向": "37", "配送流向": "10001", "纯销流向": "10002", "报损流向": "45", "库存": "44"})

        # 断言登录验证码字段为纯前端 Canvas 口径的固定值模式。
        self.assertEqual(account["登录验证码字段"], "yzmcode")

    # 定义类型门覆盖报损流向验证。
    def test_type_gate_covers_loss_type(self):

        """
        验证类型门放行报损流向并拦截未接入类型。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言报损流向通过类型门。
        platform.validate_data_type("报损流向")

        # 断言未知类型抛出异常。
        with self.assertRaises(NotImplementedError):
            platform.validate_data_type("批发流向")

    # 定义日期区间口径验证。
    def test_date_range_requirements(self):

        """
        验证四流向类要求日期区间且库存按快照口径。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言四个日期区间类型。
        for data_type in ("配送流向", "购进流向", "纯销流向", "报损流向"):
            self.assertTrue(platform.requires_date_range(data_type), data_type)

        # 断言库存为快照口径。
        self.assertFalse(platform.requires_date_range("库存"))

    # 定义功能编号构建验证。
    def test_build_func_id_reads_config(self):

        """
        验证功能编号按账号配置映射读取。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言购进与报损的功能编号。
        self.assertEqual(platform.build_func_id("购进流向"), "37")
        self.assertEqual(platform.build_func_id("报损流向"), "45")

    # 定义登录验证码固定值模式验证。
    def test_login_payload_carrys_captcha_fixed_value(self):

        """
        验证登录负载按纯前端 Canvas 口径携带验证码固定值。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建登录负载。
        payload = platform.build_login_payload()

        # 断言 Spring Security 三字段齐备。
        self.assertEqual(payload["j_username"], "0872")
        self.assertEqual(payload["yzmcode"], "abcd")

        # 断言密码为 MD5 摘要（32 位十六进制）。
        self.assertEqual(len(payload["j_password"]), 32)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
