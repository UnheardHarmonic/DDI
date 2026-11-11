# -*- coding: utf-8 -*-
"""
辽宁国大医药 guodagys 新平台接入契约测试。

本模块验证辽宁国大的账号配置完整性、协议端点映射、登录与查询表单口径、
库存双源工作表映射、公开模板凭据留空与本地账密覆盖口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入国大药房供应商查询平台适配器。
from ddi_framework.platforms.guodagys import GuodagysPlatform, DATA_TYPE_CONFIG, INVENTORY_SHEET_CONFIG

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义辽宁国大新平台接入测试套件。
class GuodagysPlatformTests(unittest.TestCase):

    """
    辽宁国大医药 guodagys 新平台接入契约测试。

    :return: 测试套件实例。
    :rtype: GuodagysPlatformTests
    """

    # 定义类级商业名称引用。
    ACCOUNT_KEY = "辽宁国大医药有限公司"

    # 定义类级站点地址引用（与浏览器抓包一致）。
    EXPECTED_SITE = "http://60.16.19.57:10088"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "库存"]

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证辽宁国大账号声明平台归属、站点地址与公司选项。

        :return: None。
        :rtype: None
        """

        # 读取辽宁国大账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 guodagys。
        self.assertEqual(account["平台"], "guodagys")

        # 断言登录页与抓包一致。
        self.assertEqual(account["登录页"], f"{self.EXPECTED_SITE}/new_gyssystem/login.jsp")

        # 断言接口根地址与抓包一致。
        self.assertEqual(account["接口根地址"], self.EXPECTED_SITE)

        # 断言系统路径与抓包一致。
        self.assertEqual(account["系统路径"], "/new_gyssystem")

        # 断言公司选项编码与下拉值一致（辽宁批发）。
        self.assertEqual(account["公司编码"], "1009")

        # 断言数据类型清单与台账映射一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义协议端点映射验证。
    def test_endpoints_match_capture(self):

        """
        验证四类型协议端点与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言大仓购进端点。
        self.assertEqual(DATA_TYPE_CONFIG["购进流向"]["端点"], "dcjh")

        # 断言大仓配送端点。
        self.assertEqual(DATA_TYPE_CONFIG["配送流向"]["端点"], "phlx")

        # 断言门店纯销端点。
        self.assertEqual(DATA_TYPE_CONFIG["纯销流向"]["端点"], "mdcx")

        # 断言大仓库存端点。
        self.assertEqual(DATA_TYPE_CONFIG["库存"]["端点"], "dckc")

        # 断言库存双工作表映射。
        self.assertEqual(INVENTORY_SHEET_CONFIG, {"dckc": "大仓库存", "mdkc": "门店库存"})

    # 定义登录表单口径验证。
    def test_login_payload_has_no_captcha(self):

        """
        验证登录表单仅含账号密码两个字段（无验证码）。

        :return: None。
        :rtype: None
        """

        # 构建空白凭据平台适配器实例。
        platform = GuodagysPlatform(self.ACCOUNT_KEY, {"平台": "guodagys", "接口根地址": self.EXPECTED_SITE, "账号": "", "密码": ""}, printer=PrintHandler())

        # 构建登录表单文本。
        payload = platform.build_login_payload()

        # 断言表单为账号密码两字段口径。
        self.assertEqual(payload, "zh=&mm=")

        # 断言表单不含验证码字段。
        self.assertNotIn("yzm", payload)

    # 定义查询表单构建验证。
    def test_query_payload_matches_capture(self):

        """
        验证流向与库存查询表单与抓包 Content-Length 口径一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例（公司编码注入）。
        platform = GuodagysPlatform(self.ACCOUNT_KEY, {"平台": "guodagys", "接口根地址": self.EXPECTED_SITE, "公司编码": "1009"}, printer=PrintHandler())

        # 构建大仓购进查询表单。
        purchase_payload = platform.build_query_payload(DATA_TYPE_CONFIG["购进流向"], "2026-10-01", "2026-10-31")

        # 断言大仓购进表单与浏览器抓包一致。
        self.assertEqual(purchase_payload, "gs=1009&bm=&logmin=2026-10-01&logmax=2026-10-31")

        # 构建门店纯销查询表单。
        sale_payload = platform.build_query_payload(DATA_TYPE_CONFIG["纯销流向"], "2026-10-01", "2026-10-31")

        # 断言门店纯销表单不携带公司字段。
        self.assertEqual(sale_payload, "bm=&logmin=2026-10-01&logmax=2026-10-31")

        # 构建大仓库存查询表单。
        stock_payload = platform.build_query_payload(DATA_TYPE_CONFIG["库存"], None, None)

        # 断言大仓库存表单为双字段快照口径。
        self.assertEqual(stock_payload, "gs=1009&bm=")

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证辽宁国大组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取辽宁国大维度。
        dimension = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言大区省份负责人。
        self.assertEqual(dimension["大区"], "西北东北")
        self.assertEqual(dimension["省份"], "辽宁省")
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
        验证本地私有文件提供辽宁国大真实凭据。

        :return: None。
        :rtype: None
        """

        # 读取本地私有配置字典。
        from ddi_framework.account_config_local import ACCOUNTS as LOCAL_ACCOUNTS

        # 读取本地辽宁国大条目。
        local_account = LOCAL_ACCOUNTS[self.ACCOUNT_KEY]

        # 断言本地账号与密码与台账一致。
        self.assertEqual(local_account["账号"], "sygd0628")
        self.assertEqual(local_account["密码"], "Sun123456")

    # 定义平台注册表装配验证。
    def test_platform_registry_binds_adapter(self):

        """
        验证平台注册表已绑定 guodagys 适配器。

        :return: None。
        :rtype: None
        """

        # 导入平台注册表。
        from ddi_framework.platform_registry import PLATFORM_REGISTRY

        # 断言注册表绑定国大药房供应商查询平台适配器。
        self.assertIs(PLATFORM_REGISTRY["guodagys"], GuodagysPlatform)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
