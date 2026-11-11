# -*- coding: utf-8 -*-
"""
金华英特 inte 新平台接入契约测试。

本模块验证金华英特的账号配置完整性、协议端点映射、算式解析口径、
公开模板凭据留空与本地账密覆盖口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入英特集团流向查询平台适配器。
from ddi_framework.platforms.inte import IntePlatform, DATA_TYPE_CONFIG

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义金华英特新平台接入测试套件。
class JinhuaYintePlatformTests(unittest.TestCase):

    """
    金华英特 inte 新平台接入契约测试。

    :return: 测试套件实例。
    :rtype: JinhuaYintePlatformTests
    """

    # 定义类级商业名称引用。
    ACCOUNT_KEY = "金华英特药业有限公司"

    # 定义类级站点地址引用（与浏览器抓包一致）。
    EXPECTED_SITE = "http://220.191.160.242:8888"

    # 定义类级数据类型清单引用（平台仅提供单一流向数据集与库存）。
    EXPECTED_TYPES = ["配送流向", "库存"]

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证金华英特账号声明平台归属、站点地址与数据类型口径。

        :return: None。
        :rtype: None
        """

        # 读取金华英特账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 inte。
        self.assertEqual(account["平台"], "inte")

        # 断言登录页与抓包一致。
        self.assertEqual(account["登录页"], f"{self.EXPECTED_SITE}/login")

        # 断言接口根地址与抓包一致。
        self.assertEqual(account["接口根地址"], self.EXPECTED_SITE)

        # 断言数据类型清单与平台实际数据集一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义协议端点映射验证。
    def test_endpoints_match_capture(self):

        """
        验证两类型协议端点与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言流向端点。
        self.assertEqual(DATA_TYPE_CONFIG["配送流向"]["端点"], "/system/itMedicinegotoInoutroom/list")

        # 断言流向时间口径为出库时间（台账映射）。
        self.assertEqual(DATA_TYPE_CONFIG["配送流向"]["时间类型"], "0")

        # 断言库存端点。
        self.assertEqual(DATA_TYPE_CONFIG["库存"]["端点"], "/system/itMedicinegotoStorege/list")

    # 定义算式解析验证。
    def test_math_expression_parsing(self):

        """
        验证算术验证码各算符解析与计算正确。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = IntePlatform(self.ACCOUNT_KEY, {"平台": "inte", "接口根地址": self.EXPECTED_SITE}, printer=PrintHandler())

        # 断言加法。
        self.assertEqual(platform.parse_math_expression("3+7=?"), 10)

        # 断言减法允许负数。
        self.assertEqual(platform.parse_math_expression("1-2≈?"), -1)

        # 断言乘法。
        self.assertEqual(platform.parse_math_expression("5*7=?"), 35)

        # 断言乘号变体。
        self.assertEqual(platform.parse_math_expression("5x7=?"), 35)

        # 断言波浪号误读归一化。
        self.assertEqual(platform.parse_math_expression("1~2=?"), -1)

        # 断言含杂讯文本取首个算式。
        self.assertEqual(platform.parse_math_expression("0+9=7"), 9)

        # 断言无法解析返回 None。
        self.assertIsNone(platform.parse_math_expression("6t5x2"))

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证金华英特组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取金华英特维度。
        dimension = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言大区省份负责人。
        self.assertEqual(dimension["大区"], "华南")
        self.assertEqual(dimension["省份"], "浙江省")
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

        # 断言账号与密码留空。
        self.assertIn('"账号": ""', entry_text)
        self.assertIn('"密码": ""', entry_text)

    # 定义本地账密覆盖验证。
    def test_local_credentials_are_filled(self):

        """
        验证本地私有文件提供金华英特真实凭据。

        :return: None。
        :rtype: None
        """

        # 读取本地私有配置字典。
        from ddi_framework.account_config_local import ACCOUNTS as LOCAL_ACCOUNTS

        # 读取本地金华英特条目。
        local_account = LOCAL_ACCOUNTS[self.ACCOUNT_KEY]

        # 断言本地账号与密码与台账一致。
        self.assertEqual(local_account["账号"], "zjyb1234")
        self.assertEqual(local_account["密码"], "XLL1982ieuuss")

    # 定义平台注册表装配验证。
    def test_platform_registry_binds_adapter(self):

        """
        验证平台注册表已绑定 inte 适配器。

        :return: None。
        :rtype: None
        """

        # 导入平台注册表。
        from ddi_framework.platform_registry import PLATFORM_REGISTRY

        # 断言注册表绑定英特平台适配器。
        self.assertIs(PLATFORM_REGISTRY["inte"], IntePlatform)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
