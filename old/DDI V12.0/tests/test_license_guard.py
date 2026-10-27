# -*- coding: utf-8 -*-
"""
DDI 本机源码开发授权测试。

本模块验证本机开发授权只能在源码环境中匹配当前机器身份后生效。
"""

# 导入 JSON 编解码模块。
import json

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入路径处理模块。
from pathlib import Path

# 导入模拟工具。
from unittest.mock import patch

# 导入授权校验函数。
from ddi_framework.license_guard import ensure_runtime_license

# 导入授权校验异常类型。
from ddi_framework.license_guard import LicenseError

# 导入源码开发环境识别函数。
from ddi_framework.license_guard import is_source_development_context


# 定义本机开发授权测试类。
class LocalDevelopmentLicenseTests(unittest.TestCase):

    """
    验证本机开发授权不会替代冻结发布程序的签名授权。

    :return: None。
    :rtype: None
    """

    # 定义有效本机开发授权测试方法。
    def test_source_development_license_accepts_matching_runtime_identity(self):

        """
        验证匹配当前身份的本机开发授权可在源码环境通过校验。

        :return: None。
        :rtype: None
        """

        # 创建独立临时项目目录。
        with tempfile.TemporaryDirectory() as temporary_directory:

            # 解析临时项目根目录。
            project_root = Path(temporary_directory)

            # 创建本机开发授权配置目录。
            configuration_directory = project_root / "config"

            # 创建授权配置目录。
            configuration_directory.mkdir()

            # 构造测试运行环境身份。
            runtime_identity = {"machine_code": "TEST-MACHINE-CODE", "machine_name": "TEST-HOST", "user_name": "tester"}

            # 构造本机开发授权数据。
            development_license = {"mode": "source-development", "license_id": "TEST-LOCAL-DEVELOPMENT", "enabled": True, "allowed_versions": ["DDI_V4.0"], "machine_code": runtime_identity["machine_code"], "machine_name": runtime_identity["machine_name"], "user_name": runtime_identity["user_name"]}

            # 写入临时本机开发授权配置。
            (configuration_directory / "local_development.json").write_text(json.dumps(development_license), encoding="utf-8")

            # 模拟当前调用来自源码开发环境。
            with patch("ddi_framework.license_guard.is_source_development_context", return_value=True):

                # 模拟当前运行环境身份。
                with patch("ddi_framework.license_guard.build_runtime_identity", return_value=runtime_identity):

                    # 执行本机开发授权校验。
                    license_result = ensure_runtime_license(project_root)

            # 断言本机开发授权结果被返回。
            self.assertEqual(license_result["授权状态"], "本机开发模式")

    # 定义机器身份不匹配测试方法。
    def test_source_development_license_rejects_different_machine_identity(self):

        """
        验证本机开发授权不会在不同机器身份下通过校验。

        :return: None。
        :rtype: None
        """

        # 创建独立临时项目目录。
        with tempfile.TemporaryDirectory() as temporary_directory:

            # 解析临时项目根目录。
            project_root = Path(temporary_directory)

            # 创建本机开发授权配置目录。
            configuration_directory = project_root / "config"

            # 创建授权配置目录。
            configuration_directory.mkdir()

            # 构造授权绑定机器身份。
            license_identity = {"machine_code": "LICENSE-MACHINE-CODE", "machine_name": "LICENSE-HOST", "user_name": "tester"}

            # 构造实际运行机器身份。
            runtime_identity = {"machine_code": "OTHER-MACHINE-CODE", "machine_name": "LICENSE-HOST", "user_name": "tester"}

            # 构造本机开发授权数据。
            development_license = {"mode": "source-development", "license_id": "TEST-LOCAL-DEVELOPMENT", "enabled": True, "allowed_versions": ["DDI_V4.0"], "machine_code": license_identity["machine_code"], "machine_name": license_identity["machine_name"], "user_name": license_identity["user_name"]}

            # 写入临时本机开发授权配置。
            (configuration_directory / "local_development.json").write_text(json.dumps(development_license), encoding="utf-8")

            # 模拟当前调用来自源码开发环境。
            with patch("ddi_framework.license_guard.is_source_development_context", return_value=True):

                # 模拟不同机器的运行环境身份。
                with patch("ddi_framework.license_guard.build_runtime_identity", return_value=runtime_identity):

                    # 断言不同机器身份无法通过校验。
                    with self.assertRaises(LicenseError):

                        # 执行本机开发授权校验。
                        ensure_runtime_license(project_root)

    # 定义跨机器开发授权回退签名授权测试方法。
    def test_foreign_source_development_license_falls_back_to_signed_license(self):

        """
        验证复制而来的开发授权不会阻断有效签名授权。

        :return: None。
        :rtype: None
        """

        # 创建独立临时项目目录。
        with tempfile.TemporaryDirectory() as temporary_directory:

            # 解析临时项目根目录。
            project_root = Path(temporary_directory)

            # 创建授权配置目录。
            configuration_directory = project_root / "config"

            # 落地授权配置目录。
            configuration_directory.mkdir()

            # 构造复制来源的开发授权身份。
            foreign_identity = {"machine_code": "HOME-MACHINE-CODE", "machine_name": "HOME-HOST", "user_name": "home-user"}

            # 构造当前公司的运行环境身份。
            runtime_identity = {"machine_code": "COMPANY-MACHINE-CODE", "machine_name": "COMPANY-HOST", "user_name": "company-user"}

            # 构造跨机器的开发授权数据。
            development_license = {"mode": "source-development", "license_id": "TEST-FOREIGN-DEVELOPMENT", "enabled": True, "allowed_versions": ["DDI_V4.0"], "machine_code": foreign_identity["machine_code"], "machine_name": foreign_identity["machine_name"], "user_name": foreign_identity["user_name"]}

            # 写入跨机器的开发授权文件。
            (configuration_directory / "local_development.json").write_text(json.dumps(development_license), encoding="utf-8")

            # 写入供签名校验替身读取的正式授权文件。
            (configuration_directory / "license.json").write_text("{}", encoding="utf-8")

            # 模拟当前调用来自源码开发环境。
            with patch("ddi_framework.license_guard.is_source_development_context", return_value=True):

                # 模拟当前公司的运行环境身份。
                with patch("ddi_framework.license_guard.build_runtime_identity", return_value=runtime_identity):

                    # 模拟有效签名授权的校验结果。
                    with patch("ddi_framework.license_guard.validate_license_data", return_value={"授权状态": "有效"}) as validate_license:

                        # 执行授权校验。
                        license_result = ensure_runtime_license(project_root)

            # 断言已返回签名授权校验结果。
            self.assertEqual(license_result["授权状态"], "有效")

            # 断言已调用签名授权校验流程。
            validate_license.assert_called_once()

    # 定义冻结发布程序隔离测试方法。
    def test_frozen_distribution_cannot_use_source_development_mode(self):

        """
        验证冻结发布程序不会被识别为源码开发环境。

        :return: None。
        :rtype: None
        """

        # 读取授权模块所在的源码项目根目录。
        project_root = Path(__file__).resolve().parent.parent

        # 模拟 PyInstaller 冻结发布标记。
        with patch("ddi_framework.license_guard.sys.frozen", True, create=True):

            # 断言冻结发布程序无法使用本机开发模式。
            self.assertFalse(is_source_development_context(project_root))
