# -*- coding: utf-8 -*-
"""
重庆万鑫药房连锁有限公司 HReport 接入契约测试。

本模块验证万鑫账号配置完整性、库存业务别名归一和 HReport 平台类型门扩容。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典与组织维度字典。
from ddi_framework.account_config import ACCOUNTS, ACCOUNT_DIMENSIONS

# 导入数据类型大类归一函数。
from ddi_framework.task_core import normalize_data_type_category

# 导入 HReport 平台适配器。
from ddi_framework.platforms.hreport import HreportPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义万鑫接入契约测试套件。
class WanxinPlatformTests(unittest.TestCase):

    """
    重庆万鑫 HReport 接入契约测试。

    :return: 测试套件实例。
    :rtype: WanxinPlatformTests
    """

    # 定义类级账号配置引用。
    ACCOUNT_KEY = "重庆万鑫药房连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["购进流向", "配送流向", "连锁库存", "门店库存"]

    # 定义类级报表功能编号映射引用。
    EXPECTED_FUNC_IDS = {"购进流向": "37", "配送流向": "45", "连锁库存": "10001", "门店库存": "10002"}

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证万鑫账号声明包含平台、凭据、主机覆盖与数据类型清单。

        :return: None。
        :rtype: None
        """

        # 读取万鑫账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 HReport。
        self.assertEqual(account["平台"], "hreport")

        # 断言登录凭据已登记。
        self.assertTrue(str(account["账号"]).strip())
        self.assertTrue(str(account["密码"]).strip())

        # 断言全部主机覆盖指向万鑫站点。
        for key in ["登录页", "登录接口", "首页", "报表页", "报表参数接口", "查询接口"]:
            self.assertIn("222.177.143.25:7070", account[key], key)

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言报表功能编号覆盖全部数据类型。
        self.assertEqual(account["报表功能编号"], self.EXPECTED_FUNC_IDS)

    # 定义配送流向查询模板验证。
    def test_distribution_query_template_matches_capture(self):

        """
        验证配送流向查询模板字段与抓包表单一致。

        :return: None。
        :rtype: None
        """

        # 读取配送流向查询模板。
        template = ACCOUNTS[self.ACCOUNT_KEY]["查询字段模板"]["配送流向"]

        # 断言抓包实证字段全部在模板中。
        self.assertEqual(
            set(template.keys()),
            {"beginDate", "endDate", "buyer", "wareid", "billname", "userid", "factoryname", "funcId"},
        )

        # 断言日期占位符使用全局变量渲染语法。
        self.assertEqual(template["beginDate"], "{start_date}")
        self.assertEqual(template["endDate"], "{end_date}")
        self.assertEqual(template["funcId"], "{func_id}")

    # 定义组织维度验证。
    def test_org_dimensions_registered(self):

        """
        验证万鑫组织维度按董事长口径登记。

        :return: None。
        :rtype: None
        """

        # 读取万鑫组织维度。
        dimensions = ACCOUNT_DIMENSIONS[self.ACCOUNT_KEY]

        # 断言维度取值。
        self.assertEqual(dimensions, {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"})

    # 定义库存业务别名归一验证。
    def test_inventory_aliases_normalize_to_inventory_category(self):

        """
        验证连锁库存与门店库存归一到库存大类。

        :return: None。
        :rtype: None
        """

        # 断言连锁库存归一到库存大类。
        self.assertEqual(normalize_data_type_category("连锁库存"), "库存")

        # 断言门店库存归一到库存大类。
        self.assertEqual(normalize_data_type_category("门店库存"), "库存")

    # 定义平台类型门验证。
    def test_hreport_type_gate_accepts_wanxin_types(self):

        """
        验证 HReport 类型门放行万鑫四类数据类型。

        :return: None。
        :rtype: None
        """

        # 构建最小可用适配器实例。
        platform = HreportPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

        # 逐类型断言类型门放行。
        for data_type in self.EXPECTED_TYPES:

            # 类型门放行时不抛出异常。
            platform.validate_data_type(data_type)

        # 断言未接入类型仍被拦截。
        with self.assertRaises(NotImplementedError):

            # 触发未接入类型异常。
            platform.validate_data_type("报损流向")

    # 定义库存类日期区间要求验证。
    def test_inventory_types_do_not_require_date_range(self):

        """
        验证两类库存不要求日期区间且流向类要求。

        :return: None。
        :rtype: None
        """

        # 构建最小可用适配器实例。
        platform = HreportPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

        # 断言库存类不要求日期区间。
        self.assertFalse(platform.requires_date_range("连锁库存"))
        self.assertFalse(platform.requires_date_range("门店库存"))

        # 断言流向类要求日期区间。
        self.assertTrue(platform.requires_date_range("购进流向"))
        self.assertTrue(platform.requires_date_range("配送流向"))


# 判断当前模块是否被直接执行。
if __name__ == "__main__":

    # 启动单元测试。
    unittest.main()
