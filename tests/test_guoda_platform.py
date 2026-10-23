# -*- coding: utf-8 -*-
"""
国药控股国大药房广西连锁有限公司接入契约测试。

本模块验证国大平台类型门、过滤模型构建、账号配置完整性和注册表装载。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典与组织维度字典。
from ddi_framework.account_config import ACCOUNTS, ACCOUNT_DIMENSIONS

# 导入平台注册表。
from ddi_framework.platform_registry import PLATFORM_REGISTRY

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义国大平台接入契约测试套件。
class GuodaPlatformTests(unittest.TestCase):

    """
    国大药房流向数据平台接入契约测试。

    :return: 测试套件实例。
    :rtype: GuodaPlatformTests
    """

    # 定义类级账号键引用。
    ACCOUNT_KEY = "国药控股国大药房广西连锁有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "库存"]

    # 构建最小适配器实例。
    def build_platform(self):

        """
        构建用于纯逻辑验证的适配器实例。

        :return: 国大平台适配器实例。
        :rtype: GuodaPlatform
        """

        # 导入平台适配器类。
        from ddi_framework.platforms.guoda import GuodaPlatform

        # 返回最小配置实例。
        return GuodaPlatform(self.ACCOUNT_KEY, {"账号": "x", "密码": "y"}, printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证万鑫式分层配置与数据类型清单。

        :return: None。
        :rtype: None
        """

        # 读取账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属与站点地址。
        self.assertEqual(account["平台"], "guoda")
        self.assertEqual(account["站点地址"], "https://gdedi.sinopharmgroup.net")

        # 断言公开模板文件凭据留空（运行时字典已被本地私有文件合并，须验文件原文）。
        from pathlib import Path
        public_source = Path(__file__).resolve().parents[1].joinpath("ddi_framework", "account_config.py").read_text(encoding="utf-8-sig")
        entry_start = public_source.index('"' + self.ACCOUNT_KEY + '": {')
        entry_text = public_source[entry_start:public_source.index("},", entry_start)]
        self.assertIn('"账号": ""', entry_text)
        self.assertIn('"密码": ""', entry_text)

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言登录与验证码端点指向国大站点。
        self.assertIn("/EDI/CheckLogin", account["登录接口"])
        self.assertIn("/EDI/CheckCode", account["验证码接口"])

    # 定义组织维度验证。
    def test_org_dimensions_registered(self):

        """
        验证组织维度按广西既有归属登记。

        :return: None。
        :rtype: None
        """

        # 断言维度取值。
        self.assertEqual(ACCOUNT_DIMENSIONS[self.ACCOUNT_KEY], {"大区": "西南华中", "省份": "广西壮族自治区", "负责人": "梁彬彬"})

    # 定义上海复美账号声明完整性验证。
    def test_shanghai_fumei_account_declaration_is_complete(self):

        """
        验证国大复美(上海)账号镜像广西条目且凭据留空。

        :return: None。
        :rtype: None
        """

        # 定义上海复美账号键。
        fumei_key = "国药控股国大复美药业(上海)有限公司"

        # 读取上海复美账号配置。
        account = ACCOUNTS[fumei_key]

        # 断言平台归属与站点地址与广西同源。
        self.assertEqual(account["平台"], "guoda")
        self.assertEqual(account["站点地址"], "https://gdedi.sinopharmgroup.net")

        # 断言数据类型清单为三类型。
        self.assertEqual(account["数据类型列表"], ["配送流向", "购进流向", "库存"])

        # 断言公开模板凭据留空。
        from pathlib import Path

        # 读取公开模板源文件。
        public_source = Path(__file__).resolve().parents[1].joinpath("ddi_framework", "account_config.py").read_text(encoding="utf-8-sig")

        # 定位上海复美条目。
        entry_start = public_source.index('"' + fumei_key + '": {')

        # 断言凭据留空。
        self.assertIn('"账号": ""', public_source[entry_start:public_source.index("},", entry_start)])
        self.assertIn('"密码": ""', public_source[entry_start:public_source.index("},", entry_start)])

    # 定义注册表装载验证。
    def test_platform_registry_maps_guoda(self):

        """
        验证注册表映射指向国大平台适配器。

        :return: None。
        :rtype: None
        """

        # 断言注册表包含 guoda 键。
        self.assertIn("guoda", PLATFORM_REGISTRY)

        # 断言实例化企业名称传递正确。
        self.assertEqual(self.build_platform().company_name, self.ACCOUNT_KEY)

    # 定义类型门验证。
    def test_type_gate_accepts_supported_and_rejects_unknown(self):

        """
        验证类型门放行三类型并拦截未接入类型。

        :return: None。
        :rtype: None
        """

        # 构建适配器实例。
        platform = self.build_platform()

        # 逐类型断言放行。
        for data_type in self.EXPECTED_TYPES:

            # 类型门放行不抛出异常。
            platform.validate_data_type(data_type)

        # 断言未接入类型被拦截。
        with self.assertRaises(NotImplementedError):

            # 触发未接入异常。
            platform.validate_data_type("纯销流向")

    # 定义日期区间要求验证。
    def test_date_range_requirement_by_type(self):

        """
        验证流向类要求日期区间而库存类不要求。

        :return: None。
        :rtype: None
        """

        # 构建适配器实例。
        platform = self.build_platform()

        # 断言流向类要求日期区间。
        self.assertTrue(platform.requires_date_range("配送流向"))
        self.assertTrue(platform.requires_date_range("购进流向"))

        # 断言库存类不要求日期区间。
        self.assertFalse(platform.requires_date_range("库存"))

    # 定义过滤模型构建验证。
    def test_data_filter_shape_by_type(self):

        """
        验证流向类过滤模型带日期区间且库存类为空模型。

        :return: None。
        :rtype: None
        """

        # 构建适配器实例。
        platform = self.build_platform()

        # 断言配送流向过滤模型。
        self.assertEqual(platform.build_data_filter("配送流向", "2025-01-01", "2026-10-20"), {"BEGINDATE": "2025-01-01", "ENDDATE": "2026-10-20"})

        # 断言库存过滤模型为空字典。
        self.assertEqual(platform.build_data_filter("库存", None, None), {})

    # 定义分页参数验证。
    def test_page_size_locked_to_server_limit(self):

        """
        验证分页大小锁定服务端可接受值。

        :return: None。
        :rtype: None
        """

        # 构建适配器实例。
        platform = self.build_platform()

        # 断言页大小为服务端实测可接受的 100。
        self.assertEqual(platform.PAGE_SIZE, "100")


# 判断当前模块是否被直接执行。
if __name__ == "__main__":

    # 启动单元测试。
    unittest.main()
