# -*- coding: utf-8 -*-
"""
山西国大万民 sxgdm 新平台接入契约测试。

本模块验证山西国大万民的账号配置完整性、协议端点映射、紧凑日期解析、
登录表单口径与公开模板凭据留空口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入山西国大万民 Scm 平台适配器。
from ddi_framework.platforms.sxgdm import SxgdmPlatform, DATA_TYPE_CONFIG

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义山西国大万民新平台接入测试套件。
class SxgdmPlatformTests(unittest.TestCase):

    """
    山西国大万民 sxgdm 新平台接入契约测试。

    :return: 测试套件实例。
    :rtype: SxgdmPlatformTests
    """

    # 定义类级商业名称引用。
    ACCOUNT_KEY = "山西国大万民药房连锁有限公司"

    # 定义类级站点地址引用（与浏览器抓包一致）。
    EXPECTED_SITE = "http://59.49.50.55:81"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "库存"]

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证山西国大万民账号声明平台归属、站点地址与数据类型口径。

        :return: None。
        :rtype: None
        """

        # 读取山西国大万民账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 sxgdm。
        self.assertEqual(account["平台"], "sxgdm")

        # 断言接口根地址与抓包一致。
        self.assertEqual(account["接口根地址"], self.EXPECTED_SITE)

        # 断言数据类型清单与平台菜单一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义协议端点映射验证。
    def test_endpoints_match_capture(self):

        """
        验证四类型协议端点与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言配送明细端点。
        self.assertEqual(DATA_TYPE_CONFIG["配送流向"]["端点"], "S_SendDtl.asp")

        # 断言入库查询端点。
        self.assertEqual(DATA_TYPE_CONFIG["购进流向"]["端点"], "s_InStock.asp")

        # 断言销量明细端点。
        self.assertEqual(DATA_TYPE_CONFIG["纯销流向"]["端点"], "S_SaleDtl.asp")

        # 断言库存明细端点。
        self.assertEqual(DATA_TYPE_CONFIG["库存"]["端点"], "s_StockDtl.asp")

    # 定义库存日期能力验证。
    def test_stock_has_no_begin_date(self):

        """
        验证库存查询仅携带截止日期。

        :return: None。
        :rtype: None
        """

        # 断言库存不需要开始日期。
        self.assertFalse(DATA_TYPE_CONFIG["库存"]["需要开始日期"])

        # 断言配送需要开始日期。
        self.assertTrue(DATA_TYPE_CONFIG["配送流向"]["需要开始日期"])

    # 定义登录表单口径验证。
    def test_login_uses_producer_form(self):

        """
        验证登录走生产商表单字段（Username2/Password2/captcha2）。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = SxgdmPlatform(self.ACCOUNT_KEY, {"平台": "sxgdm", "接口根地址": self.EXPECTED_SITE, "账号": "", "密码": ""}, printer=PrintHandler())

        # 构建登录表单文本。
        payload = f"Username2={platform.account.get('账号', '')}&Password2={platform.account.get('密码', '')}&captcha2=0"

        # 断言生产商标单字段齐全。
        self.assertTrue(payload.startswith("Username2=&Password2=&captcha2=0"))

    # 定义紧凑日期解析验证。
    def test_query_dates_compact_format(self):

        """
        验证查询日期解析为紧凑 YYYYMMDD 格式。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = SxgdmPlatform(self.ACCOUNT_KEY, {"平台": "sxgdm", "接口根地址": self.EXPECTED_SITE}, printer=PrintHandler())

        # 断言日期转换为紧凑格式。
        self.assertEqual(platform.resolve_query_dates("2026-10-01", "2026-10-31"), ("20261001", "20261031"))

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证山西国大万民组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取山西国大万民维度。
        dimension = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言大区省份负责人。
        self.assertEqual(dimension["大区"], "西北")
        self.assertEqual(dimension["省份"], "山西省")
        self.assertEqual(dimension["负责人"], "晏惟学")

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
        验证本地私有文件提供山西国大万民真实凭据。

        :return: None。
        :rtype: None
        """

        # 读取本地私有配置字典。
        from ddi_framework.account_config_local import ACCOUNTS as LOCAL_ACCOUNTS

        # 读取本地山西国大万民条目。
        local_account = LOCAL_ACCOUNTS[self.ACCOUNT_KEY]

        # 断言本地账号与密码与台账一致。
        self.assertEqual(local_account["账号"], "c00608")
        self.assertEqual(local_account["密码"], "123456")

    # 定义平台注册表装配验证。
    def test_platform_registry_binds_adapter(self):

        """
        验证平台注册表已绑定 sxgdm 适配器。

        :return: None。
        :rtype: None
        """

        # 导入平台注册表。
        from ddi_framework.platform_registry import PLATFORM_REGISTRY

        # 断言注册表绑定山西国大万民平台适配器。
        self.assertIs(PLATFORM_REGISTRY["sxgdm"], SxgdmPlatform)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
