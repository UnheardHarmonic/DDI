# -*- coding: utf-8 -*-
"""
运行期账号覆盖测试。

本模块验证账号覆盖仅影响允许字段，并能被公共任务运行时作为独立账号副本使用。
"""

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入函数模拟模块。
from unittest.mock import patch

# 导入商业账号源码配置。
from ddi_framework.account_config import ACCOUNTS

# 导入账号覆盖清除函数。
from ddi_framework.account_config import clear_runtime_account_override

# 导入有效账号读取函数。
from ddi_framework.account_config import get_effective_account

# 导入运行期账号覆盖读取函数。
from ddi_framework.account_config import get_runtime_account_overrides

# 导入运行期账号覆盖保存函数。
from ddi_framework.account_config import save_runtime_account_override

# 导入运行期账号配置读取函数。
from ddi_framework.account_config import load_runtime_account_config

# 导入运行期账号配置保存函数。
from ddi_framework.account_config import save_runtime_account_config

# 导入任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入公共任务运行时。
from ddi_framework.task_runtime import DdiTaskRuntime


# 定义运行期账号覆盖测试类。
class RuntimeAccountOverrideTests(unittest.TestCase):

    """
    验证运行期账号覆盖的保存、回退和任务传递行为。

    :return: None。
    :rtype: None
    """

    # 定义测试初始化方法。
    def setUp(self):

        """
        初始化测试商业和连接字段。

        :return: None。
        :rtype: None
        """

        # 读取首个带登录页的商业名称。
        self.company_name = next(company_name for company_name, account in ACCOUNTS.items() if "登录页" in account)

        # 读取当前商业默认配置。
        self.default_account = ACCOUNTS[self.company_name]

        # 构建不含真实账号的测试账号值。
        self.test_account_name = "runtime-test-account"

        # 构建不含真实密码的测试密码值。
        self.test_password = "runtime-test-password"

        # 构建测试登录页地址。
        self.test_login_page = "https://runtime.example.test/login"

    # 定义账号覆盖合并与恢复默认测试方法。
    def test_override_merges_allowed_fields_and_preserves_enabled_config(self):

        """
        验证账号覆盖合并有效字段且保留既有商业启停配置。

        :return: None。
        :rtype: None
        """

        # 创建临时项目目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 保存既有商业启停配置。
            save_runtime_account_config({"商业启停": {self.company_name: False}}, project_root)

            # 保存账号和连接字段覆盖值。
            save_runtime_account_override(self.company_name, {"账号": self.test_account_name, "密码": self.test_password, "登录页": self.test_login_page}, project_root)

            # 读取合并后的有效账号配置。
            effective_account = get_effective_account(self.company_name, project_root)

            # 读取保存后的运行期账号配置。
            runtime_config = load_runtime_account_config(project_root)

            # 断言账号覆盖已生效。
            self.assertEqual(effective_account["账号"], self.test_account_name)

            # 断言密码覆盖已生效。
            self.assertEqual(effective_account["密码"], self.test_password)

            # 断言登录页覆盖已生效。
            self.assertEqual(effective_account["登录页"], self.test_login_page)

            # 断言商业启停配置仍被保留。
            self.assertFalse(runtime_config["商业启停"][self.company_name])

            # 清除当前商业账号覆盖。
            clear_runtime_account_override(self.company_name, project_root)

            # 读取恢复后的有效账号配置。
            restored_account = get_effective_account(self.company_name, project_root)

            # 断言账号已恢复源码默认值。
            self.assertEqual(restored_account["账号"], self.default_account["账号"])

            # 断言密码已恢复源码默认值。
            self.assertEqual(restored_account["密码"], self.default_account["密码"])

            # 断言账号覆盖已被删除。
            self.assertNotIn(self.company_name, get_runtime_account_overrides(load_runtime_account_config(project_root)))

    # 定义非法账号覆盖字段拒绝测试方法。
    def test_override_rejects_read_only_fields(self):

        """
        验证运行期账号覆盖拒绝平台等只读协议字段。

        :return: None。
        :rtype: None
        """

        # 创建临时项目目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 断言保存只读字段会抛出异常。
            with self.assertRaisesRegex(ValueError, "字段不允许运行期编辑"):

                # 尝试保存平台只读字段。
                save_runtime_account_override(self.company_name, {"平台": "changed"}, project_root)

    # 定义公共任务运行时账号覆盖传递测试方法。
    def test_runtime_uses_account_override_snapshot(self):

        """
        验证公共任务运行时将账号覆盖副本传给协议执行函数。

        :return: None。
        :rtype: None
        """

        # 创建临时项目目录。
        with tempfile.TemporaryDirectory() as project_root:

            # 保存当前商业账号覆盖。
            save_runtime_account_override(self.company_name, {"账号": self.test_account_name, "密码": self.test_password}, project_root)

            # 构建无界面任务请求。
            request = TaskRequest("login", "全部", "2026-06-01", "2026-06-30", f"{project_root}/cookies", f"{project_root}/downloads", f"{project_root}/logs", 1)

            # 模拟授权校验结果。
            license_result = {"授权状态": "有效"}

            # 模拟公共协议执行结果。
            protocol_result = {"商业名称": self.company_name}

            # 模拟授权和协议执行函数。
            with patch("ddi_framework.task_runtime.ensure_runtime_license", return_value=license_result), patch("ddi_framework.task_runtime.execute_protocol_company", return_value=protocol_result) as executor_mock:

                # 创建公共任务运行时。
                runtime = DdiTaskRuntime(project_root)

                # 执行模拟单商业任务。
                runtime.execute(request, [self.company_name])

            # 读取协议执行函数收到的账号配置。
            executed_account = executor_mock.call_args.args[1]

            # 断言协议执行函数收到覆盖后的账号。
            self.assertEqual(executed_account["账号"], self.test_account_name)

            # 断言协议执行函数收到覆盖后的密码。
            self.assertEqual(executed_account["密码"], self.test_password)

            # 断言源码账号配置未被改写。
            self.assertEqual(ACCOUNTS[self.company_name]["账号"], self.default_account["账号"])
