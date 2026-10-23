# -*- coding: utf-8 -*-
"""
心链-SRM（hxyxt）平台商业配置契约测试。

本模块验证重庆/天津/上海三家鸿翔系商业的账号配置镜像关系、
子账号区分、类型清单与公开模板凭据留空口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS


# 定义心链-SRM 商业配置契约测试套件。
class HxyxtPlatformConfigTests(unittest.TestCase):

    """
    hxyxt 平台商业配置契约测试。

    :return: 测试套件实例。
    :rtype: HxyxtPlatformConfigTests
    """

    # 定义类级商业名称与子账号映射引用。
    EXPECTED_SUB_ACCOUNTS = {
        "重庆鸿翔一心堂药业有限公司": ("1004", "abc123456"),
        "天津鸿翔一心堂医药连锁有限公司": ("1003", "123456"),
        "上海鸿翔一心堂药业有限公司": ("1007", "123456"),
    }

    # 定义账号声明完整性验证。
    def test_hongxiang_accounts_mirror_and_differ_by_sub_account(self):

        """
        验证三家鸿翔商业同主账号镜像端点且以子账号区分。

        :return: None。
        :rtype: None
        """

        # 遍历预期商业清单。
        for company_name, (sub_account, password) in self.EXPECTED_SUB_ACCOUNTS.items():

            # 读取商业账号配置。
            account = ACCOUNTS[company_name]

            # 断言平台归属为心链-SRM。
            self.assertEqual(account["平台"], "hxyxt", company_name)

            # 断言站点根地址同站。
            self.assertEqual(account["站点根地址"], "https://yxt-srm.hxyxt.com", company_name)

            # 断言子账号区分商业。
            self.assertEqual(account["子账号"], sub_account, company_name)

            # 断言公开模板密码字段名存在（真实值在本地私有文件）。
            self.assertIn("密码", account, company_name)

    # 定义上海商业专属声明验证。
    def test_shanghai_account_declaration(self):

        """
        验证上海鸿翔条目的公司代码名称、纸张与类型清单。

        :return: None。
        :rtype: None
        """

        # 读取上海鸿翔账号配置。
        account = ACCOUNTS["上海鸿翔一心堂药业有限公司"]

        # 断言公司代码名称与抓包一致。
        self.assertEqual(account["公司代码名称"], "上海公司")

        # 断言纸张参数与配送抓包一致。
        self.assertEqual(account["纸张宽度"], 719)
        self.assertEqual(account["纸张高度"], 773)

        # 断言数据类型清单为配送加库存两类型。
        self.assertEqual(account["数据类型列表"], ["配送流向", "库存"])

        # 断言操作员名称为商业全名。
        self.assertEqual(account["操作员名称"], "上海鸿翔一心堂药业有限公司")

    # 定义公开模板凭据留空验证。
    def test_public_template_credentials_are_blank(self):

        """
        验证沪津两商业在公开模板中凭据留空（真实值仅在本地私有文件）。

        :return: None。
        :rtype: None
        """

        # 导入路径工具。
        from pathlib import Path

        # 读取公开模板源文件原文。
        public_source = Path(__file__).resolve().parents[1].joinpath("ddi_framework", "account_config.py").read_text(encoding="utf-8-sig")

        # 遍历沪津两商业。
        for company_name in ("天津鸿翔一心堂医药连锁有限公司", "上海鸿翔一心堂药业有限公司"):

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
