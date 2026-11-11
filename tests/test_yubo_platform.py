# -*- coding: utf-8 -*-
"""
浙江御博 yubo 新平台接入契约测试。

本模块验证浙江御博的账号配置完整性、协议端点映射、算式信封与事件口径、
公开模板凭据留空与本地账密覆盖口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入御博商品流向系统平台适配器。
from ddi_framework.platforms.yubo import YuboPlatform, DATA_TYPE_CONFIG

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义浙江御博新平台接入测试套件。
class YuboPlatformTests(unittest.TestCase):

    """
    浙江御博 yubo 新平台接入契约测试。

    :return: 测试套件实例。
    :rtype: YuboPlatformTests
    """

    # 定义类级商业名称引用。
    ACCOUNT_KEY = "浙江御博医药有限公司"

    # 定义类级站点地址引用（与浏览器抓包一致）。
    EXPECTED_SITE = "http://183.129.147.130:18066"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "库存"]

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证浙江御博账号声明平台归属、站点地址与数据类型口径。

        :return: None。
        :rtype: None
        """

        # 读取浙江御博账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 yubo。
        self.assertEqual(account["平台"], "yubo")

        # 断言接口根地址与抓包一致。
        self.assertEqual(account["接口根地址"], self.EXPECTED_SITE)

        # 断言数据类型清单与平台菜单一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义菜单映射验证。
    def test_menu_mapping(self):

        """
        验证数据类型与平台菜单标题映射一致。

        :return: None。
        :rtype: None
        """

        # 断言配送流向映射商品流向菜单。
        self.assertEqual(DATA_TYPE_CONFIG["配送流向"], "商品流向")

        # 断言库存映射库存查询菜单。
        self.assertEqual(DATA_TYPE_CONFIG["库存"], "库存查询")

    # 定义算式信封构建验证。
    def test_envelope_has_url_line_and_blank_line(self):

        """
        验证信封包含 Url 行与头体间空行（历史墙的两个修复点）。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = YuboPlatform(self.ACCOUNT_KEY, {"平台": "yubo", "接口根地址": self.EXPECTED_SITE, "账号": "", "密码": ""}, printer=PrintHandler())
        platform.guid = "11111111-1111-1111-1111-111111111111"

        # 构建信封（device-info 页面路径与浏览器一致）。
        envelope = platform.build_envelope("*/", "{}")

        # 断言请求行。
        self.assertTrue(envelope.startswith("STTP/1.0 GET 183.129.147.130:18066/*/"))

        # 断言 Url 行存在。
        self.assertIn("Url:http://183.129.147.130:18066/", envelope)

        # 断言头体之间为空行分隔。
        self.assertIn("\r\n\r\n{}", envelope)

    # 定义算式解析与查询日期验证。
    def test_query_dates_resolution(self):

        """
        验证查询日期解析与范围校验。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = YuboPlatform(self.ACCOUNT_KEY, {"平台": "yubo", "接口根地址": self.EXPECTED_SITE}, printer=PrintHandler())

        # 断言显式日期回传。
        self.assertEqual(platform.resolve_query_dates("2026-10-01", "2026-10-31"), ("2026-10-01", "2026-10-31"))

        # 断言开始晚于结束抛出异常。
        with self.assertRaises(ValueError):
            platform.resolve_query_dates("2026-10-31", "2026-10-01")

    # 定义未接入类型拒绝验证。
    def test_unsupported_type_is_rejected(self):

        """
        验证平台菜单外数据类型被明确拒绝。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = YuboPlatform(self.ACCOUNT_KEY, {"平台": "yubo", "接口根地址": self.EXPECTED_SITE}, printer=PrintHandler())

        # 断言购进流向拒绝（平台菜单无此数据集）。
        with self.assertRaises(ValueError):
            platform.resolve_config("购进流向")

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证浙江御博组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取浙江御博维度。
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
        验证本地私有文件提供浙江御博真实凭据。

        :return: None。
        :rtype: None
        """

        # 读取本地私有配置字典。
        from ddi_framework.account_config_local import ACCOUNTS as LOCAL_ACCOUNTS

        # 读取本地浙江御博条目。
        local_account = LOCAL_ACCOUNTS[self.ACCOUNT_KEY]

        # 断言本地账号与密码与台账一致。
        self.assertEqual(local_account["账号"], "glhn")
        self.assertEqual(local_account["密码"], "1111")

    # 定义平台注册表装配验证。
    def test_platform_registry_binds_adapter(self):

        """
        验证平台注册表已绑定 yubo 适配器。

        :return: None。
        :rtype: None
        """

        # 导入平台注册表。
        from ddi_framework.platform_registry import PLATFORM_REGISTRY

        # 断言注册表绑定御博平台适配器。
        self.assertIs(PLATFORM_REGISTRY["yubo"], YuboPlatform)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
