# -*- coding: utf-8 -*-
"""
山东燕喜堂医药连锁有限公司 yanxitang 平台接入契约测试。

本模块验证燕喜堂账号配置完整性、报表类型映射、库存双份口径、
维度信息与凭据合并，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入平台注册表。
from ddi_framework.platform_registry import PLATFORM_REGISTRY

# 导入燕喜堂平台适配器。
from ddi_framework.platforms.yanxitang import YanxitangPlatform


# 定义燕喜堂接入契约测试套件。
class YanxitangYxtTests(unittest.TestCase):

    """
    山东燕喜堂 yanxitang 平台接入契约测试。

    :return: 测试套件实例。
    :rtype: YanxitangYxtTests
    """

    # 定义类级账号配置引用。
    ACCOUNT_KEY = "山东燕喜堂医药连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "大仓库存", "门店库存"]

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建燕喜堂平台适配器实例。

        :return: 燕喜堂平台适配器实例。
        :rtype: YanxitangPlatform
        """

        # 读取燕喜堂账号配置并构建适配器。
        return YanxitangPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY])

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证燕喜堂账号声明包含平台归属、凭据合并与数据类型清单。

        :return: None。
        :rtype: None
        """

        # 读取燕喜堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为燕喜堂 ELS 平台。
        self.assertEqual(account["平台"], "yanxitang")

        # 断言私有凭据已合并。
        self.assertEqual(account["账号"], "0")
        self.assertTrue(str(account["密码"]).strip())

        # 断言 ELS 企业号与接口主机覆盖。
        self.assertEqual(account["ELS账号"], "100004244")
        self.assertIn("srm.sdyanxitang.com", account["接口根地址"])

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义报表类型映射验证。
    def test_report_type_mapping_matches_capture(self):

        """
        验证报表类型与库存类型映射与抓包负载一致。

        :return: None。
        :rtype: None
        """

        # 读取燕喜堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言报表类型映射（入库退货1/销售退货2/库存3/零售4）。
        self.assertEqual(account["报表类型映射"], {"配送流向": "2", "购进流向": "1", "纯销流向": "4", "大仓库存": "3", "门店库存": "3"})

        # 断言库存类型映射（大仓1/门店2 两份导出口径）。
        self.assertEqual(account["库存类型映射"], {"大仓库存": "1", "门店库存": "2"})

    # 定义维度信息验证。
    def test_dimensions_written(self):

        """
        验证董事长给定维度三字段写入。

        :return: None。
        :rtype: None
        """

        # 读取燕喜堂账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言维度与董事长给定一致。
        self.assertEqual(account["大区"], "东南")
        self.assertEqual(account["省份"], "山东省")
        self.assertEqual(account["负责人"], "陈诗雅")

    # 定义类型门放行验证。
    def test_validate_data_type_passes_all_types(self):

        """
        验证五类型均通过类型门校验。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 逐类型校验不抛异常。
        for data_type in self.EXPECTED_TYPES:
            platform.validate_data_type(data_type)

    # 定义平台注册验证。
    def test_platform_registered(self):

        """
        验证 yanxitang 平台标识已注册适配器。

        :return: None。
        :rtype: None
        """

        # 断言注册表包含 yanxitang 且类正确。
        self.assertIs(PLATFORM_REGISTRY["yanxitang"], YanxitangPlatform)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
