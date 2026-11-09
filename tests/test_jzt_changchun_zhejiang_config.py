# -*- coding: utf-8 -*-
"""
长春/浙江九州通 jzt 平台配置级新增契约测试。

本模块验证两家新九州通商业的账号配置完整性、机构码与抓包一致、
公开模板凭据留空与本地账密覆盖口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS


# 定义九州通两家配置级新增测试套件。
class JztConfigExpansionTests(unittest.TestCase):

    """
    长春/浙江九州通 jzt 平台配置级新增契约测试。

    :return: 测试套件实例。
    :rtype: JztConfigExpansionTests
    """

    # 定义类级商业名称与机构码映射引用（与浏览器抓包一致）。
    EXPECTED_ORGS = {
        "长春九州通医药有限公司": ["FWP"],
        "浙江九州通医药有限公司": ["FC3", "FD6", "FHZ", "FKJ", "FLK"],
    }

    # 定义类级数据类型清单映射引用。
    EXPECTED_TYPES = {
        "长春九州通医药有限公司": ["配送流向", "购进流向", "库存", "报损流向"],
        "浙江九州通医药有限公司": ["配送流向", "购进流向", "库存"],
    }

    # 定义账号声明完整性验证。
    def test_accounts_declaration(self):

        """
        验证两商业平台归属、站点与机构码与抓包一致。

        :return: None。
        :rtype: None
        """

        # 遍历两家商业。
        for company_name, orgs in self.EXPECTED_ORGS.items():

            # 读取账号配置。
            account = ACCOUNTS[company_name]

            # 断言平台归属为 jzt。
            self.assertEqual(account["平台"], "jzt", company_name)

            # 断言站点与九州通族一致。
            self.assertEqual(account["登录页"], "https://flow.jztit.com/user/login.html", company_name)

            # 断言机构码与抓包一致。
            self.assertEqual(account["机构"], orgs, company_name)

            # 断言日志机构编码为首机构。
            self.assertEqual(account["日志机构编码"], orgs[0], company_name)

            # 断言操作员名称为商业全名。
            self.assertEqual(account["操作员名称"], company_name, company_name)

            # 断言数据类型清单与约定一致。
            self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES[company_name], company_name)

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证两商业组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取长春维度。
        cc = ACCOUNTS["长春九州通医药有限公司"]

        # 断言长春大区省份负责人。
        self.assertEqual(cc["大区"], "西北东北")
        self.assertEqual(cc["省份"], "吉林省")
        self.assertEqual(cc["负责人"], "覃祝燕")

        # 读取浙江维度。
        zj = ACCOUNTS["浙江九州通医药有限公司"]

        # 断言浙江大区省份负责人。
        self.assertEqual(zj["大区"], "华南")
        self.assertEqual(zj["省份"], "浙江省")
        self.assertEqual(zj["负责人"], "覃祝燕")

    # 定义公开模板凭据留空验证。
    def test_public_template_credentials_are_blank(self):

        """
        验证两商业在公开模板中凭据留空（真实值仅在本地私有文件）。

        :return: None。
        :rtype: None
        """

        # 导入路径工具。
        from pathlib import Path

        # 读取公开模板源文件原文。
        public_source = Path(__file__).resolve().parents[1].joinpath("ddi_framework", "account_config.py").read_text(encoding="utf-8-sig")

        # 遍历两商业。
        for company_name in ("长春九州通医药有限公司", "浙江九州通医药有限公司"):

            # 定位商业条目文本。
            entry_start = public_source.index('"' + company_name + '": {')

            # 截取条目片段。
            entry_text = public_source[entry_start:public_source.index("},", entry_start)]

            # 断言账号与密码留空。
            self.assertIn('"账号": ""', entry_text, company_name)
            self.assertIn('"密码": ""', entry_text, company_name)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
