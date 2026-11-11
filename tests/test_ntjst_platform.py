# -*- coding: utf-8 -*-
"""
南通济生堂大药房 jshthy 平台配置级新增契约测试。

本模块验证南通济生堂的账号配置完整性、公司编码与台账一致、
网关参数携带 JT01、公开模板凭据留空与本地账密覆盖口径，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入路径工具。
from pathlib import Path

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入全亿健康 OA 平台适配器。
from ddi_framework.platforms.jshthy import JshthyPlatform, split_month_ranges

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义南通济生堂配置级新增测试套件。
class NantongJishengtangConfigTests(unittest.TestCase):

    """
    南通济生堂大药房 jshthy 平台配置级新增契约测试。

    :return: 测试套件实例。
    :rtype: NantongJishengtangConfigTests
    """

    # 定义类级商业名称引用。
    ACCOUNT_KEY = "南通济生堂大药房连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "库存"]

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证南通济生堂账号声明平台归属、站点双地址与公司编码。

        :return: None。
        :rtype: None
        """

        # 读取南通济生堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 jshthy。
        self.assertEqual(account["平台"], "jshthy")

        # 断言登录站点与数据网关地址与全亿健康族一致。
        self.assertEqual(account["接口根地址"], "https://oa.myquanyi.com")
        self.assertEqual(account["数据网关地址"], "https://xb-test.myquanyi.com:8080/portal-prod/gateway-manager/xxl-job")

        # 断言公司编码与租户编号与台账一致。
        self.assertEqual(account["公司编码"], "JT01")
        self.assertEqual(account["租户编号"], "18")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义组织维度声明验证。
    def test_account_dimensions(self):

        """
        验证南通济生堂组织维度与台账一致。

        :return: None。
        :rtype: None
        """

        # 读取南通济生堂维度。
        dimension = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言大区省份负责人。
        self.assertEqual(dimension["大区"], "东南")
        self.assertEqual(dimension["省份"], "江苏省")
        self.assertEqual(dimension["负责人"], "陈诗雅")

    # 定义网关参数公司编码验证。
    def test_gateway_params_carry_company_code(self):

        """
        验证网关业务参数携带南通济生堂独立公司编码。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = JshthyPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

        # 构建购进流向业务参数。
        params = platform.build_gateway_params("购进流向", "2026-10-01", "2026-10-27", 1)

        # 断言公司编码与租户编号。
        self.assertEqual(params["cort_num_id"], "JT01")
        self.assertEqual(params["tenant_num_id"], "18")

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
        验证本地私有文件提供南通济生堂真实凭据。

        :return: None。
        :rtype: None
        """

        # 读取本地私有配置字典。
        from ddi_framework.account_config_local import ACCOUNTS as LOCAL_ACCOUNTS

        # 读取本地南通济生堂条目。
        local_account = LOCAL_ACCOUNTS[self.ACCOUNT_KEY]

        # 断言本地账号与密码与全亿健康族共享账号一致。
        self.assertEqual(local_account["账号"], "JT190")
        self.assertEqual(local_account["密码"], "hbyyJT568")

    # 定义单月区间不拆分验证。
    def test_month_split_keeps_single_month_range(self):

        """
        验证单月内区间拆分保持原样。

        :return: None。
        :rtype: None
        """

        # 断言整月区间拆分为单段。
        self.assertEqual(split_month_ranges("2026-10-01", "2026-10-31"), [("2026-10-01", "2026-10-31")])

        # 断言同日区间拆分为单段。
        self.assertEqual(split_month_ranges("2026-09-15", "2026-09-15"), [("2026-09-15", "2026-09-15")])

        # 断言月内跨旬区间拆分为单段。
        self.assertEqual(split_month_ranges("2026-09-10", "2026-09-25"), [("2026-09-10", "2026-09-25")])

    # 定义跨月区间逐月拆分验证。
    def test_month_splits_cross_month_range(self):

        """
        验证跨月区间拆分为逐月连续子区间。

        :return: None。
        :rtype: None
        """

        # 断言两个月区间拆分为两段且首尾月份边界正确。
        self.assertEqual(split_month_ranges("2026-09-15", "2026-10-10"), [("2026-09-15", "2026-09-30"), ("2026-10-01", "2026-10-10")])

        # 断言三个月区间拆分为三段。
        self.assertEqual(split_month_ranges("2026-09-01", "2026-11-10"), [("2026-09-01", "2026-09-30"), ("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-10")])

        # 断言跨年区间按自然月逐段拆分。
        self.assertEqual(split_month_ranges("2026-12-15", "2027-01-05"), [("2026-12-15", "2026-12-31"), ("2027-01-01", "2027-01-05")])


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
