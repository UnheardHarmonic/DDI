# -*- coding: utf-8 -*-
"""
厦门祝强大药房 sosoyy 平台配置级新增契约测试。

本模块验证厦门祝强的账号配置完整性、站点地址与抓包一致、
协议端点映射与浏览器抓包一致、公开模板凭据留空与本地账密覆盖口径，
全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入搜搜电商平台适配器。
from ddi_framework.platforms.sosoyy import SosoyyPlatform, DATA_TYPE_CONFIG

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义厦门祝强配置级新增测试套件。
class XiamenZhuqiangConfigTests(unittest.TestCase):

    """
    厦门祝强大药房 sosoyy 平台配置级新增契约测试。

    :return: 测试套件实例。
    :rtype: XiamenZhuqiangConfigTests
    """

    # 定义类级商业名称引用。
    ACCOUNT_KEY = "厦门祝强大药房有限公司"

    # 定义类级站点地址引用（与浏览器抓包一致）。
    EXPECTED_SITE = "https://xmzqdyfyxgs24007.sosoyy.com"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["纯销流向", "库存", "购进流向", "配送流向"]

    # 定义类级协议端点映射引用（与浏览器抓包一致）。
    EXPECTED_ENDPOINTS = {
        "纯销流向": "/FlowDetails/QuerySalesDetails",
        "库存": "/FlowDetails/QueryStockDetails",
        "购进流向": "/FlowDetails/QueryPurchaseDetails",
        "配送流向": "/FlowDetails/QueryDeliveryDetails",
    }

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证厦门祝强账号声明平台归属、站点地址与分页口径。

        :return: None。
        :rtype: None
        """

        # 读取厦门祝强账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 sosoyy。
        self.assertEqual(account["平台"], "sosoyy")

        # 断言登录页与抓包一致。
        self.assertEqual(account["登录页"], f"{self.EXPECTED_SITE}/Account/Index")

        # 断言接口根地址与抓包一致。
        self.assertEqual(account["接口根地址"], self.EXPECTED_SITE)

        # 断言登录接口与抓包一致。
        self.assertEqual(account["登录接口"], f"{self.EXPECTED_SITE}/Account")

        # 断言分页大小与西昌东升同族口径。
        self.assertEqual(account["分页大小"], 500)

        # 断言查询超时与同族口径一致。
        self.assertEqual(account["查询超时秒"], 180)

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言账号处于启用状态。
        self.assertTrue(account["启用"])

    # 定义协议端点映射验证。
    def test_protocol_endpoints_match_capture(self):

        """
        验证四类型协议端点与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 遍历四类型端点映射。
        for data_type, endpoint in self.EXPECTED_ENDPOINTS.items():

            # 断言端点与抓包一致。
            self.assertEqual(DATA_TYPE_CONFIG[data_type]["endpoint"], endpoint, data_type)

    # 定义适配器站点装配验证。
    def test_adapter_binds_tenant_site(self):

        """
        验证适配器按账号配置装配厦门祝强独立租户站点。

        :return: None。
        :rtype: None
        """

        # 构建厦门祝强平台适配器实例。
        platform = SosoyyPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

        # 断言适配器根地址指向厦门祝强租户站点。
        self.assertEqual(platform.base_url, self.EXPECTED_SITE)

        # 断言适配器登录接口指向厦门祝强租户站点。
        self.assertEqual(platform.login_api_url, f"{self.EXPECTED_SITE}/Account")

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证厦门祝强组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取厦门祝强维度。
        dimension = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言大区为华南。
        self.assertEqual(dimension["大区"], "华南")

        # 断言省份为福建省。
        self.assertEqual(dimension["省份"], "福建省")

        # 断言负责人为覃祝燕。
        self.assertEqual(dimension["负责人"], "覃祝燕")

    # 定义公开模板凭据留空验证。
    def test_public_template_credentials_are_blank(self):

        """
        验证公开模板中凭据留空（真实值仅在本地私有文件）。

        :return: None。
        :rtype: None
        """

        # 读取公开模板源文件原文。
        public_source = Path(__file__).resolve().parents[1].joinpath("ddi_framework", "account_config.py").read_text(encoding="utf-8-sig")

        # 定位商业条目文本。
        entry_start = public_source.index('"' + self.ACCOUNT_KEY + '": {')

        # 截取条目片段。
        entry_text = public_source[entry_start:public_source.index("},", entry_start)]

        # 断言账号留空。
        self.assertIn('"账号": ""', entry_text)

        # 断言密码留空。
        self.assertIn('"密码": ""', entry_text)

    # 定义本地账密覆盖验证。
    def test_local_credentials_are_filled(self):

        """
        验证本地私有文件提供厦门祝强真实凭据。

        :return: None。
        :rtype: None
        """

        # 读取本地私有配置字典。
        from ddi_framework.account_config_local import ACCOUNTS as LOCAL_ACCOUNTS

        # 读取本地厦门祝强条目。
        local_account = LOCAL_ACCOUNTS[self.ACCOUNT_KEY]

        # 断言本地账号已配置。
        self.assertEqual(local_account["账号"], "15959250411")

        # 断言本地密码已配置。
        self.assertEqual(local_account["密码"], "12345678")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
