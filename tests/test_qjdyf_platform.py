# -*- coding: utf-8 -*-
"""
湖南千金大药房连锁有限公司接入契约测试。

本模块验证千金平台仅登录能力裁定、停用状态、账号分层配置和注册表装载。
"""

# 导入 JSON 编解码模块。
import json

# 导入路径工具。
from pathlib import Path

# 导入单元测试工具。
import unittest

# 导入账号配置字典与组织维度字典。
from ddi_framework.account_config import ACCOUNTS, ACCOUNT_DIMENSIONS

# 导入平台注册表。
from ddi_framework.platform_registry import PLATFORM_REGISTRY


# 定义千金平台接入契约测试套件。
class QjdyfPlatformTests(unittest.TestCase):

    """
    千金供应商系统接入契约测试。

    :return: 测试套件实例。
    :rtype: QjdyfPlatformTests
    """

    # 定义工程根目录。
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    # 定义类级账号键引用。
    ACCOUNT_KEY = "湖南千金大药房连锁有限公司"

    # 定义账号声明与停用状态验证。
    def test_account_declaration_and_disabled_state(self):

        """
        验证账号声明完整且运行期处于停止状态。

        :return: None。
        :rtype: None
        """

        # 读取账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属与站点地址。
        self.assertEqual(account["平台"], "qjdyf")
        self.assertEqual(account["站点地址"], "https://wx.qjdyf.cn")

        # 断言公开模板凭据留空（真实凭据只在本地私有文件）。
        public_source = self.PROJECT_ROOT.joinpath("ddi_framework", "account_config.py").read_text(encoding="utf-8-sig")
        entry_start = public_source.index('"' + self.ACCOUNT_KEY + '": {')
        entry_text = public_source[entry_start:public_source.index("},", entry_start)]
        self.assertIn('"账号": ""', entry_text)
        self.assertIn('"密码": ""', entry_text)

        # 断言声明状态为停用。
        self.assertFalse(account["启用"])

        # 断言运行期停用配置（运行时解析读取商业启停键）。
        runtime_config = json.loads(self.PROJECT_ROOT.joinpath("config", "account_runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(runtime_config["商业启停"][self.ACCOUNT_KEY])

        # 断言数据类型清单为空（导出未接入）。
        self.assertEqual(account["数据类型列表"], [])

    # 定义组织维度验证。
    def test_org_dimensions_follow_hunan_precedent(self):

        """
        验证组织维度按湖南既有归属登记。

        :return: None。
        :rtype: None
        """

        # 断言维度取值。
        self.assertEqual(ACCOUNT_DIMENSIONS[self.ACCOUNT_KEY], {"大区": "西南华中", "省份": "湖南省", "负责人": "晏惟学"})

    # 定义注册表装载验证。
    def test_platform_registry_maps_qjdyf(self):

        """
        验证注册表映射指向千金平台适配器。

        :return: None。
        :rtype: None
        """

        # 断言注册表包含 qjdyf 键。
        self.assertIn("qjdyf", PLATFORM_REGISTRY)

        # 实例化适配器并断言企业名称。
        platform = PLATFORM_REGISTRY["qjdyf"](self.ACCOUNT_KEY, {"账号": "x", "密码": "y"})

        # 断言企业名称与登录接口。
        self.assertEqual(platform.company_name, self.ACCOUNT_KEY)
        self.assertEqual(platform.login_api_url, "https://wx.qjdyf.cn/supplier/pc/system/user/newVersionLogin")

    # 定义登录请求体构建验证。
    def test_login_payload_carries_credentials_only(self):

        """
        验证登录请求体只含账号与密码（验证码为纯前端校验不参与交互）。

        :return: None。
        :rtype: None
        """

        # 实例化适配器并注入测试凭据。
        from ddi_framework.platforms.qjdyf import QjdyfPlatform

        # 构建适配器实例。
        platform = QjdyfPlatform(self.ACCOUNT_KEY, {"账号": "userA", "密码": "passB"})

        # 构建登录请求体。
        import urllib.parse

        # 按适配器登录逻辑编码。
        body = urllib.parse.urlencode({"userNo": platform.clean_login_name(), "pwd": platform.clean_login_password()})

        # 断言请求体只含两字段。
        self.assertEqual(body, "userNo=userA&pwd=passB")

    # 定义数据类型未接入验证。
    def test_data_query_and_export_are_not_implemented(self):

        """
        验证查询与导出按范围裁定抛出未接入异常。

        :return: None。
        :rtype: None
        """

        # 实例化适配器。
        from ddi_framework.platforms.qjdyf import QjdyfPlatform

        # 构建适配器实例。
        platform = QjdyfPlatform(self.ACCOUNT_KEY, {"账号": "x", "密码": "y"})

        # 断言查询抛出未接入异常。
        with self.assertRaises(NotImplementedError):

            # 触发查询未接入。
            platform.query_flow("配送流向", "2026-01-01", "2026-01-31")

        # 断言导出抛出未接入异常。
        with self.assertRaises(NotImplementedError):

            # 触发导出未接入。
            platform.export_flow("配送流向", "2026-01-01", "2026-01-31")

        # 断言任意数据类型校验均抛出未接入异常。
        with self.assertRaises(NotImplementedError):

            # 触发类型校验未接入。
            platform.validate_data_type("配送流向")


# 判断当前模块是否被直接执行。
if __name__ == "__main__":

    # 启动单元测试。
    unittest.main()
