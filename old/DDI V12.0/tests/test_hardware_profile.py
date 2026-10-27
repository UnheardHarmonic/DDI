# -*- coding: utf-8 -*-
"""
DDI GUI 设备与运行环境信息测试。

本模块验证硬件采集结果中的网络信息与 MCP 地址均按脱敏规则展示。
"""

# 导入环境变量模拟工具。
from unittest.mock import patch

# 导入单元测试模块。
import unittest

# 导入网络信息构建函数。
from ddi_framework.hardware_profile import build_network_configuration_texts

# 导入硬件信息采集函数。
from ddi_framework.hardware_profile import read_hardware_profile

# 导入 MCP 地址脱敏函数。
from ddi_framework.hardware_profile import sanitize_mcp_url


# 定义设备信息测试类。
class HardwareProfileTests(unittest.TestCase):

    """
    验证首页展示的环境信息不会泄露硬件标识与地址凭据。

    :return: None。
    :rtype: None
    """

    # 定义 MCP 地址脱敏测试方法。
    def test_mcp_url_removes_credentials_query_and_fragment(self):

        """
        验证 MCP 地址仅保留协议、主机、端口与路径。

        :return: None。
        :rtype: None
        """

        # 构造含凭据和查询参数的 MCP 地址。
        source_url = "https://account:secret@mcp.example.com:8443/api?token=secret#section"

        # 脱敏当前 MCP 地址。
        display_url = sanitize_mcp_url(source_url)

        # 断言凭据和查询参数已被移除。
        self.assertEqual(display_url, "https://mcp.example.com:8443/api")

    # 定义网络地址筛选测试方法。
    def test_network_configuration_keeps_ip_gateway_and_dns_without_mac(self):

        """
        验证网络摘要显示 IPv4、IPv6、网关与 DNS，不保留 MAC 地址。

        :return: None。
        :rtype: None
        """

        # 构造活动网卡的 CIM 配置样本。
        configuration_items = [{"Description": "Intel Wi-Fi", "IPAddress": ["192.168.1.12", "fe80::9c4d"], "DefaultIPGateway": ["192.168.1.1"], "DNSServerSearchOrder": ["223.5.5.5", "2400:3200::1"]}]

        # 构建可展示的网络配置文本。
        configuration_texts = build_network_configuration_texts(configuration_items)

        # 断言 IPv4 地址被保留。
        self.assertIn("IPv4 192.168.1.12", configuration_texts[0])

        # 断言 IPv6 地址被保留。
        self.assertIn("IPv6 fe80::9c4d", configuration_texts[0])

        # 断言默认网关被保留。
        self.assertIn("网关 192.168.1.1", configuration_texts[0])

        # 断言 DNS 被保留。
        self.assertIn("DNS 223.5.5.5, 2400:3200::1", configuration_texts[0])

        # 断言网络摘要不包含 MAC 字段。
        self.assertNotIn("MAC", configuration_texts[0])

    # 定义异步采集结果字段测试方法。
    def test_hardware_profile_exposes_environment_fields_without_sensitive_identifiers(self):

        """
        验证硬件采集结果包含环境字段且不输出 MAC 地址。

        :return: None。
        :rtype: None
        """

        # 构造最小 CIM 采集结果。
        cim_result = {"ComputerSystem": [{"Manufacturer": "Test", "Model": "Device", "SystemType": "x64"}], "OperatingSystem": [{"Caption": "Microsoft Windows 11 Pro", "Version": "10.0.26100", "BuildNumber": "26100", "OSArchitecture": "64-bit"}], "NetworkConfiguration": [{"Description": "Ethernet", "IPAddress": ["10.0.0.8"], "DefaultIPGateway": ["10.0.0.1"], "DNSServerSearchOrder": ["1.1.1.1"]}]}

        # 模拟本机的 MCP 地址与当前用户。
        with patch.dict("os.environ", {"DDI_MCP_URL": "http://user:secret@127.0.0.1:3000/mcp?key=secret", "USERNAME": "tester"}, clear=False):

            # 模拟后台 CIM 采集结果。
            with patch("ddi_framework.hardware_profile.read_windows_cim_hardware", return_value=cim_result):

                # 读取首页设备信息。
                profile = read_hardware_profile()

        # 断言系统版本被写入结果。
        self.assertIn("Windows 11 Pro", profile["operating_system_text"])

        # 断言当前用户被写入结果。
        self.assertEqual(profile["user_text"], "tester")

        # 断言 MCP 地址已脱敏。
        self.assertEqual(profile["mcp_url_text"], "http://127.0.0.1:3000/mcp")

        # 断言活动网络地址被写入结果。
        self.assertIn("IPv4 10.0.0.8", profile["network_configuration_texts"][0])

        # 断言结果键中不包含 MAC 地址字段。
        self.assertFalse(any("mac" in key.lower() for key in profile))
